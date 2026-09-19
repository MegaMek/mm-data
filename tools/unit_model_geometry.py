"""Small deterministic mesh writer for rigid, flat-shaded unit models (no runtime Blender dependency)."""
from collections import defaultdict
from math import cos, sin, pi, sqrt
import hashlib
import json


# Git may check these out with either line ending, so their fingerprint must not depend on it.
# Unit files (.mtf) are left out: the Java catalog fingerprints their raw bytes, and this must agree with it.
TEXT_SUFFIXES = {'.py', '.json', '.g3dj', '.txt', '.md'}


def content_digest(path):
    """SHA-256 of a file's content. Text files are read with Unix line endings, whatever is on disk."""
    raw = path.read_bytes()
    if path.suffix.lower() in TEXT_SUFFIXES:
        raw = raw.replace(b'\r\n', b'\n')
    return hashlib.sha256(raw).hexdigest()


def add(a, b):
    return tuple(x + y for x, y in zip(a, b))


def sub(a, b):
    return tuple(x - y for x, y in zip(a, b))


def mul(a, scale):
    return tuple(x * scale for x in a)


def cross(a, b):
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])


def normal(a):
    length = sqrt(sum(x*x for x in a))
    if length < 1e-10:
        raise ValueError('Degenerate face')
    return mul(a, 1/length)


PALETTE = {'paint': (.72, .75, .72), 'edge': (.50, .54, .53),
           'metal': (.22, .26, .28), 'dark': (.065, .085, .095),
           'glass': (.21, .67, .73), 'skin': (.64, .51, .40),
           # Weapon tips: red lasers, blue PPCs, green TAG, orange plasma. Cockpit glazing stays 'glass'.
           'laser': (.86, .13, .11), 'ppc': (.20, .48, 1.0), 'tag': (.22, .80, .30), 'plasma': (.97, .55, .12),
           # The lens of a searchlight.
           'lamp': (.99, .94, .62)}


class Geometry:
    def __init__(self):
        self.faces = []
        self.pivots = {'root': (0, 0, 0)}
        self.parents = {'root': None}

    def joint(self, name, pivot, parent='root'):
        self.pivots[name] = tuple(pivot)
        self.parents[name] = parent

    def face(self, points, group='CT', material='paint'):
        if group not in self.pivots:
            self.joint(group, (0, 0, 0))
        # Inputs are convex rings or quads, with outward winding.
        for i in range(1, len(points)-1):
            tri = (tuple(points[0]), tuple(points[i]), tuple(points[i+1]))
            normal(cross(sub(tri[1], tri[0]), sub(tri[2], tri[0])))
            self.faces.append((tri, group, material))

    def prism(self, ring, bottom, top, group='CT', material='paint', taper=1):
        area = sum(ring[i][0]*ring[(i+1) % len(ring)][1]
                   - ring[(i+1) % len(ring)][0]*ring[i][1] for i in range(len(ring)))
        if area < 0:
            ring = list(reversed(ring))
        cx = sum(p[0] for p in ring)/len(ring)
        cy = sum(p[1] for p in ring)/len(ring)
        lo = [(x, y, bottom) for x, y in ring]
        hi = [(cx+(x-cx)*taper, cy+(y-cy)*taper, top) for x, y in ring]
        self.face(list(reversed(lo)), group, material)
        self.face(hi, group, material)
        for i in range(len(ring)):
            j = (i+1) % len(ring)
            self.face([lo[i], lo[j], hi[j], hi[i]], group, material)

    def box(self, center, size, group='CT', material='paint', bevel=0, taper=1):
        x, y, z = center
        a, b, c = (n/2 for n in size)
        if min(a, b, c) <= 0:
            raise ValueError('Nonpositive box dimensions')
        cut = min(a, b)*bevel
        ring = [(-a, -b), (a, -b), (a, b), (-a, b)] if not cut else [
            (-a+cut, -b), (a-cut, -b), (a, -b+cut), (a, b-cut),
            (a-cut, b), (-a+cut, b), (-a, b-cut), (-a, -b+cut)]
        self.prism([(x+u, y+v) for u, v in ring], z-c, z+c, group, material, taper)

    def beam(self, start, end, width, depth=None, group='CT', material='metal', sides=4, taper=1):
        axis = normal(sub(end, start))
        u = normal(cross(axis, (0, 0, 1) if abs(axis[2]) < .9 else (0, 1, 0)))
        v = cross(axis, u)
        depth = width if depth is None else depth
        rings = []
        for p, scale in ((start, 1), (end, taper)):
            rings.append([add(p, add(mul(u, cos(2*pi*i/sides+pi/4)*width*.5*scale),
                                     mul(v, sin(2*pi*i/sides+pi/4)*depth*.5*scale)))
                          for i in range(sides)])
        self.face(list(reversed(rings[0])), group, material)
        self.face(rings[1], group, material)
        for i in range(sides):
            j = (i+1) % sides
            self.face([rings[0][i], rings[0][j], rings[1][j], rings[1][i]], group, material)

    def loft(self, rings, group='CT', material='paint'):
        """Join matching convex sections, wound toward the last section."""
        if len(rings) < 2 or len({len(r) for r in rings}) != 1:
            raise ValueError('Loft needs matching polygon sections')
        self.face(list(reversed(rings[0])), group, material)
        self.face(rings[-1], group, material)
        for lo, hi in zip(rings, rings[1:]):
            for i in range(len(lo)):
                j = (i+1) % len(lo)
                self.face([lo[i], lo[j], hi[j], hi[i]], group, material)

    def extend(self, other, offset=(0, 0, 0), angle=0, group=None):
        c, s = cos(angle), sin(angle)
        def transform(p):
            return (p[0]*c-p[1]*s+offset[0], p[0]*s+p[1]*c+offset[1], p[2]+offset[2])
        for tri, node, material in other.faces:
            self.face([transform(p) for p in tri], group or node, material)

    def export(self, path, name, z_scale=54, budget=1000):
        if len(self.faces) > budget:
            raise ValueError(f'{name}: {len(self.faces)} triangles exceeds {budget}')
        vertices, unique, parts = [], {}, defaultdict(list)
        for tri, group, material in self.faces:
            pivot = self.pivots[group]
            points = [(p[0]-pivot[0], p[1]-pivot[1], (p[2]-pivot[2])/z_scale) for p in tri]
            n = normal(cross(sub(points[1], points[0]), sub(points[2], points[0])))
            color = PALETTE[material]
            # Keep separate paint and fixed-color surfaces for owner/camouflage tinting.
            part = (group, 'paint' if material in ('paint', 'edge') else 'detail')
            for p in points:
                vertex = tuple(round(x, 7) for x in (*p, *n, *color, 1))
                key = (group, vertex)
                if key not in unique:
                    unique[key] = len(vertices)//10
                    vertices.extend(vertex)
                parts[part].append(unique[key])
        def node(group):
            parent = self.parents[group]
            translation = sub(self.pivots[group], self.pivots[parent]) if parent else self.pivots[group]
            entry = {'id': group, 'translation': [translation[0], translation[1], translation[2]/z_scale]}
            entry['parts'] = [{'meshpartid': g+'-'+role, 'materialid': role} for g, role in parts if g == group]
            entry['children'] = [node(child) for child in self.pivots if self.parents[child] == group]
            return entry
        model = {'version': [0, 1], 'id': name, 'meshes': [],
                 'materials': [{'id': role, 'diffuse': [1, 1, 1]} for role in ('paint', 'detail')],
                 'nodes': [node('root')]}
        if vertices:
            model['meshes'] = [{'attributes': ['POSITION', 'NORMAL', 'COLOR'], 'vertices': vertices,
                                'parts': [{'id': g+'-'+r, 'type': 'TRIANGLES', 'indices': indices}
                                          for (g, r), indices in parts.items()]}]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(model, separators=(',', ':'))+'\n', encoding='utf-8')
        bounds = [[min(p[i] for tri, _, _ in self.faces for p in tri),
                   max(p[i] for tri, _, _ in self.faces for p in tri)] for i in range(3)] if self.faces else []
        return {'triangles': len(self.faces), 'vertices': len(vertices)//10, 'bounds': bounds,
                'sha256': content_digest(path)}
