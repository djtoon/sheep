"""Generated gorge set piece (art/raw/terrain/gorge_1.png, gen.mjs with 2b74/c0f6 refs) -> pixel-clean, palette-locked,
cheaply animated sheets, one per chasm width. Animation: 4 frames; water pixels in the falls shift down 2px per frame
(only into other water pixels), the plunge pool shifts sideways 1px per frame.
python art/raw/terrain/gorge.py  -> assets/terrain/gorge-<w>.png (4 frames side by side), prints sizes"""
import os, sys, json
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(__file__))
import px

SRC = 'gorge_1.png'
N = 4


def water_mask(a):
    r, g, b = [a[..., i].astype(int) for i in range(3)]
    return ((b > r + 25) & (b >= g - 10) & (r + g + b > 250)) | ((r > 185) & (g > 205) & (b > 215))


def build(w_game, h_game, pool_frac=0.2):
    raw = px.load(SRC)
    H0, W0 = raw.shape[:2]
    scale = w_game / W0
    full_h = round(H0 * scale)
    img = px.quant(px.down(raw, w_game, full_h))
    img = img[max(0, full_h - h_game):]                      # keep the lower tiers + pool
    h = img.shape[0]
    wm = water_mask(img) & (img[..., 3] > 0)
    pool_y = int(h * (1 - pool_frac))
    frames = []
    for f in range(N):
        fr = img.copy()
        sh = 2 * f
        # falls: pull colour from sh px above where both are water (streaks slide down)
        src = np.roll(img, sh, axis=0); srcm = np.roll(wm, sh, axis=0)
        m = wm & srcm; m[:sh] = False; m[pool_y:] = False
        fr[m] = src[m]
        # pool: slide sideways
        src2 = np.roll(img, f, axis=1); srcm2 = np.roll(wm, f, axis=1)
        m2 = wm & srcm2; m2[:pool_y] = False
        fr[m2] = src2[m2]
        frames.append(fr)
    sheet = np.concatenate(frames, 1)
    # background step: lighter, bluer, lower contrast so the gorge sits behind the bridge deck and cliff lips
    k = 0.3; hz = np.array([150, 190, 214], np.float32)
    rgb = sheet[..., :3].astype(np.float32); sheet[..., :3] = np.clip(rgb * (1 - k) + hz * k, 0, 255).astype(np.uint8)
    name = f'gorge-{w_game}'
    Image.fromarray(sheet).save(os.path.join(px.OUT, name + '.png'))
    return name, w_game, h


if __name__ == '__main__':
    out = {}
    for w in (map(int, sys.argv[1:]) if len(sys.argv) > 1 else (300, 320, 260, 280)):
        name, ww, hh = build(w, 118)
        out[name] = [ww, hh]; print(name, ww, hh)
    json.dump(out, open(os.path.join(px.OUT, 'gorges.json'), 'w'))
