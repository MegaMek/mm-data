"""Compile authored chassis sockets into reusable bodies and runtime mounting preferences.

There is deliberately no loadout selection or packing here; Java owns both for play and review.
"""
from math import sqrt

from unit_mek_chassis import build_chassis
from unit_model_geometry import Geometry, sub


def fallback_body(topology):
    g = Geometry(modular=True)
    g.joint('pelvis', (0, 0, 29))
    g.joint('CT', (0, 0, 29), 'pelvis')
    g.box((0, 0, 28), (16, 10, 6), 'pelvis', 'metal')
    g.box((0, 0, 37), (16, 17, 15), 'CT', 'paint', .4, .85)
    for side, torso in ((-1, 'LT'), (1, 'RT')):
        g.joint(torso, (side*9, 0, 37), 'CT')
        g.box((side*9, 0, 37), (8, 15, 13), torso, 'edge', .3)
    g.joint('HD', (0, 6, 45), 'CT')
    g.box((0, 6, 45), (9, 9, 8), 'HD', 'paint', .4, .75)
    g.box((0, 10.6, 45), (6, .5, 2.6), 'HD', 'glass')
    legs = {'LL': (-9, 0), 'RL': (9, 0)}
    if topology == 'tripod':
        legs = {'LL': (-12, -7), 'RL': (12, -7), 'CL': (0, 11)}
    elif topology == 'quad':
        legs = {'FLL': (-14, 10), 'FRL': (14, 10), 'RLL': (-14, -10), 'RRL': (14, -10)}
    for leg, (x, y) in legs.items():
        g.joint(leg, (x, y, 29), 'pelvis')
        g.joint(leg+'-shin', (x*1.12, y-2, 16), leg)
        g.joint(leg+'-foot', (x*1.2, y, 3), leg+'-shin')
        g.beam((x, y, 29), (x*1.12, y-2, 17), 7, 8, leg, 'edge')
        g.beam((x*1.12, y-2, 16), (x*1.2, y, 4), 7, 9, leg+'-shin', 'paint', taper=.75)
        g.box((x*1.2, y+3, 2), (9, 13, 4), leg+'-foot', 'paint', .25)
    if topology != 'quad':
        for side, arm in ((-1, 'LA'), (1, 'RA')):
            g.joint(arm, (side*17, 0, 40), 'CT')
            g.joint(arm+'-forearm', (side*20, 1, 31), arm)
            g.box((side*17, 0, 40), (9, 10, 9), arm, 'paint', .35)
            g.beam((side*17, 0, 38), (side*20, 1, 31), 5, 6, arm, 'metal')
            for part in ('forearm', 'wrist', 'hand', 'elbow'):
                g.joint(arm+'@'+part, (side*20, 1, 31), arm if part == 'elbow' else arm+'-forearm')
            g.box((side*20, 4, 28), (7, 10, 8), arm+'@forearm', 'paint', .25)
            g.box((side*20, 8, 28), (6, 4, 5), arm+'@hand', 'metal')
            g.box((side*20, 1, 31), (7, 6, 6), arm+'@elbow', 'edge')
    return g, legs


def fallback_recipes():
    recipes = []
    for topology in ('biped', 'tripod', 'quad'):
        _, legs = fallback_body(topology)
        sockets = {'HD': [42, 25, 45], 'CT': [42, 27, 37], 'LT': [33, 28, 37], 'RT': [51, 28, 37]}
        sockets.update({leg: [42+x, 31-y, 24] for leg, (x, y) in legs.items()})
        arms = {}
        if topology != 'quad':
            for side, arm in ((-1, 'LA'), (1, 'RA')):
                sockets[arm] = [42+side*20, 28, 28]
                arms[arm] = {'hand': sockets[arm], 'wrist': sockets[arm], 'elbow': [42+side*20, 32, 31]}
        recipes.append({'id': 'fallback-'+topology, 'topology': topology, 'sockets': sockets,
                        'armSockets': arms, 'hip': [42, 36, 29], 'weaponScale': .9})
    recipes.append({**recipes[0], 'id': 'fallback-airmek', 'form': 'airmek'})
    return recipes


def point(pixel):
    return (pixel[0]-42, 36-pixel[1], pixel[2])


def aim_rotation(aim):
    """Quaternion taking +Y to a socket's authored forward direction."""
    length = sqrt(sum(value*value for value in aim))
    x, y, z = (value/length for value in aim)
    if y < -.99999:
        return [0, 0, 1, 0]
    scale = sqrt(2*(1+y))
    return [z/scale, 0, -x/scale, scale/2]


def build_meks(recipes, output, export_asset, write_json):
    assets = {}
    for recipe in recipes:
        body = fallback_body(recipe['topology'])[0] if 'topology' in recipe else build_chassis(recipe, modular=True)
        if recipe.get('form') == 'airmek':
            for side in (-1, 1):
                node = 'wing'+str(side)
                body.joint(node, (side*8, -7, 37), 'CT')
                body.prism([(side*8, -5), (side*32, -19), (side*30, -27), (side*8, -16)], 34, 37, node, 'edge')
                body.beam((side*9, -10, 32), (side*9, -11, 22), 8, 8, 'CT', 'metal', 6)
                body.emitter((side*9, -11, 21.5), (0, 0, -1), 'CT', 'exhaust', 'exhaust')
        hardpoints, mounts = [], []

        def mount(identifier, location, pixel, *, rear=False, family='', form='', bay=False, node=None):
            if node is None:
                node = location+'-forearm' if location in ('LA', 'RA') and form != 'elbow' else location
            aim = (0, -1, 0) if rear else recipe.get('socketAim', {}).get(location+':'+family,
                                               recipe.get('socketAim', {}).get(location, (0, 1, 0)))
            size = recipe.get('mountAreas', {}).get(location, {})
            width = size.get('width', 6 if location == 'HD' else 12 if location in ('CT', 'LT', 'RT') else 10)
            height = size.get('height', 6 if location == 'HD' else 14 if location in ('CT', 'LT', 'RT') else 10)
            if bay:
                height = recipe.get('missileBayHeight', height)
                width = recipe.get('missileBayWidth', 12)
            hardpoints.append({'id': identifier, 'location': location, 'side': 'rear' if rear else 'front',
                               'node': node, 'position': sub(point(pixel), body.pivots[node]),
                               'rotation': aim_rotation(aim), 'size': [width, 6, height],
                               'minScale': .4, 'maxScale': 2 if family == 'lamp' else 1.5,
                               'roles': ['misc'] if family == 'lamp' else ['weapon', 'physical', 'misc']})
            settings = {'hardpoint': identifier, 'family': family, 'form': form, 'bay': bay,
                        'scale': recipe['weaponScale']*(recipe.get('missileScale', 1) if bay else 1)}
            style = recipe.get('protrusion', {}).get(location+':'+family, recipe.get('protrusion', {}).get(location))
            if style:
                settings['style'] = style
            if family == 'ppc' and recipe.get('barrelLength'):
                settings['length'] = recipe['barrelLength']
            for override in recipe.get('weaponOverrides', []):
                if override.get('location', location) == location and override.get('family') == family:
                    if 'length' in override:
                        settings['length'] = override['length']*recipe['weaponScale']
            if bay:
                settings['profile'] = 'vertical-slope' if recipe.get('missileSlope') else 'columns-4'
                settings['bayColumns'] = recipe.get('missileBayColumns', 1)
            mounts.append(settings)

        for location, pixel in recipe['sockets'].items():
            pixel = list(pixel)
            if location in ('LL', 'RL'):
                pixel[2] = recipe['hip'][2]-5
            mount(location+'-front', location, pixel)
            rear = recipe.get('rearSockets', {}).get(location, [pixel[0], pixel[1]+9, pixel[2]])
            mount(location+'-rear', location, rear, rear=True)
            # Exhaust is a separate rear mounting preference, never a front-facing gun socket.
            mount(location+'-exhaust', location, [rear[0], rear[1], min(rear[2], 29)], family='jump-jet')
            if recipe.get('barrelLength'):
                mount(location+'-ppc', location, pixel, family='ppc')
        for location in ('LA', 'RA'):
            if location not in recipe['sockets']:
                continue
            forms = dict(recipe.get('armSockets', {}).get(location, {}))
            # A refit without lower-arm actuators must attach at the remaining elbow, not a removed hand.
            # Keep stock hand/family-bank placement unchanged when no special hand socket was authored.
            forms.setdefault('wrist', recipe['sockets'][location])
            elbow = body.pivots[location+'-forearm']
            forms.setdefault('elbow', [42+elbow[0], 36-elbow[1], elbow[2]])
            for form, pixel in forms.items():
                mount(location+'-'+form, location, pixel, form=form)
        for location, pixel in recipe.get('missileSockets', {}).items():
            mount(location+'-launcher', location, pixel, family='missile', bay=True)
        for key, bank in recipe.get('socketBanks', {}).items():
            arm, family = key.split(':')
            location, _, form = arm.partition('@')
            for index, pixel in enumerate(bank):
                mount(key+'-'+str(index), location, pixel, family=family, form=form)
        for override in recipe.get('weaponOverrides', []):
            location, family = override.get('location'), override.get('family')
            if location and family and not any(m['family'] == family and
                    next(h for h in hardpoints if h['id'] == m['hardpoint'])['location'] == location for m in mounts):
                mount(location+'-'+family, location, recipe['sockets'][location], family=family)
        # A family-specific shape adjustment also applies when actuators select a wrist/elbow socket.
        for settings in list(mounts):
            if settings['family']:
                continue
            hardpoint = next(h for h in hardpoints if h['id'] == settings['hardpoint'])
            if recipe.get('barrelLength'):
                mounts.append({**settings, 'family': 'ppc', 'length': recipe['barrelLength']})
            for override in recipe.get('weaponOverrides', []):
                if override.get('location') == hardpoint['location'] and 'length' in override:
                    mounts.append({**settings, 'family': override['family'],
                                   'length': override['length']*recipe['weaponScale']})
        lamp_settings = recipe.get('searchlightSocket', {})
        lamp_location = lamp_settings.get('location', 'LT')
        lamp = list(lamp_settings.get('position', recipe['sockets'][lamp_location]))
        if 'position' not in lamp_settings:
            lamp[2] += 9
        mount('external-searchlight', lamp_location, lamp, family='lamp', node=lamp_location)
        mounts[-1]['scale'] = lamp_settings.get('scale', recipe['weaponScale'])
        joints = {'root': 'root', 'hips': 'pelvis', 'torso': 'CT', 'head': 'HD',
                  'leftArm': 'LA', 'rightArm': 'RA', 'leftForearm': 'LA-forearm', 'rightForearm': 'RA-forearm',
                  'leftLeg': 'LL', 'rightLeg': 'RL', 'leftShin': 'LL-shin', 'rightShin': 'RL-shin',
                  'leftFoot': 'LL-foot', 'rightFoot': 'RL-foot'}
        joints = {role: node for role, node in joints.items() if node in body.pivots}
        for location in ('CL', 'FLL', 'FRL', 'RLL', 'RRL'):
            if location in body.pivots:
                joints[location] = location
                joints[location+'Shin'] = location+'-shin'
                if location+'-foot' in body.pivots:
                    joints[location+'Foot'] = location+'-foot'
        key = 'bodies/'+recipe['id']
        topology = recipe.get('topology', 'biped')
        assets[key] = export_asset(body, output, key, 'body', 'mek-'+topology, topology+'-v1', joints, hardpoints)
        descriptor = {
            'schema': 2, 'kind': 'mek', 'body': 'units/modular/'+key+'.json',
            'equipment': 'units/modular/equipment.json', 'mounts': mounts,
            'configuration': topology,
        }
        if 'topology' in recipe:
            descriptor['sizeScales'] = [.72, .86, 1, 1.14]
            descriptor['superHeavyScale'] = 1.4
        write_json(output / ('meks/'+recipe['id']+'.json'), descriptor)
    return assets
