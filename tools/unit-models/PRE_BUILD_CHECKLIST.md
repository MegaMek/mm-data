# Pre-build checklist for a new modular Mek

Run this before modelling anything. You name the unit and share the art; I work through the questions
below with you, then build. Every answer here came from a correction on an earlier chassis, so each one
saves a round of rework.

The working loop and review conventions live in `UNIT_REVIEW_PROCESS.md`; this is the step before it.

---

## 1. What I gather first, without asking

- The unit's weight class and tonnage, and its **height band** (section 9 of the process doc).
- Every variant's unit file: which locations carry weapons, which carry slotted heat sinks, which have
  hands, lower arm actuators or no arms at all, and any head weapons.
- The chassis's existing body and recipe, if it has one, so the old version can be archived.
- The three reference renders of the current state (see section 4 below).

## 2. Questions for you

**Only once the art has arrived.** Share the facts from section 1, ask for the references, look at them,
and then ask. Many questions are answered by the pictures, and the rest are sharper for them.

**The art**
1. Which picture is the authority when they disagree: the miniature, the line drawing, or a record sheet?
2. Is there a front view? A side view? If not, which angle should I trust for proportions?
3. Anything on the miniature that is a sculpting quirk rather than the design, and should be ignored?

**The body**
4. Where is the cockpit, and what does it look like: a head, a canopy blister, windows in a nose, a
   visor? (The Locust's is in its nose, not on the roof.)
5. What are the two or three features that make it read as this Mek at a glance? Those get the detail
   budget first.
6. Is the body symmetric? Anything that is on one side only, like the Atlas's dish?
7. Leg type: forward knee, reverse (bird) knee, or no legs? How bent should they stand?
8. Arms: hands, gun pods, weapon arms, or none? Do they sit flush against the torso?

**The weapons**
9. For each location, where do its weapons sit: on a front face, hanging under something, in a turret,
   held in the hand? (The Locust fires its centre weapons from a chin turret.)
10. Do weapons sharing a socket sit side by side or over and under?
11. Missile launchers: upright and stacked, or lying flat? On the shoulders, in the torso, in a bay?
12. Any special rule for this chassis, like the Atlas drawing every LRM 20 as an upright LRM 5 on its
    waist?
13. Should head weapons share another location's face?

**Surface detail**
14. Where should vents go when no heat sinks are slotted in a torso?
15. Any detail to add or leave off: antennas, dishes, spines, searchlight position?

**Sign-off**
16. Which two or three variants should I check closely? One with the fewest weapons, one with the most
    and one with an unusual loadout covers most problems.
17. Should the old version be archived before the new one replaces it?

## 3. Rules I check on every build

- **Height:** inside the class band, measured to the top of the armour.
- **Sockets:** on the surface of their own location; run the hardpoint audit and explain every flag.
- **Mirroring:** left and right mirror across the centre line, never copied.
- **Flush:** weapons sit on their surface, not floating off it or buried in it.
- **Faces the right way:** panels and windows face outward, since the game draws one side only.
- **Attached:** every part touches what it hangs from, legs to hips especially.
- **Vents after weapons:** no weapon drawn over a vent.
- **Every variant builds:** the game review passes with every weapon drawn.

## 4. The three renders you get at every step

1. **Six views** of the bare chassis: Front, Back, Left, Right, Above, Three-quarter, with the chassis
   named at the top right.
2. **Variant sheet**: every variant as the game builds it, with its real loadout, framed to the chassis's
   size, plus close-ups of the variants chosen in question 16.
3. **Weight lineup**: every chassis from lightest to heaviest, alphabetical within a tonnage, front on.

## 5. Finishing a unit

- Zip the old version into `archive/` under a plain numbered name, with its README inside.
- Update `UNIT_REVIEW_PROCESS.md` with any new rule the unit taught us.
- Commit and push with two-word code-name messages.
