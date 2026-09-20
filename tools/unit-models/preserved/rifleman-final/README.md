# Rifleman - final

The accepted Rifleman, signed off on 2026-09-20 with no outstanding changes. This is the reference
copy: if `tools/unit_mek_chassis.py` is ever overwritten, restore from here rather than re-deriving
the body from the references.

674 triangles. Sixty tons, measured height 53.0, inside the heavy band.

## What this version settles

| Feature | Decision |
|---|---|
| Head | Runs the full centre torso: chin squared off at z 31.5, cockpit standing 4.5 clear of the chest at y 11, crown falling back to y 4.5 into the antenna mast |
| Viewport | Tall rectangle, 2.8 across by 8 high, stopping 1.3 above the chin so armour closes under it as a frame |
| Garret T11-A array | Centred on the head, not on a shoulder. The overhead sprite puts it off to one side; the miniature wins |
| Vents | Left and right torso, following the heat sinks - 25 located sinks in LT and 24 in RT against 5 in CT across all variants |
| Shoulders | Stop at x 12.75, exactly where the arm pods begin, so a flipped arm never sweeps through them |
| Arm pods | x 12.75 to 21.25, no hand or lower arm on any of the 26 variants |
| Torso seam | Declared at 4.2 rather than derived, so LT and RT own their own armour |

## Why the shoulders stop where they do

The arms flip. An arm flip turns each pod about its shoulder's left-right axis, which never changes
x, so a pod that is flush with the shoulder at rest stays flush through the whole half turn. Burying
the pod in the shoulder - which is what every other chassis in this set still does - makes the arm
sweep through solid armour halfway over.

Reducing the shoulder from `x 3.5..18.5` to `x 3.25..12.75` did not change the overall width. The
pod still ends at 21.25; only the seam between the two moved.

## Files

| File | What it is |
|---|---|
| `body.py` | the `rifleman(g)` function from `tools/unit_mek_chassis.py` |
| `recipe.json` | the `rifleman` entry from `tools/unit-models/chassis.json`, expanded for readability |
| `rifleman.g3dj` | the exported mesh |
| `rifleman-body.json` | the exported body descriptor |
| `rifleman-descriptor.json` | the exported mek descriptor |
| `final-six-view.png` | bare body, six angles |
| `final-assembled-3N.png` | RFL-3N assembled with weapons, six angles |
| `final-variants.png` | all 26 variants |
| `final-arm-flip.gif` | the arm flip sweep, 15 degrees a frame |

## Restoring it

1. Replace the `rifleman(g)` function in `tools/unit_mek_chassis.py` with `body.py`.
2. Replace the `rifleman` entry in `tools/unit-models/chassis.json` with `recipe.json`, **reformatted
   to the file's compact one-key-per-line style**. Do not paste the indented form; it will not match
   the surrounding entries.
3. `python tools/build_modular_unit_models.py`
4. Confirm `bodies/rifleman` reports 674 triangles in `manifest.json`.

The exported files here are a cross-check, not an install target: the exporter rewrites them from the
Python source, so restoring the source is what matters.

The earlier accepted body is kept alongside this one in `../rifleman-mk1/`.
