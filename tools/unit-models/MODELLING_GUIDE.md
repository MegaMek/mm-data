# Modelling guide for unit models ("MegaMeks")

How a new Mek gets a low-poly model, and the conventions agreed while building the first ones. The
asset layout and build commands are in `data/models/units/README.md`; this file is the working method
and the house rules. Everything here came from review feedback on real models, so treat it as binding
until a Mek's own artwork says otherwise.

Hard limit: **1,000 triangles per model**, weapons included.

## 1. The steps

1. **Pick the Mek and gather references.** Three are used:
   - the top-down 84 x 72 game sprite, for where things sit left-right and front-back;
   - a picture copied into `data/images/fluff/Mek/` (git-ignored, but the build refuses to run without it);
   - the modern miniature renders on Sarna (`cfw.sarna.net/wiki/images/...`). **These are what the model is
     judged against.** The old TRO line art is a rough guide only and is often a different design.
2. **List every loadout first.** The catalog (`.work/mek-models/catalog.json`) says what each variant
   carries and where. Know up front which locations need launchers, rear weapons, hand weapons, jets.
3. **Write the body** in `tools/unit_mek_chassis.py`: boxes, beams and tapered sections, no weapons.
4. **Write the recipe** in `tools/unit-models/chassis.json`: sprite, picture, hip and the hard points.
5. **Preview in a scratch folder** (`--recipes <scratch file> --output <scratch dir> --preview`). The
   built-in preview sheet holds four models, so review in batches of four at most.
6. **Review, adjust, repeat.** Expect several rounds. Send a four-view sheet each time.
7. **Move it into the real files**, add the model field to the Mek's `mekset.txt` line, run the full
   build and `validate_unit_models.py`.
8. **Render every variant** (`render_unit_variants.py --chassis <id>`) and zoom into anything odd.
9. **Stage the game data** (`gradlew :megamek:stageDataFiles` in the MegaMek checkout). The game reads a
   staged copy, not this repository.

## 2. What reviewers look at first

Learned the hard way on the Archer, which took five rounds:

- **Head or cockpit: height, and how far it projects.** Check this before anything else.
- **Proportions of a solid miniature.** No bodybuilder shoulders wider than the design; keep it compact.
- **No drooping parts.** A projecting cockpit is one solid mass whose underside runs level back into the
  torso; only its top slopes. Never leave a part hanging with empty space beneath it.
- **Launcher shape matches the miniature**: tall or wide, how many tubes across, and whether the face
  leans back (`missileSlope`). Missile bay doors are modelled shut.
- **Antennas and sensors go where the miniature has them**, not where it is convenient.

## 3. Hard points

A hard point is `[sprite x, sprite y, height]`. The sprite's center is pixel (42, 36); left-right is
`x - 42`, forward is `36 - y` (up on the sprite is forward on the model). Height uses the body's units:
hips about 29 to 31, the top of a tall Mek about 55. Put a hard point where the barrel leaves the armor,
or for a launcher at its front face, just proud of the body.

Every recipe needs eight (`HD CT LT RT LA RA LL RL`). Extras:

| Recipe key | Purpose |
|---|---|
| `socketBanks` | Exact spots for one kind of weapon in one location, e.g. `"RA:hatchet"` at the fist. |
| `missileSockets` | The bay for a torso's launchers. Two or more stack inside `missileBayHeight`; three or more go side by side with `missileBayColumns` and `missileBayWidth`. |
| `rearSockets` | Rear-facing weapons. Without one the front point is reused nine pixels back, which often lands inside the body. |
| `socketAim` | A direction for a location's weapons, e.g. `"LA": [0, 0.12, -1]`. |
| `protrusion` | How far barrels stand out, per location or `LOC:family`. |
| `missileOrientation` | `horizontal` or `vertical`, for the whole Mek or per location. |
| `mountAreas` | The rectangle weapons in a location are laid out in: `{"center": [x, y, z], "width", "height"}`. |
| `beltSockets` | Overrides where leg weapons sit. |
| `armSockets` | Where an arm weapon attaches for each arm form: `{"LA": {"elbow": [...], "wrist": [...], "hand": [...]}}`. |
| `weaponOverrides` | Per-weapon changes to the standard look, matched by `location`, `family`, `name`, `rear`. |

Conventions:

- **A weapon follows its limb.** When an arm is posed hanging down, give that hard point a `socketAim`
  so the barrel runs along the forearm. A barrel must never jut out at a right angle to the limb.
- **Arm actuators decide how an arm weapon looks, per variant.** Check them when listing the loadouts.
  With a **hand** actuator the weapon rides on the forearm. With the **hand missing** it attaches at the
  **wrist**. With the **lower arm missing** it attaches at the **elbow**. Tag the optional arm parts in the
  body function (`LA@elbow`, `LA@forearm`, `LA@wrist`, `LA@hand`, and the same for `RA`), give the recipe an
  `armSockets` entry per form, and key form-specific banks like `"LA@wrist:ppc"`. The Mackie covers all
  three forms across its six variants. The catalog needs the exporter's `lowerArms` field for this.
- **Leg weapons ride just below the hip, like a low-slung belt.** The generator lifts them to hip height
  minus five automatically. **Jump jets stay in the calves, at the back.**
- **Weapons in one location never overlap.** Each location has a mounting area; a weapon that would
  overlap another is moved to the nearest free spot in it, and only shrunk if the area is truly full.
  Bay launchers and `socketBanks` spots keep their place; the rest give way, largest first. A location
  that still cannot be resolved is marked `crowded` in the manifest: state a `mountAreas` entry for it.
- **Re-check every hard point after reshaping the body.** A changed head buried the Archer's rear laser.

## 4. Standard weapon looks

`weapons.json` holds the defaults; `unit_weapon_shapes.py` draws them; `render_weapon_chart.py` renders
every look side by side. **They are a starting point.** After applying them, compare the result with the
Mek's art and adjust in that Mek's recipe (the Marauder's AC/5 has a longer barrel than standard).

- The look comes from the weapon's **type**, never its tonnage. Sizes are fixed classes multiplied by the
  recipe's `weaponScale`, so a light Mek's guns are smaller than an assault's but proportions hold.
- **Tip colors:** red lasers, blue PPCs *only*, green TAG, orange plasma and TSEMP. Cockpits keep `glass`.
- **Lasers** slim square barrels in small, medium, large; pulse is shorter and fatter with a ring; heavy
  is thicker; a Blazer has twin barrels. **PPC** a thick barrel with a ring and a narrower emitter tip.
- **Autocannons** round, from long thin AC/2 to short fat AC/20; Ultra adds a muzzle brake, LB-X a
  flared muzzle. **Rotary AC/2 and AC/5** are a gatling ring of six thin barrels.
- **Gauss** a square rail with two coil rings. **HAG** four square rails in a two-by-two block, in three
  weights: HAG/20 light, HAG/30 medium, HAG/40 heavy.
- **Anti-missile system** a small gatling on a housing, like a naval CIWS; the laser AMS shows one red lens.
- **Launchers** never show a short row. LRM, SRM, Streak, MRM and Rocket Launcher tubes are **round**:
  LRM smallest, SRM in the middle, MRM and rockets only *slightly* larger. ATM, improved ATM and MML tubes
  are **diamonds**, all one size. A launcher mounts **horizontal or vertical**; decide per hard point.
- **Every barrel has four protrusions:** recessed (flat against the body), short, medium, long. Arms
  default to long; torso lasers, machine guns and TAG to short.
- **Hand weapons:** the hatchet blade faces forward; the sword and the mace lean forward forty-five
  degrees so they clear the forearm. One chunky shape stands for industrial tools.
- **Searchlight:** a box with a pale lens. Not drawn yet: `MekModelCatalog.java` classes searchlights as
  internal, so this waits on a `searchlight` family from the exporter.

## 5. The triangle budget

Round tubes cost six triangles each, so an LRM 20 is about 132. A loadout over 1,000 steps down through
`DETAIL_LEVELS`: round tubes drawn six-sided first, and only then one dark panel per launcher. The
manifest records `launcherDetail` whenever a variant is not at full detail. If many variants of a Mek
step down, the body is too heavy; slim the body rather than the weapons.

## 6. Traps

- A shrunken launcher can end up **behind its housing wall** and look like an empty bay. Keep the
  housing face about 0.35 behind the hard point.
- Make columns times rows **equal the tube count**; five and seven tubes use two rows, short row centered.
- Launchers stacked in one bay lean about the **bay's** center, or they form a staircase.
- Anything the catalog cannot classify sets the whole variant aside (`needsReview`).
- The catalog is a snapshot: re-run the export before building if unit files changed.
- The preview sheet only fits four models; use the variant renderer for more.
- A preview PNG open in an image viewer is locked on Windows; save under a new name.
