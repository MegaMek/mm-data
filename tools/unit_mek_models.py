"""Compile authored chassis sockets into reusable bodies and runtime mounting preferences.

There is deliberately no loadout selection or packing here; Java owns both for play and review.
"""
from math import sqrt

from unit_mek_chassis import build_chassis, forward, panel, split_torso_locations, upright
from unit_model_geometry import Geometry, sub
from unit_mek_vents import finish_vents
from unit_weapon_shapes import missile_style_for

# Authored proportions, baked into each body's vertices, joints and sockets; never runtime size multipliers.
# Width, depth, leg height, torso height. The head keeps a more consistent size across the weight classes.
FALLBACK_PROPORTIONS = {
    'light': (.95, .95, 1.04, 1.12),
    'medium': (1.05, 1.04, 1.07, 1.04),
    'heavy': (1.13, 1.12, 1.10, 1.16),
    'assault': (1.22, 1.20, 1.14, 1.20),
    'superheavy': (1.52, 1.48, 1.45, 1.60),
}


def fallback_point(p, weight):
    width, depth, legs, torso = FALLBACK_PROPORTIONS[weight]
    x, y, z = p
    height = z*legs if z <= 29 else 29*legs + min(z-29, 13)*torso + max(0, z-42)
    return x*width, y*depth, height


def author_fallback(body, weight):
    """Five silhouettes: a slim scout, balanced medium, broad heavy, armored assault and massive superheavy."""
    if weight in ('assault', 'superheavy'):
        # Additional breastplate/shoulder armor contributes bulk, not baked equipment.
        body.box((0, 9, 38), (13, 3, 9), 'CT', 'edge', .3)
        for side, torso in ((-1, 'LT'), (1, 'RT')):
            body.box((side*10, 0, 43), (10, 15, 4), torso, 'paint', .4)
    body.faces = [(tuple(fallback_point(p, weight) for p in tri), node, material) for tri, node, material in body.faces]
    body.pivots = {node: fallback_point(p, weight) for node, p in body.pivots.items()}
    for emitter in body.emitters:
        emitter['position'] = fallback_point(emitter['position'], weight)
    return body


def fallback_hull(g, style):
    """Distinct bare anatomy; the approved assault shell remains the default."""
    if style == 'light':
        # Locust-like scout proportions: a forward cockpit pod, not a humanoid head.
        forward(g, [(-9, 10, 10, 0, 37.5), (0, 16, 13, 0, 37.5),
                    (12, 8, 7, 0, 35.5)], 'CT', cut=.45)
        for side, torso in ((-1, 'LT'), (1, 'RT')):
            forward(g, [(-8, 5, 10, side*8, 37), (5, 4, 7, side*8, 36)], torso, 'edge', .4)
        g.pivots['HD'] = (0, 5, 41)
        forward(g, [(1, 9, 5, 0, 41.5), (10, 6, 4, 0, 38.5),
                    (13, 3, 2, 0, 37)], 'HD', cut=.4)
        for side in (-1, 1):
            points = [(side*.4, 2, 43.9), (side*3.3, 2, 43.9),
                      (side*2, 9.5, 40.8), (side*.4, 9.5, 40.8)]
            panel(g, list(reversed(points)) if side == -1 else points, 'HD', 'glass')
    elif style == 'medium':
        # Upright, angular general-purpose frame with a separate helmet and tapered waist.
        upright(g, [(29, 12, 12, 0, 0), (38, 18, 15, 0, 0),
                    (45, 16, 12, 0, 0)], 'CT', cut=.45)
        for side, torso in ((-1, 'LT'), (1, 'RT')):
            upright(g, [(31, 6, 10, side*9, 0), (43, 8, 14, side*9, 0),
                        (45, 6, 12, side*9, 0)], torso, 'edge', .4)
        g.pivots['HD'] = (0, 3, 46)
        upright(g, [(43, 9, 8, 0, 3), (47, 9, 8, 0, 3),
                    (49, 6, 6, 0, 2)], 'HD', cut=.5)
        panel(g, [(-3, 7.05, 47), (3, 7.05, 47), (2.5, 7.05, 45), (-2.5, 7.05, 45)], 'HD', 'glass')
        panel(g, [(-3, 7.54, 38), (3, 7.54, 38), (0, 6.85, 34.8)], 'CT', 'metal')
    elif style == 'heavy':
        # Broad Warhammer/Archer-like shoulders around a low inset cockpit, with a sloped breastplate.
        forward(g, [(-10, 19, 13, 0, 37), (7, 19, 14, 0, 38),
                    (12, 14, 12, 0, 36.5)], 'CT', cut=.25)
        for side, torso in ((-1, 'LT'), (1, 'RT')):
            upright(g, [(31, 7, 14, side*10, -1), (44.5, 11, 19, side*10, -1),
                        (47, 9, 15, side*10, -1)], torso, 'paint', .25)
        g.pivots['HD'] = (0, 7, 44.5)
        g.box((0, 7, 44.5), (9, 8, 8), 'HD', 'edge', .4, .75)
        panel(g, [(-3, 11.05, 45.8), (3, 11.05, 45.8), (3, 11.05, 43.5),
                  (-3, 11.05, 43.5)], 'HD', 'glass')
    else:
        g.box((0, 0, 37), (16, 17, 15), 'CT', 'paint', .4, .85)
        for side, torso in ((-1, 'LT'), (1, 'RT')):
            g.box((side*9, 0, 37), (8, 15, 13), torso, 'edge', .3)
        g.box((0, 6, 45), (9, 9, 8), 'HD', 'paint', .4, .75)
        g.box((0, 10.6, 45), (6, .5, 2.6), 'HD', 'glass')


def fallback_body(topology, style=None):
    g = Geometry(modular=True)
    g.joint('pelvis', (0, 0, 29))
    g.joint('CT', (0, 0, 29), 'pelvis')
    g.box((0, 0, 28), (16, 10, 6), 'pelvis', 'metal')
    for side, torso in ((-1, 'LT'), (1, 'RT')):
        g.joint(torso, (side*9, 0, 37), 'CT')
    g.joint('HD', (0, 6, 45), 'CT')
    fallback_hull(g, style)
    legs = {'LL': (-9, 0), 'RL': (9, 0)}
    if topology == 'tripod':
        legs = {'LL': (-12, -7), 'RL': (12, -7), 'CL': (0, 11)}
    elif topology == 'quad':
        legs = {'FLL': (-14, 10), 'FRL': (14, 10), 'RLL': (-14, -10), 'RRL': (14, -10)}
    for leg, (x, y) in legs.items():
        g.joint(leg, (x, y, 29), 'pelvis')
        knee_y = y-8 if style == 'light' else y-2
        thigh, shin, sole = (5.4, 4.5, 7) if style == 'light' else (7, 7, 9)
        g.joint(leg+'-shin', (x*1.12, knee_y, 16), leg)
        g.joint(leg+'-foot', (x*1.2, y, 3), leg+'-shin')
        g.beam((x, y, 29), (x*1.12, knee_y, 17), thigh, thigh+1, leg, 'edge')
        g.beam((x*1.12, knee_y, 16), (x*1.2, y, 4), shin, shin+2, leg+'-shin', 'paint', taper=.75)
        g.box((x*1.2, y+3, 2), (sole, 13, 4), leg+'-foot', 'paint', .25)
    if topology != 'quad':
        for side, arm in ((-1, 'LA'), (1, 'RA')):
            g.joint(arm, (side*17, 0, 40), 'CT')
            g.joint(arm+'-forearm', (side*20, 1, 31), arm)
            if style == 'light':
                forward(g, [(-4, 7, 6, side*17, 40), (4, 6, 4, side*17, 39)], arm, cut=.4)
            elif style in ('medium', 'heavy'):
                depth = 16 if style == 'heavy' else 10
                upright(g, [(36, 8, depth-2, side*17, 0), (44, 10, depth, side*17, 0),
                            (46 if style == 'heavy' else 45, 8, depth-2, side*17, 0)], arm, cut=.4)
            else:
                g.box((side*17, 0, 40), (9, 10, 9), arm, 'paint', .35)
            g.beam((side*17, 0, 38), (side*20, 1, 31), 5, 6, arm, 'metal')
            for part in ('forearm', 'wrist', 'hand', 'elbow'):
                g.joint(arm+'@'+part, (side*20, 1, 31), arm if part == 'elbow' else arm+'-forearm')
            if style == 'light':
                forward(g, [(-1, 5, 7, side*20, 28), (8, 5, 5, side*20, 28)], arm+'@forearm', cut=.4)
            else:
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
    hybrid = {**recipes[0], 'id': 'fallback-airmek', 'form': 'airmek', 'sockets': dict(recipes[0]['sockets'])}
    hybrid['sockets'].update({'HD': [42, 12, 42], 'CT': [42, 2, 32],
                              'LT': [30, 38, 36], 'RT': [54, 38, 36]})
    recipes.append(hybrid)
    authored = []
    for recipe in recipes:
        for weight in FALLBACK_PROPORTIONS:
            variant = {**recipe, 'id': recipe['id']+'-'+weight, 'weightProfile': weight,
                       'sockets': dict(recipe['sockets'])}
            if recipe.get('form') != 'airmek' and weight in ('light', 'medium', 'heavy'):
                # Body-local mounting surfaces follow the new hull, not the old box silhouette.
                if weight == 'light':
                    front = {'HD': [42, 23, 37.5], 'CT': [42, 24, 34],
                             'LT': [34, 31, 36], 'RT': [50, 31, 36]}
                    rear_y = {'HD': 1, 'CT': -9, 'LT': -8, 'RT': -8}
                    lamp = [34, 35, 41]
                    for location, pixel in variant['sockets'].items():
                        if location in ('LL', 'RL', 'CL', 'FLL', 'FRL', 'RLL', 'RRL'):
                            variant['sockets'][location] = [pixel[0], pixel[1]+4, pixel[2]]
                elif weight == 'medium':
                    front = {'HD': [42, 28.8, 46], 'CT': [42, 28.4, 38],
                             'LT': [33, 29.6, 38], 'RT': [51, 29.6, 38]}
                    rear_y = {'HD': -1, 'CT': -8, 'LT': -7, 'RT': -7}
                    lamp = [33, 36, 45]
                else:
                    front = {'HD': [42, 24.8, 44.5], 'CT': [42, 24, 36.5],
                             'LT': [32, 28, 39], 'RT': [52, 28, 39]}
                    rear_y = {'HD': 3, 'CT': -10, 'LT': -10, 'RT': -10}
                    lamp = [32, 37, 47]
                variant['sockets'].update(front)
                variant['rearSockets'] = {location: [pixel[0], 36-rear_y[location], pixel[2]]
                                          for location, pixel in front.items()}
                variant['searchlightSocket'] = {'location': 'LT', 'position': lamp}
            authored.append(variant)
    return authored


def air_mek_body():
    """Reusable fighter fuselage with articulated arms and digitigrade legs; no baked loadout."""
    g = fallback_body('biped')[0]
    g.faces = [(tri, node, material) for tri, node, material in g.faces if node not in ('CT', 'LT', 'RT', 'HD')]
    g.pivots['HD'] = (0, 23, 40)
    forward(g, [(-30, 15, 10, 0, 36), (-10, 25, 13, 0, 36),
                (14, 21, 13, 0, 35), (41, 3, 4, 0, 29)], 'CT', cut=.45)
    forward(g, [(12, 11, 5, 0, 42), (24, 8, 5, 0, 39), (29, 3, 2, 0, 35)], 'HD', 'glass', .4)
    for side, torso in ((-1, 'LT'), (1, 'RT')):
        g.box((side*12, -17, 35), (11, 26, 13), torso, 'edge', .4)
        wing = 'wing'+str(side)
        g.joint(wing, (side*11, -6, 38), 'CT')
        g.prism([(side*10, 3), (side*44, -17), (side*41, -30), (side*10, -20)], 37, 40, wing, 'paint')
        g.beam((side*12, -23, 35), (side*12, -31, 35), 9, 9, torso, 'metal', 6)
        g.beam((side*12, -30, 35), (side*12, -31.1, 35), 6, 6, torso, 'dark', 6)
        g.emitter((side*12, -31.2, 35), (0, -1, 0), torso, 'exhaust', 'exhaust')
    g.box((0, -22, 47), (2, 17, 17), 'CT', 'edge', .6)
    # Sweep the knees backwards while keeping the feet underneath the hull.
    def leg_point(p):
        x, y, z = p
        offset = -16 * max(0, 1-abs(z-16)/16)
        return x, y+offset, z
    g.faces = [(tuple(leg_point(p) for p in tri) if node.startswith(('LL', 'RL')) else tri, node, material)
               for tri, node, material in g.faces]
    g.pivots = {node: leg_point(p) if node.startswith(('LL', 'RL')) else p for node, p in g.pivots.items()}
    return g


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
        weight = recipe.get('weightProfile')
        body = fallback_body(recipe['topology'], weight)[0] if 'topology' in recipe else build_chassis(recipe, modular=True)
        if recipe.get('form') == 'airmek':
            body = air_mek_body()
        if weight:
            body = author_fallback(body, weight)
        split_torso_locations(body)
        vents = finish_vents(body, recipe.get('ventSpares', 3)) if 'topology' not in recipe and recipe.get('form') != 'airmek' else []
        for location in ('HD', 'CT', 'LT', 'RT'):
            if not any(node == location for _, node, _ in body.faces):
                raise ValueError(recipe['id']+': no drawable '+location+' surface')
        # Existing is not enough. A chassis can carry an LT shoulder pod while its whole torso skin
        # stays labelled CT, which is the joined torso the guide forbids: the side blows off and the
        # armour over it remains. Catch it by reach - a centre section may not span the torso's width.
        torso = [tri for tri, node, _ in body.faces if node in ('CT', 'LT', 'RT')]
        half_width = max(abs(point[0]) for tri in torso for point in tri)
        centre = [tri for tri, node, _ in body.faces if node == 'CT']
        reach = max(abs(point[0]) for tri in centre for point in tri)
        if reach > half_width*.75:
            raise ValueError('%s: centre torso reaches %.1f of a %.1f half-width; the torso is joined'
                             % (recipe['id'], reach, half_width))
        hardpoints, mounts = [], []

        def mount(identifier, location, pixel, *, rear=False, family='', form='', bay=False, node=None):
            if node is None:
                node = location+'-forearm' if location in ('LA', 'RA') and form != 'elbow' else location
                node = recipe.get('socketNodes', {}).get(location+':'+family, node)
            aim = (0, -1, 0) if rear else recipe.get('socketAim', {}).get(location+':'+family,
                                               recipe.get('socketAim', {}).get(location, (0, 1, 0)))
            size = recipe.get('mountAreas', {}).get(location, {})
            width = size.get('width', 6 if location == 'HD' else 12 if location in ('CT', 'LT', 'RT') else 10)
            height = size.get('height', 6 if location == 'HD' else 14 if location in ('CT', 'LT', 'RT') else 10)
            if bay:
                height = recipe.get('missileBayHeight', height)
                width = recipe.get('missileBayWidth', 12)
            if weight:
                width *= FALLBACK_PROPORTIONS[weight][0]
                height *= FALLBACK_PROPORTIONS[weight][3]
            # A body grown to its class's height keeps its recipe in the units it was authored in.
            grown = recipe.get('bodyScale', 1)
            position = fallback_point(point(pixel), weight) if weight else tuple(v*grown for v in point(pixel))
            width *= grown
            height *= grown
            hardpoints.append({'id': identifier, 'location': location, 'side': 'rear' if rear else 'front',
                               'node': node, 'position': sub(position, body.pivots[node]),
                               'rotation': aim_rotation(aim), 'size': [width, 6, height],
                               'minScale': .4, 'maxScale': 2 if family == 'lamp' else 1.5,
                               'roles': ['misc'] if family == 'lamp' else ['weapon', 'physical', 'misc']})
            settings = {'hardpoint': identifier, 'family': family, 'form': form, 'bay': bay,
                        'scale': recipe['weaponScale']*grown*(recipe.get('missileScale', 1) if bay else 1)}
            # A location can carry its weapons larger than the chassis's norm, as the Panther's right-arm cannon is.
            settings['scale'] *= recipe.get('locationScale', {}).get(location, 1)
            style = recipe.get('protrusion', {}).get(location+':'+family, recipe.get('protrusion', {}).get(location))
            if style:
                settings['style'] = style
            if location in recipe.get('hangingMounts', []) and not rear and not family:
                # The socket marks an underside the weapon hangs from, like a Locust's guns under its gun pods.
                # A socket kept for one family of weapon sits where the recipe puts it and does not hang.
                settings['hang'] = True
            if location in recipe.get('sharedFaces', {}):
                # This location's weapons pack onto another location's face, beside that location's own.
                settings['area'] = recipe['sharedFaces'][location]
            if family == 'jump-jet':
                # Jump jets can be drawn smaller than the chassis's weapons, so several fit one torso back.
                settings['scale'] *= recipe.get('jumpJetScale', 1)
            if location in recipe.get('stackRows', []) or location+':'+family in recipe.get('stackRows', []):
                # Weapons sharing this socket sit side by side in rows, centred on the face, not one above another.
                # An entry names a whole location ("LT") or one family of weapon at it ("LT:jump-jet").
                settings['stack'] = 'rows'
            if family == 'ppc' and recipe.get('barrelLength'):
                settings['length'] = recipe['barrelLength']*recipe.get('bodyScale', 1)
            for override in recipe.get('weaponOverrides', []):
                if override.get('location', location) == location and override.get('family') == family:
                    if 'length' in override:
                        settings['length'] = override['length']*recipe['weaponScale']*recipe.get('bodyScale', 1)
            if bay and missile_style_for(location, recipe).startswith('drum-'):
                # The drum profiles are named for their length: drum-short, drum-medium, drum-long.
                settings['profile'] = missile_style_for(location, recipe)
            elif bay:
                settings['profile'] = 'vertical-slope' if recipe.get('missileSlope') else 'columns-4'
            if bay and recipe.get('missileBayStand'):
                # The launchers stand on the socket instead of being centred on it, so each rests on the surface.
                settings['stand'] = True
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
            exhaust = recipe.get('exhaustSockets', {}).get(location, [rear[0], rear[1], min(rear[2], 29)])
            mount(location+'-exhaust', location, exhaust, family='jump-jet')
            if recipe.get('barrelLength'):
                mount(location+'-ppc', location, pixel, family='ppc')
        for location in ('LA', 'RA'):
            if location not in recipe['sockets']:
                continue
            forms = dict(recipe.get('armSockets', {}).get(location, {}))
            # A refit without lower-arm actuators must attach at the remaining elbow, not a removed hand.
            # Keep stock hand/family-bank placement unchanged when no special hand socket was authored.
            forms.setdefault('wrist', recipe['sockets'][location])
            # Explicit fallback arm sockets already include the elbow; avoid scaling a transformed pivot twice.
            elbow = body.pivots[location+'-forearm']
            # The pivot is already in the grown body; a socket is written in the recipe's own units.
            grown = recipe.get('bodyScale', 1)
            forms.setdefault('elbow', [42+elbow[0]/grown, 36-elbow[1]/grown, elbow[2]/grown])
            for form, pixel in forms.items():
                mount(location+'-'+form, location, pixel, form=form)
                # Only a hand can hold a gun. A weapon with no held shape of its own keeps its usual one.
                if form == 'hand' and location in recipe.get('heldWeapons', []):
                    mounts[-1]['profile'] = 'held'
                    # A held weapon's barrel fits the front face of the gun body the chassis generated for this
                    # arm, not the centre of the fist: this is the step from the hand socket to that face.
                    hand, face = tuple(v*recipe.get('bodyScale', 1) for v in point(pixel)), body.held_fronts[location]
                    mounts[-1]['heldOffset'] = [round(face[i]-hand[i], 3) for i in range(3)]
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
                mounts.append({**settings, 'family': 'ppc', 'length': recipe['barrelLength']*recipe.get('bodyScale', 1)})
            for override in recipe.get('weaponOverrides', []):
                if override.get('location') == hardpoint['location'] and 'length' in override:
                    mounts.append({**settings, 'family': override['family'],
                                   'length': override['length']*recipe['weaponScale']*recipe.get('bodyScale', 1)})
        # A chassis rule draws one weapon with another's art at a spot of its own, whichever location carries it.
        # The runtime tries the rules before any ordinary socket; a rule's placement is never offered to other
        # weapons, so it stays out of the mount list.
        rules = []
        for index, rule in enumerate(recipe.get('equipmentRules', [])):
            mount('rule-'+str(index), rule['location'], rule['socket'], family=rule['family'], node=rule['node'])
            hardpoints[-1]['size'] = [rule['size'][0], 6, rule['size'][1]]
            placement = mounts.pop()
            placement['profile'] = rule['profile']
            placement['rule'] = True
            rules.append({'match': rule['match'], 'exclude': rule.get('exclude', ''), 'drawAs': rule['drawAs'],
                          'placement': placement})
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
        joints.update({node: node for node in body.pivots if node.startswith('wing')})
        for location in ('CL', 'FLL', 'FRL', 'RLL', 'RRL'):
            if location in body.pivots:
                joints[location] = location
                joints[location+'Shin'] = location+'-shin'
                if location+'-foot' in body.pivots:
                    joints[location+'Foot'] = location+'-foot'
        key = 'bodies/'+recipe['id']
        topology = recipe.get('topology', 'biped')
        assets[key] = export_asset(body, output, key, 'body', 'mek-'+topology, topology+'-v1', joints, hardpoints,
                                   leg_bends=recipe.get('legBends'))
        descriptor = {
            'schema': 2, 'kind': 'mek', 'body': 'units/modular/'+key+'.json',
            'equipment': 'units/modular/equipment.json', 'mounts': mounts,
            'configuration': topology,
        }
        if rules:
            descriptor['rules'] = rules
        if vents:
            descriptor['vents'] = vents
            if 'ventDefaultSides' in recipe:
                # The faces that keep the author's vents on a variant with no slotted heat sinks in its torso.
                descriptor['ventDefaultSides'] = recipe['ventDefaultSides']
        write_json(output / ('meks/'+recipe['id']+'.json'), descriptor)
    return assets
