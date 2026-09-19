# Low-poly units

Indexed G3DJ meshes for the GPU board. All nonempty assets must be 
below **1,000 triangles**, including complete infantry formations. Blender is
needed to rebuild and inspect the artwork, not to run the game.

Runtime use is controlled in MegaMek by `GpuUnitModels.ENABLED`, currently `true`.
Set it to `false` to use sprite-based units in both GPU camera views. The assets
and generation/review commands below remain available with either setting.

The first authored chassis are **Atlas, Locust, Warhammer, and Mad Cat (Timber
Wolf)**. Their **112 catalogued variants** share four source bodies and assemble
equipment from MegaMek's loaded unit records. Chassis anatomy is authored against
both the north-facing 84 by 72 sprites and the matching illustrations in
`data/images/fluff/Mek`. The bodies use a few sloped armor volumes, with emphasis
on the skull/shoulders, cockpit profile, leg joints, and weapon arrangement that
distinguish each chassis. These are deliberately stylized silhouettes, not
physical scale reconstructions or automatic single-image 3D reconstruction.

The reference assemblies are **575 triangles for Atlas AS7-D**, **330 for Locust
LCT-1V**, **448 for Warhammer WHM-6R**, and **594 for Mad Cat Prime**. Across all
112 assembled Mek variants the range is **310–672 triangles**. Foot infantry and
BA geometry is unchanged. Six jump troopers are the largest complete asset at
**996 triangles**; transport formations reach **976 triangles**.

The exported catalog covers **4,295 Mek variants / 738 chassis**. The other
**734 chassis** are listed in `chassis-queue.json` and currently use a fallback.
This is not a claim that all chassis have received bespoke models.

## Assets and selection

- `meks/<chassis>/body.g3dj`: shared unarmed chassis, with named rigid pivots.
- `meks/<chassis>/variants/*.g3dj`: assembled variants. Offline baking keeps
  equipment together with its body location and avoids a separate runtime draw
  for every barrel. The generator remains the single assembly implementation.
- `meks/<chassis>/model.json`: loaded unit names plus equipment fingerprints mapped
  to assemblies. Unknown/custom variants use the unarmed chassis, including a
  refit that retains its stock name but changes equipment.
- `fallback/`: visibly generic biped, quadruped, and tripod bodies.
- `infantry/poses/` and `battle-armor/poses/`: standing, aiming, kneeling and
  advancing figures, reused when building the small formations.
- `infantry/squad-0..6.g3dj` and `battle-armor/squad-0..4.g3dj`: compressed
  formations. Zero is intentionally empty. Count is `ceil(sqrt(survivors))`,
  capped at six for infantry and four for BA: 28 infantry -> six figures;
  five BA -> three figures. Disabled weapons do not remove a living BA trooper.
- `infantry/vehicles/`: reinforced open jeeps and a shared enclosed APC hull with
  tracks, six wheels, or a hover skirt and rear thrusters. Transports use twice
  the first prototype's dimensions. Each occupies one compressed formation slot.
- `infantry/{motorized,tracked,wheeled,hover}/squad-0..6.g3dj`: one transport
  replaces a troop at 1–4 slots; two replace troops at 5–6 slots. Thus 3 slots
  show 1 vehicle + 2 troops; 4 show 1 + 3; 5 show 2 + 3; 6 show 2 + 4.
  Zero slots remain empty. Vehicles and troops use a shared layout with clearance
  for the largest hover skirt; no additional runtime entities are created.
- `infantry/jump/`: the four existing poses with small back-mounted jump jets,
  plus formations of 0–6 troopers. Each pack adds only eight triangles.
- `manifest.json`: geometry/source hashes, triangle counts, attachment identities,
  reference sprites and illustrations, source unit paths, coverage, and any
  unresolved variants. Illustration hashes make a changed reference visible to
  the validator, just like changed equipment and generator inputs. Infantry
  formation records identify every source component and placement for review.

The existing `data/images/units/mekset.txt` accepts an optional fourth field:

```text
chassis "Atlas" "meks/Atlas.png" "units/meks/atlas/model.json"
exact "default_medium" "defaults/default_medium.png" "units/fallback/biped.json"
exact "default_infantry" "defaults/default_infantry_platoon.png" "units/infantry/model.json"
```

Paths are relative to `data/models`. Resolution is exact variant, then chassis,
then the existing unit-type default. A sprite-only exact entry inherits the
chassis's model. Transformation modes and secondary positions retain the existing
tileset suffix rules. Aircraft/vehicle conversion modes without 3D assets keep
their sprites. A missing/broken model tries the unit's generic descriptor and
then the previous sprite rendering. Unidentified sensor contacts never carry a
3D identity or troop count into the render snapshot.

For conventional infantry, the immutable selection key is the unit's actual
`EntityMovementMode` name. The infantry descriptor's optional `movementFormations`
maps `INF_MOTORIZED`, `TRACKED`, `WHEELED`, `HOVER`, and `INF_JUMP` to their own
0–6 formations. The existing numeric `formations` remain the fallback for foot
infantry, unsupported movement types and older/custom descriptors. BA retains
its existing pose library and count selection. Vehicle count is a visual slot
replacement, not a simulation of the unit's actual transport inventory.

Infantry/BA are currently generic pose libraries, not separate armor designs or
weapon-specific infantry. Paint surfaces inherit the average hue of the already
colored unit sprite; individual camouflage patterns are not baked into the mesh.
Rigid pivots are present for later limb animation. Movement uses the existing
board animation; walk cycles, damage-specific meshes, and conversion animations
are not supplied in this first library.

Every Mek descriptor, the generic bodies included, names an `upperBodyNode`
(`CT`). The game turns that one part about its pivot to show a torso twist
while the legs keep the unit's own facing, so the head, side torsos and arms
must hang from it, the hips and legs must not, and its pivot must sit on the
center line at the waist (the recipe's `hip`). The validator enforces all
three. A descriptor without the key still loads; the whole body then turns
with the torso, as the flat sprite does.

## Rebuild

From the mm-data checkout, with the sibling MegaMek checkout:

```powershell
.\tools\build_unit_models.ps1 -Preview
```

Pass `-MegaMekRoot` and `-Blender` if the checkouts or executable are elsewhere.
The equivalent portable steps are:

```text
# In the MegaMek checkout:
./gradlew :megamek:exportMekModelCatalog
# In the mm-data checkout:
blender --background --factory-startup --python-exit-code 1 --python tools/build_unit_models.py -- --preview
python tools/validate_unit_models.py
```

`MekModelCatalog` calls the actual `MekFileParser`, equipment types and
`MekTileset` resolver. There is no second MTF parser or duplicate game-rule model.
Its generated input is `.work/mek-models/catalog.json`. The build has no external
Python package dependency. Run without `--preview` for a faster asset-only build.
The PowerShell command uses Blender's Python for validation too.
The Blender build also rejects intersecting transport/trooper surfaces in every
formation, so changing vehicle dimensions requires adjusting its layout too.

`--preview` also writes `.work/mek-models/review/unit-models.blend`, `preview.png`,
`front.png`, `side.png`, and `top.png`. The four orthographic views show the actual
generated geometry. Append its `MegaMek silhouette review` scene to the running
Blender instance; existing scenes remain separate. The file includes both sprite
and illustration image references and rigid joint parents. The `.blend` is a
derived review artifact: edit `tools/unit_mek_chassis.py` and the socket recipe
to keep changes across regeneration.

To inspect every loadout of selected chassis, render labeled contact sheets
directly from the exported G3DJ meshes:

```text
blender --background --factory-startup --python-exit-code 1 --python tools/render_unit_variants.py -- --chassis warhammer mad-cat
```

This writes `warhammer.png` (33 variants), `mad-cat.png` (20 variants), compact
JPEG copies, `variants.blend`, and `gallery.json` under `.work/mek-models/variants`. The JSON
records the exact asset hashes, triangle counts and equipment behind each image.
The renderer checks mesh hashes/counts and requires every catalogued variant of
each requested chassis to exist before rendering it.
Add `--bare` to render just the shared bodies, without any equipment modules;
these previews default to `.work/mek-models/bare-chassis`.
Add `--turn 60` to either sheet to show every upper body turned one hexside to
its right, which is how the game shows a torso twist.

Add `--infantry` instead to review all infantry movement types and the 3/4/5/6-slot
transport compositions. This writes `infantry.png`, `infantry-counts.png`, JPEG
copies, `gallery.json`, and `infantry.blend` to `.work/mek-models/infantry`. The jump
formation faces backward in the overview to expose the packs. All views import
the exported game meshes and check their hashes and triangle counts.

## Add a chassis

1. Choose a chassis from `chassis-queue.json` and its actual sprite/variant.
2. Add a record to `tools/unit-models/chassis.json`, including a proper chassis
   illustration and the silhouette features to preserve. Author its anatomy in
   `tools/unit_mek_chassis.py` using a small number of polygon sections; do not
   extrude a top-view mask and guess a common humanoid body. Leave guns and
   launchers for the equipment pass. Define joints and socket positions.
   `socketBanks` provides explicit multiple mounts; `missileSockets` supports
   high shoulder pods, `missileColumns` their proportions, and `rearSockets`
   rear weapons. Multiple shoulder launchers stack within `missileBayHeight`,
   using their actual housing dimensions so they cannot intersect one another.
3. Run the build and inspect front, side, three-quarter and top views against
   both references. Check joints/feet for gaps and inspect the silhouette before
   spending triangles on detail. Every
   catalogued variant of the chassis assembles automatically. Unsupported
   equipment and triangle overflow are reported in `needsReview`; they are not
   silently dropped from a purportedly complete variant.
4. Add the fourth field to that chassis's existing mekset entry and run the
   validator and `:megamek:gpuBoardSmoke --tests '*GpuUnitModelsSmokeTest'`.

This generator currently authors biped chassis. Quad/tripod fallbacks are
provided, but distinct quad/tripod anatomy needs an authored construction path
before those entries are promoted from the queue. Missing anatomy should never
be represented as a completed chassis just to increase the coverage count.

## Coordinates and verification

G3DJ is Z-up, facing +Y. X/Y are sprite pixels centered at (42, 36); vertical
authoring coordinates divide by 54 at export. The board applies its existing
unit-footprint and occupied-height scales. Geometry has flat normals, indexed
triangles, vertex colors and separate paint/detail materials. No textures,
negative scales, external mesh dependencies, or runtime geometry generation are
needed for authored units. Meshes are owned/cached by the GPU view and disposed
when the view closes; instances own their paint tint.

The validator checks hashes, finite vertices, normal lengths, triangle area and
winding, indices, node/part references, budgets, descriptor dependencies, and
one-to-one correspondence with every exported external equipment mount, including
location, rear flag, rack size and equipment identity. It also checks infantry
slot composition and the total triangles contributed by its source components.
The native smoke test
loads the entire generated mesh catalog with libGDX, checks its triangle counts,
resolves every infantry movement/count combination, renders both camera views,
and exercises missing assets and empty formations.

Artwork uses MegaMek Data's existing sprites and chassis illustrations as
references. Retain the repository's asset terms and existing BattleTech notices;
refer to LICENSE, illustration credits, and sprite credits in `mekset.txt`.
