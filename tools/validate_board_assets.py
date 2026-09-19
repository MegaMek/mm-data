"""Validate the shipped 3D board catalog, roof fidelity and isolated dependencies."""
from pathlib import Path
import json
from PIL import Image, ImageChops

ROOT = Path(__file__).resolve().parents[1]
BOARD = ROOT / 'data/models/board'
buildings = json.loads((BOARD / 'building-manifest.json').read_text())
features = json.loads((BOARD / 'manifest.json').read_text())
maximum = 0
assert not {'tank', 'industrial'}.intersection(features), 'Generic structure models must not return'
for asset in dict(features, **buildings):
    path = BOARD / (asset + '.g3dj')
    model = json.loads(path.read_text())
    triangles = 0
    for mesh in model['meshes']:
        assert mesh['attributes'] == ['POSITION', 'NORMAL', 'COLOR', 'TEXCOORD0'], path
        vertices = mesh['vertices']
        assert len(vertices) % 12 == 0, path
        for part in mesh['parts']:
            indices = part['indices']
            assert len(indices) % 3 == 0, path
            assert all(0 <= index < len(vertices) // 12 for index in indices), path
            triangles += len(indices) // 3
            if part['id'] == 'roof' and asset in buildings:
                for offset in range(0, len(indices), 3):
                    a, b, c = [vertices[index * 12:index * 12 + 3] for index in indices[offset:offset + 3]]
                    normal_z = (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
                    assert normal_z > 0, f'Roof winding: {path}'
    assert 0 < triangles <= 500, (path, triangles)
    maximum = max(maximum, triangles)
    for material in model['materials']:
        for texture in material.get('textures', []):
            dependency = (path.parent / texture['filename']).resolve()
            assert dependency.is_relative_to(BOARD.resolve()), dependency
            assert dependency.is_file(), dependency
    if asset in buildings:
        facade = buildings[asset]['wall_texture']
        wall = next(material for material in model['materials'] if material['id'] != 'roof')
        assert (path.parent / wall['textures'][0]['filename']).resolve() == (BOARD / facade).resolve(), path
        assert '/full-resolution/' not in facade, path
        assert Image.open(BOARD / facade).size == (128, 128), path
        assert (wall['id'] == 'shell') == buildings[asset]['full_height_facade'], path
        source = Image.open(BOARD / 'tileset' / buildings[asset]['source']).convert('RGBA')
        roof = Image.open(BOARD / (asset + '-roof.png')).convert('RGB')
        difference = ImageChops.difference(source.convert('RGB'), roof)
        mask = source.getchannel('A').point(lambda alpha: 255 if alpha >= 245 else 0)
        assert ImageChops.multiply(difference.convert('L'), mask).getbbox() is None, path
    elif asset not in ('bridge', 'field') and not asset.startswith('rock-'):
        roles = {material['id'] for material in model['materials']}
        leaf = ('needles-pine' if asset.startswith('pine') else
                'leaves-willow' if asset.startswith('willow') else
                'fronds-palm' if asset.startswith('palm') else 'leaves-broad')
        bark = 'bark-birch' if asset.startswith('birch') else 'bark-palm' if asset.startswith('palm') else 'bark'
        assert roles == {leaf, bark} | ({'snow'} if asset.endswith('-snow') else set()), (asset, roles)
        for material in model['materials']:
            assert material['textures'][0]['filename'] == f"textures/foliage/{material['id']}.png", path
        for mesh in model['meshes']:
            vertices = mesh['vertices']
            for part in mesh['parts']:
                assert part['indices'], (asset, part['id'])
                for offset in range(0, len(part['indices']), 3):
                    a, b, c = [vertices[index * 12 + 10:index * 12 + 12]
                               for index in part['indices'][offset:offset + 3]]
                    area = (b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0])
                    assert abs(area) > 1e-10, f'Collapsed foliage UV: {asset}: {part["id"]}'
                if part['id'] == 'snow':
                    assert all(min(vertices[index * 12 + 6:index * 12 + 9]) > .75
                               for index in part['indices']), f'Snow must not inherit foliage tint: {asset}'

for family in ('buildings', 'terrain'):
    folder = BOARD / 'textures' / family
    for original in (folder / 'full-resolution').glob('*.png'):
        assert min(Image.open(original).size) > 128, original
        assert Image.open(folder / original.name).size == (128, 128), original

for name in ('bed', 'grass-rim', 'dirt-rim', 'sand-rim', 'rock-rim', 'concrete-rim', 'snow-rim'):
    with Image.open(BOARD / 'textures' / (name + '.png')) as image:
        assert image.size == (128, 128), name
        assert image.convert('RGBA').getchannel('A').getextrema() == (255, 255), name

for path in (BOARD / 'textures/foliage').glob('*.png'):
    with Image.open(path) as image:
        assert image.size == (64, 64), path
        assert image.convert('RGBA').getchannel('A').getextrema() == (255, 255), path

sources = json.loads((BOARD / 'tileset/sources.json').read_text())['files']
for name in sources:
    copy = BOARD / 'tileset' / name
    assert copy.is_file(), copy
    assert copy.resolve().is_relative_to((BOARD / 'tileset').resolve()), copy
    assert not copy.samefile(ROOT / 'data/images/hexes' / name), copy
print(json.dumps({'buildings': len(buildings), 'features': len(features),
                  'max_triangles': maximum, 'independent_tileset_files': len(sources)}))
