# Modular models: implementation review

Date: 2026-09-20. Scope: current modular assets, Java assembly/snapshot boundaries and movement/attack playback.

**The plan is not complete.** C0–C5 have useful baseline evidence; C6–C8 have working foundations with incomplete
coverage, and C9 has not passed. This review originally identified the five concrete defects below; their
subsequent corrections and verification are recorded in [the follow-up](MODULAR_MODELS_REVIEW_FIXES.md).
The findings below preserve the original reproduction evidence.

[MODULAR_MODELS_PLAN.md](MODULAR_MODELS_PLAN.md) is the single active checklist. This document records findings
and evidence as of the review date. The checkpoint documents preserve historical verification, not competing
current task status.

## Findings

Follow-up: R1–R5 below are historical findings and have since been corrected. See the
[implementation and verification note](MODULAR_MODELS_REVIEW_FIXES.md) and the main plan for current status.

### R1 — Generated aerospace weapon groups become extra physical guns (P2)

Location: [UnitModelEquipment.java:30](C:/Projects/megamek/megamek_temp/megamek/src/megamek/client/ui/tileset/UnitModelEquipment.java:30),
[UnitModelState.java:100](C:/Projects/megamek/megamek_temp/megamek/src/megamek/client/ui/clientGUI/boardview/gpu/UnitModelState.java:100).

With the capital-fighter rule enabled, the game adds aggregate `WeaponMounted` entries alongside the actual
weapons. Capture classifies only their `EquipmentType`; a generated group has the same weapon type as a real gun.
It consequently reaches assembly with its own index and a drawable weapon policy. The bay/MGA type exclusions
do not handle `Mounted.isWeaponGroup()`.

Reproduction: one actual medium laser plus its generated rules group produces **two drawable weapon snapshots**.
Each has a distinct index, so assembly's index deduplication cannot remove the extra housing. This violates the
equipment baseline and increases hardpoint crowding and geometry unnecessarily.

Small correction: normalize mounted grouping state in the existing shared equipment capture helper. Keep the
group's logical firing membership, but do not give the aggregate mount another housing. Keep equipment type
policy shared between offline tooling and runtime; a second weapon classifier in the renderer would duplicate
the problem.

### R2 — Squadron shots can select the wrong member weapons (P2)

Location: [GpuAttackEffects.java:52](C:/Projects/megamek/megamek_temp/megamek/src/megamek/client/ui/clientGUI/boardview/gpu/GpuAttackEffects.java:52),
[UnitAnimator.java:317](C:/Projects/megamek/megamek_temp/megamek/src/megamek/client/ui/clientGUI/boardview/gpu/UnitAnimator.java:317).
Identity boundary: [SquadronVisual.java:48](C:/Projects/megamek/megamek_temp/megamek/src/megamek/client/ui/clientGUI/boardview/gpu/SquadronVisual.java:48).

Squadron bindings correctly retain each fighter's own equipment index and member ID. Resolved attacks instead
carry the squadron's aggregate equipment index. Firing and recoil compare only the integers and ignore the member
identity. The game's group index is not a child equipment index.

Reproduction with actual game-generated groups: fighter A has laser/PPC, fighter B has PPC/laser. The squadron's
laser group is index 0; index-only child lookup selects **Medium Laser and PPC**. Depending on equipment ordering,
effects can use the wrong weapon/position, or find no appropriate muzzle and fall back to the unit center.

Small correction: resolve the authorized attack to actual constituent member/mount identities at the snapshot
boundary using existing game group membership. Feed that one resolved selection to both recoil and effects.
Do not independently infer groups from names or equipment order in each renderer component. Include bays/MGAs
in the same integration review, without inventing a general event framework.

### R3 — The completion hold starts before a terminal posture animation finishes (P2)

Location: [UnitPlayback.java:94](C:/Projects/megamek/megamek_temp/megamek/src/megamek/client/ui/clientGUI/boardview/gpu/UnitPlayback.java:94),
[UnitMotion.java:503](C:/Projects/megamek/megamek_temp/megamek/src/megamek/client/ui/clientGUI/boardview/gpu/UnitMotion.java:503),
[UnitAnimator.java:157](C:/Projects/megamek/megamek_temp/megamek/src/megamek/client/ui/clientGUI/boardview/gpu/UnitAnimator.java:157).

While moving, sampled posture reads the starting waypoint of the current segment. A fall at the final waypoint
therefore starts in `UnitAnimator` only when route playback ends. At exactly that boundary `UnitPlayback` starts
its one-second real-time hold. The animator independently approaches the fallen pose over 0.4 animation seconds.

Reproduction: a terminal fall followed by a shot at half speed starts the shot while the Mek is only
**56.8° through its 90° fall**. At normal speed the fall still consumes most of the purported post-animation hold.
The queue timing tests pass because they currently measure route completion, not completion of the displayed pose.

Small correction: make terminal posture and arrival recovery part of the shared movement interval, with one
duration/progress source. The hold must start after that interval, including the last staggered member. Test both
intermediate and terminal posture changes, every playback speed and Instant. Do not solve this by lengthening the
hold or adding another timer; those would hide the disagreement instead of removing it.

### R4 — Queued transport movement uses the latest formation to decide boarding (P2)

Location: [UnitPlayback.java:87](C:/Projects/megamek/megamek_temp/megamek/src/megamek/client/ui/clientGUI/boardview/gpu/UnitPlayback.java:87),
[GpuBattleView.java:472](C:/Projects/megamek/megamek_temp/megamek/src/megamek/client/ui/clientGUI/boardview/gpu/GpuBattleView.java:472).

The queued movement retains its captured unit appearance, but its transport predicate looks up the unit in the
latest scene. The renderer evaluates that predicate before applying the queue's historical presentation. A later
casualty/composition update can therefore remove the vehicles used to decide boarding while the old movement still
displays its original formation. The reverse mismatch is also possible when composition gains a vehicle.

A boundary reproduction queues a transport move behind another event, changes the latest transport availability,
then starts that move: its boarding stage disappears. This is a snapshot consistency issue, not a need for a
second survivor or movement rules system.

Small correction: derive transport participation from the same captured unit/formation used by that event, through
the existing composition logic. Avoid looking up an ID in mutable current scene state. Verify mid-queue casualties,
one/two-vehicle changes, consecutive moves and catch-up to the current authoritative game state.

### R5 — Rotated weapons recoil in the wrong direction (P2)

Location: [UnitAnimator.java:322](C:/Projects/megamek/megamek_temp/megamek/src/megamek/client/ui/clientGUI/boardview/gpu/UnitAnimator.java:322).

Recoil translates every attachment along parent-space negative Y. A rear-facing mount is rotated 180° relative
to that parent, so its recoil moves toward the muzzle. Side/angled mounts have the corresponding axis error.

Reproduction: a rear mount at peak recoil has displacement dot barrel direction **+0.9**, whereas backward recoil
requires a negative value. This can be checked without rendering or changing geometry.

Small correction: transform the authored recoil/barrel axis into the attachment parent's space, then displace
opposite it from the rest transform. Reuse existing attachment/emitter transforms. Verify front/rear/rotated sockets
under torso twist and parent scaling; no separate rear-gun animation implementation is needed.

## What remains from the plan

| Checkpoint | Implemented foundation | Remaining work / acceptance |
|---|---|---|
| C0–C5 | Component pipeline, live formations/loadouts, family fallback bodies, large footprints/supports, camouflage, damaged parts and collectable limbs. | Correct R1 and preserve the existing baseline during later changes. Coverage means family fallbacks, not authored art for every chassis. |
| C6 | Shared rigid poses, distance-driven gait/wheels, ramps and bounded speed, airborne wobble, Mek twist/prone, troop headings/jitter, blue jets/smoke and basic physical clips. | R3; explicit family/action coverage; slopes, pivot/strafe and reverse contact; conversion/get-up transitions; target-aware aim/contact; layer/interruption and pause/skip/reveal/load behavior. |
| C7 | Member/vehicle assignment and boarding → driving/parking → stopped unloading, with a native review sequence. | R4; complete wheeled/tracked/hover and one/two-vehicle matrix, bends/reverse/varied arrivals and casualty/removal/queue interruption cases. |
| C8 | Typed visibility-filtered resolved events, basic muzzle effects, hit/miss reactions and Mek physical clips on the shared queue. | R1/R2/R5; specialized grouped/bay/AMS/artillery and ammo/mode presentations; aiming, sound, physical contact/push displacement; family death/crash/collapse/wreck transitions. `ResolvedAttack` currently has no death event. |
| C9 | Reference migration and several focused visual/lifecycle tests. | Real mixed-board 64/256/stress measurements, loading/memory/allocation and disposal/reveal/refit checks, clean staged package review, final authoring examples and a full family/camera acceptance reel. |

The original C6–C8 checkboxes mixed working foundations with their remaining acceptance gates. They have been
split in the active plan so they no longer imply that boarding, firing or troop headings have not been implemented.
The earlier C0 benchmark is a component proxy; it is **not** evidence of mixed-board frame times with terrain,
shadows, varied camo, animation and effects.

Deliberate deferrals remain unchanged: dynamic infantry/BA equipment is evaluated only at the end and may be
omitted; unit distance LoD follows later measurement. A new physics engine, ragdolls, ECS, general animation graph
editor, asset plugin registry or class per concrete Entity is unnecessary for this plan.

## DRY/KISS and one source of truth

The existing composition is a workable foundation. The most useful simplification is to tighten boundaries,
not replace it with a larger framework.

- **Game state:** keep survivors, movement capability, legal facing/footprint, prone cause and combat outcomes in
  existing game/client code. Render snapshots are observations. Fix R4 by using the right observation, not by storing
  a competing troop count in playback.
- **Equipment:** retain `EquipmentModelPolicy`/`UnitModelEquipment` as the shared normalization path. Offline
  catalog and live assembly already share weapon family classification. Extend it for actual mounted groups rather
  than adding a renderer-only exclusion list. Art mappings remain the source for meshes and hardpoint preferences.
- **Playback:** `UnitPlayback` sequences events/holds, `UnitMotion` samples movement, and pose/effects consume those
  intervals. Their separate responsibilities are useful; R3 exposes a duration agreement missing between them.
  Resolve it once, including pause semantics, rather than adding frame-based exceptions to multiple classes.
- **Firing identity:** resolve constituent mount selection once and share it between recoil and VFX. The existing
  member ID on bindings is useful data, not an excuse to reproduce squadron grouping rules in presentation.
- **Family code:** retain the shared `FamilyVisual` plus the few special assemblers. The original proposed
  `UnitVisual`, separate vehicle/aircraft/naval/static classes and a common inheritance tree are not requirements.
  Extract a helper only for actual duplicated behavior, not a few similar lines around distinct anatomy.
- **Resources:** keep immutable GPU assets view-owned and instance transforms/materials unit-owned. Swing camo
  pixel caching and GL texture ownership are different lifetimes; combining them would weaken the thread boundary.
  Add cache/batching complexity only after C9 measures a concrete issue.
- **Status:** this plan owns task checkboxes; evidence files are dated observations. Reference-only Python builders
  may remain for comparison, but Java must remain the live/review composition path. Do not delete reference tools
  solely to reduce file count.

Recommended order: fix grouping/identity (R1/R2), finish timing and snapshot consistency (R3/R4), correct mount-space
recoil (R5), then close the C6/C7 matrix, C8 specialized/death behavior and C9 measurements/package review.
For each fix, promote a meaningful regression into the normal suite and rerun the affected native acceptance case.

## Verification and limits of this review

- Recompiled the six reviewed playback/animation classes against the last successful complete workspace build.
- **25 existing checks passed:** 17 movement, 2 group movement and 6 shared playback checks.
- **Five local reproductions confirmed the defects above.** These intentionally assert the observed bad behavior;
  their passing result must not be described as the bugs being fixed. The posture/recoil cases use minimal rigid
  nodes, the transport case exercises the queue boundary, and the grouping cases create actual game weapon groups.
- No new native render, full mixed-board performance run or complete application regression suite was performed
  during this review. Earlier native screenshots/playback evidence remain the evidence for those foundations.
- Production Java and deployed model assets were not changed by this review. The local harness/results are under
  `megamek_temp/.work/modular-review/`; reproduce with the command below while that local build snapshot exists.

```powershell
.\gradlew.bat -I .work/modular-review.init.gradle --project-cache-dir .work/modular-review-gradle-cache :megamek:verifyModularReview --offline --console=plain --max-workers=2
```

This is a focused audit of the modular-model plan and its main integration boundaries, not a claim that every
weapon handler, family animation, platform or concurrent board change has been exhaustively reviewed.
