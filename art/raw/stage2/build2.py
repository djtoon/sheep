"""Stage 02 (night base B-02) art: generated with gen.mjs (--ref ref/levels/level2.png) -> pixel-clean, night-palette-locked.
python art/raw/stage2/build2.py -> assets/stage2/*.png + assets/parts/stage2.json"""
import os, sys, json
import numpy as np
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'terrain'))
import px
from build_terrain import seamless_x

ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
OUT = os.path.join(ROOT, 'assets', 'stage2')
os.makedirs(OUT, exist_ok=True)


def night_palette(n=128):
    cache = os.path.join(HERE, 'palette2.png')
    if os.path.exists(cache):
        return np.array(Image.open(cache).convert('RGB')).reshape(-1, 3)
    im = Image.open(os.path.join(ROOT, 'ref', 'levels', 'level2.png')).convert('RGB')
    im = im.resize((im.width // 3, im.height // 3), Image.BOX)
    q = im.quantize(colors=n, method=Image.Quantize.MEDIANCUT)
    pal = np.array(q.getpalette()[:n * 3]).reshape(-1, 3)
    Image.fromarray(pal.reshape(1, -1, 3).astype(np.uint8)).save(cache)
    return pal


PAL = night_palette()
META = {}


def load(n):
    return px.load(os.path.join(HERE, n))


def q(a):
    return px.quant(a, PAL)


def save(name, a, **meta):
    Image.fromarray(a).save(os.path.join(OUT, name + '.png'))
    META[name] = {'w': int(a.shape[1]), 'h': int(a.shape[0]), **meta}
    print(name, a.shape[1], a.shape[0])


def piece(src, box, h, name):
    a = load(src)[box[1]:box[3], box[0]:box[2]]
    w = round(a.shape[1] * h / a.shape[0])
    save(name, px.crop_alpha(q(px.down(a, w, h))))


def strip(src, h, name, crop=None, opaque=True, blend=24):
    a = load(src)
    if crop: a = a[crop[1]:crop[3], crop[0]:crop[2]]
    w = round(a.shape[1] * h / a.shape[0])
    s = px.down(a, w + blend, h)
    if opaque: s[..., 3] = 255
    s = seamless_x(s, blend)
    save(name, q(s))


if __name__ == '__main__':
    strip('sky_1.png', 270, 'sky')
    strip('mid_1.png', 118, 'mid', crop=(0, 630, 2048, 1060), opaque=False)
    strip('floor_1.png', 108, 'floor')
    strip('floorB.png', 108, 'floorB')
    strip('floorC.png', 108, 'floorC')
    strip('compound_2.png', 74, 'compound', crop=(0, 660, 2048, 865), opaque=False)
    piece('scaffold_2.png', (56, 322, 1991, 907), 80, 'scaffold')
    piece('fortress_2.png', (14, 20, 1523, 1118), 150, 'fortress')
    P = 'props_1.png'
    piece(P, (1225, 30, 1373, 496), 72, 'lamp')
    piece(P, (347, 226, 561, 477), 50, 'crates2')
    piece(P, (61, 328, 263, 470), 28, 'crate')
    piece(P, (633, 286, 770, 493), 26, 'drum')
    piece(P, (886, 287, 1159, 493), 26, 'drums')
    piece(P, (52, 635, 536, 959), 42, 'fence')
    piece(P, (601, 517, 862, 985), 84, 'watchtower')
    piece(P, (971, 511, 1145, 985), 90, 'radar')
    piece(P, (1239, 566, 1456, 985), 60, 'searchlight')
    k = 0
    for src in ('bigs_1.png', 'bigs_2.png'):
        a = load(src)
        for bx in px.components(a, 3000):
            h = bx[3] - bx[1]; w = bx[2] - bx[0]
            piece(src, bx, 118 if w < h * 1.3 else 92, 'big%d' % k); k += 1
    k = 0
    for src in ('towers_1.png', 'towers_2.png'):
        a = load(src)
        for bx in px.components(a, 3000):
            piece(src, bx, [104, 86, 96, 112, 90, 84][k % 6], 'tower%d' % k); k += 1
    parts = {'assets': [{'type': 'image', 'key': 's2-' + k, 'url': 'assets/stage2/' + k + '.png'} for k in META], 'anims': []}
    json.dump(parts, open(os.path.join(ROOT, 'assets', 'parts', 'stage2.json'), 'w'), indent=0)
    json.dump(META, open(os.path.join(OUT, 'pieces.json'), 'w'), indent=1)
