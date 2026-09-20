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
