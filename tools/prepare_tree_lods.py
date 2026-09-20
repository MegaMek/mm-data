"""Run with Blender --background --python tools/prepare_tree_lods.py.

Keep the near mesh's visible triangles and their exact attributes. Remove only
triangles strictly enclosed in another closed component, with no intersection
with that component's surface. Generate the smaller, textured meshes offline;
the renderer never simplifies geometry or changes tree placement.
"""
import collections
import copy
import json
import math
from pathlib import Path

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

BOARD = Path(__file__).resolve().parents[1] / 'data/models/board'
BUDGETS = (240, 96)


def geometry(model):
    """Weld positions for topology only; retain the authored per-corner data."""
    vertices, shared, faces, corners = [], {}, [], []
    mesh = model['meshes'][0]
    source = mesh['vertices']
    for part in mesh['parts']:
        for offset in range(0, len(part['indices']), 3):
            attributes = [source[i * 12:i * 12 + 12] for i in part['indices'][offset:offset + 3]]
            face = []
            for vertex in attributes:
                # Simplification operates in the tree's original proportions.
                point = (vertex[0], vertex[1], vertex[2] * 30)
                if point not in shared:
                    shared[point] = len(vertices)
                    vertices.append(Vector(point))
                face.append(shared[point])
            faces.append(face)
            corners.append((part['id'], attributes))
    return vertices, faces, corners


def enclosed_faces(vertices, faces):
    adjacent = [set() for _ in vertices]
    for face in faces:
        for vertex in face:
            adjacent[vertex].update(face)
    components, visited = [], set()
    for start in range(len(vertices)):
        if start in visited:
            continue
        group, pending = set(), [start]
        while pending:
            vertex = pending.pop()
            if vertex not in group:
                group.add(vertex)
                pending.extend(adjacent[vertex] - group)
        visited.update(group)
        components.append([i for i, face in enumerate(faces) if face[0] in group])
    whole = BVHTree.FromPolygons(vertices, faces, all_triangles=True)
    hidden = set()
    for component in components:
        surface = [faces[i] for i in component]
        edges = collections.Counter((face[k], face[(k + 1) % 3]) for face in surface for k in range(3))
        # Open palm fronds must never be mistaken for enclosing volumes.
        if any(count != 1 or edges[b, a] != 1 for (a, b), count in edges.items()):
            continue
        shell = BVHTree.FromPolygons(vertices, surface, all_triangles=True)
        intersecting = {a for a, _ in whole.overlap(shell)} | set(component)
        triangles = [[vertices[i] for i in face] for face in surface]

        def inside(point):
            if shell.find_nearest(point)[3] < 0.0001:
                return False
            # Solid angle works for concave canopies too; no assumed ray direction.
            angle = 0
            for triangle in triangles:
                a, b, c = [vertex - point for vertex in triangle]
                denominator = (a.length * b.length * c.length + a.dot(b) * c.length
                               + b.dot(c) * a.length + c.dot(a) * b.length)
                angle += 2 * math.atan2(a.dot(b.cross(c)), denominator)
            return abs(angle) > 2 * math.pi

        for index, face in enumerate(faces):
            if index in intersecting or index in hidden:
                continue
            points = [vertices[i] for i in face]
            if inside(sum(points, Vector()) / 3) and all(inside(point) for point in points):
                hidden.add(index)
    return hidden


def pack(source, name, corners):
    model = copy.deepcopy(source)
    vertices, shared, parts = [], {}, {}
    for role, triangle in corners:
        indices = parts.setdefault(role, [])
        for vertex in triangle:
            key = tuple(vertex)
            if key not in shared:
                shared[key] = len(vertices) // 12
                vertices.extend(vertex)
            indices.append(shared[key])
    model['id'] = name
    model['meshes'] = [{'attributes': ['POSITION', 'NORMAL', 'COLOR', 'TEXCOORD0'], 'vertices': vertices,
                        'parts': [{'id': role, 'type': 'TRIANGLES', 'indices': indices}
                                  for role, indices in parts.items()]}]
    model['nodes'] = [{'id': name, 'parts': [{'meshpartid': role, 'materialid': role} for role in parts]}]
    return model


def simplified(source, name, budget):
    vertices, faces, corners = geometry(source)
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    materials, roles = {}, []
    for polygon, (role, attributes) in zip(mesh.polygons, corners):
        key = (role, tuple(attributes[0][6:10]))
        if key not in materials:
            materials[key] = len(roles)
            roles.append(key)
            mesh.materials.append(bpy.data.materials.new(role))
        polygon.material_index = materials[key]
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    modifier = obj.modifiers.new('Tree screen-size detail', 'DECIMATE')
    modifier.ratio = min(1, budget / len(faces))
    modifier.use_collapse_triangulate = True
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    mesh = obj.data
    mesh.calc_loop_triangles()
    result = []
    low = Vector(tuple(min(point[i] for point in vertices) for i in range(3)))
    high = Vector(tuple(max(point[i] for point in vertices) for i in range(3)))
    for triangle in mesh.loop_triangles:
        role, color = roles[triangle.material_index]
        normal = triangle.normal
        n = Vector((normal.x, normal.y, normal.z * 30)).normalized()
        attributes = []
        for index in triangle.vertices:
            point = mesh.vertices[index].co
            # All levels share the near model's coordinate system and bounds.
            point = Vector(tuple(max(low[i], min(high[i], point[i])) for i in range(3)))
            if abs(normal.z) >= max(abs(normal.x), abs(normal.y)):
                uv = (point.x, point.y)
            else:
                uv = (point.x if abs(normal.y) > abs(normal.x) else point.y, point.z)
            repeat = 4 if role.startswith('bark') else 8 if name.startswith('birch') else 12
            attributes.append(tuple(round(v, 6) for v in
                                    (point.x, point.y, point.z / 30, *n, *color, uv[0] / repeat, uv[1] / repeat)))
        result.append((role, attributes))
    bpy.data.objects.remove(obj, do_unlink=True)
    bpy.data.meshes.remove(mesh)
    assert len(result) <= budget, (name, len(result), budget)
    return pack(source, name, result)


def counts(model):
    mesh = model['meshes'][0]
    return {'triangles': sum(len(part['indices']) // 3 for part in mesh['parts']),
            'vertices': len(mesh['vertices']) // 12}


def prepare():
    manifest = json.loads((BOARD / 'manifest.json').read_text())
    old_scene = bpy.context.window.scene
    scene = bpy.data.scenes.new('MegaMek tree detail levels')
    bpy.context.window.scene = scene
    try:
        for name, entry in manifest.items():
            if 'source' not in entry:
                continue
            source = json.loads((BOARD / (name + '.g3dj')).read_text())
            vertices, faces, corners = geometry(source)
            hidden = enclosed_faces(vertices, faces)
            near_name = name + '-lod0'
            near = pack(source, near_name, [corner for index, corner in enumerate(corners) if index not in hidden])
            entry['lods'] = [{'asset': near_name, **counts(near)}]
            (BOARD / (near_name + '.g3dj')).write_text(json.dumps(near, separators=(',', ':')))
            for level, budget in enumerate(BUDGETS, 1):
                asset = f'{name}-lod{level}'
                budget = min(budget, entry['triangles'] // (2 if level == 1 else 5))
                # Simplify the closed original, so enclosed surfaces cannot leave
                # holes when the distant canopy changes shape.
                model = simplified(source, asset, budget)
                (BOARD / (asset + '.g3dj')).write_text(json.dumps(model, separators=(',', ':')))
                entry['lods'].append({'asset': asset, **counts(model)})
            # Keep the authored model for close transparent trees: their enclosed
            # branches can become visible through a faded canopy.
            print(name, entry['triangles'], '->',
                  [lod['triangles'] for lod in entry['lods']], flush=True)
        (BOARD / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    finally:
        bpy.context.window.scene = old_scene
        bpy.data.scenes.remove(scene)


if __name__ == '__main__':
    prepare()
