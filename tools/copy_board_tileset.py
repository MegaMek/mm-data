"""Bootstrap the editable 3D-only Saxarba copy; never overwrite local artwork edits."""
from pathlib import Path
import json
import re
import shutil

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'data/images/hexes'
DEST = ROOT/'data/models/board/tileset'
seen = set()
copied = set()


def copy(name):
    if not name:
        return
    name = re.sub(r'\(\d+,\d+-\d+,\d+\)$', '', name)
    source = SOURCE/name
    if not source.is_file():
        raise FileNotFoundError(str(source))
    destination = DEST/name
    if not source.resolve().is_relative_to(SOURCE.resolve()):
        raise ValueError(name)
    if not destination.exists():
        destination.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(source,destination)
    copied.add(name)


def scan(name):
    if name in seen:
        return
    seen.add(name)
    copy(name)
    contents = (DEST/name).read_text(errors='replace')
    repaired = contents.replace('saxarba/saxarba/', 'saxarba/').replace('ssaxarba/', 'saxarba/')
    if repaired != contents:
        (DEST/name).write_text(repaired)
    for line in repaired.splitlines():
        quoted = re.findall(r'"([^"]*)"',line)
        if line.startswith('include ') and quoted:
            scan(quoted[0])
        elif line.startswith(('base ','super ','ortho ')) and len(quoted) >= 3:
            for image in quoted[2].split(';'):
                copy(image)


scan('saxarba.tileset')
for depth in range(5):
    copy(f'saxarba/anim_water_{depth}.gif')
(DEST/'sources.json').write_text(json.dumps({'source':'data/images/hexes','files':sorted(copied)},indent=2))
print(json.dumps({'files':len(copied),'bytes':sum((DEST/name).stat().st_size for name in copied)}))
