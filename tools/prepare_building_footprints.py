"""Offline outline preparation; runtime never extrudes terrain pixels.

Follow the active Saxarba include tree, retain the exact roof pixels, and simplify
each opaque footprint to a small polygon before Blender triangulates it.
"""
from pathlib import Path
from collections import defaultdict, deque
import json
import math
import re
from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'data/models/board'
HEXES = OUT / 'tileset'
seen, sources = set(), set()


def scan(path):
    if path in seen:
        return
    seen.add(path)
    for line in path.read_text(errors='replace').splitlines():
        fields = re.findall(r'"([^"]*)"', line)
        if line.startswith('include ') and fields:
            scan(HEXES / fields[0])
        elif line.startswith(('super ', 'base ')) and fields:
            if any(t.startswith('building:') for t in fields[0].split(';')):
                sources.update(fields[2].split(';'))


def rdp(points, epsilon):
    if len(points) < 3:
        return points
    a, b = points[0], points[-1]
    dx, dy = b[0]-a[0], b[1]-a[1]
    length = math.hypot(dx, dy)
    distances = [abs(dy*(p[0]-a[0])-dx*(p[1]-a[1])) / length
                 if length else math.dist(a, p) for p in points[1:-1]]
    far = max(range(len(distances)), key=distances.__getitem__)
    if distances[far] <= epsilon:
        return [a, b]
    split = far+1
    return rdp(points[:split+1], epsilon)[:-1]+rdp(points[split:], epsilon)


def area(poly):
    return sum(a[0]*b[1]-a[1]*b[0] for a,b in zip(poly,poly[1:]+poly[:1])) / 2


def contours(mask):
    width, height = mask.size
    filled = {(x,y) for y in range(height) for x in range(width) if mask.getpixel((x,y))}
    edges = defaultdict(list)
    for x,y in filled:
        for neighbor,a,b in [((x,y-1),(x,y),(x+1,y)), ((x+1,y),(x+1,y),(x+1,y+1)),
                             ((x,y+1),(x+1,y+1),(x,y+1)), ((x-1,y),(x,y+1),(x,y))]:
            if neighbor not in filled:
                edges[a].append(b)
    loops = []
    while edges:
        start = next(iter(edges))
        loop, current = [], start
        while True:
            loop.append(current)
            targets = edges[current]
            target = targets.pop()
            if not targets:
                del edges[current]
            current = target
            if current == start:
                break
        if len(loop) < 4 or abs(area(loop)) < 12:
            continue
        opposite = max(range(len(loop)), key=lambda i: math.dist(loop[0],loop[i]))
        epsilon = max(width/84, height/72)*1.2
        simplified = rdp(loop[:opposite+1],epsilon)[:-1]+rdp(loop[opposite:]+loop[:1],epsilon)[:-1]
        while len(simplified) > 80:
            epsilon *= 1.2
            simplified = rdp(loop[:opposite+1],epsilon)[:-1]+rdp(loop[opposite:]+loop[:1],epsilon)[:-1]
        if len(simplified) >= 3:
            loops.append(simplified)
    return loops


scan(HEXES / 'saxarba.tileset')
entries = []
for source in sorted(sources):
    path = HEXES / source
    if not path.is_file():
        raise FileNotFoundError(path)
    image = Image.open(path).convert('RGBA')
    width,height = image.size
    # Exclude the tileset's translucent drop shadow from the physical footprint.
    mask = image.getchannel('A').point(lambda value: 255 if value >= 245 else 0)
    loops = contours(mask)
    if not loops:
        continue
    asset = 'buildings/' + str(Path(source).with_suffix('')).replace('\\','/')
    # Extend only RGB into transparent texels for bilinear filtering at simplified
    # edges. Every original opaque roof texel and its UV location stays unchanged.
    rgba = list(image.getdata())
    queue = deque(i for i,p in enumerate(rgba) if p[3] >= 245)
    visited = set(queue)
    while queue:
        index = queue.popleft()
        x,y = index%width,index//width
        for nx,ny in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
            ni=ny*width+nx
            if 0 <= nx < width and 0 <= ny < height and ni not in visited:
                visited.add(ni)
                if rgba[ni][3] < 245:
                    rgba[ni] = (*rgba[index][:3],rgba[ni][3])
                queue.append(ni)
    roof = OUT / (asset+'-roof.png')
    roof.parent.mkdir(parents=True,exist_ok=True)
    prepared = Image.new('RGB', image.size)
    prepared.putdata([p[:3] for p in rgba])
    prepared.save(roof)
    entries.append({'source':source,'asset':asset,'width':width,'height':height,'loops':loops})
(ROOT/'tools/building-footprints.json').write_text(json.dumps(entries,separators=(',',':')))
print(json.dumps({'sources':len(sources),'models':len(entries),'max_outline_vertices':max(sum(map(len,e['loops'])) for e in entries)}))
