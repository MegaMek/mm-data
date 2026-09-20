"""Legacy reference renderer for baked Mek variants and infantry formations; never deploy its output.

Run with Blender: blender --background --factory-startup --python tools/build_unit_models.py -- --preview
The Java catalog owns equipment/locations. This script owns art, never game rules.
"""
import argparse
from collections import defaultdict
from copy import deepcopy
import hashlib
import json
from math import pi
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from unit_model_geometry import Geometry, PALETTE, TRIANGLE_LIMIT, TRIANGLE_TARGET, add, content_digest
from unit_mek_chassis import build_chassis
from unit_infantry_shapes import person, infantry_vehicle
import unit_weapon_shapes as weapons
from unit_mount_layout import MountArea

ROOT = Path(__file__).resolve().parents[1]
SPRITES = ROOT / 'data/images/units'


def digest(path):
    return content_digest(path)


def slug(text):
    stem = re.sub('[^a-z0-9]+', '-', text.lower()).strip('-')
    return stem + '-' + hashlib.sha256(text.encode()).hexdigest()[:8]


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')


def point(pixel):
    return (pixel[0]-42, 36-pixel[1], pixel[2])


# Which optional arm parts each arm form keeps. A body function tags such parts "LA@elbow", "RA@forearm"...
ARM_PARTS = {'elbow': ('elbow',), 'wrist': ('forearm', 'wrist'), 'hand': ('forearm', 'hand')}


def arm_form(unit, arm):
    """How an arm ends, read from its actuators: with a hand, at the wrist, or at the elbow.

    A hand carries its weapon on the forearm. Without a hand the weapon attaches at the wrist, and without a
    lower arm it attaches at the elbow. Older catalogs do not list lower arms; those arms are taken as present.
    """
    if arm in unit.get('hands', []):
        return 'hand'
    return 'wrist' if arm in unit.get('lowerArms', ['LA', 'RA']) else 'elbow'


def fit_arms(base, unit):
    """The body with only the arm parts that suit this variant's actuators, folded into the arm itself."""
    fitted = Geometry()
    fitted.pivots = {group: pivot for group, pivot in base.pivots.items() if '@' not in group}
    fitted.parents = {group: parent for group, parent in base.parents.items() if '@' not in group}
    for triangle, group, material in base.faces:
        if '@' in group:
            arm, part = group.split('@')
            if part not in ARM_PARTS[arm_form(unit, arm)]:
                continue
            group = arm
        fitted.faces.append((triangle, group, material))
    return fitted


def assemble(base, recipe, unit, detail='full'):
    result = fit_arms(base, unit)
    mounts = [m for m in unit['equipment'] if m['family'] != 'internal']
    rules = {m['index']: weapons.rule_for(m, recipe) for m in mounts}
    unresolved = [m for m in mounts if rules[m['index']] is None or m['location'] not in recipe['sockets']]
    if unresolved:
        return None, [{'equipment': m['internalName'], 'location': m['location'], 'family': m['family']} for m in unresolved]
    counts = defaultdict(int)
    placements = []
    stacked_launchers = {}
    for loc, socket in recipe.get('missileSockets', {}).items():
        if loc+':missile' in recipe.get('socketBanks', {}):
            continue
        launchers = [m for m in mounts if m['location'] == loc and m['family'] == 'missile' and not m['rear']]
        if len(launchers) < 2:
            continue
        scale = recipe['weaponScale']*recipe.get('missileScale', 1)
        grids = [weapons.launcher_grid(rules[m['index']], m, scale, recipe.get('missileColumns', 0),
                                       weapons.orientation_for(m, rules[m['index']], recipe)) for m in launchers]
        gap = .4
        # A crowded bay lays its launchers out side by side rather than shrinking one thin stack.
        across = recipe.get('missileBayColumns', 1) if len(launchers) > 2 else 1
        rows = [list(range(start, min(start+across, len(launchers)))) for start in range(0, len(launchers), across)]
        heights = [max(grids[i]['height'] for i in row) for row in rows]
        available = recipe['missileBayHeight']-gap*(len(rows)-1)
        if available <= 0:
            raise ValueError('Too many launchers for '+recipe['name']+' '+loc)
        fit = min(1, available/sum(heights))
        widest = max(grid['width'] for grid in grids)
        if across > 1:
            fit = min(fit, (recipe['missileBayWidth']-gap*(across-1))/(across*widest))
        cursor = socket[2]-(sum(heights)*fit+gap*(len(rows)-1))/2
        for row, height in zip(rows, heights):
            for place, i in enumerate(row):
                shift = (place-(len(row)-1)/2)*(widest*fit+gap)
                stacked_launchers[launchers[i]['index']] = (cursor+height*fit/2, fit, shift)
            cursor += height*fit+gap
    for mount in mounts:
        loc = mount['location']
        special = mount['family'] == 'missile' and loc in recipe.get('missileSockets', {}) and not mount['rear']
        source = recipe['rearSockets'] if mount['rear'] else recipe.get('missileSockets', {}) if special else recipe['sockets']
        pixel = list(source.get(loc, recipe['sockets'][loc]))
        if mount['rear'] and loc not in source:
            pixel[1] += 9
        rule = rules[mount['index']]
        family = weapons.bank_family(mount, rule)
        bank = recipe.get('socketBanks', {}).get(loc+':'+family) if not mount['rear'] else None
        form = arm_form(unit, loc) if loc in ('LA', 'RA') else None
        if form and not mount['rear'] and not special:
            # An arm weapon attaches where the arm ends: on the forearm, at the wrist or at the elbow.
            pixel = list(recipe.get('armSockets', {}).get(loc, {}).get(form, pixel))
            bank = recipe.get('socketBanks', {}).get(loc+'@'+form+':'+family, bank)
        key = (loc, mount['rear'], family if bank else special)
        index = counts[key]
        counts[key] += 1
        if bank and index < len(bank):
            pixel = list(bank[index])
        else:
            # Stable sockets are keyed by actual mount identity; extra equipment uses a compact bank.
            pixel[0] += ((index+1)//2)*(1 if index % 2 else -1)*recipe['slotSpacing']
            pixel[2] -= (index//3)*3
        if loc in ('LL', 'RL') and mount['family'] != 'jump-jet' and not mount['rear']:
            # Leg weapons ride just below the hip like a low-slung belt, never down on the shin.
            pixel = list(recipe.get('beltSockets', {}).get(loc, [pixel[0], pixel[1], recipe['hip'][2]-5]))
        if mount['index'] in stacked_launchers:
            pixel = list(source[loc])
            pixel[0] += stacked_launchers[mount['index']][2]
            pixel[2] = stacked_launchers[mount['index']][0]
        if mount['family'] == 'jump-jet':
            pixel[1] += 9
            pixel[2] = min(pixel[2], 29)
        scale = recipe['weaponScale']*(recipe.get('missileScale', 1) if special else 1)
        if mount['index'] in stacked_launchers:
            scale *= stacked_launchers[mount['index']][1]
        if mount['family'] == 'ppc' and recipe.get('barrelLength'):
            # The recipe states this length in model units, so it is not scaled again.
            rule['length'] = recipe['barrelLength']/scale
        options = {'maximumColumns': recipe.get('missileColumns', 0), 'detail': detail,
                   'orientation': weapons.orientation_for(mount, rule, recipe), 'aim': weapons.aim_for(mount, recipe),
                   'slope': recipe.get('missileSlope', 0) if special else 0, 'slopeOrigin': source[loc][2]}
        hard_point = point(recipe['rearSockets'].get(loc, recipe['sockets'][loc]) if mount['rear']
                           else recipe.get('armSockets', {}).get(loc, {}).get(form, recipe['sockets'][loc]))
        placements.append({'mount': mount, 'rule': rule, 'position': list(point(pixel)), 'scale': scale,
                           'options': options, 'hardPoint': hard_point,
                           # A launcher in its bay and a weapon on an art-directed bank spot keep their place.
                           'fixed': special, 'banked': bool(bank and index < len(bank))})
    lay_out(recipe, placements)
    attachments = []
    for placement in placements:
        mount = placement['mount']
        weapons.draw(result, mount, placement['rule'], tuple(placement['position']), placement['scale'],
                     placement['options'])
        attachments.append({'equipmentIndex': mount['index'], 'equipment': mount['internalName'],
                            'location': mount['location'], 'rear': mount['rear'], 'family': mount['family'],
                            'position': placement['position'], 'rackSize': mount['rackSize']})
        if placement.get('crowded'):
            attachments[-1]['crowded'] = True
    return result, attachments


def lay_out(recipe, placements):
    """Moves any weapon that would overlap another in its location to a free spot in that location's area."""
    def size_of(placement):
        return weapons.footprint(placement['rule'], placement['mount'], placement['scale'], placement['options'])

    def priority(placement):
        size = size_of(placement)
        return (not placement['fixed'], not placement['banked'], -(size[0]*size[1] if size else 0))

    areas = {}
    # Bay launchers reserve their space first, then art-directed bank spots, then the rest, largest first.
    for placement in sorted(placements, key=priority):
        mount = placement['mount']
        size = size_of(placement)
        if size is None or placement['options']['aim'] is not None:
            continue
        key = (mount['location'], mount['rear'])
        if key not in areas:
            areas[key] = MountArea.for_location(recipe, mount['location'],
                                                (placement['hardPoint'][0], placement['hardPoint'][2]))
        x, _, z = placement['position']
        if placement['fixed']:
            areas[key].block(x, z, *size)
            continue
        placement['position'][0], placement['position'][2], fit, crowded = areas[key].place(x, z, *size)
        placement['scale'] *= fit
        if crowded:
            placement['crowded'] = True


# The part that carries everything above the waist. The game turns this part on its own to show a torso
# twist, so the head, side torsos and arms must hang from it and the hips and legs must not.
UPPER_BODY = 'CT'


# Where each generic body stands its legs, keyed by the game's own location abbreviations. Left is -x, front is +y.
FALLBACK_LEGS = {'biped': {'LL': (-10, 0), 'RL': (10, 0)},
                 'tripod': {'LL': (-13, -9), 'RL': (13, -9), 'CL': (0, 11)},
                 'quad': {'RLL': (-14, -10), 'RRL': (14, -10), 'FLL': (-14, 10), 'FRL': (14, 10)}}


def fallback(kind):
    """A generic body. Every part is named after the game location it stands for, as the recipes' parts are,
    so the game can show a lost or destroyed location on any body without a lookup table."""
    g = Geometry()
    g.joint(UPPER_BODY, (0, 0, 0))
    g.joint('HD', (0, 0, 0), UPPER_BODY)
    g.box((0, 0, 34), (11, 18, 16), 'CT', 'paint', .3, .85)
    for side, torso in ((-1, 'LT'), (1, 'RT')):
        g.joint(torso, (0, 0, 0), UPPER_BODY)
        g.box((side*8, 0, 33.5), (6.5, 16, 14), torso, 'paint', .3, .9)
    g.box((0, 8, 43), (10, 10, 10), 'HD', 'paint', .4, .75)
    g.box((0, 13, 43), (7, 1, 3), 'HD', 'glass')
    for leg, (x, y) in FALLBACK_LEGS[kind].items():
        g.beam((x, y, 31), (x*1.2, y, 17), 8, 9, leg, 'edge')
        g.beam((x*1.2, y, 17), (x*1.25, y, 4), 8, 9, leg, 'paint')
        g.box((x*1.25, y+3, 2), (9, 13, 4), leg, 'paint', .3)
    if kind != 'quad':
        for side, arm in ((-1, 'LA'), (1, 'RA')):
            g.joint(arm, (0, 0, 0), UPPER_BODY)
            g.box((side*18, 0, 37), (10, 12, 9), arm, 'paint', .4)
            g.box((side*20, 2, 27), (8, 10, 14), arm, 'edge', .3)
    return g


def infantry_slots(count, vehicle=False):
    """Each slot owns its position and heading; the live unit supplies only its count."""
    if not vehicle:
        positions = [(0, 0)] if count == 1 else [(-12, 9), (12, 9), (0, -10), (-17, -12), (17, -12), (0, 17)]
        return [('trooper', position, ((i % 3)-1)*.12) for i, position in enumerate(positions[:count])]
    if count == 0:
        return []
    vehicles = 1 if count <= 4 else 2
    if count == 1:
        placements = [((0, 0), .18)]
    elif count == 2:
        placements = [((-6, 3), .23), ((25, -14), -.45)]
    elif count <= 4:
        placements = [((-10, 1), -.28), ((24, 25), .55), ((28, -20), -.35), ((-36, -28), .5)]
    else:
        placements = [((-24, 10), .30), ((24, -10), -.27), ((6, 32), .5),
                      ((-4, -33), -.45), ((-42, -24), .5), ((42, 26), -.5)]
    return [('vehicle' if i < vehicles else 'trooper', *placements[i]) for i in range(count)]


def make_preview(examples, out, recipes):
    if not bpy.app.background:
        raise RuntimeError('Build the review .blend in a background Blender process, then append it in the UI')
    scene = bpy.data.scenes.new('MegaMek silhouette review')
    roots, labels = [], []
    materials = {}
    for role, rgb in PALETTE.items():
        material = bpy.data.materials.new('MM unit '+role)
        # Display-space palette to Blender's linear color representation.
        linear = tuple(c/12.92 if c <= .04045 else ((c+.055)/1.055)**2.4 for c in rgb)
        material.diffuse_color = (*linear, 1)
        material.use_nodes = True
        material.node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value = (*linear, 1)
        material.node_tree.nodes.get('Principled BSDF').inputs['Roughness'].default_value = .8
        materials[role] = material
    for i, (label, geometry, reference) in enumerate(examples):
        collection = bpy.data.collections.new(label)
        scene.collection.children.link(collection)
        offset = ((3-i)*70, 0, 0)
        joints = {}
        for name in geometry.pivots:
            joint = bpy.data.objects.new(label+' / '+name, None)
            joint.empty_display_size = 1.5
            parent = geometry.parents[name]
            if parent:
                joint.parent = joints[parent]
                joint.location = Vector(geometry.pivots[name])-Vector(geometry.pivots[parent])
            else:
                joint.location = add(geometry.pivots[name], offset)
            collection.objects.link(joint)
            joints[name] = joint
        roots.append(joints['root'])
        groups = defaultdict(list)
        for tri, group, material in geometry.faces:
            groups[(group, material)].append(tri)
        for (group, role), triangles in groups.items():
            vertices = [Vector(p)-Vector(geometry.pivots[group]) for tri in triangles for p in tri]
            mesh = bpy.data.meshes.new(label+' '+group+' '+role)
            mesh.from_pydata(vertices, [], [tuple(range(j, j+3)) for j in range(0, len(vertices), 3)])
            mesh.materials.append(materials[role])
            obj = bpy.data.objects.new(mesh.name, mesh)
            obj.parent = joints[group]
            collection.objects.link(obj)
            obj['rigid_joint'] = group
            obj['source_sprite'] = reference
        illustration = next(r['illustration'] for r in recipes if r['sprite'] == reference)
        obj = bpy.data.objects.new(label+' illustration reference', None)
        obj.empty_display_type = 'IMAGE'
        obj.data = bpy.data.images.load(str(ROOT / 'data/images/fluff' / illustration), check_existing=True)
        obj.empty_display_size = 65
        obj.location = (offset[0], -45, 32)
        obj.rotation_euler = (pi/2, 0, pi)
        obj.hide_render = True
        collection.objects.link(obj)
        # Reference is a non-rendering image empty. Open the library to compare original pixels directly.
        if reference:
            obj = bpy.data.objects.new(label+' sprite reference', None)
            obj.empty_display_type = 'IMAGE'
            obj.data = bpy.data.images.load(str(SPRITES / reference), check_existing=True)
            obj.empty_display_size = 84
            obj.location = (offset[0], offset[1]+60, 0)
            obj.hide_render = True
            collection.objects.link(obj)
    scene.world = bpy.data.worlds.new('Unit review world')
    scene.world.use_nodes = True
    scene.world.node_tree.nodes['Background'].inputs[0].default_value = (.26, .32, .39, 1)
    scene.world.node_tree.nodes['Background'].inputs[1].default_value = .9
    light = bpy.data.lights.new('Unit review key', 'AREA')
    light.energy = 450000
    light.shape = 'DISK'
    light.size = 170
    obj = bpy.data.objects.new('Unit review key', light)
    obj.location = (150, 110, 190)
    obj.rotation_euler = (Vector((105, 0, 25))-obj.location).to_track_quat('-Z', 'Y').to_euler()
    scene.collection.objects.link(obj)
    camera = bpy.data.objects.new('Unit review camera', bpy.data.cameras.new('Unit review camera'))
    camera.data.type = 'ORTHO'
    camera.data.ortho_scale = 285
    camera.location = (105, 350, 165)
    camera.rotation_euler = (Vector((105, 0, 26))-camera.location).to_track_quat('-Z', 'Y').to_euler()
    scene.collection.objects.link(camera)
    scene.camera = camera
    label_material = bpy.data.materials.new('Review labels')
    label_material.use_nodes = True
    nodes = label_material.node_tree.nodes
    nodes.clear()
    emission = nodes.new('ShaderNodeEmission')
    emission.inputs['Color'].default_value = (.9, .94, .98, 1)
    output = nodes.new('ShaderNodeOutputMaterial')
    label_material.node_tree.links.new(emission.outputs[0], output.inputs['Surface'])
    for i, (label, geometry, _) in enumerate(examples):
        text = bpy.data.curves.new(label+' label', 'FONT')
        text.body = label+'\n'+str(len(geometry.faces))+' triangles'
        text.align_x = 'CENTER'
        text.size = 3.3
        text.materials.append(label_material)
        obj = bpy.data.objects.new(label+' label', text)
        obj.location = ((3-i)*70, 20, -4)
        obj.rotation_euler = camera.rotation_euler
        scene.collection.objects.link(obj)
        labels.append(obj)
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 20
    scene.render.resolution_x = 2000
    scene.render.resolution_y = 750
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.film_transparent = False
    scene.view_settings.view_transform = 'Standard'
    for root in roots:
        root.rotation_euler.z = -.4
    # This runs in a fresh background process. The running interactive Blender file is untouched.
    bpy.context.window.scene = scene
    scene.view_layers[0].update()
    bpy.ops.wm.save_as_mainfile(filepath=str(out / 'unit-models.blend'), check_existing=False)
    scene.render.filepath = str(out / 'preview.png')
    bpy.ops.render.render(write_still=True, scene=scene.name)
    for name, angle, location, target in (
            ('front', 0, (105, 350, 29), (105, 0, 29)),
            ('side', pi/2, (105, 350, 29), (105, 0, 29)),
            ('top', 0, (105, 0, 350), (105, 0, 0))):
        for i, root in enumerate(roots):
            root.rotation_euler.z = angle
            root.location.x = i*70 if name == 'top' else (3-i)*70
        camera.location = location
        camera.rotation_euler = (0, 0, 0) if name == 'top' else (Vector(target)-camera.location).to_track_quat('-Z', 'Y').to_euler()
        for i, label in enumerate(labels):
            label.location = (i*70, -30, 0) if name == 'top' else ((3-i)*70, 25, -6)
            label.rotation_euler = camera.rotation_euler
        scene.render.filepath = str(out / (name+'.png'))
        bpy.ops.render.render(write_still=True, scene=scene.name)


def build(args):
    catalog_path = Path(args.catalog).resolve()
    catalog = json.loads(catalog_path.read_text(encoding='utf-8'))
    recipes_path = Path(args.recipes).resolve()
    recipes = json.loads(recipes_path.read_text(encoding='utf-8'))['chassis']
    if catalog['schema'] != 1 or catalog['failures']:
        raise ValueError('Catalog has unsupported schema or loading failures')
    out = Path(args.output).resolve()
    if out.is_relative_to((ROOT / 'data').resolve()):
        raise ValueError('Baked reference assemblies cannot be exported into deployed data; use tools/unit-models/references')
    out.mkdir(parents=True, exist_ok=True)
    units_by_chassis = defaultdict(list)
    for unit in catalog['units']:
        units_by_chassis[unit['chassis']].append(unit)
    manifest = {'schema': 1, 'triangleTarget': TRIANGLE_TARGET, 'triangleLimit': TRIANGLE_LIMIT,
                'triangleBudgetScope': 'bare-unit',
                'catalogSha256': digest(catalog_path),
                'recipesSha256': digest(recipes_path), 'generatorSha256': digest(Path(__file__)),
                'geometrySha256': digest(Path(__file__).with_name('unit_model_geometry.py')),
                'weaponShapesSha256': digest(Path(__file__).with_name('unit_weapon_shapes.py')),
                'weaponRulesSha256': digest(weapons.RULES_PATH),
                'mountLayoutSha256': digest(Path(__file__).with_name('unit_mount_layout.py')),
                'chassisBuilderSha256': digest(Path(__file__).with_name('unit_mek_chassis.py')),
                'references': {},
                'models': {}, 'variants': {}, 'formations': {}, 'needsReview': [], 'coverage': {}}
    examples = []
    def export(geometry, relative, bare_unit=True):
        manifest['models'][relative] = geometry.export(out / relative, relative, bare_unit=bare_unit)
        return relative
    for recipe in recipes:
        units = units_by_chassis.get(recipe['name'], [])
        if not units:
            raise ValueError('Unknown chassis '+recipe['name'])
        if len({u['name'] for u in units}) != len(units):
            raise ValueError('Duplicate unit names in '+recipe['name']+'; give each catalogued refit a distinct model name')
        manifest['references'][recipe['name']] = {
            'sprite': recipe['sprite'], 'spriteSha256': digest(SPRITES / recipe['sprite']),
            'illustration': recipe['illustration'],
            'illustrationSha256': digest(ROOT / 'data/images/fluff' / recipe['illustration'])}
        base = build_chassis(recipe)
        folder = 'meks/'+recipe['id']+'/'
        # The shared unarmed body takes the arm form of the reference variant.
        reference_unit = next((u for u in units if u['model'] == recipe['referenceVariant']), units[0])
        export(fit_arms(base, reference_unit), folder+'body.g3dj')
        descriptor = {'schema': 1, 'kind': 'mek', 'chassis': recipe['name'], 'fallback': 'body.g3dj',
                      'upperBodyNode': UPPER_BODY, 'variants': {}}
        for unit in units:
            detail = weapons.DETAIL_LEVELS[0]
            geometry, attachments = assemble(base, recipe, unit, detail)
            body_triangles = len(fit_arms(base, unit).faces)
            if geometry is None or body_triangles > TRIANGLE_LIMIT:
                manifest['needsReview'].append({'name': unit['name'], 'source': unit['source'],
                                                'reason': attachments if geometry is None else 'body-triangle-hard-cap'})
                continue
            name = 'variants/'+slug(unit['model'])+'.g3dj'
            export(geometry, folder+name, bare_unit=False)
            if unit['variantKey'] in descriptor['variants']:
                raise ValueError('Duplicate variant name '+unit['name'])
            descriptor['variants'][unit['variantKey']] = name
            manifest['variants'][unit['name']] = {'asset': folder+name, 'chassis': recipe['name'],
                'bodyTriangles': body_triangles, 'equipmentTriangles': len(geometry.faces)-body_triangles,
                'sprite': unit['sprite'], 'spriteSha256': digest(SPRITES / unit['sprite']),
                'source': unit['source'], 'sourceSha256': unit['sourceSha256'], 'variantKey': unit['variantKey'], 'attachments': attachments,
                'differentSprite': unit['sprite'] != recipe['sprite']}
            if detail != 'full':
                manifest['variants'][unit['name']]['launcherDetail'] = detail
            if unit['model'] == recipe['referenceVariant']:
                examples.append((unit['name'], geometry, recipe['sprite']))
        write_json(out / (folder+'model.json'), descriptor)
    for kind in ('biped', 'quad', 'tripod'):
        export(fallback(kind), 'fallback/'+kind+'.g3dj')
        write_json(out / ('fallback/'+kind+'.json'), {'schema': 1, 'kind': 'mek', 'fallback': kind+'.g3dj',
                                                       'upperBodyNode': UPPER_BODY})
    poses = ('standing', 'aiming', 'kneeling', 'advancing')
    for armored, kind, limit, reference in ((False, 'infantry', 6, 'defaults/default_infantry_platoon.png'),
                                             (True, 'battle-armor', 4, 'defaults/default_ba.png')):
        library = [person(pose, armored) for pose in poses]
        for pose, geometry in zip(poses, library):
            export(geometry, kind+'/poses/'+pose+'.g3dj')
        formations = {}
        for count in range(limit+1):
            geometry = Geometry()
            for i, (_, (x, y), angle) in enumerate(infantry_slots(count)):
                geometry.extend(library[i % len(library)], (x, y, 0), angle, group='formation')
            relative = 'squad-'+str(count)+'.g3dj'
            export(geometry, kind+'/'+relative)
            formations[str(count)] = relative
            if count == (3 if armored else 6):
                examples.append((kind+' formation', geometry, reference))
        descriptor = {'schema': 1, 'kind': 'formation', 'fallback': 'squad-1.g3dj', 'formations': formations}
        if not armored:
            descriptor['movementFormations'] = {}
            for mode, style, sprite in (
                    ('INF_MOTORIZED', 'motorized', 'motorized_infantry_platoon.png'),
                    ('TRACKED', 'tracked', 'mecha_t_platoon.png'),
                    ('WHEELED', 'wheeled', 'mecha_w_platoon.png'),
                    ('HOVER', 'hover', 'mecha_h_platoon.png'),
                    ('INF_JUMP', 'jump', 'jump_infantry_platoon.png')):
                reference = 'Infantry/'+sprite
                manifest['references']['infantry-'+style] = {
                    'sprite': reference, 'spriteSha256': digest(SPRITES / reference)}
                troop_library = [person(pose, jump=True) for pose in poses] if style == 'jump' else library
                if style == 'jump':
                    for pose, trooper in zip(poses, troop_library):
                        export(trooper, 'infantry/jump/poses/'+pose+'.g3dj')
                else:
                    # Transports are twice the original dimensions, including height.
                    vehicle = Geometry()
                    for triangle, group, material in infantry_vehicle(style).faces:
                        vehicle.face([(x*2, y*2, z*2) for x, y, z in triangle], group, material)
                    export(vehicle, 'infantry/vehicles/'+style+'.g3dj')
                choices = {}
                for count in range(7):
                    geometry, components, placed = Geometry(), [], []
                    troop_index = 0
                    for role, (x, y), angle in infantry_slots(count, style != 'jump'):
                        if role == 'vehicle':
                            part = vehicle
                            asset = 'infantry/vehicles/'+style+'.g3dj'
                        else:
                            part = troop_library[troop_index % len(poses)]
                            asset = 'infantry/'+('jump/' if style == 'jump' else '')+'poses/'+poses[troop_index % len(poses)]+'.g3dj'
                            troop_index += 1
                        start = len(geometry.faces)
                        geometry.extend(part, (x, y, 0), angle, group='formation')
                        if style != 'jump':
                            vertices = [p for tri, _, _ in geometry.faces[start:] for p in tri]
                            tree = BVHTree.FromPolygons(vertices,
                                [tuple(range(j, j+3)) for j in range(0, len(vertices), 3)], all_triangles=True)
                            for other_role, other in placed:
                                if 'vehicle' in (role, other_role) and tree.overlap(other):
                                    raise ValueError(f'{style} / {count} slots: transport intersects {role}')
                            placed.append((role, tree))
                        components.append({'role': role, 'asset': asset, 'position': [x, y, 0], 'angle': angle})
                    relative = style+'/squad-'+str(count)+'.g3dj'
                    export(geometry, 'infantry/'+relative)
                    choices[str(count)] = relative
                    manifest['formations']['infantry/'+relative] = {
                        'movementMode': mode, 'slots': count, 'components': components}
                descriptor['movementFormations'][mode] = choices
        write_json(out / (kind+'/model.json'), descriptor)
    known = {r['name'] for r in recipes}
    pending = []
    for chassis, units in sorted(units_by_chassis.items()):
        if chassis not in known:
            reference = min(units, key=lambda u: (u['genericSprite'], len(u['model']), u['name']))
            pending.append({'chassis': chassis, 'variants': len(units), 'configuration': reference['configuration'],
                            'sprite': reference['sprite'], 'genericSprite': reference['genericSprite'],
                            'referenceVariant': reference['model'], 'status': 'needs-chassis-recipe'})
    manifest['coverage'] = {'mekVariants': len(catalog['units']), 'mekChassis': len(units_by_chassis),
                            'authoredChassis': len(recipes), 'assembledVariants': len(manifest['variants']),
                            'pendingChassis': len(pending)}
    write_json(out / 'manifest.json', manifest)
    write_json(out / 'chassis-queue.json', pending)
    if args.preview:
        preview = ROOT / '.work/mek-models/review'
        preview.mkdir(parents=True, exist_ok=True)
        make_preview(examples[:len(recipes)], preview, recipes)
    print(json.dumps({'coverage': manifest['coverage'], 'models': len(manifest['models']),
                      'maximumTriangles': max(m['triangles'] for m in manifest['models'].values()),
                      'needsReview': len(manifest['needsReview'])}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--catalog', default=str(ROOT / '.work/mek-models/catalog.json'))
    parser.add_argument('--recipes', default=str(ROOT / 'tools/unit-models/chassis.json'))
    parser.add_argument('--output', default=str(ROOT / 'tools/unit-models/references/generated'))
    parser.add_argument('--preview', action='store_true')
    build(parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []))
