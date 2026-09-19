"""Render labeled contact sheets directly from the exported game meshes.

blender --background --factory-startup --python-exit-code 1 \
    --python tools/render_unit_variants.py -- --chassis warhammer mad-cat
"""
import argparse
import json
from math import ceil, radians
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bpy
from mathutils import Matrix, Vector
from unit_model_geometry import content_digest

ROOT = Path(__file__).resolve().parents[1]
MODELS = ROOT / 'data/models/units'


def natural(value):
    return [int(s) if s.isdigit() else s.lower() for s in re.split(r'(\d+)', value)]


def material(rgb, cache):
    key = tuple(rgb)
    if key not in cache:
        result = bpy.data.materials.new('Unit color '+str(key))
        linear = tuple(c/12.92 if c <= .04045 else ((c+.055)/1.055)**2.4 for c in rgb)
        result.diffuse_color = (*linear, 1)
        result.use_nodes = True
        shader = result.node_tree.nodes.get('Principled BSDF')
        shader.inputs['Base Color'].default_value = (*linear, 1)
        shader.inputs['Roughness'].default_value = .8
        cache[key] = result
    return cache[key]


def import_model(path, expected, colors, turn=0, upper_body='CT'):
    """The generated G3DJ subset: indexed colors and translated rigid nodes, Z / 54.

    A non-zero turn shows the upper body turned that many degrees to its right, as the game shows a torso twist.
    """
    raw = path.read_bytes()
    if content_digest(path) != expected['sha256']:
        raise ValueError('Stale manifest for '+str(path))
    data = json.loads(raw)
    parts = {}
    for mesh in data['meshes']:
        if mesh['attributes'] != ['POSITION', 'NORMAL', 'COLOR']:
            raise ValueError('Unsupported review vertex format')
        for part in mesh['parts']:
            parts[part['id']] = (mesh['vertices'], part['indices'])
    vertices, faces, face_colors = [], [], []

    def visit(node, parent, pivot=None):
        if 'rotation' in node or 'scale' in node:
            raise ValueError('Review importer only supports the generated translated nodes')
        offset = parent + Vector(node.get('translation', (0, 0, 0)))
        if node['id'] == upper_body:
            pivot = offset
        for part in node.get('parts', []):
            source, indices = parts[part['meshpartid']]
            for j in range(0, len(indices), 3):
                start = len(vertices)
                for index in indices[j:j+3]:
                    v = source[index*10:index*10+10]
                    p = Vector(v[:3])+offset
                    if pivot is not None and turn:
                        p = Matrix.Rotation(radians(-turn), 3, 'Z') @ (p-pivot)+pivot
                    vertices.append((p.x, p.y, p.z*54))
                faces.append((start, start+1, start+2))
                face_colors.append(tuple(source[indices[j]*10+6:indices[j]*10+9]))
        for child in node.get('children', []):
            visit(child, offset, pivot)

    for node in data['nodes']:
        visit(node, Vector((0, 0, 0)))
    if len(faces) != expected['triangles']:
        raise ValueError('Triangle mismatch for '+str(path))
    mesh = bpy.data.meshes.new(data['id'])
    mesh.from_pydata(vertices, [], faces)
    slots = {}
    for color in dict.fromkeys(face_colors):
        slots[color] = len(mesh.materials)
        mesh.materials.append(material(color, colors))
    for polygon, color in zip(mesh.polygons, face_colors):
        polygon.material_index = slots[color]
        polygon.use_smooth = False
    return mesh


def label(scene, body, position, rotation, size, ink, align='CENTER'):
    curve = bpy.data.curves.new(body, 'FONT')
    curve.body = body
    curve.align_x = align
    curve.size = size
    curve.materials.append(ink)
    obj = bpy.data.objects.new(body, curve)
    obj.location = position
    obj.rotation_euler = rotation
    scene.collection.objects.link(obj)


def render(recipe, units, manifest, out, columns, caption='variants', formations=False, turn=0):
    rows = ceil(len(units)/columns)
    cell_width, cell_height, header = (110, 100, 27) if formations else (70, 83, 27)
    width, height = columns*cell_width, rows*cell_height+header
    scene = bpy.data.scenes.new(recipe['name']+' '+caption)
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 20
    scene.render.resolution_x = columns*(600 if formations else 480)
    scene.render.resolution_y = round(scene.render.resolution_x*height/width)
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.view_settings.view_transform = 'Standard'
    scene.world = bpy.data.worlds.new(recipe['id']+' world')
    scene.world.use_nodes = True
    scene.world.node_tree.nodes['Background'].inputs[0].default_value = (.22, .28, .35, 1)
    scene.world.node_tree.nodes['Background'].inputs[1].default_value = .85
    camera = bpy.data.objects.new('Contact sheet camera', bpy.data.cameras.new('Contact sheet camera'))
    camera.data.type = 'ORTHO'
    camera.data.sensor_fit = 'HORIZONTAL'
    camera.data.ortho_scale = width
    camera.data.clip_end = 3000
    direction = Vector((0, 350, 270 if formations else 139)).normalized()
    rotation = (-direction).to_track_quat('-Z', 'Y')
    right = rotation @ Vector((1, 0, 0))
    up = rotation @ Vector((0, 1, 0))
    camera.location = direction*1000
    camera.rotation_euler = rotation.to_euler()
    scene.collection.objects.link(camera)
    scene.camera = camera
    light = bpy.data.lights.new('Consistent key', 'SUN')
    light.energy = 2.3
    light.angle = .18
    obj = bpy.data.objects.new('Consistent key', light)
    obj.rotation_euler = Vector((-.4, -.6, -1)).to_track_quat('-Z', 'Y').to_euler()
    scene.collection.objects.link(obj)
    ink = bpy.data.materials.new('Sheet labels')
    ink.use_nodes = True
    nodes = ink.node_tree.nodes
    nodes.clear()
    emission = nodes.new('ShaderNodeEmission')
    emission.inputs['Color'].default_value = (.92, .96, 1, 1)
    output = nodes.new('ShaderNodeOutputMaterial')
    ink.node_tree.links.new(emission.outputs[0], output.inputs['Surface'])
    entries, colors = [], {}
    for i, unit in enumerate(units):
        variant = manifest['variants'][unit['name']]
        expected = manifest['models'][variant['asset']]
        mesh = import_model(MODELS / variant['asset'], expected, colors, turn)
        obj = bpy.data.objects.new(unit['name'], mesh)
        x = (i % columns-(columns-1)/2)*cell_width
        y = height/2-header-(i//columns+.5)*cell_height
        center = right*x+up*y
        obj.location = center-Vector((0, 0, 10 if formations else 27))
        obj.rotation_euler.z = unit.get('angle', -.4)
        obj['game_asset'] = variant['asset']
        obj['triangles'] = expected['triangles']
        scene.collection.objects.link(obj)
        label(scene, unit['model'], center-up*(38 if formations else 32), rotation.to_euler(), 3.3, ink)
        label(scene, str(expected['triangles'])+' triangles', center-up*(48 if formations else 37),
              rotation.to_euler(), 2.6, ink)
        entries.append({'name': unit['name'], 'variant': unit['model'], 'asset': variant['asset'],
                        'triangles': expected['triangles'], 'sha256': expected['sha256'],
                        'equipment': [{'name': m['name'], 'location': m['location'], 'rear': m['rear']}
                                      for m in unit['equipment'] if m['family'] != 'internal']})
    counts = [e['triangles'] for e in entries]
    label(scene, recipe['name'].upper(), up*(height/2-10), rotation.to_euler(), 6, ink)
    label(scene, f'{len(units)} {caption}  |  {min(counts)}-{max(counts)} triangles  |  actual exported game meshes',
          up*(height/2-17), rotation.to_euler(), 3, ink)
    bpy.context.window.scene = scene
    scene.render.filepath = str(out / (recipe['id']+'.png'))
    bpy.ops.render.render(write_still=True, scene=scene.name)
    scene.render.image_settings.file_format = 'JPEG'
    scene.render.image_settings.quality = 93
    bpy.data.images['Render Result'].save_render(str(out / (recipe['id']+'.jpg')), scene=scene)
    scene.render.image_settings.file_format = 'PNG'
    return {'chassis': recipe['name'], 'image': recipe['id']+'.png', 'variants': entries}


def render_infantry(manifest, out):
    groups = [('motorized', 'Motorized'), ('tracked', 'Tracked APC'), ('wheeled', 'Wheeled APC'),
              ('hover', 'Hover APC'), ('jump', 'Jump infantry (rear)'), ('', 'Foot infantry')]
    sheets = []
    for sheet, counts in (('infantry', (6,)), ('infantry-counts', (3, 4, 5, 6))):
        units, assets = [], {}
        for style, title in (groups if len(counts) == 1 else groups[:4]):
            for count in counts:
                name = title+' / '+str(count)
                vehicles = (1 if count <= 4 else 2) if style and style != 'jump' else 0
                detail = f'{vehicles} vehicle{"s" if vehicles != 1 else ""} + {count-vehicles} troops' if vehicles else f'{count} troops'
                units.append({'name': name, 'model': title+'\n'+detail, 'equipment': [],
                              'angle': 2.7 if style == 'jump' else -.4})
                assets[name] = {'asset': 'infantry/'+(style+'/' if style else '')+'squad-'+str(count)+'.g3dj'}
        sheets.append(render({'id': sheet, 'name': 'Infantry' if len(counts) == 1 else 'Infantry slot counts'},
                             units, {'models': manifest['models'], 'variants': assets}, out,
                             3 if len(counts) == 1 else 4, 'formations', formations=True))
    return sheets


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--chassis', nargs='+', default=['warhammer', 'mad-cat'])
    parser.add_argument('--columns', type=int, default=5)
    parser.add_argument('--bare', action='store_true', help='Show the shared chassis without the equipment pass')
    parser.add_argument('--infantry', action='store_true', help='Review movement types and 3-6 slot transport formations')
    parser.add_argument('--turn', type=float, default=0,
                        help='Show the upper body turned this many degrees to its right (60 is one hexside)')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    if not bpy.app.background or not 1 <= args.columns <= 8:
        raise ValueError('Use background Blender and 1-8 columns')
    recipes = json.loads((ROOT / 'tools/unit-models/chassis.json').read_text(encoding='utf-8'))['chassis']
    known = {r['id']: r for r in recipes}
    unknown = set(args.chassis)-known.keys()
    if unknown:
        raise ValueError('Unknown chassis: '+', '.join(sorted(unknown)))
    catalog = json.loads((ROOT / '.work/mek-models/catalog.json').read_text(encoding='utf-8'))
    manifest = json.loads((MODELS / 'manifest.json').read_text(encoding='utf-8'))
    args.output = (args.output or ROOT / '.work/mek-models' /
                   ('infantry' if args.infantry else 'bare-chassis' if args.bare else 'variants')).resolve()
    args.output.mkdir(parents=True, exist_ok=True)
    sheets = []
    if args.infantry:
        sheets = render_infantry(manifest, args.output)
    elif args.bare:
        units = [{'name': known[k]['name'], 'model': known[k]['name'], 'equipment': []} for k in args.chassis]
        bodies = {'models': manifest['models'], 'variants': {
            known[k]['name']: {'asset': 'meks/'+k+'/body.g3dj'} for k in args.chassis}}
        sheets.append(render({'id': 'bare-chassis', 'name': 'Bare chassis'}, units, bodies,
                             args.output, min(args.columns, len(units)), 'unarmed chassis', turn=args.turn))
    else:
        for key in args.chassis:
            recipe = known[key]
            units = [u for u in catalog['units'] if u['chassis'] == recipe['name']]
            # The reference configuration leads each sheet, then use natural variant order.
            units.sort(key=lambda u: (u['model'] != recipe['referenceVariant'], natural(u['model'])))
            if not units or any(u['name'] not in manifest['variants'] for u in units):
                raise ValueError('Incomplete generated coverage for '+recipe['name'])
            sheets.append(render(recipe, units, manifest, args.output, args.columns, turn=args.turn))
    (args.output / 'gallery.json').write_text(json.dumps(sheets, indent=2)+'\n', encoding='utf-8')
    filename = 'infantry.blend' if args.infantry else 'bare-chassis.blend' if args.bare else 'variants.blend'
    bpy.ops.wm.save_as_mainfile(filepath=str(args.output / filename), check_existing=False)
    print(json.dumps({'sheets': len(sheets), 'variants': sum(len(s['variants']) for s in sheets),
                      'output': str(args.output)}))


if __name__ == '__main__':
    main()
