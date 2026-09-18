# 3D board assets

This directory is the libGDX board's independent art source. Runtime never reads
terrain or water from the 2D board's images directory. The Java build stages this
directory with the game's data. Blender is an authoring dependency only.

## Contents and editing

- `tileset/saxarba.tileset`: the forced 3D tileset, with all recursive includes
  and referenced images, including references outside the Saxarba subdirectory.
  The 7,269 files are independent copies. Edit these without affecting 2D.
- `buildings/`: 3,295 structure models with roofs derived from the exact selected
  tile image. Simplified outlines retain diagonal walls, curves, disconnected
  parts and courtyards; no runtime pixel extrusion or generic substitutions.
- `building-manifest.json`: each structure's source, facade family, wall tint,
  outline, vertex and triangle counts. The largest has 499 triangles. Fuel tanks
  and industrial structures use their selected Saxarba artwork too; generic
  cylinder/factory substitutes have been removed.
- `bridge`, `field`, sixteen foliage and six rock G3DJ
  files, all at or below 480 triangles. Rocks use 70–150 triangles. Counts and
  the imported Blender source names are in `manifest.json`.
- `textures/foliage/`: eight shared 64 by 64 detail albedos for broad leaves,
  pine needles, hanging willow leaves, palm fronds, ordinary bark, birch bark,
  ringed palm bark and snow. Source material boundaries keep snow caps separate
  from green foliage and preserve the birch's pale trunk and dark scars. Existing
  vertex colors tint the pale maps; dominant-axis UVs follow the tree's original
  proportions. Snow variants use their own authored geometry. Texture generation
  prompts are recorded in `tools/board-foliage-texture-prompts.json`.
- `textures/buildings/`: 128 by 128 runtime facade maps. Light buildings retain
  windows; medium uses concrete, hard reinforced concrete, and heavy armored
  panels. Fortresses/gun emplacements use massive sci-fi walls, hangars use
  large shutter bays, fuel tanks use metal courses, and industry uses service
  panels/vents. Sealed structures and dropships use closed armored panels.
  Source names select the family; opaque roof colors tint each model's walls.
  Ordinary facade courses repeat once per four stories. Hangar doors and
  fortress buttresses span the full height instead of stacking per story.
  Eight light-building windows span 128 world units; other families have fewer,
  larger structural bays at that width.
- `textures/terrain/`: 128 by 128 runtime concrete, dirt, rock and sand maps,
  repeating once per 96 world units. Both texture directories have a
  `full-resolution/` subdirectory containing the untouched editable originals.
  Models and materials reference only the small runtime versions. Rebuild those
  after editing originals with `tools/prepare_board_textures.py`.
- `textures/bed.png`: a 128 by 128 silt, sand and pebble riverbed albedo;
  water reflections and animation remain in the separate water surface.
- `textures/*-rim.png`: six 128 by 128 pale material-detail maps for grass,
  dirt, sand, rock, concrete and snow. Runtime tints them from the selected
  Saxarba ground artwork, preserving each theme's palette. An irregular mesh
  edge fades into the geology; fixed world-scale UVs crop the texture on short
  walls instead of stretching it to fit. Model rebuilds preserve these maps.
- Animated water comes from this directory's own `tileset/saxarba/anim_water_N.gif`.
  The renderer constructs curved banks and actual depth; the static
  `Structured_Water` art is a shoreline reference, not a baked replacement.
  Two nonadjacent water openings form a continuous channel. Elevation drops
  use vertically scrolling, animated water on the waterfall face.
- Exposed top edges reuse the single south-facing `08` patches under
  `tileset/High_Incline/`, oriented per edge. Edit these to change cliff-top
  detail without affecting 2D. The renderer avoids mixing their baked lighting
  with the brighter north-facing variants and leaves road approaches open.

Edit roof art under `tileset/`, then rebuild the derived roof texture and mesh.
Opaque source roof pixels and their UV locations are unchanged by the export;
RGB is extended only outside the roof mask to prevent filtering fringes.
`buildings/*-roof.png` is generated output. Edit the facade originals under
`textures/buildings/full-resolution/` to change windows/walls. Edit
`tools/building-footprints.json` between preparation
and export to author a silhouette manually.

Models are indexed G3DJ with positions, flat normals, vertex colors and UVs.
Z is up; X/Y use the 84 by 72 pixel hex dimensions. Local height one scales to
the game's feature height. Bridge decks sit at local Z=0, with rails above and
girders below. Textures and meshes are shared; translucency changes instance
materials, not the assets. Snow trees have their own snow geometry/materials.
The 36-triangle bridge arm samples `tileset/saxarba/bridges/bridge_09.png`.
Deck and rail tops retain the source artwork's layout, while vertical rail and
fascia faces unwrap its guardrail strip, including bars and supports. Edit that
independent image to change the bridge. There is no transverse coping over the
roadway. Runtime places the deck slightly
above the riverbank to avoid coplanar depth flicker at zero bridge elevation.
Rubble rock footprints are at most 12 units wide before instance scaling;
placement limits their height to 0.16–0.265 of a level. Snow rubble uses the
pack's snow-covered rock geometry and materials.

## Rebuild

Run from the mm-data root (Python requires Pillow):

```text
python tools/copy_board_tileset.py
python tools/prepare_board_textures.py
python tools/prepare_building_footprints.py
blender --background tools/board-assets.blend --python tools/build_saxarba_buildings.py
blender --background tools/board-assets.blend --python tools/build_board_assets.py
python tools/validate_board_assets.py
```

The copy step copies missing files only; it preserves local 3D artwork edits.
It repairs two pre-existing fungus image-path typos in the copy only.
Preparation follows actual building, fuel-tank and industrial entries in the
independent include tree. Family selection lives in `facade_family` in the
preparation script; it recognizes named fortress/hangar/sealed families before
ordinary construction strength, including reinforced SMV structures.
Blender uses constrained triangulation for the simplified roof outlines,
exports runtime files, and saves editable object libraries at
`tools/saxarba-buildings.blend` and `tools/board-assets.blend`.
Use Blender's Append command to load their objects. The source scripts create
their own scenes and do not replace the user's open scene.

The nature pack must be present at
`TO_SORT/many_trees/Ultimate Nature Pack - Jun 2019/Blends` to rebuild foliage
and rubble. These sources match the user's Quaternius ZIP;
runtime does not need that folder. Export converts Blender's linear colors to
display-space vertex colors, preserving the green/snow material distinction.

Validation checks all 3,319 model budgets and texture dependencies, structure
roof winding, unchanged opaque roof pixels, facade assignments, small runtime
texture dimensions, preserved source resolution, and independent copied files.
Native Java integration tests additionally check transparency, lighting,
water animation and representative model loading.

## Provenance

Roof/terrain/water art comes from the existing MegaMek data tileset; its license
headers and original paths are retained. The repository license remains at
`../../../LICENSE`.

Trees and rocks are simplified derivatives of Quaternius's **Ultimate Nature
Pack (June 2019)**: `CommonTree_1/2/4`, `PineTree_1/3`, `BirchTree_2`,
`Willow_2`, their corresponding snow models, `PalmTree_1/2`, and
`Rock_1/3/6` with their snow models. The supplied CC0 notice is preserved
in `QUATERNIUS-LICENSE.txt`.

Bridge and crop models were authored with the Blender script.
Dirt, sandstone, rock, concrete and windowed facade albedos were generated with
the built-in image_gen tool; exact prompts are in
`../../../tools/board-texture-prompts.json`. The seven contextual facade prompts
are in `../../../tools/building-texture-prompts.json`; these also used built-in
image_gen. Bed and rim art also use built-in image_gen; their prompts and
references are in `../../../tools/board-rim-texture-prompts.json`. Only the
128 by 128 runtime maps are shipped. The rim maps are pale detail albedos;
their final theme colors come from the hex artwork, and geometry supplies
their uneven lower silhouette.
