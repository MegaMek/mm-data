# Unit LoD: assessment and experiment proposal

Date: 2026-09-20. Status: equipment-hiding policy selected; runtime implementation and benchmark remain deferred.
No game code, runtime settings or deployed assets were changed for this assessment.
The [main implementation plan](MODULAR_MODELS_PLAN.md) remains the active checkpoint list.

Decision: keep the unit mesh unchanged and use progressive equipment hiding for LoD. The alternatives below remain
historical comparison material, not competing implementation choices. The user requested documentation only for
LoD at this stage and continuation of the existing modular-model completion work.

## Recommendation

Start with **the actual body at every normal board zoom, selective removal of unreadable details, and real 3D
shadows**. Preserve large loadout shapes. Measure this before adding replacement geometry or impostors.

This requires no additional mesh per chassis or variant. It also avoids changing an Atlas into a generic biped
when zooming out. Weapons are sometimes part of the recognizable silhouette: Warhammer arm cannons and Mad Cat
launcher pods must not all disappear merely because they belong to the loadout.

Two rendering levels are enough for the first experiment: full detail and reduced details with the same silhouette.
A third, extreme-distance representation is justified only if the measured result still requires it.

## Evidence inspected

The task [Optimize tree geometry and LoD](codex://threads/01a0bb82-f141-7f50-b428-7667e0faf482) and its current code
use three levels, screen-pixel thresholds and 10% hysteresis. The thresholds are 80 and 24 framebuffer pixels;
they are tree-specific and should not be copied blindly to units. Both board views use an orthographic camera,
so geometric distance from the camera is not a useful proxy for how small a unit looks.

The tree implementation also preserves picking and uses its selected geometry in shadow rendering. Reuse these
principles and any identical pixel-scale calculation. Moving modular units need their own small policy; they should
not be forced through tree asset naming or a new general LoD framework.

Read-only counts from the current deployed component files:

| Bare asset | Triangles | Mesh parts |
|---|---:|---:|
| Atlas | 421 | 23 |
| Warhammer | 282 | 19 |
| Mad Cat | 512 | 20 |
| Locust | 288 | 15 |
| One standing Battle Armor figure | 214 | 14 |
| One standing conventional infantry figure | 158 | 14 |

These are asset counts, not measured per-frame draw calls. Actual assemblies can change parts through anatomy,
equipment, damage and pose. Six copies of a 14-part figure illustrate why entity count and triangle count alone
are insufficient cost estimates.

`GpuBattleView` evaluates authored unit poses before its main-pass frustum rejection. `GpuTerrain.renderShadows`
compares unit transforms, node poses and enabled parts; changes can cause a full shadow pass. Idle troop motion
and airborne wobble therefore deserve measurement alongside geometry. This is a cost hypothesis, not a measured
bottleneck or a reason to remove those animations.

The [earlier C0 component probe](MODULAR_MODELS_C0.md#draw-cost-prototype) measured 4,352 draw calls for 256 bare
legacy Warhammers and 7,424 with twelve box modules each. It excluded terrain, shadows, camo, animation and effects.
Those historical numbers cannot be presented as current full-board performance. They do establish that component
submission deserves attention: libGDX's `ModelBatch` sorts/manages render calls but does not merge them automatically.
[Official ModelBatch documentation](https://libgdx.com/wiki/graphics/3d/modelbatch).

## Options

| Option | Visual consequence | Shadows / maintenance | Assessment |
|---|---|---|---|
| One generic distant shape per family | Chassis outline, proportions and loadout can change visibly at the switch. | Easy 3D shadows; few assets. | Avoid for identifiable units at normal board zoom. Keep existing generic bodies for units without authored art. |
| Hide every loadout module | Body remains recognizable in some cases; gun arms, pods and physical weapons disappear in others. | Easy 3D shadows; no new assets. | Useful only as an aggressive cost-bound experiment, not the preferred delivered result. |
| Preserve body and major equipment; cull tiny fittings | Maintains recognizable mass and outline. | Uses existing meshes and shadow casting. | Preferred first candidate. |
| Flat billboard | Low geometry, but view changes, poses, damage, camo and dynamic loadouts complicate matching. | A camera-facing quad alone is not the unit's 3D shadow volume. | Reserve for extreme overview only if profiling justifies it. |
| View-dependent impostor with 3D shadow proxy | Can preserve a distant outline better than a generic body. | Requires capture/baking, bounded texture/cache ownership, invalidation and a shadow representation. | Possible later; not the simplest first step for this dynamic assembly system. |
| Automatically simplified reusable components | Preserves the selected body's identity better than family replacement if silhouette/rig boundaries survive. | Additional component data and validation, but no baked loadout cross-product. | Consider only if triangle cost proves important and component LoDs are acceptable. |

An impostor need not be pre-authored for every variant: an actual assembled unit could be captured on demand.
However, pose, turret/torso orientation, camo, lost limbs, troop casualties and loadout changes invalidate captures.
The texture and shadow costs remain. Multi-view impostors are a real option, not equivalent to a free two-triangle
substitute; see [Epic's impostor documentation](https://dev.epicgames.com/documentation/en-us/unreal-engine/impostor-baker-plugin-in-unreal-engine).

## Rules for the first candidate

- Derive detail from projected framebuffer size, accounting for zoom, display scale, real unit scale and large-unit
  footprint. A distant-looking Union may still cover many pixels and deserve full detail. Use stable full bounds,
  not bounds already reduced by LoD, to avoid feedback and switching loops.
- Keep the actual body and silhouette-defining equipment. Cull only details below a tested pixel contribution
  threshold. Start by testing roughly 1–2 pixel details, not adopting that value as a final specification.
  A conservative importance override belongs on the reusable component/attachment metadata if needed, not in a
  per-chassis or per-variant renderer exception list.
- Use hysteresis, as with trees. If a change is still visible in slow zoom/orbit tests, preserve it longer or test
  a short dither transition. Avoid adding blending and duplicated rendering before demonstrating a visible need.
- Keep real 3D body/major-equipment shadow casters. Start with the same reduced component selection in color and
  depth passes. A small visible part can cast a long shadow in low sun, so validate light directions as well as
  camera angles. Shadow-specific simplification needs its own evidence; a billboard should not replace the caster.
- Compute selection once and use it consistently in the relevant passes. Combine LoD eligibility with actual
  damage/visibility; never overwrite destroyed/removed state to restore detail on zoom-in. Do not mutate shared
  asset parts or remove mounts/emitters from the authoritative loadout snapshot.
- Keep full footprint/picking and gameplay information independent of visual detail. Preserve living troop count,
  member positions and transport composition. LoD must not look like casualties or toggle BA compression.
- Keep movement/attack events and their clock authoritative. If CPU pose work is expensive, first test less frequent
  distant *idle* posing. Active walking/jumping/boarding/attacks require smooth motion, correct emitter placement and
  the established foot-contact behavior. Pose evaluation frequency is not animation speed.
- Keep selected/inspected and actively firing units detailed enough for readable feedback without using those
  exceptions to conceal poor transitions elsewhere. Unknown/sensor-only units must remain unknown.

## Dense-battlefield experiment

Use an isolated native review harness or existing debug fixtures. Candidate changes stay outside production game
code until the visual/performance comparison supports a choice. Use real Java runtime assemblies and loadouts;
the old box-module benchmark alone cannot choose unit LoD.

### Scenes

1. **36 versus 36 game units** as an initial battalion-sized fixture, with a Mek-heavy roster.
2. The same entity count with mixed Meks, six-member BA, conventional foot/motorized/mechanized infantry, vehicles,
   VTOLs and one or two large Aero units. Record rendered member counts as well as Entity counts.
3. **108 versus 108** and then **512 total units** as stress cases. These are explicit test sizes, not assumptions
   that every faction or unit family has the same battalion organization.
4. Run open-ground and wooded versions with fixed seeds, identical tree LoD, camo/material diversity, terrain,
   lighting, shadows and HUD. Keep duplicate-loadout and diverse/custom-loadout cases separate.

### Candidates and isolation

| Run | Change from baseline | What it establishes |
|---|---|---|
| A | None: full bodies/equipment/current animation and shadows. | Current frame and visual reference. |
| B | Hide only unreadable, nonessential components; preserve silhouettes and shadows. | Value and visible cost of the preferred simple policy. |
| C | Hide all external equipment, retain 3D body shadows. | Aggressive upper bound for equipment-removal savings and a visual counterexample. Not the intended result. |
| D | Keep A geometry, reduce only distant idle pose updates. | Whether pose/shadow invalidation work matters more than triangles. |

Only combine B and D after their independent results are known. If they are insufficient, the measured bottleneck
chooses the next experiment: compatible rigid-part batching for submission cost, automatic component simplification
for geometry cost, or impostors for an extreme overview. A frozen/merged proxy can reduce calls but adds buffers,
memory and pose invalidation; it is not a free optimization or a second runtime assembler.

### Measurements and visual gates

- Record hardware, driver, resolution/framebuffer scale and background GPU activity. Warm up, repeat each run and
  report median/p95/p99 frame time, not one FPS observation. Measure the actual device resolution and a higher-DPI
  case. Diagnose CPU pose/submission, GPU color/depth, draw calls, triangles, shadow redraw frequency, allocations,
  load time and resident memory separately where instrumentation permits.
- Test overview, middle and near zoom in both board views, with slow zoom/orbit through transition thresholds.
  Include repeated threshold crossings to expose flicker, and a camera pan exposing/offscreening many units.
- Include idle, movement with infantry boarding and BA jumps, firing/physical attacks, damage/limb removal,
  casualties, refits, reveals, pause/Instant and large-unit takeoff/landing. Use legitimate playback patterns plus
  a separate synthetic active-animation stress case; do not imply all 512 units normally attack simultaneously.
- Review native side-by-side frames and short clips at actual display size. Atlas head/shoulders, Warhammer gun
  arms and Mad Cat pods must retain their identity. Check full-footprint selection, camo, facing/twist and casualty
  counts. Check shadows over slopes and raised terrain at different light angles for popping or detachment.
- Accept the simplest candidate that meets an agreed full-board frame budget with preserved silhouettes, smooth
  transitions, correct state and intact shadows. If baseline already meets the budget, keep the evidence and avoid
  adding distant mesh assets without a demonstrated need.

## Current conclusion

Selective detail reduction with the real body and large equipment retained is the best first hypothesis. Generic
unit replacements would trade away identity, and impostors introduce substantial dynamic-appearance work. The
dense mixed-unit benchmark above is still **to be run**; no new performance improvement is claimed by this study.
