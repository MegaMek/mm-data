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
# A warm ground against a cool model, on every sheet. A blue-grey ground sat in the same hue family as the
# joint and shin armour, so those parts separated from it only by brightness and read as background.
GROUND = (.21, .13, .10, 1)


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


def spare_vents(body_id):
    """The vent spots a bare body does not show: the spares the game picks from once weapons are placed."""
    descriptor = BODIES.parent / 'meks' / (body_id + '.json')
    if not descriptor.exists():
        return set()
    vents = json.loads(descriptor.read_text(encoding='utf-8')).get('vents', [])
    return {vent['node'] for vent in vents if not vent['authored']}


def load_body(path, expected, colors, turn=0, upper_body='CT', hidden=()):
    """Schema-2 bodies keep vertices local to their node and stack rigid translations.

    Unlike the legacy bake these carry a paint UV and unnormalized Z, so the stride is read
    from the attribute list rather than assumed. Nodes named in hidden are left out, with their children.
    """
    data = json.loads(path.read_text(encoding='utf-8'))
    skipped = [0]
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
        if node['id'] in hidden:
            skipped[0] += sum(len(parts[part['meshpartid']][1])//3 for part in node.get('parts', []))
            return
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
    if expected and len(faces) + skipped[0] != expected['triangles']:
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
    scene.world.node_tree.nodes['Background'].inputs[0].default_value = GROUND

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


def lineup(entries, out, name='lineup'):
    """One shared camera over several grounded bodies, so relative proportion reads directly.

    Unlike the six-view sheet, nothing is centred on its own bounds: every body stands on the same
    ground line at the same scale, because the comparison is the point.
    """
    scene = bpy.data.scenes.new(name + ' lineup')
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 24
    scene.render.image_settings.file_format = 'PNG'
    scene.view_settings.view_transform = 'Standard'
    scene.world = bpy.data.worlds.new(name + ' world')
    scene.world.use_nodes = True
    scene.world.node_tree.nodes['Background'].inputs[0].default_value = GROUND

    ink = bpy.data.materials.new('Lineup labels')
    ink.use_nodes = True
    ink.node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value = (1, 1, 1, 1)

    posed = [posed_bounds(mesh, (0, 0, 180)) for _, _, mesh in entries]
    tallest = max(high.z for _, high in posed)
    gap = tallest * .12
    widths = [high.x - low.x for low, high in posed]
    span = sum(widths) + gap * (len(entries) + 1)
    front = -tallest * 3

    cursor = -span / 2 + gap
    for (body_id, caption, mesh), (low, high), width in zip(entries, posed, widths):
        obj = bpy.data.objects.new(body_id + ' lineup', mesh)
        obj.rotation_euler = (0, 0, radians(180))
        # Feet on the shared ground line, not centred: height difference is what is being read.
        obj.location = (cursor - low.x, 0, -low.z)
        scene.collection.objects.link(obj)
        middle = cursor + width / 2
        label(scene, caption, (middle, front, -tallest * .09), tallest * .046, ink)
        label(scene, '%.1f' % (high.z - low.z), (middle, front, -tallest * .155), tallest * .038, ink)
        cursor += width + gap

    # A ground line makes the shared baseline explicit.
    ground = bpy.data.meshes.new('ground')
    ground.from_pydata([(-span / 2, front, 0), (span / 2, front, 0),
                        (span / 2, front, -tallest * .006), (-span / 2, front, -tallest * .006)],
                       [], [(0, 1, 2, 3)])
    ground.materials.append(ink)
    scene.collection.objects.link(bpy.data.objects.new('ground', ground))

    camera_data = bpy.data.cameras.new(name + ' camera')
    camera_data.type = 'ORTHO'
    camera_data.ortho_scale = span
    camera = bpy.data.objects.new(name + ' camera', camera_data)
    camera.location = (0, -tallest * 6, tallest * .42)
    camera.rotation_euler = (radians(90), 0, 0)
    scene.collection.objects.link(camera)
    scene.camera = camera

    for energy, angles in ((3.2, (58, 0, -35)), (1.1, (72, 0, 130)), (.9, (0, 0, 0))):
        lamp = bpy.data.lights.new(name + str(energy), 'SUN')
        lamp.energy = energy
        lamp_object = bpy.data.objects.new(name + str(energy), lamp)
        lamp_object.rotation_euler = tuple(radians(a) for a in angles)
        scene.collection.objects.link(lamp_object)

    scene.render.resolution_x = 460 * len(entries)
    scene.render.resolution_y = round(scene.render.resolution_x * (tallest * 1.28) / span)
    scene.render.filepath = str(out / (name + '-lineup.png'))
    bpy.ops.render.render(write_still=True, scene=scene.name)
    return Path(scene.render.filepath)


def gallery(entries, out, name, title, columns=6, rotation=(0, 0, 215)):
    """Many models in a grid, one view each, all at one scale.

    For comparing a family of shapes: each model is centred in its own cell, but nothing is resized to fill it,
    so a larger weapon reads as larger.
    """
    scene = bpy.data.scenes.new(name + ' gallery')
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 24
    scene.render.image_settings.file_format = 'PNG'
    scene.view_settings.view_transform = 'Standard'
    scene.world = bpy.data.worlds.new(name + ' world')
    scene.world.use_nodes = True
    scene.world.node_tree.nodes['Background'].inputs[0].default_value = GROUND
    ink = bpy.data.materials.new('Gallery labels')
    ink.use_nodes = True
    ink.node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value = (1, 1, 1, 1)

    posed = [posed_bounds(mesh, rotation) for _, _, mesh in entries]
    reach = max(max(high.x - low.x, high.z - low.z) for low, high in posed)
    columns = min(columns, len(entries))
    rows = ceil(len(entries) / columns)
    cell, pitch = reach * 1.3, reach * 1.6
    span, tall = cell * columns, pitch * rows
    front = -reach * 3
    for index, ((model_id, caption, mesh), (low, high)) in enumerate(zip(entries, posed)):
        middle = (low + high) / 2
        cell_x = (index % columns) * cell - span / 2 + cell / 2
        cell_z = -(index // columns) * pitch
        obj = bpy.data.objects.new(model_id + ' gallery', mesh)
        obj.rotation_euler = tuple(radians(angle) for angle in rotation)
        obj.location = (cell_x - middle.x, 0, cell_z - middle.z + pitch * .06)
        scene.collection.objects.link(obj)
        for line, text in enumerate(caption.split('\n')):
            label(scene, text, (cell_x, front, cell_z - pitch * (.36 + .075 * line)), reach * .062, ink)
    label(scene, title, (span / 2 - cell * .06, front, pitch * .42), reach * .085, ink, 'RIGHT')

    camera_data = bpy.data.cameras.new(name + ' camera')
    camera_data.type = 'ORTHO'
    camera_data.ortho_scale = span
    camera = bpy.data.objects.new(name + ' camera', camera_data)
    camera.location = (0, -reach * 6, -(rows - 1) * pitch / 2)
    camera.rotation_euler = (radians(90), 0, 0)
    scene.collection.objects.link(camera)
    scene.camera = camera
    for energy, angles in ((3.2, (58, 0, -35)), (1.1, (72, 0, 130)), (.9, (0, 0, 0))):
        lamp = bpy.data.lights.new(name + str(energy), 'SUN')
        lamp.energy = energy
        lamp_object = bpy.data.objects.new(name + str(energy), lamp)
        lamp_object.rotation_euler = tuple(radians(a) for a in angles)
        scene.collection.objects.link(lamp_object)

    scene.render.resolution_x = 360 * columns
    scene.render.resolution_y = round(scene.render.resolution_x * tall / span)
    scene.render.filepath = str(out / (name + '-gallery.png'))
    bpy.ops.render.render(write_still=True, scene=scene.name)
    return Path(scene.render.filepath)


def held_guns(manifest):
    """Every distinct held gun, captioned with the weapons that share it, grouped by family."""
    catalog = json.loads((BODIES.parent / 'equipment.json').read_text(encoding='utf-8'))
    catalog = catalog.get('equipment', catalog)
    names = {}
    units = ROOT / '.work/mek-models/catalog.json'
    if units.exists():
        for unit in json.loads(units.read_text(encoding='utf-8'))['units']:
            for mount in unit['equipment']:
                names.setdefault(mount['internalName'], mount['name'])
    shapes = {}
    for key, entry in catalog.items():
        asset = isinstance(entry, dict) and entry.get('profiles', {}).get('held')
        if asset:
            shapes.setdefault(asset, (entry['family'], []))[1].append(names.get(key, key))
    order = {'ppc': 0, 'ballistic': 1, 'laser': 2}
    result = []
    for asset, (family, weapons) in sorted(shapes.items(), key=lambda item: (order.get(item[1][0], 9),
                                                                              -len(set(item[1][1])))):
        # Head the group with its plainest name: no brackets or prototypes, then the shortest, then alphabetical.
        weapons = sorted(set(weapons), key=lambda weapon: ('(' in weapon or 'Prototype' in weapon
                                                          or 'Primitive' in weapon, len(weapon), weapon))
        caption = weapons[0] + ('\n+%d more' % (len(weapons) - 1) if len(weapons) > 1 else '')
        key = asset.removeprefix('units/modular/').removesuffix('.json')
        result.append((key.split('/')[-1], caption, BODIES.parent / (key + '.g3dj'), manifest.get(key)))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--body', action='append', default=[],
                        help='body id under data/models/units/modular/bodies; repeatable')
    parser.add_argument('--turn', type=float, default=0,
                        help='degrees of upper-body twist, for the waist clearance check')
    parser.add_argument('--output', type=Path, default=ROOT / '.work/body-review')
    parser.add_argument('--lineup', metavar='NAME',
                        help='render the named bodies side by side on one ground line instead of sheets')
    parser.add_argument('--tons', action='append', default=[],
                        help='tonnage shown beside each --body in a lineup; repeat in the same order')
    parser.add_argument('--equipment', action='append', default=[],
                        help='equipment canonical name from equipment.json, rendered on its own; repeatable')
    parser.add_argument('--profile', default='',
                        help='equipment profile to render instead of the standard shape, such as held')
    parser.add_argument('--held-all', metavar='NAME',
                        help='render every distinct held gun on one sheet, captioned with its weapons')
    parser.add_argument('--angle', type=float, default=215,
                        help='turn applied to every model on a --held-all sheet; 215 is three-quarter, 120 side-on')
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
    manifest = json.loads(MANIFEST.read_text(encoding='utf-8'))['assets'] if MANIFEST.exists() else {}
    if args.held_all:
        args.output.mkdir(parents=True, exist_ok=True)
        colors = {}
        entries = [(model_id, caption, load_body(path, expected, colors))
                   for model_id, caption, path, expected in held_guns(manifest)]
        print('Wrote', gallery(entries, args.output, args.held_all,
                               'Held weapons  -  %d shapes' % len(entries), rotation=(0, 0, args.angle)))
        return
    if not args.body and not args.equipment:
        parser.error('name at least one --body or --equipment')
    # A sheet is headed with the chassis as players know it, not the body's file id.
    titles = {entry['id']: entry['name'] for entry in
              json.loads(RECIPES.read_text(encoding='utf-8'))['chassis']} if RECIPES.exists() else {}
    args.output.mkdir(parents=True, exist_ok=True)
    colors = {}
    entries = []
    sources = [(body_id, BODIES / (body_id + '.g3dj'), manifest.get('bodies/' + body_id)) for body_id in args.body]
    if args.equipment:
        catalog = json.loads((BODIES.parent / 'equipment.json').read_text(encoding='utf-8'))
        catalog = catalog.get('equipment', catalog)
        for name in args.equipment:
            entry = catalog.get(name)
            if entry is None:
                raise SystemExit('No such equipment: ' + name)
            asset = entry.get('profiles', {}).get(args.profile) if args.profile else None
            if args.profile and asset is None:
                raise SystemExit('%s has no %s profile' % (name, args.profile))
            key = (asset or entry['model']).removeprefix('units/modular/').removesuffix('.json')
            title = '%s (%s)' % (name, args.profile) if args.profile else name
            titles[title] = title
            sources.append((title, BODIES.parent / (key + '.g3dj'), manifest.get(key)))
    for body_id, path, expected in sources:
        if not path.exists():
            raise SystemExit('No such model: ' + str(path))
        hidden = spare_vents(body_id)
        mesh = load_body(path, expected, colors, hidden=hidden)
        entries.append((body_id, titles.get(body_id, body_id), mesh))
        if args.lineup:
            continue
        print('Wrote', render(body_id, mesh, list(VIEWS), args.output, title=titles.get(body_id, body_id)))
        if args.turn and not args.lineup:
            # The twisted copy is separate geometry; the untwisted views must stay untouched.
            turned = load_body(path, expected, colors, turn=args.turn, hidden=hidden)
            print('Wrote', render(body_id + '-turn', turned,
                                  [('Front %g' % args.turn, (0, 0, 180)),
                                   ('Left %g' % args.turn, (0, 0, 90)),
                                   ('Right %g' % args.turn, (0, 0, -90)),
                                   ('Above %g' % args.turn, (90, 0, 0))],
                                  args.output, columns=4))

    if args.lineup:
        labelled = [(body_id, '%s  %st' % (title, tons) if tons else title, mesh)
                    for (body_id, title, mesh), tons
                    in zip(entries, list(args.tons) + [None] * len(entries))]
        print('Wrote', lineup(labelled, args.output, args.lineup))


main()
