"""Package native Java review frames as a portable gallery; never generates or assembles game models."""
import argparse
from fnmatch import fnmatch
from html import escape
from pathlib import Path

from PIL import Image, ImageDraw


def build(frames, output, include=('*',)):
    output.mkdir(parents=True, exist_ok=True)
    cards = []
    standalone = ('atlas-', 'battle-armor', 'infantry-transports', 'lrm20-', 'posture-', 'ammo-', 'polish-')
    for folder in sorted(frames.glob('playback-*')):
        name = folder.name.removeprefix('playback-')
        if not any(fnmatch(name, pattern) for pattern in include):
            continue
        paired = name.endswith('-iso')
        if not paired and not name.startswith(standalone):
            continue
        top = folder.with_name(folder.name.removesuffix('-iso')+'-top') if paired else None
        paths = sorted(folder.glob('*.png'))
        if not paths or (paired and not top.is_dir()):
            continue
        images = []
        # Review samples are intentionally slowed; the production clock is tested in Java.
        for path in paths[::max(1, len(paths)//30)]:
            panels = [path, top/path.name] if paired else [path]
            image = Image.new('RGB', (320*len(panels), 262), '#26303b')
            for index, source in enumerate(panels):
                with Image.open(source) as original:
                    image.paste(original.resize((320, 240), Image.Resampling.LANCZOS), (index*320, 22))
            ImageDraw.Draw(image).text((8, 5), name.removesuffix('-iso') + (' | isometric / top' if paired else ''), fill='white')
            images.append(image.quantize(colors=128))
        filename = name.removesuffix('-iso')+'.gif'
        images[0].save(output/filename, save_all=True, append_images=images[1:], duration=140, loop=0, disposal=2)
        cards.append(f'<figure><figcaption>{escape(name.removesuffix("-iso"))}</figcaption>'
                     f'<img loading="lazy" src="{escape(filename)}" alt="{escape(name)}"></figure>')
    (output/'index.html').write_text('''<!doctype html><html lang="en"><meta charset="utf-8">
<title>Modular unit review</title><style>body{background:#17212b;color:#eef3f6;font:16px system-ui;margin:32px}
main{display:grid;grid-template-columns:repeat(auto-fit,minmax(480px,1fr));gap:20px}figure{margin:0;background:#26303b;padding:12px}
img{width:100%;height:auto}figcaption{margin-bottom:8px}input{padding:10px;width:340px;margin:16px 0}</style>
<h1>Modular unit review</h1><p>Frames from the game renderer. Paired clips show isometric and top views.
Clips are slowed review samples, not recordings of real-time playback. Generic fallbacks are intentional.</p>
<label>Filter clips <input oninput="document.querySelectorAll('figure').forEach(f=>f.hidden=!f.textContent.toLowerCase().includes(this.value.toLowerCase()))"></label>
<main>''' + '\n'.join(cards) + '</main></html>\n', encoding='utf-8')
    print(f'Packaged {len(cards)} native review clips into {output}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--frames', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--include', nargs='+', default=['*'], help='Review-name patterns, e.g. polish-* contact-*')
    args = parser.parse_args()
    build(args.frames, args.output, args.include)
