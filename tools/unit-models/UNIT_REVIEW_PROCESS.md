# Unit review process

How a chassis gets authored, reviewed and signed off. [MODELLING_GUIDE.md](MODELLING_GUIDE.md) holds the
house rules for the artwork itself; this file holds the working loop and the review conventions agreed
while building them. Everything here came from real review rounds, so treat it as binding.

## 1. The loop

Two catalogs are prerequisites. Re-export them only when MegaMek's equipment or unit files change.

```bash
./gradlew :megamek:exportEquipmentModelCatalog :megamek:exportMekModelCatalog --console=plain
```

They land in `mm-data/.work/modular-models/equipment.json` and `mm-data/.work/mek-models/catalog.json`.
Nothing downstream runs without them.

| Step | Command | Time |
|---|---|---|
| Author the body | `tools/unit_mek_chassis.py`: a `def <id>(g)` plus an entry in the `builders` dict | - |
| Write the recipe | `tools/unit-models/chassis.json`: hip, eight sockets, mount areas | - |
| Export | `python tools/build_modular_unit_models.py` | 11 s |
| Review the bare body | `blender --background --factory-startup --python tools/render_modular_body.py -- --body <id> --turn 60` | 10 s |
| Register | one `chassis` line in `data/images/units/mekset.txt` | - |
| Validate | `./gradlew :megamek:test --tests "*UnitModelDescriptorTest*"` | 6 min |
| Review assembled | `./gradlew :megamek:gpuBoardSmoke --tests '*GpuModularUnitModelsSmokeTest*'` | 2 min |

The middle three rows are the iteration loop, about twenty seconds a round. Expect several rounds;
the Archer took five. Send a sheet each round.

Assembled review images land in `megamek/build/gpu-board-review/`. A chassis with no frozen legacy bake
gets a `runtime-new-<id>` pair of its own; one with a bake gets `runtime-compare-<id>`.

**Three tools are legacy and must not be used on modular assets:** `build_unit_models.py`,
`render_unit_variants.py` and `validate_unit_models.py`. All three still expect schema 1 and the baked
variant layout.

## 2. The review sheet

`render_modular_body.py` renders the deployed schema-2 body. Standard sheet, every round, no exceptions:

**Front, Back, Left, Right, Above, Three-quarter**, on a three-by-two grid.

### The three renders to ask for

| Ask for | What it shows | Produced by |
|---|---|---|
| **the chassis** | bare body, six angles, no loadout | `render_modular_body.py` |
| **the chassis with weapons** | one variant assembled, six angles | `renderFullReview` |
| **the variant sheet** | every variant of the chassis in a grid, one angle each, with triangle counts | `GpuVariantSheetReview` |

The variant sheet is the comparison view: it shows the shared body under every loadout the game will
hang on it, so a specific variant can be picked out for a closer render. It writes
`variants-<Chassis>.png`, eight across, sorted by model, headed with the count and the triangle range.
It renders to an off-screen framebuffer, so the sheet is not limited to the 1280x800 window.

A **full render** means all six of those angles on one sheet. Two renderers produce one:

- **Bare body:** `render_modular_body.py` writes `<id>-review.png`, labelled, three across.
- **Assembled, with weapons:** `renderFullReview` in the native smoke test writes
  `runtime-new-<label>-full.png`, same three-across order, **unlabelled**. Read it as
  front, back, left on the top row; right, above, three-quarter on the bottom.

Give every test unit a full render, not just the chassis it was authored from. Each variant hangs a
different loadout on the same body, which is the only way to see whether a pod suits a PPC as well as
an autocannon.

`--turn <deg>` adds a second sheet for the waist-twist gate: the upper body rotates about the recipe's
hip point while hips and legs stay put. Nothing above the waist may cut through the hips or legs, and no
gap may open between them.

View conventions, verified against geometry that exists on one side only (the Mackie's shield disc rings
its right arm):

- **Front:** the unit faces you, so its right side is on the image left.
- **Back:** its right side is on the image right.
- **Above:** looking down, nose up the page, its right on the image right. Same convention as the
  84x72 game sprite, which makes the two directly comparable.
- Each cell is centred on its own posed bounds, so a plan view does not float against an elevation.

## 3. Markup conventions

Mark up the rendered sheet and send it back. Marks are located to the pixel and mapped to authored
numbers, so rough boxes are fine.

| Mark | Meaning |
|---|---|
| **Red box** | **Always a sizing change.** May indicate both size and basic shape. |

Rules that go with a red box:

- **Tapering stays.** Any taper, step or bevel already authored is preserved through a resize unless
  it is specifically called out. A resize scales what is there; it does not flatten it.
- **Two boxes on the same part from different views are one instruction**, not two. Front and Back both
  measure width and height, so a pair of boxes is a cross-check; average them.
- **Which edges the box shares with the part carries meaning.** A box whose bottom sits on the part's
  bottom edge means take the change off the top.

### Vocabulary

Direction is given in plain words. This maps them to the control that actually changes.

| You say | Control | Value |
|---|---|---|
| full render | all six angles of one unit on one sheet | bare body: `render_modular_body.py`; assembled: `renderFullReview` |
| the chassis | the bare body, no loadout | `render_modular_body.py` |
| the chassis with weapons | one variant assembled | `renderFullReview` |
| variant sheet | every variant in a grid, for comparison | `GpuVariantSheetReview` |
| flush, recessed, flat against the body | `protrusion` for that location | `recessed` (0.06) |
| barely proud, stubby | `protrusion` | `short` (0.4) |
| standing out | `protrusion` | `medium` (0.7) |
| reaching well ahead | `protrusion` | `long` (1.0) |
| longer / shorter barrel than standard | `weaponOverrides` `length` for that location and family | authoring units, scaled by `weaponScale` |
| bigger / smaller guns overall | `weaponScale` | 0.83 (Atlas) to 0.95 (Mad Cat, Mackie, Rifleman) |
| closer to / further from a feature | the location's socket in `sockets` | sprite x, sprite y, height |

**flush and recessed mean the same thing.** Both map to `protrusion: recessed`.

Terms are recorded here as they come up rather than agreed in advance; add a row when a new one lands.

### Measuring a marked box

Never eyeball it. Establish the scale from a known dimension in the same render:

1. Measure the model's silhouette width in pixels for one panel.
2. Divide by the body's known width in authoring units (from `manifest.json` bounds).
3. Apply that pixels-per-unit figure to the box.

Worked example, Rifleman arm pod: the Front panel measured 353 px across a known 41-unit width, giving
**8.61 px per unit**. The two boxes measured 72x99 and 66x104 px, or 8.4x11.5 and 7.7x12.1 units,
averaging **8.0 x 11.8**. Against a pod then 10 x 15, that is a uniform 0.79 scale holding the
authored 2/3 width-to-height proportion.

## 4. How weapons are placed

A hard point names where a weapon leaves the armour, and `mountAreas` gives the facing it is laid out
on. The runtime fitter then places the location's weapons on that facing.

**Weapons sharing a hard point are centred on it as a group.** Their heights are summed with a 0.4 gap,
the stack is centred on the facing, and the largest sits on top. Without this the first weapon took the
socket and the rest were pushed clear of it, so a pair hung below the middle of its facing.

A single weapon still sits exactly on its hard point, which is already the centre of its facing. Bay
launchers arrange their own rows and are left alone. A weapon that cannot fit is shrunk through fixed
steps, and only then moved.

Review images are named for the unit they show, not the body they were authored from:
`runtime-new-Rifleman RFL-3N-full.png`. Every sheet also carries the chassis and model **in the top
right of the image**, so a render stays identifiable once it leaves the build directory. A bare-body
sheet uses the chassis name from the recipe, since it has no variant.

## 5. Vents

Vents are the standard surface detail for a torso, and they read far better than a box stood off the
armour. A vent is a shaded recess behind three lit fins, drawn as flat panels lying in the skin:
`dark` backing at 0.06 proud, `edge` fins at 0.16. Eight triangles each.

Use them sparingly. The limits:

- **At most two on the front** and **at most two on the back**.
- **Back vents only on torso locations.**

Two things to get right, both learned the hard way on the Rifleman:

- **Follow the skin's slope.** A torso that lofts from 13 deep to 14.5 over six units of height moves
  its face 0.125 per unit. A panel at one fixed depth is half buried and half floating.
- **Stay inside the flat part of the face.** A bevelled section chamfers its corners, so the flat band
  is narrower than the section width: a `cut` of 0.3 on a 17-wide, 13.7-deep section leaves only about
  +/-6.4 flat. Geometry outside that band hangs off the chamfer and reads as stuck on.
- Winding reverses on the back so the panels still face outward.

## 6. Budget

Bare unit before loadout: **target under 1,000 triangles**, hard cap 1,500. A thousand is available and
may be spent on detail; there is no virtue in coming in far under. Equipment is counted separately and
never consumes the body allowance: each module targets under 100 triangles and must stay under 150.

Report body, equipment and assembled totals separately. The exporter prints the body count and the
manifest records it per asset.

## 7. Calibration by tonnage

Legs are the easiest thing to overbuild. Check a new chassis against what is already in
`unit_mek_chassis.py` before trusting your own eye:

| Chassis | Tons | Hip x | Foot |
|---|---:|---|---|
| Warhammer | 70 | 7.5 | 9 x 12 |
| Archer | 70 | 8 | 11 x 15 |
| Rifleman | 60 | 7.5 | 9.5 x 13 |

A sixty-tonner with a wider stance and a bigger foot than either seventy-tonner is wrong, however good
it looks in isolation.

## 8. Per-chassis decisions

### Rifleman (60 t, `rifleman`)

- **No variant has a hand or a lower arm.** All 27 carry their weapons at the elbow, so each arm is a
  weapon pod rather than a limb. No forearm or fist is authored.
- **Every variant carries two weapons per arm.** The pod's mount area is taller than it is wide, so the
  pair stacks over-under, matching the line art.
- No variant mounts a rear-facing weapon; 27 mounts are jump jets, which ride in the calves.
- Radar: a swept blade on a short mast, centred, angle approved at review. The game sprite puts a
  two-pronged array right of centre; the miniature and the approved artwork win.
- Barrels are lengthened in the recipe (`weaponOverrides`, ballistic 21, laser 18) because the standard
  shapes read as stubs on a design whose identity is its guns.
