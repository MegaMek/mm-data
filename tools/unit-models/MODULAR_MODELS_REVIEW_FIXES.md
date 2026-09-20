# Modular models: review corrections

Date: 2026-09-20. The [main plan](MODULAR_MODELS_PLAN.md) remains the active checklist.
This closes R1–R5 from the [implementation review](MODULAR_MODELS_REVIEW.md), not the entire model plan.

## Corrections

| Finding | Implemented correction | Regression evidence |
|---|---|---|
| R1: duplicate capital-fighter guns | Shared equipment capture classifies generated `isWeaponGroup()` mounts as logical members, with no aggregate housing/fallback. | One real laser plus its rules group produces one drawable gun, including zero/destroyed groups. |
| R2: wrong squadron guns | Game-owned Aero/LAM group location normalization is shared with physical membership resolution. The server captures `(owner entity ID, equipment index)` pairs once in `ResolvedAttack`. `UnitAttack.fires()` is the one selector for recoil and effects. | Mixed fighters carry laser/PPC in reversed index order. Only the correct lasers resolve; FCS loss and empty groups exclude members. Captured membership stays immutable. Nested mount identities survive the actual network serialization filter. |
| R3: premature movement completion | Posture transitions reserve their own interval after arrival in `UnitMotion`. The animator samples their pose directly, including the final waypoint. Formation settling also belongs to this timeline. The real-time completion hold starts afterward. | A terminal fall reaches 45 degrees halfway through its pose interval and 90 degrees before the full one-second hold, at every non-Instant speed. Intermediate fall/get-up cues, group landing/settling and Instant cleanup are covered. Native Atlas crouch, fall and recovery sequences were reviewed. |
| R4: current formation used for queued boarding | The transport predicate accepts the queued movement's captured `BoardScene.Unit`. Completion evaluates the final captured pose in queue order, including Instant playback; clearing a board discards the old queue without rebuilding old models. | A later formation cannot change an earlier movement's boarding decision. Native motorized/wheeled/tracked/hover fixtures cover one/two initial vehicles, bends, return travel, casualty reduction to one vehicle, and matching normal/Instant final member placements and headings. |
| R5: rear recoil points toward the muzzle | Recoil is opposite the authored emitter direction, converted into the attachment parent's local space. The calculation uses the rest assembly, so recoil never accumulates. | Front, side, rear and oblique mounts under a rotated, nonuniformly scaled parent all move opposite the barrel and return exactly to rest. |

The Aero/LAM/squadron extraction preserves the existing group-count rules. It does not introduce another weapon
classifier, client-side combat resolution, or inferred fighter equipment indices. Physical group identities are
presentation data captured by the server; they are not another authoritative game loadout.

## Playback follow-through

- `POSTURE_SECONDS = 0.4` and `FORMATION_SETTLE_SECONDS = 0.3` are animation-clock durations. The existing
  `COMPLETION_HOLD_SECONDS = 1` remains real time. A slow fall receives its full pose interval before that hold.
- Normal and skipped movement use the same completion callback and pose evaluator. This matters when several
  queued transport moves change approach direction or lose troops/vehicles before the renderer catches up.
- The native transport matrix checks passengers remain hidden through driving/parking and vehicles remain
  stationary throughout unloading. Final survivors are visible; obsolete vehicle/member slots disappear.
- The blue-flame/smoke integration continues sampling delayed members after the group root lands. Per-member
  exhaust already uses the shared group timeline; the board must not stop sampling it at the root's landing.
- Pause/Resume freezes the same playback clock and the completion hold. The board freezes pose/hover/rotor time
  along with it; muzzle effects and smoke already sample that clock. Instant bypasses pause. Timing regressions
  and the actual Scene2D button/caption test pass. A queued or paused fall uses its captured starting posture,
  so its final prone state cannot appear before playback begins.
- Equipment hiding LoD is recorded as policy only. No distance-based equipment hiding, substitute body mesh,
  billboard or extra chassis/variant mesh was implemented here.

## Verification

Whole-source main/test compilation and both Java style gates passed. The final focused rerun passed 45 tests,
including the paused/queued starting-pose regression. Earlier full-source runs also passed the four
`WeaponPlaybackTest` cases, the native modular-model suite, the expanded native playback suite (including eight
motive/formation combinations), and the native toolbar/input/layout review. The last focused compile included the
current shared `BoardScene` alongside `UnitPlayback` while another task was updating movement overlays.

Native posture samples are retained in [references/reviews/review-fixes](references/reviews/review-fixes/).
`forced-004.png` is the half-fall pose, `forced-008.png` is the completed fall, and `none-008.png` is the completed
get-up. These use production meshes, assembly, placement and animation code, without Blender or a new asset bake.

Relevant test entry points: `UnitModelStateTest`, `WeaponGroupMembersTest`, `ResolvedAttackPacketTest`,
`ResolvedAttackServerTest`, `WeaponPlaybackTest`, `UnitAnimatorTest`, `UnitMotionTest`, `UnitGroupMotionTest`,
`UnitPlaybackTest`, `GpuModularUnitModelsSmokeTest` and `GpuPlaybackSmokeTest`.

Runs used isolated build/cache directories to avoid other workspace tasks replacing outputs. Existing staged
data was reused; this is not a clean-package verification or a full-battlefield performance claim. No mesh detail
or polygon budget changed. The remaining C6–C9 gates are still tracked in the main plan.
