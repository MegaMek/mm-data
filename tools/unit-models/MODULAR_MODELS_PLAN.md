# Modular unit models: implementation plan

Status: C0–C8 proof-of-concept behavior has recorded verification, including the C4 landed-Aero support addendum.
C9 migration, authoring, gallery and resource checks are complete; **production performance sign-off remains open**.
The C0 component benchmark passes, but full-board stress runs still have excessive draw calls and long frame-time tails.
See the [completion review and measured limits](MODULAR_MODELS_COMPLETION.md) and the subsequent
[stride, equipment LoD and tree/rendering review](MODULAR_MODELS_DETAIL.md). The
[2026-09-20 implementation review](MODULAR_MODELS_REVIEW.md) found five defects; R1–R5 are now corrected with
[verification evidence](MODULAR_MODELS_REVIEW_FIXES.md). The checkpoint list below is the active source of task status;
dated evidence documents record what was verified at that time.
Updated: 2026-09-20. Scope: MegaMek's GPU board and the shared mm-data art pipeline.

## 1. Outcome and boundaries

Ship reusable bodies, equipment, troop meshes and animation data. Assemble the actual units present in a game from their current Entity state. Stop shipping a complete mesh for every loadout or every infantry headcount. An unlisted custom refit must work without running Blender or rebuilding mm-data.

Deployment requirement (2026-09-19): the existing full baked loadouts are visual references only. Move them, their descriptors and old baked formations out of deployed/work directories into `tools/unit-models/references/`; game mappings must select dynamic assemblies. The legacy reference builder must not regenerate baked files under deployed `data/`.

The first deliverable is a playable proof of concept for every unit family, with modular Meks, correct formation counts, basic animation, weapon emitters, camouflage and large footprints. Production quality means readable silhouettes, consistent transforms, correct state transitions, predictable asset ownership and measured performance. It does not require a replacement game engine, a physics simulation or a large class hierarchy.

Preserve the established low-poly look, infantry proportions, doubled infantry vehicles, staggered placements, torso twist, damage display, both camera views and the existing model switch. Leave `GpuUnitModels.ENABLED` enabled unless requested otherwise. **Bare-unit working target: under 1,000 triangles, before any loadout is applied. Conventional infantry and Battle Armor are always exempt from this target because several figure/transport meshes form one game unit. Reviewed bare units may use up to 1,500 triangles; the 1,500 bare-unit hard cap still applies to all families.** Weapons and selected visual equipment are additional and do not consume this body allowance. Report body, equipment and assembled totals separately; effects have their own measured cost. Conventional infantry and Battle Armor keep their authored component detail. The six-BA formation uses 1,284 triangles (214 each); keep its helmet/torso bevels, backpack, rifle and cannon detail. Equipment-only distance detail is implemented as specified below; body mesh replacement remains out of scope.

This document is the migration plan. [MODELLING_GUIDE.md](MODELLING_GUIDE.md) remains the current authoring guide; its visual conventions still apply. Its instructions to bake every variant and formation are replaced only when the corresponding migration checkpoint passes.

LoD decision (2026-09-20): **keep the actual unit/body mesh unchanged and progressively hide equipment at small
screen sizes**. Hide unreadable fittings first; retain silhouette-defining equipment until its removal is visually
imperceptible. Preserve real 3D body shadows, authoritative loadout/emitter bindings, damage state, troop counts and
footprint/picking. Use projected pixels with hysteresis, not camera distance or generic replacement bodies. Do not
author additional chassis/variant meshes, billboards or simplified body LoDs for this approach. The subsequent
implementation request is now handled: attachment diameter below 4 projected pixels, with 15% hysteresis;
selected units and participants in active attacks retain full detail. Embedded parts stay visible. See the
[measured implementation](MODULAR_MODELS_DETAIL.md); the [initial assessment](MODULAR_MODELS_LOD_STUDY.md)
remains historical context. Runtime LoD does not mutate damage flags, gameplay state, picking or emitters.

Equipment art clarification (2026-09-19, coordinated weapon task): each equipment module should ideally stay **under 100 triangles** and must stay **strictly under 150** (149 maximum), including compact/style/profile exports and fallbacks. Enforce this independently in the exporter and runtime validator. The complete body plus loadout can exceed 1,500; no individual weapon inherits the body's allowance.

Infantry equipment decision (2026-09-19): **do not attach dynamic equipment to conventional infantry or Battle Armor
during the current implementation**. Keep their approved figure meshes and current rifle/cannon details. Revisit
trooper-level equipment only at the end, after visual and performance review; it may not be worth implementing.
The equipment catalog can retain those assets for reference/future use. Do not assign passenger weapons to
transport vehicles, or treat a catalog entry as proof that it is already mounted on a troop.

## 2. Verified starting point

This is the historical pre-migration baseline, not a description of the current implementation. See the
checkpoint list and implementation review for current coverage.

Repository paths in this document are relative to either **mm-data** or **megamek_temp**, as labelled. Counts are observations, not permanent acceptance criteria.

| Area | Current implementation | Consequence for this plan |
|---|---|---|
| Shipped models | `data/models/units/manifest.json`: 7 authored Mek chassis, 188 assemblies, 261 mesh assets at inspection | Preserve authored anatomy; migrate its output rather than starting over. |
| Authoring | `tools/build_unit_models.py`, `unit_mek_chassis.py`, `unit_weapon_shapes.py`, `unit_mount_layout.py`; `tools/unit-models/{chassis,weapons}.json` | Separate geometry authoring from live loadout selection and placement. |
| Equipment input | `megamek/src/megamek/utilities/MekModelCatalog.java` scans Mek MTFs and exports equipment, locations and actuator information | Useful reference/test catalog; it must cease being a runtime prerequisite. Extend equipment coverage using the real equipment registry. |
| Selection/loading | `UnitModelSelection`, `GpuUnitModels`, `MekTileset`, `UnitModelKey` | Today a loadout fingerprint selects a baked mesh; unknown refits fall back to a body. Keep tileset precedence, replace the baked dependency. |
| Rigging | Existing rigid nodes, pelvis/CT pivots and some shin/arm parts; `UpperBodyTurn` already animates torso twist | There is a useful partial rigid hierarchy, but no complete shared family rig/clip contract. |
| Movement/damage | `UnitMotion` owns path playback; `UnitDamageDisplay` handles location loss; `GpuBattleView` adds airborne wobble | Extend these responsibilities; do not introduce a second movement clock or lose existing damage behavior. |
| Infantry | Separate source poses/vehicle meshes exist, but the shipped selection uses baked groups | Reuse the artwork and composition rules; retain separate children at runtime. |
| Searchlights | Warhammer and Mackie body functions contain lamps; exporter classifies searchlights as internal | Remove baked lamps only as their dynamic replacements become available. Include external Entity searchlights as well as mounted equipment. |
| Muzzles/effects | Weapon builders calculate barrel ends but do not export emitter contracts. `BoardScene.FiringLine` is an order/overlay line | Export actual emitter transforms. An attack declaration is not proof that a weapon fired or hit. |
| Camo | `GpuBattleView` uses average sprite hue; `Camouflage` supports images, inherited choices, rotation and scale | Image camouflage needs a material path, not another average-color approximation. |
| Large units | `GpuBoardSource` emits secondary sprite parts independently; `GpuMeeple.place()` uses scale 1 for those parts, 0.6 for ordinary units | A complete large model must be assembled once, with independent 0.85 scaling and a shared support height. |
| Prone | `Mek.height()` returns 0 when prone, otherwise 1 or 2 for superheavy. `Entity` stores only a prone boolean | Do not squash an animated model a second time through its current gameplay height. Add the requested persistent cause. |

## 3. Non-negotiable design rules

1. **Entity and existing client/game code remain authoritative.** Equipment, locations, visibility, gameplay facing where applicable, legal movement, prone state, damage, occupancy and attack outcomes are not recomputed by the renderer. Conventional infantry and Battle Armor have no gameplay facing; their individual figures and conventional-infantry transports have cosmetic headings only.
2. **One snapshot boundary.** Swing captures immutable visible appearance/state data; the render thread never retains or reads Entity, Mounted, mutable Camouflage or AWT images. CPU asset parsing may run off the UI thread; GPU creation/disposal stays on the GL thread.
3. **One runtime assembly implementation.** Java assembles live units and produces review fixtures. Python authors meshes and metadata; it does not keep a competing variant/formation assembly algorithm after migration.
4. **Share resources, isolate state.** Mesh buffers, textures and clips are shared; transforms, material parameters, damage masks and playback belong to each displayed unit/child. Twisting or painting one unit cannot change another.
5. **Deterministic presentation.** Slots and idle variation may use a stable unit/member seed, never gameplay RNG or frame-time randomness. Infantry arrival variation also uses the destination, sampled once for that arrival. Rendering, camera changes, casualty reconciliation and unchanged snapshots must not reshuffle survivors or reroll their headings. Normal playback and skip select the same final formation.
6. **Only Meks get gameplay torso twist and prone animation.** Vehicle turret rotation is separate. Infantry kneeling, lying down and aiming are cosmetic poses, never changes to `Entity.isProne()`.
7. **Type-specific equipment policy.** Structure, armor and ammunition never create models or hardpoints. Weapons require visualization with fallbacks; physical misc weapons require visualization. Other misc equipment is explicitly opted in and has no generic fallback. Report missing required visuals and missing opted-in assets without inventing misc attachments.
8. **Review working slices.** Every checkpoint includes behavior checks, actual-renderer visual review and a correctness/complexity review before moving on.

## 4. Small architecture, explicit ownership

Keep the existing GPU board package. Extract a class when it owns a distinct responsibility, not because a new
type exists in the rules hierarchy. The implementation now uses the owners below; completing the plan does not
require adding the earlier proposed `UnitVisual` wrapper or a separate handler for every family.

| Responsibility | Owner / continuation rule |
|---|---|
| Capture authorized structure, equipment, appearance, pose and footprint | `GpuBoardSource`, `UnitModelSelection`, `UnitModelState` and immutable `BoardScene` records. Game/client state owns rules, survivors, size, visibility and outcomes. |
| Resolve mekset override, chassis and family fallback | Existing tileset/model selection; retain explicit dispatch and no reflective discovery or plugin registry. |
| Decide equipment scope and identity | `EquipmentModelPolicy` and `UnitModelEquipment`, shared by tooling and live capture. Type policy must be supplemented by actual mounted grouping state; logical weapon groups are not extra guns. |
| Load/cache validated assets and per-unit assemblies | View-owned `GpuUnitModels`. `GpuUnitCamouflage` owns GPU camo resources; `UnitCamouflage` owns Swing-side pixel capture. These are different resource lifetimes. |
| Assemble family structure | `MekVisual`, `InfantryVisual`, `BattleArmorVisual`, `FamilyVisual` and `SquadronVisual`, using `UnitEquipmentAssembly`. Keep the working shared family handler; split only for substantial distinct behavior. |
| Pose a displayed entity | Per-unit `UnitAnimator` and `InfantryMotion` operate on its `GpuMeeple`/placed instance. Share immutable assets, never mutable transforms or materials between units. |
| Sequence events and completion holds | `UnitPlayback` owns event order and the one-second real-time hold. It must wait for the full movement/pose interval and use the same captured formation as the queued event. |
| Travel timing and sampled movement | `UnitMotion` owns route progress, ramps, boarding/gear intervals and troop jitter. Members sample that route; no independent root motion or member clock. |
| Resolved attacks and effects | `ResolvedAttack` supplies authorized outcomes; `UnitAttack` samples its clip; `GpuAttackEffects` and `GpuJumpJets` own bounded effects. Recoil and firing must consume the same resolved constituent binding identities. |
| Common transforms, fitting and bounds | Reuse `UnitModelAttachment`, `UnitModelMountArea`, `UnitBounds`, `UnitFootprint` and `UnitLandingSupports` in live and review rendering. |

Keep family handlers concerned with visual structure and animation. Do not subclass `Entity` to render it, and do not mirror the full game-unit inheritance tree in presentation classes.

### Assembly lifecycle

At map load, prepare only visible/resolvable units needed by that board. At first reveal, deployment, reinforcement or a relevant update, create or update that unit's assembly. Do not assume all entities exist at map start.

Use separate change categories:

- **Structure:** chosen body/override, configuration/conversion mode, actuator form, visual equipment identities/locations, living troop membership/count and composition. Reconcile the affected assembly or children; casualties must update the formation as the authoritative survivor state changes.
- **Appearance:** camo/tint, damage appearance and enabled equipment. Update materials/visibility; do not reload geometry. A casualty also changes structure as described above.
- **Pose:** movement, torso/turret facing, prone cause and animation time. Update transforms only.

Compare these immutable inputs on change; do not hash the whole unit or scan all equipment every render frame. Stable member slots survive casualty changes where possible. Save/load, reconnect and becoming visible snap to the known current state rather than replaying imagined past actions.

GPU assets are loaded once per asset/content key. Optional assembly-layout caching is limited to loadouts actually encountered in the current view; do not build or persist the cross-product of chassis and variants. Bound pending loads; discard stale results after a unit disappears or changes shape. Reference counts or a simple view-owned retain/release policy must have one owner, not both.

## 5. Asset and equipment contracts

### Minimal modular descriptor

Introduce a versioned descriptor for modular assets while retaining a temporary schema-1 loader. Keep G3DJ and libGDX's existing rigid nodes for the proof of concept. Do not switch formats or add a skeletal middleware dependency to obtain capabilities the current stack can provide.

| Record | Required content |
|---|---|
| Body | Mesh, family/configuration, rest dimensions, rig ID and node-role bindings; game-location tags; attachment areas/sockets; material roles; footprint reference dimensions. |
| Hardpoint | Stable ID, location and front/rear/side designation, parent node, local position/orientation, permitted visual roles, mounting area and art scale limits. Add explicit hand/wrist/elbow or turret sockets only where used. |
| Equipment module | Mesh/LOD key, mount origin, local axes, footprint bounds, material roles, optional recoil/aim nodes, emitter list and effect profile. |
| Emitter | Stable local ID, parent node, position and forward direction, role: muzzle, beam, launcher exit, exhaust, lamp or melee contact. Multiple barrels/exits are supported. |
| Landing support | Optional body `landingSupports`: stable `id`, deployment `node`, independent `shaft` and `foot`, rest shaft `length`, foot-local `contact` and authored `stowedOffset` inside the hull. Each support reaches its own ground contact; it is part of the body rig, not loadout equipment. Required for landable multi-hex Aero assets; building entities/mobile structures are excluded. |
| Equipment mapping | Canonical equipment internal ID to reusable visual/module parameters; explicit internal/container/embedded classifications. Chassis-specific visual overrides remain data. |
| Rig/clip | Joint roles, hierarchy, rest transforms and limits; named animation actions/tracks or a small family procedure; contact/door/boarding markers when needed. |
| Variant override | A body/hardpoint/rig override plus declared compatibility. An exceptional complete authored assembly must also declare its equipment bindings and compatibility fingerprint. |

Use a single coordinate contract: +Y forward, +Z up, documented mount origin and consistent model units. Keep authoring X/Y/Z transforms, rig tracks, sockets, normals and emitter axes consistent. Put the old Z/54 conversion in the legacy adapter; new modular data must not require scattered 54 multipliers. Preserve current visible proportions during conversion with comparison renders.

Bodies and modules use a common vertex layout and material feature set, including the same color/UV attributes. C0's draw-cost probe showed that inconsistent layouts introduce hundreds of avoidable shader switches; do not make each equipment type a new shader variant.

The pose transform order is fixed: **board placement and scale → unit root → family/stance pose → location/limb → hardpoint fit → equipment aim/recoil → emitter**. Camo sampling uses the corresponding stable rest-space mapping. Test this composition with a twisted, moving, scaled unit and a rear weapon before authoring the full library.

### Equipment inventory and finite reusable exports

Enumerate `EquipmentType.allTypes()` using MegaMek initialization, not just weapons found on the seven current chassis. Also sample real units from every family for mounting contexts, bay membership and intrinsic equipment. Keep canonical IDs and relevant flags; names and regexes are authoring conveniences, not the runtime identity. WeaponType coverage is the main priority: reuse the existing weapon recipes and shape variants before creating replacements.

Apply these user-defined type gates before mesh lookup or hardpoint allocation. Check the exclusions first because `ArmorType` and `StructureType` derive from `MiscType`:

| Equipment type | Visualization requirement |
|---|---|
| `StructureType`, `ArmorType`, `AmmoType` | Always excluded: no equipment mesh, hardpoint or emitter allocation. Ammo may still select an attack effect; it does not become a mounted visual. |
| `WeaponType` | Required visual representation, using authored meshes or appropriate weapon fallbacks. Logical bays/arrays resolve member weapons without a duplicate aggregate model. `INTERNAL_REPRESENTATION` is the documented exception: it represents an action rather than physical hardware, so the action supplies the animation/release origin and no dummy module is created. Actual bomb launchers remain eligible. |
| `MiscType` with `F_PHYSICAL_WEAPON` | Required physical-equipment visualization: hatchet, sword, claw, shield and other flagged equipment. `F_CLUB` alone is insufficient. Reuse authored shapes; any necessary fallback must represent physical equipment, never a gun. |
| Other `MiscType` | Only explicitly mapped items such as ECM, searchlights and selected existing extras are visualized. No generic fallback: unmapped items allocate nothing; a missing opted-in mesh is reported and omitted until supplied. |
| Other equipment types | No automatic attachment; record the type for review. |

These gates take precedence over broad art defaults and chassis overrides. A new armor or ammunition ID cannot become visible by accidentally matching a name rule. The misc allowlist is the set of explicit visual mappings, not a second list maintained elsewhere.

Every equipment type/context receives one explicit policy:

| Policy | Examples / treatment |
|---|---|
| External module | Energy/ballistic/missile weapons, physical weapons, and explicitly mapped misc such as jump jets, lamps and ECM/probe pods. |
| Embedded appearance/emitter | A flush gun port, internal launcher exit or integrated sensor; bind its weapon/effect without inventing a large external pod. |
| Container/aggregate | Weapon bays and logical grouping devices such as machine-gun arrays: bind their real member weapons without drawing the container and members twice. |
| No visualization | All StructureType/ArmorType/AmmoType items and unmapped optional misc. No geometry or hardpoint allocation. Never use this policy as a catch-all for an unclassified WeaponType or flagged physical weapon. |

Audit all flagged physical equipment and existing weapon art first. Review ECM/ECCM, probes, TAG/designators, C3 housings where appropriate, searchlights, manipulators, industrial tools and special BA mounts under the type gates above. Not every ECM installation has an external box; an explicit mapping can choose a small integrated representation. Optional misc without an authored mapping gets no placeholder mesh.

Searchlights have two physical sources: `MiscType.F_SEARCHLIGHT` equipment mounts, and external lamps described by the unit. Meks and vehicles automatically receive `Entity.hasExternalSearchlight()` for gameplay; that automatic flag alone must **not** create a lamp mesh. For those families, an external housing also requires the Searchlight design quirk. Read the design quirk independently of whether optional quirk effects are enabled. Other families retain explicitly added external lights. Presence and operability are separate: a destroyed mounted lamp may leave a dark housing; `isUsingSearchlight()` controls its visible light, and loss of the external flag removes its housing. An external lamp with no game location gets an authored chassis/family socket and a synthetic visual ID, never a made-up Mounted or critical slot. Remove baked lamps in the same checkpoint that binds these replacements, and check for duplicates.

Generate one module per **distinct visual recipe/size/detail combination**, shared by equivalent equipment types. A custom loadout is a list of references and transforms, not a new exported mesh. Ammo/mode changes can select different shot effects without replacing the barrel. Unknown weapons receive an appropriate generic module or embedded emitter and a precise diagnostic. This fallback does not apply to optional misc or excluded equipment.

`weapons.json` and the geometry builders remain the art source. Compile their known equipment mappings into normalized metadata so Java does not reimplement Python's regex/modifier logic. Keep the existing Mek catalog only for anatomy references, compatibility cases and regression sampling. Extend the existing Java normalization used by the catalog for live units instead of writing a second parser.

### Adding future equipment

Once eligible equipment is registered in MegaMek, adding its visual representation must be an **asset and mapping change**, without per-equipment renderer code. StructureType, ArmorType and AmmoType remain excluded:

1. Author/import a mesh that follows the module contract, or reuse an existing module. Supply its mount origin, bounds, material roles and applicable emitters/effect profile.
2. Map the equipment's canonical internal ID to that module in the shared equipment metadata. Existing authoring rules may assign a shared mesh broadly to a related equipment family; an explicit equipment mapping takes precedence over that broad default.
3. Validate and stage the assets, then reload through the normal asset lifecycle. Every compatible chassis and family fallback using that equipment, including custom loadouts, picks up the mapping automatically. No per-unit, per-variant or mekset assignment is required; intentional chassis/variant overrides remain supported.

Replacing that global mesh mapping updates its users in the same way. Keep unrecognized weapons on the documented weapon fallback until a mapping exists; optional misc stays unrepresented until explicitly mapped, with no misc fallback. This covers new equipment using the established mount, rig and effect contracts; new game mechanics still belong to MegaMek's rules, and genuinely new visual behavior extends the shared contract rather than adding item-specific branches.

### Placement, identity and overrides

Use `(entity ID, equipment number)` to bind an actual mounted item for the current entity revision; preserve canonical type, actual primary/secondary location, rear mounting, bay membership and actuator/turret context. A split weapon is one weapon with one appearance binding, not a mesh per critical slot. Refits that replace/reindex equipment invalidate these bindings.

Port collision-aware mounting to one Java implementation. First use explicit compatible sockets/bays, then deterministically pack within the authored area, with orientation and scale limits. Preserve limb-following barrels, leg/belt mounts, rear exits, actuator-dependent hands and launcher bank shape. Critical-slot positions alone are not physical hardpoint coordinates.

When an area is full, use the authored compact/embedded alternative; never move a weapon to a different game location, cover a muzzle, or silently overlap/drop it. Expose unresolved placements in the review tool. The fallback body also supplies attachment areas and emitter anchors, so custom loadouts retain weapon effects even without bespoke chassis art.

Resolution order:

1. Compatible explicit variant design from the existing mekset model override.
2. Chassis body and its hardpoints, assembled with the **current** loadout.
3. Family/configuration/size fallback, assembled with the current loadout.
4. Safe family proxy, then the existing sprite path if assets cannot be loaded.

A variant override normally changes the body, sockets or cosmetics and still assembles its equipment. A deliberately complete authored assembly is an explicit exception: validate all integral weapon/emitter bindings, attach only declared dynamic slots, and use it only when its compatibility rule/fingerprint matches. A custom refit retaining a stock name must not keep stale guns or receive duplicate guns.

## 6. Family coverage and rigs

Each row must have a loadable fallback, applicable hardpoints/emitters, material roles, valid bounds and basic animation behavior before the proof of concept is called complete. Non-Mek families may share geometry across sizes; Mek fallbacks use the five authored weight-class bodies specified below.

| Family / forms | Minimum fallback and rig behavior |
|---|---|
| Conventional infantry | Preserve standing/aiming/kneeling/advancing looks, jump packs and motorized/tracked/wheeled/hover transport meshes. Each figure/vehicle is an independent child with a stable member ID. |
| Battle Armor | Existing compact armored figures, their own proportions, articulated limbs and relevant weapon/exhaust bindings. Dedicated family compression switch defaults to `false`: one figure per living trooper. No conventional-infantry boarding sequence. |
| Meks | Biped, tripod and quad; pelvis, upper torso, head, location-tagged arms/legs, knees/feet and attachment nodes. Support armless and industrial appearances. |
| ProtoMeks | Small distinct bodies; reuse suitable limb mechanics with an explicit role map, including applicable quad anatomy. No gameplay torso-twist or prone controller. |
| Ground vehicles | Tracked, wheeled, hover, WiGE, rail/maglev; combat/support/superheavy/large support variants. Body, optional one/two turrets, barrel recoil and wheel/track/hover motion. |
| VTOL / airship | Combat/support rotorcraft and airships, rotor/propulsor nodes, landing gear, body banking/idle hover. |
| Fighters | Aerospace, conventional and fixed-wing support; flight/landed poses, engines and firing arcs. Fighter squadrons compose shared aircraft children from actual member information. |
| Small craft / DropShips | Distinct spheroid and aerodyne fallbacks; independently extending landing supports, engines, bay/arc emitters; landed and airborne footprints. Multi-hex supports contact uneven ground only at relative elevation 0, with no protruding gear in flight. Union-sized seven-hex fixture is mandatory. |
| JumpShips / WarShips / stations | Distinct capital-ship/station silhouettes and appropriate thruster/bay emitters, including space-board behavior; stations do not receive walk/run clips. |
| Water units | Naval, hydrofoil and submarine bodies; turret/propulsor nodes, waterline/depth-aware placement and restrained surface motion. |
| Conversion units | LAM ground/AirMek/fighter states and QuadVee Mek/vehicle states, selected from the existing conversion state. Share equipment identity across forms; no invented conversion legality. |
| Static / exceptional entities | Gun emplacements, building entities/mobile structures, handheld-weapon entities, ejected crews/MekWarriors, escape pods, telemissiles and Battlefield Support Assets: reuse the closest valid family with an explicit mapping or a distinct small proxy. Cover `NONE` and unknown future types safely. |

Run an inventory against concrete entity classes/type flags and movement modes; inheritance must not cause a DropShip to become a generic fighter, BA to become conventional infantry, or a turreted vehicle to become a Mek. Marker/support assets retain their existing marker semantics where those are the intended presentation. Off-board or non-visible entities are not instantiated merely to satisfy coverage.

### Mek weight-class bodies

Named Meks and fallbacks follow the same authored scale standard. Export distinct **light, medium, heavy,
assault and superheavy** bodies for biped, tripod and quad layouts; the reusable hybrid air-Mek has the same
five classes. Bake proportions into geometry, joints and hardpoints. Do not resize one fallback body at runtime.

Use `Entity.getWeightClass()` and `Mek.isSuperHeavy()` for selection; the latter currently means weight above
100 t. Ultra-light uses the light fallback. Default mekset paths resolve `{weightClass}` before loading.
The body remains subject to common BoardGeometry and neutral per-family fine-tuning only. Custom/named mappings
still win over defaults. The former shared fallback bodies are archived under `references/superseded-fallbacks/`.

The class proportion briefs, authoring ranges and reproducible recipes live in
[MODELLING_GUIDE.md](MODELLING_GUIDE.md#2-coordinates-scale-and-proportions), the single authoring specification.
Alpha Strike size queries remain useful for other families; they no longer enlarge/shrink Mek fallback meshes.

### Rigid rigs first

Rigid node animation matches this flat-shaded art: body pieces keep their shape, and limbs/doors/turrets rotate around pivots. Standardize joint roles and rest poses per family, with a mapping from authored node names to those roles. Preserve location ownership independently of joint naming so damage reaches attached modules correctly.

Reuse clip logic by topology and proportions, rather than copying animation files for each chassis. Give biped, quad and tripod locomotion appropriate leg phasing. Infantry/BA retain their recognizable pose silhouettes while their source geometry is assigned to articulated parts. Weighted skinning, physics ragdolls and a general retargeting system are deferred unless a concrete reviewed asset needs them.

## 7. Pose, movement, firing and destruction

### Persistent prone cause — user-requested refinement

Add a small `ProneCause` field to `Entity`, used for Mek presentation, with `NONE`, `VOLUNTARY`, `FORCED` and `UNKNOWN` states. `VOLUNTARY` includes player and AI orders. Keep `isProne()` authoritative; cause must not change movement costs, modifiers, legal actions or damage.

- Intentional `GO_PRONE` resolution sets `VOLUNTARY`; actual fall resolution sets `FORCED`, including failed checks, failed standing/jumps and applicable combat falls. An actual fall wins over an earlier intention to lie down.
- Standing up clears cause. `setHullDown(true)` currently clears the prone boolean directly and must clear cause too; audit all posture setters/direct writes, not only `setProne()` callers.
- Provide an explicit cause-setting path while preserving existing callers safely. An unclassified new prone transition becomes `UNKNOWN`; repeated legacy writes must not erase a known cause without a real new transition.
- Persist/replicate the field through the existing entity save/network mechanisms; verify both rather than assuming adding a Java field covers every format. Older saves/peers without a cause resolve to `UNKNOWN` when prone and `NONE` when standing.
- On a **new visible transition**, voluntary prone lowers into a compact crouch/kneel (quad/tripod equivalent); forced prone uses an authored fall/ground pose. Unknown cause uses a neutral prone pose without an invented accident.
- Loading or revealing an already-prone unit applies the resting pose directly. It must not replay the fall merely because the unit entered the render cache. Saving stores cause/state, not animation progress.

Current source touchpoints include `Entity.setProne`, `Entity.setHullDown`, `MovePathHandler`'s `GO_PRONE` paths and `TWGameManager` fall resolution. The swarmer-displacement branch must follow the actual resolved action. Keep `HULL_DOWN` distinct from the requested voluntary-prone visual.

Persistent cause selects the resting pose; it does not record a fall followed by recovery within one received movement path. Reuse existing resolved movement events for transition order. If those events omit the necessary posture, add sparse posture/cause cues tied to existing waypoints through the same event/snapshot boundary. A final Entity snapshot must not make a Mek fall at the start of a path when the fall occurred at its end. These cues are presentation history, not another movement simulation or saved animation clock.

### Shared playback and transform layers

Use one time source and the existing playback-speed/skip controls for travel, limbs, embarkation, weapon effects and idle wobble. Evaluate poses from rest transforms plus current animation parameters; avoid cumulative transform drift. Family capabilities select applicable actions, not a universal clip list blindly applied to every type.

Use distance and the captured game movement capability to determine travel time, with bounded speed influence.
Normal playback advances at half the old clock rate; 2x restores the old clock. Accelerate/brake once per continuous
travel block. Gait and wheel rotation follow actual displayed distance and model scale. Complete movement and
attack recovery before a named one-second real-time hold; Instant skips both. See [playback specification and
verification](MODULAR_MODELS_PLAYBACK.md).

Foot and jump formations stagger individual departures by a small deterministic interval. Delayed members keep
the same travel speed and get their own landing time, pose, exhaust and outward settling. The group finishes only
after the last member; its path, picking/labels and event order still use the shared unit timeline. Changing the
camera or frame rate must not reroll these delays. Transported soldiers retain the boarding/parking/unloading order.

| Action | Required behavior |
|---|---|
| Standby | Breathing/weight shifts for troops, restrained Mek idle, rotor/engine/hover behavior where appropriate. Move existing airborne wobble into this layer exactly once. |
| Walk / run | Use actual movement type and path playback speed; sync step/wheel/track cycles to displayed distance. Reverse/turning movement and interrupted paths remain coherent. |
| Jump | Existing path/arc remains authoritative; add anticipation, airborne limb pose, exhaust and landing recovery. Blue flame stays strong through the actual apex, then tapers on descent. World-space smoke expands/dissipates, reducing progressively from takeoff to none at landing. Effects use authored, posed nozzles and the same playback clock; skip/hidden/destroyed sources clear them. Include get-up/landing recovery so clips have a route back to idle. |
| Shoot | Aim the permitted joint/weapon within visual limits, then recoil/emission; preserve the unit's actual firing arc and gameplay facing. |
| Physical attack | Meks only: push, kick, punch and physical-weapon attacks, with anticipation, contact/miss and recovery. Select the actual attacking arm/leg or mounted weapon; punches/kicks/pushes need no fabricated equipment entry. |
| Torso twist | Meks only, preserving the existing CT behavior and appropriate upper/lower-body separation. Equipment and muzzles follow the posed torso/limb. |
| Prone / get up | Meks only, driven by state plus `ProneCause`; visible low pose must fit its occupied-height presentation without rescaling the skeleton from current `height()`. |
| Hit / location loss | Brief optional reaction; existing lost/wrecked locations remain correct. An attached weapon disappears or burns with its actual parent/location, and disabled muzzles cannot keep firing. |
| Destruction / death | Authored fall/collapse, wreck, crash or troop death per family; emit only when visible information permits it. Maintain wrecks only when game/client state supports displaying them. |
| Conversion / landing | Applicable LAM/QuadVee and aircraft states; begin with correct state poses, then require a basic transition before declaring that family animated. |

Layer locomotion with aim/recoil where compatible; forced falls, death and conversion take precedence over incompatible lower-priority clips. Bound transient actions and effects. Skip, pause/resume, save/load, rapid new orders, removal and hidden-state transitions must leave the same final placement and pose as normal playback.

Physical attacks use the existing resolved action identity (`PushAttackAction`, `KickAttackAction`, `PunchAttackAction`, `ClubAttackAction` and applicable Mek variants), including side/limb, weapon binding and visible target/outcome. Bind contact markers to hands, feet or the physical weapon; synchronize target reactions with confirmed outcomes. A push animation must not displace a target unless the game reports displacement. Missing/destroyed limbs, weapon shapes, misses and interruption must recover to valid poses. Physical-attack animation is explicitly Mek-only; other families retain their existing rules and do not receive these clips.

### Troop counts and casualties

Capture current surviving personnel from Entity into the immutable snapshot on each relevant update. Conventional infantry uses the existing active-trooper count; BA uses the actual living trooper locations, excluding the squad/body location. Damage reduces the visible group when the rules report casualties, not by estimating a percentage from remaining armor. A living BA trooper with damaged armor or a disabled weapon still gets a figure.

- **Battle Armor:** add a simple family-owned `BattleArmorVisual.COMPRESS_TROOPS` switch, default **`false`**. With compression disabled, visible figures equal living troopers, with no old four-figure cap. Six alive means six figures; five alive means five; six originally with five dead means one; none alive means no living figures. Use the actual supported troop count rather than hardcoding six as a maximum.
- **Optional BA compression:** when the switch is `true`, use the existing shared `min(4, ceil(sqrt(alive)))` rule. Keep the switch in the BA family handler; do not add a separate settings framework or change conventional infantry's policy with it.
- **Conventional infantry:** retain `min(6, ceil(sqrt(activeTroopers)))`, recalculated from current survivors. For example, 28 alive gives six slots, 16 gives four, one gives one and zero gives none. Compression means an individual casualty need not always remove a displayed figure.

With BA compression disabled, use stable trooper IDs so the figure belonging to a dead trooper is removed and survivors keep their poses/slots. Compressed slots remain representative and should also avoid unnecessary reshuffling. A bounded death animation may finish, but its dying child no longer counts as a living member. Reload, reinforcement, casualty updates and animation skipping must all produce the same current living group. Both families reuse the same formation helpers and shared mesh assets; changing a count does not generate a new group asset.

### Infantry headings and arrival

Conventional infantry and Battle Armor do not inherit a gameplay-facing restriction. Each soldier can watch any direction, independently of its neighbors. Heading is presentation state on the child, not a write to `Entity` facing, firing arcs, movement legality or the classic sprite system. The formation root follows the displayed path without forcing every child to share an incidental facing value.

At deployment/reveal/load, choose stable headings from each member's position relative to the hex center, with small deterministic angle variations seeded by unit ID, member/slot ID and destination coordinates. Most soldiers face outward, covering the perimeter; an occasional inward-facing member is allowed. On a visible move, choose the destination headings once and ease into them as the troops finish moving. Keep them unchanged until another arrival; updates, casualties, camera switching and frame rate must not reroll them. Preserve surviving member IDs and the current count/compression rules.

Troops face along their local walking approach, decelerate, then turn by the shortest angular route into their resting/aiming pose with small deterministic timing offsets. Include the necessary standing/kneeling transition and foot placement; do not rotate the whole formation abruptly at the end or make a planted figure slide sideways. Use the shared animation clock and bounded arrival interval. Jump troops settle after landing. BA follows this individual-troop behavior, without conventional-infantry boarding.

Vehicles use route-dependent orientation rather than arbitrary all-angle soldier facing. Derive travel heading from the actual approach/path tangent and forward/reverse movement. Distinct parking directions, including one vehicle facing left and another forward, are allowed when their local approach can reach them naturally. Wheeled vehicles steer through short arcs; tracked vehicles may pivot as part of their stop; hover vehicles can drift appropriately. No sideways wheeled motion or instant 90-degree parking snaps. Keep all final 2× vehicle footprints and soldier slots inside the hex and clear of one another; no new navigation or gameplay movement solver is needed.

### Infantry with vehicles

Use the current conventional-infantry slot count above. Conventional transport compositions remain 0 → empty; 1–4 slots → one vehicle plus remaining troops; 5–6 slots → two vehicles plus remaining troops. Thus 3 = 1+2, 4 = 1+3, 5 = 2+3 and 6 = 2+4. Reconcile vehicles and figures when casualties change that slot count. Jump infantry adds packs and keeps troop slots. Cosmetic pose choice never changes survivor counts; BA does not use this transport composition rule.

For **motorized and mechanized conventional infantry only**:

1. Assign each visible troop a transport and an authored boarding point; vary offsets/headings deterministically within the hex.
2. At travel start, troops approach their assigned vehicle locally; hide them as they board. Do not create transport-capacity rules or write to the game's transport system.
3. Vehicles align with and follow the existing unit path; troop children remain logically attached/hidden during travel. Their local parking approach preserves the direction they came from and ends in distinct, reachable headings.
4. Finish vehicle translation, braking and parking rotation first. A stopped group root alone is insufficient: the vehicle itself must have finished moving and turning before its passengers unload.
5. Only after the vehicles have stopped, troops emerge at the stopped vehicles' exit markers, walk to their destination slots and ease into their varied final headings/poses. Vehicles remain stationary throughout disembarkation.

Use a short bounded approach/boarding → driving/parking → full stop → disembarking/settling sequence under the same playback clock. Add fixed group-level boarding/unloading intervals to travel time; never shorten driving to fit them or add seconds per soldier. Game processing continues while the presentation queue plays. Mid-sequence casualties, destruction, removal or a changed composition must cancel/reconcile children safely. Skipping snaps directly to the correct final group/headings. Animation is presentation only: this infantry does not become a separate passenger entity.

Keep path sampling in `UnitMotion`: hold the displayed group root at departure during boarding, sample the existing path during the driving interval, then hold it at arrival during disembarking. The infantry handler controls child offsets and visibility; it must not implement a second path interpolator. Picking, labels, shadows and terrain support use that same displayed root.

### Weapon emission and attack information

Bind emitters to actual eligible equipment numbers, including bay-member weapons, multiple barrels, rear mounts, AMS and physical weapons. AmmoType items never allocate their own hardpoints; bomb/munition effects use the resolved attack's valid weapon or release anchor. Evaluate the final emitter transform after all parent animation, fitting, camo-independent scaling and recoil; do not derive a muzzle from the unit center or from a screenshot.

Start with beam/laser, ballistic bullet/shell, single missile and missile-salvo/cluster profiles. Also classify PPC/plasma pulses, flame streams, artillery arcs, bombs, TAG/searchlight beams, exhaust and melee contact so they do not all masquerade as lasers. Ammo/mode can change the effect profile. Missile weapons launch `rackSize` visible low-poly missiles; `F_LARGE_MISSILE` launches one (its caliber/rack value is not a count). Do not reduce an LRM-20 to a representative handful of projectiles. Batch bodies and bound smoke density separately from missile count.

Missile cluster results must carry the actual resolved **missile hits**, captured before converting them into damage points or damage clusters. An LRM-20 with twelve cluster hits launches twenty: twelve approach the target and eight visibly miss. Miss paths, including beams and ballistic shots, clear the posed target bounds even for large craft. Never reroll the cluster table in presentation. Indirect missiles use an arc; each smoke trail samples that same flight path. Where aerospace attack-value rules do not resolve individual missiles, keep the count explicitly unknown rather than inventing a cluster result. Logical-group totals may be distributed cosmetically across their captured physical launchers while preserving the total; actual per-mount results take priority.

Adjacent resolved shots from the same unit/pose form one volley with configurable launch jitter (`UnitPlayback.VOLLEY_JITTER_SECONDS`). Apply the shared one-second completion hold once, after the last shot recovers; movement, conversion, another firing unit and physical actions remain queue boundaries. Preserve the captured appearance until the volley reaches its last impact, accept late packets without truncating their animation, and retain Pause/Instant behavior. Per-missile launch jitter has its own constant. Initial implementation and native/packet evidence are in [the broad checkpoint update](MODULAR_MODELS_C6_C9.md).

Audit the existing attack/action/report path for a structured, visibility-safe **fired/resolved** event carrying attacker, equipment/member IDs, target/endpoint and outcome information available to that client. Reuse it; if missing, add the smallest typed presentation payload to the existing event/packet path. Do not parse localized report text or fire animations whenever a firing-order overlay changes. Never fabricate hit/damage outcomes or expose hidden attackers/targets through effects or cache loading.

Keep muzzle flash, projectile/beam, impact, recoil and optional sound on the same event timeline with deduplication. Support indirect fire, strafing, bay volleys, misses, target removal and attacks at hexes/buildings. Basic synchronized sound hooks, selection feedback and effect intensity controls belong here; new cinematic camera systems do not.

Capture the minimum authorized appearance/binding revision and pose needed by queued shots or death events before an entity or mount is removed. An already-confirmed shot can finish after its source is destroyed; a later refit must not redirect it to a newly indexed weapon. Retain only the visible event data/shared asset references needed until playback ends, with bounded lifetime and cleanup. Do not fetch hidden current state to reconstruct an old event.

## 8. Camouflage, scale, footprint and terrain

### Camouflage

Use `Entity.getCamouflageOrElseOwners()` and the existing force/owner fallback chain; capture immutable image/parameters after visibility checks. Support `Camouflage` image versus solid-color modes, `getRotationRadians()`, `getScaleFactor()` and missing-file fallback. Respect applicable Battlefield Support marker overlays rather than accidentally recoloring their identity away.

For the proof of concept, author stable UVs for paint surfaces using a simple box-projection convention in rest space; allow authored UV overrides for important designs. Reuse the existing texture/material path where possible. Avoid world-space projection that makes camouflage slide as a unit moves or twists. A triplanar shader is a later option only if UV quality demonstrably needs it.

Paint and fixed-detail surfaces remain separate: rubber, metal, cockpit glass, lenses and emitters do not inherit the camo pattern. Chassis and equipment use consistent pattern density and per-unit orientation/scale. Cache image textures by content and sampler configuration; share pixels across units without sharing mutable per-unit material state. Verify camo in lit, shadow, see-through and damaged rendering passes. Do not retain the sprite's baked lighting/shadow overlay on top of real 3D lighting.

### Nominal dimensions and multi-hex units

- Keep normal unit scale controlled by `BoardGeometry` and Tuning. Use a separate **multi-hex unit scale of 0.85**, with its dedicated default constant and slider. This replaces the normal scale for a large assembly; do not multiply both scales or shrink each tile section independently. Neutral per-family `UNIT_SCALE`/`HEIGHT_SCALE` multiply the selected board tuning.
- A multi-hex asset is authored against its full footprint dimensions. Scaling a one-hex proxy by 0.85 will not make it a seven-hex craft. Never normalize all bodies to a single-hex bounding box during loading.
- Represent one authored multi-hex unit by one visual assembly with the real occupied coordinates and one authoritative anchor. Secondary positions remain game footprint/selection data, not seven duplicate complete meshes. Legacy multi-part sprites remain a supported fallback until their whole-unit path is replaced safely.
- For grounded multi-hex units, choose the **highest occupied support level** as the common base. Use the existing terrain/elevation/bridge or support-surface interpretation; do not double-add relative elevation or treat a building roof as solid ground unless the unit actually rests there. Submarine waterlines/depth and flying altitude use their own existing placement semantics, not the grounded maximum.
- Re-evaluate the occupied support set when terrain, position, facing, conversion mode or landed/airborne state changes. During movement, use the same support policy for the visible swept footprint; do not drag a large hull through a higher occupied hex. This corrects visual clearance, not movement legality.
- Use stable rest dimensions/family appearance scale for the skeleton. `Entity.height()` remains correct for rules/LOS and snapshot occupancy, but no longer drives a posed model's changing body scale. Superheavy appearance size and multilevel occupancy are separate concerns.
- Bounds used for culling, shadows, labels and picking must include posed limbs/modules and the whole footprint. Pick any occupied part as the same entity, preserve the game's hex targeting and handle unit stacks. Use the same geometry in top and isometric views.

Mandatory fixture: a Union-style seven-hex craft over unequal levels, then takeoff/landing and rotation, alongside a single-hex unit. At default scales it must visibly span its intended footprint, stand on the highest support and receive only one identity/selection/animation state. Also test an elongated multi-hex hull, map edge, water, bridge/support and altered hex scale.

### Landed multi-hex Aero supports — C4 addendum

This extends the verified highest-support placement; [implementation evidence](MODULAR_MODELS_C4_SUPPORTS.md).
It applies to multi-hex Aero
units and their future named/variant/fallback bodies, such as DropShips and other landable spacecraft. Building
entities/mobile structures use their own placement rules and are explicitly excluded. Do not enable this for
every large unit merely because its footprint has several hexes, or invent a landing state for a space-only craft.

- **Grounded eligibility:** deploy supports only at the unit's actual terrain-relative elevation **0** and when
  the existing client/game altitude/airborne state says it is landed. Positive elevation, airborne Aero altitude
  (including its elevation sentinel) and space flight show **no protruding support legs/struts**. Use the existing
  state bridge to capture the needed relative-elevation/landed observation; do not infer it from the rendered
  waypoint height, the hull's world Z, or an aircraft movement-mode name. An elevation-0 craft over level-1 terrain
  is still landed. Other families' elevation, waterline, roof and bridge rules remain with their existing logic.
- **Hull clearance:** keep the hull at the highest valid occupied support level, with its authored ground
  clearance. Do not lower or tilt the hull into higher terrain to reach the lower hexes. Extend supports instead;
  extension is cosmetic and never changes occupancy, movement legality, elevation, `height()` or LOS rules.
- **Independent contacts:** transform each authored foot/contact point through the unit's facing, footprint fit
  and the live multi-hex scale (default **0.85**). Sample the existing valid ground/support surface below that
  actual world X/Y. Extend that support to the sampled height; another foot over a higher hex needs less or no
  extra extension. Do not give every leg the lowest occupied height or assign one invented leg per occupied hex.
- **Simple rig:** prefer a rigid upper support/deployment joint, a telescoping lower shaft and an unscaled foot.
  Apply only the required extra downward reach, converted from world distance into the support's local frame.
  Preserve shaft thickness, foot size and hull proportions. Reuse rest transforms and the existing surface query;
  no general terrain IK, physics simulation, balance solver or second terrain-height implementation is needed.
- **Ground-only lifecycle:** fully stow the support geometry and clear ground extensions before flying travel;
  an 85-degree rotation that leaves struts sticking out is insufficient. Deployment/retraction uses the shared
  landing/takeoff timeline: visibly slide supports into the hull before liftoff
  and begin deployment only in the landed elevation-0 phase. Use the displayed phase's state observation, not a
  future landed snapshot while the unit is still flying along its path. Loading/revealing or skipping to a state
  applies its correct support pose immediately. Re-evaluate contacts after terrain, position, facing, scale or
  landed-state changes; do not preserve stale leg lengths after taking off and landing elsewhere.
  The authored stowed pose must fully enclose the pads, shafts and braces inside the opaque hull before hiding
  their parts. Preserve the grounded fitting footprint during support motion. Takeoff/landing updates without
  a path still use the same timeline; add fixed support phases without shortening the intervening travel.
- **Shared rendering:** evaluate hull placement, family pose and support contacts before final bounds, picking,
  shadows and drawing. Both camera views use the same resulting geometry. Extended legs belong in posed bounds
  but must never feed back into hull height or the stable rest dimensions used to fit the unit to its footprint.
  Off-board/missing or unsupported surfaces must not produce non-finite or indefinitely extending struts. Reuse
  the existing surface validity rules for water, bridges and roofs; this feature does not grant new landing rights.

Required example: a landed seven-hex Union occupies one level-1 hex and six level-0 hexes. Keep its hull at the
level-1 support height. Every authored foot above level 0 extends **one terrain level farther than its flat-ground
pose**, while any foot above level 1 keeps its normal reach. At positive elevation/in flight, no legs reach toward
the board. Asset requirements and the authoring review checklist are in
[MODELLING_GUIDE.md §7](MODELLING_GUIDE.md#7-multi-hex-aero-landing-supports).

## 9. Performance and content reliability

The modular design solves asset duplication, not automatically draw cost. A 900-triangle unit with many materials/children can still be expensive.

- Aim below **1,000 triangles for the bare unit before loadout**. **Conventional infantry and Battle Armor always qualify for an exception to this target:** multiple figure/transport meshes make up one effective game unit, so exceeding 1,000 in the combined formation needs no separate exception approval. Other families need art review for base counts from 1,000 through 1,500. Enforce **1,500 as the bare-unit hard cap for all families** in authoring/import/base assembly. For infantry, the base formation comprises its figures/transports; added loadout modules are separate. Count repeated base mesh instances, and measure both stored and rendered geometry. Do not apply the body cap to individual equipment modules or to a complete chassis-plus-loadout total.
- Preserve the 214-triangle BA components and unchanged conventional figures/transports; six BA use 1,284 triangles under the standing infantry exception. Do not remove recognizable infantry details, enable compression or drop living figures solely to fit the target. Profile complete formations before further optimization. Record counts and visual review outcomes for future artwork; no generic runtime approval framework is needed.
- A body above 1,500 requires redesigned base artwork or a valid family fallback and a diagnostic. A valid body may exceed 1,500 in total after equipment is attached; this is not grounds to reject the body, drop weapons or strip its detail. Keep equipment low-poly and report its cost alongside the body and total; do not invent a numeric equipment cap from the body specification. Dense loadouts and capital ships need complete-instance profiling. Equipment-only distance detail follows the reviewed projected-size policy; do not replace the body mesh.
- Track draw calls/material switches, resident geometry/textures, assembly time, GC/allocation and CPU/GPU frame time as well as triangles. Avoid geometry uploads, model loading and allocation loops during normal pose updates.
- Start with shared mesh instances and ModelBatch. Measure before adding hardware instancing or merging. Any later batching is per compatible material/joint; it must not destroy troop/limb independence or emitter bindings.
- Use frustum/visibility culling, bounded effects and animation update reduction for distant/offscreen units. Use the measured equipment-only LoD policy above; retain body geometry and shared animation state. Avoid shader/asset variant explosions.
- Benchmark representative 64-unit, 256-unit and large stress encounters with infantry, repeated and unique loadouts, large craft, camo and simultaneous effects. Record actual hardware/resolution, median/p95/p99 frame times, load/assembly time and resident memory. Establish practical targets from the baseline in checkpoint 0; do not claim universal frame rates.
- Check licenses/reference provenance, deterministic hashes, absent/broken assets, path containment, schema errors, missing nodes, degenerate geometry, emitter direction, UVs and shared-resource cleanup. Keep a generic/sprite recovery path and actionable diagnostics.

## 10. Checkpoints and acceptance gates

Execute in dependency order. Each checkpoint is a small deliverable or several focused changes; it is not a single giant commit. Do not start a new checkpoint to avoid a failed gate.

### Review protocol applied at every checkpoint

Before checking a checkpoint off, record its changed files, tests, review images/video, measured results where relevant, remaining limitations and fixes from review in a short completion note under that checkpoint.

Review must answer: Are rules/state still owned by existing game code? Is there one implementation of shared behavior? Are caches/resources owned and released exactly once? Are transforms and event ordering correct under updates? Do both camera views, visibility, damage and fallbacks still work? Can an abstraction or duplicated code path be removed? Fix findings, then rerun only affected checks. Reversible visual edits need review renders, not tests that merely restate constants.

### Required fixes from the 2026-09-20 implementation review

These are concrete follow-up defects, not new architecture work. Details, source locations and reproductions are
in [the review](MODULAR_MODELS_REVIEW.md). Close these before C6–C8 sign-off; C0–C5 evidence remains historical.

- [x] R1 — Exclude generated aerospace weapon-group mounts from physical geometry while retaining their logical firing membership. Verify one real gun plus one rules group renders one gun, including disabled/empty groups.
- [x] R2 — Resolve squadron/group firing to actual member and mounted equipment identities once. Recoil and effects must use that same result. Verify a mixed squadron with different equipment ordering.
- [x] R3 — Include final prone/get-up and arrival settling in movement completion; start the one-second hold afterward. Verify a terminal fall followed by another event at every speed, including half speed and Instant.
- [x] R4 — Derive boarding from the queued event's captured formation instead of the latest scene's unit ID lookup. Verify queued movement across casualties/composition changes and consecutive moves.
- [x] R5 — Recoil opposite the authored barrel direction in the correct parent space. Verify front, rear and rotated mounts, including a twisted torso.

All five corrections and the queued-transport completion follow-through have
[recorded tests and native review evidence](MODULAR_MODELS_REVIEW_FIXES.md). Broader family/terrain/attack gates below remain independent.

### C0 — Freeze the baseline and inventory

- [x] Record current working rendering, data/build commands, references and benchmark hardware/scenarios. Validate inputs against the actual current exporter; never mask a stale catalog by changing only its hash.
- [x] Produce exhaustive equipment classification and concrete entity-family/configuration coverage lists from MegaMek, including intrinsic equipment and exceptions. Verify hard exclusions, WeaponType recipe/fallback coverage, F_PHYSICAL_WEAPON coverage and explicit optional-misc mappings without fallback.
- [x] Verify client/server/save routes for prone cause, movement posture cues and structured firing/physical-attack outcomes. Confirm what data is visible to each client and when.
- [x] Review the contracts and one dense-loadout draw-call prototype before committing to asset layout.

**Gate:** inventory has no unclassified family/equipment entry, baseline is reproducible, and necessary state/event changes are bounded and named. Required weapon fallback and optional-misc omission are explicit; excluded types allocate nothing.

Completed 2026-09-19. [C0 evidence](MODULAR_MODELS_C0.md) records the reproducible baseline, integrated inventory, native review, draw probe and issues carried forward.

### C1 — Contracts, shared assets and state bridge

- [x] Add the modular descriptor/rig/emitter contracts and validators alongside schema 1. Build one chassis, one articulated troop and representative gun/launcher/lamp modules.
- [x] Add immutable structure/appearance/pose snapshots, stable mount/member identity and a small shared equipment normalization path.
- [x] Implement `ProneCause` in Entity and authoritative state transitions, including `setHullDown`, saved/replicated state and old-data defaults.
- [x] Prove shared asset/per-instance state ownership and a transformed emitter through a parent limb. Retain the existing switch and legacy rendering path.

**Gate:** player/AI deliberate prone, a forced fall, get-up/hull-down, legacy unknown data and multiplayer/save round trips give correct causes without any rule changes. Two identical units can twist, damage and recolor independently. Invalid descriptors fail safely.

Completed 2026-09-19. [C1 evidence and schema contract](MODULAR_MODELS_C1.md) records 114 focused tests, native transform/material/damage review, five independent assets and unchanged geometry hashes for all 261 legacy meshes. Runtime assembly and animation playback remain open below.

### C2 — Runtime infantry assembly

- [x] Assemble separate conventional/BA figures and transport children using the family count policies above, troop poses and movement type. Add `BattleArmorVisual.COMPRESS_TROOPS = false`, with optional compression through the shared helper. Keep all current silhouettes and the 2× vehicle dimensions.
- [x] Move slot layout/headings into the one runtime assembler, including stable variation, current survivor counts/BA identities and zero strength. Reconcile casualty changes without retaining dead members or reshuffling every survivor. Python exports component meshes only.
- [x] Make the runtime assembler produce review scene data so Blender/native previews consume the same placements as the game.
- [x] Bake the requested height changes into component meshes: conventional troops/transports +10%, Battle Armor +50%, preserving detail and matching joints/emitters. Keep per-family `UnitFamilyScale.UNIT_SCALE` and `HEIGHT_SCALE` neutral at `1.0f`, multiplying the shared board tuning for later visual adjustments.
- [x] Fit infantry positions using the final board/family scale. Preserve requested mesh sizes: reposition where practical, keep parked vehicles apart and troopers clear of them, and allow crowded formations to bleed outside the hex. Keep captured parking positions stable through unloading/casualty updates. [Height and layout evidence](MODULAR_MODELS_C2.md).

**Gate:** 0–6 conventional slots resolve correctly from current survivors. BA defaults to uncompressed: test 0–6 living troopers, especially six alive → five dead → one remaining → zero, with the correct member removed each time. Enabling BA compression restores the shared compressed rule (five alive → three figures) without changing infantry. Armor damage without a casualty does not remove a BA figure. Motorized/mechanized 3/4/5/6 counts match 1+2, 1+3, 2+3, 2+4; casualty-driven slot changes reconcile transports too. Jump packs work; vehicles differ in headings/positions; groups meet the triangle budget, including six BA figures. Fit inside the hex where space permits; oversized formations may bleed beyond it without shrinking members. Casualties do not reshuffle every survivor. The initial gate covers assembly; the later scale/layout addendum also checks boarding playback.

### C3 — Runtime Mek loadouts and equipment library

Previous gate: [C2 evidence](MODULAR_MODELS_C2.md) records runtime infantry, full-detail 1,284-triangle six-member BA groups, scale-aware placement, shared resources, review views and retained compatibility files.

- [x] Export bare articulated bodies, optional actuator-dependent anatomy and local hardpoint areas; export/normalize reusable equipment and all emitter profiles.
- [x] Apply shared type gates before attachment allocation. Reuse existing WeaponType shapes and fallbacks, cover all F_PHYSICAL_WEAPON misc, and only attach explicitly mapped other misc without fallback. StructureType/ArmorType/AmmoType must never reserve hardpoints.
- [x] Implement one runtime fitter and equip actual mounted items, including split/rear/bay/integrated items, dense loadouts and fallback bodies. Preserve torso twist and location damage.
- [x] Move Warhammer/Mackie lamps to dynamic mounted/external searchlight bindings. Test presence, active state, destruction and no duplicates.
- [x] Support compatible dedicated variant designs and exact/fallback precedence. Remove the shipped per-variant requirement after comparing old stock appearances.
- [x] Prove the future-equipment workflow: add a previously unmapped equipment ID, assign a new or shared mesh globally, then replace that mapping. Verify stock/custom loadouts and compatible family fallbacks update without renderer changes or per-variant generation.

**Gate:** stock Warhammer and Mad Cat, an uncatalogued custom refit, same-name altered equipment, duplicate weapons, rear launchers, all arm actuator forms, physical weapons, ECM and unknown modules work without a Blender rebuild. One emitter binding per real weapon; all barrel origins stay correct through twist, recoil and limb posing. The offline and live paths cannot diverge because they use the same assembly implementation.

### C4 — All-family fallback and large-unit placement

- [x] Supply the coverage-table family fallbacks and 15 authored Mek topology/weight-class bodies, plus five hybrid air-Mek bodies. Shared generator helpers do not imply shared runtime size profiles.
- [x] Capture actual occupancy/configuration; render whole large units once and apply independent 0.85 scaling. Separate rest dimensions from gameplay height.
- [x] Implement highest-support placement, correct airborne/naval alternatives, shared picking/bounds/shadows and live scale tuning. Keep `BoardGeometry.DEFAULT_MULTI_HEX_UNIT_SCALE = 0.85f` and a dedicated **TUNING → Multi-hex unit scale** slider, independent of the normal unit scale.
- [x] **Landed-Aero support addendum:** extend the body/export/validation contract with independent landing supports; update the Union fallback and future multi-hex Aero authoring requirements. Capture actual grounded elevation/state and extend each support to its own valid surface. Visibly slide supports into the hull before liftoff and deploy them after landing, using authored stowed offsets and the shared timeline. Exclude building entities/mobile structures; reuse the C6 rig/timeline. [Verified implementation and animation](MODULAR_MODELS_C4_SUPPORTS.md).

**Baseline gate (verified):** each inventory family/configuration loads a recognizable fallback; a superheavy is visibly larger than a 100 t Mek; a grounded seven-hex Union over unequal heights passes both views, picking, shadow and landing tests. Normal 0.7 and large 0.85 scale are independent. No rules/occupancy are changed for visual convenience.

**Support addendum gate (verified):** verify the one-level-1/six-level-0 Union example with each foot touching its
own surface and the hull staying clear. Cover flat terrain, mixed levels, grounded elevation 0 above/below world
Z=0, positive elevation/airborne altitude, takeoff/landing elsewhere, rotation, both scale sliders, changed terrain,
map edges and valid/invalid water/bridge/roof contacts. Both views, picking and shadows include the extended legs.
Skip/reveal/restore cannot leave dangling flight gear or stale extensions. A multi-hex building/mobile structure
receives none of this behavior. Review the named and fallback rigs before checking off this addendum.

### C5 — Camouflage materials

Previous gate: [C4 evidence](MODULAR_MODELS_C4.md) records family/configuration coverage, live equipment on other
families, whole-Union placement, both cameras, picking/shadows, squadron membership and the independent scale controls.

- [x] Export paint UVs/material roles and resolve current Entity/force/owner camouflage through existing APIs.
- [x] Apply image/solid camo, rotation and density consistently to bodies and modules; cache textures and isolate per-unit material parameters.
- [x] Retain glass/metal/lens colors, location damage and applicable marker overlays; add the existing missing-camo fallback.
- [x] Author the destroyed-armor texture, hide confirmed blown-off locations and display collectable ground limbs through the shared equipment mesh, with flat-marker fallback.

Verified behavior, screenshots and tests: [C5 evidence](MODULAR_MODELS_C5.md).

Damage art addition (2026-09-19): use an authored, opaque 128×128 neutral-gray scorched-metal texture for attached
destroyed locations and disabled equipment. A confirmed blown-off Mek head, arm or leg must disappear together
with its location-owned modules, including during the phase that reports the loss. Preserve game damage/phase rules.
Use actual `Terrains.ARMS` / `Terrains.LEGS` counts to draw the existing canonical `Limb Club` equipment mesh on the
ground; collecting a limb removes its prop. No extra Entity or inferred corpse inventory. Keep classic limb decals
as fallback when models are disabled or the mapped asset cannot load. The terrain records no head remains,
source chassis, owner/camouflage or carried loadout, so these ground props use the shared authored limb appearance.

**Gate:** two identical units with different camo/rotation/scale remain independent during movement, twist, damage and loadout changes. Pattern does not swim. Lit/shadow/see-through views are correct, and repeated view open/close releases textures.

### C6 — Shared family animation

In progress: assembled bodies/formation members carry their authored joint-role mappings. The renderer now has
a rest-based family pose evaluator and shares unit playback speed with torso twist/airborne wobble. Resolved
movement waypoints carry optional Mek prone-cause observations, preserving fall/get-up order instead of applying
the final posture at the beginning of travel. Native walking/crouch/fall and BA heading reviews pass, with fixed
ankle bindings/contact levels and unchanged mesh detail. [C6 progress evidence](MODULAR_MODELS_C6.md) separates
this verified foundation from the remaining family/action/arrival work.

The later [playback checkpoint](MODULAR_MODELS_PLAYBACK.md) adds bounded capability-based travel time,
acceleration/braking, distance-driven foot/wheel motion, configurable per-troop start-time jitter, independently
timed jump exhaust and the one-second completion hold. Native straight/level contact and six-suit staggered jump
reviews pass. The later terrain, conversion and interruption evidence is linked below.

The [broad checkpoint update](MODULAR_MODELS_C6_C9.md) records the initial movement matrix. The
[completion review](MODULAR_MODELS_COMPLETION.md) adds actual ramp-surface renders, target contact across
biped/tripod/quad rigs, both-way conversion clips, visibility interruption, death priority and reload poses.
Conversion remains a generic fold/switch/deploy; terrain support remains rigid contact without a second solver.

- [x] Carry authored rigid joint/rest mappings into the shared pose evaluator, including basic locomotion, Mek twist/prone poses and airborne wobble.
- [x] Connect bounded travel speed, acceleration/braking, distance-driven foot/wheel motion and configurable troop start jitter to the shared timeline. Straight/level movement and staggered BA jumps have native review evidence.
- [x] Complete the family action-support matrix and applicable reverse/turn/strafe, slope contact, jump/landing, get-up and conversion transitions. Native fixtures render all 24 non-Mek families on the actual ramp surface in both cameras; generic conversion limits are recorded.
- [x] Add blue jump-jet flame and dissipating smoke at posed pack/module emitters. Use the actual arc for ascent/descent strength, taper smoke to none at landing, and verify depth occlusion, visibility, skip and bounded cleanup. Preserve troop mesh detail.
- [x] Give infantry/BA individual cosmetic headings, outward-biased rest positions and walking-to-rest interpolation. Preserve approved figure detail and independence from gameplay facing.
- [x] Add the basic resolved Mek push, kick, punch and physical-weapon clips on the shared queue.
- [x] Finish target-aware aim/contact, correct limb/weapon selection across configurations, hit/miss recovery and damage-aware layer priority. Keep Mek-only physical/prone/twist clips out of other families.
- [x] Add a shared Pause/Resume control for travel, poses, effects and the completion hold. Instant bypasses pause and skips; the real Scene2D control and queue timing are verified.
- [x] R3 is closed. Complete the wider interruption/reveal/load matrix; preserve captured starting poses while events are queued or paused, without adding another clock.

**Gate:** each family has an explicit action-support matrix with no accidental Mek-only behavior on other units. Voluntary prone crouches, forced prone falls, unknown/reloaded prone rests directly. A fall/recovery within one path occurs at the correct waypoint even if the final state is standing. Prone does not double-shrink. Two views, changes in facing and negative/reversed movement use the same timeline. Foot/track contact is visually credible on slopes without a new movement solver.

### C7 — Infantry boarding travel

The boarding/parking/unloading sequence is in the [playback evidence](MODULAR_MODELS_PLAYBACK.md).
The [completion review](MODULAR_MODELS_COMPLETION.md) closes the motive/lifecycle matrix, including all four
transport motives, destruction, concealment, queued survivor changes and normal/Instant arrival equivalence.

- [x] Add boarding markers, member assignment and approach/board → drive/park → full stop → disembark/settle on the shared interval. Basic transport review verifies passengers emerge after parking.
- [x] Verify motorized, wheeled, tracked and hover approach/parking across one/two-vehicle groups, bends, reverse and all six arrival directions. Native tests measure bounded turns, forward/reverse alignment, stopped vehicles during unloading and matching normal/Instant placements at default and enlarged board/family scales. Oversized groups may bleed beyond the hex, as requested. See the broad checkpoint update.
- [x] Close R4 and verify queued casualty/vehicle slot changes, consecutive moves and matching normal/Instant arrival formations across motorized, wheeled, tracked and hover groups.
- [x] Complete destruction/hidden-unit lifecycle coverage. Keep BA, foot and jump troops on their own locomotion behavior.

**Gate:** one/two-vehicle motorized and mechanized groups visibly board, drive, finish parking and stop before troops emerge. Review arrivals from different directions, one vehicle facing left and another forward, a bend/reverse, rapid queued moves and mid-sequence casualties. Vehicles remain stationary while soldiers walk/turn into their varied final slots. No ghost passengers, orphan children, extra Entity instances or long per-soldier waits. Skip and normal playback yield identical final placement/headings; frame rate and camera switching do not reroll them.

### C8 — Firing effects, damage and destruction

Static damaged materials, blown-off location visibility and collectable arm/leg props are verified in C5.
The [playback checkpoint](MODULAR_MODELS_PLAYBACK.md) implements resolved firing and basic Mek physical-attack
playback, authored muzzle effects, hit/miss reactions and recovery, with server/client visibility checks.
The [completion review](MODULAR_MODELS_COMPLETION.md) records observed bay/MGA/AMS/artillery firing, ammunition
impact variants, target contact, optional synchronized sound hooks and family death/crash/wreck poses. Swarm
secondary flight and attack-value-only cluster counts remain explicit presentation limits; no game resolution is replayed.

- [x] Wire the structured visible firing/resolution stream, deduplication, basic posed muzzle effects and resolved Mek physical clips with hit/miss reaction and recovery.
- [x] Group adjacent shots into one volley with configurable launch jitter and one completion hold. Render exact missile rack counts, partial cluster hits/misses, indirect arcs and bounded smoke; preserve real physical gun identities. Native LRM-20, mixed Atlas volleys and 1,280-missile stress checks pass. Server tests distinguish missile counts from ATM/iATM/dead-fire damage points. Swarm continuation paths and attack-value-only outcomes remain documented limitations.
- [x] R1/R2/R5 are closed. Complete specialized bay/MGA/AMS/artillery, rear and multi-barrel firing, moving/indirect/hex targets and ammo/mode-specific effects without replaying game resolution.
- [x] Complete target-aware aiming/contact and synchronized sound hooks, using existing authorized events. Verify disabled/missing mounts and model-disabled fallback presentation. Hooks default to silence; a sound pack is not included.
- [x] Finish physical hit/miss contact across rig configurations and game-reported push displacement; verify contact positions through torso/limb animation.
- [x] Complete family death/crash/collapse/wreck transitions and attachment damage, respecting visibility and entity removal. Native terminal-pose/reload checks cover 33 fixtures; persistent wrecks follow existing BoardView eligibility and preferences.

**Gate:** a firing order alone produces no fake shot; actual firing originates at the correct animated muzzle. Hit/miss/death match authorized game information, and the same event is not emitted twice. Sensor contacts leak no model, camo, weapon or hidden target through loading, audio or effects. Death/skip/pause/target removal leave no unbounded particles or retained models.

### C9 — Performance, migration and maintainability sign-off

The final 64/256/512 stress matrix, realistic 72/144-unit battalion mix, GL allocation audit and clean staging
inspection are in the [completion review](MODULAR_MODELS_COMPLETION.md). The exact C0 proxy passes at p95
11.004 ms. The full 144-unit board is roughly 36–40 ms median on the measured Iris Xe, and the 512-unit stress
case has tails above 500 ms. These do not constitute production performance sign-off. Bounds, opaque ordering,
outline culling and depth-pass merging preserve the art. The subsequent [detail review](MODULAR_MODELS_DETAIL.md)
adds equipment hiding, cached tree detail levels and reuse of captured depth instead of another geometry pass.

- [x] Run the agreed mixed-unit benchmark matrix; profile draw calls, frame-time tails, allocation, assembly/loading and memory. Apply only optimizations supported by those measurements.
- [ ] Resolve the remaining dense-board draw cost and long stress frame-time tails before production performance sign-off. Retain the full-board measurements as the next comparison baseline; do not substitute the C0 proxy for them.
- [x] Exercise reinforcements, refits, repeated reveals, camera/board switches, terrain changes, game reloads and repeated view disposal; verify bounded resources and no per-frame uploads.
- [x] Move migrated baked variants/formations to references and guard the legacy builder against deployed output. C3 records the asset/hash, mekset and staging checks.
- [x] Verify a clean staged package contains only live components/intentional overrides. Remove obsolete live consumers or duplicate assembly paths if found; retain deliberate schema-1/reference compatibility without using it for shipped baked loadouts.
- [x] Finish authoring examples and validation commands against the completed rig/event behavior. Review a new chassis, equipment recipe and variant override without editing the central rendering loop.
- [x] Complete a native gallery/short animation reel covering every family, both views and the acceptance cases below; record any remaining limitations rather than declaring every chassis authored.
- [x] At the end, review whether dynamic infantry/BA equipment provides enough visual benefit to justify its cost.
  Keep approved figure meshes and their embedded weapon detail; dynamic troop equipment remains deferred.
- [x] Remove tree opacity/fading and its tuning control; retain opaque LoD, picking, shadows and unit outlines. Tree-club collection changes equipment only. Tree counts follow engine-provided woods/jungle cover reductions, with no renderer-owned damage or tree inventory.
- [x] Hide unreadable attached equipment using projected size and hysteresis; preserve body meshes, selected/attacking detail, damage, emitters, bounds and shared buffers. Measure full/hidden equipment in 72/144-unit scenes and repeatedly cross thresholds.
- [x] Cache tree batches per chunk/detail level on first use; avoid tree occupancy checks and rebuilding trees when building cutaways change. Unit-only tuning does not rebuild forests; dropped-limb scale changes rebuild only affected chunks. Record the extra cache memory, without claiming a memory reduction.
- [x] Reuse captured camera depth for overlay occlusion; keep shadow resolution and geometry coverage. Reuse shadow transforms and skip shadow-map redraw for changes only to light color, fog or exposure.
- [x] Remove extruded unit meeples. Retain flat sprite fallback for disabled/unavailable models and independent raised sensor/terrain markers. The shared model wrapper is `GpuUnitModel`.
- [x] Increase Mek/ProtoMek stride and airtime by one third at fixed travel speed; use distance-driven planted feet. Give all ProtoMek fallback forms actual foot joints, without changing triangles or rest silhouettes. Verify lateral/backward movement as well as forward travel.

**Gate:** family coverage is complete, generated asset growth follows reusable components rather than unit/loadout count, custom units work without baking, benchmarks meet the targets agreed at C0, and all correctness/visual gates are signed off.

## 11. Minimum regression/review fixtures

Use existing test infrastructure and actual libGDX imports/renders; extend `UnitModelSelectionTest`, `GpuUnitModelsSmokeTest`, movement/twist/damage and board geometry/source tests rather than creating parallel harnesses. New semantic tests belong at the state/assembly boundary, not around trivial getters.

| Fixture | Required observation |
|---|---|
| Same chassis × two owners/camos × two custom loadouts | Shared buffers, independent materials/pose, correct live equipment; no baked variant dependency. |
| Warhammer searchlight | Absent, external, mounted, active and destroyed states; one appropriate mesh/emitter, never a baked duplicate. |
| Dense/rear/split/bay loadout and missing actuators | Deterministic valid location fit; no duplicated split/bay weapons; correct muzzle and hand/wrist/elbow anatomy. |
| Structure/armor/ammo; unmapped WeaponType; flagged physical misc; mapped/unmapped optional misc | Excluded types create no mesh/hardpoint/emitter; required weapons have authored or appropriate fallback visuals; optional misc never receives a generic fallback. Claws/shields are not missed by an F_CLUB-only check. |
| Mek push, kick, punch and physical-weapon hit/miss; same action family on a non-Mek | Correct attacking limb/weapon, contact and recovery; target displacement follows the game. No Mek physical-attack clips on another family. |
| Newly mapped equipment on multiple compatible chassis/fallbacks and a custom loadout | A global asset/mapping change supplies the mesh and emitters everywhere; exact mapping overrides broad defaults, intentional chassis overrides survive, and no renderer code or variant bake is needed. |
| Capital-fighter generated groups and a mixed squadron with reversed weapon ordering | Logical groups add no physical guns; one resolved group selects the correct real member mounts for both recoil and effects, including disabled/empty groups. |
| Terminal fall/get-up followed by a shot or another move at all speeds | Full posture recovery/arrival finishes first, then the one-second real-time hold, then the next event. Instant skips both animation and hold. |
| Queued transport movement while the latest scene changes survivors/composition | Boarding, displayed members and movement use the same authorized event snapshot; current game state remains authoritative when playback catches up. |
| All conventional movement types and 0–6 slots from current survivors; BA compression off/on | Default BA shows one figure per living trooper, including six → one → zero; exact living member removal and no reduction for armor damage alone. Optional BA compression and conventional survivor compression remain independent. Check separate children, staggered layout, jump packs, casualty stability, transport reconciliation and boarding applicability. |
| Voluntary/forced/unknown prone; saved prone; get-up/hull-down; fall then recovery within one path | Cause survives state transfer, transitions occur at the correct waypoints, scale constant, no gameplay effect. |
| Tripod/quad/biped sizes 1–4 plus superheavy | Recognizable topology/size, rig compatibility and no invented AS category. |
| Union seven-hex and elongated large unit over mixed terrain | One assembly, highest support, 0.85 scale, full-footprint pick/cull/shadow, correct takeoff/landing. |
| Landed multi-hex Aero supports; Union over one level-1 and six level-0 hexes; multi-hex building control | Hull stays at the highest support; each foot independently reaches its own lower ground after facing/scale. Elevation 0 on raised terrain deploys supports; positive elevation/flight has none protruding. Terrain/landing changes and skip/reveal reset lengths; building entities/mobile structures are excluded. |
| Fighter, squadron, VTOL, ship, submarine, emplacement, conversion unit, exceptional proxy | Appropriate fallback, movement/animation/effects and no borrowed Mek-only state handling. |
| Visible → sensor/hidden → visible; mid-animation removal | No identity leaks or stale effect replay; correct snap/release behavior. |
| Paused/skipped/accelerated movement, shots, falls and death | One clock and the same final state; no animation frame rate changes game results. |
| Old/bad descriptor, missing node/texture, unrecognized equipment | Explicit safe fallback and useful diagnostics; board still opens. |

## 12. Original plan review and deliberate exclusions

The table below records the original proposal review. The current implementation audit is
[MODULAR_MODELS_REVIEW.md](MODULAR_MODELS_REVIEW.md); neither table substitutes for the checkpoint gates.

| Finding from review | Adjustment included above |
|---|---|
| Map-start-only assembly misses reinforcements, reveals, refits and mode changes | Separate structure/appearance/pose updates and bounded per-view ownership. |
| Persistent prone boolean cannot distinguish deliberate lowering from falls | User's refinement: authoritative `ProneCause` on Entity, including save/network compatibility and clearing through hull-down. |
| Final posture/cause can omit a fall and recovery within one movement update | Sparse resolved posture cues use existing waypoints and playback; Entity retains only current cause/state. |
| Existing height-based Z scaling would shrink an already crouched skeleton | Fixed rest dimensions; current height remains rules/occupancy data. |
| Existing rigid nodes and torso/damage/motion behavior already solve useful parts | Reuse them, standardize roles and replace only duplicated/limiting responsibilities. |
| One class per concrete Entity type would grow an unmaintainable parallel hierarchy | A handful of family handlers plus composition and explicit coverage mapping. |
| “All weapons” can double-count bays/grouping devices and miss intrinsic searchlights | Explicit visible/embedded/container/internal inventory and stable logical mount bindings. |
| Blanket fallback and F_CLUB-only selection contradict the refined equipment scope | Type gates exclude structure/armor/ammo first, prioritize WeaponType, cover F_PHYSICAL_WEAPON and require explicit optional-misc mappings without fallback. |
| Firing/recoil alone does not cover physical combat | Mek-only push/kick/punch/weapon clips use resolved action, attacking limb, contact and recovery on the same timeline. |
| Porting the build verbatim leaves two equipment matchers and two placement algorithms | Compile art mappings; Java becomes the single live/review assembler. |
| New equipment could require renderer edits or repeated assignments for every chassis | A global canonical-ID/module mapping, with broad family defaults, supplies compatible units automatically; C3 verifies adding and replacing it. |
| The previous shared compression policy capped BA at four displayed figures and did not express the requested one-per-survivor default | `BattleArmorVisual` owns a compression switch defaulting to `false`; immutable living-member updates drive casualty reconciliation, with both policies and six-figure budgets checked at C2. |
| Sharing ModelInstances can share transforms/materials accidentally | Shared immutable assets; isolated child/pose/material state; lifecycle gates. |
| A complete model emitted per secondary sprite would duplicate a large craft | One assembly, real occupancy, independent 0.85 scale, common highest support. |
| “Low poly” alone says nothing about draw-call or texture cost | Measured benchmark gate and bounded caches/effects before broad rollout. |
| Runtime format/rig migration could destroy handmade variant anatomy | Compatible body/rig overrides and a documented exceptional complete-assembly path. |
| Cosmetic shots could imply fabricated outcomes or expose hidden units | Structured visibility-filtered firing/resolution events, not order-line or text parsing. |
| A source can be removed or refitted before its queued shot/death plays | Retain minimal authorized event bindings/pose for bounded playback, then release them. |
| Boarding phases could duplicate travel interpolation or leave labels following a different root | UnitMotion owns the driving path sampler and displayed root; infantry owns child movement. |

Keep these outside the initial proof of concept: physics ragdolls, dynamic mesh fracture, cloth, a general animation graph editor, a new ECS/asset-plugin framework, networked animation simulation, a new renderer, unrestricted procedural body generation, and a full cinematic camera system. Multi-joint terrain IK, advanced decals, triplanar camo and hardware instancing are candidates only after a measured/visual need. Basic contact, readable impacts, sound hooks, selection, effect controls and all family fallbacks are in scope.

Large-unit tactical footprint, physical dimensions and strategic/space-board scale are different concepts. Keep board-mode profiles explicit; do not extrapolate a universal metres-per-hex model from the Union example. No unsupported unit should disappear because it is outside the first visual profile.

### Tracking

The requested melee, conversion, fall, missed-shot/flamer and intermediate-damage corrections are tracked in
[the animation and damage polish checklist](MODULAR_MODELS_POLISH.md). Earlier proof-of-concept checks do not
constitute sign-off for these new acceptance requirements.

- [x] Inspect the current tools, descriptors, renderer, movement/damage/camo and relevant rules.
- [x] Incorporate runtime assembly, all-family coverage, superheavy/multi-hex handling and persistent prone cause.
- [x] Review the plan for missing lifecycle/event cases, duplication and unnecessary frameworks.
- [x] C0 baseline/inventory complete. See [verification evidence](MODULAR_MODELS_C0.md).
- [x] C1 contracts/state bridge complete. See [verification evidence](MODULAR_MODELS_C1.md).
- [x] C2 runtime infantry complete. See [verification evidence](MODULAR_MODELS_C2.md).
- [x] C3 runtime Meks/equipment complete. See [verification evidence](MODULAR_MODELS_C3.md).
- [x] C4 family fallback/large placement baseline complete. See [verification evidence](MODULAR_MODELS_C4.md).
- [x] C4 landed multi-hex Aero support addendum complete (independent ground contact, fully stowed in flight; building units excluded).
- [x] C5 camouflage/damage materials and collectable limb props complete. See [C5 evidence](MODULAR_MODELS_C5.md).
- [x] C6 family animation proof of concept complete; generic contact/conversion limits recorded.
- [x] C7 boarding travel complete.
- [x] C8 firing/damage/death proof of concept complete; specialized-effect limits and silent sound hooks recorded.
- [ ] C9 performance/migration sign-off complete.

Record evidence at each gate before marking it complete. Open checkpoints can contain verified foundations and
unfinished work; the individual tasks and evidence above distinguish them. Historical completion does not waive
the implementation-review fixes.
