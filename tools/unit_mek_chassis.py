"""Recognizable bare silhouettes, authored against the repository's sprites and Mek illustrations.

These are chassis anatomy, not equipment or game rules. The variant assembler adds
the actual guns and launchers. +Y faces forward; all dimensions are authoring units.
"""
from unit_model_geometry import Geometry, sub


def section(width, depth, cut=.25):
    a, b = width/2, depth/2
    if not cut:
        return [(-a, -b), (a, -b), (a, b), (-a, b)]
    c = min(a, b)*cut
    return [(-a+c, -b), (a-c, -b), (a, -b+c), (a, b-c),
            (a-c, b), (-a+c, b), (-a, b-c), (-a, -b+c)]


def upright(g, sections, group='CT', material='paint', cut=.25):
    # Sections: z, width, depth, center x, center y. Slopes replace surface greebles.
    g.loft([[(x+u, y+v, z) for u, v in section(w, d, cut)]
            for z, w, d, x, y in sections], group, material)


def forward(g, sections, group='CT', material='paint', cut=.25):
    # Sections: y, width, height, center x, center z; rear to nose.
    g.loft([[(x+u, y, z-v) for u, v in section(w, h, cut)]
            for y, w, h, x, z in sections], group, material)


def panel(g, points, group='CT', material='dark'):
    """A front-facing inset represented by one plane, not a stack of boxes."""
    g.face(points, group, material)


def foot(g, x, y, width, length, group):
    if g.modular:
        parent = group
        group = group.removesuffix('-shin')+'-foot'
        g.joint(group, (x, y-1, 4), parent)
    upright(g, [(0, width, length, x, y), (4, width*.78, length*.68, x, y-1)], group, cut=0)


def toes(g, x, y, group, width=3, length=8):
    if g.modular:
        parent = group
        group = group.removesuffix('-shin')+'-foot'
        g.joint(group, (x, y, 2.3), parent)
    # Two splayed toes create the bird-foot outline with sixteen triangles.
    for side in (-1, 1):
        ring = [(x+side*1.2-width/2, y-1), (x+side*1.2+width/2, y-1),
                (x+side*3.4, y+length)]
        g.prism(ring, 0, 2.3, group, 'paint', .68)


def lofted_face(sections, rear=False):
    """Surface of a torso lofted upward, whose depth changes with height so the face slopes.

    Sections are the (z, width, depth, center x, center y) rows handed to upright().
    """
    rows = sorted(sections)

    def face(z, stand):
        low, high = rows[0], rows[-1]
        for first, second in zip(rows, rows[1:]):
            if first[0] <= z <= second[0]:
                low, high = first, second
                break
        ratio = (z - low[0])/((high[0] - low[0]) or 1)
        depth = low[2] + (high[2] - low[2])*ratio
        middle = low[4] + (high[4] - low[4])*ratio
        return middle - depth/2 - stand if rear else middle + depth/2 + stand
    return face


def capped_face(y, rear=False):
    """Surface of a torso lofted forward, whose front and back are flat caps at a fixed depth."""
    return lambda z, stand: (y - stand) if rear else (y + stand)


def vent(g, face, center_x, half_width, low_z, high_z, rear=False, group='CT'):
    """A cooling vent lying in the armour: a shaded recess behind three lit fins.

    House rule: at most two on the front and two on the back, the back pair on a torso only. The
    panels follow the face rather than sitting at one depth, and must stay inside its flat band,
    since a bevelled section chamfers its corners away.
    """
    low_x, high_x = center_x - half_width, center_x + half_width

    def slat(first_z, second_z, stand, material):
        # Winding reverses on the back so both faces still point outward.
        near, far = (low_x, high_x) if rear else (high_x, low_x)
        g.face([(near, face(first_z, stand), first_z), (far, face(first_z, stand), first_z),
                (far, face(second_z, stand), second_z), (near, face(second_z, stand), second_z)],
               group, material)

    slat(low_z, high_z, .06, 'dark')
    span = high_z - low_z
    for index in range(3):
        base = low_z + span*(.13 + index*.29)
        slat(base, base + span*.22, .16, 'edge')


def held_housing(g, arm):
    """The body of a gun this arm can hold, sized to the arm it is held on.

    Measured from the chassis's own forearm end and hand, never authored per chassis, so any Mek that lists the
    arm in heldWeapons gets one that fits it. It starts flush on the end of the forearm and runs forward far enough
    to cover where the hand was, with a raised deck over its rear and a grip hanging below. It is optional
    anatomy like the hand: the runtime shows it only while that arm holds a gun, and removes the hand instead.
    The weapon's own barrel is fitted to its front face; that face is recorded for the exporter.
    """
    def bounds(node):
        points = [point for triangle, owner, _ in g.faces if owner == node for point in triangle]
        if not points:
            return None
        return [(min(p[axis] for p in points), max(p[axis] for p in points)) for axis in range(3)]

    forearm, hand = bounds(arm+'@forearm'), bounds(arm+'@hand')
    if forearm is None or hand is None:
        raise ValueError(arm+' lists held weapons but has no forearm and hand to hold them')
    front = forearm[1][1]
    # The cross-section of the forearm where it ends, which the gun body matches so the two meet flush.
    end = [point for triangle, owner, _ in g.faces if owner == arm+'@forearm'
           for point in triangle if point[1] > front - .5]
    x0, x1 = min(p[0] for p in end), max(p[0] for p in end)
    z0, z1 = min(p[2] for p in end), max(p[2] for p in end)
    width, height = (x1 - x0)*.95, (z1 - z0)*.85
    middle_x, middle_z = (x0 + x1)/2, (z0 + z1)/2
    depth = max(hand[1][1] - front + .5, height*.65)
    group = arm+'@held'
    g.box((middle_x, front + depth/2, middle_z), (width, depth, height), group, 'paint')
    g.box((middle_x, front + depth*.3, middle_z + height*.59), (width*.7, depth*.55, height*.18), group, 'edge')
    g.box((middle_x, front + depth*.3, middle_z - height*.72), (width*.4, depth*.4, height*.45), group, 'metal')
    # Where the weapon's barrel goes: centred on the front face, a little above its middle like a rifle's bore.
    if not hasattr(g, 'held_fronts'):
        g.held_fronts = {}
    g.held_fronts[arm] = (middle_x, front + depth, middle_z + height*.15)


def split_torso_locations(body, seam=None):
    """Give joined torso shells real side locations without changing their visible silhouette.

    Split once per body and no more. The test cannot be "does an LT face exist", because a shoulder
    or a pod is an LT face and every chassis that has one would skip the split and keep its whole
    torso skin labelled CT - a side torso would then blow off leaving the armour over it intact.
    Splitting twice is just as wrong: the plane comes from the CT shell's own width, so a second pass
    would cut the already-narrowed centre again.

    Pass `seam` to state where the design's own division sits. The 0.38 fallback is a migration
    measure for bodies authored before locations were separated; a new body function should give its
    seam, because that is a fact about the design rather than a fraction of whatever the shell
    happens to measure.
    """
    if getattr(body, 'torso_split', False):
        return
    shell = [tri for tri, node, _ in body.faces if node == 'CT']
    if not shell:
        return
    body.torso_split = True
    edge = seam if seam is not None else max(abs(p[0]) for tri in shell for p in tri) * .38

    def clip(points, plane, sign):
        result = []
        for index, a in enumerate(points):
            b = points[(index+1) % len(points)]
            inside_a, inside_b = sign*(a[0]-plane) >= 0, sign*(b[0]-plane) >= 0
            if inside_a:
                result.append(a)
            if inside_a != inside_b:
                t = (plane-a[0])/(b[0]-a[0])
                result.append(tuple(a[axis]+(b[axis]-a[axis])*t for axis in range(3)))
        return result

    faces = []
    for tri, node, material in body.faces:
        if node != 'CT':
            faces.append((tri, node, material))
            continue
        regions = [('LT', clip(tri, -edge, -1)), ('CT', clip(clip(tri, -edge, 1), edge, -1)),
                   ('RT', clip(tri, edge, 1))]
        for location, polygon in regions:
            for index in range(1, len(polygon)-1):
                tri = (polygon[0], polygon[index], polygon[index+1])
                a, b = sub(tri[1], tri[0]), sub(tri[2], tri[0])
                area = sum((a[(i+1)%3]*b[(i+2)%3]-a[(i+2)%3]*b[(i+1)%3])**2 for i in range(3))
                if area > 1e-12:
                    faces.append((tri, location, material))
    body.faces = faces


def atlas(g):
    g.box((0, 0, 31), (17, 9, 6), 'pelvis', 'edge')
    g.box((0, 0, 36), (13, 9, 6), 'CT', 'metal')
    upright(g, [(36, 18, 10, 0, 0), (46, 28, 14, 0, 0), (53, 25, 12, 0, 0)], cut=.45)
    torso = [(36, 18, 10, 0, 0), (46, 28, 14, 0, 0), (53, 25, 12, 0, 0)]
    for side in (-1, 1):
        vent(g, lofted_face(torso), side*5, 3, 38, 42)
        vent(g, lofted_face(torso, rear=True), side*5, 3, 38, 42, rear=True)
    for side, arm, leg in ((-1, 'LA', 'LL'), (1, 'RA', 'RL')):
        x = side*8
        g.joint(leg, (x, 0, 30), 'pelvis')
        g.joint(leg+'-shin', (x*1.12, 0, 18), leg)
        upright(g, [(19, 6.7, 8, x*1.12, 0), (30, 9, 9, x, 0)], leg, cut=0)
        g.box((x*1.12, 1, 18), (7, 8, 4), leg+'-shin', 'metal')
        upright(g, [(4, 7, 8, x*1.18, 0), (16.3, 10, 10, x*1.12, 0)], leg+'-shin', cut=.45)
        foot(g, x*1.18, 2, 10, 13, leg+'-shin')
        # Rounded shoulder caps, straight upper arms, long gauntlets and closed fists.
        forearm, hand = arm, arm
        if g.modular:
            g.joint(arm, (side*18, 0, 47), 'CT')
            g.joint(arm+'-forearm', (side*21, 1, 38), arm)
            forearm, hand = arm+'@forearm', arm+'@hand'
        upright(g, [(46, 10, 11, side*18, 0), (53, 12, 13, side*17, 0),
                    (57, 7, 9, side*16, 0)], arm, cut=.65)
        g.beam((side*18, 0, 47), (side*21, 1, 38), 7, 7, arm, 'metal')
        upright(g, [(28, 8, 9, side*21, 3), (39, 9, 9, side*21, 1)], forearm, cut=0)
        g.box((side*21, 3.5, 26), (6.5, 7, 4), hand, 'metal')
        panel(g, [(side*21-2, 7.03, 27), (side*21+2, 7.03, 27),
                  (side*21+2, 7.03, 25), (side*21-2, 7.03, 25)], hand, 'edge')
    # Skull: broad brow, tapered cheeks/jaw, paired sockets and a toothed mouth.
    forward(g, [(-2, 8, 9, 0, 55.5), (3, 10, 10, 0, 55.5),
                (6.7, 7.8, 8.4, 0, 54.5)], 'HD', cut=.65)
    for side in (-1, 1):
        x = side*2.15
        panel(g, [(x-1.5, 6.73, 56.8), (x+1.5, 6.73, 56.8),
                  (x+1.2, 6.73, 54.8), (x-1.1, 6.73, 54.8)], 'HD')
        panel(g, [(x-.7, 6.76, 56.2), (x+.7, 6.76, 56.2),
                  (x+.7, 6.76, 55.6), (x-.7, 6.76, 55.6)], 'HD', 'glass')
    panel(g, [(-.7, 6.76, 53.8), (0, 6.76, 54.9), (.7, 6.76, 53.8)], 'HD')
    panel(g, [(-2.4, 6.73, 53.1), (2.4, 6.73, 53.1),
              (1.8, 6.73, 51.6), (-1.8, 6.73, 51.6)], 'HD')
    for x in (-1.45, 0, 1.45):
        panel(g, [(x-.38, 6.77, 53), (x+.38, 6.77, 53),
                  (x+.38, 6.77, 51.75), (x-.38, 6.77, 51.75)], 'HD', 'paint')


def locust(g):
    # The entire upper body is a low forward cockpit pod, with no humanoid head.
    forward(g, [(-9, 10, 10, 0, 39), (1, 13, 11, 0, 39),
                (12, 7, 6, 0, 35.8)], 'CT', cut=.45)
    for side in (-1, 1):
        # A twenty tonner has almost no flat frontage, so its vents stay small.
        vent(g, capped_face(12), side*1.05, .85, 34.5, 37)
        vent(g, capped_face(-9, rear=True), side*1.4, 1.15, 37, 40, rear=True)
    g.box((0, -1, 31), (9, 9, 6), 'pelvis', 'metal')
    for side in (-1, 1):
        # Angled glazing lies just above the sloped top of the nose.
        points = [(side*.5, 2, 44.12), (side*3.4, 2, 44.12),
                  (side*2, 10.8, 39.48), (side*.5, 10.8, 39.48)]
        panel(g, list(reversed(points)) if side == -1 else points, 'HD', 'glass')
    g.beam((0, -3, 44), (0, -6, 53), .7, .7, 'HD', 'metal', taper=.2)
    for side, arm, leg in ((-1, 'LA', 'LL'), (1, 'RA', 'RL')):
        hip, knee, ankle = (side*8, -1, 31.5), (side*11, -9, 20), (side*12, -1, 3)
        g.joint(leg, hip, 'pelvis')
        g.joint(leg+'-shin', knee, leg)
        g.beam((side*6, -1, 32), (side*10, -1, 32), 10, 10, leg, 'edge', 6)
        g.beam(hip, knee, 5, 7, leg, 'paint', taper=.7)
        g.beam((side*9.8, -9, 20), (side*12, -9, 20), 4.8, 4.8, leg+'-shin', 'metal')
        g.beam(knee, ankle, 3, 4, leg+'-shin', 'edge', taper=.8)
        g.box((ankle[0], -1, 2.2), (2.8, 4, 3), leg+'-shin', 'metal')
        toes(g, ankle[0], -1, leg+'-shin', 2.8, 7)
        # High, compact gun stubs flank the cockpit; no forearms or hands.
        if g.modular:
            g.joint(arm, (side*5, -1, 39), 'CT')
        g.beam((side*5, -1, 39), (side*12, -1, 39), 3, 3, arm, 'metal')
        forward(g, [(-4, 4.5, 5, side*13, 39.5), (3, 4.5, 4, side*13, 39)], arm, cut=0)


def warhammer(g):
    g.box((0, 0, 29), (16, 8, 6), 'pelvis', 'edge')
    g.box((0, 0, 34), (9, 7, 6), 'CT', 'metal')
    forward(g, [(-6, 22, 12, 0, 43), (3, 23, 14, 0, 43),
                (7, 18, 9, 0, 41.5)], cut=0)
    for side in (-1, 1):
        vent(g, capped_face(7), side*4.5, 3, 38.5, 41.5)
        vent(g, capped_face(-6, rear=True), side*5, 3.5, 39, 42, rear=True)
    forward(g, [(-3, 7, 6, 0, 49), (4, 8, 5, 0, 48), (6, 6, 3, 0, 46.5)], 'HD', cut=0)
    panel(g, [(-2.6, 6.04, 47.4), (2.6, 6.04, 47.4),
              (2.6, 6.04, 46.1), (-2.6, 6.04, 46.1)], 'HD', 'glass')
    for side, arm, leg in ((-1, 'LA', 'LL'), (1, 'RA', 'RL')):
        x = side*7.5
        g.joint(leg, (x, 0, 29.4), 'pelvis')
        g.joint(leg+'-shin', (side*9, 0, 18), leg)
        g.beam((x, 0, 29), (side*9, 0, 19), 9, 10, leg, 'edge')
        g.box((side*9, 1.5, 18), (7, 8, 4), leg+'-shin', 'metal')
        upright(g, [(4, 7, 8, side*9.7, 0), (16.3, 9, 9, side*9, 0)], leg+'-shin', cut=.35)
        foot(g, side*9.7, 2, 9, 12, leg+'-shin')
        upright(g, [(43, 11, 10, side*15, 0), (49, 12, 10, side*14, -1)], arm, cut=0)
        g.beam((side*16, 0, 44), (side*20, -1, 34), 5, 5, arm, 'metal')
        forearm = arm
        if g.modular:
            g.joint(arm, (side*15, 0, 44), 'CT')
            forearm = arm+'-forearm'
            g.joint(forearm, (side*20, -1, 34), arm)
        # Broad cannon gauntlets, terminating in sockets for the actual variant weapons.
        forward(g, [(-4, 6, 7, side*20, 33), (4, 8, 8, side*20, 32),
                    (9, 5, 5, side*20, 32)], forearm, cut=0)
    # The left searchlight balances the equipment-driven right shoulder launcher.
    if not g.modular:
        g.box((-12.5, 0, 51.8), (5.5, 5, 4.5), 'LT', 'edge')
        panel(g, [(-14.7, 2.54, 53.5), (-10.3, 2.54, 53.5),
                  (-10.3, 2.54, 50.2), (-14.7, 2.54, 50.2)], 'LT', 'glass')


def mad_cat(g):
    g.beam((-11, -2, 28), (11, -2, 28), 8, 8, 'pelvis', 'metal', 6)
    g.box((0, -2, 31), (14, 10, 5), 'CT', 'edge')
    # Four coarse sections form the projecting, rounded cockpit prow.
    forward(g, [(-10, 16, 14, 0, 39), (1, 20, 17, 0, 39),
                (11, 13, 11, 0, 36), (15, 7, 7, 0, 34.5)], 'CT', cut=.65)
    for side in (-1, 1):
        vent(g, capped_face(3), side*3.5, 2.5, 29.5, 32.5)
        vent(g, capped_face(-10, rear=True), side*1.7, 1.5, 36, 40, rear=True)
    # The cockpit is a faceted bubble canopy wrapped over the top and front of the nose, not skylights:
    # a glass shell standing proud of the hull, with a frame rib down its center.
    forward(g, [(6, 12, 7, 0, 42), (11.5, 11.5, 8, 0, 39.2), (15.6, 6.8, 5.4, 0, 36.2)], 'HD', 'glass', .6)
    g.beam((0, 6.2, 45.6), (0, 11.5, 43.3), 1.1, .6, 'HD', 'edge')
    g.beam((0, 11.5, 43.3), (0, 15.7, 39), 1.1, .6, 'HD', 'edge')
    for side, arm, leg, torso in ((-1, 'LA', 'LL', 'LT'), (1, 'RA', 'RL', 'RT')):
        hip, knee = (side*8, -3, 28), (side*10.5, -9, 21)
        g.joint(leg, hip, 'pelvis')
        g.joint(leg+'-shin', knee, leg)
        g.beam(hip, knee, 5, 6, leg, 'edge')
        g.beam((side*9, -9, 21), (side*12, -9, 21), 5, 5, leg+'-shin', 'metal')
        upright(g, [(4, 5, 6, side*12, 0), (12, 8, 10, side*11.5, -2),
                    (20.3, 6, 7, side*10.5, -7)], leg+'-shin', cut=.65)
        g.box((side*12, 0, 2.5), (4, 4, 4), leg+'-shin', 'metal')
        toes(g, side*12, -1, leg+'-shin', 3.8, 9)
        # Tall narrow supports make the launchers float above the cockpit and low arms.
        if g.modular:
            g.joint(arm, (side*14, -4, 40), 'CT')
        g.box((side*14, -5, 42), (7, 8, 13), torso, 'edge')
        g.beam((side*14, -4, 40), (side*21, -3, 32), 5, 6, arm, 'metal')
        forward(g, [(-5, 6, 10, side*21, 31), (7, 6, 9, side*21, 31)], arm+'@forearm', cut=.35)
        forward(g, [(-5, 6, 10, side*21, 31), (1, 6, 9.5, side*21, 31)], arm+'@elbow', cut=.35)


def marauder(g):
    # A hunched pod slung ahead of the hips: tall humped back falling to a low pointed nose.
    g.beam((-9, -3, 29), (9, -3, 29), 8, 8, 'pelvis', 'metal', 6)
    g.box((0, -3, 32.5), (11, 9, 5), 'CT', 'edge')
    forward(g, [(-14, 14, 12, 0, 42), (-4, 19, 17, 0, 41.5),
                (8, 16, 13, 0, 38.5), (18, 7, 6, 0, 35)], 'CT', cut=.55)
    for side in (-1, 1):
        vent(g, capped_face(1.5), side*2.7, 2, 31, 34)
        vent(g, capped_face(-14, rear=True), side*1.8, 1.5, 39, 43, rear=True)
    for side in (-1, 1):
        # Glazing lies just above the sloped top of the nose.
        points = [(side*.5, 9.5, 44.05), (side*3.4, 9.5, 44.05),
                  (side*1.8, 16.5, 39.5), (side*.5, 16.5, 39.5)]
        panel(g, list(reversed(points)) if side == -1 else points, 'HD', 'glass')
    # Dorsal gun pedestal; the long barrel itself belongs to the variant's equipment.
    g.box((2, -6, 51), (6, 7, 4), 'RT', 'metal')
    for side, arm, leg, torso in ((-1, 'LA', 'LL', 'LT'), (1, 'RA', 'RL', 'RT')):
        hip, knee = (side*8.5, -3, 29), (side*11, -10, 21)
        g.joint(leg, hip, 'pelvis')
        g.joint(leg+'-shin', knee, leg)
        g.beam(hip, knee, 7, 8, leg, 'paint')
        g.beam((side*9, -10, 21), (side*13, -10, 21), 5.5, 5.5, leg+'-shin', 'metal')
        upright(g, [(4, 6, 7, side*12.5, 0), (12, 8, 10, side*12, -2),
                    (20.3, 6.5, 8, side*11, -8)], leg+'-shin', cut=.45)
        g.box((side*12.5, 0, 2.5), (6, 6, 4.5), leg+'-shin', 'metal')
        toes(g, side*12.5, 0, leg+'-shin', 4.6, 12)
        g.beam((side*12.5, -2, 1.3), (side*12.5, -9, 1.3), 4, 2.6, leg+'-shin', 'paint', taper=.6)
        # Armored shoulder housings flank the hump and carry the short upper arms.
        if g.modular:
            g.joint(arm, (side*12, -2, 40), 'CT')
        g.box((side*11, -5, 42), (5, 13, 9), torso, 'edge', .3)
        g.beam((side*12, -2, 40), (side*21, 1, 33), 6.5, 6.5, arm, 'metal')
        # Long double-deck forearm pods held low and forward; their muzzles are equipment.
        forward(g, [(-4, 6, 8, side*21.5, 30.5), (2, 7.5, 10, side*21.5, 30.5),
                    (16, 7.5, 10, side*21.5, 30.5)], arm+'@forearm', cut=.3)
        forward(g, [(-4, 6, 8, side*21.5, 30.5), (1, 7.5, 10, side*21.5, 30.5),
                    (6, 7.5, 10, side*21.5, 30.5)], arm+'@elbow', cut=.3)
        g.box((side*21.5, 18, 30.5), (6, 4, 6.5), arm+'@hand', 'metal')


def archer(g):
    g.box((0, 0, 30), (17, 10, 6), 'pelvis', 'edge')
    g.box((0, 0, 35), (12, 9, 5), 'CT', 'metal')
    # Barrel chest: the variant's launchers fill the two upper bays under the raised hoods.
    upright(g, [(34, 16, 12, 0, 0), (43, 27, 21, 0, 0), (53, 25, 19, 0, -.5)], cut=.35)
    torso = [(34, 16, 12, 0, 0), (43, 27, 21, 0, 0), (53, 25, 19, 0, -.5)]
    for side in (-1, 1):
        # The cockpit wedge owns the middle of the front, so its vents sit outboard of it.
        vent(g, lofted_face(torso), side*7, 1.3, 38.5, 41.5)
        vent(g, lofted_face(torso, rear=True), side*4.5, 3, 38, 42, rear=True)
    # No separate head: the centre is one solid mass. Its top slopes from the back down to the
    # cockpit, while its underside runs level from the base of the cockpit straight back into the
    # torso, so the window sits in front of the launchers and below them without drooping.
    forward(g, [(-8, 11, 19, 0, 45.5), (3, 11, 18, 0, 45.5), (13, 9.5, 11.7, 0, 42.6),
                (20, 7, 6.3, 0, 40.1)], 'HD', cut=.3)
    panel(g, [(-2.3, 20.03, 42.3), (2.3, 20.03, 42.3),
              (2.3, 20.03, 38.5), (-2.3, 20.03, 38.5)], 'HD', 'glass')
    # Twin antennas stand on the back of the wedge, directly behind the cockpit.
    for side in (-1, 1):
        g.beam((side*2.4, -5, 54.6), (side*2.8, -7, 61.5), 1.1, 1.1, 'HD', 'metal', taper=.2)
    for side, arm, leg, torso in ((-1, 'LA', 'LL', 'LT'), (1, 'RA', 'RL', 'RT')):
        x = side*8
        g.joint(leg, (x, 0, 29), 'pelvis')
        g.joint(leg+'-shin', (x*1.1, 0, 17), leg)
        upright(g, [(18, 8, 9, x*1.1, 0), (29, 10.5, 10.5, x, 0)], leg, cut=.3)
        g.box((x*1.1, 1, 17), (7.5, 8.5, 4), leg+'-shin', 'metal')
        upright(g, [(4, 8, 9, x*1.15, 0), (15.5, 10.5, 10.5, x*1.1, 0)], leg+'-shin', cut=.4)
        foot(g, x*1.15, 2.5, 11, 15, leg+'-shin')
        # Tall bay housings rise above the centre and lean back with their launchers; doors shut.
        upright(g, [(43.1, 10, 14, side*9.2, 5.9), (54.9, 10, 14, side*9.2, .6)], torso, cut=.2)
        # Round shoulders, short upper arms, heavy forearms held forward and closed fists.
        if g.modular:
            g.joint(arm, (side*17.5, 0, 43), 'CT')
        # Compact shoulders tucked against the bays: a solid machine, not a broad-shouldered one.
        upright(g, [(42, 8, 10, side*17.2, 0), (48.5, 9.5, 11.5, side*17, 0),
                    (52, 6.5, 8, side*16.6, 0)], arm, cut=.6)
        g.beam((side*17.5, 0, 43), (side*20.5, -3, 35), 6, 6, arm, 'metal')
        forward(g, [(-6, 7, 8, side*21, 33), (4, 8, 9.5, side*21, 33),
                    (11, 6.5, 8, side*21, 33)], arm+'@forearm', cut=.3)
        g.box((side*21, 13, 33), (5.5, 4, 5.5), arm+'@hand', 'metal')
        # Without a lower arm the upper arm ends in a capped elbow that carries the weapon.
        g.box((side*20.7, -1.5, 34), (7.5, 7.5, 7), arm+'@elbow', 'edge', .3)


def mackie(g):
    # Squat and very wide: a boxy torso under a glass bubble, with both arms simply guns held level.
    g.box((0, 0, 31), (19, 11, 6), 'pelvis', 'edge')
    g.box((0, 0, 35.5), (14, 10, 4), 'CT', 'metal')
    upright(g, [(37, 24, 16, 0, 0), (43, 32, 21, 0, 0), (54, 30, 20, 0, 0)], cut=.2)
    torso = [(37, 24, 16, 0, 0), (43, 32, 21, 0, 0), (54, 30, 20, 0, 0)]
    for side in (-1, 1):
        vent(g, lofted_face(torso), side*6, 4, 38, 41.5)
        vent(g, lofted_face(torso, rear=True), side*6, 4, 38, 41.5, rear=True)
    # A raised plate marks the center of the chest.
    g.box((0, 10.4, 46), (12, 1.2, 9), 'CT', 'edge')
    # The bubble cockpit sits on a collar at the front of the roof.
    g.box((0, 3.5, 55), (15, 14, 2), 'HD', 'edge', .3)
    upright(g, [(56, 13, 12, 0, 3.5), (61, 12, 11, 0, 3.5), (65, 7, 6, 0, 3.5)], 'HD', 'glass', .55)
    # Twin guns hang from a block under the front of the torso.
    g.box((0, 8, 35), (9, 5, 3.6), 'CT', 'metal')
    # Right shoulder: a box searchlight. Left shoulder: a vented housing.
    if not g.modular:
        g.box((13, -2, 58.5), (7, 6, 7), 'RT', 'edge', .3)
        panel(g, [(10.4, 1.03, 61.1), (15.6, 1.03, 61.1), (15.6, 1.03, 55.9), (10.4, 1.03, 55.9)], 'RT', 'lamp')
    g.box((-13, -3, 57), (11, 8, 5), 'LT', 'edge')
    panel(g, [(-17.6, 1.03, 58.8), (-8.4, 1.03, 58.8), (-8.4, 1.03, 55.4), (-17.6, 1.03, 55.4)], 'LT', 'dark')
    for side, arm, leg in ((-1, 'LA', 'LL'), (1, 'RA', 'RL')):
        x = side*9.5
        g.joint(leg, (x, 0, 30), 'pelvis')
        g.joint(leg+'-shin', (x*1.08, 0, 17), leg)
        upright(g, [(18, 9, 10, x*1.08, 0), (30, 12, 12, x, 0)], leg, cut=.25)
        # One raised plate stands for the tiled thigh armor.
        g.box((x, 6.3, 25), (9, 1.2, 8), leg, 'edge')
        g.box((x*1.08, 1, 17), (8.5, 9.5, 4), leg+'-shin', 'metal')
        upright(g, [(4, 9, 10, x*1.12, 0), (15.5, 11, 11, x*1.08, 0)], leg+'-shin', cut=.35)
        foot(g, x*1.12, 3, 13, 17, leg+'-shin')
        # A shoulder block, then an arm held level at shoulder height. How it ends follows the actuators.
        if g.modular:
            g.joint(arm, (side*19.5, 0, 46), 'CT')
        g.box((side*19.5, 0, 46), (8, 11, 11), arm, 'edge', .3)
        for part in ('elbow', 'forearm', 'wrist', 'hand'):
            g.joint(arm+'@'+part, g.pivots[arm], arm)
        # No lower arm: the gun housing starts at the elbow.
        forward(g, [(-9, 9, 11, side*28.5, 45), (-1, 10, 12, side*28.5, 45), (6, 8.5, 10.5, side*28.5, 45)],
                arm+'@elbow', cut=.35)
        # A lower arm, then either a gun housing at the wrist or a closed fist.
        forward(g, [(-7, 8, 9, side*28.5, 45), (8, 8, 9, side*28.5, 45)], arm+'@forearm', cut=.3)
        forward(g, [(6, 9.5, 11.5, side*28.5, 45), (14, 8.5, 10.5, side*28.5, 45)], arm+'@wrist', cut=.35)
        g.box((side*28.5, 10.5, 45), (7, 5, 7), arm+'@hand', 'metal')
    # A round shield disc rings the right arm's gun, which always starts at the elbow.
    g.beam((28.5, 5, 45), (28.5, 7, 45), 17, 17, 'RA@elbow', 'edge', 8)


def rifleman(g):
    # Drawn to the overhead sprite for width and placement, to the miniature for form: wide shoulders
    # carrying the weapon pods outboard, a broad torso, and the Garret communications array centred on
    # the head rather than set on one shoulder. No variant has a hand or a lower arm, so each arm is a
    # pod whose guns leave the armour at its stepped face.
    g.box((0, -1, 29.4), (16, 11, 6), 'pelvis', 'edge')
    torso = [(30.4, 18, 13, 0, -1), (36.4, 22, 15, 0, -1), (45.4, 20, 13.5, 0, -1.5)]
    upright(g, torso, cut=.3)
    # Give the shell real side locations before any LT/RT accessory is authored, or the side armour
    # stays labelled CT and a destroyed side torso takes only its shoulder with it. The seam is the
    # shoulder root at 4.2, where the chest stops and the arm-carrying structure begins.
    split_torso_locations(g, seam=4.2)
    for side in (-1, 1):
        # Vents follow the heat sinks. Across the Rifleman's variants the catalog puts 25 located
        # sinks in the left torso and 24 in the right against 5 in the centre, so the vents belong
        # on LT and RT. They sit low, clear of the flush medium laser those locations mount at 37.9.
        location = 'LT' if side < 0 else 'RT'
        vent(g, lofted_face(torso), side*5.7, 1.4, 30.9, 33.4, group=location)
        vent(g, lofted_face(torso, rear=True), side*5.7, 1.4, 34.4, 36.9, rear=True, group=location)
    # The sprite puts the cockpit just left of the centre line, ahead of the torso and below the pods.
    # The head runs the full length of the centre torso rather than perching on it, so it lofts
    # upward like the torso does: the front face has to move with height, which a forward loft cannot
    # do. Four sections, bottom to top - a narrow chin dropped to 31.5, just above the torso floor at
    # 30.4; the cockpit standing 4.5 clear of the chest front at y 11; then the crown falling back
    # behind the chest to y 4.5, which is the slope the line art runs up into the antenna mast.
    # The cockpit's two sections share a front face so the glass lies flat on it instead of floating.
    # A deep chamfer keeps the protrusion rounded; the old head was a box and read as one.
    upright(g, [(31.5, 8, 12, 0, 5), (35.5, 10, 12, 0, 5),
                (41, 10, 12, 0, 5), (45, 8, 7, 0, 1)], 'HD', cut=.45)
    # The viewport runs most of the cockpit's standing height, 2.8 across by 8, stopping 1.3 above
    # the chin so the armour closes under it as a frame rather than running off the bottom edge.
    panel(g, [(-1.4, 11.05, 40.8), (1.4, 11.05, 40.8), (1.4, 11.05, 32.8), (-1.4, 11.05, 32.8)], 'HD', 'glass')
    # Search radar: a housing on the right shoulder with two forward prongs, as the sprite draws it.
    # Garret T11-A communications array: a mast on the centre line carrying a crossbar that runs
    # across the Mek with its tips swept forward. The miniature sets both the form and the central
    # mounting; the overhead sprite draws the block off to one side, and the miniature wins.
    g.box((0, 1, 47.9), (5.5, 5.5, 5), 'CT', 'edge')
    g.box((0, 1.8, 51), (7, 6, 2.6), 'CT', 'edge', .3)
    for reach in (-8, 8):
        g.beam((0, .6, 52.4), (reach, 4.6, 52.4), 2.6, 1.8, 'CT', 'edge')
    for side, arm, leg, torso_side in ((-1, 'LA', 'LL', 'LT'), (1, 'RA', 'RL', 'RT')):
        x = side*7.5
        g.joint(leg, (x, 0, 29), 'pelvis')
        g.joint(leg+'-shin', (x*1.05, -1, 16.5), leg)
        # Sixty tons: the legs stay lighter than the seventy-ton designs already in this file.
        upright(g, [(16.5, 8, 9.5, x*1.05, -1), (29.4, 10, 10.5, x, 0)], leg, cut=.3)
        g.box((side*11.5, -1, 23.5), (2.8, 9, 9.5), leg, 'edge', .45)
        g.box((x*1.05, 0, 16.5), (8, 9, 4), leg+'-shin', 'metal')
        upright(g, [(5, 8.5, 9.5, x*1.1, 0), (14, 9.5, 10, x*1.05, -.5)], leg+'-shin', cut=.35)
        foot(g, x*1.1, 2.5, 9.5, 13, leg+'-shin')
        # The shoulder stops where the pod starts, at 12.75, instead of running out underneath it. An arm
        # flip turns the pod about this joint's left-right axis, which never changes x, so a pod that is
        # flush with the shoulder at rest stays flush all the way round rather than sweeping through it.
        # Overall width is unchanged - the pod still ends at 21.25; only the seam between them moves.
        upright(g, [(33.4, 9, 15, side*8.25, -1.5), (45.9, 9.5, 15.5, side*8, -1.5)], torso_side, cut=.25)
        if g.modular:
            g.joint(arm, (side*14, 0, 40.4), 'CT')
        # The miniature is primary on size and stance: the pods are slim and sit against the side
        # torso rather than out on the shoulder. Still half again as tall as they are wide.
        forward(g, [(-7, 7.4, 11.2, side*17, 40.4), (2, 8.5, 12.8, side*17, 40.4),
                    (10, 7.4, 11.2, side*17, 40.4), (14, 5.6, 8.4, side*17, 40.4)], arm, cut=.15)


def battlemaster(g):
    # Eighty-five ton assault Mek: very broad angular pauldrons, a domed cockpit set low between
    # them, long arms held forward, and a missile bay riding high on each shoulder. Every variant
    # keeps both lower arms and most keep both hands, so the arms are full limbs, not pods.
    g.box((0, -1, 31), (21, 14, 7), 'pelvis', 'edge')
    torso = [(32, 21, 16, 0, -1), (41, 28, 20, 0, -1), (51, 25, 17, 0, -1.5)]
    upright(g, torso, cut=.35)
    # Real side locations before the pauldrons are authored, for the same reason. The seam is 5.3,
    # where the chest slab ends and the structure carrying the pauldrons begins; it also puts the
    # side-torso vents wholly outboard of the centre section rather than straddling it.
    split_torso_locations(g, seam=5.3)
    for side in (-1, 1):
        # Same rule: 37 located sinks in the right torso and 23 in the left against 7 in the centre.
        # Well inboard of the arm mounts at 14 and the shoulder missile bays at 15.
        location = 'LT' if side < 0 else 'RT'
        vent(g, lofted_face(torso), side*6.7, 1.3, 33, 36.5, group=location)
        vent(g, lofted_face(torso, rear=True), side*6.7, 1.3, 37.5, 41, rear=True, group=location)
    # A glass blister, not a pane set into a frame. The whole bulb is lofted in glass and runs from
    # low at the front straight back and up to a narrow ridge at the top, which is the triangle the
    # artwork shows there. The old head was a hexagonal housing with a flat rectangle inside it -
    # the frame read as the head and the glass as a window, which is the wrong way round.
    forward(g, [(-3, 4, 3.5, 0, 52.5), (2, 9.5, 8, 0, 50.5), (7, 11.5, 10, 0, 47.5),
                (10.5, 10.5, 9, 0, 47)], 'HD', 'glass', cut=.5)
    # Two frames banding the glass, as drawn. Each is a short loft of the canopy's own section a
    # third of a unit larger, so it wraps the bulb as a rib. A box will not do it: a box is a filled
    # slab, and at this size its flat face shows around the glass as a plate rather than a frame.
    for station, width, height, middle in ((3.5, 10.45, 8.95, 49.6), (8.2, 11.2, 9.75, 47.2)):
        forward(g, [(station - .3, width, height, 0, middle),
                    (station + .3, width, height, 0, middle)], 'HD', 'edge', cut=.5)
    # A supporting frame under the cockpit rather than a block it sits in: narrower than the glass
    # and set back a unit behind its face, so it reads as carrying the bulb. Keeping it low also lets
    # the bulb's lower chamfer show, which is what makes the bottom of the glass mirror its top.
    g.box((0, 3.5, 41.6), (9.5, 12, 3.2), 'HD', 'edge', .3)
    # A grey cowl closing the back of the canopy, where the artwork puts an angular housing rather
    # than letting the glass simply stop. It laps over the bulb's rear ridge and carries the antennas
    # out of its own back face instead of out of the chest behind it.
    forward(g, [(-6.5, 5.5, 5, 0, 52), (-2.5, 6.5, 5.5, 0, 52.8)], 'HD', 'edge', cut=.3)
    # Twin antennas stand behind the canopy on the back of the chest.
    for side in (-1, 1):
        g.beam((side*3, -6, 50.5), (side*4, -8.5, 59), 1.2, 1.2, 'CT', 'metal', taper=.25)
    for side, arm, leg, torso_side in ((-1, 'LA', 'LL', 'LT'), (1, 'RA', 'RL', 'RT')):
        x = side*9
        g.joint(leg, (x, 0, 31), 'pelvis')
        g.joint(leg+'-shin', (x*1.05, -1, 17.5), leg)
        # Eighty-five tons: heavier than the seventy-ton designs, short of the Mackie. The thigh itself
        # is narrower than it was; the hip pad below carries the outer line instead of the leg's own
        # mass, which is what made the legs read as over-wide.
        # No hip plate: the thigh carries its own line. It is widest at 28 and draws back in above
        # that, so the top outer corner slopes away under the pelvis instead of squaring off against
        # it - the cut the artwork puts there.
        upright(g, [(17.5, 11, 13.5, x*1.05, -1), (28, 13, 15, x, 0),
                    (33, 9, 12, x*.9, 0)], leg, cut=.3)
        # The knee is a distinct armoured block, as the artwork draws it.
        g.box((x*1.05, .5, 17.5), (12, 12.5, 5.5), leg+'-shin', 'metal')
        upright(g, [(5, 11.5, 12.5, x*1.1, 0), (15, 13, 13.5, x*1.05, -.5)], leg+'-shin', cut=.35)
        foot(g, x*1.1, 3, 13, 17, leg+'-shin')
        # Broad angular pauldron over the side torso, carrying the missile bay on its top. It stops at
        # 18.25, where the arm begins, rather than running out under it: an arm flip turns about this
        # joint's left-right axis, which never changes x, so an arm flush with the pauldron at rest
        # stays flush all the way round. Each section keeps its width and moves inboard, so the
        # pauldron keeps its mass and the unit keeps its width - the arm still ends at 31.75.
        # A shoulder pad, not a slab beside the arm: a broad shell capping the shoulder, widest where
        # its lower lip drapes out over the arm at 40, drawing back in as it rises toward the neck.
        # The arm hangs underneath it, narrower, so the pad overhangs it on both sides.
        upright(g, [(41, 15, 15, side*19.5, -1), (45, 16, 16, side*19, -1),
                    (48, 14, 14, side*16, -1), (50.5, 9, 10, side*11.5, -1)], torso_side, cut=.35)
        if g.modular:
            # Hung from the top of the shoulder, up inside the pad, rather than socketed into its side.
            g.joint(arm, (side*19.5, 0, 44), 'CT')
        # The upper arm hangs from that point and is narrower than the pad above it, so the pad's lip
        # covers its top rather than meeting it edge to edge.
        upright(g, [(30, 10, 11, side*19.5, 0), (44, 12, 13, side*19.5, 0)], arm, cut=.45)
        # The lower arm reaches forward level with the chest; the fist caps it when one is fitted.
        forward(g, [(-7, 10, 11, side*19.5, 31), (6, 11, 12, side*19.5, 31),
                    (20, 9.5, 10.5, side*19.5, 31)], arm+'@forearm', cut=.3)
        g.box((side*19.5, 23.5, 31), (8, 6, 8.5), arm+'@hand', 'edge', .3)
        # Without a lower arm the upper arm ends in a capped elbow that carries the weapon.
        g.box((side*19.5, -1, 32), (10.5, 10.5, 9.5), arm+'@elbow', 'edge', .3)


def king_crab(g):
    # A broad low carapace, slit cockpit and open pincers: the guns inside them are live equipment.
    g.box((0, -2, 29), (24, 13, 7), 'pelvis', 'metal', .35)
    g.box((0, -2, 36), (17, 11, 12), 'CT', 'edge', .3)

    def shell_ring(x, rear, front, low, high, nose):
        # Long sloping roof, knife-edged prow and an undercut belly; no rounded forehead on top.
        return [(x, rear+4, low+4), (x, front-8, min(low+4, nose-4)), (x, front-2.3, nose-4),
                (x, front-2.3, nose+.5), (x, front-9, nose+2), (x, rear+6, high),
                (x, rear, high-2.5), (x, rear, low+9)]

    # Three actual armor shells own the roof and flanks. The complete visor band is a fourth, detachable HD mesh.
    inner = (-30, 26, 38, 56, 49)
    mid = (-28, 20, 39, 55, 48)
    outer = (-22, 7, 40, 52, 46.5)
    g.loft([shell_ring(-7, *inner), shell_ring(0, -30, 29, 38, 57, 50), shell_ring(7, *inner)], 'CT')
    for side, torso in ((-1, 'LT'), (1, 'RT')):
        rings = [shell_ring(side*7, *inner), shell_ring(side*18, *mid), shell_ring(side*25, *outer)]
        g.loft(rings if side == 1 else list(reversed(rings)), torso)
        # Back heat-exchanger recesses stay part of the hull, not optional searchlights or weapon barrels.
        g.box((side*13, -29, 50), (8, 3, 7), torso, 'metal')
        # Raised rear mounting shoulders support forward-firing weapons; these are not rear-firing ports.
        g.box((side*16, -21, 55.5), (9, 12, 3), torso, 'edge', .3)
        # Short armor pad seats small dorsal guns without covering their forward muzzle.
        g.box((side*18, -7, 53.25), (7, 4, 1.5), torso, 'edge')

    brow = [(-25, 7, 46.5), (-18, 20, 48), (-7, 26, 49), (0, 29, 50),
            (7, 26, 49), (18, 20, 48), (25, 7, 46.5)]
    def lip_ring(p):
        x, y, z = p
        # The outer lip must clear the shell's closed side cap instead of sharing its plane.
        if abs(x) == 25:
            x *= 25.2/25
        return [(x, y-3, z-.4), (x, y+.25, z-.8), (x, y+.25, z), (x, y-3, z+.7)]
    for owner, points in (('LT', brow[:3]), ('CT', brow[2:5]), ('RT', brow[4:])):
        g.loft([lip_ring(p) for p in points], owner)

    # HD is the whole thin front band, including every window and its frame. The hull is recessed behind it.
    g.joint('HD', (0, 23, 46), 'CT')
    rings = [[(x, y-1.8, z-4), (x, y+.15, z-4), (x, y+.15, z-1), (x, y-1.8, z-1)]
             for x, y, z in brow]
    g.face(list(reversed(rings[0])), 'HD', 'edge')
    g.face(rings[-1], 'HD', 'edge')
    for a, b, lo, hi in zip(brow, brow[1:], rings, rings[1:]):
        for index in (0, 2, 3):  # Bottom, top and back. The window/frame tessellation supplies the front face.
            other = (index+1) % 4
            g.face([lo[index], lo[other], hi[other], hi[index]], 'HD', 'edge')
        def window(t, below):
            return (a[0]+(b[0]-a[0])*t, a[1]+(b[1]-a[1])*t+.15, a[2]+(b[2]-a[2])*t-below)
        # Adjacent pieces, not glass layered over a nearly coplanar backing (which causes depth stripes).
        for start, end, top, bottom, material in ((0, .12, 1, 4, 'dark'), (.88, 1, 1, 4, 'dark'),
                (.12, .88, 1, 1.55, 'dark'), (.12, .88, 3.45, 4, 'dark'), (.12, .88, 1.55, 3.45, 'glass')):
            panel(g, [window(end, bottom), window(start, bottom), window(start, top), window(end, top)], 'HD', material)
    # Compact recessed CT grille; no broad hanging jaw underneath the visor.
    forward(g, [(14, 10, 5, 0, 41.5), (18.5, 7.5, 3.5, 0, 41.5)], 'CT', 'edge', .25)
    panel(g, [(-2.7, 18.53, 42.4), (2.7, 18.53, 42.4),
              (2.7, 18.53, 40.6), (-2.7, 18.53, 40.6)], 'CT', 'metal')
    for z in (40.85, 41.5, 42.15):
        panel(g, [(-2.3, 18.59, z+.1), (2.3, 18.59, z+.1),
                  (2.3, 18.59, z-.1), (-2.3, 18.59, z-.1)], 'CT', 'edge')

    for side, arm, leg in ((-1, 'LA', 'LL'), (1, 'RA', 'RL')):
        hip, knee, ankle = (side*10.5, -2, 29), (side*14, -10, 18.5), (side*15, -1, 5)
        g.joint(leg, hip, 'pelvis')
        g.joint(leg+'-shin', knee, leg)
        g.beam((side*8, -2, 29), (side*14, -2, 29), 10, 10, leg, 'edge', 6)
        g.beam(hip, knee, 10, 11, leg, 'paint', 4, .85)
        # The knee sits behind both hip and ankle; the shin slopes forward to the planted foot.
        g.box((knee[0], knee[1], 19), (10, 10, 5), leg+'-shin', 'edge', .45)
        upright(g, [(5, 9, 9, ankle[0], -1), (13, 12, 13, side*15, -5.5),
                    (18, 9, 9, knee[0], -9.5)], leg+'-shin', cut=.5)
        # Broad multi-toed armored feet, not the thin bird toes used by lighter reverse-knee Meks.
        g.joint(leg+'-foot', ankle, leg+'-shin')
        upright(g, [(0, 15, 18, ankle[0], 3), (4, 12, 14, ankle[0], 1)], leg+'-foot', cut=.65)
        for offset in (-4.3, 4.3):
            g.box((ankle[0]+offset, 10.7, 1.1), (3, 2.5, 2.2), leg+'-foot', 'metal')

        shoulder, elbow = (side*22, -1, 44), (side*30, 0, 34)
        g.joint(arm, shoulder, 'CT')
        g.joint(arm+'-forearm', elbow, arm)
        # Keep the shoulder end cap outside the x=+/-25 shell wall, not coplanar with it.
        g.beam((side*20, -1, 44), (side*25.4, -1, 44), 10, 10, arm, 'edge', 6)
        g.beam(shoulder, elbow, 7, 8, arm, 'metal')
        for form in ('forearm', 'hand', 'wrist', 'elbow'):
            g.joint(arm+'@'+form, elbow, arm if form == 'elbow' else arm+'-forearm')
        # With lower-arm actuators, a short armored cuff ends behind the open claw.
        forward(g, [(-4, 11, 12, side*30, 34), (3, 13, 13, side*30, 34),
                    (8, 10, 10, side*30, 34)], arm+'@forearm', cut=.4)
        # The alternate no-hand/no-lower-arm housings remain open at the gun end.
        for form, start in (('elbow', -3), ('wrist', 7)):
            for vertical in (-1, 1):
                forward(g, [(start, 11, 3, side*30, 34+vertical*5.2),
                            (16, 9, 2.5, side*30, 34+vertical*4.5)], arm+'@'+form, 'paint', 0)
            g.box((side*35, (start+13)/2, 34), (2, 13-start, 9), arm+'@'+form, 'edge')
        # Upper/lower pincer fingers frame a real equipment aperture, with a visible gap when bare.
        for vertical in (-1, 1):
            forward(g, [(6, 12, 4, side*30, 34+vertical*6),
                        (13, 13, 4, side*30, 34+vertical*7),
                        (20, 9, 3, side*30, 34+vertical*4.5)], arm+'@hand', 'paint', .3)
        g.box((side*35, 10, 34), (2.5, 6, 11), arm+'@hand', 'edge')


def build_chassis(recipe, modular=False):
    g = Geometry(modular=modular)
    hip = recipe['hip']
    g.joint('pelvis', (hip[0]-42, 36-hip[1], hip[2]))
    g.joint('CT', g.pivots['pelvis'], 'pelvis')
    for location in ('LT', 'RT', 'HD', 'LA', 'RA'):
        x, y, z = recipe['sockets'][location]
        g.joint(location, (x-42, 36-y, z), 'CT')
    builders = {'atlas': atlas, 'locust': locust, 'warhammer': warhammer, 'mad-cat': mad_cat,
                'marauder': marauder, 'archer': archer, 'mackie': mackie,
                'king-crab': king_crab, 'rifleman': rifleman,
                'battlemaster': battlemaster}
    builders[recipe['id']](g)
    if modular:
        for arm in recipe.get('heldWeapons', []):
            held_housing(g, arm)
        # Optional anatomy remains separate; the runtime keeps the parts matching the actual actuators.
        # All of it follows the articulated arm, including groups formerly folded into baked variants.
        for arm in ('LA', 'RA'):
            forearm = arm+'-forearm'
            if forearm not in g.pivots:
                socket = recipe.get('armSockets', {}).get(arm, {}).get('elbow', recipe['sockets'][arm])
                g.joint(forearm, (socket[0]-42, 36-socket[1], socket[2]), arm)
            for node in list(g.pivots):
                if node.startswith(arm+'@'):
                    g.parents[node] = arm if node.endswith('@elbow') else forearm
    return g
