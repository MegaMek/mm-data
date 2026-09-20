"""Small, reusable fallback bodies. Gameplay type selection and live loadouts remain in Java.

These are deliberately generic family silhouettes, with rigid parts and empty attachment areas.
They are not a catalog of named variants or finished production artwork.
"""
from math import cos, sin, pi

from unit_model_geometry import Geometry, sub
from unit_mek_chassis import forward, upright
from unit_mek_models import aim_rotation


def landing_support(g, node, x, y, top, width, pad, thickness=4, *, stowed_offset):
    """Vertical lower shaft, with a separate rigid pad. The deployment node may also own an angled upper brace."""
    shaft, foot = node+'Shaft', node+'Foot'
    bottom = thickness/2
    g.joint(shaft, (x, y, top), node)
    g.joint(foot, (x, y, bottom), node)
    g.box((x, y, (top+bottom)/2), (width, width, top-bottom), shaft, 'metal')
    g.box((x, y, bottom), (*pad, thickness), foot, 'paint', .3)
    g.landing_supports.append({'id': node, 'node': node, 'shaft': shaft, 'foot': foot,
                               'length': top-bottom, 'contact': [0, 0, -bottom], 'stowedOffset': list(stowed_offset)})


def vehicle(mode):
    g = Geometry(modular=True)
    g.joint('hull', (0, 0, 12))
    forward(g, [(-25, 28, 12, 0, 11), (15, 28, 12, 0, 11), (25, 22, 6, 0, 10)], 'hull')
    if mode in ('tracked', 'rail', 'wheeled'):
        for side in (-1, 1):
            node = 'leftDrive' if side < 0 else 'rightDrive'
            g.joint(node, (side*16, 0, 6), 'hull')
            if mode == 'tracked':
                g.box((side*16, 0, 6), (8, 52, 11), node, 'dark', .5)
                g.box((side*20.1, 0, 6), (.3, 42, 5), node, 'metal')
            else:
                for y in (-18, -6, 6, 18):
                    wheel = f'wheel-{side}-{y}'
                    g.joint(wheel, (side*16.5, y, 5), node)
                    g.beam((side*14, y, 5), (side*19, y, 5), 9, 9, wheel, 'dark', 6)
    else:
        g.box((0, 0, 4), (39, 55, 7), 'hull', 'dark', .7)
        if mode == 'wige':
            for side in (-1, 1):
                g.prism([(side*11, -17), (side*32, -22), (side*29, 9), (side*12, 18)], 8, 10, 'hull')
    g.box((0, 15, 17.2), (12, 5, 1), 'hull', 'glass')
    for key, y, width in (('turret', -5, 19), ('turret2', 15, 11)):
        g.joint(key, (0, y, 18), 'hull')
        g.box((0, y, 21), (width, width, 8), key, 'paint', .65, .7)
    return g


def rotorcraft(airship=False):
    g = Geometry(modular=True)
    g.joint('hull', (0, 0, 15))
    if airship:
        forward(g, [(-34, 3, 4, 0, 26), (-24, 24, 25, 0, 26), (16, 30, 29, 0, 26),
                    (33, 4, 5, 0, 26)], 'hull', cut=.6)
        g.box((0, 4, 7), (12, 23, 10), 'hull', 'paint', .4)
        g.box((0, 15.6, 8), (8, .5, 4), 'hull', 'glass')
        for side in (-1, 1):
            g.box((side*17, -17, 19), (19, 7, 2), 'hull', 'edge')
    else:
        forward(g, [(-15, 8, 9, 0, 15), (-2, 19, 17, 0, 15), (17, 16, 12, 0, 13),
                    (23, 7, 6, 0, 10)], 'hull', cut=.45)
        forward(g, [(6, 15, 8, 0, 19), (17, 12, 6, 0, 15)], 'hull', 'glass', .4)
        g.beam((0, -12, 15), (0, -34, 17), 7, 7, 'hull', 'paint', 4, .35)
        g.box((0, -30, 18), (20, 6, 2), 'hull', 'edge')
        g.joint('rotor', (0, -1, 27), 'hull')
        g.beam((0, -1, 20), (0, -1, 28), 3, 3, 'hull', 'metal')
        for angle in (0, pi/2):
            g.beam((-31*cos(angle), -1-31*sin(angle), 28), (31*cos(angle), -1+31*sin(angle), 28),
                   3, 1, 'rotor', 'dark')
    for side in (-1, 1):
        g.joint('gear'+str(side), (side*9, 0, 8), 'hull')
        g.beam((side*9, -12, 2), (side*9, 15, 2), 2, 3, 'gear'+str(side), 'metal')
        g.beam((side*9, 0, 3), (side*7, 0, 12), 2, 2, 'gear'+str(side), 'metal')
    return g


def aircraft(transport=False):
    g = Geometry(modular=True)
    g.joint('hull', (0, 0, 10))
    if transport:
        forward(g, [(-30, 26, 17, 0, 13), (12, 30, 19, 0, 13), (32, 15, 13, 0, 11)], 'hull')
    else:
        forward(g, [(-27, 12, 9, 0, 10), (0, 17, 12, 0, 11), (29, 2, 3, 0, 8)], 'hull', cut=.45)
    g.box((0, 16, 18 if transport else 15), (12 if transport else 8, 12, 4), 'hull', 'glass', .6)
    for side in (-1, 1):
        g.joint('wing'+str(side), (side*8, -4, 10), 'hull')
        g.prism([(side*7, 14), (side*33, -14), (side*32, -24), (side*7, -17)], 8, 11, 'wing'+str(side))
        g.joint('engine'+str(side), (side*11, -21, 10), 'hull')
        g.beam((side*11, -13, 10), (side*11, -30, 10), 10, 10, 'engine'+str(side), 'edge', 6)
        g.beam((side*11, -29, 10), (side*11, -30.2, 10), 7, 7, 'engine'+str(side), 'dark', 6)
        g.emitter((side*11, -30.3, 10), (0, -1, 0), 'engine'+str(side), 'exhaust', 'exhaust')
        if not transport:
            g.joint('gear'+str(side), (side*9, 0, 8), 'hull')
            g.box((side*9, 2, 3), (3, 12, 6), 'gear'+str(side), 'metal')
        g.prism([(side*5, -13), (side*6, -27), (side*15, -24)], 11, 16, 'hull', 'edge', .4)
    if transport:
        for index, (x, y) in enumerate(((-12, -10), (12, -10), (0, 20))):
            node = 'gear-'+str(index)
            g.joint(node, (x, y, 8), 'hull')
            landing_support(g, node, x, y, 8, 3, (7, 12), 2, stowed_offset=(-x*.5, -y*.15, 10))
    return g


def flight_fighter():
    """A small formation member; ten members stay below the bare-formation budget."""
    g = Geometry(modular=True)
    g.joint('hull', (0, 0, 10))
    forward(g, [(-26, 13, 9, 0, 10), (2, 15, 10, 0, 10), (29, 2, 3, 0, 8)], 'hull')
    g.box((0, 11, 15), (7, 12, 3), 'hull', 'glass', .4)
    for side in (-1, 1):
        g.joint('wing'+str(side), (side*7, -4, 10), 'hull')
        g.prism([(side*6, 10), (side*30, -16), (side*29, -23), (side*6, -15)], 8, 10, 'wing'+str(side))
        g.emitter((side*4, -26, 10), (0, -1, 0), 'hull', 'exhaust', 'exhaust')
    return g


def spheroid(small=False):
    g = Geometry(modular=True)
    g.joint('hull', (0, 0, 30))
    rings = [(7, 12), (13, 25), (27, 33), (44, 30), (58, 19), (64, 6)]
    g.loft([[(radius*cos(2*pi*i/12), radius*sin(2*pi*i/12), z) for i in range(12)]
            for z, radius in rings], 'hull')
    g.box((0, 11, 58), (15, 10, 7), 'hull', 'edge', .45)
    g.box((0, 16.1, 58), (11, .4, 3), 'hull', 'glass')
    for angle in (pi/4, 3*pi/4, 5*pi/4, 7*pi/4):
        x, y = 27*cos(angle), 27*sin(angle)
        node = 'gear'+str(round(angle, 2))
        g.joint(node, (x, y, 14), 'hull')
        g.beam((x*.65, y*.65, 15), (x, y, 10), 7, 7, node, 'metal')
        landing_support(g, node, x, y, 10, 5, (13, 13), stowed_offset=(-x*.35, -y*.35, 23))
        g.beam((x*.52, y*.52, 9), (x*.52, y*.52, 6), 9, 9, 'hull', 'dark', 6)
        g.emitter((x*.52, y*.52, 5.8), (0, 0, -1), 'hull', 'exhaust', 'exhaust')
    if small:
        scale_geometry(g, .65)
    return g


def capital(kind):
    g = Geometry(modular=True)
    g.joint('hull', (0, 0, 15))
    if kind == 'station':
        for i in range(12):
            a, b = 2*pi*i/12, 2*pi*(i+1)/12
            g.prism([(31*cos(a), 31*sin(a)), (31*cos(b), 31*sin(b)),
                     (24*cos(b), 24*sin(b)), (24*cos(a), 24*sin(a))], 10, 16, 'hull', 'edge')
        g.beam((0, 0, 4), (0, 0, 29), 17, 17, 'hull', 'paint', 8)
        for side in (-1, 1):
            g.box((side*16, 0, 13), (25, 6, 4), 'hull', 'paint')
            g.box((0, side*16, 13), (6, 25, 4), 'hull', 'paint')
    else:
        width = 20 if kind == 'warship' else 10
        forward(g, [(-37, width*.7, 10, 0, 14), (-22, width, 17, 0, 14),
                    (19, width, 16, 0, 14), (39, width*.4, 9, 0, 14)], 'hull', cut=.5)
        g.box((0, 10, 25), (12, 19, 6), 'hull', 'edge', .4)
        if kind == 'warship':
            for side in (-1, 1):
                g.box((side*16, -9, 13), (13, 37, 13), 'hull', 'paint', .45)
        else:
            for side in (-1, 1):
                g.box((side*18, -24, 15), (30, 17, 1), 'hull', 'dark')
                g.beam((0, -24, 15), (side*32, -24, 15), 1, 2, 'hull', 'metal')
        g.emitter((0, -38, 14), (0, -1, 0), 'hull', 'exhaust', 'exhaust')
    return g


def naval(kind):
    g = Geometry(modular=True)
    g.joint('hull', (0, 0, 8))
    if kind == 'submarine':
        forward(g, [(-32, 2, 3, 0, 8), (-22, 15, 15, 0, 8), (21, 17, 15, 0, 8), (34, 3, 4, 0, 8)],
                'hull', cut=.7)
        g.box((0, 3, 18), (6, 14, 10), 'hull', 'edge', .4)
        g.beam((0, 7, 22), (0, 7, 29), 1, 1, 'hull', 'metal')
        g.box((0, -25, 9), (28, 6, 2), 'hull', 'edge')
    else:
        forward(g, [(-29, 18, 9, 0, 6), (9, 23, 12, 0, 7), (34, 2, 7, 0, 7)], 'hull', cut=.3)
        g.box((0, -8, 16), (13, 21, 10), 'hull', 'paint', .3)
        g.box((0, -1, 22), (11, 8, 5), 'hull', 'edge')
        g.box((0, 3.1, 22), (8, .4, 2), 'hull', 'glass')
        if kind == 'hydrofoil':
            for side in (-1, 1):
                g.beam((side*8, 10, 6), (side*15, 10, 0), 2, 3, 'hull', 'metal')
                g.box((side*15, 10, 0), (10, 12, 1), 'hull', 'metal')
        for name, y in (('turret', 17), ('turret2', -23)):
            g.joint(name, (0, y, 12), 'hull')
            g.box((0, y, 15), (12, 12, 6), name, 'edge', .4)
    # The origin is the waterline/depth supplied by the game, not the keel.
    waterline = 10 if kind == 'submarine' else 7
    g.faces = [(tuple((p[0], p[1], p[2]-waterline) for p in tri), node, material)
               for tri, node, material in g.faces]
    g.pivots = {node: (p[0], p[1], p[2]-waterline) for node, p in g.pivots.items()}
    return g


def proto(quad=False):
    g = Geometry(modular=True)
    g.joint('hull', (0, 0, 18))
    g.joint('head', (0, 3, 31), 'hull')
    upright(g, [(17, 10, 8, 0, 0), (26, 17, 12, 0, 0), (30, 12, 10, 0, 1)], 'hull', cut=.4)
    g.box((0, 3, 32), (7, 8, 7), 'head', 'paint', .6)
    g.box((0, 7.1, 33), (5, .4, 2), 'head', 'glass')
    for i, (x, y) in enumerate(((-8, 8), (8, 8), (-8, -8), (8, -8)) if quad else ((-5, 0), (5, 0))):
        leg = 'leg'+str(i)
        g.joint(leg, (x, y, 18), 'hull')
        g.joint(leg+'Shin', (x*1.1, y-3, 10), leg)
        g.beam((x, y, 18), (x*1.1, y-3, 10), 5, 6, leg, 'metal')
        g.beam((x*1.1, y-3, 10), (x*1.2, y+1, 3), 6, 6, leg+'Shin', 'paint')
        g.box((x*1.2, y+3, 2), (7, 10, 4), leg+'Shin', 'edge')
    for side in (-1, 1):
        arm = 'arm'+str(side)
        g.joint(arm, (side*11, 0, 26), 'hull')
        g.box((side*11, 0, 26), (7, 8, 8), arm, 'paint', .4)
        g.beam((side*11, 0, 25), (side*13, 3, 19), 4, 5, arm, 'metal')
    return g


def static_body(kind):
    g = Geometry(modular=True)
    g.joint('hull', (0, 0, 9))
    if kind == 'missile':
        forward(g, [(-25, 6, 6, 0, 8), (17, 8, 8, 0, 8), (28, 1, 1, 0, 8)], 'hull')
        g.box((0, -16, 8), (24, 9, 2), 'hull', 'edge')
        g.box((0, -16, 8), (2, 9, 17), 'hull', 'edge')
        g.emitter((0, -25, 8), (0, -1, 0), 'hull', 'exhaust', 'exhaust')
    elif kind == 'escape-pod':
        upright(g, [(0, 13, 17, 0, 0), (11, 17, 22, 0, 0), (23, 9, 12, 0, 1)], 'hull', cut=.6)
        g.box((0, 6.5, 20), (6, .4, 3), 'hull', 'glass')
    else:
        g.box((0, 0, 4), (36, 31, 8), 'hull', 'edge', .3)
        g.joint('turret', (0, 0, 10), 'hull')
        g.box((0, 0, 15), (23, 23, 15 if kind == 'structure' else 9), 'turret', 'paint', .45)
    return g


def scale_geometry(g, scale):
    g.faces = [(tuple(tuple(value*scale for value in point) for point in tri), node, material)
               for tri, node, material in g.faces]
    g.pivots = {node: tuple(value*scale for value in point) for node, point in g.pivots.items()}
    for emitter in g.emitters:
        emitter['position'] = tuple(value*scale for value in emitter['position'])
    for support in g.landing_supports:
        support['length'] *= scale
        support['contact'] = [value*scale for value in support['contact']]
        support['stowedOffset'] = [value*scale for value in support['stowedOffset']]


def build_families(output, export_asset, write_json):
    bodies = {mode: ('vehicle', vehicle(mode)) for mode in ('tracked', 'wheeled', 'hover', 'wige', 'rail')}
    bodies.update({name: ('aircraft', geometry) for name, geometry in (
        ('vtol', rotorcraft()), ('airship', rotorcraft(True)), ('fighter', aircraft()), ('flight-fighter', flight_fighter()),
        ('aerodyne', aircraft(True)), ('spheroid', spheroid()), ('small-spheroid', spheroid(True)),
        ('jumpship', capital('jumpship')), ('warship', capital('warship')), ('station', capital('station')))})
    bodies.update({kind: ('naval', naval(kind)) for kind in ('naval', 'hydrofoil', 'submarine')})
    glider = proto()
    for side in (-1, 1):
        glider.prism([(side*6, 8), (side*25, -9), (side*23, -16), (side*6, -8)], 24, 26, 'hull', 'edge')
    bodies.update({'proto': ('proto', proto()), 'quad-proto': ('proto', proto(True)), 'glider-proto': ('proto', glider)})
    bodies.update({kind: ('static', static_body(kind)) for kind in ('emplacement', 'structure', 'escape-pod', 'missile')})
    assets = {}
    for name, (family, g) in bodies.items():
        xs = [p[0] for tri, _, _ in g.faces for p in tri]
        ys = [p[1] for tri, _, _ in g.faces for p in tri]
        zs = [p[2] for tri, _, _ in g.faces for p in tri]
        x, y, z = max(abs(min(xs)), max(xs)), max(abs(min(ys)), max(ys)), max(zs)
        # Explicit location aliases cover current family abbreviations; '*' retains unknown-location identity.
        locations = {'BD': (0, y*.6, z*.45), 'FR': (0, y, z*.35), 'NOS': (0, y, z*.35),
                     'LS': (-x*.8, 0, z*.4), 'RS': (x*.8, 0, z*.4), 'LWG': (-x*.8, 0, z*.4),
                     'RWG': (x*.8, 0, z*.4), 'RR': (0, -y, z*.4), 'AFT': (0, -y, z*.4),
                     'FLS': (-x*.65, y*.55, z*.4), 'FRS': (x*.65, y*.55, z*.4),
                     'ALS': (-x*.65, -y*.55, z*.4), 'ARS': (x*.65, -y*.55, z*.4),
                     'FRLS': (-x*.65, y*.55, z*.4), 'FRRS': (x*.65, y*.55, z*.4),
                     'RRLS': (-x*.65, -y*.55, z*.4), 'RRRS': (x*.65, -y*.55, z*.4),
                     'LBS': (-x*.8, 0, z*.4), 'RBS': (x*.8, 0, z*.4), 'HULL': (0, 0, z),
                     'FSLG': (0, 0, z), '*': (0, y*.35, z*.65)}
        if family == 'vehicle':
            # Converted QuadVees keep Mek equipment locations. No gameplay locations are reassigned.
            locations.update({'HD': (0, y*.5, z), 'CT': (0, y*.7, z*.5), 'LT': (-x*.5, y*.5, z*.5),
                              'LA': (-x*.9, y*.3, z*.4), 'RA': (x*.9, y*.3, z*.4),
                              'LL': (-x*.65, -y*.6, z*.3), 'RL': (x*.65, -y*.6, z*.3)})
        if family == 'proto':
            locations.update({'HD': (0, 7, 32), 'T': (0, 7, 25), 'MG': (0, 2, 32),
                              'RA': (13, 5, 21), 'LA': (-13, 5, 21), 'L': (5, 4, 12)})
        hardpoints, mounts = [], []
        for location, position in locations.items():
            for rear in (False, True):
                node = 'hull'
                if family == 'proto':
                    node = {'HD': 'head', 'RA': 'arm1', 'LA': 'arm-1'}.get(location, node)
                direction = (0, -1, 0) if rear or location in ('RR', 'AFT', 'ALS', 'ARS', 'RRLS', 'RRRS') else (0, 1, 0)
                if not rear and location in ('LS', 'LWG', 'LBS'):
                    direction = (-1, 0, 0)
                if not rear and location in ('RS', 'RWG', 'RBS'):
                    direction = (1, 0, 0)
                key = location+('-rear' if rear else '-front')
                hardpoints.append({'id': key, 'location': location, 'side': 'rear' if rear else 'front', 'node': node,
                                   'position': sub(position, g.pivots[node]), 'rotation': aim_rotation(direction),
                                   'size': [18, 12, 18], 'minScale': .25, 'maxScale': 2,
                                   'roles': ['weapon', 'physical', 'misc']})
                mounts.append({'hardpoint': key, 'scale': .6 if family == 'proto' else .8})
        for location, node in (('TU', 'turret'), ('RT', 'turret'), ('FT', 'turret2')):
            if node in g.pivots:
                key = location+'-turret'
                hardpoints.append({'id': key, 'location': location, 'side': 'front', 'node': node,
                                   'position': [0, 9, 4], 'rotation': [0, 0, 0, 1], 'size': [18, 12, 10],
                                   'minScale': .25, 'maxScale': 2, 'roles': ['weapon', 'physical', 'misc']})
                mounts.append({'hardpoint': key, 'scale': .8})
        hardpoints.append({'id': 'external-searchlight', 'location': 'HULL' if family == 'aircraft' else 'BD',
                           'side': 'front', 'node': 'hull', 'position': sub((x*.3, y*.2, z*.85), g.pivots['hull']),
                           'rotation': [0, 0, 0, 1], 'size': [8, 8, 8], 'minScale': .4, 'maxScale': 2,
                           'roles': ['misc']})
        mounts.append({'hardpoint': 'external-searchlight', 'family': 'lamp', 'scale': .8})
        joints = {node: node for node in g.pivots}
        key = 'bodies/family-'+name
        assets[key] = export_asset(g, output, key, 'body', family, family+'-v1', joints, hardpoints)
        descriptor = {
            'schema': 2, 'kind': 'family', 'family': family, 'body': 'units/modular/'+key+'.json',
            'equipment': 'units/modular/equipment.json', 'mounts': mounts,
        }
        if family == 'vehicle':
            descriptor['forms'] = {mode: 'units/modular/families/'+target+'.json' for mode, target in (
                ('TRACKED', 'tracked'), ('WHEELED', 'wheeled'), ('HOVER', 'hover'), ('WIGE', 'wige'),
                ('RAIL', 'rail'), ('MAGLEV', 'rail'), ('VTOL', 'vtol'), ('AIRSHIP', 'airship'))}
        elif family == 'proto':
            descriptor['forms'] = {kind: 'units/modular/families/'+kind+'.json'
                                   for kind in ('proto', 'quad-proto', 'glider-proto')}
        write_json(output / ('families/'+name+'.json'), descriptor)
        if name == 'flight-fighter':
            write_json(output / 'families/squadron.json', {**descriptor, 'kind': 'squadron'})
    return assets
