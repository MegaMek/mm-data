"""Shared low-poly figure and transport artwork; formation assembly belongs to the runtime."""
from unit_model_geometry import Geometry, normal


INFANTRY_HEIGHT_SCALE = 1.10
BATTLE_ARMOR_HEIGHT_SCALE = 1.50


def bake_height(geometry, armored=False):
    """Bake component proportions before export, keeping rotating wheels round and grounded."""
    scale = BATTLE_ARMOR_HEIGHT_SCALE if armored else INFANTRY_HEIGHT_SCALE

    def point(value, node):
        return tuple(value) if node.startswith('wheel-') else (value[0], value[1], value[2]*scale)

    geometry.faces = [(tuple(point(vertex, node) for vertex in triangle), node, material)
                      for triangle, node, material in geometry.faces]
    geometry.pivots = {node: point(pivot, node) for node, pivot in geometry.pivots.items()}
    for emitter in geometry.emitters:
        emitter['position'] = point(emitter['position'], emitter['node'])
        emitter['direction'] = normal(point(emitter['direction'], emitter['node']))
    return geometry


def person(pose, armored=False, jump=False, modular=False):
    g = Geometry(modular=modular)
    kneel = pose == 'kneeling'
    advance = pose == 'advancing'
    torso_z = 10 if kneel else 14
    spread = 3.2 if armored else 2.1
    group = lambda role: role if modular else 'soldier'
    if modular:
        g.joint('hips', (0, 0, torso_z-3))
        g.joint('torso', (0, 0, torso_z-3), 'hips')
        g.joint('head', (0, -.8, torso_z+3), 'torso')
    for sign in (-1, 1):
        hip = (sign*spread/2, 0, torso_z-3)
        knee = (sign*spread, 3 if kneel and sign == -1 else -1 if kneel else sign*2 if advance else 0, 4 if kneel else 6)
        foot = (sign*spread, -3 if kneel and sign == 1 else 4 if advance and sign == 1 else 0, 1)
        width = 3.1 if armored else 1.9
        leg = 'leftLeg' if sign == -1 else 'rightLeg'
        if modular:
            g.joint(leg, hip, 'hips')
            g.joint(leg+'Shin', knee, leg)
            g.joint(leg+'Foot', foot, leg+'Shin')
        g.beam(hip, knee, width, width, group(leg), 'paint')
        g.beam(knee, foot, width, width, group(leg+'Shin'), 'edge')
        g.box((foot[0], foot[1]+1, 1), (width, 3.5, 2), group(leg+'Foot'), 'metal')
    g.box((0, 0, torso_z), (7 if armored else 5, 5 if armored else 3.3, 7 if armored else 6),
          group('torso'), 'paint', .3 if armored else 0, .82)
    g.box((0, -.8, torso_z+5), (4.5 if armored else 3.3, 4 if armored else 3.3, 4),
          group('head'), 'paint', .4 if armored else 0, .8)
    g.face([(-1.5, 1.3, torso_z+5.6), (1.5, 1.3, torso_z+5.6),
            (1.5, 1.3, torso_z+4.4), (-1.5, 1.3, torso_z+4.4)],
           group('head'), 'glass' if armored else 'dark')
    for sign in (-1, 1):
        shoulder = (sign*(4 if armored else 3), 0, torso_z+2)
        elbow = (sign*(4.5 if armored else 3.5), 2, torso_z-1)
        hand = (1.5, 3, torso_z-2) if pose == 'standing' else (sign*3, 4, torso_z-2) if advance else (1.5, 5, torso_z+1)
        arm = 'leftArm' if sign == -1 else 'rightArm'
        if modular:
            g.joint(arm, shoulder, 'torso')
            g.joint(arm+'Forearm', elbow, arm)
        g.beam(shoulder, elbow, 3.5 if armored else 2, group=group(arm), material='paint')
        g.beam(elbow, hand, 3 if armored else 1.7, group=group(arm+'Forearm'), material='edge')
    g.box((1.5, 3, torso_z-2) if pose == 'standing' else (1.5, 5, torso_z+.8),
          (2, 3, 8) if pose == 'standing' else (2, 8, 2), group('rightArmForearm'), 'metal')
    if modular and not armored:
        g.emitter((1.5, 3, torso_z-6) if pose == 'standing' else (1.5, 9, torso_z+.8),
                  (0, 0, -1) if pose == 'standing' else (0, 1, 0), 'rightArmForearm', 'muzzle', 'bullet')
    if armored:
        # A compact jump pack / arm cannon follows the generic BA sprite's bulky shoulders.
        g.box((0, -3, torso_z+2), (7, 3, 7), group('torso'), 'edge')
        g.beam((4, 2, torso_z), (4, 8, torso_z), 2.4, 2.4, group('rightArmForearm'), 'metal')
        if modular:
            g.emitter((4, 8, torso_z), (0, 1, 0), 'rightArmForearm', 'muzzle', 'bullet')
            for side in (-1, 1):
                g.emitter((side*2, -3.3, torso_z-1.5), (0, 0, -1), 'torso', 'exhaust', 'exhaust')
    if jump:
        # Preserve the established tapered jump pack and downward exhaust.
        lo = [(-2.3, -1.4, torso_z-4), (0, -4.3, torso_z-4), (2.3, -1.4, torso_z-4)]
        hi = [(x*.8, y, torso_z+2.5) for x, y, _ in lo]
        g.face(list(reversed(lo)), group('torso'), 'dark')
        g.face(hi, group('torso'), 'edge')
        for i in range(3):
            j = (i+1) % 3
            g.face([lo[i], lo[j], hi[j], hi[i]], group('torso'), 'edge')
        if modular:
            g.emitter((0, -2.4, torso_z-4), (0, 0, -1), 'torso', 'exhaust', 'exhaust')
    return g


def infantry_vehicle(kind, modular=False):
    """Small sprite-proportioned transports; +Y is forward, as for the troops."""
    g = Geometry(modular=modular)
    if modular:
        g.joint('vehicle', (0, 0, 0))
        g.joint('boarding', (8, -5, 0) if kind == 'motorized' else (0, -15, 0), 'vehicle')
        g.joint('cabin', (0, -3, 4), 'vehicle')
    if kind == 'motorized':
        g.box((0, 0, 4), (11, 21, 3), 'vehicle', 'paint')
        g.box((0, 6.7, 6.5), (10, 8, 3), 'vehicle', 'paint', taper=.85)
        g.box((0, -5, 6), (8, 3, 4), 'vehicle', 'dark')
        for sign in (-1, 1):
            for y in (-7, 7):
                wheel = f'wheel-{sign}-{y}' if modular else 'vehicle'
                if modular:
                    g.joint(wheel, (sign*6, y, 3.5), 'vehicle')
                g.beam((sign*6-1.3, y, 3.5), (sign*6+1.3, y, 3.5),
                       7.2, group=wheel, material='dark', sides=6)
            g.beam((sign*4.5, -6, 5), (sign*4.5, -6, 12), 1.2, group='vehicle')
        g.beam((-4.5, -6, 12), (4.5, -6, 12), 1.2, group='vehicle')
        windshield = [(-4, 0, 12), (4, 0, 12), (4, 2.5, 8), (-4, 2.5, 8)]
        g.face(windshield, 'vehicle', 'glass')
        g.face(list(reversed(windshield)), 'vehicle', 'glass')
        g.box((0, 11, 4), (12, 1.5, 2), 'vehicle', 'metal')
        for x in (-3.5, 3.5):
            g.face([(x-.8, 10.72, 6.5), (x+.8, 10.72, 6.5),
                    (x+.8, 10.72, 5.5), (x-.8, 10.72, 5.5)], 'vehicle', 'glass')
        return g

    # Shared enclosed APC hull, visibly different from the open motorized jeep.
    g.box((0, 0, 8.5), (13, 25, 9), 'vehicle', 'paint', bevel=.35, taper=.78)
    g.box((0, -1, 13.4), (5, 6, .8), 'vehicle', 'edge')
    for sign in (-1, 1):
        g.face([(sign*.4, 10.08, 12), (sign*3, 10.08, 12),
                (sign*3, 10.68, 10), (sign*.4, 10.68, 10)][::sign], 'vehicle', 'glass')
        x = sign*4
        g.face([(x-.65, 11.96, 6), (x+.65, 11.96, 6),
                (x+.65, 12.2, 5.2), (x-.65, 12.2, 5.2)], 'vehicle', 'glass')
    g.face([(-3, -12.23, 5), (3, -12.23, 5), (3, -10.4, 11), (-3, -10.4, 11)],
           'vehicle', 'metal')
    if kind == 'wheeled':
        for sign in (-1, 1):
            for y in (-8, 0, 8):
                wheel = f'wheel-{sign}-{y}' if modular else 'vehicle'
                if modular:
                    g.joint(wheel, (sign*6.5, y, 3.5), 'vehicle')
                g.beam((sign*6.5-1.3, y, 3.5), (sign*6.5+1.3, y, 3.5),
                       7.2, group=wheel, material='dark', sides=6)
    elif kind == 'tracked':
        profile = [(-10, 0), (10, 0), (13, 3), (10, 6), (-10, 6), (-13, 3)]
        for sign in (-1, 1):
            g.loft([[(x, y, z) for y, z in profile]
                    for x in (sign*7.2-1.7, sign*7.2+1.7)], 'vehicle', 'dark')
            x = sign*8.92
            g.face([(x, -9, 1.5), (x, 9, 1.5), (x, 10.5, 3),
                    (x, 9, 4.5), (x, -9, 4.5), (x, -10.5, 3)][::sign], 'vehicle', 'metal')
    elif kind == 'hover':
        g.box((0, 0, 2), (20, 29, 4), 'vehicle', 'dark', bevel=.5, taper=.9)
        for x in (-4, 4):
            g.beam((x, -11, 6.5), (x, -14, 6.5), 4.5, group='vehicle', material='metal', sides=6)
            g.face([(x-1, -14.02, 5.5), (x+1, -14.02, 5.5),
                    (x+1, -14.02, 7.5), (x-1, -14.02, 7.5)], 'vehicle', 'dark')
    else:
        raise ValueError('Unknown infantry transport '+kind)
    return g


