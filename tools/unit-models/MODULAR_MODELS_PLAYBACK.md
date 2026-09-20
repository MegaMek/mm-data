# Movement and attack playback

Playback foundation implemented and reviewed on 2026-09-19. This extends C6/C8 of
[the model plan](MODULAR_MODELS_PLAN.md); their broader family/terrain/death gates remain open.
The [2026-09-20 review corrections](MODULAR_MODELS_REVIEW_FIXES.md) fix grouped-weapon identity, recoil direction,
terminal posture timing and captured/Instant transport arrivals. Use that evidence with the active plan checklist.

## Requested behavior

- Normal playback runs the animation clock at half its previous rate. Controls are 0.5x, 1x, 2x, 4x and Instant.
- Travel time depends on distance, turns and climbs. A four-hex walk is the reference for the slower normal pace.
- Use the unit's game-calculated movement capability, with named lower/upper speed limits for extreme units.
- All movement accelerates and brakes smoothly, once per uninterrupted travel block rather than once per hex.
- Movement, gait, troop boarding/parking/unloading, gear, attacks and effects share playback timing.
- Foot/jump formations use configurable start-time jitter. Each troop keeps its normal travel time and its own
  pose, jet flame, smoke, landing and outward settling. Waiting troops remain grounded. The group completes
  after the delayed members finish. Stable unit/member/event seeds prevent frame-rate or camera changes from
  rerolling timing. A single visible figure receives no group jitter. Vehicle passengers keep their existing
  staggered boarding and may emerge only after parking has finished.
- After each completed movement or attack, hold the completed pose for one second before the next event.
  This is a named constant and a wall-clock hold; Instant bypasses animation and the hold.
- Pause/Resume freezes movement, pose, effects and that hold together. Instant bypasses pause. Captured starting
  poses remain visible while events wait; a queued fall cannot display its final fallen pose early.
- Implement actual firing and Mek punch/kick/push/physical-weapon playback from resolved, visibility-filtered
  outcomes. Declaration arrows are not firing events. Never infer hits from report text or change game results.

## Checkpoints

- [x] Distance/capability-based movement, bounded speed and ordered speed controls; meaningful timing tests.
- [x] Shared event completion hold, queue order, cancellation and Instant behavior.
- [x] Typed resolved firing/physical events from server through visibility filtering to client snapshots.
- [x] Authored emitter VFX/recoil and basic Mek physical clips, with confirmed outcomes and recovery.
- [x] Native movement/attack review, bounded cleanup/skip tests, documentation and focused quality review.
- [x] Repeat whole-workspace compilation after the concurrent board-marker refactor compiles together (2026-09-20, during the searchlight regression fix).

Review each checkpoint for shared authority, event order, visibility, transform/resource ownership and regressions.
Do not mark an event contract or a static screenshot as complete attack playback.

## Settings and ownership

| Setting | Value | Meaning |
|---|---:|---|
| `UnitMotion.GROUP_START_JITTER_SECONDS` | `0.16` | Maximum troop start delay in animation-clock seconds; **0 disables jitter**. Up to 0.32 real seconds at 1x. |
| `UnitPlayback.COMPLETION_HOLD_SECONDS` | `1` | Real seconds after finished movement/attack recovery; independent of speed; Instant skips it. |
| `UnitMotion.MIN_UNIT_SPEED` / `MAX_UNIT_SPEED` | `0.65` / `2.5` | Clamp movement capability's influence relative to the 4-MP reference. |
| `UnitMotion.RAMP_SECONDS` | `0.2` | Animation-clock acceleration/braking interval; shortened for very brief movement. |
| `UnitMotion.BOARD_SECONDS` / `UNLOAD_SECONDS` | `0.45` / `0.6` | Fixed group-level phases added to travel, never charged per soldier. |
| `UnitMotion.LANDING_GEAR_SECONDS` | `0.45` | Added per retraction/extension transition. |
| `UnitMotion.POSTURE_SECONDS` | `0.4` | Full posture interval after the corresponding waypoint is reached, before the completion hold. |
| `UnitMotion.FORMATION_SETTLE_SECONDS` | `0.3` | Arrival orientation/pose recovery after the last walking/jumping member lands, before the completion hold. |

Normal playback advances the animation clock at 0.5 seconds per real second. At 4 MP, a straight four-hex walk
takes 2.8 real seconds, then the 1-second hold. At 3 MP it takes about 3.6 seconds; at 12 or 40 MP the upper clamp
gives 1.36 seconds. These examples exclude boarding, turns, elevation and group jitter. The game's run/sprint MP
already includes the movement mode, so the renderer does not multiply its speed a second time. Aero uses current
velocity rather than thrust for this visual pacing input.

`UnitMotion` owns route interpolation, acceleration, jump height and distance. Delayed troops sample that same
immutable route at an earlier clock value; they do not create extra game entities or advance independent clocks.
Leg cadence converts world travel into each body's scaled local dimensions. Two rigid leg segments follow a
support/return foot trajectory; vehicle wheels use their actual driving/parking distance divided by wheel radius.
`UnitAnimator` evaluates from rest each frame, including recoil cleanup and removal/skip reconciliation.

`UnitPlayback` owns one ordered movement/attack queue for both camera views. It keeps received appearance snapshots
until their event has played, while game/network processing continues. Source and renderer queues are bounded.
`ResolvedAttack` travels from actual server resolution through visibility filtering and the client event boundary.
It contains identity and outcome, never client-computed damage. Captured owner-ID/equipment-index pairs select posed emitters;
missing emitter art has a generic visual fallback. Shot/contact, recovery and the completion hold occur in order.
The extra packet command is appended to preserve existing command ordinals; this feature needs updated clients
and server together.

## Review scope

The native review measures supporting-foot world movement against body travel, and wheel rolling against actual
vehicle travel. It renders Atlas locomotion, all five attack kinds, transported infantry, and a six-suit staggered
BA jump through takeoff, apex, separate landings and settling. The jump review checks actual grounded waiting suits,
per-member nozzle activation, final formation equality and skipping during takeoff.

Earlier review found almost one unit of foot sliding for every unit of Atlas travel. Corrections account for leg
length, asymmetric authored poses, chassis/figure scale and bounded phase seeds. The measured straight, level
support phases then had less than 0.01% foot drift for Atlas, quad, tripod and all tested conventional/BA poses.
Vehicle wheel rolling matched travel to within 0.001% in the parking/reversing fixture. These are fixture results,
not a claim of terrain-aware foot locking or universal animation quality.

## Verification evidence

- **55 tests passed:** 53 focused timing, group jitter, queue, source-boundary, packet/server/weapon-resolution,
  surface and footprint checks; plus the native modular-model review and native playback review.
- Atlas walking/running was measured forward and backward at 3, 12 and 40 MP. Native contact measurements also
  cover quad/tripod fallbacks and all six conventional/BA poses. The group fixture checks grounded waiting suits,
  separate departures/landings, twelve individually timed nozzles, frame-rate independence and Instant cleanup.
- The transport fixture measures two opposite-direction routes, wheel rotation during driving/parking/reversing,
  hidden passengers through parking, and stationary vehicles during unloading. Physical clips and firing effects
  render from production pose/placement code, with mount transforms restored on completion/cancellation.
- Final combined evidence used `.work/playback-evidence.init.gradle` with a private Gradle cache. It compiles the
  current playback/pose/formation/jet/effect sources and tests against a saved, previously compiled board runtime.
  This isolates an unrelated concurrent board-marker refactor. That run was **not** a whole-workspace build:
  its full-source attempt stopped on duplicate `BoardView.captureTacticalGeometry()` definitions. The
  earlier focused event/server tests also passed before that refactor interrupted whole-source compilation.
- On 2026-09-20, complete main/test source compilation passed during the searchlight regression fix, after the
  board-marker refactor compiled together. The 55-test playback result above remains the isolated run's evidence.
- Both Java style gates passed on current sources; compile tasks were excluded for that separate style run
  because of the unrelated duplicate method. Focused diff whitespace checks also passed.
- Native sequences are encoded at normal playback speed and 24 frames/second. They are review artifacts only;
  the game does not invoke the encoding script or use these GIFs as animation assets.

[Six Battle Armor suits with start-time jitter](references/reviews/playback/battle-armor-jitter.gif),
[Atlas walking](references/reviews/playback/atlas-walk.gif),
[infantry boarding/driving/unloading](references/reviews/playback/infantry-transport.gif),
[firing](references/reviews/playback/atlas-fire.gif),
[Mek kick](references/reviews/playback/atlas-kick.gif).

The implementation is concentrated in `UnitMotion`, `UnitPlayback`, `UnitAnimator`, `InfantryMotion`,
`GpuJumpJets`, `GpuMeeple`, `UnitAttack` and `GpuAttackEffects`. `BoardScene`, `GpuBoardSource` and `GpuBattleView`
carry snapshots and connect the shared queue to both views. `ResolvedAttack`, its game event, the packet/client
boundary, `TWGameManager` and weapon handlers carry actual visibility-filtered outcomes. No second game-state
authority or separate per-member timeline was added.

## Remaining limits

Remaining C6/C8 work includes full slope/pivot/strafe contact review, every family/conversion transition, authored
target-aware aiming, specialized bay/artillery/AMS presentation, sound, and death/crash/collapse sequences. Existing
generic effects and rigid physical clips are a working playback foundation. No new geometry, infantry equipment
attachment, external runtime script or physics solver is introduced here.
