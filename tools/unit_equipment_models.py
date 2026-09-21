"""Compile equipment art rules into finite, reusable modules and canonical-ID mappings.

This exports equipment shapes only. Java selects and fits live Mounted items; it does not repeat these regex rules.
"""
from copy import deepcopy
import hashlib
import json

from unit_model_geometry import Geometry
from unit_weapon_shapes import BOOK, draw, held_for, rule_for


def fallback_rule(item, low_detail=False):
    family = item['family']
    if item['policy'] == 'PHYSICAL_WEAPON' or family == 'infantry-melee':
        return {'id': 'fallback-physical', 'look': 'blade'}
    if family in ('missile', 'bomb', 'mine', 'screen-launcher'):
        return {'id': 'fallback-launcher', 'look': 'launcher', 'tubes': 'hatch', 'tubeCount': 1}
    return {'id': 'fallback-weapon', 'look': 'barrel', 'length': 6, 'width': 2,
            'sides': 3 if low_detail else 4, 'protrusion': 'long',
            'tip': {'laser': 'laser', 'ppc': 'ppc', 'energy': 'plasma', 'sensor': 'tag'}.get(family, 'dark')}


def build_equipment(catalog, output, export_asset):
    assets, mappings, fallback_models, diagnostics = {}, {}, {}, []
    required = ('WEAPON', 'PHYSICAL_WEAPON')

    def module(item, rule, style='default', low_detail=False, options=None):
        mount = dict(item, location='mount', rear=False)
        rule = deepcopy(rule)
        if style != 'default' and rule['look'] in ('barrel', 'gatling'):
            rule['protrusion'] = style
        geometry = Geometry(modular=True)
        geometry.joint('mount', (0, 0, 0))
        draw(geometry, mount, rule, (0, 0, 0), 1, {'detail': 'panel' if low_detail else 'full', **(options or {})})
        if item['policy'] in required and not geometry.emitters:
            raise ValueError('Required equipment has no emitter/contact: '+item['internalName'])
        effect = {'laser': 'laser', 'ppc': 'ppc', 'energy': 'energy', 'sensor': 'none', 'flamer': 'flame',
                  'ballistic': 'bullet', 'machine-gun': 'bullet',
                  'extinguisher': 'spray', 'screen-launcher': 'screen', 'bomb': 'bomb', 'mine': 'mine'}.get(item['family'])
        if effect is not None:
            for emitter in geometry.emitters:
                emitter['effect'] = effect
                if effect == 'bullet':
                    emitter['role'] = 'muzzle'
        content = json.dumps({'faces': geometry.faces, 'emitters': geometry.emitters}, sort_keys=True, separators=(',', ':'))
        key = 'equipment/library/'+hashlib.sha256(content.encode()).hexdigest()[:20]
        if key not in assets:
            assets[key] = export_asset(geometry, output, key, 'equipment', item['family'], 'module-v1',
                                       {'root': 'root', 'aim': 'mount'})
        return 'units/modular/'+key+'.json'

    for item in catalog['equipment']:
        policy = item['policy']
        if policy not in (*required, 'OPTIONAL_MISC'):
            continue
        # An explicit canonical-ID mapping wins over broad authoring recipes, after mandatory type exclusions.
        rule = rule_for(dict(item, location='mount', rear=False))
        authored = BOOK.get('models', {}).get(item['internalName'])
        if authored:
            override = {'model': authored} if isinstance(authored, str) else dict(authored)
            bank = 'lamp' if rule and rule['look'] == 'lamp' else (rule or {}).get('bankFamily', item['family'])
            mappings[item['internalName']] = {'family': item['family'], 'bankFamily': bank, 'policy': policy,
                                             'fallback': False, 'styles': {}, **override}
            continue
        missing = rule is None
        if missing and policy == 'OPTIONAL_MISC':
            continue
        if missing:
            rule = fallback_rule(item)
            diagnostics.append({'internalName': item['internalName'], 'family': item['family'], 'reason': 'weapon fallback'})
        choices = {}
        if rule['look'] in ('barrel', 'gatling'):
            for style in ('recessed', 'short', 'medium', 'long'):
                choices[style] = module(item, rule, style)
        model = module(item, rule)
        profiles = {}
        if rule['look'] == 'launcher':
            profiles['columns-4'] = module(item, rule, options={'maximumColumns': 4})
            profiles['vertical-slope'] = module(item, rule, options={'maximumColumns': 4,
                                             'orientation': 'vertical', 'slope': .45, 'slopeOrigin': 0})
            # Stood on end against an upright face, with no lean.
            profiles['vertical'] = module(item, rule, options={'maximumColumns': 4, 'orientation': 'vertical'})
        if not missing and held_for(dict(item, location='mount', rear=False), rule):
            # A gun gripped in the fist; used only where a recipe asks for it at a hand.
            profiles['held'] = module(item, rule, options={'held': True})
        entry = {'model': model, 'styles': choices, 'profiles': profiles, 'family': item['family'],
                 'bankFamily': 'lamp' if rule['look'] == 'lamp' else rule.get('bankFamily', item['family']),
                 'policy': policy, 'fallback': missing}
        if policy == 'WEAPON':
            entry['lowDetail'] = module(item, fallback_rule(item, True), low_detail=True)
        mappings[item['internalName']] = entry

    # These assets also cover a weapon type added to the game after this art catalog was exported.
    for family in ('weapon', 'missile', 'laser', 'ppc', 'energy', 'flamer', 'sensor', 'infantry-melee', 'physical',
                   'bomb', 'mine', 'screen-launcher', 'extinguisher'):
        item = {'internalName': 'fallback-'+family, 'name': family, 'family': family, 'rackSize': 1,
                'policy': 'PHYSICAL_WEAPON' if family == 'physical' else 'WEAPON'}
        fallback_models[family] = module(item, fallback_rule(item, True), low_detail=True)
    metadata = {'schema': 2, 'equipment': mappings, 'fallbacks': fallback_models, 'diagnostics': diagnostics,
                'note': 'Mappings describe reusable equipment, not unit variants. Optional misc has no generic fallback.'}
    (output / 'equipment.json').write_text(json.dumps(metadata, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
    print(f'Equipment: {len(mappings)} canonical mappings, {len(assets)} shared module assets, {len(diagnostics)} fallbacks')
    return assets
