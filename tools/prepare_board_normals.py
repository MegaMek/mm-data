"""Prepare faceted normal maps from the independent GPU ground tileset (Pillow + NumPy).

RGB is a tangent-space normal in image U/right, V/down coordinates. Alpha is the
source mask, so normal layers follow the exact albedo layering at runtime. These
are shading approximations from painted brightness, not measured height data.
"""
from pathlib import Path
import argparse
import hashlib
import json
import re

import numpy as np
from PIL import Image

GROUND = {'road', 'road_fluff', 'pavement', 'sand', 'snow', 'tundra', 'mud', 'swamp',
          'ice', 'magma', 'fields', 'rough', 'rubble'}
CELL = 4
FLAT = (128, 128, 255)


def strength(terrains, theme):
    types = set(terrains)
    if 'pavement' in types or ('road' in types and terrains['road'] != '3'):
        return 0.0
    if types & {'rough', 'rubble'}:
        return 12.0
    if 'ice' in types:
        return 1.0
    if types & {'snow', 'tundra'} or 'snow' in theme:
        return 4.0
    if 'sand' in types or 'desert' in theme or 'sand' in theme:
        return 3.0
    if types & {'mud', 'swamp'} or 'mars' in theme or 'dirt' in theme:
        return 5.0
    if 'magma' in types or any(word in theme for word in ('lunar', 'rock', 'volcan')):
        return 8.0
    return 4.0


def sources(tileset):
    result, seen = {}, set()

    def scan(name):
        if name in seen:
            return
        seen.add(name)
        for line in (tileset / name).read_text(errors='replace').splitlines():
            line = line.strip()
            quoted = re.findall(r'"([^"]*)"', line)
            if line.startswith('include ') and quoted:
                scan(quoted[0])
            elif line.startswith(('base ', 'super ')) and len(quoted) >= 3:
                terrains = {part.split(':')[0]: part.split(':')[1]
                            for part in quoted[0].split(';') if ':' in part}
                if line.startswith('super ') and not set(terrains).issubset(GROUND):
                    continue
                for image in quoted[2].split(';'):
                    if image:
                        image = image.replace('\\', '/')
                        amount = strength(terrains, quoted[1].lower())
                        result[image] = max(result.get(image, 0), amount)

    scan('saxarba.tileset')
    return dict(sorted(result.items()))


def read_source(tileset, name):
    crop = re.search(r'\((\d+),(\d+)-(\d+),(\d+)\)$', name)
    path = (tileset / (name[:crop.start()] if crop else name)).resolve()
    if not path.is_relative_to(tileset.resolve()):
        raise ValueError(name)
    with Image.open(path) as source:
        image = source.convert('RGBA')
    if crop:
        x, y, width, height = map(int, crop.groups())
        image = image.crop((x, y, x + width, y + height))
    return image


def faceted(image, amount):
    pixels = np.array(image, dtype=np.uint8)
    height, width = pixels.shape[:2]
    output = np.empty_like(pixels)
    output[:, :, :3] = FLAT
    output[:, :, 3] = pixels[:, :, 3]
    if not amount:
        return Image.fromarray(output)

    alpha = pixels[:, :, 3].astype(np.float32) / 255
    light = (pixels[:, :, :3] @ np.array([.2126, .7152, .0722], dtype=np.float32)) / 255
    # Smooth individual paint texels, never treating transparent RGB as a height.
    weights = np.pad(alpha, 2, mode='edge')
    weighted = np.pad(light * alpha, 2, mode='edge')
    total, mass = np.zeros_like(light), np.zeros_like(light)
    for y in range(5):
        for x in range(5):
            total += weighted[y:y + height, x:x + width]
            mass += weights[y:y + height, x:x + width]
    blurred = np.divide(total, mass, out=np.full_like(total, np.nan), where=mass > 0)
    xs = np.minimum(np.arange(0, width + CELL, CELL), width - 1)
    ys = np.minimum(np.arange(0, height + CELL, CELL), height - 1)
    samples = blurred[ys[:, None], xs]
    a, b = samples[:-1, :-1], samples[:-1, 1:]
    c, d = samples[1:, :-1], samples[1:, 1:]

    def normal(origin, horizontal, vertical, sign_x, sign_y):
        values = np.stack((origin, horizontal, vertical))
        valid = np.isfinite(values)
        count = valid.sum(axis=0)
        mean = np.divide(np.where(valid, values, 0).sum(axis=0), count,
                         out=np.zeros_like(origin), where=count > 0)
        values = np.where(valid, values, mean)
        x = sign_x * (values[1] - values[0]) * amount / CELL
        y = sign_y * (values[2] - values[0]) * amount / CELL
        vectors = np.stack((x, y, np.ones_like(x)), axis=-1)
        vectors /= np.linalg.norm(vectors, axis=-1, keepdims=True)
        return np.rint(128 + 127 * vectors).clip(0, 255).astype(np.uint8)

    row, col = np.indices(a.shape)
    reverse = ((row + col) % 2 != 0)[:, :, None]
    first = np.where(reverse, normal(b, a, d, 1, -1), normal(a, b, c, -1, -1))
    second = np.where(reverse, normal(c, d, a, -1, 1), normal(d, c, b, 1, 1))
    y, x = np.indices((height, width))
    row, col = y // CELL, x // CELL
    lower = np.where((row + col) % 2 != 0, y % CELL > x % CELL, x % CELL + y % CELL >= CELL)
    output[:, :, :3] = np.where(lower[:, :, None], second[row, col], first[row, col])
    output[alpha == 0, :3] = FLAT
    return Image.fromarray(output)


def prepare(board, check=False):
    tileset = board / 'tileset'
    manifest = {'cell_pixels': CELL, 'encoding': 'U-right V-down; neutral 128,128,255', 'images': {}}
    for name, amount in sources(tileset).items():
        image = read_source(tileset, name)
        normal = faceted(image, amount)
        destination = board / 'normals' / (name + '.png')
        if check:
            with Image.open(destination) as existing:
                assert existing.mode == 'RGBA' and existing.size == image.size, destination
                assert existing.tobytes() == normal.tobytes(), f'Stale normal map: {destination}'
        else:
            destination.parent.mkdir(parents=True, exist_ok=True)
            normal.save(destination, optimize=True)
        manifest['images'][name] = {'size': list(image.size), 'strength': amount,
                                    'source_sha256': hashlib.sha256(image.tobytes()).hexdigest()}
    manifest_file = board / 'normal-manifest.json'
    if check:
        assert json.loads(manifest_file.read_text()) == manifest, 'Normal manifest is stale'
        actual = {str(path.relative_to(board / 'normals')).replace('\\', '/')
                  for path in (board / 'normals').rglob('*.png')}
        assert actual == {name + '.png' for name in manifest['images']}, 'Unexpected normal assets'
    else:
        manifest_file.write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps({'normal_maps': len(manifest['images']), 'checked': check,
                      'bytes': sum(path.stat().st_size for path in (board / 'normals').rglob('*.png'))}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--board', type=Path, default=Path(__file__).resolve().parents[1] / 'data/models/board')
    parser.add_argument('--check', action='store_true', help='Verify all generated maps without writing')
    args = parser.parse_args()
    prepare(args.board.resolve(), args.check)
