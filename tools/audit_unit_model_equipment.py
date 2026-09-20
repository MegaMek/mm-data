"""Audit the registered-equipment export against existing art recipes, without generating unit variants."""
import argparse
from collections import Counter
import json
from pathlib import Path

from unit_model_geometry import content_digest
from unit_weapon_shapes import BOOK, RULES_PATH, rule_for

ROOT = Path(__file__).resolve().parents[1]


def audit(catalog):
    if catalog.get('schema') != 1:
        raise ValueError('Expected equipment catalog schema 1')
    entries, policies, coverage, recipes = [], Counter(), Counter(), set()
    identifiers = Counter()
    for item in catalog['equipment']:
        policy = item['policy']
        if policy not in ('NONE', 'MEMBERS', 'WEAPON', 'PHYSICAL_WEAPON', 'OPTIONAL_MISC'):
            raise ValueError('Unknown equipment policy: '+policy)
        expected_fallback = policy in ('WEAPON', 'PHYSICAL_WEAPON')
        if item['allowsFallback'] != expected_fallback:
            raise ValueError('Incorrect fallback policy: '+item['internalName'])
        identifiers[item['internalName']] += 1
        policies[policy] += 1
        entry = {key: item[key] for key in ('internalName', 'name', 'policy', 'family')}
        rule = None
        if policy == 'NONE':
            status = 'excluded'
        elif policy == 'MEMBERS':
            status = 'members'
        else:
            mount = dict(item, location='', rear=False)
            rule = rule_for(mount)
            if rule is not None:
                status = 'recipe'
                entry['recipe'] = rule['id']
                entry['look'] = rule['look']
                recipes.add(rule['id'])
            elif expected_fallback:
                status = 'needs-physical-fallback' if policy == 'PHYSICAL_WEAPON' else 'needs-weapon-fallback'
            else:
                status = 'optional-omitted'
        entry['coverage'] = status
        coverage[status] += 1
        entries.append(entry)
    return {
        'schema': 1,
        'note': 'Recipe coverage is not a claim that modular meshes, emitters or animation are exported or reviewed.',
        'counts': {'equipment': len(entries), 'policy': dict(sorted(policies.items())),
                   'coverage': dict(sorted(coverage.items())), 'matchedRecipes': len(recipes)},
        'unmatchedRecipeIds': sorted(rule['id'] for rule in BOOK['rules'] if rule['id'] not in recipes),
        'duplicateInternalIds': sorted(name for name, count in identifiers.items() if count > 1),
        'equipment': entries,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--catalog', type=Path, default=ROOT / '.work/modular-models/equipment.json')
    parser.add_argument('--output', type=Path, default=ROOT / '.work/modular-models/equipment-coverage.json')
    args = parser.parse_args()
    report = audit(json.loads(args.catalog.read_text(encoding='utf-8')))
    report['catalogSha256'] = content_digest(args.catalog)
    report['weaponRulesSha256'] = content_digest(RULES_PATH)
    report['weaponShapesSha256'] = content_digest(ROOT / 'tools/unit_weapon_shapes.py')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
    print(json.dumps(report['counts'], sort_keys=True))


if __name__ == '__main__':
    main()
