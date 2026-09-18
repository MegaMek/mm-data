"""Four deliberately simple silhouettes, authored against the repository's Mek illustrations.

These are chassis anatomy, not equipment or game rules. The variant assembler adds
the actual guns and launchers. +Y faces forward; all dimensions are authoring units.
"""
from unit_model_geometry import Geometry


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
    upright(g, [(0, width, length, x, y), (4, width*.78, length*.68, x, y-1)], group, cut=0)


def toes(g, x, y, group, width=3, length=8):
    # Two splayed toes create the bird-foot outline with sixteen triangles.
    for side in (-1, 1):
        ring = [(x+side*1.2-width/2, y-1), (x+side*1.2+width/2, y-1),
                (x+side*3.4, y+length)]
        g.prism(ring, 0, 2.3, group, 'paint', .68)


def atlas(g):
    g.box((0, 0, 31), (17, 9, 6), 'pelvis', 'edge')
    g.box((0, 0, 36), (13, 9, 6), 'CT', 'metal')
    upright(g, [(36, 18, 10, 0, 0), (46, 28, 14, 0, 0), (53, 25, 12, 0, 0)], cut=.45)
    for side, arm, leg in ((-1, 'LA', 'LL'), (1, 'RA', 'RL')):
        x = side*8
        g.joint(leg, (x, 0, 30), 'pelvis')
        g.joint(leg+'-shin', (x*1.12, 0, 18), leg)
        upright(g, [(19, 6.7, 8, x*1.12, 0), (30, 9, 9, x, 0)], leg, cut=0)
        g.box((x*1.12, 1, 18), (7, 8, 4), leg+'-shin', 'metal')
        upright(g, [(4, 7, 8, x*1.18, 0), (16.3, 10, 10, x*1.12, 0)], leg+'-shin', cut=.45)
        foot(g, x*1.18, 2, 10, 13, leg+'-shin')
        # Rounded shoulder caps, straight upper arms, long gauntlets and closed fists.
        upright(g, [(46, 10, 11, side*18, 0), (53, 12, 13, side*17, 0),
                    (57, 7, 9, side*16, 0)], arm, cut=.65)
        g.beam((side*18, 0, 47), (side*21, 1, 38), 7, 7, arm, 'metal')
        upright(g, [(28, 8, 9, side*21, 3), (39, 9, 9, side*21, 1)], arm, cut=0)
        g.box((side*21, 3.5, 26), (6.5, 7, 4), arm, 'metal')
        panel(g, [(side*21-2, 7.03, 27), (side*21+2, 7.03, 27),
                  (side*21+2, 7.03, 25), (side*21-2, 7.03, 25)], arm, 'edge')
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
        g.beam((side*5, -1, 39), (side*12, -1, 39), 3, 3, arm, 'metal')
        forward(g, [(-4, 4.5, 5, side*13, 39.5), (3, 4.5, 4, side*13, 39)], arm, cut=0)


def warhammer(g):
    g.box((0, 0, 29), (16, 8, 6), 'pelvis', 'edge')
    g.box((0, 0, 34), (9, 7, 6), 'CT', 'metal')
    forward(g, [(-6, 22, 12, 0, 43), (3, 23, 14, 0, 43),
                (7, 18, 9, 0, 41.5)], cut=0)
    forward(g, [(-3, 7, 6, 0, 49), (4, 8, 5, 0, 48), (6, 6, 3, 0, 46.5)], 'HD', cut=0)
    panel(g, [(-2.6, 6.04, 47.4), (2.6, 6.04, 47.4),
              (2.6, 6.04, 46.1), (-2.6, 6.04, 46.1)], 'HD', 'glass')
    for side, arm, leg in ((-1, 'LA', 'LL'), (1, 'RA', 'RL')):
        x = side*7.5
        g.joint(leg, (x, 0, 29), 'pelvis')
        g.joint(leg+'-shin', (side*9, 0, 18), leg)
        g.beam((x, 0, 29), (side*9, 0, 19), 9, 10, leg, 'edge')
        g.box((side*9, 1.5, 18), (7, 8, 4), leg+'-shin', 'metal')
        upright(g, [(4, 7, 8, side*9.7, 0), (16.3, 9, 9, side*9, 0)], leg+'-shin', cut=.35)
        foot(g, side*9.7, 2, 9, 12, leg+'-shin')
        upright(g, [(43, 11, 10, side*15, 0), (49, 12, 10, side*14, -1)], arm, cut=0)
        g.beam((side*16, 0, 44), (side*20, -1, 34), 5, 5, arm, 'metal')
        # Broad cannon gauntlets, terminating in sockets for the actual variant weapons.
        forward(g, [(-4, 6, 7, side*20, 33), (4, 8, 8, side*20, 32),
                    (9, 5, 5, side*20, 32)], arm, cut=0)
    # The left searchlight balances the equipment-driven right shoulder launcher.
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
        points = [(side*.6, 2, 46.96), (side*3.9, 2, 46.96),
                  (side*2.6, 10, 42.2), (side*.6, 10, 42.2)]
        panel(g, list(reversed(points)) if side == -1 else points, 'HD', 'glass')
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
        g.box((side*14, -5, 42), (7, 8, 13), torso, 'edge')
        g.beam((side*14, -4, 40), (side*21, -3, 32), 5, 6, arm, 'metal')
        forward(g, [(-5, 6, 10, side*21, 31), (7, 6, 9, side*21, 31)], arm, cut=.35)


def build_chassis(recipe):
    g = Geometry()
    hip = recipe['hip']
    g.joint('pelvis', (hip[0]-42, 36-hip[1], hip[2]))
    g.joint('CT', g.pivots['pelvis'], 'pelvis')
    for location in ('LT', 'RT', 'HD', 'LA', 'RA'):
        x, y, z = recipe['sockets'][location]
        g.joint(location, (x-42, 36-y, z), 'CT')
    builders = {'atlas': atlas, 'locust': locust, 'warhammer': warhammer, 'mad-cat': mad_cat}
    builders[recipe['id']](g)
    return g
