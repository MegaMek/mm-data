# Rifleman mk1 - preserved

The reviewed and accepted Rifleman body as it stood on 2026-09-19, before the redraw that follows the
overhead sprite more closely. Nothing in this pipeline was committed, so without this copy the mk1
body would be unrecoverable once its source is overwritten.

550 triangles. Seven review rounds. Accepted by the reviewer with the radar angle approved, legs cut to
60-ton scale, arm pods at 8.0 x 11.8, flush side torso lasers and four vents.

| File | What it is |
|---|---|
| `body.py` | the `rifleman(g)` function from `tools/unit_mek_chassis.py` |
| `recipe.json` | the `rifleman` entry from `tools/unit-models/chassis.json`, expanded for readability |
| `rifleman.g3dj` | the exported mesh |
| `rifleman-body.json` | the exported body descriptor |
| `rifleman-descriptor.json` | the exported mek descriptor |
| `mk1-six-view.png` | bare body, six angles |
| `mk1-assembled-3N.png` | RFL-3N assembled with weapons, six angles |
| `mk1-variants.png` | all 26 variants |

## Restoring it

1. Replace the `rifleman(g)` function in `tools/unit_mek_chassis.py` with `body.py`.
2. Replace the `rifleman` entry in `tools/unit-models/chassis.json` with `recipe.json`, **reformatted
   to the file's compact one-key-per-line style**. Do not paste the indented form; it will not match
   the surrounding entries.
3. `python tools/build_modular_unit_models.py`
4. Confirm `bodies/rifleman` reports 550 triangles in `manifest.json`.

The exported files here are a cross-check, not an install target: the exporter rewrites them from the
Python source, so restoring the source is what matters.
