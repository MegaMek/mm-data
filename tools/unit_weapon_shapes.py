"""Standard looks and sizes for the equipment drawn on unit models.

The rules live in tools/unit-models/weapons.json. They are defaults: a chassis recipe adjusts them with
its weaponOverrides list after the result has been compared with that Mek's artwork. The catalog owns
what a variant carries and where; this module only decides what each item looks like.
"""
from copy import deepcopy
from math import ceil, cos, pi, sin
import json
from pathlib import Path
import re

from unit_model_geometry import Geometry, add, cross, mul, normal, sub

RULES_PATH = Path(__file__).resolve().parent / 'unit-models/weapons.json'


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate equipment art key: '+key)
        result[key] = value
    return result


BOOK = json.loads(RULES_PATH.read_text(encoding='utf-8'), object_pairs_hook=unique_object)
# Above this many rounds the face is a launcher symbol, not one opening per round.
MAXIMUM_TUBES = 20
# Sides and the angle of the first vertex. A square sits flat; a diamond is the same square stood on a corner.
TUBE_SHAPES = {'round': (8, pi/2), 'hex': (6, pi/2), 'square': (4, pi/4), 'diamond': (4, pi/2)}
# Launcher detail options, richest first. Large round-tube packs use six-sided ports to stay below 100 triangles;
# small packs retain eight sides. A panel is the last resort, rather than removing individual launcher exits.
DETAIL_LEVELS = ('full', 'reduced', 'panel')


def _matches(entry, mount):
    families = entry['family'] if isinstance(entry['family'], list) else [entry['family']]
    if mount['family'] not in families:
        return False
    if 'internalName' in entry and re.search(entry['internalName'], mount.get('internalName', '')) is None:
        return False
    return 'name' not in entry or re.search(entry['name'], mount['name'], re.IGNORECASE) is not None


def _override_matches(override, mount):
    if 'location' in override and override['location'] != mount['location']:
        return False
    if 'family' in override and override['family'] != mount['family']:
        return False
    if 'rear' in override and override['rear'] != mount['rear']:
        return False
    return 'name' not in override or re.search(override['name'], mount['name'], re.IGNORECASE) is not None


def rule_for(mount, recipe=None):
    """The standard look for one catalogued mount, or None when nothing is drawn for it yet."""
    base = next((entry for entry in BOOK['rules'] if _matches(entry, mount)), None)
    if base is None:
        return None
    rule = deepcopy(base)
    for modifier in BOOK['modifiers']:
        if rule['look'] != 'barrel' or not _matches(modifier, mount):
            continue
        for key, factor in modifier.get('scale', {}).items():
            rule[key] *= factor
        rule.update(modifier.get('set', {}))
        rule.setdefault('segments', []).extend(deepcopy(modifier.get('addSegments', [])))
    for override in (recipe or {}).get('weaponOverrides', []):
        if _override_matches(override, mount):
            rule.update({key: value for key, value in override.items()
                         if key not in ('location', 'family', 'rear', 'name', 'note')})
    if rule['look'] in ('barrel', 'gatling') and 'protrusion' not in rule:
        rule['protrusion'] = default_protrusion(mount, rule, recipe)
    return rule


def held_for(mount, rule):
    """Whether this weapon may be drawn as a gun gripped in the fist, as well as its usual barrel.

    Only a weapon a Mek can mount qualifies. Name matching alone also catches infantry and battle armor weapons
    such as gauss pistols and support PPCs, which share the words but are not the large weapons meant here.
    """
    return rule is not None and rule['look'] in ('barrel', 'gatling') and \
        'F_MEK_WEAPON' in mount.get('flags', ()) and \
        any(_matches(entry, mount) for entry in BOOK.get('held', []))


def default_protrusion(mount, rule, recipe=None):
    """How far a barrel stands out of the armor when neither the recipe nor an override says."""
    chosen = (recipe or {}).get('protrusion', {})
    location = mount['location']
    if location+':'+mount['family'] in chosen:
        return chosen[location+':'+mount['family']]
    if location in chosen:
        return chosen[location]
    return 'long' if location in ('LA', 'RA') else rule.get('torsoProtrusion', 'long')


def aim_for(mount, recipe=None):
    """The direction a front weapon at this hard point faces, or None for straight ahead.

    A weapon follows the limb it is mounted on: a forearm that hangs down carries a barrel that points down.
    The recipe's socketAim map is keyed by location, or by location and family, e.g. "LA" or "LA:ppc".
    """
    if mount['rear']:
        return None
    chosen = (recipe or {}).get('socketAim', {})
    location = mount['location']
    return chosen.get(location+':'+mount['family'], chosen.get(location))


def footprint(rule, mount, scale, options=None):
    """The width and height a mount takes up on the face it looks out of, or None when it is not laid out.

    Jump jets sit on the back of the body and hand weapons in the fist, so neither competes for face space.
    """
    look = rule['look']
    if look == 'launcher' and (options or {}).get('style') == 'drum':
        side = 2*drum_layout(rule, mount, scale)['lip']
        return side, side
    if look == 'launcher':
        options = options or {}
        grid = launcher_grid(rule, mount, scale, options.get('maximumColumns', 0),
                             options.get('orientation', 'horizontal'))
        return grid['width'], grid['height']
    if look == 'artillery-launcher':
        side = ARTILLERY_WIDTH*scale*rule.get('artilleryScale', 1)
        return side, side
    if look == 'barrel':
        widest = rule['width']*max([1]+[segment['width']*segment.get('taper', 1)
                                        for segment in rule.get('segments', [])])*scale
        return widest*(1+(rule.get('count', 1)-1)*1.15), widest
    if look == 'gatling':
        if 'housing' in rule:
            return rule['housing'][0]*scale, rule['housing'][2]*scale
        return rule['width']*1.15*scale, rule['width']*1.15*scale
    if look in ('pod', 'lamp'):
        return rule['size'][0]*scale, rule['size'][2]*scale
    return None


def bank_family(mount, rule):
    """Melee weapons share the hatchet's hand socket rather than needing a bank per weapon."""
    return rule.get('bankFamily', mount['family'])


def missile_style_for(location, recipe=None):
    """Whether launchers at this location are drawn as the usual box or as a round drum, and how long a drum.

    A recipe sets missileStyle for the whole Mek ("drum-long") or per location ({"RT": "drum-long",
    "default": "box"}). A drum is drum-short, drum-medium or drum-long; plain "drum" is drum-medium.
    """
    chosen = (recipe or {}).get('missileStyle', 'box')
    if not isinstance(chosen, str):
        chosen = chosen.get(location, chosen.get('default', 'box'))
    return 'drum-medium' if chosen == 'drum' else chosen


def orientation_for(mount, rule, recipe=None):
    """Whether a launcher at this hard point is mounted horizontal (wide) or vertical (tall)."""
    if 'orientation' in rule:
        return rule['orientation']
    chosen = (recipe or {}).get('missileOrientation', 'horizontal')
    if isinstance(chosen, str):
        return chosen
    return chosen.get(mount['location'], chosen.get('default', 'horizontal'))


def launcher_grid(rule, mount, scale, maximum_columns=0, orientation='horizontal'):
    """Lines of tube counts plus the launcher's face size. No line is left short when a full grid exists.

    The grid is worked out as a horizontal launcher; a vertical one is that same grid turned on its side.
    """
    tubes = BOOK['tubes'][rule['tubes']]
    visible = min(MAXIMUM_TUBES, rule.get('tubeCount', max(1, mount['rackSize'])))
    widest = min(maximum_columns or 5, visible)
    columns = next((across for across in range(widest, 1, -1) if visible % across == 0 and visible//across >= 2), None)
    if columns is None:
        # Five or seven tubes cannot fill a rectangle: two rows, with the short row centered under the long one.
        columns = visible if visible <= 3 else ceil(visible/2)
    rows = [min(columns, visible-start) for start in range(0, visible, columns)]
    tube_scale = scale*rule.get('tubeScale', 1)
    pitch = tubes['pitch']*tube_scale
    vertical = orientation == 'vertical'
    long_side, short_side = columns*pitch+scale, len(rows)*pitch+scale
    return {'lines': rows, 'vertical': vertical, 'pitch': pitch, 'diameter': tubes['diameter']*tube_scale,
            'shape': tubes['shape'], 'width': short_side if vertical else long_side,
            'height': long_side if vertical else short_side}


def _opening(geometry, center, radius, shape, direction, group, material):
    x, y, z = center
    sides, turn = TUBE_SHAPES[shape]
    points = [(x+radius*cos(turn+2*pi*i/sides), y, z+radius*sin(turn+2*pi*i/sides)) for i in range(sides)]
    geometry.face(list(reversed(points)) if direction == 1 else points, group, material)


# A drum launcher at scale 1: a long drum centred on its mount, lying front to back along the top of a shoulder like
# the Griffin's TRO launcher, the last .6 of it a lip slightly wider than the drum. The lengths are the whole drum's;
# at the Griffin's scale the medium drum overhangs its shoulder a little at the front and back.
# Eight sides keep an LRM 20 under the equipment triangle limit.
DRUM_LIP = .6
DRUM_LENGTHS = {'short': 12, 'medium': 15.5, 'long': 19}
DRUM_SIDES = 8
# Space between the outer ring of tubes and the drum's side, and how much wider the lip is than the drum.
DRUM_MARGIN, DRUM_FLARE = .7, 1.08


def drum_layout(rule, mount, scale):
    """Tube centres on a round face, as (across, up) offsets, and the drum's radius and lip radius.

    Up to six tubes form one ring; seven are one in the middle and six round it; more are an inner ring holding about
    three in ten of them inside an outer ring; past fourteen a single tube also sits in the middle.
    """
    tubes = BOOK['tubes'][rule['tubes']]
    visible = min(MAXIMUM_TUBES, rule.get('tubeCount', max(1, mount['rackSize'])))
    tube_scale = scale*rule.get('tubeScale', 1)
    pitch, diameter = tubes['pitch']*tube_scale, tubes['diameter']*tube_scale
    if visible <= 6:
        rings = [visible]
    elif visible == 7:
        rings = [1, 6]
    elif visible <= 14:
        inner = max(2, round(visible*.3))
        rings = [inner, visible-inner]
    else:
        middle = round((visible-1)*.35)
        rings = [1, middle, visible-1-middle]
    centres, radius = [], 0
    for index, count in enumerate(rings):
        if count == 1:
            ring_radius = 0
        else:
            # Neighbours on a ring are a pitch apart, and each ring clears the one inside it by a pitch.
            ring_radius = max(pitch/(2*sin(pi/count)), radius + pitch if index else 0)
        turn = pi/2 + (pi/count if index % 2 else 0)
        centres.extend((ring_radius*cos(turn + 2*pi*i/count), ring_radius*sin(turn + 2*pi*i/count))
                       for i in range(count))
        radius = ring_radius
    drum = radius + diameter/2 + DRUM_MARGIN*scale
    return {'centres': centres, 'diameter': diameter, 'shape': tubes['shape'], 'radius': drum,
            'lip': drum*DRUM_FLARE}


def _drum_launcher(geometry, mount, rule, position, scale, options):
    """A launcher drawn as a short drum lying front to back, its round face packed with tubes, on a small saddle."""
    x, y, z = position
    group = mount['location']
    direction = -1 if mount['rear'] else 1
    layout = drum_layout(rule, mount, scale)
    half = DRUM_LENGTHS[options.get('drumLength', 'medium')]/2

    def ring(along, radius):
        # Wound so the loft's front cap faces the way the launcher points.
        return [(x + radius*cos(pi/DRUM_SIDES - direction*2*pi*i/DRUM_SIDES), y + direction*along,
                 z + radius*sin(pi/DRUM_SIDES - direction*2*pi*i/DRUM_SIDES)) for i in range(DRUM_SIDES)]
    geometry.loft([ring(-half*scale, layout['radius']), ring((half-DRUM_LIP)*scale, layout['radius']),
                   ring(half*scale, layout['lip'])], group, 'paint')
    # The saddle it rests on runs most of its length.
    geometry.box((x, y, z - layout['radius']*.8), (layout['radius']*1.1, 1.2*half*scale, layout['radius']*.5),
                 group, 'metal')
    front = y + direction*(half + .02)*scale
    if options.get('detail') == 'panel':
        # The last resort: the whole face is one dark disc.
        corners = [(x + layout['radius']*.8*cos(pi/DRUM_SIDES + 2*pi*i/DRUM_SIDES), front,
                    z + layout['radius']*.8*sin(pi/DRUM_SIDES + 2*pi*i/DRUM_SIDES)) for i in range(DRUM_SIDES)]
        geometry.face(list(reversed(corners)) if direction == 1 else corners, group, 'dark')
        geometry.emitter((x, front, z), (0, direction, 0), group, 'launcher', 'cluster')
        return
    reduced = layout['shape'] == 'round' and (options.get('detail') == 'reduced' or len(layout['centres']) >= 15)
    for across, up in layout['centres']:
        centre = (x + across, front, z + up)
        _opening(geometry, centre, layout['diameter']/2, 'hex' if reduced else layout['shape'], direction, group,
                 'dark')
        geometry.emitter(centre, (0, direction, 0), group, 'launcher', 'missile')


def _launcher(geometry, mount, rule, position, scale, options):
    if options.get('style') == 'drum':
        _drum_launcher(geometry, mount, rule, position, scale, options)
        return
    x, y, z = position
    group = mount['location']
    direction = -1 if mount['rear'] else 1
    grid = launcher_grid(rule, mount, scale, options.get('maximumColumns', 0),
                         options.get('orientation', 'horizontal'))
    slope = options.get('slope', 0)
    # A leaning bay is built upright, then sheared about the bay's center so stacked launchers share one face.
    launcher = Geometry() if slope else geometry
    launcher.box((x, y-direction*2.3*scale, z), (grid['width'], 6*scale, grid['height']), group, 'paint')
    front = y+direction*.76*scale
    if options.get('detail') == 'panel':
        # The last resort: each launcher's tube face is one panel, not tube by tube.
        half_width = (grid['width']-scale)/2
        half_height = (grid['height']-scale)/2
        corners = [(x-half_width, front, z-half_height), (x+half_width, front, z-half_height),
                   (x+half_width, front, z+half_height), (x-half_width, front, z+half_height)]
        launcher.face(list(reversed(corners)) if direction == 1 else corners, group, 'dark')
    else:
        lines = grid['lines']
        for line, count in enumerate(lines):
            for place in range(count):
                along = (place-(count-1)/2)*grid['pitch']
                across = ((len(lines)-1)/2-line)*grid['pitch']
                # A vertical launcher's lines stand upright, the first one on the left, filled from the top.
                center = (x-across, front, z-along) if grid['vertical'] else (x+along, front, z+across)
                reduced = grid['shape'] == 'round' and (options.get('detail') == 'reduced' or sum(grid['lines']) >= 15)
                _opening(launcher, center, grid['diameter']/2, 'hex' if reduced else grid['shape'], direction,
                         group, 'dark')
                launcher.emitter(center, (0, direction, 0), group, 'launcher', 'missile')
    if options.get('detail') == 'panel':
        launcher.emitter((x, front, z), (0, direction, 0), group, 'launcher', 'cluster')
    if slope:
        origin = options.get('slopeOrigin', z)
        for triangle, node, material in launcher.faces:
            geometry.face([(point_x, point_y-direction*slope*(point_z-origin), point_z) for point_x, point_y, point_z in triangle], node, material)
        for emitter in launcher.emitters:
            px, py, pz = emitter['position']
            geometry.emitter((px, py-direction*slope*(pz-origin), pz), emitter['direction'],
                             emitter['node'], emitter['role'], emitter['effect'])


# An artillery launcher at scale 1: an 11 wide, 11 tall block about 9 deep (the Inner Sphere Arrow IV, 15 tons).
ARTILLERY_WIDTH = 11
# The block's front sits flush on the mount, so only the tube rims stand proud of the armor; it is .05 forward so it
# covers a limb end in the same plane instead of flickering with it. It is set low by the cylinders' height above
# it, so the whole launcher, cylinders included, is centered on the mount.
ARTILLERY_BODY = {'center': (0, -4.45, -.69), 'size': (11, 9, 9.4)}
# Five tubes in a dice-five pattern: two over one over two, each a short raised rim around a dark bore.
ARTILLERY_TUBES = ((-2.9, 2.6), (2.9, 2.6), (0, 0), (-2.9, -2.6), (2.9, -2.6))
ARTILLERY_RIM, ARTILLERY_BORE = 1.5, 1.1
ARTILLERY_FACE, ARTILLERY_LIP = .05, .65


def _artillery_launcher(geometry, mount, rule, position, scale, options):
    """A large artillery launcher such as the Arrow IV, drawn from its artwork rather than a tube grid.

    It is built facing forward and horizontal, with the two cylinders along the top. The vertical profile turns
    the whole launcher on its side, so the cylinders run down the outer face; the slope then leans it back.
    """
    x, y, z = position
    group = mount['location']
    direction = -1 if mount['rear'] else 1
    size = scale*rule.get('artilleryScale', 1)
    vertical = options.get('orientation', 'horizontal') == 'vertical'
    slope = options.get('slope', 0)
    origin = options.get('slopeOrigin', z)
    local = Geometry()
    body_x, body_y, body_z = ARTILLERY_BODY['center']
    width, depth, height = ARTILLERY_BODY['size']
    local.box(ARTILLERY_BODY['center'], ARTILLERY_BODY['size'], group, 'paint')
    face_z = body_z
    if options.get('detail') == 'panel':
        half_width, half_height = width/2-1, height/2-1
        front = ARTILLERY_FACE+.06
        local.face([(-half_width, front, face_z-half_height), (half_width, front, face_z-half_height),
                    (half_width, front, face_z+half_height), (-half_width, front, face_z+half_height)][::-1],
                   group, 'dark')
        local.emitter((0, front, face_z), (0, 1, 0), group, 'launcher', 'missile')
    else:
        sides, turn = TUBE_SHAPES['hex']
        for across, up in ARTILLERY_TUBES:
            center_z = face_z+up

            def ring(radius, front):
                return [(across+radius*cos(turn+2*pi*i/sides), front, center_z+radius*sin(turn+2*pi*i/sides))
                        for i in range(sides)]
            back, lip = ring(ARTILLERY_RIM, ARTILLERY_FACE), ring(ARTILLERY_RIM, ARTILLERY_LIP)
            for i in range(sides):
                j = (i+1) % sides
                local.face([lip[i], lip[j], back[j], back[i]], group, 'paint')
            local.face(lip[::-1], group, 'paint')
            local.face(ring(ARTILLERY_BORE, ARTILLERY_LIP+.03)[::-1], group, 'dark')
            local.emitter((across, ARTILLERY_LIP+.03, face_z+up), (0, 1, 0), group, 'launcher', 'missile')
        # Two cylinders half sunk into the top, front to back. Only the upper half is drawn: three faces and
        # a half-hexagon cap at each end.
        top = body_z+height/2
        for across in (-2.6, 2.6):
            arc = [(across+1.6*cos(pi*i/3), top+1.6*sin(pi*i/3)) for i in range(4)]
            rear_end, front_end = body_y-depth/2+.3, ARTILLERY_FACE+.3
            for i in range(3):
                local.face([(arc[i][0], front_end, arc[i][1]), (arc[i+1][0], front_end, arc[i+1][1]),
                            (arc[i+1][0], rear_end, arc[i+1][1]), (arc[i][0], rear_end, arc[i][1])], group, 'paint')
            local.face([(point_x, front_end, point_z) for point_x, point_z in arc][::-1], group, 'paint')
            local.face([(point_x, rear_end, point_z) for point_x, point_z in arc], group, 'paint')
        # A slotted vent on the left side: a dark recess behind three lit fins.
        side = body_x-width/2
        vent = [(-6, -3), (-1.5, -3), (-1.5, 1.5), (-6, 1.5)]
        local.face([(side-.06, vent_y, body_z+vent_z) for vent_y, vent_z in vent][::-1], group, 'dark')
        for fin in (-4.6, -3.75, -2.9):
            local.face([(side-.16, fin, body_z+1.5), (side-.16, fin+.35, body_z+1.5),
                        (side-.16, fin+.35, body_z-3), (side-.16, fin, body_z-3)], group, 'edge')

    def place(point):
        point_x, point_y, point_z = point
        if vertical:
            point_x, point_z = point_z, -point_x
        placed_y = y+direction*point_y*size
        placed_z = z+point_z*size
        return x+point_x*size, placed_y-direction*slope*(placed_z-origin), placed_z

    for triangle, node, material in local.faces:
        points = [place(point) for point in triangle]
        geometry.face(points if direction == 1 else points[::-1], node, material)
    for emitter in local.emitters:
        geometry.emitter(place(emitter['position']), (0, direction, 0), emitter['node'], emitter['role'],
                         emitter['effect'])


def _barrel(geometry, mount, rule, position, scale):
    x, y, z = position
    group = mount['location']
    direction = -1 if mount['rear'] else 1
    # Recessed is a port flat against the armor; short, medium and long stand progressively further out.
    length = rule['length']*scale*BOOK['protrusions'][rule.get('protrusion', 'long')]
    width = rule['width']*scale
    sides = rule.get('sides', 4)
    count = rule.get('count', 1)
    for barrel in range(count):
        barrel_x = x+(barrel-(count-1)/2)*width*1.15
        muzzle = y+length*direction
        geometry.beam((barrel_x, y-2*direction*scale, z), (barrel_x, muzzle, z), width, width, group, 'metal', sides,
               rule.get('taper', .85))
        tip_y, tip_width = muzzle, width*rule.get('taper', .85)
        for segment in rule.get('segments', []):
            back, front = min(segment['from']*scale, length), min(segment['to']*scale, length)
            if back-front < .2:
                # A shortened torso port has no room for this ring.
                continue
            start, end = muzzle-direction*back, muzzle-direction*front
            segment_width = width*segment['width']
            geometry.beam((barrel_x, start, z), (barrel_x, end, z), segment_width, segment_width, group, 'metal',
                   segment.get('sides', sides), segment.get('taper', 1))
            if (end-tip_y)*direction > 0:
                tip_y, tip_width = end, segment_width*segment.get('taper', 1)
        half = tip_width*rule.get('tipSize', .22)
        face_y = tip_y+direction*.03
        corners = [(barrel_x-half, face_y, z+half), (barrel_x+half, face_y, z+half),
                   (barrel_x+half, face_y, z-half), (barrel_x-half, face_y, z-half)]
        geometry.face(corners if direction == 1 else list(reversed(corners)), group, rule.get('tip', 'dark'))
        effect = {'laser': 'laser', 'ppc': 'ppc', 'flamer': 'flame'}.get(mount['family'], 'bullet')
        geometry.emitter((barrel_x, face_y, z), (0, direction, 0), group,
                         'beam' if effect == 'laser' else 'muzzle', effect)


def _held(geometry, mount, rule, position, scale):
    """The weapon's half of a gun held in the fist: its barrel and the feature that marks its family.

    The other half, the gun body, belongs to the chassis. It is generated to fit that chassis's own forearm, so
    one set of weapon shapes suits every Mek that holds guns. The origin is the centre of the body's front face,
    on the bore, and the barrel runs forward from there. Every size comes from the weapon's own barrel length and
    width, so a Heavy PPC carries a bigger barrel than a Light PPC. The model is built at its finished size: a
    recipe's barrel length override does not stretch it.
    """
    x, y, bore = position
    group = mount['location']
    length = rule['length']*scale
    width = rule['width']*scale
    # A collar where the barrel leaves the gun body, then the barrel.
    geometry.beam((x, y, bore), (x, y+length*.12, bore), width, width, group, 'edge', 6, 1)
    muzzle = y+length*.9
    geometry.beam((x, y+length*.1, bore), (x, muzzle, bore), width*.75, width*.75, group, 'metal', 6, 1)
    # One feature per family, so the families read apart at a glance while sharing every other part.
    # Six-sided rings and barrels keep every shape inside the equipment triangle budget.
    family = mount['family']
    if family == 'ppc':
        # Field coils ringing the barrel; the forward coil is also the muzzle ring.
        geometry.beam((x, muzzle-length*.35, bore), (x, muzzle-length*.27, bore), width, width, group, 'edge', 6, 1)
        sleeve = width
        geometry.beam((x, muzzle-length*.1, bore), (x, muzzle, bore), sleeve, sleeve, group, 'edge', 6, 1)
    elif family == 'ballistic' and re.search('Gauss', mount['name'], re.IGNORECASE):
        # Twin magnetic rails along either side of the barrel.
        for side in (-1, 1):
            geometry.box((x+side*width*.45, muzzle-length*.35, bore), (width*.2, length*.55, width*.28), group,
                         'edge')
        sleeve = width*.9
        geometry.beam((x, muzzle-length*.06, bore), (x, muzzle, bore), sleeve, sleeve, group, 'metal', 6, 1)
    elif family == 'laser':
        # A broad lens housing at the muzzle.
        sleeve = width*1.2
        geometry.beam((x, muzzle-length*.15, bore), (x, muzzle, bore), sleeve, sleeve, group, 'edge', 6, 1)
    else:
        # An autocannon: a plain heavy barrel ending in a thick muzzle ring.
        sleeve = width*1.1
        geometry.beam((x, muzzle-length*.2, bore), (x, muzzle, bore), sleeve, sleeve, group, 'metal', 6, 1)
    half = sleeve*.3
    face_y = muzzle+.03
    geometry.face([(x-half, face_y, bore+half), (x+half, face_y, bore+half),
                   (x+half, face_y, bore-half), (x-half, face_y, bore-half)], group, rule.get('tip', 'dark'))
    effect = {'laser': 'laser', 'ppc': 'ppc'}.get(mount['family'], 'bullet')
    geometry.emitter((x, face_y, bore), (0, 1, 0), group, 'beam' if effect == 'laser' else 'muzzle', effect)


def _pod(geometry, mount, rule, position, scale):
    x, y, z = position
    group = mount['location']
    direction = -1 if mount['rear'] else 1
    width, depth, height = (value*scale for value in rule['size'])
    geometry.box((x, y+direction*(depth/2-1*scale), z), (width, depth, height), group, 'edge')
    front = y+direction*(depth-1*scale)
    for stub in range(rule.get('stubs', 0)):
        stub_x = x+(stub-(rule['stubs']-1)/2)*width*.42
        geometry.beam((stub_x, front-direction*.3*scale, z), (stub_x, front+direction*1.8*scale, z), .8*scale, .8*scale,
               group, 'metal', 4, .85)
        geometry.emitter((stub_x, front+direction*1.8*scale, z), (0, direction, 0), group, 'muzzle', 'bullet')
    if not rule.get('stubs'):
        half = width*.3
        face_y = front+direction*.03
        corners = [(x-half, face_y, z+half), (x+half, face_y, z+half), (x+half, face_y, z-half), (x-half, face_y, z-half)]
        geometry.face(corners if direction == 1 else list(reversed(corners)), group, rule.get('tip', 'dark'))
        if mount.get('policy', 'WEAPON') == 'WEAPON':
            geometry.emitter((x, face_y, z), (0, direction, 0), group, 'beam', 'none')


def _lamp(geometry, mount, rule, position, scale):
    x, y, z = position
    group = mount['location']
    direction = -1 if mount['rear'] else 1
    width, depth, height = (value*scale for value in rule['size'])
    geometry.box((x, y+direction*(depth/2-scale), z), (width, depth, height), group, 'edge')
    # The lens fills the face, leaving a narrow bezel.
    face_y = y+direction*(depth-scale+.03)
    half_width, half_height = width*.4, height*.38
    corners = [(x-half_width, face_y, z+half_height), (x+half_width, face_y, z+half_height),
               (x+half_width, face_y, z-half_height), (x-half_width, face_y, z-half_height)]
    geometry.face(corners if direction == 1 else list(reversed(corners)), group, 'lamp')
    geometry.emitter((x, face_y, z), (0, direction, 0), group, 'lamp', 'lamp')


def _jet(geometry, mount, rule, position, scale):
    x, y, z = position
    half = rule['length']*scale/2
    geometry.beam((x, y, z+half), (x, y, z-half), rule['width']*scale, rule['width']*scale, mount['location'], 'metal', 6)
    geometry.emitter((x, y, z-half), (0, 0, -1), mount['location'], 'exhaust', 'exhaust')


def _gatling(geometry, mount, rule, position, scale):
    x, y, z = position
    group = mount['location']
    direction = -1 if mount['rear'] else 1
    length = rule['length']*scale*BOOK['protrusions'][rule.get('protrusion', 'long')]
    width = rule['width']*scale
    drum_sides = rule.get('drumSides', 6)
    if 'housing' in rule:
        # A turret housing takes the place of the drum, and the barrels start from its front.
        housing_width, housing_depth, housing_height = (value*scale for value in rule['housing'])
        geometry.box((x, y+direction*(housing_depth/2-scale), z), (housing_width, housing_depth, housing_height),
              group, 'edge')
        y += direction*(housing_depth-scale)
    else:
        # A drum at the root, a ring of barrels, and a clamp near the muzzles. Four barrels sit as a square block.
        geometry.beam((x, y-2*direction*scale, z), (x, y+direction*min(length, 2.4*scale), z), width*1.15, width*1.15,
               group, 'metal', drum_sides)
    muzzle = y+length*direction
    barrel_width = width*rule.get('barrelWidth', .3)
    for barrel in range(rule['barrels']):
        angle = 2*pi*(barrel+.5)/rule['barrels'] if rule['barrels'] == 4 else 2*pi*barrel/rule['barrels']
        barrel_x, barrel_z = x+cos(angle)*width*.32, z+sin(angle)*width*.32
        geometry.beam((barrel_x, y, barrel_z), (barrel_x, muzzle, barrel_z), barrel_width, barrel_width, group, 'metal',
               rule.get('barrelSides', 3))
        geometry.emitter((barrel_x, muzzle, barrel_z), (0, direction, 0), group, 'muzzle', 'bullet')
    if length > 4*scale:
        geometry.beam((x, muzzle-direction*2.2*scale, z), (x, muzzle-direction*1.2*scale, z), width*1.05, width*1.05,
               group, 'edge', drum_sides)


def _slab(geometry, x, half_thickness, outline, group, material):
    """A flat plate standing on edge, its convex outline given as (y, z) points and its thickness across x."""
    near = [(x+half_thickness, y, z) for y, z in outline]
    far = [(x-half_thickness, y, z) for y, z in outline]
    faces = [near, list(reversed(far))]
    for i in range(len(outline)):
        j = (i+1) % len(outline)
        faces.append([far[i], far[j], near[j], near[i]])
    middle = [sum(p[axis] for p in near+far)/(2*len(outline)) for axis in range(3)]
    for points in faces:
        # Wind each face outward from the plate's middle, whichever way the outline was given.
        centre = [sum(p[axis] for p in points)/len(points) for axis in range(3)]
        if sum(a*b for a, b in zip(cross(sub(points[1], points[0]), sub(points[2], points[0])),
                                    sub(centre, middle))) < 0:
            points = list(reversed(points))
        geometry.face(points, group, material)


# A hatchet at scale 1, in (forward, up) from its mount: a long handle standing just in front of the fist, and a thin
# axe head at its top front - a narrow neck that flares into a broad blade with a curved edge, leading forward as the
# Mek would swing it.
HATCHET_HANDLE = 2.3
HATCHET_NECK = ((0, 5.2), (2.5, 4.6), (2.5, 9.2), (0, 8.6))
HATCHET_BLADE = ((2.5, 4.6), (4.9, 2.6), (6.0, 4.4), (6.3, 6.8), (6.0, 9.2), (4.9, 11.0), (2.5, 9.2))


def _hatchet(geometry, mount, position, scale):
    x, y, z = position
    group = mount['location']
    handle = y + HATCHET_HANDLE
    geometry.beam((x, handle, z-7), (x, handle, z+9.6), 1.3, 1.3, group, 'metal', 6)
    _slab(geometry, x, .6, [(handle+forward, z+up) for forward, up in HATCHET_NECK], group, 'metal')
    _slab(geometry, x, .35, [(handle+forward, z+up) for forward, up in HATCHET_BLADE], group, 'edge')
    geometry.emitter((x, handle+6.3, z+6.8), (0, 1, 0), group, 'contact', 'melee')


def _leaning(position):
    """Points along a line held at forty-five degrees, up and forward, so a hand weapon clears the forearm."""
    x, y, z = position
    lean = .70710678
    return lambda distance: (x, y+distance*lean, z+distance*lean)


def _blade(geometry, mount, position, scale):
    group = mount['location']
    along = _leaning(position)
    geometry.beam(along(-4), along(2), 1.8, 1.8, group, 'metal')
    geometry.beam(along(2), along(3), 2, 7, group, 'metal')
    geometry.beam(along(3), along(19), 1.4, 4.8, group, 'edge', 4, .2)
    geometry.emitter(along(19), (0, 1, 1), group, 'contact', 'melee')


def _mace(geometry, mount, position, scale):
    group = mount['location']
    along = _leaning(position)
    geometry.beam(along(-6), along(10), 2, 2, group, 'metal')
    # The head is a faceted drum that narrows toward its crown.
    geometry.beam(along(10), along(12), 5, 5, group, 'edge', 8, 1.4)
    geometry.beam(along(12), along(16), 7, 7, group, 'edge', 8, .7)
    geometry.emitter(along(16), (0, 1, 1), group, 'contact', 'melee')


def _lance(geometry, mount, position, scale):
    x, y, z = position
    group = mount['location']
    geometry.beam((x, y-3, z), (x, y+4, z), 3.4, 3.4, group, 'metal', 6)
    geometry.beam((x, y+4, z), (x, y+21, z), 3, 3, group, 'edge', 6, .1)
    geometry.emitter((x, y+21, z), (0, 1, 0), group, 'contact', 'melee')


def _side_plate(geometry, outline, x, width, group, material):
    """A convex Y/Z profile with thickness along X, used by saws and tool jaws."""
    area = sum(y*outline[(i+1) % len(outline)][1]-outline[(i+1) % len(outline)][0]*z
               for i, (y, z) in enumerate(outline))
    if area < 0:
        outline = list(reversed(outline))
    geometry.loft([[(x+side*width/2, y, z) for y, z in outline] for side in (-1, 1)], group, material)


def _sweep(geometry, points, widths, group, materials, sides=3):
    """One joined tube: shared bend sections and caps only at the two exposed ends."""
    rings, side = [], None
    for i, point in enumerate(points):
        axis = normal(sub(points[min(i+1, len(points)-1)], points[max(0, i-1)]))
        if side is None:
            side = cross(axis, (0, 0, 1) if abs(axis[2]) < .9 else (0, 1, 0))
        side = normal(sub(side, mul(axis, sum(a*b for a, b in zip(side, axis)))))
        up = cross(axis, side)
        rings.append([add(point, add(mul(side, cos(2*pi*j/sides+pi/4)*widths[i]/2),
                                      mul(up, sin(2*pi*j/sides+pi/4)*widths[i]/2))) for j in range(sides)])
    geometry.face(list(reversed(rings[0])), group, materials[0])
    geometry.face(rings[-1], group, materials[-1])
    for lo, hi, material in zip(rings, rings[1:], materials):
        for j in range(sides):
            k = (j+1) % sides
            geometry.face([lo[j], lo[k], hi[k], hi[j]], group, material)


def _chain(geometry, points, group):
    """Open, interlocking oval links; alternate link planes so a chain reads from either side."""
    for index, (start, end) in enumerate(zip(points, points[1:])):
        delta = sub(end, start)
        axis = normal(delta)
        center = mul(add(start, end), .5)
        length = sum(v*v for v in delta)**.5/2+.2
        side = normal(cross(axis, (0, 0, 1) if abs(axis[2]) < .9 else (0, 1, 0)))
        if index % 2:
            side = cross(axis, side)
        perpendicular = cross(axis, side)
        rings = []
        # Alternate oval face-on links with simpler edge-on links; both are closed solid loops.
        steps = 4 if index % 2 else 6
        for step in range(steps):
            angle = 2*pi*step/steps
            radial = add(mul(axis, cos(angle)), mul(side, sin(angle)))
            middle = add(center, add(mul(axis, length*cos(angle)), mul(side, 1.1*sin(angle))))
            rings.append([add(middle, add(mul(radial, .35*cos(2*pi*j/3)),
                                          mul(perpendicular, .35*sin(2*pi*j/3)))) for j in range(3)])
        for index, ring in enumerate(rings):
            following = rings[(index+1) % len(rings)]
            for j in range(3):
                k = (j+1) % 3
                geometry.face([ring[j], following[j], following[k], ring[k]], group, 'metal')


def _ball(geometry, center, radius, group):
    # An icosahedron keeps a round silhouette in twenty triangles.
    phi = (1+5**.5)/2
    vertices = [normal(p) for p in ((-1, phi, 0), (1, phi, 0), (-1, -phi, 0), (1, -phi, 0),
                                  (0, -1, phi), (0, 1, phi), (0, -1, -phi), (0, 1, -phi),
                                  (phi, 0, -1), (phi, 0, 1), (-phi, 0, -1), (-phi, 0, 1))]
    for face in ((0,11,5), (0,5,1), (0,1,7), (0,7,10), (0,10,11), (1,5,9), (5,11,4),
                 (11,10,2), (10,7,6), (7,1,8), (3,9,4), (3,4,2), (3,2,6), (3,6,8),
                 (3,8,9), (4,9,5), (2,4,11), (6,2,10), (8,6,7), (9,8,1)):
        geometry.face([add(center, mul(vertices[i], radius)) for i in face], group, 'metal')


def _spike(geometry, start, end, width, group, material='edge', sides=3, depth=None):
    """A real point, avoiding the extra ring and cap of a nearly closed tapered beam."""
    axis = normal(sub(end, start))
    side = normal(cross(axis, (0, 0, 1) if abs(axis[2]) < .9 else (0, 1, 0)))
    up = cross(axis, side)
    ring = [add(start, add(mul(side, width*.5*cos(2*pi*i/sides)),
                           mul(up, (depth or width)*.5*sin(2*pi*i/sides)))) for i in range(sides)]
    geometry.face(list(reversed(ring)), group, material)
    for i in range(sides):
        geometry.face([ring[i], ring[(i+1) % sides], end], group, material)


def _flexible(geometry, group, rule):
    look = rule['look']
    if look == 'wrecking-ball':
        geometry.box((0, 1, 1), (4, 4, 4), group, 'paint')
        geometry.beam((0, 1, 1), (0, 5, 10), 2.2, 2.2, group, 'metal', 3)
        _chain(geometry, [(0, 5, 10), (0, 8, 10), (0, 10, 7.3), (0, 10, 4)], group)
        _ball(geometry, (0, 10, .5), 3.8, group)
        contact = (0, 13.8, .5)
    else:
        geometry.beam((0, -1, -4), (0, 3, 8), 1.7, 1.7, group, 'metal', 3)
        if look == 'flail':
            center = (6.5, 9.5, 4.8)
            _chain(geometry, [(0, 3, 8), (.5, 5.4, 11), (4, 7.8, 11), (6.5, 9.5, 7.4)], group)
            _ball(geometry, center, 2.9, group)
            for direction in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, 0, -1)):
                _spike(geometry, add(center, mul(direction, 2.1)), add(center, mul(direction, 4.4)), 1.6, group)
            contact = add(center, (0, 4.4, 0))
        else:
            geometry.beam((0, -1, -4), (0, .5, .5), 2.1, 2.1, group, 'dark', 3)
            _chain(geometry, [(0, 3, 8), (0, 5.5, 11), (3.5, 7.5, 12), (7, 9.5, 10), (8, 10.5, 6)], group)
            _spike(geometry, (8, 10.5, 6), (7, 11.5, 1), 1.8, group)
            contact = (7, 11.5, 1)
    geometry.emitter(contact, (0, 1, 0), group, 'contact', 'melee')


def _wood_branch(geometry, start, end, width, taper, group):
    axis = normal(sub(end, start))
    side = normal(cross(axis, (1, 0, 0)))
    up = cross(axis, side)
    rings = [[add(center, add(mul(side, cos(2*pi*i/7)*width*factor/2),
                              mul(up, sin(2*pi*i/7)*width*factor/2))) for i in range(7)]
             for center, factor in ((start, 1), (end, taper))]
    geometry.face(list(reversed(rings[0])), group, 'wood')
    geometry.face(rings[1], group, 'wood')
    for i in range(7):
        j = (i+1) % 7
        geometry.face([rings[0][i], rings[0][j], rings[1][j], rings[1][i]], group, 'bark')


def _club(geometry, group, rule):
    look = rule['look']
    if look == 'tree-club':
        _wood_branch(geometry, (0, -2, -4), (0, 8, 14), 2.8, 1.9, group)
        _wood_branch(geometry, (0, 4, 7), (-5, 8, 12), 2.6, .5, group)
        _wood_branch(geometry, (0, 6, 10), (4.5, 10, 12), 2.2, .45, group)
        _wood_branch(geometry, (.5, 7, 12), (1, 6, 17), 2, .35, group)
        contact = (0, 9, 15)
    elif look == 'limb-club':
        geometry.beam((0, -2, -4), (0, 2, 4), 2.2, 2.2, group, 'dark', 3)
        geometry.beam((0, 1, 2), (0, 5, 8), 5, 4.5, group, 'paint', 4, .8)
        geometry.beam((-3, 6, 10), (3, 6, 10), 4.3, 4.3, group, 'metal', 5)
        geometry.box((0, 7.4, 10.7), (4, 2.5, 3.5), group, 'edge')
        geometry.beam((0, 6.5, 11), (0, 10.5, 18), 5.7, 4.5, group, 'paint', 4, .7)
        geometry.beam((0, 10.5, 17), (0, 12, 19), 2.4, 2.4, group, 'dark', 4)
        geometry.box((0, 13.5, 19), (6.5, 7, 3.5), group, 'paint', taper=.85)
        geometry.box((0, 16, 18.7), (6.2, 2.4, 2.1), group, 'metal')
        contact = (0, 17.2, 19)
    else:
        # I-section scrap girder: two flanges joined by a visibly narrower web.
        along = _leaning((0, 0, 0))
        across = (0, -.70710678, .70710678)
        geometry.beam(along(-4), along(19), 1.1, 4.6, group, 'metal', 4)
        for sign in (-1, 1):
            offset = mul(across, sign*1.5)
            geometry.beam(add(along(-4), offset), add(along(19), offset), 5.4, .8, group, 'edge', 4)
        contact = along(19)
    geometry.emitter(contact, (0, 1, 1), group, 'contact', 'melee')


def _round_saw(geometry, x, radius, teeth, group, thick=.7, center=(8, 0)):
    cy, cz = center
    # One closed toothed disk replaces a cylinder with separate overlapping tooth prisms.
    root_radius = .68 if teeth <= 6 else .8
    outline = [(cy+radius*(root_radius if i % 2 else 1)*cos(pi*i/teeth),
                cz+radius*(root_radius if i % 2 else 1)*sin(pi*i/teeth)) for i in range(teeth*2)]
    rings = [[(x+side*thick/2, y, z) for y, z in outline] for side in (-1, 1)]
    for side, ring in zip((-1, 1), rings):
        core = ring[1::2]
        geometry.face(core if side == 1 else list(reversed(core)), group, 'metal')
        for i in range(0, len(outline), 2):
            tooth = [ring[(i-1) % len(outline)], ring[i], ring[(i+1) % len(outline)]]
            geometry.face(tooth if side == 1 else list(reversed(tooth)), group, 'edge')
    for i in range(len(outline)):
        j = (i+1) % len(outline)
        geometry.face([rings[0][i], rings[0][j], rings[1][j], rings[1][i]], group, 'metal')


def _saw(geometry, group, rule):
    look = rule['look']
    if look == 'dual-saw':
        geometry.beam((0, 0, 0), (0, 8, 0), 8, 4, group, 'paint', 3)
    else:
        geometry.box((0, 1, 0), (4.5, 5, 4), group, 'paint')
    if look == 'chainsaw':
        _side_plate(geometry, [(2, -1.5), (12, -1.5), (14, -.4), (14, .8), (12, 2), (2, 2)],
                    0, 1.1, group, 'edge')
        for y in (4, 8, 12):
            for sign, z in ((-1, -1.5), (1, 2)):
                _side_plate(geometry, [(y-.5, z), (y+.6, z), (y+.4, z+sign*.9)], 0, 1.4, group, 'metal')
        _side_plate(geometry, [(13.7, -.4), (15, .2), (13.7, .9)], 0, 1.4, group, 'metal')
        geometry.emitter((0, 15, .2), (0, 1, 0), group, 'contact', 'melee')
    else:
        dual = look == 'dual-saw'
        radius = 5.1 if look == 'rock-cutter' else 4.2
        for x in (-2.8, 2.8) if dual else (0,):
            cy, cz = 8, 0
            if not dual:
                geometry.beam((x, 2, 0), (x, cy, cz), 1.5, 1.5, group, 'metal', 3)
            _round_saw(geometry, x, radius, 6 if dual else 8, group,
                       1.3 if look == 'rock-cutter' else .65, (cy, cz))
            geometry.emitter((x, cy+radius, cz), (0, 1, 0), group, 'contact', 'melee')


def _industrial(geometry, group, rule):
    look = rule['look']
    if look != 'combine':
        geometry.box((0, 1, 0), (4, 4, 4), group, 'paint')
    if look == 'backhoe':
        geometry.beam((0, 1, 0), (0, 6, 5), 2, 2, group, 'edge', 3)
        geometry.beam((0, 6, 5), (0, 10, 1), 1.8, 1.8, group, 'edge', 3)
        for x in (-3.2, 3.2):
            _side_plate(geometry, [(9, 1.5), (12, 1.5), (14, -2.5), (9, -2.5)], x, .5, group, 'paint')
        geometry.box((0, 9, -.5), (6.5, .8, 4), group, 'metal')
        geometry.box((0, 11.4, -2.4), (6.5, 5, .6), group, 'edge')
        for x in (-2.4, -.8, .8, 2.4):
            _spike(geometry, (x, 13, -2.3), (x, 15, -2.5), .8, group, 'metal')
        contact = (0, 15, -2.5)
    elif look == 'combine':
        geometry.beam((0, 1, 0), (0, 6, 0), 2.5, 2.5, group, 'metal', 3)
        geometry.box((0, 7, -1.2), (15, 3, 1.7), group, 'paint')
        for x in (-6, -3, 0, 3, 6):
            _spike(geometry, (x, 7, -1), (x, 11, -1.5), 1.5, group, depth=.8)
        for angle in (0, pi):
            y, z = 7+1.8*cos(angle), 1.5+1.8*sin(angle)
            geometry.beam((-6.5, y, z), (6.5, y, z), .7, .7, group, 'metal', 3)
            for x in (-6.5, 6.5):
                geometry.beam((x, 7, 1.5), (x, y, z), .5, .5, group, 'edge', 3)
        contact = (0, 11, -1.5)
    elif look == 'pile-driver':
        geometry.box((0, 4, 0), (5, 7, 5), group, 'paint')
        for x in (-1.6, 1.6):
            geometry.beam((x, 3, 1.6), (x, 8, 1.6), .7, .7, group, 'metal', 4)
        geometry.beam((0, 7, 0), (0, 12, 0), 2.5, 2.5, group, 'metal', 6)
        _spike(geometry, (0, 12, 0), (0, 15, 0), 2.5, group)
        contact = (0, 15, 0)
    elif look == 'mining-drill':
        geometry.beam((0, 2, 0), (0, 5, 0), 4, 4, group, 'metal', 4)
        _spike(geometry, (0, 5, 0), (0, 15, 0), 4.5, group, sides=6)
        # A raised helical cutting ridge, tapering with the conical bit.
        points = [(2.3*(1-i/9)*cos(i*pi*3/8), 5+i*1.15, 2.3*(1-i/9)*sin(i*pi*3/8)) for i in range(9)]
        for start, end in zip(points, points[1:]):
            geometry.beam(start, end, .65, .65, group, 'metal', 3, .9)
        contact = (0, 15, 0)
    else:  # Two copper electrode jaws distinguish the spot welder from a gun barrel.
        for sign in (-1, 1):
            geometry.beam((sign*1.5, 2, 0), (sign*2.4, 7, 0), 1.3, 1.3, group, 'metal')
            geometry.beam((sign*2.4, 7, 0), (sign*.5, 10, 0), 1, 1, group, 'plasma', 4, .6)
        contact = (0, 10, 0)
    geometry.emitter(contact, (0, 1, 0), group, 'contact', 'melee')


def _curved_claw(geometry, x, group, length=1, z=0):
    # The hooked outline and two side ridges form one solid blade, without buried segment caps.
    outline = [(x, 1, z-.5*length), (x, 6.5*length, z+.3*length),
               (x, 9.5*length, z-2*length), (x, 7.5*length, z+1.5*length),
               (x, 4*length, z+2.6*length), (x, 1, z+.55*length)]
    for sign in (-1, 1):
        ridge = (x+sign*.65*length, 4.5*length, z+2.2*length)
        for i, point in enumerate(outline):
            triangle = [point, outline[(i+1) % len(outline)], ridge]
            geometry.face(triangle if sign == 1 else list(reversed(triangle)), group, 'edge')
    return (x, 9.5*length, z-2*length)


def _physical(geometry, group, rule):
    look = rule['look']
    if look == 'shield':
        width, height = rule['size']
        outline = [(-width*.38, height/2), (width*.38, height/2), (width/2, height*.3),
                   (width*.44, -height*.3), (0, -height/2), (-width*.44, -height*.3), (-width/2, height*.3)]
        rear = [(x, .3, z) for x, z in outline]
        front = [(x, 1.2, z) for x, z in outline]
        geometry.face(list(reversed(rear)), group, 'metal')
        for i in range(len(outline)):
            j = (i+1) % len(outline)
            geometry.face([rear[i], rear[j], front[j], front[i]], group, 'edge')
            inner_i, inner_j = (front[i][0]*.85, 1.4, front[i][2]*.85), (front[j][0]*.85, 1.4, front[j][2]*.85)
            geometry.face([front[i], front[j], inner_j, inner_i], group, 'edge')
            geometry.face([inner_i, inner_j, (0, 2.8, 0)], group, 'paint')
        geometry.beam((0, 2.2, 0), (0, 3.3, 0), 2.5, 2.5, group, 'metal', 6, .5)
        geometry.box((0, -.6, 0), (3.5, 1, 1), group, 'metal')
        geometry.emitter((0, 3.3, 0), (0, 1, 0), group, 'contact', 'melee')
    elif look == 'claw':
        geometry.box((0, 0, 0), (7, 3, 3), group, 'paint')
        for x in (-2.4, 0, 2.4):
            tip = _curved_claw(geometry, x, group)
            geometry.emitter(tip, (0, 1, -1), group, 'contact', 'melee')
        geometry.beam((-3.1, 0, -1), (-3.5, 4, -3), 1.8, 1.8, group, 'metal', 3, .6)
        _spike(geometry, (-3.5, 4, -3), (-1.8, 6, -1.8), 1, group)
    elif look == 'talons':
        geometry.box((0, 0, 0), (7, 4, 2.2), group, 'metal')
        for x in (-2.5, 0, 2.5):
            tip = _curved_claw(geometry, x, group, .78 if x else 1.05, -.5)
            geometry.emitter(tip, (0, 1, -1), group, 'contact', 'melee')
        _spike(geometry, (0, -1, -.5), (0, -4.5, -2), 2.1, group)
    else:
        geometry.box((0, 0, 0), (7.5, 1.5, 7.5), group, 'paint', .25)
        for x, z, reach in ((-2.3, -2.3, 3.8), (-2.3, 2.3, 3.8), (2.3, -2.3, 3.8), (2.3, 2.3, 3.8), (0, 0, 5.7)):
            _spike(geometry, (x, .5, z), (x*1.2, reach, z*1.2), 2.4, group, 'metal', 4)
            geometry.emitter((x*1.2, reach, z*1.2), (0, 1, 0), group, 'contact', 'melee')


def _support(geometry, group, rule):
    look = rule['look']
    if look == 'bomb-rack':
        geometry.box((0, 1, 1.5), (8.5, 4, 2), group, 'paint')
        for x in (-2.8, 0, 2.8):
            geometry.beam((x, 1, -.7), (x, 6, -.7), 2, 2, group, 'metal', 4)
            _spike(geometry, (x, 6, -.7), (x, 8, -.7), 2, group, sides=4)
            for dx in (-.7, .7):
                _spike(geometry, (x, 1, -.7), (x+dx, 0, -1.8), 1.3, group, depth=.35)
            geometry.emitter((x, 4, -1.8), (0, 0, -1), group, 'launcher', 'bomb')
    elif look == 'mine-launcher':
        geometry.box((0, 2, -.8), (6, 5, 2), group, 'paint')
        _sweep(geometry, [(0, 1, .5), (0, 5, 1.5), (0, 6.3, 1.825)], [4.5, 4.5, 3.6],
               group, ['metal', 'edge'], 6)
        axis = normal((0, 1, .25))
        up = cross(axis, (1, 0, 0))
        center = add((0, 6.3, 1.825), mul(axis, .01))
        geometry.face([add(center, add((.65*cos(2*pi*i/6+pi/4), 0, 0),
                                      mul(up, .65*sin(2*pi*i/6+pi/4)))) for i in range(6)], group, 'dark')
        geometry.emitter((0, 6.3, 1.83), (0, 1, .25), group, 'launcher', 'mine')
    elif look == 'screen-launcher':
        geometry.box((0, 2, 0), (9, 6, 4.5), group, 'paint')
        for x in (-2.8, 0, 2.8):
            # Recess markings and the lower sill are surfaces on the housing, not six solid boxes.
            geometry.face([(x-1, 5.01, -1.55), (x-1, 5.01, 1.55),
                           (x+1, 5.01, 1.55), (x+1, 5.01, -1.55)], group, 'dark')
            geometry.face([(x-.8, 5.02, -1.075), (x-.8, 5.02, -.725),
                           (x+.8, 5.02, -.725), (x+.8, 5.02, -1.075)], group, 'metal')
            geometry.emitter((x, 5.3, 0), (0, 1, 0), group, 'launcher', 'screen')
    else:
        geometry.beam((-2, 1, -3), (-2, 1, 4), 3.2, 3.2, group, 'paint', 6, .85)
        geometry.beam((-2, 1, 3.8), (-2, 1, 4.7), 1.1, 1.1, group, 'metal', 4)
        geometry.beam((-3, 1, 4.7), (-1, 1, 4.7), .5, .5, group, 'laser', 3)
        hose = [(-1.5, 1, 3.5), (1, 1, 4), (2, 3, 2), (1.5, 4, 0)]
        _sweep(geometry, hose, [.7]*len(hose), group, ['dark']*(len(hose)-1))
        geometry.beam((1.5, 2, 0), (1.5, 6, 0), 1.3, 1.3, group, 'metal', 4)
        geometry.beam((1.5, 6, 0), (1.5, 9, 0), 1.4, 1.4, group, 'dark', 5, 1.8)
        _opening(geometry, (1.5, 9.02, 0), .8, 'square', 1, group, 'metal')
        geometry.emitter((1.5, 9.05, 0), (0, 1, 0), group, 'muzzle', 'spray')


def _infantry_melee(geometry, group, rule):
    look = rule['variant']
    length = rule.get('length', 9)
    along = _leaning((0, 0, 0))
    if look in ('blade', 'axe', 'spear'):
        geometry.beam(along(-2.5), along(1.5), .9, .9, group, 'dark', 4)
        if look == 'axe':
            geometry.beam(along(1), along(8), 1, 1, group, 'wood', 4)
            _side_plate(geometry, [(3, 6), (7, 8), (8, 5), (4, 4)], 0, 1.1, group, 'edge')
        else:
            geometry.beam(along(1), along(1.5), .8, 3, group, 'metal')
            geometry.beam(along(1.5), along(length), .6, 2 if look == 'blade' else .8,
                          group, rule.get('material', 'edge'), 4, .04)
        contact = along(length)
    elif look == 'staff':
        _sweep(geometry, [along(p) for p in (-length/2, -length/2+1.5, length/2-1.5, length/2)],
               [1.1, .8, .8, 1.1], group, ['edge', 'wood' if rule.get('wood') else 'metal', 'edge'], 6)
        contact = along(length/2)
    elif look == 'club':
        geometry.beam(along(-2), along(length), 1, 1, group, 'wood', 6, 2.5)
        contact = along(length)
    elif look == 'claws':
        geometry.box((0, 0, 0), (3, 2, 1.2), group, 'metal')
        for x in (-1, 0, 1):
            _curved_claw(geometry, x, group, .45)
        contact = (0, 4.3, -.9)
    elif look == 'star':
        geometry.beam((0, 1, -.3), (0, 1, .3), 1.8, 1.8, group, 'metal', 4)
        for i in range(4):
            a = i*pi/2
            ring = [(cos(a-.3), 1+sin(a-.3)), (3*cos(a+.15), 1+3*sin(a+.15)),
                    (cos(a+.9), 1+sin(a+.9))]
            geometry.prism(ring, -.2, .2, group, 'edge')
        contact = (0, 4, 0)
    else:
        geometry.beam((0, 0, -2), (0, 1, 3), .8, .8, group, 'dark', 3)
        points = [(0, 1, 3), (0, 3, 6), (1, 6, 8), (3, 8, 7), (4, 9, 4), (4, 9, 0), (3, 9, -3)]
        _sweep(geometry, points, [.55-i*.07 for i in range(len(points))], group, ['metal']*(len(points)-1))
        contact = points[-1]
    geometry.emitter(contact, (0, 1, 0), group, 'contact', 'melee')


def _partial_wing(geometry, group):
    """Paired swept lifting surfaces with raised tips; +Y is forward, so the whole module lies behind its root."""
    geometry.box((0, -2, 0), (12, 4, 4), group, 'metal')
    wing = Geometry()
    sections = [(4, -1, -7, 1), (13, -1.5, -10, 3), (24, -4, -11, 5), (30, -5, -9, 10)]
    rings = [[(x, front, z+.6), (x, back, z+.6), (x, back, z-.6), (x, front, z-.6)]
             for x, front, back, z in sections]
    wing.loft(rings, group, 'paint')
    # A continuous darker leading edge emphasizes the bent, aerodynamic silhouette at board scale.
    for a, b in zip(sections, sections[1:]):
        wing.face([(a[0], a[1], a[3]+.62), (a[0], a[1]-1.2, a[3]+.62),
                   (b[0], b[1]-1.2, b[3]+.62), (b[0], b[1], b[3]+.62)], group, 'edge')
    for side in (-1, 1):
        geometry.beam((side*5, -.5, 1), (side*5, -6, 1), 4, 4, group, 'metal', sides=3)
        for triangle, _, material in wing.faces:
            points = [(side*x, y, z) for x, y, z in triangle]
            geometry.face(list(reversed(points)) if side < 0 else points, group, material)


def _detailed(geometry, mount, rule, position, scale):
    """Author small equipment at one local origin; transform mesh and contacts together."""
    shape, group, look = Geometry(), mount['location'], rule['look']
    if look in ('flail', 'chain-whip', 'wrecking-ball'):
        _flexible(shape, group, rule)
    elif look in ('tree-club', 'limb-club', 'girder-club'):
        _club(shape, group, rule)
    elif look in ('chainsaw', 'buzzsaw', 'dual-saw', 'rock-cutter'):
        _saw(shape, group, rule)
    elif look in ('backhoe', 'combine', 'pile-driver', 'mining-drill', 'spot-welder'):
        _industrial(shape, group, rule)
    elif look in ('shield', 'claw', 'talons', 'spikes'):
        _physical(shape, group, rule)
    elif look == 'infantry-melee':
        _infantry_melee(shape, group, rule)
    elif look in ('bomb-rack', 'mine-launcher', 'screen-launcher', 'extinguisher'):
        _support(shape, group, rule)
    elif look == 'partial-wing':
        _partial_wing(shape, group)
    else:
        raise ValueError('Unknown equipment look: '+look)
    facing = -1 if mount['rear'] else 1
    def orient(point):
        return point[0]*facing, point[1]*facing, point[2]
    for triangle, node, material in shape.faces:
        geometry.face([add(position, mul(orient(point), scale)) for point in triangle], node, material)
    for emitter in shape.emitters:
        geometry.emitter(add(position, mul(orient(emitter['position']), scale)), orient(emitter['direction']),
                         emitter['node'], emitter['role'], emitter['effect'])


def draw(geometry, mount, rule, position, scale, options=None):
    """Adds one catalogued mount to a model at its socket, using its standard look."""
    options = options or {}
    aim = options.get('aim')
    if aim is None:
        _draw_ahead(geometry, mount, rule, position, scale, options)
        return
    # Built facing straight ahead at the origin, then turned to the aim and moved to the socket.
    ahead = Geometry()
    origin = options.get('slopeOrigin', position[2])-position[2]
    _draw_ahead(ahead, mount, rule, (0, 0, 0), scale, {**options, 'slopeOrigin': origin})
    forward = normal(aim)
    flat = cross(forward, (0, 0, 1))
    # Aiming straight up or down leaves no sideways reference; the weapon then keeps the model's own right.
    right = normal(flat) if sum(value*value for value in flat) > 1e-6 else (1, 0, 0)
    up = cross(right, forward)
    for triangle, node, material in ahead.faces:
        geometry.face([tuple(position[i]+right[i]*point_x+forward[i]*point_y+up[i]*point_z for i in range(3))
                for point_x, point_y, point_z in triangle], node, material)
    for emitter in ahead.emitters:
        def rotate(point):
            return tuple(right[i]*point[0]+forward[i]*point[1]+up[i]*point[2] for i in range(3))
        geometry.emitter(add(position, rotate(emitter['position'])), rotate(emitter['direction']),
                         emitter['node'], emitter['role'], emitter['effect'])


def _draw_ahead(geometry, mount, rule, position, scale, options):
    look = rule['look']
    if options.get('held') and look in ('barrel', 'gatling'):
        _held(geometry, mount, rule, position, scale)
    elif look == 'launcher':
        _launcher(geometry, mount, rule, position, scale, options)
    elif look == 'artillery-launcher':
        _artillery_launcher(geometry, mount, rule, position, scale, options)
    elif look == 'barrel':
        _barrel(geometry, mount, rule, position, scale)
    elif look == 'gatling':
        _gatling(geometry, mount, rule, position, scale)
    elif look == 'pod':
        _pod(geometry, mount, rule, position, scale)
    elif look == 'jet':
        _jet(geometry, mount, rule, position, scale)
    elif look == 'lamp':
        _lamp(geometry, mount, rule, position, scale)
    elif look in ('hatchet', 'blade', 'mace', 'lance'):
        {'hatchet': _hatchet, 'blade': _blade, 'mace': _mace, 'lance': _lance}[look](
            geometry, mount, position, scale)
    else:
        _detailed(geometry, mount, rule, position, scale)
