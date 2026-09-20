# Low-poly runtime unit models

The game uses reusable assets under `modular/` and assembles each visible unit from its actual loadout or surviving troops. Python and Blender are authoring/review tools; the game launches neither.

`GpuUnitModels.ENABLED` is **true**. Both GPU camera views share the same models and placement.

## Geometry budget

The bare unit before loadout targets **under 1,000 triangles**. Conventional infantry and Battle Armor always qualify for an exception because multiple figure/transport meshes form one game unit. Other families need art review to exceed the target. The **1,500-triangle bare-unit hard cap** applies to all families. Equipment is additional; report body, equipment and total costs separately. Preserve the full-detail 214-triangle BA figure (six suits: 1,284). Distance LoD hides small attached equipment; body meshes remain unchanged.

Each equipment module has a separate target of **under 100 triangles** and a strict maximum of **149**.
The exporter and runtime validator check this independently of the bare body and assembled totals.

## Runtime assets

- `modular/meks/<chassis>.json`: a body, mounting preferences and the global equipment catalog. The seven authored chassis are Atlas, Locust, Warhammer, Mad Cat, Marauder, Archer and Mackie.
- `modular/meks/fallback-<layout>-<weightClass>.json`: separately authored light/medium/heavy/assault/superheavy bodies for biped, tripod, quad and hybrid air-Mek layouts. Mek weight class and `isSuperHeavy()` select the asset; there is no runtime size-profile scaling.
- `modular/bodies/`: bare bodies, location ownership, rigid joints and hardpoint areas.
- `modular/equipment.json`: canonical equipment ID to reusable module, optional placement styles and weapon-family fallbacks.
- `modular/equipment/library/`: independently shared weapon/misc meshes with emitter/contact metadata.
- `modular/infantry.json`, `modular/battle-armor.json`: runtime formation recipes using independent `troops/` and `transports/` components. BA compression is disabled: one figure per living trooper. Conventional infantry uses up to six displayed slots; transport slots follow movement mode.
- `modular/families/`: shared vehicle, aircraft, naval, ProtoMek, static and squadron fallback descriptors, verified at C4.
- `modular/manifest.json`: the current reusable asset inventory, bounds and triangle counts.

Troop recipes use one `trooper` asset and, for conventional jump infantry, an optional
`jumpTrooper` asset. The three `troops/*-standing` meshes are the base rigs; kneeling,
watching, walking and jumping are runtime joint animations. Advancing and kneeling
mesh variants are no longer shipped or exported. Jump packs remain equipment-specific
geometry with emitters attached to the animated torso.

Mekset paths are relative to `data/models`:

```text
chassis "Atlas" "meks/Atlas.png" "units/modular/meks/atlas.json"
exact "default_medium" "defaults/default_medium.png" "units/modular/meks/fallback-biped-{weightClass}.json"
exact "default_infantry" "defaults/default_infantry_platoon.png" "units/modular/infantry.json"
```

Exact model overrides precede chassis entries, then the normal family fallback. A sprite-only exact entry inherits its chassis model. A dedicated modular variant may replace the body/mounting descriptor; its equipment still comes from the current unit. An optional `compatibility` fingerprint restricts a descriptor to its intended loadout. Sensor contacts do not reveal model identity or troop count.

Structure changes replace that unit's assembly tree. Mesh buffers are shared; material state, damage and joint transforms remain per instance. Required weapons without authored mappings use weapon-family fallbacks. Armor, structure, ammo and logical weapon containers allocate no modules. Optional misc needs an explicit mapping and has no generic fallback.

Inner Sphere and Clan Mek Partial Wing share one 96-triangle deployed paired-wing module. The renderer uses
the existing rear-torso mounting height, seats the root on the actual back with the shared surface picker, and
derives the span from the bare body's width. Named chassis and all fallback layouts use this placement without
individual wing sockets. The pair follows torso animation, inherits
paint/camouflage and equipment damage, and does not occupy weapon or jump-jet mounting space. Critical slots
spread across the torsos still produce one assembly. ProtoMek and Battle Armor wing art is not mapped by this Mek recipe.

Conventional infantry and Battle Armor retain their approved figure meshes. Dynamic equipment attachment for
these families is deliberately deferred until the end; passenger equipment must not be attached to transports.

The normal unit scale defaults to `0.7` (`BoardGeometry.DEFAULTS`). Whole multi-hex models use the separate
`BoardGeometry.DEFAULT_MULTI_HEX_UNIT_SCALE = 0.85f` default and the dedicated **Multi-hex unit scale** slider
in **TUNING** (F9). Changing either slider does not change the other; Defaults restores both values.

Paint uses the existing Entity/force/owner camouflage image or color, including rotation and scale.
Attached destroyed locations and disabled equipment use `textures/destroyed-armor.png`, an authored 128×128
grayscale texture. Confirmed blown-off Mek locations hide their anatomy and equipment. Collectable arms/legs
on the ground reuse the canonical `Limb Club` equipment mesh and the actual terrain counts; classic markers
remain the fallback when models are disabled or unavailable. See `tools/unit-models/MODULAR_MODELS_C5.md`.

Intermediate damage uses seven authored 128x128 RGBA overlays. Mek locations show worn armor, exposed structure
and battered structure before the existing destroyed material; whole-body families have four damage stages.
Infantry/BA use survivor counts instead. `UnitDamageDisplay` owns the configurable thresholds.

## Authoring and verification

The primary specification for all families is [MODELLING_GUIDE.md](../../../tools/unit-models/MODELLING_GUIDE.md).
It covers proportions, weight classes, parts/joints, effects, damage, supports and reproducible authoring/review.

Run `python tools/build_modular_unit_models.py` in mm-data after exporting the equipment catalog described in `tools/unit-models/MODULAR_MODELS_C1.md`. This creates finite reusable components, not variant/headcount combinations. Add a global canonical-ID mapping in `tools/unit-models/weapons.json` to reuse or replace an equipment mesh everywhere; optional object mappings may also specify `bankFamily`.

In MegaMek, the `UnitModelDescriptorTest` validates these assets through the actual loader contract. The native `GpuModularUnitModelsSmokeTest` assembles real stock units and a custom refit, validates bindings and writes top/isometric review images. Run the focused tests and `:megamek:gpuBoardSmoke --tests '*GpuModularUnitModelsSmokeTest'`, then `:megamek:stageDataFiles` to update local game data.

`GpuPartialWingSmokeTest` reviews every current Mek body with both wing types and each torso as the primary
critical location. It also writes `partial-wing-{locust,atlas,marauder}-{isometric,top}.png` to MegaMek's
`build/gpu-board-review/`, using real stock loadouts with the wing added. Each image shows the front at left
and the rear at right. Run `:megamek:gpuBoardSmoke --tests '*GpuPartialWingSmokeTest'` to reproduce the renders.

Full baked loadouts and old formation files live in **`tools/unit-models/references/legacy/units`**, outside deployed data. Historical verification copies are in `tools/unit-models/references/verification`. They remain visual targets; no game mapping points to them. `build_unit_models.py` is a legacy reference tool and refuses output beneath `data/`.

The checkpoint plan and remaining animation, boarding, firing/death and performance work are tracked in `tools/unit-models/MODULAR_MODELS_PLAN.md`. Runtime mounting is not a claim that every chassis has bespoke artwork or that all later checkpoints are finished.
