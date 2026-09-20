# Brief: author a new unit chassis

A standing task brief. Read this plus [UNIT_REVIEW_PROCESS.md](UNIT_REVIEW_PROCESS.md) and
[MODELLING_GUIDE.md](MODELLING_GUIDE.md) and you have everything needed to take a chassis from a name
to a reviewed, in-game model. Written after building the Rifleman; every trap listed here cost real
time on that one.

**Your deliverable is not code, it is a reviewed model.** The reviewer judges the artwork against the
miniature. Your job is to get it in front of them quickly and iterate.

---

## 1. What this pipeline is

MegaMek's GPU board assembles each unit at runtime from a **bare body** plus the **equipment its actual
loadout carries**. Nothing is baked per variant. One authored body serves every variant of a chassis:
the Rifleman body serves all 26, the Atlas body all 31.

Two repositories, both needed:

| Repo | Holds |
|---|---|
| `mm-data` | the Python authoring tools, the recipes, the exported assets, the mekset |
| `megamek` | the Java runtime that assembles and draws units, and the review/validation tests |

**Geometry is authored in Python, not modelled in Blender.** Bodies are boxes, beams and lofted
cross-sections written as code. Blender is used only to *render review sheets*. The exporter says so
itself: "no bpy or Blender process is required".

Environment on the machine this was written for: Blender 5.2 at
`C:\Program Files\Blender Foundation\Blender 5.2\blender.exe`, Python 3.13, working directory
`D:\MegaMek Projects\mekhq\megamek`.

---

## 2. Prerequisites, and the trap in them

The exporter needs two catalog files. Without them it dies with `FileNotFoundError` and nothing
downstream runs. Generate both from the megamek checkout:

```bash
./gradlew :megamek:exportEquipmentModelCatalog :megamek:exportMekModelCatalog --console=plain
```

They land in `mm-data/.work/modular-models/equipment.json` (every registered equipment type and its
visualisation policy) and `mm-data/.work/mek-models/catalog.json` (every unit, its loadout, and its
actuators). Re-run only when MegaMek's equipment or unit files change. Takes about six minutes cold.

**The documentation trap:** several docs reference `MODULAR_MODELS_C0.md` through `C6.md` and
`MODULAR_MODELS_C4_SUPPORTS.md`. **None of those files exist** and none are in git history - 28 dead
links across the doc set. The C1 document was supposed to explain the catalog step above. Do not waste
time hunting for them.

**Three tools are legacy. Never use them on modular assets:**

| Tool | Why not |
|---|---|
| `build_unit_models.py` | the old baked-variant builder |
| `render_unit_variants.py` | reads only frozen legacy bakes, rejects schema-2 vertex layouts |
| `validate_unit_models.py` | demands a schema-1 manifest key and crashes on the current one |

The live validator is the Java `UnitModelDescriptorTest`.

---

## 3. Research before you model

Do all of this before writing a line of geometry. It decides the design.

**Loadouts and actuators.** This is the highest-value query. It told us every Rifleman variant lacks
hands and lower arms, which means the arms are weapon pods rather than limbs - the single most
important design fact about that chassis.

```bash
python -c "
import json
d=json.load(open('.work/mek-models/catalog.json'))
units=[u for u in d['units'] if u['chassis']=='<CHASSIS>']
print(len(units),'variants')
for u in sorted(units,key=lambda u:u['model'])[:15]:
    print('%-16s %5.0ft hands=%-8s lowerArms=%-8s' % (u['model'],u['mass'],
          ','.join(u['hands']) or '-', ','.join(u['lowerArms']) or '-'))
    for m in u['equipment']:
        if m['location'] in ('LA','RA') and m['family'] not in ('internal','none'):
            print('    %-3s %-28s %s' % (m['location'], m['name'][:28], m['family']))
"
```

Run from `mm-data`. Also count weapon families per location, and check for rear-facing mounts:

```bash
python -c "
import json, collections
d=json.load(open('.work/mek-models/catalog.json'))
units=[u for u in d['units'] if u['chassis']=='<CHASSIS>']
live=[m for u in units for m in u['equipment'] if m['family'] not in ('internal','none')]
print('families:', dict(collections.Counter(m['family'] for m in live)))
print('locations:', dict(collections.Counter(m['location'] for m in live)))
print('rear:', [(m['location'],m['name']) for m in live if m['rear']] or 'NONE')
"
```

What to take from it:

- **No hands and no lower arms on every variant** means arm weapons mount at the elbow. Author no
  forearm and no fist; the arm *is* the gun housing.
- **How many weapons per arm** decides the mount area shape. Two per arm wants a tall narrow area so
  they stack over-under, or a wide one so they sit abreast.
- **Jump jets** ride in the calves automatically; you do not author them.
- **Rear mounts** need `rearSockets` that actually clear the hull. If none exist, still author them for
  custom refits, but do not spend review time on them.

**The game sprite.** It gives left-right and front-back placement. Dump it as text rather than
squinting at an 84x72 image:

```bash
python -c "
from PIL import Image
im = Image.open('data/images/units/meks/<Sprite>.png').convert('LA'); w,h = im.size; px = im.load()
print('    ' + ''.join(str((x//10)%10) for x in range(w)))
print('    ' + ''.join(str(x%10) for x in range(w)))
for y in range(h):
    row = ''.join('.' if px[x,y][1]<40 else '#' if px[x,y][0]<60 else '+' if px[x,y][0]<140
                  else '-' if px[x,y][0]<210 else 'o' for x in range(w))
    if row.strip('.'): print('%3d ' % y + row)
"
```

Sprite centre is pixel (42, 36). Model x = sprite x - 42, model y = 36 - sprite y. Up on the sprite is
forward on the model.

**The per-variant sprites.** `data/images/units/meks/` holds roughly 3,500 top-down sprites, and a
chassis usually has one generic sprite plus a sprite per variant. Do not stop at the generic one.
Diff them against it to see what the artists varied:

```bash
python -c "
from PIL import Image
from pathlib import Path
base = Path('data/images/units/meks')
ref = Image.open(base / '<Chassis>.png').convert('LA'); w, h = ref.size; a = ref.load()
def shape(px, x, y):
    lum, alpha = px[x, y]
    return lum if alpha >= 40 else None
for path in sorted(base.glob('<Chassis>*.png')):
    im = Image.open(path).convert('LA')
    if im.size != (w, h):
        print('%-24s other size' % path.name); continue
    b = im.load()
    rows = [y for y in range(h) if any(shape(a,x,y) != shape(b,x,y) for x in range(w))]
    print('%-24s %s' % (path.name, 'identical' if not rows else '%d..%d' % (min(rows), max(rows))))
"
```

Two patterns come out of it, and they mean different things:

- **Differences confined to the weapon rows** (the top third) mean one body with different guns. The
  barrel width is a direct reference for how thick that weapon should be. On the Rifleman the generic
  sprite draws 4-pixel barrels and the RFL-3C, which carries twin AC/10s, draws 5-pixel ones.
- **Differences running down to the legs** mean the artists drew a genuinely different machine for that
  era. Eleven of the nineteen Rifleman sprites do this; the RFL-1N is the original 3025 design and
  shares almost nothing with the reseen body.

**You cannot satisfy all of them, and you are not meant to.** Check `mekset.txt`: a variant with a
sprite-only `exact` line inherits the chassis model. All 32 Rifleman variants do, so one body serves
every design the sprites show. Treat the generic sprite as the primary reference, the variant sprites
as a weapon-sizing reference and a cross-check, and say in review which design the body follows.

Cross-checking placement across variants is also how you separate a drawing convention from a one-off.
The Rifleman radar sits right of centre in the generic sprite *and* in the RFL-1N sprite, so that is
deliberate, not an accident of one drawing - worth raising with the reviewer even if the miniature
wins in the end.

**The miniature renders on Sarna.** These are what the model is judged against. The old line art is a
rough guide and is often a different design. Ask the reviewer for links, or fetch them. When the sprite
and the miniature disagree, the miniature usually wins - but say so and let the reviewer rule.

---

## 4. The three-file change

Adding a chassis touches exactly three files. Miss the second half of the first and you get a
`KeyError` at export.

### 4.1 `mm-data/tools/unit_mek_chassis.py`

Add `def <id>(g):` building the body, **and** add `'<id>': <id>` to the `builders` dict inside
`build_chassis`. The dict is a hard lookup; a recipe without a builder entry crashes.

Geometry API on `g` (see `unit_model_geometry.py`):

| Call | Makes |
|---|---|
| `g.box(center, size, group, material, bevel=0, taper=1)` | a box, optionally chamfered |
| `g.beam(start, end, width, depth, group, material, sides=4, taper=1)` | a beam between two points |
| `g.prism(ring, bottom, top, group, material, taper=1)` | an extruded polygon |
| `g.loft(rings, group, material)` | a skin through a list of rings |
| `g.face(points, group, material)` | one flat polygon; winding sets the normal |
| `g.joint(name, pivot, parent)` | a rig pivot; geometry is stored local to it |
| `g.emitter(position, direction, group, role, effect)` | a muzzle or exhaust point |

Module helpers:

| Helper | Use |
|---|---|
| `upright(g, sections, group, material, cut)` | stack lofted cross-sections upward; sections are `(z, width, depth, center x, center y)` |
| `forward(g, sections, group, material, cut)` | loft front-to-back; sections are `(y, width, height, center x, center z)` |
| `panel(g, points, group, material)` | a flat inset such as cockpit glazing |
| `foot(g, x, y, width, length, group)` / `toes(...)` | feet; they create the `-foot` joint themselves |
| `lofted_face(sections, rear)` | surface of an `upright` torso at any height, for flush detail |
| `capped_face(y, rear)` | surface of a `forward` torso's flat end cap |
| `vent(g, face, center_x, half_width, low_z, high_z, rear, group)` | a cooling vent lying in the skin |

Materials: `paint`, `edge`, `metal`, `dark`, `glass`, plus weapon tips `laser`, `ppc`, `tag`, `plasma`
and `lamp`. `metal` and `dark` read as near-black; use them sparingly on large faces.

Rig groups a Mek body must produce: `pelvis`, `CT`, `HD`, `LT`, `RT`, `LA`, `RA`, `LL`, `RL`, plus
`-shin` and `-foot` on each leg. Optional arm anatomy is tagged `LA@elbow`, `LA@forearm`, `LA@wrist`,
`LA@hand` and shown per variant according to actuators. `build_chassis` auto-creates `LA-forearm` and
`RA-forearm` pivots if you do not.

Height convention: hips sit around z=29 to 31, the top of a tall Mek around 55. Check the Calibration
table in [UNIT_REVIEW_PROCESS.md](UNIT_REVIEW_PROCESS.md) before trusting your eye on leg mass - legs
are the easiest thing to overbuild, and a 60-tonner was authored heavier than two 70-tonners before
the numbers caught it.

### 4.2 `mm-data/tools/unit-models/chassis.json`

Append one recipe. **Match the file's compact hand formatting** - several keys per line, no spaces
after colons in arrays. Do not rewrite the file with `json.dumps(indent=2)`; that reformats all
existing chassis and produces a 1,100-line diff for a 10-line change.

Required: `name`, `id`, `referenceVariant`, `sprite`, `illustration`, `hip`, `silhouette`, and
`sockets` with all eight of `HD CT LT RT LA RA LL RL`. A socket is `[sprite x, sprite y, height]`,
placed where the barrel leaves the armour.

**Live optional keys**, read by the current exporter:

| Key | Purpose |
|---|---|
| `rearSockets` | rear-facing mounts; without one the front point is reused nine pixels back, usually inside the hull |
| `socketBanks` | exact spots for one family in one location, e.g. `"RA:hatchet"`, or per arm form `"LA@wrist:ppc"` |
| `socketAim` | direction for a location's weapons, so a barrel follows its limb |
| `protrusion` | how far barrels stand out, per location or `LOC:family`: `recessed` 0.06, `short` 0.4, `medium` 0.7, `long` 1.0 |
| `mountAreas` | the facing weapons are laid out on: `{"width": x extent, "height": z extent}`, optional `center` |
| `armSockets` | per-form attach points: `{"LA": {"elbow": [...], "wrist": [...], "hand": [...]}}` |
| `weaponOverrides` | per-weapon changes matched by `location`, `family`, `name`, `rear`; `length` is scaled by `weaponScale` |
| `missileSockets`, `missileBayHeight`, `missileBayColumns`, `missileBayWidth`, `missileScale`, `missileSlope` | launcher bays |
| `barrelLength`, `weaponScale` | gun sizing; `weaponScale` runs 0.83 (Atlas) to 0.95 |
| `searchlightSocket` | external lamp position, undocumented in the older guide but live |

**Dead keys.** These appear in existing recipes and in `MODELLING_GUIDE.md` section 3, but **only the
legacy builder reads them**. Setting them does nothing and produces no warning:

`beltSockets`, `missileOrientation`, `missileColumns`, `slotSpacing`

Vertical launcher orientation in the current path comes from `missileSlope`, not `missileOrientation`.

### 4.3 `mm-data/data/images/units/mekset.txt`

One line, placed with the other chassis entries:

```text
chassis "<Name>" "meks/<Sprite>.png" "units/modular/meks/<id>.json"
```

A sprite-only `exact` entry for a variant inherits the chassis model, so per-variant lines need no
change.

---

## 5. Build, review, validate

```bash
# from mm-data - about 11 seconds, exports every asset
python tools/build_modular_unit_models.py

# bare body, six angles plus the waist-twist gate - about 10 seconds
"/c/Program Files/Blender Foundation/Blender 5.2/blender.exe" --background --factory-startup \
    --python-exit-code 1 --python tools/render_modular_body.py -- --body <id> --turn 60

# from megamek - asset contract gate, about 6 minutes
./gradlew :megamek:test --tests "*UnitModelDescriptorTest*" --console=plain

# from megamek - assembles real units and writes review images, about 2 minutes
./gradlew :megamek:gpuBoardSmoke --tests '*GpuModularUnitModelsSmokeTest*' --console=plain
```

Bare-body sheets land in `mm-data/.work/body-review/`. Assembled review images land in
`megamek/build/gpu-board-review/`.

The middle two commands are the iteration loop, about twenty seconds a round. **Expect several rounds.
The Archer took five, the Rifleman seven.** Send a sheet each round.

To get a new chassis into the assembled review, add it to the `cases` array in
`GpuMekAssemblyReview.java` as `{ label, body descriptor id, unit file path }`. Add a row per variant
you want rendered; several rows may share one descriptor. To add it to the variant sheets, extend the
chassis list at the end of `verify`.

---

## 6. Traps that cost real time

- **A stale edit is silent.** Editing a recipe by string replacement against a value an earlier pass
  already changed does nothing, the build still succeeds, and the render looks unchanged for the wrong
  reason. **Assert on every edit** and print the value back.
- **A bevel narrows the flat face.** `section(w, d, cut)` chamfers the corners, so the flat band is
  `width/2 - min(width, depth)/2 * cut`, not `width/2`. A `cut` of 0.3 on a 17-wide, 13.7-deep section
  leaves only about +/-6.4 flat. Detail outside that band hangs off the chamfer and reads as stuck on.
- **A lofted face slopes.** A torso going from 13 deep to 14.5 over six units of height moves its
  surface 0.125 per unit. Flush detail at one fixed depth is half buried and half floating. Use
  `lofted_face`.
- **Winding sets the normal.** A front panel and a back panel need opposite vertex order or one of them
  renders invisible.
- **Mount area axes:** `width` is left-right, `height` is vertical. A tall narrow area stacks weapons
  over-under; a wide one sets them abreast.
- **Vertices are node-relative.** In the exported `.g3dj`, a part's vertices are local to its node;
  world position is the accumulated chain of node translations.
- **House rules** from `CLAUDE.md`: no Unicode anywhere in code, no trademarked words in Java
  (`Mech`, `BattleMech`, `MechWarrior`, `AeroTech`), no `@author` tags and no individual named in
  licensing text, and no `.stream()` inside a conditional - use a plain loop.
- **Never commit.** The user handles commits. Never push without permission for that specific push.

---

## 7. Definition of done

- [ ] Bare body under 1,000 triangles. A thousand is available; there is no virtue in coming in far under.
- [ ] Each equipment module under 100 triangles, and strictly under 150.
- [ ] Six-view bare sheet reviewed and accepted by the reviewer.
- [ ] Waist twist clean at 60 degrees: nothing above the waist cuts the hips or legs, no gap opens.
- [ ] Rear view confirmed - rear weapons must actually show, not sit inside the hull.
- [ ] `UnitModelDescriptorTest` passes.
- [ ] `GpuModularUnitModelsSmokeTest` passes, and the assembled render is reviewed with at least two
      loadouts that differ in weapon family, so a PPC and an autocannon are both seen in the same mount.
- [ ] Variant sheet rendered and reviewed.
- [ ] Vents present: at most two front, at most two back, back on torso locations only.
- [ ] Registered in `mekset.txt` and confirmed present in staged game data.
- [ ] Nothing committed.

---

## 8. Worked example

The Rifleman is the reference build. Its decisions, and why, are in section 8 of
[UNIT_REVIEW_PROCESS.md](UNIT_REVIEW_PROCESS.md); its body is `rifleman` in `unit_mek_chassis.py` and
its recipe is the last entry in `chassis.json`. Read both before starting a new one - the arm-pod
treatment for a chassis with no hands, and the vent placement, both transfer directly.
