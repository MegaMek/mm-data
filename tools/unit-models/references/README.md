# Unit model references

These assets are visual references, outside the deployed `data/` tree. The game uses the dynamic descriptors and reusable components in `data/models/units/modular/`.

- `legacy/units/`: the original shipped bodies, 188 baked Mek loadouts, infantry poses/transports/formations, fallback bodies and their original manifest. Files and historical hashes are preserved.
- `verification/modular-models-baseline`, `modular-models-legacy-after-c1`, `modular-models-legacy-after-c2`: the previous `.work/modular-models` verification exports, moved here without changing their content.
- `verification/modular-models-compatibility`: the old coordinate-compatibility fixture.
- `verification/mek-models-infantry-verification`: the old baked infantry verification fixtures.
- `generated/`: optional output from the legacy reference builder. It cannot write into deployed `data/`.
- `equipment-library/`: superseded generated weapon modules, archived by the modular exporter. Explicitly referenced
  canonical overrides and custom filenames stay in the deployed library. The first cleanup moved 118 files.

`tools/render_unit_variants.py` reads `legacy/units/` to inspect the frozen visual targets. Current assembly reviews use Java's production `MekVisual` and `GpuUnitModels`, including custom loadouts. The legacy manifest's source hashes describe the historical build, not the evolving current authoring scripts.
