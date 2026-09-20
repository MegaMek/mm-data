"""Render labelled review sheets of the deployed modular bare bodies.

The variant renderer reads the frozen legacy bakes; this one reads the live schema-2 bodies
under data/models/units/modular/bodies, so a newly authored chassis can be reviewed before
any game data is staged. Bare bodies only: weapons and troops are assembled by Java.

blender --background --factory-startup --python-exit-code 1 \
    --python tools/render_modular_body.py -- --body locust --body atlas --turn 60
"""
import argparse
import json
from math import ceil, radians
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bpy
from mathutils import Euler, Matrix, Vector

ROOT = Path(__file__).resolve().parents[1]
BODIES = ROOT / 'data/models/units/modular/bodies'
MANIFEST = ROOT / 'data/models/units/modular/manifest.json'
RECIPES = ROOT / 'tools/unit-models/chassis.json'

# Presenting the model to one fixed camera keeps every view on a single render. The camera sits
# behind the grid looking along +Y, so a body must turn 180 to show the front it was authored
# facing. Above tips the model onto its back, which puts its nose up the page like the game sprite.
VIEWS = [('Front', (0, 0, 180)), ('Back', (0, 0, 0)), ('Left', (0, 0, 90)),
         ('Right', (0, 0, -90)), ('Above', (90, 0, 0)), ('Three-quarter', (0, 0, 215))]


def material(rgb, cache):
    """House convention: authored colors are sRGB, Blender shades in linear light."""
    key = tuple(rgb)
    if key not in cache:
        result = bpy.data.materials.new('Body color ' + str(key))
        linear = tuple(c / 12.92 if c <= .04045 else ((c + .055) / 1.055) ** 2.4 for c in rgb)
        result.diffuse_color = (*linear, 1)
        result.use_nodes = True
        shader = result.node_tree.nodes.get('Principled BSDF')
        shader.inputs['Base Color'].default_value = (*linear, 1)
        shader.inputs['Roughness'].default_value = .8
        # A plan view looks into enclosed recesses that no lamp reaches. A faint self-lit floor keeps
        # those reading as dark grey rather than as pure black holes in the hull.
        shader.inputs['Emission Color'].default_value = (*linear, 1)
        shader.inputs['Emission Strength'].default_value = .06
        cache[key] = result
    return cache[key]


def load_body(path, expected, colors, turn=0, upper_body='CT'):
    """Schema-2 bodies keep vertices local to their node and stack rigid translations.

    Unlike the legacy bake these carry a paint UV and unnormalized Z, so the stride is read
    from the attribute list rather than assumed.
    """
    data = json.loads(path.read_text(encoding='utf-8'))
    parts, strides = {}, {'POSITION': 3, 'NORMAL': 3, 'COLOR': 4, 'TEXCOORD0': 2}
    for mesh in data['meshes']:
        attributes = mesh['attributes']
        unknown = [name for name in attributes if name not in strides]
        if unknown:
            raise ValueError('Unsupported vertex attribute ' + ', '.join(unknown))
        stride = sum(strides[name] for name in attributes)
        color = sum(strides[name] for name in attributes[:attributes.index('COLOR')])
        for part in mesh['parts']:
            parts[part['id']] = (mesh['vertices'], part['indices'], stride, color)
    vertices, faces, face_colors = [], [], []

    def visit(node, parent, pivot=None):
        if 'rotation' in node or 'scale' in node:
            raise ValueError('The review importer only supports the generated translated nodes')
        offset = parent + Vector(node.get('translation', (0, 0, 0)))
        if node['id'] == upper_body:
            pivot = offset
        for part in node.get('parts', []):
            source, indices, stride, color = parts[part['meshpartid']]
            for corner in range(0, len(indices), 3):
                start = len(vertices)
                for index in indices[corner:corner + 3]:
                    point = Vector(source[index * stride:index * stride + 3]) + offset
                    if pivot is not None and turn:
                        point = Matrix.Rotation(radians(-turn), 3, 'Z') @ (point - pivot) + pivot
                    vertices.append(tuple(point))
                faces.append((start, start + 1, start + 2))
                first = indices[corner] * stride + color
                face_colors.append(tuple(source[first:first + 3]))
        for child in node.get('children', []):
            visit(child, offset, pivot)

    for node in data['nodes']:
        visit(node, Vector((0, 0, 0)))
    if expected and len(faces) != expected['triangles']:
        raise ValueError('Triangle mismatch for %s: rendered %d, manifest %d'
                         % (path.name, len(faces), expected['triangles']))
    mesh = bpy.data.meshes.new(data['id'])
    mesh.from_pydata(vertices, [], faces)
    slots = {}
    for color in dict.fromkeys(face_colors):
        slots[color] = len(mesh.materials)
        mesh.materials.append(material(color, colors))
    for polygon, color in zip(mesh.polygons, face_colors):
        polygon.material_index = slots[color]
        # Flat shading is the established look; smoothing would hide the authored facets.
        polygon.use_smooth = False
    return mesh


def label(scene, body, position, size, ink, align='CENTER'):
    curve = bpy.data.curves.new(body, 'FONT')
    curve.body = body
    curve.align_x = align
    curve.size = size
    curve.materials.append(ink)
    obj = bpy.data.objects.new(body, curve)
    obj.location = position
    # The sheet is read face-on, so the text stands up in the camera's plane.
    obj.rotation_euler = (radians(90), 0, 0)
    scene.collection.objects.link(obj)


def posed_bounds(mesh, rotation):
    """Extent of the mesh once a view's rotation is applied, so every cell can be centred."""
    matrix = Euler([radians(angle) for angle in rotation], 'XYZ').to_matrix()
    points = [matrix @ vertex.co for vertex in mesh.vertices]
    low = Vector((min(p.x for p in points), min(p.y for p in points), min(p.z for p in points)))
    high = Vector((max(p.x for p in points), max(p.y for p in points), max(p.z for p in points)))
    return low, high


def render(body_id, mesh, views, out, columns=3, title=None):
    scene = bpy.data.scenes.new(body_id + ' review')
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 24
    scene.render.image_settings.file_format = 'PNG'
    scene.view_settings.view_transform = 'Standard'
    scene.world = bpy.data.worlds.new(body_id + ' world')
    scene.world.use_nodes = True
    scene.world.node_tree.nodes['Background'].inputs[0].default_value = (.22, .28, .35, 1)

    ink = bpy.data.materials.new('Sheet labels')
    ink.use_nodes = True
    ink.node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value = (1, 1, 1, 1)

    # One cell fits the largest view, so a plan view cannot crowd an elevation.
    posed = {name: posed_bounds(mesh, rotation) for name, rotation in views}
    reach = max(max(high.x - low.x, high.z - low.z) for low, high in posed.values())
    columns = min(columns, len(views))
    rows = ceil(len(views) / columns)
    cell, pitch = reach * 1.18, reach * 1.46
    span, tall = cell * columns, pitch * rows
    # Labels sit well in front of the geometry; an angled view would otherwise occlude its caption.
    front = -reach * 3
    for index, (name, rotation) in enumerate(views):
        low, high = posed[name]
        middle = (low + high) / 2
        cell_x = (index % columns) * cell - span / 2 + cell / 2
        cell_z = -(index // columns) * pitch
        obj = bpy.data.objects.new(body_id + ' ' + name, mesh)
        obj.rotation_euler = tuple(radians(angle) for angle in rotation)
        obj.location = (cell_x - middle.x, 0, cell_z - middle.z)
        scene.collection.objects.link(obj)
        label(scene, name, (cell_x, front, cell_z - pitch * .43), reach * .052, ink)
    # The unit is named top right on every sheet, matching the assembled review renders.
    label(scene, title or body_id, (span / 2 - cell * .06, front, pitch * .40), reach * .072, ink, 'RIGHT')

    camera_data = bpy.data.cameras.new(body_id + ' camera')
    camera_data.type = 'ORTHO'
    camera_data.ortho_scale = span
    camera = bpy.data.objects.new(body_id + ' camera', camera_data)
    # +Y is forward, so the camera sits in front of the grid and looks back along -Y.
    # Centre on the block of rows; each row is a full pitch tall, so the labels stay inside.
    camera.location = (0, -reach * 6, -(rows - 1) * pitch / 2)
    camera.rotation_euler = (radians(90), 0, 0)
    scene.collection.objects.link(camera)
    scene.camera = camera

    sun = bpy.data.lights.new(body_id + ' sun', 'SUN')
    sun.energy = 3.2
    sun_object = bpy.data.objects.new(body_id + ' sun', sun)
    sun_object.rotation_euler = (radians(58), 0, radians(-35))
    scene.collection.objects.link(sun_object)

    fill = bpy.data.lights.new(body_id + ' fill', 'SUN')
    fill.energy = 1.1
    fill_object = bpy.data.objects.new(body_id + ' fill', fill)
    fill_object.rotation_euler = (radians(72), 0, radians(130))
    scene.collection.objects.link(fill_object)

    # A plan view looks straight into the gaps between shoulders and torso. Without an overhead
    # light those read as pure black holes rather than as recesses.
    overhead = bpy.data.lights.new(body_id + ' overhead', 'SUN')
    overhead.energy = .9
    overhead_object = bpy.data.objects.new(body_id + ' overhead', overhead)
    overhead_object.rotation_euler = (0, 0, 0)
    scene.collection.objects.link(overhead_object)

    scene.render.resolution_x = 520 * columns
    scene.render.resolution_y = round(scene.render.resolution_x * tall / span)
    scene.render.filepath = str(out / (body_id + '-review.png'))
    bpy.ops.render.render(write_still=True, scene=scene.name)
    return Path(scene.render.filepath)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--body', action='append', default=[],
                        help='body id under data/models/units/modular/bodies; repeatable')
    parser.add_argument('--turn', type=float, default=0,
                        help='degrees of upper-body twist, for the waist clearance check')
    parser.add_argument('--output', type=Path, default=ROOT / '.work/body-review')
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
    if not args.body:
        parser.error('name at least one --body')

    manifest = json.loads(MANIFEST.read_text(encoding='utf-8'))['assets'] if MANIFEST.exists() else {}
    # A sheet is headed with the chassis as players know it, not the body's file id.
    titles = {entry['id']: entry['name'] for entry in
              json.loads(RECIPES.read_text(encoding='utf-8'))['chassis']} if RECIPES.exists() else {}
    args.output.mkdir(parents=True, exist_ok=True)
    colors = {}
    for body_id in args.body:
        path = BODIES / (body_id + '.g3dj')
        if not path.exists():
            raise SystemExit('No such body: ' + str(path))
        expected = manifest.get('bodies/' + body_id)
        mesh = load_body(path, expected, colors)
        print('Wrote', render(body_id, mesh, list(VIEWS), args.output, title=titles.get(body_id, body_id)))
        if args.turn:
            # The twisted copy is separate geometry; the untwisted views must stay untouched.
            turned = load_body(path, expected, colors, turn=args.turn)
            print('Wrote', render(body_id + '-turn', turned,
                                  [('Front %g' % args.turn, (0, 0, 180)),
                                   ('Left %g' % args.turn, (0, 0, 90)),
                                   ('Right %g' % args.turn, (0, 0, -90)),
                                   ('Above %g' % args.turn, (90, 0, 0))],
                                  args.output, columns=4))


main()
