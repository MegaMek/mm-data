def rifleman(g):
    # A sixty-ton gun platform: light-footed legs under a boxy torso, a swept radar blade standing
    # clear on its mast, and a long slim weapon pod beside each shoulder. No variant carries a hand
    # or a lower arm, so an arm is the pod itself and its guns leave the armour at its stepped face.
    g.box((0, -1, 29), (15, 11, 6), 'pelvis', 'edge')
    upright(g, [(30, 15.5, 13, 0, -1), (36, 18.5, 14.5, 0, -1), (44.5, 17, 13, 0, -1.5)], cut=.3)
    torso = [(30, 15.5, 13, 0, -1), (36, 18.5, 14.5, 0, -1), (44.5, 17, 13, 0, -1.5)]
    for side in (-1, 1):
        # Two vents on the front, two on the back, both inside the flat part of the torso skin.
        vent(g, lofted_face(torso), side*3.75, 2.15, 30.5, 33)
        vent(g, lofted_face(torso, rear=True), side*3.75, 2.15, 34, 36.5, rear=True)
    # A compact angular cockpit fills the front of the torso rather than sitting in a recess.
    forward(g, [(3, 9.5, 9, 0, 37.5), (10, 8.5, 8, 0, 37.2), (15, 6.5, 5.6, 0, 36.7)], 'HD', cut=.3)
    panel(g, [(-2.7, 15.05, 38.2), (2.7, 15.05, 38.2), (2.7, 15.05, 35.3), (-2.7, 15.05, 35.3)], 'HD', 'glass')
    # Search radar: the mast lifts the swept blade clear of the pods so it reads from every side.
    g.box((0, -5, 47.5), (5, 5, 6), 'CT', 'metal')
    g.prism([(-10.5, -8.5), (10.5, -4), (10.5, .5), (-10.5, -4)], 50.4, 53, 'CT', 'edge')
    for side, arm, leg, torso in ((-1, 'LA', 'LL', 'LT'), (1, 'RA', 'RL', 'RT')):
        x = side*7.5
        g.joint(leg, (x, 0, 29), 'pelvis')
        g.joint(leg+'-shin', (x*1.05, -1, 16.5), leg)
        # Sixty tons: the legs stay lighter than the seventy-ton designs already in this file.
        upright(g, [(16.5, 8, 9.5, x*1.05, -1), (29, 10, 10.5, x, 0)], leg, cut=.3)
        g.box((side*11.5, -1, 23.5), (2.8, 9, 9.5), leg, 'edge', .45)
        g.box((x*1.05, 0, 16.5), (8, 9, 4), leg+'-shin', 'metal')
        upright(g, [(5, 8.5, 9.5, x*1.1, 0), (14, 9.5, 10, x*1.05, -.5)], leg+'-shin', cut=.35)
        foot(g, x*1.1, 2.5, 9.5, 13, leg+'-shin')
        # The shoulder runs deep enough to sit under the whole pod, so nothing overhangs at the back.
        upright(g, [(34, 11, 15, side*11.5, -1.5), (42, 12, 15, side*11.5, -1.5)], torso, cut=.25)
        if g.modular:
            g.joint(arm, (side*15.5, 0, 41.5), 'CT')
        # The pod stands half again as tall as it is wide, so its paired guns sit one above the
        # other behind a muzzle face of the same proportion. It keeps its lower edge on the
        # shoulder and loses its extra height off the top.
        forward(g, [(-7, 7, 10.6, side*15, 40), (2, 8, 11.8, side*15, 40),
                    (10, 7, 10.6, side*15, 40), (14, 5.2, 7.8, side*15, 40)], arm, cut=.15)
