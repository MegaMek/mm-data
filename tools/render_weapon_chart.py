"""Render every standard weapon look side by side, at one scale, for review.

Run with Blender: blender --background --factory-startup --python tools/render_weapon_chart.py -- [--output DIR]
Each weapon is drawn by the same code that dresses the unit models, mounted on a plain block the size of
a forearm, so shapes and relative sizes can be judged before they are applied to any Mek.
"""
import argparse
from collections import defaultdict
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bpy
from mathutils import Vector
from unit_model_geometry import Geometry, PALETTE
import unit_weapon_shapes as weapons

ROOT = Path(__file__).resolve().parents[1]
# (catalog family, display name, rack size, optional settings). One example per look the rules tell apart.
EXAMPLES = [
    ('laser', 'Small Laser', 0), ('laser', 'Medium Laser', 0), ('laser', 'ER Large Laser', 0),
    ('laser', 'Medium Pulse Laser', 0), ('laser', 'Large Pulse Laser', 0), ('laser', 'Heavy Large Laser', 0),
    ('laser', 'Binary Laser (Blazer) Cannon', 0), ('ppc', 'Light PPC', 0), ('ppc', 'PPC', 0),
    ('ppc', 'Heavy PPC', 0), ('ppc', 'Snub-Nose PPC', 0), ('energy', 'Plasma Rifle', 1),
    ('ballistic', 'AC/2', 2), ('ballistic', 'AC/5', 5), ('ballistic', 'AC/10', 10), ('ballistic', 'AC/20', 20),
    ('ballistic', 'Ultra AC/5', 5), ('ballistic', 'LB 10-X AC', 10), ('ballistic', 'Rotary AC/2', 2),
    ('ballistic', 'Rotary AC/5', 5),
    ('ballistic', 'Light Gauss Rifle', 0), ('ballistic', 'Gauss Rifle', 0), ('ballistic', 'Heavy Gauss Rifle', 0),
    ('ballistic', 'HAG/20', 20), ('ballistic', 'HAG/30', 30), ('ballistic', 'HAG/40', 40),
    ('ballistic', 'AP Gauss Rifle', 0),
    ('machine-gun', 'Machine Gun', 2), ('flamer', 'Flamer', 0), ('sensor', 'TAG', 0),
    ('ballistic', 'Anti-Missile System', 2), ('laser', 'Laser AMS', 0), ('ballistic', 'M-Pod', 15),
    ('jump-jet', 'Jump Jet', 0), ('searchlight', 'Searchlight (Mounted)', 0),
    ('missile', 'LRM 5', 5), ('missile', 'LRM 10', 10), ('missile', 'LRM 15', 15), ('missile', 'LRM 20', 20),
    ('missile', 'SRM 2', 2), ('missile', 'SRM 4', 4), ('missile', 'SRM 6', 6), ('missile', 'MRM 10', 10),
    ('missile', 'MRM 20', 20), ('missile', 'Rocket Launcher 15', 15), ('missile', 'ATM 3', 3), ('missile', 'ATM 6', 6),
    ('missile', 'ATM 9', 9), ('missile', 'ATM 12', 12), ('missile', 'MML 5', 5), ('missile', 'MML 7', 7),
    ('missile', 'Thunderbolt 10', 1), ('missile', 'Narc', 1), ('missile', 'Arrow IV', 20),
    ('hatchet', 'Hatchet', 0), ('unmapped-melee', 'Sword', 0), ('unmapped-melee', 'Mace', 0),
    ('unmapped-melee', 'Lance', 0), ('unmapped-melee', 'Chainsaw', 0),
    ('missile', 'LRM 20', 20, {'orientation': 'horizontal'}), ('missile', 'LRM 20', 20, {'orientation': 'vertical'}),
    ('missile', 'LRM 15', 15, {'orientation': 'horizontal'}), ('missile', 'LRM 15', 15, {'orientation': 'vertical'}),
    ('missile', 'SRM 6', 6, {'orientation': 'horizontal'}), ('missile', 'SRM 6', 6, {'orientation': 'vertical'}),
    ('missile', 'MML 7', 7, {'orientation': 'horizontal'}), ('missile', 'MML 7', 7, {'orientation': 'vertical'}),
]
for _weapon in (('laser', 'Medium Laser', 0), ('ballistic', 'AC/2', 2), ('ballistic', 'AC/5', 5),
                ('ballistic', 'AC/10', 10), ('ballistic', 'AC/20', 20), ('ppc', 'PPC', 0)):
    EXAMPLES += [(*_weapon, {'protrusion': length}) for length in ('recessed', 'short', 'medium', 'long')]
COLUMNS = 10
SPACING_X, SPACING_Z = 26, 34
# The mounting block costs twelve triangles; the rest of each model is the weapon.
BLOCK_TRIANGLES = 12


def build(family, name, rack, settings=None):
    mount = {'family': family, 'name': name, 'rackSize': rack, 'location': 'RA', 'rear': False}
    rule = weapons.rule_for(mount)
    if rule is None:
        raise ValueError('No standard look for '+name)
    rule.update(settings or {})
    geometry = Geometry()
    # A forearm-sized block shows where the weapon leaves the armor.
    # Slightly off the common launcher widths, so no launcher side lies exactly in the block's side.
    geometry.box((0, -4.2, 0), (8.3, 8, 9.3), 'RA', 'paint')
    weapons.draw(geometry, mount, rule, (0, 0, 0), 1, {'orientation': weapons.orientation_for(mount, rule)})
    return geometry, rule


def make_materials():
    materials = {}
    for role, rgb in PALETTE.items():
        material = bpy.data.materials.new('MM weapon '+role)
        linear = tuple(c/12.92 if c <= .04045 else ((c+.055)/1.055)**2.4 for c in rgb)
        material.diffuse_color = (*linear, 1)
        material.use_nodes = True
        material.node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value = (*linear, 1)
        material.node_tree.nodes.get('Principled BSDF').inputs['Roughness'].default_value = .8
        materials[role] = material
    ink = bpy.data.materials.new('Chart labels')
    ink.use_nodes = True
    ink.node_tree.nodes.clear()
    emission = ink.node_tree.nodes.new('ShaderNodeEmission')
    emission.inputs['Color'].default_value = (.9, .94, .98, 1)
    ink.node_tree.links.new(emission.outputs[0], ink.node_tree.nodes.new('ShaderNodeOutputMaterial').inputs['Surface'])
    return materials, ink


def render(out):
    scene = bpy.data.scenes.new('MegaMek weapon chart')
    materials, ink = make_materials()
    rows = -(-len(EXAMPLES)//COLUMNS)
    width, height = COLUMNS*SPACING_X, rows*SPACING_Z
    center = Vector((0, 0, 0))
    camera = bpy.data.objects.new('Chart camera', bpy.data.cameras.new('Chart camera'))
    camera.data.type = 'ORTHO'
    # A three-quarter view, so both a barrel's length and a launcher's face can be judged.
    camera.location = center+Vector((-260, 230, 110))
    camera.rotation_euler = (center-camera.location).to_track_quat('-Z', 'Y').to_euler()
    # The grid is laid out in the camera's own plane, so rows and columns stay square in the picture.
    basis = camera.rotation_euler.to_matrix()
    right, up = basis @ Vector((1, 0, 0)), basis @ Vector((0, 1, 0))
    scene.collection.objects.link(camera)
    scene.camera = camera
    summary = []
    for index, example in enumerate(EXAMPLES):
        family, name, rack = example[:3]
        geometry, rule = build(*example)
        if len(example) > 3:
            name += ' - '+' '.join(example[3].values())
        origin = (right*((index % COLUMNS-(COLUMNS-1)/2)*SPACING_X)
                  - up*((index//COLUMNS-(rows-1)/2)*SPACING_Z-5))
        groups = defaultdict(list)
        for tri, _, role in geometry.faces:
            groups[role].append(tri)
        for role, triangles in groups.items():
            vertices = [Vector(p) for tri in triangles for p in tri]
            mesh = bpy.data.meshes.new(name+' '+role)
            mesh.from_pydata(vertices, [], [tuple(range(j, j+3)) for j in range(0, len(vertices), 3)])
            mesh.materials.append(materials[role])
            obj = bpy.data.objects.new(mesh.name, mesh)
            obj.location = origin
            scene.collection.objects.link(obj)
        text = bpy.data.curves.new(name+' label', 'FONT')
        text.body = name+'\n'+str(len(geometry.faces)-BLOCK_TRIANGLES)+' triangles'
        text.align_x = 'CENTER'
        text.size = 2.3
        text.materials.append(ink)
        label = bpy.data.objects.new(name+' label', text)
        label.location = origin-up*13
        label.rotation_euler = camera.rotation_euler
        scene.collection.objects.link(label)
        summary.append((name, rule['id'], len(geometry.faces)-BLOCK_TRIANGLES))
    # The orthographic scale is the horizontal extent; the picture is 3000 by 2900.
    camera.data.ortho_scale = max(width*1.08, height*1.1*3000/2900)
    scene.world = bpy.data.worlds.new('Chart world')
    scene.world.use_nodes = True
    scene.world.node_tree.nodes['Background'].inputs[0].default_value = (.26, .32, .39, 1)
    scene.world.node_tree.nodes['Background'].inputs[1].default_value = .9
    light = bpy.data.lights.new('Chart key', 'AREA')
    light.energy = 900000
    light.shape = 'DISK'
    light.size = 260
    key = bpy.data.objects.new('Chart key', light)
    key.location = center+Vector((-120, 300, 320))
    key.rotation_euler = (center-key.location).to_track_quat('-Z', 'Y').to_euler()
    scene.collection.objects.link(key)
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 24
    scene.render.resolution_x = 3000
    scene.render.resolution_y = 2900
    scene.render.image_settings.file_format = 'PNG'
    scene.view_settings.view_transform = 'Standard'
    bpy.context.window.scene = scene
    out.mkdir(parents=True, exist_ok=True)
    scene.render.filepath = str(out / 'weapon-chart.png')
    bpy.ops.render.render(write_still=True, scene=scene.name)
    for name, rule_id, triangles in summary:
        print(f'CHART {name:32} {rule_id:22} {triangles:4} triangles')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / '.work/mek-models/weapons')
    render(parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []).output.resolve())
