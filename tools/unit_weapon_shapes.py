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

from unit_model_geometry import Geometry, cross, normal

RULES_PATH = Path(__file__).resolve().parent / 'unit-models/weapons.json'
BOOK = json.loads(RULES_PATH.read_text(encoding='utf-8'))
# Above this many rounds the face is a launcher symbol, not one opening per round.
MAXIMUM_TUBES = 20
# Sides and the angle of the first vertex. A square sits flat; a diamond is the same square stood on a corner.
TUBE_SHAPES = {'round': (8, pi/2), 'hex': (6, pi/2), 'square': (4, pi/4), 'diamond': (4, pi/2)}
# Launcher detail, richest first. A loadout over the triangle budget steps down until it fits: round tubes
# drawn with six sides still read as round at this size and cost a third less; a panel is the last resort.
DETAIL_LEVELS = ('full', 'reduced', 'panel')


def _matches(entry, mount):
    families = entry['family'] if isinstance(entry['family'], list) else [entry['family']]
    if mount['family'] not in families:
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
    if look == 'launcher':
        options = options or {}
        grid = launcher_grid(rule, mount, scale, options.get('maximumColumns', 0),
                             options.get('orientation', 'horizontal'))
        return grid['width'], grid['height']
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
    columns = next((c for c in range(widest, 1, -1) if visible % c == 0 and visible//c >= 2), None)
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


def _opening(g, center, radius, shape, direction, group, material):
    x, y, z = center
    sides, turn = TUBE_SHAPES[shape]
    points = [(x+radius*cos(turn+2*pi*i/sides), y, z+radius*sin(turn+2*pi*i/sides)) for i in range(sides)]
    g.face(list(reversed(points)) if direction == 1 else points, group, material)


def _launcher(g, mount, rule, position, scale, options):
    x, y, z = position
    group = mount['location']
    direction = -1 if mount['rear'] else 1
    grid = launcher_grid(rule, mount, scale, options.get('maximumColumns', 0),
                         options.get('orientation', 'horizontal'))
    slope = options.get('slope', 0)
    # A leaning bay is built upright, then sheared about the bay's center so stacked launchers share one face.
    launcher = Geometry() if slope else g
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
                reduced = options.get('detail') == 'reduced' and grid['shape'] == 'round'
                _opening(launcher, center, grid['diameter']/2, 'hex' if reduced else grid['shape'], direction,
                         group, 'dark')
    if slope:
        origin = options.get('slopeOrigin', z)
        for tri, node, material in launcher.faces:
            g.face([(px, py-direction*slope*(pz-origin), pz) for px, py, pz in tri], node, material)


def _barrel(g, mount, rule, position, scale):
    x, y, z = position
    group = mount['location']
    direction = -1 if mount['rear'] else 1
    # Recessed is a port flat against the armor; short, medium and long stand progressively further out.
    length = rule['length']*scale*BOOK['protrusions'][rule.get('protrusion', 'long')]
    width = rule['width']*scale
    sides = rule.get('sides', 4)
    count = rule.get('count', 1)
    for barrel in range(count):
        bx = x+(barrel-(count-1)/2)*width*1.15
        muzzle = y+length*direction
        g.beam((bx, y-2*direction*scale, z), (bx, muzzle, z), width, width, group, 'metal', sides,
               rule.get('taper', .85))
        tip_y, tip_width = muzzle, width*rule.get('taper', .85)
        for segment in rule.get('segments', []):
            back, front = min(segment['from']*scale, length), min(segment['to']*scale, length)
            if back-front < .2:
                # A shortened torso port has no room for this ring.
                continue
            start, end = muzzle-direction*back, muzzle-direction*front
            segment_width = width*segment['width']
            g.beam((bx, start, z), (bx, end, z), segment_width, segment_width, group, 'metal',
                   segment.get('sides', sides), segment.get('taper', 1))
            if (end-tip_y)*direction > 0:
                tip_y, tip_width = end, segment_width*segment.get('taper', 1)
        half = tip_width*rule.get('tipSize', .22)
        face_y = tip_y+direction*.03
        corners = [(bx-half, face_y, z+half), (bx+half, face_y, z+half),
                   (bx+half, face_y, z-half), (bx-half, face_y, z-half)]
        g.face(corners if direction == 1 else list(reversed(corners)), group, rule.get('tip', 'dark'))


def _pod(g, mount, rule, position, scale):
    x, y, z = position
    group = mount['location']
    direction = -1 if mount['rear'] else 1
    width, depth, height = (value*scale for value in rule['size'])
    g.box((x, y+direction*(depth/2-1*scale), z), (width, depth, height), group, 'edge')
    front = y+direction*(depth-1*scale)
    for stub in range(rule.get('stubs', 0)):
        sx = x+(stub-(rule['stubs']-1)/2)*width*.42
        g.beam((sx, front-direction*.3*scale, z), (sx, front+direction*1.8*scale, z), .8*scale, .8*scale,
               group, 'metal', 4, .85)
    if not rule.get('stubs'):
        half = width*.3
        face_y = front+direction*.03
        corners = [(x-half, face_y, z+half), (x+half, face_y, z+half), (x+half, face_y, z-half), (x-half, face_y, z-half)]
        g.face(corners if direction == 1 else list(reversed(corners)), group, rule.get('tip', 'dark'))


def _lamp(g, mount, rule, position, scale):
    x, y, z = position
    group = mount['location']
    direction = -1 if mount['rear'] else 1
    width, depth, height = (value*scale for value in rule['size'])
    g.box((x, y+direction*(depth/2-scale), z), (width, depth, height), group, 'edge')
    # The lens fills the face, leaving a narrow bezel.
    face_y = y+direction*(depth-scale+.03)
    half_width, half_height = width*.4, height*.38
    corners = [(x-half_width, face_y, z+half_height), (x+half_width, face_y, z+half_height),
               (x+half_width, face_y, z-half_height), (x-half_width, face_y, z-half_height)]
    g.face(corners if direction == 1 else list(reversed(corners)), group, 'lamp')


def _jet(g, mount, rule, position, scale):
    x, y, z = position
    half = rule['length']*scale/2
    g.beam((x, y, z+half), (x, y, z-half), rule['width']*scale, rule['width']*scale, mount['location'], 'metal', 6)


def _gatling(g, mount, rule, position, scale):
    x, y, z = position
    group = mount['location']
    direction = -1 if mount['rear'] else 1
    length = rule['length']*scale*BOOK['protrusions'][rule.get('protrusion', 'long')]
    width = rule['width']*scale
    drum_sides = rule.get('drumSides', 6)
    if 'housing' in rule:
        # A turret housing takes the place of the drum, and the barrels start from its front.
        housing_width, housing_depth, housing_height = (value*scale for value in rule['housing'])
        g.box((x, y+direction*(housing_depth/2-scale), z), (housing_width, housing_depth, housing_height),
              group, 'edge')
        y += direction*(housing_depth-scale)
    else:
        # A drum at the root, a ring of barrels, and a clamp near the muzzles. Four barrels sit as a square block.
        g.beam((x, y-2*direction*scale, z), (x, y+direction*min(length, 2.4*scale), z), width*1.15, width*1.15,
               group, 'metal', drum_sides)
    muzzle = y+length*direction
    barrel_width = width*rule.get('barrelWidth', .3)
    for barrel in range(rule['barrels']):
        angle = 2*pi*(barrel+.5)/rule['barrels'] if rule['barrels'] == 4 else 2*pi*barrel/rule['barrels']
        bx, bz = x+cos(angle)*width*.32, z+sin(angle)*width*.32
        g.beam((bx, y, bz), (bx, muzzle, bz), barrel_width, barrel_width, group, 'metal',
               rule.get('barrelSides', 3))
    if length > 4*scale:
        g.beam((x, muzzle-direction*2.2*scale, z), (x, muzzle-direction*1.2*scale, z), width*1.05, width*1.05,
               group, 'edge', drum_sides)


def _hatchet(g, mount, position, scale):
    x, y, z = position
    group = mount['location']
    g.beam((x, y, z-7), (x, y, z+8), 2, 2, group, 'metal')
    # The blade faces forward, edge leading, as the Mek would swing it.
    g.prism([(x+1, y), (x+3, y+7), (x, y+9), (x-3, y+7), (x-1, y)], z+4, z+10, group, 'edge')


def _leaning(position):
    """Points along a line held at forty-five degrees, up and forward, so a hand weapon clears the forearm."""
    x, y, z = position
    lean = .70710678
    return lambda distance: (x, y+distance*lean, z+distance*lean)


def _blade(g, mount, position, scale):
    group = mount['location']
    along = _leaning(position)
    g.beam(along(-4), along(2), 1.8, 1.8, group, 'metal')
    g.beam(along(2), along(3), 2, 7, group, 'metal')
    g.beam(along(3), along(19), 1.4, 4.8, group, 'edge', 4, .2)


def _mace(g, mount, position, scale):
    group = mount['location']
    along = _leaning(position)
    g.beam(along(-6), along(10), 2, 2, group, 'metal')
    # The head is a faceted drum that narrows toward its crown.
    g.beam(along(10), along(12), 5, 5, group, 'edge', 8, 1.4)
    g.beam(along(12), along(16), 7, 7, group, 'edge', 8, .7)


def _lance(g, mount, position, scale):
    x, y, z = position
    group = mount['location']
    g.beam((x, y-3, z), (x, y+4, z), 3.4, 3.4, group, 'metal', 6)
    g.beam((x, y+4, z), (x, y+21, z), 3, 3, group, 'edge', 6, .1)


def _tool(g, mount, position, scale):
    x, y, z = position
    group = mount['location']
    g.box((x, y+2, z), (5, 7, 5), group, 'edge', .25)
    g.beam((x-.7, y+8, z), (x+.7, y+8, z), 7.5, 7.5, group, 'metal', 8)


def draw(g, mount, rule, position, scale, options=None):
    """Adds one catalogued mount to a model at its socket, using its standard look."""
    options = options or {}
    aim = options.get('aim')
    if aim is None:
        _draw_ahead(g, mount, rule, position, scale, options)
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
    for tri, node, material in ahead.faces:
        g.face([tuple(position[i]+right[i]*px+forward[i]*py+up[i]*pz for i in range(3))
                for px, py, pz in tri], node, material)


def _draw_ahead(g, mount, rule, position, scale, options):
    look = rule['look']
    if look == 'launcher':
        _launcher(g, mount, rule, position, scale, options)
    elif look == 'barrel':
        _barrel(g, mount, rule, position, scale)
    elif look == 'gatling':
        _gatling(g, mount, rule, position, scale)
    elif look == 'pod':
        _pod(g, mount, rule, position, scale)
    elif look == 'jet':
        _jet(g, mount, rule, position, scale)
    elif look == 'lamp':
        _lamp(g, mount, rule, position, scale)
    else:
        {'hatchet': _hatchet, 'blade': _blade, 'mace': _mace, 'lance': _lance, 'tool': _tool}[look](
            g, mount, position, scale)
