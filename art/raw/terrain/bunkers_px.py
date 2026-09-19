"""Hand-pixelled base structures at native resolution (no resampling): flat concrete panels with 1px seams,
lit top + left rim, dark recessed slit windows and doors, hazard frames, 1px outline, ~10 colours.
python art/raw/terrain/bunkers_px.py -> assets/terrain/bunker.png, bunker2.png, bigdoor.png (replacing the soft ones)"""
import os
import numpy as np
from PIL import Image

OUT = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'assets', 'terrain')
P = {'ol': (14, 18, 22), 'c0': (46, 54, 56), 'c1': (78, 88, 88), 'c2': (104, 114, 112), 'c3': (140, 150, 144),
     'rim': (196, 204, 194), 'dk': (10, 14, 18), 'win': (58, 40, 22), 'hot': (255, 196, 96), 'yel': (224, 168, 40),
     'st': (60, 70, 78), 'red': (200, 40, 36), 'rst': (112, 66, 34)}


def rect(im, x0, y0, x1, y1, c):
    im[max(0, y0):y1, max(0, x0):x1] = (*c, 255)


def outline(im, c):
    h, w = im.shape[:2]; o = np.zeros((h + 2, w + 2, 4), np.uint8); o[1:-1, 1:-1] = im
    m = o[..., 3] > 0; n = np.zeros_like(m)
    n[1:] |= m[:-1]; n[:-1] |= m[1:]; n[:, 1:] |= m[:, :-1]; n[:, :-1] |= m[:, 1:]
    o[n & ~m] = (*c, 255); return o


def hazard(im, x0, y0, x1, y1):
    for y in range(y0, y1):
        for x in range(x0, x1):
            im[y, x] = (*P['yel'], 255) if ((x + y) // 3) % 2 == 0 else (*P['dk'], 255)


def bunker(w, h, windows, door, seed):
    r = np.random.default_rng(seed)
    im = np.zeros((h, w, 4), np.uint8)
    rect(im, 0, 6, w, h, P['c1'])                                   # body
    rect(im, 0, 0, w, 6, P['c2']); rect(im, 0, 0, w, 1, P['rim']); rect(im, 0, 1, w, 2, P['c3'])   # roof slab, lit top
    rect(im, 0, 6, w, 8, P['c0'])                                   # shadow under the slab
    rect(im, 0, 8, 1, h, P['rim']); rect(im, 1, 8, 2, h, P['c3'])   # lit left rim
    rect(im, w - 4, 8, w, h, P['c0'])                               # right side shade
    # panel courses: 1px seams, each seam has a lit pixel row under it
    for y in range(20, h - 4, 14): rect(im, 2, y, w - 4, y + 1, P['c0']); rect(im, 2, y + 1, w - 4, y + 2, P['c2'])
    for x in range(18, w - 6, 24):
        rect(im, x, 8, x + 1, h, P['c0']); rect(im, x + 1, 8, x + 2, h, P['c2'])
    # rivets
    for x in range(8, w - 6, 12):
        for y in range(11, h - 4, 14): im[y, x] = (*P['c3'], 255)
    # slit windows: dark recess, frame lit at top/left, warm inside
    for (wx, wy, ww) in windows:
        rect(im, wx - 1, wy - 1, wx + ww + 1, wy + 6, P['c3'])
        rect(im, wx, wy, wx + ww, wy + 5, P['dk'])
        rect(im, wx + 1, wy + 2, wx + ww - 1, wy + 4, P['win'])
        for k in range(wx + 2, wx + ww - 2, 5): im[wy + 2, k] = (*P['hot'], 255)
    # door with hazard frame
    if door:
        dx, dw = door
        hazard(im, dx - 3, h - 36, dx + dw + 3, h)
        rect(im, dx, h - 33, dx + dw, h, P['st']); rect(im, dx, h - 33, dx + dw, h - 32, P['c3'])
        rect(im, dx + dw // 2, h - 33, dx + dw // 2 + 1, h, P['dk'])
        for y in range(h - 28, h, 5): rect(im, dx + 1, y, dx + dw - 1, y + 1, P['c0'])
        rect(im, dx + dw // 2 - 4, h - 42, dx + dw // 2 + 4, h - 38, P['dk']); rect(im, dx + dw // 2 - 3, h - 41, dx + dw // 2 + 3, h - 39, P['red'])
    # a few rust/water streaks (1px, deliberate)
    for _ in range(w // 16):
        x = int(r.integers(4, w - 6)); y = int(r.integers(9, h // 2)); ln = int(r.integers(4, 12))
        rect(im, x, y, x + 1, min(h, y + ln), P['rst'] if r.random() < 0.4 else P['c0'])
    # roof vent + antenna with red light
    rect(im, 10, -3 + 3, 22, 3, P['c1'])
    return outline(im, P['ol'])


def save(a, name):
    Image.fromarray(a).save(os.path.join(OUT, name + '.png')); print(name, a.shape[1], a.shape[0])


if __name__ == '__main__':
    save(bunker(200, 96, [(14, 30, 34), (140, 30, 34)], (84, 28), 1), 'bunker')
    save(bunker(194, 100, [(12, 26, 30), (60, 26, 30), (150, 26, 30)], (112, 26), 2), 'bunker2')
    save(bunker(118, 72, [(10, 18, 24)], (64, 34), 3), 'bigdoor')
