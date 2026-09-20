"""Export reusable schema-2 assets, without baking any loadout or troop-count combinations.

Python authors art only. Unit selection, attachment fitting and formation assembly belong to Java.
Run with Python (Blender's bundled Python also works); no bpy or Blender process is required.
"""
import argparse
import json
import re
from pathlib import Path

from unit_infantry_shapes import person, infantry_vehicle, bake_height
from unit_model_geometry import Geometry, TRIANGLE_LIMIT, TRIANGLE_TARGET, sub
from unit_weapon_shapes import draw, rule_for
from unit_equipment_models import build_equipment
from unit_mek_models import build_meks, fallback_recipes
from unit_family_models import build_families

ROOT = Path(__file__).resolve().parents[1]
EQUIPMENT_TRIANGLE_TARGET = 100
EQUIPMENT_TRIANGLE_LIMIT = 149


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')


def archive_superseded_modules(output, assets):
    """Only generated hash-named files in the deployed library; never touch custom meshes or scratch exports."""
    if output.resolve() != (ROOT / 'data/models/units/modular').resolve():
        return
    live = {Path(key).name for key in assets if key.startswith('equipment/library/')}

    def references(value):
        if isinstance(value, dict):
            for child in value.values():
                references(child)
        elif isinstance(value, list):
            for child in value:
                references(child)
        elif isinstance(value, str) and value.startswith('units/modular/equipment/library/'):
            live.add(Path(value).stem)

    # Explicit canonical mappings can reuse an earlier exported asset; the manifest alone does not list those.
    references(json.loads((output / 'equipment.json').read_text(encoding='utf-8')))
    library = (output / 'equipment/library').resolve()
    archive = (ROOT / 'tools/unit-models/references/equipment-library').resolve()
    archive.mkdir(parents=True, exist_ok=True)
    count = 0
    for path in library.iterdir():
        if not re.fullmatch(r'[0-9a-f]{20}\.(json|g3dj)', path.name) or path.stem in live:
            continue
        if not path.resolve().is_relative_to(library):
            raise ValueError('Generated module link escapes its library: '+str(path))
        target = archive / path.name
        if target.exists():
            if target.read_bytes() != path.read_bytes():
                raise ValueError('Reference archive already has different contents: '+str(target))
            path.unlink()
        else:
            path.rename(target)
        count += 1
    print(f'Archived {count} superseded generated equipment files')


def export_asset(geometry, output, key, kind, family, rig, joints, hardpoints=(), *, leg_bends=None):
    if kind == 'equipment' and len(geometry.faces) > EQUIPMENT_TRIANGLE_LIMIT:
        raise ValueError(f'{key}: equipment has {len(geometry.faces)} triangles; maximum {EQUIPMENT_TRIANGLE_LIMIT}')
    descriptor = output / (key+'.json')
    mesh = descriptor.with_suffix('.g3dj')
    stats = geometry.export(mesh, key, z_scale=1, bare_unit=kind != 'equipment', paint_uv=True)
    emitters = [{**emitter, 'position': sub(emitter['position'], geometry.pivots[emitter['node']])}
                for emitter in geometry.emitters]
    locations = {node: node.split('-')[0].split('@')[0] for node in geometry.pivots
                 if node.split('-')[0].split('@')[0] in ('HD', 'CT', 'LT', 'RT', 'LA', 'RA', 'LL', 'RL',
                                                       'CL', 'FLL', 'FRL', 'RLL', 'RRL')}
    write_json(descriptor, {
        'schema': 2, 'kind': kind, 'family': family, 'mesh': mesh.name,
        'bounds': {'min': [axis[0] for axis in stats['bounds']], 'max': [axis[1] for axis in stats['bounds']]},
        'rig': rig, 'joints': joints, 'locations': locations,
        'hardpoints': list(hardpoints), 'emitters': emitters,
        **({'legBends': leg_bends} if leg_bends else {}),
        **({'landingSupports': geometry.landing_supports} if geometry.landing_supports else {}),
    })
    return stats


def build(output, catalog):
    assets = {}
    recipes = json.loads((ROOT / 'tools/unit-models/chassis.json').read_text(encoding='utf-8'))['chassis']
    assets.update(build_meks(recipes+fallback_recipes(), output, export_asset, write_json))
    assets.update(build_families(output, export_asset, write_json))

    joints = {role: node for role, node in [('root', 'root'), ('hips', 'hips'), ('torso', 'torso'), ('head', 'head')]}
    for side in ('left', 'right'):
        joints.update({side+'Arm': side+'Arm', side+'Forearm': side+'ArmForearm', side+'Leg': side+'Leg',
                       side+'Shin': side+'LegShin', side+'Foot': side+'LegFoot'})
    for kind, armored, jump in (('rifle', False, False), ('jump', False, True), ('battle-armor', True, False)):
        key = 'troops/'+kind+'-standing'
        troop = bake_height(person('standing', armored=armored, jump=jump, modular=True), armored=armored)
        assets[key] = export_asset(troop, output, key, 'troop', 'battle-armor' if armored else 'infantry',
                                   'trooper-v1', joints)
    for kind in ('motorized', 'tracked', 'wheeled', 'hover'):
        key = 'transports/'+kind
        transport = bake_height(infantry_vehicle(kind, modular=True))
        joints = {'root': 'root', 'hull': 'vehicle', 'boarding': 'boarding', 'exit': 'boarding', 'cabin': 'cabin'}
        joints.update({node: node for node in transport.pivots if node.startswith('wheel-')})
        assets[key] = export_asset(transport, output, key, 'body', 'infantry-transport', 'transport-v1', joints)

    equipment = {item['internalName']: item for item in catalog['equipment']}
    for key, internal_name in (('ppc', 'PPC'), ('srm-6', 'SRM 6'), ('searchlight', 'Searchlight')):
        mount = dict(equipment[internal_name], location='mount', rear=False)
        rule = rule_for(mount)
        if rule is None:
            raise ValueError('Missing reference equipment recipe: '+internal_name)
        module = Geometry(modular=True)
        module.joint('mount', (0, 0, 0))
        draw(module, mount, rule, (0, 0, 0), 1)
        assets['equipment/'+key] = export_asset(module, output, 'equipment/'+key, 'equipment',
                                                mount['family'], 'module-v1', {'root': 'root', 'aim': 'mount'})
    assets.update(build_equipment(catalog, output, export_asset))
    write_json(output / 'manifest.json', {'schema': 2, 'triangleTarget': TRIANGLE_TARGET,
                                         'triangleLimit': TRIANGLE_LIMIT, 'triangleBudgetScope': 'bare-unit',
                                         'equipmentTriangleTarget': EQUIPMENT_TRIANGLE_TARGET,
                                         'equipmentTriangleLimit': EQUIPMENT_TRIANGLE_LIMIT, 'assets': assets,
                                         'note': 'Reusable components; the Java renderer assembles formations/loadouts.'})
    for family, prefix in (('infantry', 'rifle'), ('battle-armor', 'battle-armor')):
        descriptor = {'schema': 2, 'kind': 'formation', 'family': family,
                      'trooper': 'units/modular/troops/'+prefix+'-standing.json'}
        if family == 'infantry':
            descriptor['jumpTrooper'] = 'units/modular/troops/jump-standing.json'
            descriptor['vehicles'] = {mode: 'units/modular/transports/'+kind+'.json' for mode, kind in
                                      (('INF_MOTORIZED', 'motorized'), ('TRACKED', 'tracked'),
                                       ('WHEELED', 'wheeled'), ('HOVER', 'hover'))}
        write_json(output / (family+'.json'), descriptor)
    archive_superseded_modules(output, assets)
    print(f'Exported {len(assets)} independent assets; maximum {max(a["triangles"] for a in assets.values())} triangles')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'data/models/units/modular')
    parser.add_argument('--catalog', type=Path, default=ROOT / '.work/modular-models/equipment.json')
    args = parser.parse_args()
    build(args.output, json.loads(args.catalog.read_text(encoding='utf-8')))
