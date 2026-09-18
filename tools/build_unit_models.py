"""Build sprite-referenced Mek chassis/variants and compressed infantry formations.

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
from unit_model_geometry import Geometry, PALETTE, add, content_digest
from unit_mek_chassis import build_chassis
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


def assemble(base, recipe, unit, detail='full'):
    result = deepcopy(base)
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
                           else recipe['sockets'][loc])
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


def fallback(kind):
    g = Geometry()
    g.box((0, 0, 34), (22, 18, 16), 'CT', 'paint', .45, .8)
    g.box((0, 8, 43), (10, 10, 10), 'HD', 'paint', .4, .75)
    g.box((0, 13, 43), (7, 1, 3), 'HD', 'glass')
    legs = [(-10, 0), (10, 0)] if kind == 'biped' else [(-13, -9), (13, -9), (0, 11)] if kind == 'tripod' else [(-14, -10), (14, -10), (-14, 10), (14, 10)]
    for i, (x, y) in enumerate(legs):
        g.beam((x, y, 31), (x*1.2, y, 17), 8, 9, 'leg-'+str(i), 'edge')
        g.beam((x*1.2, y, 17), (x*1.25, y, 4), 8, 9, 'leg-'+str(i), 'paint')
        g.box((x*1.25, y+3, 2), (9, 13, 4), 'leg-'+str(i), 'paint', .3)
    if kind != 'quad':
        for sign in (-1, 1):
            g.box((sign*18, 0, 37), (10, 12, 9), 'arm-'+str(sign), 'paint', .4)
            g.box((sign*20, 2, 27), (8, 10, 14), 'arm-'+str(sign), 'edge', .3)
    return g


def person(pose, armored=False):
    g = Geometry()
    kneel = pose == 'kneeling'
    advance = pose == 'advancing'
    torso_z = 10 if kneel else 14
    spread = 3.2 if armored else 2.1
    for sign in (-1, 1):
        hip = (sign*spread/2, 0, torso_z-3)
        knee = (sign*spread, 3 if kneel and sign == -1 else -1 if kneel else sign*2 if advance else 0, 4 if kneel else 6)
        foot = (sign*spread, -3 if kneel and sign == 1 else 4 if advance and sign == 1 else 0, 1)
        width = 3.1 if armored else 1.9
        g.beam(hip, knee, width, width, 'soldier', 'paint')
        g.beam(knee, foot, width, width, 'soldier', 'edge')
        g.box((foot[0], foot[1]+1, 1), (width, 3.5, 2), 'soldier', 'metal')
    g.box((0, 0, torso_z), (7 if armored else 5, 5 if armored else 3.3, 7 if armored else 6),
          'soldier', 'paint', .3 if armored else 0, .82)
    g.box((0, -.8, torso_z+5), (4.5 if armored else 3.3, 4 if armored else 3.3, 4),
          'soldier', 'paint', .4 if armored else 0, .8)
    g.face([(-1.5, 1.3, torso_z+5.6), (1.5, 1.3, torso_z+5.6),
            (1.5, 1.3, torso_z+4.4), (-1.5, 1.3, torso_z+4.4)],
           'soldier', 'glass' if armored else 'dark')
    for sign in (-1, 1):
        shoulder = (sign*(4 if armored else 3), 0, torso_z+2)
        elbow = (sign*(4.5 if armored else 3.5), 2, torso_z-1)
        hand = (1.5, 3, torso_z-2) if pose == 'standing' else (sign*3, 4, torso_z-2) if advance else (1.5, 5, torso_z+1)
        g.beam(shoulder, elbow, 3.5 if armored else 2, group='soldier', material='paint')
        g.beam(elbow, hand, 3 if armored else 1.7, group='soldier', material='edge')
    g.box((1.5, 3, torso_z-2) if pose == 'standing' else (1.5, 5, torso_z+.8),
          (2, 3, 8) if pose == 'standing' else (2, 8, 2), 'soldier', 'metal')
    if armored:
        # A compact jump pack / arm cannon follows the generic BA sprite's bulky shoulders.
        g.box((0, -3, torso_z+2), (7, 3, 7), 'soldier', 'edge')
        g.beam((4, 2, torso_z), (4, 8, torso_z), 2.4, 2.4, 'soldier', 'metal')
    return g


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
    out.mkdir(parents=True, exist_ok=True)
    units_by_chassis = defaultdict(list)
    for unit in catalog['units']:
        units_by_chassis[unit['chassis']].append(unit)
    manifest = {'schema': 1, 'budget': 1000, 'catalogSha256': digest(catalog_path),
                'recipesSha256': digest(recipes_path), 'generatorSha256': digest(Path(__file__)),
                'geometrySha256': digest(Path(__file__).with_name('unit_model_geometry.py')),
                'weaponShapesSha256': digest(Path(__file__).with_name('unit_weapon_shapes.py')),
                'weaponRulesSha256': digest(weapons.RULES_PATH),
                'mountLayoutSha256': digest(Path(__file__).with_name('unit_mount_layout.py')),
                'chassisBuilderSha256': digest(Path(__file__).with_name('unit_mek_chassis.py')),
                'references': {},
                'models': {}, 'variants': {}, 'needsReview': [], 'coverage': {}}
    examples = []
    def export(geometry, relative):
        manifest['models'][relative] = geometry.export(out / relative, relative)
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
        export(base, folder+'body.g3dj')
        descriptor = {'schema': 1, 'kind': 'mek', 'chassis': recipe['name'], 'fallback': 'body.g3dj', 'variants': {}}
        for unit in units:
            for detail in weapons.DETAIL_LEVELS:
                geometry, attachments = assemble(base, recipe, unit, detail)
                if geometry is None or len(geometry.faces) <= 1000:
                    break
            if geometry is None or len(geometry.faces) > 1000:
                manifest['needsReview'].append({'name': unit['name'], 'source': unit['source'],
                                                'reason': attachments if geometry is None else 'triangle-budget'})
                continue
            name = 'variants/'+slug(unit['model'])+'.g3dj'
            export(geometry, folder+name)
            if unit['variantKey'] in descriptor['variants']:
                raise ValueError('Duplicate variant name '+unit['name'])
            descriptor['variants'][unit['variantKey']] = name
            manifest['variants'][unit['name']] = {'asset': folder+name, 'chassis': recipe['name'],
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
        write_json(out / ('fallback/'+kind+'.json'), {'schema': 1, 'kind': 'mek', 'fallback': kind+'.g3dj'})
    poses = ('standing', 'aiming', 'kneeling', 'advancing')
    for armored, kind, limit, reference in ((False, 'infantry', 6, 'defaults/default_infantry_platoon.png'),
                                             (True, 'battle-armor', 4, 'defaults/default_ba.png')):
        library = [person(pose, armored) for pose in poses]
        for pose, geometry in zip(poses, library):
            export(geometry, kind+'/poses/'+pose+'.g3dj')
        formations = {}
        for count in range(limit+1):
            geometry = Geometry()
            for i in range(count):
                # Vary stance/facing deterministically. Small squads stay centered in the hex.
                positions = [(0, 0)] if count == 1 else [(-12, 9), (12, 9), (0, -10), (-17, -12), (17, -12), (0, 17)]
                x, y = positions[i]
                geometry.extend(library[i % len(library)], (x, y, 0), ((i % 3)-1)*.12, group='formation')
            relative = 'squad-'+str(count)+'.g3dj'
            export(geometry, kind+'/'+relative)
            formations[str(count)] = relative
            if count == (3 if armored else 6):
                examples.append((kind+' formation', geometry, reference))
        write_json(out / (kind+'/model.json'), {'schema': 1, 'kind': 'formation',
                   'fallback': 'squad-1.g3dj', 'formations': formations})
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
    parser.add_argument('--output', default=str(ROOT / 'data/models/units'))
    parser.add_argument('--preview', action='store_true')
    build(parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []))
