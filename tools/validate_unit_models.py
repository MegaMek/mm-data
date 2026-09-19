"""Validate generated geometry, source provenance, budgets and complete variant mount coverage. Stdlib only."""
import argparse
import json
import math
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from unit_model_geometry import content_digest

ROOT = Path(__file__).resolve().parents[1]


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    return content_digest(path)


LOWER_LOCATIONS = ('pelvis', 'LL', 'RL', 'CL', 'FLL', 'FRL', 'RLL', 'RRL')
# The game finds a location's part by its own abbreviation, so every body must carry one part per location.
LOCATIONS = {'biped': {'HD', 'CT', 'LT', 'RT', 'LA', 'RA', 'LL', 'RL'},
             'tripod': {'HD', 'CT', 'LT', 'RT', 'LA', 'RA', 'LL', 'RL', 'CL'},
             'quad': {'HD', 'CT', 'LT', 'RT', 'FLL', 'FRL', 'RLL', 'RRL'}}


def check_upper_body(path, name, layout='biped'):
    """The game turns the named part on its own to show a torso twist, so it must carry exactly the upper body.
    It also hides or darkens the part named after a lost or destroyed location, so each location needs its part."""
    model = json.loads(path.read_text(encoding='utf-8'))
    found, names = [], set()

    def visit(node, offset, inside):
        here = [offset[i]+node.get('translation', (0, 0, 0))[i] for i in range(3)]
        names.add(node['id'])
        if node['id'] == name:
            found.append(here)
        elif node['id'].startswith(LOWER_LOCATIONS):
            require(not inside, str(path)+': '+node['id']+' must not hang from '+name)
        elif node['id'] != 'root':
            # Anything that is not a hip or leg part belongs to the upper body, including any new group a
            # future body adds, so nothing is left behind when the upper body turns.
            require(inside, str(path)+': '+node['id']+' must hang from '+name)
        for child in node.get('children', []):
            visit(child, here, inside or node['id'] == name)

    for node in model['nodes']:
        visit(node, (0, 0, 0), False)
    require(len(found) == 1, str(path)+': missing upper body part '+name)
    missing = LOCATIONS[layout]-names
    require(not missing, str(path)+': no part for location '+', '.join(sorted(missing)))
    require(abs(found[0][0]) < 1e-6, str(path)+': the upper body must turn about the center line')


def validate(out, catalog_path):
    manifest = json.loads((out / 'manifest.json').read_text(encoding='utf-8'))
    catalog = json.loads(catalog_path.read_text(encoding='utf-8'))
    require(not catalog['failures'], 'Catalog contains failures')
    require(sha(catalog_path) == manifest['catalogSha256'], 'Catalog changed; rebuild the models')
    require(sha(ROOT / 'tools/unit-models/chassis.json') == manifest['recipesSha256'], 'Chassis recipes changed')
    require(sha(ROOT / 'tools/build_unit_models.py') == manifest['generatorSha256'], 'Generator changed')
    require(sha(ROOT / 'tools/unit_model_geometry.py') == manifest['geometrySha256'], 'Geometry writer changed')
    require(sha(ROOT / 'tools/unit_mek_chassis.py') == manifest['chassisBuilderSha256'], 'Chassis artwork changed')
    require(sha(ROOT / 'tools/unit_weapon_shapes.py') == manifest['weaponShapesSha256'], 'Weapon shapes changed')
    require(sha(ROOT / 'tools/unit-models/weapons.json') == manifest['weaponRulesSha256'], 'Weapon rules changed')
    require(sha(ROOT / 'tools/unit_mount_layout.py') == manifest['mountLayoutSha256'], 'Mount layout changed')
    for name, reference in manifest['references'].items():
        require(sha(ROOT / 'data/images/units' / reference['sprite']) == reference['spriteSha256'], name+': reference sprite changed')
        if 'illustration' in reference:
            require(sha(ROOT / 'data/images/fluff' / reference['illustration']) == reference['illustrationSha256'], name+': reference illustration changed')
    maximum = 0
    for relative, expected in manifest['models'].items():
        path = (out / relative).resolve()
        require(path.is_relative_to(out), 'Model escapes asset directory: '+relative)
        require(sha(path) == expected['sha256'], 'Model changed: '+relative)
        model = json.loads(path.read_text(encoding='utf-8'))
        triangles, ids = 0, set()
        for mesh in model['meshes']:
            require(mesh['attributes'] == ['POSITION', 'NORMAL', 'COLOR'], relative+': unexpected vertex format')
            vertices = mesh['vertices']
            require(len(vertices) % 10 == 0 and all(math.isfinite(v) for v in vertices), relative+': invalid vertices')
            for i in range(0, len(vertices), 10):
                require(abs(sum(v*v for v in vertices[i+3:i+6])-1) < 1e-5, relative+': invalid normal')
            for part in mesh['parts']:
                require(part['id'] not in ids, relative+': duplicate mesh part')
                ids.add(part['id'])
                indices = part['indices']
                require(len(indices) % 3 == 0, relative+': partial triangle')
                require(all(isinstance(i, int) and 0 <= i < len(vertices)//10 for i in indices), relative+': invalid index')
                triangles += len(indices)//3
                for i in range(0, len(indices), 3):
                    a, b, c = [vertices[j*10:j*10+3] for j in indices[i:i+3]]
                    ab, ac = [b[k]-a[k] for k in range(3)], [c[k]-a[k] for k in range(3)]
                    normal = (ab[1]*ac[2]-ab[2]*ac[1], ab[2]*ac[0]-ab[0]*ac[2], ab[0]*ac[1]-ab[1]*ac[0])
                    require(sum(v*v for v in normal) > 1e-15, relative+': degenerate triangle')
                    stored = vertices[indices[i]*10+3:indices[i]*10+6]
                    require(sum(normal[k]*stored[k] for k in range(3)) > 0, relative+': inverted normal')
        require(triangles == expected['triangles'] and triangles <= manifest['budget'], relative+': triangle budget')
        require(triangles > 0 or relative.endswith('/squad-0.g3dj'), relative+': unexpectedly empty model')
        referenced, nodes = set(), set()
        materials = {m['id'] for m in model['materials']}
        def visit(node):
            require(node['id'] not in nodes, relative+': duplicate node')
            nodes.add(node['id'])
            for part in node.get('parts', []):
                require(part['materialid'] in materials, relative+': missing material')
                require(part['meshpartid'] in ids, relative+': missing mesh part')
                require(part['meshpartid'] not in referenced, relative+': part drawn twice')
                referenced.add(part['meshpartid'])
            for child in node.get('children', []):
                visit(child)
        for node in model['nodes']:
            visit(node)
        require(ids == referenced, relative+': unreachable mesh part')
        maximum = max(maximum, triangles)
    for descriptor_path in sorted(out.glob('fallback/*.json')):
        descriptor = json.loads(descriptor_path.read_text(encoding='utf-8'))
        require('upperBodyNode' in descriptor, str(descriptor_path)+': no upper body part named')
        check_upper_body(descriptor_path.parent / descriptor['fallback'], descriptor['upperBodyNode'],
                         descriptor_path.stem)
    for descriptor_path in out.rglob('model.json'):
        descriptor = json.loads(descriptor_path.read_text(encoding='utf-8'))
        targets = [descriptor['fallback'], *descriptor.get('variants', {}).values(), *descriptor.get('formations', {}).values()]
        require(descriptor['kind'] != 'mek' or 'upperBodyNode' in descriptor,
                str(descriptor_path)+': no upper body part named')
        if 'upperBodyNode' in descriptor:
            for target in [descriptor['fallback'], *descriptor.get('variants', {}).values()]:
                check_upper_body(descriptor_path.parent / target, descriptor['upperBodyNode'])
        for mode, formations in descriptor.get('movementFormations', {}).items():
            require(set(formations) == set(map(str, range(7))), mode+': missing formation size')
            targets.extend(formations.values())
        for target in targets:
            path = (descriptor_path.parent / target).resolve()
            require(path.is_relative_to(out) and path.is_file(), 'Missing descriptor target '+str(path))
            require(path.relative_to(out).as_posix() in manifest['models'], 'Untracked model '+str(path))
    for relative, formation in manifest.get('formations', {}).items():
        slots = formation['slots']
        components = formation['components']
        vehicles = sum(c['role'] == 'vehicle' for c in components)
        troopers = sum(c['role'] == 'trooper' for c in components)
        expected_vehicles = (0, 1, 1, 1, 1, 2, 2)[slots] if formation['movementMode'] != 'INF_JUMP' else 0
        require(vehicles == expected_vehicles and troopers == slots-vehicles,
                relative+': transport/trooper composition mismatch')
        require(sum(manifest['models'][c['asset']]['triangles'] for c in components)
                == manifest['models'][relative]['triangles'], relative+': missing or duplicated formation geometry')
        for component in components:
            require(all(math.isfinite(v) for v in [*component['position'], component['angle']]),
                    relative+': invalid placement')
    by_source = {u['source']: u for u in catalog['units']}
    for name, entry in manifest['variants'].items():
        unit = by_source[entry['source']]
        require(sha(ROOT / 'data' / unit['source']) == entry['sourceSha256'], name+': unit source changed')
        require(sha(ROOT / 'data/images/units' / unit['sprite']) == entry['spriteSha256'], name+': sprite changed')
        expected = {(m['index'], m['internalName'], m['location'], m['rear'], m['rackSize'])
                    for m in unit['equipment'] if m['family'] != 'internal'}
        actual = [(a['equipmentIndex'], a['equipment'], a['location'], a['rear'], a['rackSize']) for a in entry['attachments']]
        require(expected == set(actual) and len(actual) == len(expected), name+': equipment assembly mismatch')
    print(json.dumps({'models': len(manifest['models']), 'variants': len(manifest['variants']),
                      'maximumTriangles': maximum, 'needsReview': len(manifest['needsReview'])}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default=str(ROOT / 'data/models/units'))
    parser.add_argument('--catalog', default=str(ROOT / '.work/mek-models/catalog.json'))
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else None)
    validate(Path(args.output).resolve(), Path(args.catalog).resolve())
