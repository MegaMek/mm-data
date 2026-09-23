"""Recognizable bare silhouettes, authored against the repository's sprites and Mek illustrations.

These are chassis anatomy, not equipment or game rules. The variant assembler adds
the actual guns and launchers. +Y faces forward; all dimensions are authoring units.
"""
from math import pi, sin, cos

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


def vent(g, face, center_x, half_width, low_z, high_z, rear=False, group='CT', authored=True):
    """A cooling vent lying in the armour: a shaded recess behind three lit fins.

    House rule: at most two on the front and two on the back, the back pair on a torso only. The
    panels follow the face rather than sitting at one depth, and must stay inside its flat band,
    since a bevelled section chamfers its corners away.

    On a modular body each vent is a spot of its own, not part of the armour: weapons are placed first and
    the runtime then keeps the vents that fit around them (see unit_mek_vents). The authored vents are the
    chassis's first choice.
    """
    low_x, high_x = center_x - half_width, center_x + half_width
    if g.modular:
        if not hasattr(g, 'vents'):
            g.vents = []
        node = 'vent-%d' % len(g.vents)
        g.vents.append({'node': node, 'group': group, 'rear': rear, 'authored': authored})
        group = node

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
    # One hundred tons, the heaviest biped in the set, so it has to carry the most mass: a deep torso, the
    # thickest legs and the heaviest arms of any humanoid here. It was once the thinnest in the set - a
    # torso only 10 to 14 deep and thighs lighter than a sixty-ton Rifleman's - which read as spindly beside
    # much lighter designs. Every detail and its place is unchanged; only the mass has grown.
    # Squared up rather than barrel-chested: the chest is narrower across than its depth suggests, so the
    # shoulders sit close in beside the head and the legs stand close under the body, as the miniature has it.
    # The lower torso drops nearly straight from the armpits rather than tapering in, and the waist block is
    # widened to sit under it, so the flank runs in one line from the shoulder down into the legs.
    g.box((0, 0, 31), (23, 13, 7), 'pelvis', 'edge')
    g.box((0, 0, 36), (19, 12, 6), 'CT', 'metal')
    torso = [(36, 24, 15, 0, 0), (46, 26, 19, 0, 0), (53, 24, 17, 0, 0)]
    upright(g, torso, cut=.45)
    # Two vents stacked on the centre line, the pair centred between the bottom of the chin (50.3) and the
    # bottom of the torso (36).
    for low, high in ((38.65, 42.65), (43.65, 47.65)):
        vent(g, lofted_face(torso), 0, 4, low, high)
        vent(g, lofted_face(torso, rear=True), 0, 4, low, high, rear=True)
    for side, arm, leg in ((-1, 'LA', 'LL'), (1, 'RA', 'RL')):
        x = side*8
        g.joint(leg, (x, 0, 30), 'pelvis')
        g.joint(leg+'-shin', (x*1.12, 0, 18), leg)
        # Legs at the weight of the other hundred-tonners: wider than any lighter Mek's.
        # The top of the thigh tapers in so its outer edge meets the corner of the waist block.
        upright(g, [(19, 10, 11, x*1.12, 0), (24, 13, 13, x, 0), (27.5, 9.5, 12, side*6.8, 0),
                    (30, 9.5, 12, side*6.8, 0)], leg, cut=0)
        g.box((x*1.12, 1, 18), (10, 11, 5), leg+'-shin', 'metal')
        upright(g, [(4, 10.5, 11, x*1.18, 0), (16.3, 13, 13, x*1.12, 0)], leg+'-shin', cut=.45)
        # The foot is as wide as the shin above it, so it stands under the leg instead of spilling out past it.
        foot(g, x*1.18, 2, 11, 17, leg+'-shin')
        # Rounded shoulder caps, straight upper arms, long gauntlets and closed fists.
        forearm, hand = arm, arm
        if g.modular:
            g.joint(arm, (side*16.5, 0, 47), 'CT')
            g.joint(arm+'-forearm', (side*19.5, 1, 38), arm)
            forearm, hand = arm+'@forearm', arm+'@hand'
        upright(g, [(45, 13, 14, side*16.5, 0), (53, 15, 16, side*15.5, 0),
                    (57.5, 9, 11, side*14.5, 0)], arm, cut=.65)
        g.beam((side*16.5, 0, 47), (side*19.5, 1, 38), 9, 9, arm, 'metal')
        upright(g, [(27, 11, 12, side*19.5, 3), (39, 12, 12, side*19.5, 1)], forearm, cut=0)
        g.box((side*19.5, 3.5, 25.3), (9, 9, 5.5), hand, 'metal')
        panel(g, [(side*19.5-2.8, 8.03, 26.4), (side*19.5+2.8, 8.03, 26.4),
                  (side*19.5+2.8, 8.03, 24.2), (side*19.5-2.8, 8.03, 24.2)], hand, 'edge')
    # Skull: broad brow, tapered cheeks/jaw, paired sockets and a toothed mouth. Set 2.5 further forward than
    # it was, so the face still stands proud of the deeper chest instead of sinking into it.
    ahead = 2.5
    forward(g, [(-2+ahead, 8, 9, 0, 55.5), (3+ahead, 10, 10, 0, 55.5),
                (6.7+ahead, 7.8, 8.4, 0, 54.5)], 'HD', cut=.65)
    for side in (-1, 1):
        x = side*2.15
        panel(g, [(x-1.5, 6.73+ahead, 56.8), (x+1.5, 6.73+ahead, 56.8),
                  (x+1.2, 6.73+ahead, 54.8), (x-1.1, 6.73+ahead, 54.8)], 'HD')
        panel(g, [(x-.7, 6.76+ahead, 56.2), (x+.7, 6.76+ahead, 56.2),
                  (x+.7, 6.76+ahead, 55.6), (x-.7, 6.76+ahead, 55.6)], 'HD', 'glass')
    # The nose: a triangle at its base, and a thin bridge rising from it between the eyes to their top edge.
    panel(g, [(-.9, 6.76+ahead, 53.6), (0, 6.76+ahead, 54.7), (.9, 6.76+ahead, 53.6)], 'HD')
    panel(g, [(-.18, 6.76+ahead, 56.8), (.18, 6.76+ahead, 56.8),
              (.18, 6.76+ahead, 54.4), (-.18, 6.76+ahead, 54.4)], 'HD')
    panel(g, [(-2.4, 6.73+ahead, 53.1), (2.4, 6.73+ahead, 53.1),
              (1.8, 6.73+ahead, 51.6), (-1.8, 6.73+ahead, 51.6)], 'HD')
    for x in (-1.45, 0, 1.45):
        panel(g, [(x-.38, 6.77+ahead, 53), (x+.38, 6.77+ahead, 53),
                  (x+.38, 6.77+ahead, 51.75), (x-.38, 6.77+ahead, 51.75)], 'HD', 'paint')
    # A gorget: a thin sheet of armour on each side of the lower face. Each plate starts at the cheekbone, level
    # with the bottom of the eye sockets, drops almost straight down beside the cheek, then turns in at about
    # 45 degrees to run parallel with the jawline down to the collarbone. Nothing crosses under the chin.
    for side in (-1, 1):
        upright(g, [(49.5, .8, 5, side*2.8, 6.8), (51.9, .8, 5.5, side*5.2, 6.5),
                    (54.2, .8, 5, side*5.8, 6.5)], 'HD', 'edge', cut=0)
    # The satellite dish on the head's right, facing forward: a short stalk off the crown meets the back of the
    # dish, and a smaller dish of the same shape sits inside it as the receiver.
    g.beam((4.2, 1.6, 58), (6.6, 2, 59.4), 1, 1, 'HD', 'metal', 4)
    forward(g, [(2.4, 3.8, 3.8, 6.6, 59.4), (3.3, 4.2, 4.2, 6.6, 59.4)], 'HD', 'edge', cut=.3)
    forward(g, [(3.2, 1.7, 1.7, 6.6, 59.4), (3.8, 2, 2, 6.6, 59.4)], 'HD', 'metal', cut=.3)


def claw_foot(g, x, y, group, width=1.4, length=6):
    """Three toes splayed forward and a spur behind, the bird foot of a reverse-jointed Mek."""
    if g.modular:
        parent = group
        group = group.removesuffix('-shin')+'-foot'
        g.joint(group, (x, y, 2), parent)
    for angle, reach in ((-.6, length), (0, length*1.1), (.6, length), (pi, length*.55)):
        dx, dy = sin(angle), cos(angle)
        ring = [(x-dy*width/2, y+dx*width/2), (x+dy*width/2, y-dx*width/2), (x+dx*reach, y+dy*reach)]
        g.prism(ring, 0, 1.8, group, 'paint', .6)


def locust(g):
    # Twenty tons and the smallest Mek in the set: a pod on two short, splayed, reverse-jointed legs. The pod is
    # most of the Mek, as on the miniature, and is built in three pieces as QA drew it from the front: a wide deck
    # squared off across the top and reaching out to the gun pods, a six-sided cockpit hull below it that narrows
    # under the deck, flares out at the lower window and tapers to a keel, and a rounded chin turret under the keel
    # that carries the centre weapons. A spine runs along the deck with a short antenna standing from it, and big
    # round actuator discs cover the hips.
    forward(g, [(-9.5, 11, 3.4, 0, 30.2), (-7, 11.6, 3.8, 0, 30.3), (4.5, 11.6, 3.8, 0, 30.3),
                (7.2, 10, 2.2, 0, 29.4)], 'CT', cut=.2)

    def hull(y, top, middle, bottom, top_half, middle_half, bottom_half):
        return [(-top_half, y, top), (top_half, y, top), (middle_half, y, middle),
                (bottom_half, y, bottom), (-bottom_half, y, bottom), (-middle_half, y, middle)]
    # The nose reaches well out past the deck, narrowing toward its tip, as the drawing has it.
    g.loft([hull(-8, 28.2, 23.6, 21.2, 3.4, 5.1, 2.5), hull(-4, 28.4, 23.2, 20.6, 3.8, 5.7, 2.8),
            hull(7, 28.4, 23.2, 20.6, 3.8, 5.7, 2.8), hull(10.5, 28.3, 23.2, 20.7, 3.7, 5.5, 2.7),
            hull(13.2, 25.6, 23.2, 21.6, 3.2, 4.8, 2.3)], 'CT')
    # The chin turret, rounded beneath and standing just proud of the nose, which the centre weapons fire from.
    forward(g, [(9.4, 3.8, 2.8, 0, 20.1), (13.8, 3.8, 2.8, 0, 20.1)], 'CT', 'edge', cut=.6)
    g.box((0, -2, 32.7), (2.4, 9, 1.1), 'CT', 'edge')
    for side in (-1, 1):
        # No flat frontage to spare on the nose, so the vents sit on the back of the deck.
        vent(g, capped_face(-9.5, rear=True), side*2.7, .8, 29.3, 31.1, rear=True)
    g.box((0, -1, 21.2), (8, 7, 3.6), 'pelvis', 'metal')
    # The cockpit is the front of the hull: a framed pane on the steep facet under the deck and a framed window
    # across the face below it, both set in a darker surround.
    def facet(y, lift):
        return 28.3 - (y-10.5)*2.7/2.7 + lift
    for lift, inset, material in ((.02, 0, 'edge'), (.05, .3, 'glass')):
        front = 13.2 + lift
        panel(g, [(-2.2+inset, front, 24.9-inset), (2.2-inset, front, 24.9-inset),
                  (2.2-inset, front, 22.7+inset), (-2.2+inset, front, 22.7+inset)], 'HD', material)
        near, far = 10.7+inset*.5, 13-inset*.5
        panel(g, [(-2.4+inset, near+lift, facet(near, lift)), (2.4-inset, near+lift, facet(near, lift)),
                  (2.2-inset, far+lift, facet(far, lift)), (-2.2+inset, far+lift, facet(far, lift))], 'HD', material)
    g.beam((0, -5, 33.2), (0, -5, 34.4), 1.8, 1.8, 'HD', 'metal', 8)
    g.beam((0, -5, 34.4), (0, -5.9, 40.5), .63, .63, 'HD', 'metal', taper=.3)
    for side, arm, leg in ((-1, 'LA', 'LL'), (1, 'RA', 'RL')):
        # A shallow backward knee, so the leg stands nearly straight rather than crouched.
        hip, knee, ankle = (side*8, -1, 20.5), (side*10, -2.5, 11.8), (side*11.5, 0, 3.2)
        g.joint(leg, hip, 'pelvis')
        g.joint(leg+'-shin', knee, leg)
        # The hip axle runs out of the pelvis into the disc, so the leg hangs from the body rather than beside it.
        g.beam((side*3.5, -1, 20.5), (side*6.8, -1, 20.5), 4.4, 4.4, 'pelvis', 'metal', 8)
        # The round hip actuator, a broad armoured disc on the outside of the hip with a hub at its centre.
        g.beam((side*6.5, -1, 20.5), (side*9.3, -1, 20.5), 9, 9, leg, 'paint', 8)
        g.beam((side*9.3, -1, 20.5), (side*9.8, -1, 20.5), 4, 4, leg, 'metal', 8)
        g.beam(hip, knee, 4.5, 6, leg, 'paint', taper=.75)
        g.beam((side*8.6, -2.5, 11.8), (side*11.4, -2.5, 11.8), 4, 4, leg+'-shin', 'metal', 8)
        g.beam(knee, ankle, 3.2, 4, leg+'-shin', 'edge', taper=.8)
        g.box((ankle[0], 0, 2.6), (2.6, 3.4, 2.4), leg+'-shin', 'metal')
        claw_foot(g, ankle[0], 0, leg+'-shin')
        # Gun pods hard against the ends of the deck: no forearms or hands.
        if g.modular:
            g.joint(arm, (side*5.85, .05, 30.15), 'CT')
        forward(g, [(-3.55, 3.6, 4.05, side*7.65, 30.15), (3.65, 3.6, 3.6, side*7.65, 30.15)], arm, cut=.2)


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


def panther(g):
    # Thirty-five tons, named for its head: a broad cat's skull with two ears, slanted visor eyes and a short
    # snout pushing forward below them. A big faceted chest over a narrow waist and a hip skirt, high blocky
    # shoulders, straight blocky legs on clawed feet. The right forearm is the particle cannon itself, a heavy
    # housing and barrel held forward with no hand; the variant's actual gun fits its muzzle. The left arm ends
    # in a hand. Drawn from the ilClan line drawing, with the colour render and the miniature for the front.
    # The chest is squared off at the top: full width straight up to the shoulders, tapering only below.
    # The lower chest is a vertical plate, so launchers stacked on it all sit flush on one flat face.
    torso = [(34, 12, 11.5, 0, .3), (40, 16, 11.5, 0, .3), (43.2, 16, 10.8, 0, .2)]
    upright(g, torso, cut=.2)
    # The chest top is dropped so the head sits in a recess. A collar cradles it: each side rises high toward the
    # shoulder, near eye level, and slopes down and in to a flat ledge under the chin.
    for side in (-1, 1):
        if side == 1:
            ring = [(3.2, 43.8), (7.6, 47.2), (7.6, 43.2), (2.8, 43.2)]
        else:
            ring = [(-7.6, 47.2), (-3.2, 43.8), (-2.8, 43.2), (-7.6, 43.2)]
        g.loft([[(x, y, z) for x, z in ring] for y in (-4.5, 4.6)], 'CT')
    g.box((0, 0, 32.4), (8, 7.5, 3.6), 'CT', 'metal')
    upright(g, [(24.2, 9, 7.5, 0, 0), (30.6, 10.5, 8.5, 0, 0)], 'pelvis', cut=.3)
    for side in (-1, 1):
        vent(g, lofted_face(torso), side*4.4, .8, 35.4, 37.8)
        vent(g, lofted_face(torso, rear=True), side*4.4, .9, 38.5, 41.5, rear=True)
    # The panther's head: one compact flat-topped block, no snout, a wide slanted visor in a dark surround, a small
    # chin plate, a round actuator at each cheek, and ears laid flat back along the top like an angry cat's.
    g.box((0, .5, 43.9), (4.5, 4.5, 1.6), 'HD', 'metal')
    forward(g, [(-3, 8.4, 5.4, 0, 47.4), (4.6, 8.2, 5, 0, 47.1)], 'HD', cut=.35)
    g.box((0, 3.9, 44.4), (4.2, 1.8, 1.1), 'HD', 'edge')
    for side in (-1, 1):
        for lift, inset, material in ((.03, 0, 'dark'), (.06, .2, 'glass')):
            eye = [(side*(3.5-inset), 4.6+lift, 48.6-inset), (side*(.25+inset), 4.6+lift, 47.7-inset),
                   (side*(.25+inset), 4.6+lift, 46.5+inset), (side*(3.3-inset), 4.6+lift, 47.2+inset)]
            panel(g, eye if side == -1 else list(reversed(eye)), 'HD', material)
        g.beam((side*4.2, .3, 47.2), (side*4.8, .3, 47.2), 2.2, 2.2, 'HD', 'metal', 6)
        # The ears lie flat along the top edges of the head, running straight back past it.
        g.beam((side*3.1, 1.2, 50.15), (side*3.2, -5.6, 50.9), 2.4, .7, 'HD', 'paint', 4, taper=.6)
    for side, arm, leg in ((-1, 'LA', 'LL'), (1, 'RA', 'RL')):
        x = side*6.5
        g.joint(leg, (x, 0, 27), 'pelvis')
        g.joint(leg+'-shin', (x*1.12, 0, 15.5), leg)
        # The thigh tapers in at the top to tuck under the corner of the hip skirt, then widens as it comes down.
        upright(g, [(16.5, 6, 7, x*1.1, 0), (22, 6.8, 7.6, x, 0), (26.5, 4.2, 6.2, side*3.9, 0)], leg, cut=.3)
        g.box((x*1.12, 0, 15.5), (5, 5.6, 3), leg+'-shin', 'metal')
        g.box((x*1.13, 3.9, 16.2), (5, 1.8, 5.5), leg+'-shin', 'paint')
        upright(g, [(6, 6, 6.8, x*1.25, 0), (14.5, 6.4, 7.2, x*1.14, 0)], leg+'-shin', cut=.3)
        # The foot: a faceted block bevelled along its top edges and tapering in toward the front, a dark ankle dome
        # a heel block, and two wide dark claws sloping down from the front face.
        fx, feet = x*1.3, leg+'-shin'
        if g.modular:
            feet = leg+'-foot'
            g.joint(feet, (fx, .2, 4), leg+'-shin')
        forward(g, [(-4, 6.6, 3.6, fx, 1.8), (5.4, 6, 3, fx, 1.5)], feet, cut=.35)
        g.beam((fx, .4, 3.4), (fx, .4, 5.8), 4.6, 4.6, feet, 'metal', 6, taper=.8)
        g.box((fx, -4.6, 1.2), (4, 1.6, 2.4), feet, 'paint')
        for dx in (-1.25, 1.25):
            forward(g, [(5.2, 1.8, 2.4, fx+dx, 1.6), (7.9, 1.5, 1.4, fx+dx, .7)], feet, 'metal', cut=0)
        # High blocky shoulders set against the chest, over a short upper arm hung close beside it.
        forearm, hand = arm, arm
        if g.modular:
            g.joint(arm, (side*8.6, 0, 44), 'CT')
            g.joint(arm+'-forearm', (side*11.1, .5, 33), arm)
            forearm, hand = arm+'@forearm', arm+'@hand'
        # Layered shoulder: a boxy lower block under a wider, flat top plate that overhangs outward and forward.
        upright(g, [(38.5, 6.4, 8, side*9.9, 0), (44.2, 6.8, 8.4, side*10.1, 0)], arm, cut=.2)
        upright(g, [(44.2, 8, 9.2, side*10.6, .3), (46.6, 8, 9.2, side*10.6, .3)], arm, cut=0)
        # An armoured upper arm under the shoulder rather than a bare rod.
        upright(g, [(33.5, 4.6, 5, side*11.0, .4), (39.2, 5, 5.4, side*10.6, .1)], arm, cut=0)
        if side == 1:
            # The gun forearm, held forward: a blocky housing ending in a plain closed fist. The gun
            # itself is the variant's weapon, bolted along the forearm's outer side and reaching past the fist.
            forward(g, [(-3.5, 5.6, 6, 11.1, 33), (2.8, 6.2, 6.6, 11.1, 33)], forearm, cut=.3)
            g.box((11.1, 4.6, 33), (5.4, 3.6, 5.8), forearm, 'paint')
        else:
            upright(g, [(26.5, 4.8, 5.2, -11.1, .5), (33, 5.2, 5.6, -11.1, .5)], forearm, cut=.3)
            # A hand in armour colour: the palm, a row of fingers curled under with dark seams between them, and a
            # thumb on the inner side.
            g.box((-11.1, .6, 25), (4.4, 4, 3), hand, 'paint')
            g.box((-11.1, 1.5, 22.6), (4, 2.6, 1.9), hand, 'paint')
            for dx in (-1, 0, 1):
                panel(g, [(-11.1+dx-.1, 2.82, 23.5), (-11.1+dx+.1, 2.82, 23.5), (-11.1+dx+.1, 2.82, 21.7),
                          (-11.1+dx-.1, 2.82, 21.7)], hand, 'dark')
            g.box((-8.7, 1.4, 24), (1.2, 2, 2.4), hand, 'paint')


def narrow(g, scale, socketed):
    """Scales the body across its width about the centre line, leaving height and depth alone. The sockets in the
    recipe are already given at the narrowed width, so joints placed from them are left as they are."""
    if scale == 1:
        return
    def across(point):
        return (point[0]*scale,) + tuple(point[1:])
    g.faces = [(tuple(across(point) for point in tri), group, material) for tri, group, material in g.faces]
    for emitter in g.emitters:
        emitter['position'] = across(emitter['position'])
    for name, pivot in g.pivots.items():
        if socketed.get(name) != pivot:
            g.pivots[name] = across(pivot)
    for arm, front in getattr(g, 'held_fronts', {}).items():
        g.held_fronts[arm] = across(front)


def grow(g, scale):
    """Scales the whole body evenly about the ground under its centre, keeping every proportion.

    The recipe's sockets stay in the unscaled units the body was authored in; the exporter scales them by the same
    amount, so a body can be resized to its class's height without re-measuring a single socket.
    """
    if scale == 1:
        return
    def larger(point):
        return tuple(value*scale for value in point)
    g.faces = [(tuple(larger(point) for point in tri), group, material) for tri, group, material in g.faces]
    for emitter in g.emitters:
        emitter['position'] = larger(emitter['position'])
    g.pivots = {name: larger(pivot) for name, pivot in g.pivots.items()}
    for arm, front in getattr(g, 'held_fronts', {}).items():
        g.held_fronts[arm] = larger(front)


# --- MiniMek draft urbanmech: generated by the BattleTech Unit Viewer; refine by hand ---
def urbanmech(g):
    # UrbanMech, version 1: generated from the Urbanmech draft v1, detail level High.
    # One lofted shape per body segment, fitted to measurements of the HBS model. A starting point for
    # review: replace these shapes with authored ones as the chassis is refined.
    g.joint('LL', (-6.77, 0, 21.27), 'pelvis')
    g.joint('LL-shin', (-6.99, 1.06, 11.86), 'LL')
    g.joint('RL', (6.77, 0, 21.27), 'pelvis')
    g.joint('RL-shin', (6.99, 1.06, 11.86), 'RL')
    left_foot, right_foot = 'LL-shin', 'RL-shin'
    if g.modular:
        g.joint('LL-foot', (-7.19, -1.08, 2.68), 'LL-shin')
        left_foot = 'LL-foot'
        g.joint('RL-foot', (7.19, -1.08, 2.68), 'RL-shin')
        right_foot = 'RL-foot'
        # Every variant fires its arm weapons from the end of the upper arm, so each arm is one pod hung on its
        # shoulder with no forearm or hand; the recipe's elbow socket places the forearm pivot at the pod's front.
        g.joint('LA', (-9, -.1, 32.7), 'CT')
        g.joint('RA', (9, -.1, 32.7), 'CT')
    # The body is one round barrel, as the line art draws it: straight sides 15.7 across and 15.9 deep, a short
    # rounded corner underneath curving in toward the waist, and the head tapering above it - from viewport
    # height the walls slope inward to a fairly flat top at 41.5 rather than rounding over into a dome. Sixteen
    # sides, turned half a step so a flat facet faces front, back and each side.
    body_centre_y = -0.3
    body_rings = [(26.5, 5.4, 5.5), (27.6, 7.2, 7.3), (29, 7.8, 7.9), (35.2, 7.85, 7.95),
                  (36.6, 7.5, 7.6), (39.3, 6.1, 6.2), (40.9, 5, 5.1), (41.5, 3.8, 3.9)]
    sides = 16
    g.loft([[(half_width*cos(2*pi*(index + .5)/sides), body_centre_y + half_depth*sin(2*pi*(index + .5)/sides), z)
             for index in range(sides)] for z, half_width, half_depth in body_rings], 'CT')
    # The flat armour plate across the lower front of the barrel, the art's most readable front feature. Its back
    # sits inside the curve so no gap shows at its edges; the centre-torso weapons mount on its face. It stands
    # half a unit proud of the barrel's front, halved at review.
    g.box((0, 6.4, 31.8), (8.4, 3.2, 7.6), 'CT', 'edge', .15)
    # The barrel is one shell, so it is split into real side torsos before anything else is added. The seam is
    # 3.5 from the centre line: the chest plate's middle stays CT and the curved flanks carrying the arms are LT
    # and RT, each a real region with its own front, back and top.
    split_torso_locations(g, seam=3.5)
    # The head is a band of the dome itself, not a block stuck on it: the five front facets between 36.9 and 39.1,
    # standing 0.12 proud of the dome so it reads flush while still being a separate HD region. It wraps round
    # to the side facets so the outer viewports can look sideways. Losing HD takes the band and every viewport,
    # leaving the dome behind.
    def dome_point(angle, z, stand):
        # A point on the dome's own facets at this height, pushed out by `stand` units.
        for (low_z, low_width, low_depth), (high_z, high_width, high_depth) in zip(body_rings, body_rings[1:]):
            if low_z <= z <= high_z:
                break
        ratio = (z - low_z)/(high_z - low_z)
        half_width = low_width + (high_width - low_width)*ratio
        half_depth = low_depth + (high_depth - low_depth)*ratio
        growth = 1 + stand/((half_width + half_depth)/2)
        return (half_width*growth*cos(angle), body_centre_y + half_depth*growth*sin(angle), z)

    band_angles = [2*pi*(index + .5)/sides for index in range(1, 7)]
    band_low, band_high = 36.9, 39.1
    outer_low = [dome_point(angle, band_low, .12) for angle in band_angles]
    outer_high = [dome_point(angle, band_high, .12) for angle in band_angles]
    inner_low = [dome_point(angle, band_low, -.4) for angle in band_angles]
    inner_high = [dome_point(angle, band_high, -.4) for angle in band_angles]
    for first in range(len(band_angles) - 1):
        second = first + 1
        g.face([outer_low[first], outer_low[second], outer_high[second], outer_high[first]], 'HD')
        g.face([inner_high[first], inner_high[second], inner_low[second], inner_low[first]], 'HD')
        g.face([outer_high[first], outer_high[second], inner_high[second], inner_high[first]], 'HD')
        g.face([inner_low[first], inner_low[second], outer_low[second], outer_low[first]], 'HD')
    g.face([outer_low[0], outer_high[0], inner_high[0], inner_low[0]], 'HD')
    g.face([inner_low[-1], inner_high[-1], outer_high[-1], outer_low[-1]], 'HD')
    # Four separate viewports, as the art's close-up draws them: two on the centre facet, parted by a pillar on the
    # centre line, and one on each side facet looking out sideways, with a plain armour facet between them.
    # Armour stays between the panes instead of one continuous slit. Each pane is glass inside a thin dark rim,
    # lying on its own facet. The side panes sit a little lower and shorter, following the head as it tapers.
    centre_angle = pi/2
    left_edge, right_edge = band_angles[2], band_angles[3]
    panes = [(band_angles[0], band_angles[1], 37.2, 38.7), (left_edge, centre_angle, 37.1, 38.9),
             (centre_angle, right_edge, 37.1, 38.9), (band_angles[4], band_angles[5], 37.2, 38.7)]
    for pane_start, pane_end, low, high in panes:
        pillar = (pane_end - pane_start)*.09
        pane_start, pane_end = pane_start + pillar, pane_end - pillar
        for inset, stand, material in ((0, .15, 'dark'), (.18, .18, 'glass')):
            rim = (pane_end - pane_start)*inset/2.5
            first, second = pane_start + rim, pane_end - rim
            bottom, top = low + inset, high - inset
            panel(g, [dome_point(first, bottom, stand), dome_point(second, bottom, stand),
                      dome_point(second, top, stand), dome_point(first, top, stand)], 'HD', material)
    # Two stub antennas toward the back of the crown, swept back at 45 degrees as the art draws them rather than
    # standing like HBS's tall wires. Each is 5.3 long, reaching past the back of the dome.
    # Metal, so they never count toward the body's height.
    for side in (-1, 1):
        g.beam((side*2.2, -3.8, 40.5), (side*2.4, -7.55, 44.25), .8, .8, 'CT', 'metal', taper=.6)
    # Armour packs high on the back of each side torso, where the HBS model carries its two back blocks. Each is a
    # flat face on an otherwise curved back, so the side torso's vent lies flat on its lower half, clear of the
    # jump jets the recipe mounts above it. The inner side stops at 3.6, outboard of the 3.5 seam, so each pack
    # belongs wholly to its own side torso.
    for side, location in ((-1, 'LT'), (1, 'RT')):
        g.box((side*4.9, -6.1, 36), (2.6, 3.8, 5.4), location, 'edge')
        vent(g, capped_face(-8, rear=True), side*4.9, .9, 33.9, 36.1, rear=True, group=location)
    # LL foot (measured)
    g.loft([
        [(-9.23, -4.96, 0.01), (-5.14, -4.96, 0.01), (-4.4, -4.21, 0.01), (-4.4, 5.85, 0.01), (-6.23, 7.69, 0.01), (-8.22, 7.69, 0.01), (-10, 5.91, 0.01), (-10, -4.19, 0.01)],
        [(-8.76, -5.38, 1.82), (-5.61, -5.38, 1.82), (-4.09, -3.85, 1.82), (-4.09, 5.26, 1.82), (-6.1, 7.28, 1.82), (-8.31, 7.28, 1.82), (-10.29, 5.3, 1.82), (-10.29, -3.85, 1.82)],
        [(-9.18, -5.37, 3.65), (-5.19, -5.37, 3.65), (-4.09, -4.26, 3.65), (-4.09, 3.31, 3.65), (-6.71, 5.94, 3.65), (-7.7, 5.94, 3.65), (-10.29, 3.35, 3.65), (-10.29, -4.26, 3.65)],
        [(-9.36, -5.23, 5.46), (-5.01, -5.23, 5.46), (-4.08, -4.3, 5.46), (-4.08, 1.74, 5.46), (-5.68, 3.34, 5.46), (-8.66, 3.34, 5.46), (-10.28, 1.72, 5.46), (-10.28, -4.31, 5.46)],
    ], left_foot)
    # LL shin (measured)
    g.loft([
        [(-5.26, -2.27, 15.05), (-9.01, -1.92, 15.05), (-9.92, -0.84, 14.82), (-9.41, 4.61, 13.54), (-8, 5.75, 13.24), (-5.64, 5.53, 13.24), (-3.9, 3.49, 13.68), (-4.37, -1.55, 14.87)],
        [(-5.41, -3.26, 11.12), (-9.27, -2.9, 11.12), (-10.61, -1.33, 10.79), (-10.23, 2.64, 9.85), (-8.01, 4.44, 9.38), (-5.83, 4.24, 9.38), (-3.33, 1.3, 10.01), (-3.62, -1.82, 10.75)],
        [(-4.91, -4.65, 7.27), (-9.74, -4.2, 7.27), (-10.8, -2.96, 7), (-10.28, 2.57, 5.7), (-8.45, 4.05, 5.32), (-5.31, 3.75, 5.32), (-3.24, 1.32, 5.84), (-3.71, -3.68, 7.02)],
        [(-5.3, -3.58, 2.86), (-9.84, -3.15, 2.86), (-10.69, -2.16, 2.65), (-10.37, 1.24, 1.85), (-9.46, 1.98, 1.66), (-4.31, 1.5, 1.66), (-3.48, 0.52, 1.87), (-3.75, -2.33, 2.54)],
    ], 'LL-shin')
    # LL thigh (measured)
    g.loft([
        [(-5.08, -2.38, 24.67), (-8.22, -2.38, 24.67), (-9.04, -1.55, 24.67), (-9.04, 1.14, 24.67), (-8, 2.18, 24.67), (-4.74, 2.18, 24.67), (-3.44, 0.87, 24.67), (-3.44, -0.73, 24.67)],
        [(-5.3, -3.19, 20.29), (-8.06, -3.19, 20.29), (-9.63, -1.62, 20.29), (-9.63, 1.69, 20.29), (-7.66, 3.65, 20.29), (-5.73, 3.65, 20.29), (-2.93, 0.85, 20.29), (-2.93, -0.82, 20.29)],
        [(-6.38, -2.27, 15.91), (-7.68, -2.27, 15.91), (-9.13, -0.82, 15.91), (-9.13, 2.7, 15.91), (-7.97, 3.86, 15.91), (-5.75, 3.86, 15.91), (-5.07, 3.18, 15.91), (-5.07, -0.95, 15.91)],
        [(-5.39, -0.64, 11.53), (-8.48, -0.64, 11.53), (-8.79, -0.32, 11.53), (-8.79, 1.74, 11.53), (-7.33, 3.21, 11.53), (-6.59, 3.21, 11.53), (-5.17, 1.78, 11.53), (-5.17, -0.42, 11.53)],
    ], 'LL')
    # pelvis shell (measured)
    g.loft([
        [(-2.65, -2.22, 17.92), (2.65, -2.22, 17.92), (4.33, -0.54, 17.92), (4.33, 2.58, 17.92), (3.13, 3.78, 17.92), (-3.13, 3.78, 17.92), (-4.33, 2.58, 17.92), (-4.33, -0.54, 17.92)],
        [(-3.32, -2.83, 21.35), (3.32, -2.83, 21.35), (4.39, -1.76, 21.35), (4.39, 2.37, 21.35), (2.24, 4.52, 21.35), (-2.24, 4.52, 21.35), (-4.39, 2.37, 21.35), (-4.39, -1.76, 21.35)],
        [(-2.35, -4.81, 24.79), (2.35, -4.81, 24.79), (4.27, -2.9, 24.79), (4.27, 2.48, 24.79), (2.29, 4.46, 24.79), (-2.29, 4.46, 24.79), (-4.27, 2.48, 24.79), (-4.27, -2.9, 24.79)],
        [(-3.39, -3.64, 28.22), (3.39, -3.64, 28.22), (4.04, -2.99, 28.22), (4.04, 2.62, 28.22), (3.22, 3.44, 28.22), (-3.22, 3.44, 28.22), (-4.04, 2.62, 28.22), (-4.04, -2.99, 28.22)],
    ], 'pelvis')
    # Short shoulder stubs on the flanks of the barrel carry the arms. Each belongs to its side torso and stops at
    # 9 from the centre line, where its pod starts: an arm flip turns the pod about the shoulder's left-right
    # axis, which never changes x, so a pod flush with its stub at rest stays flush all the way round.
    for side, location in ((-1, 'LT'), (1, 'RT')):
        g.beam((side*7.2, -.1, 32.7), (side*9, -.1, 32.7), 3.4, 3.4, location, 'edge', 8)
    # The right arm is the art's cannon: a drum housing hung on the shoulder and a long barrel reaching forward,
    # capped with a thicker muzzle ring. Whatever a variant carries in this arm leaves from that muzzle, so an
    # AC/10, a PPC or a large laser all read as the same big gun.
    # The housing was made a quarter taller at review, 8 high instead of 6.4. It grows evenly above and below
    # the barrel's line, so the barrel and every weapon leaving it stay centred on the housing.
    forward(g, [(-6.5, 4.2, 7, 11.3, 32.7), (-4.5, 4.6, 8, 11.3, 32.7), (2, 4.6, 8, 11.3, 32.7),
                (3.5, 4, 6.75, 11.3, 32.7)], 'RA', cut=.35)
    g.beam((11.3, 3.4, 32.7), (11.3, 9.6, 32.7), 3.2, 3.2, 'RA', 'paint', 8)
    g.beam((11.3, 9.2, 32.7), (11.3, 10.6, 32.7), 3.8, 3.8, 'RA', 'edge', 8)
    # The left arm is the art's square pod: slimmer than the cannon, half again as tall as it is wide, with the
    # weapons stacked over-under on its front face.
    forward(g, [(-5.5, 3.2, 6.8, -10.7, 33.2), (3.5, 3.4, 7.2, -10.7, 33.2), (5.6, 3, 6.4, -10.7, 33.2)], 'LA', cut=.2)
    # RL foot (measured)
    g.loft([
        [(10, -4.19, 0.01), (10, 5.91, 0.01), (8.22, 7.69, 0.01), (6.23, 7.69, 0.01), (4.4, 5.85, 0.01), (4.4, -4.21, 0.01), (5.14, -4.96, 0.01), (9.23, -4.96, 0.01)],
        [(10.29, -3.85, 1.82), (10.29, 5.3, 1.82), (8.31, 7.28, 1.82), (6.1, 7.28, 1.82), (4.09, 5.26, 1.82), (4.09, -3.85, 1.82), (5.61, -5.38, 1.82), (8.76, -5.38, 1.82)],
        [(10.29, -4.26, 3.65), (10.29, 3.35, 3.65), (7.7, 5.94, 3.65), (6.71, 5.94, 3.65), (4.09, 3.31, 3.65), (4.09, -4.26, 3.65), (5.19, -5.37, 3.65), (9.18, -5.37, 3.65)],
        [(10.28, -4.31, 5.46), (10.28, 1.72, 5.46), (8.66, 3.34, 5.46), (5.68, 3.34, 5.46), (4.08, 1.74, 5.46), (4.08, -4.3, 5.46), (5.01, -5.23, 5.46), (9.36, -5.23, 5.46)],
    ], right_foot)
    # RL shin (measured)
    g.loft([
        [(4.37, -1.55, 14.87), (3.9, 3.49, 13.68), (5.64, 5.53, 13.24), (8, 5.75, 13.24), (9.41, 4.61, 13.54), (9.92, -0.84, 14.82), (9.01, -1.92, 15.05), (5.26, -2.27, 15.05)],
        [(3.62, -1.82, 10.75), (3.33, 1.3, 10.01), (5.83, 4.24, 9.38), (8.01, 4.44, 9.38), (10.23, 2.64, 9.85), (10.61, -1.33, 10.79), (9.27, -2.9, 11.12), (5.41, -3.26, 11.12)],
        [(3.71, -3.68, 7.02), (3.24, 1.32, 5.84), (5.31, 3.75, 5.32), (8.45, 4.05, 5.32), (10.28, 2.57, 5.7), (10.8, -2.96, 7), (9.74, -4.2, 7.27), (4.91, -4.65, 7.27)],
        [(3.75, -2.33, 2.54), (3.48, 0.52, 1.87), (4.31, 1.5, 1.66), (9.46, 1.98, 1.66), (10.37, 1.24, 1.85), (10.69, -2.16, 2.65), (9.84, -3.15, 2.86), (5.3, -3.58, 2.86)],
    ], 'RL-shin')
    # RL thigh (measured)
    g.loft([
        [(3.44, -0.73, 24.67), (3.44, 0.87, 24.67), (4.74, 2.18, 24.67), (8, 2.18, 24.67), (9.04, 1.14, 24.67), (9.04, -1.55, 24.67), (8.22, -2.38, 24.67), (5.08, -2.38, 24.67)],
        [(2.93, -0.82, 20.29), (2.93, 0.85, 20.29), (5.73, 3.65, 20.29), (7.66, 3.65, 20.29), (9.63, 1.69, 20.29), (9.63, -1.62, 20.29), (8.06, -3.19, 20.29), (5.3, -3.19, 20.29)],
        [(5.07, -0.95, 15.91), (5.07, 3.18, 15.91), (5.75, 3.86, 15.91), (7.97, 3.86, 15.91), (9.13, 2.7, 15.91), (9.13, -0.82, 15.91), (7.68, -2.27, 15.91), (6.38, -2.27, 15.91)],
        [(5.17, -0.42, 11.53), (5.17, 1.78, 11.53), (6.59, 3.21, 11.53), (7.33, 3.21, 11.53), (8.79, 1.74, 11.53), (8.79, -0.32, 11.53), (8.48, -0.64, 11.53), (5.39, -0.64, 11.53)],
    ], 'RL')
    # The legs are 10 per cent shorter than HBS measured, at review: the thigh and the shin each lose a tenth of
    # their length, the feet keep their size and stay on the ground, and everything above the hips drops by the
    # 1.86 the legs lost. The shapes above are authored at HBS's heights and moved here; the recipe already gives
    # the lowered hip and sockets.
    ankle, knee, hip = 2.68, 11.86, 21.27
    leg_scale = .9
    lowered_knee = ankle + (knee - ankle)*leg_scale
    lowered_hip = lowered_knee + (hip - knee)*leg_scale
    drop = hip - lowered_hip

    def lowered(point, group):
        x, y, z = point
        if group.endswith('-foot') or z <= ankle:
            return point
        if group.endswith('-shin'):
            return (x, y, ankle + (z - ankle)*leg_scale)
        if group in ('LL', 'RL'):
            return (x, y, lowered_knee + (z - knee)*leg_scale)
        return (x, y, z - drop)

    g.faces = [(tuple(lowered(point, group) for point in triangle), group, material)
               for triangle, group, material in g.faces]
    for name in ('LL', 'RL', 'LL-shin', 'RL-shin', 'LA', 'RA'):
        if name in g.pivots:
            g.pivots[name] = lowered(g.pivots[name], name)
# --- end of MiniMek draft urbanmech ---


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
                'battlemaster': battlemaster, 'panther': panther,
                'urbanmech': urbanmech}
    socketed = dict(g.pivots)
    builders[recipe['id']](g)
    if modular:
        for arm in recipe.get('heldWeapons', []):
            held_housing(g, arm)
    narrow(g, recipe.get('widthScale', 1), socketed)
    if modular:
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
    # Last, so a joint added above from a recipe socket, such as a forearm for an arm that has none, is resized with
    # everything else. Resizing earlier left those joints at the unscaled height.
    grow(g, recipe.get('bodyScale', 1))
    return g
