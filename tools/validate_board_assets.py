"""Validate the shipped 3D board catalog, roof fidelity and isolated dependencies."""
from pathlib import Path
import json
from PIL import Image, ImageChops

ROOT = Path(__file__).resolve().parents[1]
BOARD = ROOT / 'data/models/board'
buildings = json.loads((BOARD / 'building-manifest.json').read_text())
features = json.loads((BOARD / 'manifest.json').read_text())
maximum = 0
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
        source = Image.open(BOARD / 'tileset' / buildings[asset]['source']).convert('RGBA')
        roof = Image.open(BOARD / (asset + '-roof.png')).convert('RGB')
        difference = ImageChops.difference(source.convert('RGB'), roof)
        mask = source.getchannel('A').point(lambda alpha: 255 if alpha >= 245 else 0)
        assert ImageChops.multiply(difference.convert('L'), mask).getbbox() is None, path

sources = json.loads((BOARD / 'tileset/sources.json').read_text())['files']
for name in sources:
    copy = BOARD / 'tileset' / name
    assert copy.is_file(), copy
    assert copy.resolve().is_relative_to((BOARD / 'tileset').resolve()), copy
    assert not copy.samefile(ROOT / 'data/images/hexes' / name), copy
print(json.dumps({'buildings': len(buildings), 'features': len(features),
                  'max_triangles': maximum, 'independent_tileset_files': len(sources)}))
