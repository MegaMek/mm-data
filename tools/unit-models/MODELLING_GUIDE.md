# Unit model authoring guide

This is the current authoring specification for **every unit family**, including named designs, custom variants,
and generic fallbacks. All use the same coordinate, material, rig and runtime-assembly contracts. Historical
checkpoint reports document what was tested at the time; they do not override this guide. Track unfinished work
in [the plan](MODULAR_MODELS_PLAN.md) and [the animation/damage follow-up](MODULAR_MODELS_POLISH.md).

Start with sections 1–3, follow your family's row in section 4, then build and review using section 8.
Existing full-loadout meshes under `references/legacy/units/` are visual references only.

## 1. One production workflow

1. **Identify the real unit.** Record the chassis/reference variant, movement form and game weight class from
   the unit definition/catalog. Gameplay data owns classification, equipment, troops, conversions and footprints.
2. **Gather references.** Inspect the north-facing game sprite for the top silhouette and equipment placement,
   plus a clear miniature/concept image for depth and articulation. Store source attribution/reference images under
   `tools/unit-models/references/<id>/`. Distinguish fixed body features from optional equipment. Resolve major
   silhouette/proportion disagreements before adding detail. Fallbacks need a deliberate family silhouette too.
3. **Author a bare component and its recipe.** Use the source/helper listed in section 4. Separate rigid moving
   parts and damage locations while constructing the geometry. Do not generate stock/custom loadout combinations,
   casualty combinations, terrain-specific leg lengths, or preassembled troop groups.
4. **Export schema-2 components.** `build_modular_unit_models.py` runs in ordinary Python. Blender is optional for
   authoring or inspection; neither Blender, MCP nor Python runs when a map loads. Java assembles the captured unit
   using the same code for game rendering and native reviews.
5. **Review at the shared scale.** Compare bare and assembled silhouettes, front/back/side/top views, a same-family
   size lineup, and actual animation on terrain. Check attachment clearance, damage, camouflage and both cameras.
6. **Register and validate.** Add the modular model to mekset, run section 8's checks, then stage the reviewed assets
   into MegaMek. Keep the source recipe, generated descriptor/mesh, manifest and review evidence together.

Asset ownership: `Geometry`/Python owns authored shape; `MekTileset` selects a model; `UnitModelState` captures visible
Entity data; `GpuUnitModels` and the existing family assemblers own shared mesh buffers; each displayed instance
owns its pose/materials. `UnitAnimator`/`UnitPlayback` own one presentation timeline for both cameras. Do not add a
second loadout resolver, animation clock or mutable copy of game state to an authoring tool.

## 2. Coordinates, scale and proportions

**All component meshes:** +X right, +Y forward, +Z up, one model-unit convention on all axes. Ground/sole reference
is Z=0 for land bodies; naval bodies retain their authored waterline. Apply transforms to exported vertices,
pivots, sockets, emitters and support metadata together. Do not use legacy Z/54 export scaling.
The exporter uses `Geometry.export(..., z_scale=1, paint_uv=True)`.

For sprite-derived Mek recipes, `[pixelX, pixelY, height]` becomes `[pixelX-42, 36-pixelY, height]`.
Other geometry is authored directly in model coordinates. Exported hardpoints/emitters are **local to their
parent's rest pivot**; the Python helpers convert from authoring coordinates. Do not subtract the pivot twice.

### Mek weight standard: authored bodies, not runtime size profiles

Named chassis and fallbacks follow one standard: **their resting dimensions and proportions are baked into the
asset**. There is no runtime `sizeScales`/`superHeavyScale` enlargement for Mek bodies. Reuse authoring helpers,
but export distinct light, medium, heavy, assault and superheavy bodies for biped, tripod and quad layouts.
The generic hybrid air-Mek also has these five body classes. QuadVee uses its quad body in both modes.

Selection uses `Entity.getWeightClass()` and `Mek.isSuperHeavy()` (currently weight >100t). Ultra-light units use
the light fallback. Do not duplicate tonnage cutoffs in Python or introduce an Alpha Strike size-to-mesh scale.
Named chassis and exact modular variant mappings still take precedence. The default mekset paths use the supported
`{weightClass}` token, for example `units/modular/meks/fallback-tripod-{weightClass}.json`; Java resolves it to
`light`, `medium`, `heavy`, `assault` or `superheavy` before loading.

| Body class | Proportion brief | Starting bare-body height range, model units |
|---|---|---:|
| Light | Narrow chest/hips, thin limbs, compact shoulder masses; long scout legs are allowed | 46–54 |
| Medium | Balanced torso and legs; visibly more volume than a light with comparable posture | 50–57 |
| Heavy | Broad chest and substantial limbs; preserve specialized pod/reverse-leg silhouettes | 53–62 |
| Assault | Deep armor masses, thick thighs/gauntlets, broad planted feet; larger volume than a heavy | 55–66 |
| Superheavy | Clearly larger hull, supports and feet than a 100t assault; substantial depth as well as height | 68–84 |

These are **art review starting ranges**, not gameplay measurements or an automatic normalization rule. A tall,
thin Locust may rival a hunched heavy's height; it must still read as much lighter in width, depth and armored
volume. Weapons, launchers and antennas must not be used to inflate a bare body's apparent weight class. Review
with optional equipment hidden as well as attached. Record deliberate reference-driven exceptions with images.

The fallback proportions live in `FALLBACK_PROPORTIONS` in `unit_mek_models.py`: width, depth, leg span and torso
height vary independently. `fallback_hull()` authors a different hull for each of the three lighter classes;
`fallback_body()` supplies the matching limbs and shared articulation contract. Light is a low cockpit-pod scout
with thin reverse-knee legs; medium has an angular tapered chest, distinct helmet and balanced shoulders; heavy
has broad slab shoulders and a low inset cockpit. The approved boxy assault and enlarged superheavy retain their
existing geometry. Hybrid air-Meks retain their fighter fuselage instead of receiving a humanoid hull.

The current land fallback heights are about 47 / 52 / 53 / 56 / 70 model units, light through superheavy. The
three lighter classes read as roughly 84% / 93% / 96% of the assault's height; distinguish mass primarily through
width, depth, limbs and silhouette rather than making light units tiny. Each class exports its own G3DJ and local
joints/sockets. These are authoring dimensions, not runtime scale factors. Regenerate all layouts and compare the
five-class lineup after a recipe change; never patch only a deployed mesh or its bounding box. Moving a hull's
cockpit or armor panels also requires moving its front/rear hardpoints and optional searchlight socket.

Verified reference units in `data/mekfiles/meks/`: Locust LCT-1V is 20t/light; Warhammer WHM-6R and Archer ARC-2R
are 70t/heavy; Marauder MAD-3R and Mad Cat Prime are 75t/heavy; Atlas AS7-D and Mackie MSK-6S are 100t/assault.
There is no named medium in the current seven-chassis set. Do not label one of the heavy examples as medium to
fill that gap. Use a deliberate intermediate design and compare its body volume with both neighboring classes.

### Board/family fine-tuning

Author and compare with every `UnitFamilyScale` entry at `UNIT_SCALE=1.0f`, `HEIGHT_SCALE=1.0f`. These multiply
`BoardGeometry` settings; they are fine-tuning, not compensation for a wrongly proportioned source mesh.
The normal board unit scale defaults to 0.7; the independent multi-hex default is 0.85 with its own TUNING slider.
Both dimensions and movement distance use `GpuUnitModel.horizontalScale()`/`verticalScale()`; do not recreate
these formulas in a family class. Gameplay `.height()` is not a model-scaling input during prone/conversion.

Other family fallbacks currently use the small `FamilyVisual.SIZE_SCALES` table for their game size profile.
Do not apply that multiplier in their generator as well. For new **named** non-Mek bodies, review their actual
runtime dimensions under this existing policy; a future change to that policy must update all affected assets
and their fixtures together. It is not an excuse to use one Mek body for all weights.

Conventional figures/transports already bake +10% height, and Battle Armor figures +50%, through
`unit_infantry_shapes.bake_height`. Do not apply those changes a second time. Infantry transports retain their
approved 2× assembly scale in `InfantryVisual`; do not copy it into vehicle vertices. Compare a whole group,
not raw troop and transport coordinates in isolation.

## 3. Mesh, materials and component contract

- **Bare-unit target:** under 1,000 triangles before loadout; 1,000–1,500 requires art review. Infantry/BA formations
  have a standing exception to the 1,000 target because they contain multiple figures. **1,500 is the hard cap**
  for any bare effective unit. Count all displayed members and supports. Report body, equipment and total separately.
- **Equipment:** target under 100 triangles, hard maximum 149 for every exported style/profile/fallback. No hidden
  high-detail version may exceed it. Preserve useful silhouette detail rather than chasing an arbitrary minimum.
- Use flat-shaded broad shapes, consistent face winding and valid normals. No degenerate faces, duplicate surfaces,
  invisible ornamental shells or gratuitous materials. Closed cut faces matter where removable parts expose them.
- A descriptor names its mesh relative to itself, rest bounds, kind, family, rig roles, location ownership,
  hardpoints and emitters. Paths must stay inside the model root. The runtime loader validates this contract.
- Use the shared `unit_model_geometry.PALETTE` and exporter material roles. Paint receives camouflage; glass,
  exposed metal, weapon tips and detail retain their authored identity. Do not embed external texture filenames
  into G3DJ. The appearance system owns texture loading and inheritance.
- Paint UVs and damage projection stay in rest space so markings do not crawl during motion. Damage overlays
  blend their alpha over the original opaque surface; do not enable mesh transparency to simulate scratches.
- Every independently moving part has a stable node, rest pivot and parent. Reuse a family's existing rig roles.
  Parts must rotate about physical joints, not their bounding-box centers. Child geometry and equipment follow
  the same joint, including while damaged or hidden. Instances never mutate/dispose a shared source mesh.
- There is no chassis billboard or replacement body for distance LoD. The current renderer hides small attached
  equipment using projected size/hysteresis. Keep bare silhouettes, shadow geometry and embedded troop detail.

## 4. Family recipes and proportions

All dimensions below are **examples from current authored components**, not real-world meters. The generated
`modular/manifest.json` is the current measurement/count record. Rendered family size/footprint fitting still
applies as described in section 2.

| Family | Source and recipe | Shape, articulation and scale review |
|---|---|---|
| Biped Mek | `unit_mek_chassis.py` + `chassis.json`; `unit_mek_models.py` exports | Recognizable head/chest/limbs; waist, shoulder/elbow, hip/knee/foot controls. Match section 2's weight-class lineage. |
| Tripod Mek | `unit_mek_models.py`, `fallback_body('tripod')` | Three stable support legs. Keep the third leg separate; melee kicks always use side legs. Five authored weight classes. |
| Quad / QuadVee | `unit_mek_models.py`, `fallback_body('quad')` | Four distinct articulated limbs, broad support footprint; five authored weight classes. QuadVee squats with horizontal folded legs using the same mesh/equipment. |
| LandAirMek | `air_mek_body()` plus Mek/fighter forms | Hybrid has a pointed cockpit/fuselage, wings, arms, reverse-knee legs and exhaust. Fold using rig joints during conversion; keep loadout modular. No baked fighter weapons. |
| Conventional infantry | `unit_infantry_shapes.person()` + `build_modular_unit_models.py` pose list | Separate standing/advancing/kneeling figures; standing example 8.65×6.95×23.1 after height bake. Jump figures include a small backpack with jet emitter. Runtime survivor count determines composition. |
| Battle Armor | Same figure generator, `armored=True` | Broader armored torso, helmet, limbs/backpack; standing example 11.9×12.5×31.5, 214 triangles. Compression is false: six living suits show six figures, one survivor shows one. |
| Infantry transports | `infantry_vehicle()` for motorized/tracked/wheeled/hover | Motorized jeep/quad; mechanized APC hull with correct drive silhouette. Example motorized 14.6×22.25×13.64 before the approved 2× assembly scale. Separate wheels/hull/boarding/cabin nodes. |
| Ground vehicles | `unit_family_models.vehicle()` | Tracked/wheeled/hover/WiGE/rail silhouettes; hull, drives, wheels and independent turret(s). Example tracked 40.5×52×24.5. Do not give turretless vehicles a turret body. |
| VTOL / airship | `rotorcraft()` | VTOL cockpit, tail, rotor and fixed skids; example rotor envelope about 62×64×27. Airship is a distinct elongated buoyant hull, not an enlarged VTOL. |
| Fighter / aerodyne | `aircraft()` | Narrow nose, clear wings, engines/exhaust; fighter example 66×59.2×17. Transport/aerodyne is deeper, with retractable supports if landable and multi-hex. |
| Spheroid / small craft | `spheroid()` | Rounded faceted hull and separate supports, not a squat box; spheroid example 66×66×64. Follow section 7 for terrain support and full hull retraction. |
| JumpShip / WarShip / station | `capital()` | Elongated ship or radial station silhouettes; separate movable parts only where useful. Preserve actual game footprint; do not invent landing capability or support legs for space-only craft. |
| Naval / hydrofoil / submarine | `naval()` | Long hull and authored waterline, subtype-specific foils/tower; naval example 23×63×23.5. Do not settle watercraft like an infantry figure. |
| ProtoMek | `proto()`, including quad/glider forms | Smaller articulated machine: biped example about 30×14×35.5. Use `proto-v1` joint roles for distance-driven gait; no Mek torso twist/prone rules. |
| Emplacement / building / pods / standalone missile | `static_body()` | Distinct static-family bodies, useful facing/working ports where applicable. Mobile structures/buildings have their own ground integration, not Aero struts. |
| Fighter squadron | `flight_fighter()` + squadron descriptor | Reusable 96-triangle member, about 60×55×11.5 before formation sizing. Runtime uses visible member identities/loadouts; never duplicate a logical weapon group as a physical gun. |

For infantry groups, author **members only**. Conventional headcount is compressed into display slots; transports
replace one slot when there are at most four slots, otherwise two. Troops usually face outward. They board before
vehicle travel and unload only after the vehicle stops. Their final positions/headings and movement jitter are
runtime presentation. Reposition to fit when possible; crowded groups may bleed outside the hex without shrinking
vehicles. Infantry/BA keep embedded rifle/cannon details; additional dynamic equipment remains deferred.

### Required Mek anatomy and damage ownership

Every bare Mek requires actual drawable `HD`, `CT`, `LT`, `RT` surfaces, plus its appropriate arms and legs.
**An empty LT/RT node or a socket named LT/RT is not a torso mesh.** Each armor surface must belong to the correct
location so damage, detachment and attachments work independently. Do not label an entire joined torso as CT.
The migration helper `split_torso_locations()` partitions joined shells without changing their silhouette; new
body functions should label torso regions explicitly along their actual seams.

- Root → pelvis → CT at the waist. Head, side torsos and shoulder joints follow CT; hips/legs follow pelvis.
  Keep upper/lower-body separation clean through ±60° torso twist.
- Biped: `LL/RL`; tripod adds `CL`; quad uses `FLL/FRL/RLL/RRL`. Each needs hip, shin and foot controls exported
  under the existing semantic rig roles. The feet must support the model while knees bend; do not lock whole legs.
- Arms: shoulder → forearm, with optional `LA@hand`, `LA@wrist`, `LA@forearm`, `LA@elbow` (and RA equivalents).
  Actual actuators select the retained anatomy and hand/wrist/elbow attachment. A missing arm must not leave
  floating weapons or a replacement strike limb.
- A detachable head/limb needs a sensible capped cut surface. Validate visibility using the location-damage
  path and the native contact test, including a destroyed side torso taking its arm with it.

## 5. Hardpoints and equipment recipes

Every location capable of carrying modeled equipment needs a front/rear mounting preference. Default biped
recipes cover `HD CT LT RT LA RA LL RL`; tripod/quad recipes use their matching limb tags. A hardpoint contains
stable ID, game location/side, parent, local position, normalized XYZW rotation, positive fitting area, scale
limits and accepted roles. Rear ports must actually clear the rear armor; inspect the rear view.

| Mek recipe field | Current modular meaning |
|---|---|
| `hip` | Sprite-coordinate waist reference; keep on the centerline under the torso. |
| `sockets`, `rearSockets` | Front/rear placement for each real location. Without explicit rear placement the legacy nine-unit offset is used; author rear sockets where that would bury a barrel. |
| `armSockets` | Hand/wrist/elbow locations matching the optional actuator geometry. |
| `socketAim` | +Y-forward replacement direction, by location or `LOC:family`; an arm gun must follow its forearm. |
| `socketBanks` | Authored positions for a weapon family, including actuator-specific keys such as `LA@wrist:ppc`. |
| `mountAreas` | Available width/height for packing each location. Java performs live packing, not Python. |
| `missileSockets`, `missileBayHeight/Width/Columns`, `missileSlope` | Location-specific launcher placement and available bay shape. Tubes remain weapon geometry. |
| `weaponScale`, `missileScale`, `barrelLength`, `protrusion` | Art fitting preferences; inspect both stock and crowded custom refits. |
| `weaponOverrides` | Modular exporter supports location/family/length adjustments. Do not depend on unimplemented legacy name filters. |
| `searchlightSocket` | Optional physical lamp placement only; having a socket never proves the unit carries a lamp. |

`weapons.json` and `unit_weapon_shapes.py` own reusable weapon looks. Use thin square laser barrels, heavier PPC
emitters, recognizably different ballistic/rotary/gauss weapons and correct launcher families. Preserve existing
weapon-tip colors: red laser, blue PPC, green TAG, orange plasma/TSEMP. Cockpits use glass. A physical weapon's
contact point belongs at its striking tip/edge, not its grip. Prefer silhouette over ornamental surface cuts.

Equipment visibility is one shared policy: StructureType/ArmorType/AmmoType never allocate a module. WeaponType
needs a visual or family fallback. MiscType with `F_PHYSICAL_WEAPON` needs a physical module. Optional misc such
as ECM/searchlight requires an explicit mapping; it has no generic fallback. Logical grouped weapons are not
extra hardware. Generic gameplay searchlight capability alone must not create a searchlight housing.

To add future equipment globally, register it in the game's normal equipment system, refresh the catalog and
add a broad shape recipe or a canonical internal-ID mapping to `weapons.json`. Example using an existing module:

```json
{"models": {"ExampleWeaponInternalID": {"model": "units/modular/equipment/custom/example.json", "bankFamily": "laser"}}}
```

Explicit mapping wins over the broad recipe; mandatory exclusions still win. Do not edit generated
`modular/equipment.json` by hand. A new shape needs one geometry recipe; reassigning an existing shape needs no
new renderer or chassis-specific code.

## 6. Animation, effects and damage requirements

Use existing family rig roles and one runtime timeline. Author enough joint clearance for walking/running,
jump/idle/shoot/death and the family's actual conversion. Infantry members remain independently articulated.
Mek punch/kick: walk into reach, plant feet, strike, recover and run back. Push raises arms during the run-in;
overhead weapons raise on approach and strike at contact; lance/spear can thrust. Center tripod legs never kick.
Review at half/normal/double/Instant speed, including skip, pause and final rest pose.

Forced Mek falls use the engine's stored `FallSide` and final facing, fall inside the occupied hex, then get up
through bracing/kneeling. Voluntary prone is a controlled crouch. Infantry poses are cosmetic and do not use
Mek prone state. Do not bake a single fall direction or a default facedown texture into the body.

Each firing exit has an emitter node, local position, normalized direction, role and effect (`laser`, `ppc`,
`bullet`, `missile`, `cluster`, `flame`, etc.). Flame exits sit at the nozzle; larger flamer housings yield larger
plumes. Missiles use the game's rack count (one for `F_LARGE_MISSILE`) and resolved cluster hits; emitter count is
not ammunition count. Smoke, indirect arcs, irregular terrain misses and straight laser rays are runtime VFX,
never baked projectiles or explosions. Jump packs need exhaust emitters for blue flame and dissipating smoke.

Damage artwork is 128×128 RGBA in `data/models/units/textures/`; full-resolution authoring references remain under
`references/damage-textures/`. Mek thresholds, owned by `UnitDamageDisplay`, are `ARMOR_WORN_LOSS=.5`,
`ARMOR_STRIPPED_LOSS=1`, `STRUCTURE_BATTERED_LOSS=.5`, followed by the existing destroyed-location texture.
Whole-body families use `BODY_DAMAGE_1..4=.25/.5/.75/1` on combined armor/internal loss. Intact paint/camo shows
through alpha holes. Infantry/BA never receive these overlays; use living figure counts. Do not replace the
approved darker `destroyed-armor.png` while adding intermediate stages.

## 7. Multi-hex Aero landing supports

Required for future landable multi-hex Aero bodies, including named ships, dedicated variants and family
fallbacks. A Union DropShip is the first review fixture. Building entities/mobile structures are excluded;
their ground integration is separate. Space-only craft do not acquire a new ability to land through this artwork.
The runtime behavior and acceptance gate are specified in the
[plan's landed-support addendum](MODULAR_MODELS_PLAN.md#landed-multi-hex-aero-supports--c4-addendum).

At terrain-relative **elevation 0**, the hull keeps its highest-occupied-support placement and each authored foot
reaches the surface below it. Elevated/flying units have **no protruding struts or legs**. Terrain level and unit
elevation are different: a landed ship above a level-1 hex still deploys its supports.

### Asset contract

| Part/data | Authoring requirement |
|---|---|
| Support identity and ownership | Give each physical support a stable ID and bind it to the hull's existing rig. Supports are bare-body geometry, not equipment mounts. Their number and arrangement follow the craft reference, not the number of occupied hexes. |
| Deployment joint / upper brace | A rigid attachment at the proper hull position, with an authored flat-ground deployed pose and a fully stowed/hidden flight pose. Stowing must remove protrusions; simply rotating visible legs is insufficient. |
| Extendable shaft | Separate the length-changing section from the hull, upper brace and foot. Prefer a simple telescoping lower section with downward travel. It must gain reach without scaling its thickness or stretching the whole support assembly. |
| Foot/pad and contact marker | A separate rigid foot with a contact point on its sole in the nominal flat-ground pose. The marker follows that foot's own support. Feet keep their dimensions when shafts extend. |
| Rest transforms and fitting bounds | Supply consistent rest axes and deployed contact points in the existing +Y-forward/+Z-up convention. Stable body/footprint dimensions drive fitting; runtime extension must not change the ship's nominal size or lift/lower its hull again. |
| Materials and budget | Use existing paint/detail/camouflage/damage roles. Count all support geometry in the bare-unit budget: target under 1,000 triangles, reviewed exceptions up to the unchanged 1,500 hard cap. Reuse geometry and pose it; do not export a mesh for every terrain difference or leg length. |

The schema-2 body descriptor now accepts an optional `landingSupports` list. Each entry has `id`, `node`
(deployment parent), `shaft`, `foot`, `length`, `contact` (three coordinates local to the foot) and `stowedOffset`
(three coordinates translating the deployment node in its parent's frame). Every control
must belong to the rig. The shaft and foot are separate, direct children of the deployment node; neither has
children. Author the shaft with identity rotation/scale, its pivot at the top and its length along local **-Z**.
The foot pivot is exactly `length` below the shaft pivot. Keep the deployed parent upright in world space.
The contact marker is on the sole, usually `[0, 0, -halfFootThickness]`. The shaft stretches only along Z;
its sibling foot translates down without changing its scale. Upper braces remain rigid.

Author `stowedOffset` upward, and inward where necessary, so **all** support geometry is inside the opaque hull
at full retraction. Check the pad's outer corners and the upper brace as well as the shaft. The runtime smoothly
slides the deployment node between these poses while extending/shortening the lower shaft for local ground.
It hides the subtree only after full retraction; hiding must not conceal an incorrectly placed stowed pose.

`Geometry.landing_supports` is exported by `build_modular_unit_models.py`; the reusable `landing_support()`
authoring helper in `unit_family_models.py` builds compatible parts. Descriptor validation rejects missing,
shared or incorrectly parented controls and inconsistent rest lengths before allocating GPU resources.
Existing bodies without this optional field continue to load. The deployed spheroid/small-spheroid bodies
have four supports and use **468 triangles** each; the aerodyne has three supports and uses **312 triangles**.
No mesh is generated per terrain level, and no external program runs when the map opens.

Takeoff reserves a grounded phase for visible withdrawal into the hull before flight starts; landing reserves
a grounded phase for the reverse motion. Each support phase adds 0.45 animation-clock seconds without reducing
travel time (0.9 real seconds at normal playback). The whole transition uses the shared movement
clock, including state-only takeoff/landing updates, queueing, playback speed and skip. Captured ground footprints
keep the fitting stable while the legs move. Newly loaded/revealed units start directly in their current pose.
Ground contact uses existing road/bank/ground
surfaces or solid ice. A contact over open liquid, outside the board or with invalid axes hides that support;
elevation-0 feet do not attach themselves to roofs/bridges above the unit. This does not change landing legality.

Contact points must work after footprint fitting, facing and the live **Multi-hex unit scale** (default **0.85**).
They are sampled at their actual transformed positions, not assigned to fixed hex indices. Author supports with
enough separation and hull clearance to remain credible on uneven terrain; retain the full silhouette when the
unit is viewed from above and from the side. Extended geometry must be available to normal bounds, picking and
shadow rendering, while retracted/hidden geometry must not leave detached feet or shadows in flight.

### Required review checklist for each new body

- [ ] Flat-ground deployed pose: every sole meets the same support level, with the hull clear of the ground.
- [ ] Seven-hex Union over one level-1 hex and six level-0 hexes: hull stays at the level-1 base; feet above level 0
  gain exactly one terrain level of extra reach, and any foot above level 1 retains its normal reach.
- [ ] Mixed ground under different feet: independent extension, no floating pads, hull sinking, widened shafts or
  stretched feet. Rotate the craft and adjust hex/multi-hex scale to check contact conversion.
- [ ] Elevation 0 on raised or negative-level terrain still deploys; positive elevation and airborne altitude
  fully stow/hide the supports. Review takeoff, landing at another site, skip and restored/revealed state.
- [ ] Terrain edits, map edges and supported/unsupported water/bridge/roof surfaces follow the existing surface
  rules without invalid lengths. Buildings/mobile structures never receive this support behavior.
- [ ] Both cameras, picking and shadows match the same extended/stowed geometry. Record body triangle counts and
  native images of actual unit selection and its family fallback before accepting the new body.
- [ ] Retraction/extension visibly slides from/to the hull while the hull remains grounded. At full retraction,
  forcing the support parts visible must not change the rendered hull or its shadow in either camera.

The current Union selection and three updated family bodies are covered by the
[C4 support implementation review](MODULAR_MODELS_C4_SUPPORTS.md). Repeat this checklist for new named or variant art.


## 8. Build, register and review

Sources live in mm-data; Java lives in the MegaMek checkout. Use ordinary Python for the exporter; Pillow is
needed only when packaging review images. Run from the indicated repository, adjusting paths to your checkout:

```powershell
# MegaMek: refresh the equipment inventory from the authoritative registry.
.\gradlew.bat :megamek:exportEquipmentModelCatalog
# mm-data: make a candidate first; no live assembly or unit variants are generated here.
python tools/build_modular_unit_models.py --output .work/model-review/units/modular
# After inspecting the candidate, rebuild deployable components.
python tools/build_modular_unit_models.py
# MegaMek: copy reviewed mm-data into the game and validate the actual loader/assembler.
.\gradlew.bat :megamek:stageDataFiles :megamek:test --tests '*UnitModelDescriptorTest' --tests '*UnitEquipmentModelsTest' --tests '*UnitModelSelectionTest'
.\gradlew.bat :megamek:gpuBoardSmoke --tests '*GpuModularUnitModelsSmokeTest' --tests '*GpuPolishSmokeTest' --tests '*GpuPhysicalContactSmokeTest' --tests '*GpuPlaybackSmokeTest'
# mm-data: package the Java renderer's frames; this script does no model assembly.
python tools/build_unit_review_gallery.py --frames ../megamek_temp/megamek/build/gpu-board-review --output tools/unit-models/references/reviews/my-review
```

The exporter defaults to `.work/modular-models/equipment.json`; use `--catalog` if your refreshed registry is
elsewhere. The Gradle export supports `-PunitModelDataRoot=<mm-data path>`. A checkout with relocated build
outputs must pass its actual native screenshot folder to the gallery packager. The legacy
`validate_unit_models.py` validates old reference-format assets, not the live schema-2 library.

### Adding a Mek or another family member

For a named Mek, add its bare geometry function and `build_chassis` mapping in `unit_mek_chassis.py`, then a
`chassis.json` entry with `name/id/referenceVariant/sprite/illustration/hip/sockets/weaponScale` and useful optional
fields from section 5. Add explicit LT/CT/RT ownership and the existing limb roles. Follow the chosen class's
fallback lineup for scale while preserving the reference silhouette. Do not copy another chassis's dimensions
and simply rename it.

For another family, extend its existing generator function and `build_families()` entry in `unit_family_models.py`.
Use an existing family's rig/assembler when the behavior is the same; a new visual body is not a reason to create
a Java subclass. Body descriptor: `kind=body`, existing family/rig and joints, appropriate hardpoints/emitters.
Assembly descriptor: `kind=family`, that body path, global equipment catalog and mounting preferences. Add new
behavior only if the existing family contract truly cannot represent it. A trooper or infantry transport goes
through the existing pose/vehicle entries in `build_modular_unit_models.py`, not `build_families()`.

Registration examples:

```text
chassis "Example Chassis" "meks/Example.png" "units/modular/meks/example.json"
chassis "Example Vehicle" "vehicles/Example.png" "units/modular/families/example.json"
exact "Example Chassis EX-1" "meks/Example.png" "units/custom/example-ex-1.json"
```

A dedicated variant's modular descriptor may use its own body/mounting preferences. Its loadout still comes
from the current Entity. Use a `compatibility` fingerprint only when the design truly depends on one loadout;
an incompatible custom refit must fall back safely. Custom assets must not share a generated filename.

### Acceptance checklist for every delivered model

- [ ] Reference sprite and useful front/side/concept image, source attribution, and short silhouette brief.
- [ ] Bare mesh, reproducible source recipe, descriptor and manifest agree; no loadout/group combinations in data.
- [ ] Same-family lineup at shared board/family tuning; correct weight/size proportions and no double scaling.
- [ ] Report bare/equipment/assembled triangle counts; all hard caps respected.
- [ ] Required surfaces contain triangles, including all three Mek torso locations; independent location damage
      and detached limbs leave no floating attachments. All rig controls/ports resolve to real nodes.
- [ ] Stock/custom loadout and hand/wrist/elbow/rear mounting checks; no baked searchlights or generic hidden guns.
- [ ] Camouflage and every applicable damage stage in the native shader; intact areas stay readable.
- [ ] Walk/run/jump/attack/idle/death as applicable, foot contact and correct facing; pause/skip/restored state.
- [ ] Conversion uses the correct body/pose without replacing QuadVee geometry. Five Mek fallback classes select
      distinct assets; superheavy is larger than assault.
- [ ] Terrain, footprint, supports and shadows match in both camera views. Multi-hex Aero also passes section 7.
- [ ] Runtime loader/native checks pass; inspect rendered frames and record remaining limitations honestly.

Keep the generated review under `references/reviews/` and link it from the relevant checkpoint. Current review
sets: [C6–C9](references/reviews/c6-c9/index.html) and [animation/damage polish](references/reviews/polish/index.html).
Do not call a screenshot an animation test or claim a dense-battle performance gain without measurement.
