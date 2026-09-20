"""Catalog the deployed generic meshes reachable from mekset and modular descriptors.

Render with Blender --background --factory-startup --python-exit-code 1 --python
tools/render_fallback_catalog.py -- ; then compose with ordinary Python and Pillow:
python tools/render_fallback_catalog.py --compose
No assets are generated, fitted, or changed. These are untextured rest-pose art previews.
"""
import argparse
import json
from math import ceil
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
MODELS = ROOT / 'data/models'
MODULAR = MODELS / 'units/modular'
SECTIONS = ('Mek fallbacks', 'Vehicle, aerospace and other fallbacks', 'Infantry and Battle Armor components')
WEIGHTS = ('light', 'medium', 'heavy', 'assault', 'superheavy')
TOPOLOGIES = ('biped', 'quad', 'tripod', 'airmek')


def inventory():
    """Follow asset references, including conversion forms, without reimplementing unit selection."""
    manifest = json.loads((MODULAR / 'manifest.json').read_text())['assets']
    roots = re.findall(r'"(units/modular/[^"\n]+\.json)"',
                       (ROOT / 'data/images/units/mekset.txt').read_text(encoding='utf-8'))
    visited, selected = set(), set()

    def visit(value):
        if isinstance(value, dict):
            for key, child in value.items():
                if key != 'equipment':
                    visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)
        elif isinstance(value, str) and value.startswith('units/modular/') and value.endswith('.json'):
            if '{weightClass}' in value:
                matches = sorted(MODELS.glob(value.replace('{weightClass}', '*')))
                if not matches:
                    raise ValueError('No deployed assets for '+value)
                for path in matches:
                    visit(path.relative_to(MODELS).as_posix())
                return
            if value in visited:
                return
            visited.add(value)
            descriptor = json.loads((MODELS / value).read_text())
            if 'mesh' in descriptor:
                key = value.removeprefix('units/modular/').removesuffix('.json')
                if key.startswith(('bodies/fallback-', 'bodies/family-', 'troops/', 'transports/')):
                    selected.add(key)
            visit(descriptor)

    for root in roots:
        visit(root)

    def order(key):
        name = key.split('/')[-1]
        if name.startswith('fallback-'):
            _, topology, weight = name.split('-')
            return (0, TOPOLOGIES.index(topology), WEIGHTS.index(weight))
        return (1 if name.startswith('family-') else 2, key, '')

    entries = []
    for key in sorted(selected, key=order):
        stats = manifest[key]
        descriptor = MODULAR / (key+'.json')
        mesh = descriptor.with_name(json.loads(descriptor.read_text())['mesh'])
        title = key.split('/')[-1].removeprefix('fallback-').removeprefix('family-').replace('-', ' ').title()
        title = title.replace('Airmek', 'AirMek').replace('Vtol', 'VTOL').replace('Wige', 'WiGE')
        if key.startswith('transports/'):
            title += ' transport'
        if key.endswith('family-flight-fighter'):
            title = 'Fighter squadron member'
        entries.append({'key': key, 'title': title, 'section': order(key)[0],
                        'mesh': mesh.relative_to(ROOT).as_posix(), **stats,
                        'image': key.replace('/', '--')+'.png'})
    return entries


def render(output):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import bpy
    from mathutils import Vector
    from render_unit_variants import import_model

    entries = inventory()
    output.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    scene.render.engine = 'BLENDER_WORKBENCH'
    scene.render.resolution_x = 800
    scene.render.resolution_y = 460
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGBA'
    scene.render.film_transparent = True
    scene.view_settings.view_transform = 'Standard'
    shading = scene.display.shading
    shading.light = 'STUDIO'
    shading.color_type = 'MATERIAL'
    shading.show_shadows = True
    shading.show_cavity = True
    shading.cavity_type = 'BOTH'
    shading.curvature_ridge_factor = 1.2
    shading.curvature_valley_factor = 1.0
    shading.show_specular_highlight = True
    scene.display.render_aa = '32'
    camera = bpy.data.objects.new('Catalog camera', bpy.data.cameras.new('Catalog camera'))
    scene.collection.objects.link(camera)
    scene.camera = camera
    camera.data.type = 'ORTHO'
    camera.data.sensor_fit = 'HORIZONTAL'
    camera.data.clip_end = 10000
    direction = Vector((.85, 1.4, .95)).normalized()
    rotation = (-direction).to_track_quat('-Z', 'Y')
    camera.rotation_euler = rotation.to_euler()
    right, up = rotation @ Vector((1, 0, 0)), rotation @ Vector((0, 1, 0))
    colors = {}
    for entry in entries:
        mesh = import_model(ROOT / entry['mesh'], entry, colors, z_scale=1)
        obj = bpy.data.objects.new(entry['title'], mesh)
        scene.collection.objects.link(obj)
        points = [vertex.co for vertex in mesh.vertices]
        xs, ys = [p.dot(right) for p in points], [p.dot(up) for p in points]
        center = right*((min(xs)+max(xs))/2) + up*((min(ys)+max(ys))/2)
        camera.location = center + direction*1500
        camera.data.ortho_scale = max(max(xs)-min(xs), (max(ys)-min(ys))*800/460)*1.14
        scene.render.filepath = str(output / entry['image'])
        bpy.ops.render.render(write_still=True)
        bpy.data.objects.remove(obj, do_unlink=True)
        bpy.data.meshes.remove(mesh)
        print('CATALOG '+entry['key'], flush=True)
    (output / 'catalog.json').write_text(json.dumps({'entries': entries,
        'note': 'Deployed meshes reachable from mekset references and descriptor forms. Rest poses, '
                'vertex colors, no camouflage or runtime loadout. Each tile is independently scaled.'}, indent=2)+'\n')


def compose(output):
    from PIL import Image, ImageDraw, ImageFont
    entries = json.loads((output / 'catalog.json').read_text())['entries']
    font_root = Path('C:/Windows/Fonts')
    def font(size, bold=False):
        return ImageFont.truetype(str(font_root / ('segoeuib.ttf' if bold else 'segoeui.ttf')), size)
    bg, panel, ink, muted, accent = '#111b26', '#1c2a38', '#ecf2f7', '#9eafc0', '#72d4be'
    width, margin, gap, cell_w, cell_h = 3200, 64, 18, 600, 406
    groups = [[e for e in entries if e['section'] == i] for i in range(3)]
    height = 240 + sum(100 + ceil(len(g)/5)*(cell_h+gap) for g in groups) + 95
    sheet = Image.new('RGB', (width, height), bg)
    draw = ImageDraw.Draw(sheet)
    draw.text((margin, 42), 'FALLBACK MODEL CATALOG', font=font(64, True), fill=ink)
    draw.text((margin, 129), f'{len(entries)} deployed meshes  /  MegaMek  /  20 September 2026', font=font(30), fill=accent)
    draw.text((margin, 180), 'Bare assets in rest pose  •  Individual tile scales  •  Loadouts and formations are assembled in game', font=font(27), fill=muted)
    y = 240
    for index, group in enumerate(groups):
        start = y
        draw.line((margin, y, width-margin, y), fill='#35485a', width=2)
        draw.text((margin, y+22), SECTIONS[index], font=font(38, True), fill=ink)
        draw.text((width-margin-200, y+30), f'{len(group)} meshes', font=font(27), fill=accent)
        y += 100
        for j, entry in enumerate(group):
            x, top = margin+(j%5)*(cell_w+gap), y+(j//5)*(cell_h+gap)
            draw.rounded_rectangle((x, top, x+cell_w, top+cell_h), radius=12, fill=panel)
            with Image.open(output / entry['image']) as original:
                tile = original.convert('RGBA')
                tile.thumbnail((cell_w-24, 300), Image.Resampling.LANCZOS)
                sheet.paste(tile, (x+(cell_w-tile.width)//2, top+8), tile)
            draw.text((x+22, top+309), entry['title'], font=font(28, True), fill=ink)
            name = entry['key'].split('/')[-1]
            draw.text((x+22, top+351), f'{name}  /  {entry["triangles"]:,} tris', font=font(21), fill=muted)
        y += ceil(len(group)/5)*(cell_h+gap)
        sheet.crop((0, start, width, y)).save(output / f'fallback-catalog-{index+1}.png')
    draw.text((margin, y+20), 'Source: mm-data/data/models/units/modular  •  Infantry poses and transports shown individually; squadron shown as one member.',
              font=font(25), fill=muted)
    sheet.save(output / 'fallback-catalog.png')
    sheet.resize((1600, height//2), Image.Resampling.LANCZOS).save(output / 'fallback-catalog-preview.png')
    print(f'Catalog: {len(entries)} meshes, {width} x {height}: {output / "fallback-catalog.png"}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / '.work/fallback-catalog')
    parser.add_argument('--compose', action='store_true')
    argv = sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else sys.argv[1:]
    args = parser.parse_args(argv)
    (compose if args.compose else render)(args.output.resolve())
