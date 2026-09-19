"""Per-layer stats of opaque pixels in assets/world (V/S median, 8x8 local contrast) - checks depth-step ordering."""
import sys, colorsys, numpy as np
from PIL import Image
L = [('play (terrain ref)', None), ('A near', 'near'), ('A midset', 'midset'), ('A canopy', 'canopy'), ('A outpost2', 'outpost2'),
     ('B cliffs', 'cliffs'), ('B midtrees', 'midtrees'), ('B outpost1', 'outpost1'),
     ('C farcliffs', 'farcliffs'), ('C hills', 'hills'), ('C outpost0', 'outpost0'), ('far mtns', 'far')]
def st(f):
    a = np.array(Image.open('assets/world/%s.png' % f).convert('RGBA')).astype(np.float32) / 255
    m = a[..., 3] > 0; rgb = a[..., :3]
    v = rgb.max(-1); s = np.where(v > 0, (v - rgb.min(-1)) / np.maximum(v, 1e-6), 0)
    lc = []
    for y in range(0, a.shape[0] - 7, 8):
        for x in range(0, a.shape[1] - 7, 8):
            mm = m[y:y + 8, x:x + 8]
            if mm.all(): lc.append(v[y:y + 8, x:x + 8].std())
    return np.median(v[m]), np.median(s[m]), np.median(lc) if lc else 0
for name, f in L:
    if f: print('%-14s V %.2f  S %.2f  lc %.3f' % ((name,) + st(f)))
