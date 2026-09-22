"""Vent spots for a modular Mek body, chosen at runtime after the weapons are placed.

A vent is surface detail, a weapon is equipment, and a weapon drawn over a vent reads as nonsense. The body is
shared by every variant of a chassis while the weapons differ per variant, so the body cannot know where its
vents belong. It offers spots instead: the vents the chassis author drew, which are its first choice, and a few
more found on the flat of each torso face. The runtime places the variant's weapons, then keeps the vents that
land in a torso holding the variant's heat sinks and clear of its weapons.

Every spot is its own node under its torso location, so a spot the runtime does not keep is simply detached,
and one that is kept goes with its location when that location is destroyed.
"""
from unit_mek_chassis import vent
from unit_model_geometry import sub

TORSO = ('CT', 'LT', 'RT')
# Spare spots found per torso location and face, beyond the authored vents.
SPARES = 3
STEP = .5
GAP = .5


def _normal(tri):
    a, b = sub(tri[1], tri[0]), sub(tri[2], tri[0])
    n = (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])
    length = (n[0]**2+n[1]**2+n[2]**2) ** .5
    return None if length < 1e-9 else (n[0]/length, n[1]/length, n[2]/length)


def _inside(tri, x, z):
    (ax, _, az), (bx, _, bz), (cx, _, cz) = tri
    d1 = (x-bx)*(az-bz) - (ax-bx)*(z-bz)
    d2 = (x-cx)*(bz-cz) - (bx-cx)*(z-cz)
    d3 = (x-ax)*(cz-az) - (cx-ax)*(z-az)
    negative = d1 < -1e-9 or d2 < -1e-9 or d3 < -1e-9
    positive = d1 > 1e-9 or d2 > 1e-9 or d3 > 1e-9
    return not (negative and positive)


class _Surface:
    """The outermost skin of the body seen straight on from the front or the back."""

    def __init__(self, body, rear):
        self.sign = -1 if rear else 1
        self.faces = []
        for tri, node, _ in body.faces:
            # Vents lie on the skin; they are what is being placed, not the skin they are placed on.
            if node.startswith('vent-'):
                continue
            normal = _normal(tri)
            if normal is None or normal[1]*self.sign <= .05:
                continue
            xs, zs = [p[0] for p in tri], [p[2] for p in tri]
            plane = (normal, sum(normal[i]*tri[0][i] for i in range(3)))
            self.faces.append((tri, node, plane, (min(xs), max(xs), min(zs), max(zs))))

    def hit(self, x, z):
        """The outermost face at (x, z): its node, its plane, and its depth, or None."""
        best = None
        for tri, node, plane, (x0, x1, z0, z1) in self.faces:
            if not (x0-1e-6 <= x <= x1+1e-6 and z0-1e-6 <= z <= z1+1e-6) or not _inside(tri, x, z):
                continue
            (nx, ny, nz), d = plane
            y = (d - nx*x - nz*z)/ny
            if best is None or y*self.sign > best[2]*self.sign:
                best = (node, plane, y)
        return best


def _flat(surface, location, x0, x1, z0, z1):
    """The plane every sample of the rectangle lies on, when all of it is flat skin of this location."""
    plane = None
    for x in (x0+.1, (x0+x1)/2, x1-.1):
        for z in (z0+.1, (z0+z1)/2, z1-.1):
            hit = surface.hit(x, z)
            if hit is None or hit[0] != location:
                return None
            (normal, d) = hit[1]
            # Upright and square to the view, so the vent's depth varies with height only, as vent() draws it.
            if abs(normal[0]) > .05 or abs(normal[1]) < .9:
                return None
            if plane is None:
                plane = hit[1]
            elif max(abs(plane[0][i]-normal[i]) for i in range(3)) > .01 or abs(plane[1]-d) > .05:
                return None
    return plane


def _overlap(a, b):
    return a[0] < b[1]+GAP and b[0] < a[1]+GAP and a[2] < b[3]+GAP and b[2] < a[3]+GAP


def _rectangle(body, node):
    points = [p for tri, owner, _ in body.faces if owner == node for p in tri]
    return (min(p[0] for p in points), max(p[0] for p in points), min(p[2] for p in points),
            max(p[2] for p in points))


def _spares(body, surface, location, width, height, taken, limit=SPARES):
    """Up to SPARES flat spots of this location, nearest its middle first, clear of each other and of taken."""
    faces = [bounds for _, node, _, bounds in surface.faces if node == location]
    if not faces:
        return []
    x0, x1 = min(f[0] for f in faces), max(f[1] for f in faces)
    z0, z1 = min(f[2] for f in faces), max(f[3] for f in faces)
    middle = ((x0+x1)/2, (z0+z1)/2)
    found = []
    x = round(x0/STEP)*STEP
    while x+width <= x1+1e-6:
        z = round(z0/STEP)*STEP
        while z+height <= z1+1e-6:
            plane = _flat(surface, location, x, x+width, z, z+height)
            if plane is not None:
                found.append(((x, x+width, z, z+height), plane))
            z += STEP
        x += STEP
    found.sort(key=lambda item: ((item[0][0]+item[0][1])/2-middle[0])**2
               + ((item[0][2]+item[0][3])/2-middle[1])**2)
    chosen = []
    for rectangle, plane in found:
        if len(chosen) == limit:
            break
        if any(_overlap(rectangle, other) for other in taken + [c[0] for c in chosen]):
            continue
        chosen.append((rectangle, plane))
    return chosen


def finish_vents(body, spares=SPARES):
    """Moves every vent to a node of its own under its torso location, adds spare spots, and lists them all.

    Call after the torso is split into its locations. Returns the list the Mek descriptor carries.
    """
    authored = getattr(body, 'vents', [])
    spares_wanted = spares
    if not authored:
        return []
    surfaces = {rear: _Surface(body, rear) for rear in (False, True)}
    spots = []
    for entry in authored:
        rectangle = _rectangle(body, entry['node'])
        hit = surfaces[entry['rear']].hit((rectangle[0]+rectangle[1])/2, (rectangle[2]+rectangle[3])/2)
        location = hit[0] if hit and hit[0] in TORSO else entry['group']
        spots.append({'node': entry['node'], 'location': location, 'rear': entry['rear'], 'authored': True,
                      'rectangle': rectangle})
    # Spare spots take the size the author gave this chassis's vents on that face.
    for rear in (False, True):
        drawn = [spot['rectangle'] for spot in spots if spot['rear'] == rear]
        if not drawn:
            continue
        width = max(r[1]-r[0] for r in drawn)
        height = max(r[3]-r[2] for r in drawn)
        right = []
        for location in ('CT', 'RT', 'LT'):
            taken = [spot['rectangle'] for spot in spots if spot['rear'] == rear and spot['location'] == location]
            spares = []
            if location == 'LT':
                # The left side is the right side mirrored, never found separately, so the pair always match.
                for (x0, x1, z0, z1), _ in right:
                    mirrored = (-x1, -x0, z0, z1)
                    plane = _flat(surfaces[rear], 'LT', *mirrored)
                    if plane is not None and not any(_overlap(mirrored, other) for other in taken):
                        spares.append((mirrored, plane))
            # A narrow location may still take a smaller vent.
            for across, up in ((1, 1), (.7, .8), (.45, .8)):
                spares = spares or _spares(body, surfaces[rear], location, width*across, height*up, taken, spares_wanted)
            if location == 'RT':
                right = spares
            for (x0, x1, z0, z1), ((nx, ny, nz), d) in spares:
                sign = -1 if rear else 1
                middle = (x0+x1)/2

                def face(z, stand, nx=nx, ny=ny, nz=nz, d=d, middle=middle, sign=sign):
                    return (d - nx*middle - nz*z)/ny + sign*stand
                vent(body, face, middle, (x1-x0)/2, z0, z1, rear=rear, group=location, authored=False)
                node = body.vents[-1]['node']
                spots.append({'node': node, 'location': location, 'rear': rear, 'authored': False,
                              'rectangle': (x0, x1, z0, z1)})
    listed = []
    for index, spot in enumerate(spots):
        name = '%s#vent-%s-%d' % (spot['location'], 'rear' if spot['rear'] else 'front', index)
        body.faces = [(tri, name if node == spot['node'] else node, material) for tri, node, material in body.faces]
        body.pivots.pop(spot['node'], None)
        body.parents.pop(spot['node'], None)
        parent = spot['location'] if spot['location'] in body.pivots else 'CT'
        body.joint(name, body.pivots[parent], parent)
        points = [p for tri, node, _ in body.faces if node == name for p in tri]
        low = [min(p[axis] for p in points) for axis in range(3)]
        high = [max(p[axis] for p in points) for axis in range(3)]
        listed.append({'node': name, 'location': spot['location'], 'side': 'rear' if spot['rear'] else 'front',
                       'authored': spot['authored'],
                       'min': [round(v, 3) for v in sub(low, body.pivots[name])],
                       'max': [round(v, 3) for v in sub(high, body.pivots[name])]})
    return listed
