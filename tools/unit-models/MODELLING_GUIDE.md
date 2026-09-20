# Modelling guide for unit models ("MegaMeks")

How a new Mek gets a low-poly model, and the conventions agreed while building the first ones. The
asset layout and build commands are in `data/models/units/README.md`; this file is the working method
and the house rules. Everything here came from review feedback on real models, so treat it as binding
until a Mek's own artwork says otherwise.

Bare-unit target: **under 1,000 triangles before loadout**. **Conventional infantry and Battle Armor are always
exempt from this target**, since several figure/transport meshes form one game unit. Other families may exceed
the target after art review. The **1,500-triangle bare-unit hard cap** still applies to every family, including
infantry formations. Weapons/equipment are additional and do not consume the body allowance. Report body,
equipment and assembled totals separately. Preserve infantry and Battle Armor detail: the six-suit base
formation uses 1,284 triangles. Distance-based LoD will be evaluated later.

The proposed runtime assembly, rigging and animation migration is tracked in
[MODULAR_MODELS_PLAN.md](MODULAR_MODELS_PLAN.md). This guide describes current authoring until each
corresponding migration checkpoint is implemented.

The reusable schema-2 component format, build command and verified fixtures are documented in
[MODULAR_MODELS_C1.md](MODULAR_MODELS_C1.md). Default infantry now uses runtime components as described in
[MODULAR_MODELS_C2.md](MODULAR_MODELS_C2.md). Mek loadouts use the verified runtime assembly described in
[MODULAR_MODELS_C3.md](MODULAR_MODELS_C3.md). Family fallback/large-unit placement is verified in
[MODULAR_MODELS_C4.md](MODULAR_MODELS_C4.md). Image camouflage, authored damaged armor and collectable limb
props are verified in [MODULAR_MODELS_C5.md](MODULAR_MODELS_C5.md).
Landable multi-hex Aero artwork must meet the landing-support specification in [§7](#7-multi-hex-aero-landing-supports).
Independent ground-reaching supports are an open addendum to C4, not part of its already verified placement behavior.
The old baked meshes are visual targets in `tools/unit-models/references/legacy/units`, outside deployed data.

Dynamic equipment attachments for conventional infantry and Battle Armor are deferred until the final review.
Keep their approved figure meshes, including their current rifle/cannon details; equipment-library entries do not
imply that those items should be attached to figures or their transports now.

## 1. The steps

1. **Pick the Mek and gather references.** Three are used:
   - the top-down 84 x 72 game sprite, for where things sit left-right and front-back;
   - a picture copied into `data/images/fluff/Mek/` (git-ignored, but the build refuses to run without it);
   - the modern miniature renders on Sarna (`cfw.sarna.net/wiki/images/...`). **These are what the model is
     judged against.** The old TRO line art is a rough guide only and is often a different design.
2. **Inspect representative loadouts.** The catalog (`.work/mek-models/catalog.json`) provides reference
   examples. Cover launchers, rear weapons, hand weapons, jets and custom refits; do not export every loadout.
3. **Write the body** in `tools/unit_mek_chassis.py`: boxes, beams and tapered sections, no weapons.
4. **Write the recipe** in `tools/unit-models/chassis.json`: sprite, picture, hip and the hard points.
5. **Export reusable components** with `build_modular_unit_models.py`. Review actual assembled units with the
   native Java renderer; this uses the same placement implementation as the game.
6. **Review, adjust, repeat.** Expect several rounds. Send a four-view sheet each time.
7. **Update mekset** to `units/modular/meks/<id>.json` and validate through `UnitModelDescriptorTest` and the
   native `GpuModularUnitModelsSmokeTest`. No baked variant or group files belong under deployed `data/`.
8. **Compare stock and custom assemblies** with the archived visual targets. `render_unit_variants.py` now
   reads the frozen references; the live/review assembler is Java, not the old Python variant builder.
9. **Stage the game data** (`gradlew :megamek:stageDataFiles` in the MegaMek checkout). The game reads a
   staged copy, not this repository.

## 2. What reviewers look at first

Learned the hard way on the Archer, which took five rounds:

- **Head or cockpit: height, and how far it projects.** Check this before anything else.
- **The cockpit is a canopy, not skylights.** Model the glazing as a faceted glass shell standing proud of
  the hull where the art has it, usually wrapped over the top and front of the nose, with a frame rib.
  Flat glass strips laid on top of the hull read as roof windows and are wrong.
- **Proportions of a solid miniature.** No bodybuilder shoulders wider than the design; keep it compact.
- **No drooping parts.** A projecting cockpit is one solid mass whose underside runs level back into the
  torso; only its top slopes. Never leave a part hanging with empty space beneath it.
- **Launcher shape matches the miniature**: tall or wide, how many tubes across, and whether the face
  leans back (`missileSlope`). Missile bay doors are modelled shut.
- **Antennas and sensors go where the miniature has them**, not where it is convenient.
- **The upper body must turn cleanly at the waist.** The game twists everything that hangs from `CT`
  (head, side torsos, arms) about the recipe's `hip` point while the hips and legs stay put. Keep that
  point on the center line under the middle of the torso, keep hip and leg parts out of the upper body
  groups, and render the body with `--bare --turn 60`: nothing above the waist may cut through the hips
  or legs, and no gap may open between them.

## 3. Hard points

A hard point is `[sprite x, sprite y, height]`. The sprite's center is pixel (42, 36); left-right is
`x - 42`, forward is `36 - y` (up on the sprite is forward on the model). Height uses the body's units:
hips about 29 to 31, the top of a tall Mek about 55. Put a hard point where the barrel leaves the armor,
or for a launcher at its front face, just proud of the body.

Every recipe needs eight (`HD CT LT RT LA RA LL RL`). Extras:

| Recipe key | Purpose |
|---|---|
| `socketBanks` | Exact spots for one kind of weapon in one location, e.g. `"RA:hatchet"` at the fist. |
| `missileSockets` | The bay for a torso's launchers. Two or more stack inside `missileBayHeight`; three or more go side by side with `missileBayColumns` and `missileBayWidth`. |
| `rearSockets` | Rear-facing weapons. Without one the front point is reused nine pixels back, which often lands inside the body. |
| `socketAim` | A direction for a location's weapons, e.g. `"LA": [0, 0.12, -1]`. |
| `protrusion` | How far barrels stand out, per location or `LOC:family`. |
| `missileOrientation` | `horizontal` or `vertical`, for the whole Mek or per location. |
| `mountAreas` | The rectangle weapons in a location are laid out in: `{"center": [x, y, z], "width", "height"}`. |
| `beltSockets` | Overrides where leg weapons sit. |
| `armSockets` | Where an arm weapon attaches for each arm form: `{"LA": {"elbow": [...], "wrist": [...], "hand": [...]}}`. |
| `weaponOverrides` | Per-weapon changes to the standard look, matched by `location`, `family`, `name`, `rear`. |

Conventions:

- **A weapon follows its limb.** When an arm is posed hanging down, give that hard point a `socketAim`
  so the barrel runs along the forearm. A barrel must never jut out at a right angle to the limb.
- **Arm actuators decide how an arm weapon looks, per variant.** Check them when listing the loadouts.
  With a **hand** actuator the weapon rides on the forearm. With the **hand missing** it attaches at the
  **wrist**. With the **lower arm missing** it attaches at the **elbow**. Tag the optional arm parts in the
  body function (`LA@elbow`, `LA@forearm`, `LA@wrist`, `LA@hand`, and the same for `RA`), give the recipe an
  `armSockets` entry per form, and key form-specific banks like `"LA@wrist:ppc"`. The Mackie covers all
  three forms across its six variants. The catalog needs the exporter's `lowerArms` field for this.
- **Leg weapons ride just below the hip, like a low-slung belt.** The generator lifts them to hip height
  minus five automatically. **Jump jets stay in the calves, at the back.**
- **Weapons in one location never overlap.** Each location has a mounting area; a weapon that would
  overlap another is moved to the nearest free spot in it, and only shrunk if the area is truly full.
  Bay launchers and `socketBanks` spots keep their place; the rest give way, largest first. A location
  that still cannot be resolved is marked `crowded` in the manifest: state a `mountAreas` entry for it.
- **Re-check every hard point after reshaping the body.** A changed head buried the Archer's rear laser.
- **Always render a rear view.** A rear launcher's face stands less than one unit proud of its hard point,
  so a rear hard point even slightly inside the hull buries it. Put rear hard points just behind the back
  of the hull and confirm in a rear view that every rear weapon shows. The variant sheets only show the front.

## 4. Standard weapon looks

`weapons.json` holds the defaults; `unit_weapon_shapes.py` draws them; `render_weapon_chart.py` renders
every look side by side. **They are a starting point.** After applying them, compare the result with the
Mek's art and adjust in that Mek's recipe (the Marauder's AC/5 has a longer barrel than standard).

- The look comes from the weapon's **type**, never its tonnage. Sizes are fixed classes multiplied by the
  recipe's `weaponScale`, so a light Mek's guns are smaller than an assault's but proportions hold.
- **Tip colors:** red lasers, blue PPCs *only*, green TAG, orange plasma and TSEMP. Cockpits keep `glass`.
- **Lasers** slim square barrels in small, medium, large; pulse is shorter and fatter with a ring; heavy
  is thicker; a Blazer has twin barrels. **PPC** a thick barrel with a ring and a narrower emitter tip.
- **Autocannons** round, from long thin AC/2 to short fat AC/20; Ultra adds a muzzle brake, LB-X a
  flared muzzle. **Rotary AC/2 and AC/5** are a gatling ring of six thin barrels.
- **Gauss** a square rail with two coil rings. **HAG** four square rails in a two-by-two block, in three
  weights: HAG/20 light, HAG/30 medium, HAG/40 heavy.
- **Anti-missile system** a small gatling on a housing, like a naval CIWS; the laser AMS shows one red lens.
- **Launchers** never show a short row. LRM, SRM, Streak, MRM and Rocket Launcher tubes are **round**:
  LRM smallest, SRM in the middle, MRM and rockets only *slightly* larger. ATM, improved ATM and MML tubes
  are **diamonds**, all one size. A launcher mounts **horizontal or vertical**; decide per hard point.
- **Every barrel has four protrusions:** recessed (flat against the body), short, medium, long. Arms
  default to long; torso lasers, machine guns and TAG to short.
- **Hand weapons:** the hatchet blade faces forward; the sword and the mace lean forward forty-five
  degrees so they clear the forearm. Industrial tools have distinct silhouettes: saws, drills, a backhoe,
  a combine, a pile driver and a welder use their own reusable shapes and contact/working points.
- **Searchlight:** a separate box with a pale lens, attached from actual mounted equipment or an external
  lamp declared by the design. The automatic gameplay searchlight granted to Meks/vehicles does not add a
  housing by itself; those external housings also require the Searchlight design quirk. Do not bake lamps
  into a bare chassis. See `MODULAR_MODELS_PLAN.md` for presence, damage and illumination behavior.

## 5. The triangle budget

Aim below 1,000 triangles for the bare unit and preserve its recognizable silhouette. Conventional infantry and
Battle Armor formations have a standing exception to this target because they combine multiple figures/transports;
they need no separate exception approval to exceed 1,000. The exporter reports base counts at or above the target;
other families need art review. The 1,500 bare-unit hard cap still applies to all families. Complete loadouts may
exceed 1,500 in total: weapons and equipment have separately reported costs,
and are not removed to meet the body allowance. Each equipment module instead targets **under 100 triangles**
and must remain **strictly under 150** (149 maximum), including every compact/style/profile export and fallback.
The authoring exporter and runtime asset validator enforce this separate equipment cap.
Reviewed chain exceptions are Flail (140), Chain Whip (140) and Wrecking Ball (136); all other current
equipment modules, including styles, profiles and fallbacks, stay under 100 triangles.
`DETAIL_LEVELS` remains an authoring option for a deliberate, visually reviewed reduction. Distance-based LoD
is future work, not an excuse to remove current full-detail artwork.

## 6. Traps

- A shrunken launcher can end up **behind its housing wall** and look like an empty bay. Keep the
  housing face about 0.35 behind the hard point.
- Make columns times rows **equal the tube count**; five and seven tubes use two rows, short row centered.
- Launchers stacked in one bay lean about the **bay's** center, or they form a staircase.
- Anything the catalog cannot classify sets the whole variant aside (`needsReview`).
- The catalog is a snapshot: re-run the export before building if unit files changed.
- The preview sheet only fits four models; use the variant renderer for more.
- A preview PNG open in an image viewer is locked on Windows; save under a new name.

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
