"""Build small runtime albedos; preserve the editable original artwork."""
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1] / 'data/models/board/textures'
for family in ('buildings', 'terrain'):
    for source in sorted((ROOT / family / 'full-resolution').glob('*.png')):
        with Image.open(source) as image:
            image.convert('RGB').resize((128, 128), Image.Resampling.LANCZOS).save(ROOT / family / source.name)
        print(f'{family}/{source.name}')
