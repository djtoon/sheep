"""Tiered chasm cascade (2b74 centre): a sheet of water drops onto a mossy rock shelf, spreads and foams,
splits around boulders, drops again, and lands in irregular churning foam. 12 frames, hard pixels only.
python art/raw/terrain/tiers.py -> assets/terrain/tiers.png (W*12 x H), churn.png (8 frames 24x7)"""
import os, sys
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(__file__))
import px
from spill import BLUES, streaks

N = 12
OUTL = (16, 22, 26)


def rock(name):
    return np.array(Image.open(os.path.join(px.OUT, name + '.png')).convert('RGBA'))


def paste(fr, im, x, y):
    h, w = im.shape[:2]
    for yy in range(h):
        for xx in range(w):
            if im[yy, xx, 3] and 0 <= y + yy < fr.shape[0] and 0 <= x + xx < fr.shape[1]:
                fr[y + yy, x + xx] = im[yy, xx]


def shelf(w, h, seed):
    """a mossy rock shelf: brown/olive boulder band with a green moss top, outlined"""
    r = np.random.default_rng(seed)
    out = np.zeros((h, w, 4), np.uint8)
    top = np.round(np.convolve(r.random(w + 6), np.ones(4) / 4, 'same')[3:w + 3] * 3).astype(int)
    browns = [(58, 44, 32), (84, 64, 42), (110, 86, 56), (132, 108, 70)]
    for x in range(w):
        for y in range(top[x], h):
            d = y - top[x]
            if d < 2:
                c = (126, 190, 58) if d == 0 else (70, 130, 40)
            elif d < 3 and r.random() < 0.6:
                c = (46, 92, 30)
            else:
                c = browns[min(3, max(0, 3 - (d // 2) + (1 if (x // 5 + y // 3) % 2 else 0) - 1))]
            out[y, x] = (*c, 255)
    # outline
    m = out[..., 3] > 0
    ring = m & ~(np.roll(m, 1, 0) & np.roll(m, -1, 0) & np.roll(m, 1, 1) & np.roll(m, -1, 1))
    ring[:, 0] |= m[:, 0]; ring[:, -1] |= m[:, -1]
    out[ring] = (*OUTL, 255)
    # moss drips
    for _ in range(w // 6):
        x = int(r.integers(1, w - 1)); ln = int(r.integers(2, 5))
        for k in range(ln):
            if top[x] + 2 + k < h: out[top[x] + 2 + k, x] = (70, 130, 40, 255)
    return out


def build(W=150, H=98, seed=9):
    r = np.random.default_rng(seed)
    # geometry: tier 1 sheet falls y0..13 onto shelf A (y13-17) spanning most width with a notch;
    # tier 2 streams (split by boulders) fall 17..30 onto shelf B pieces; tier 3 falls 30..H into the pool
    mask = np.zeros((H, W), bool); white = np.zeros((H, W), int)
    gate = (np.sin(np.arange(W) * 1.7 + seed) * 0.5 + 0.5) * 0.6 + r.random(W) * 0.4
    def band(y0, y1, a0, b0, a1, b1, foam_top=3):
        na = np.cumsum(r.normal(0, 0.9, H)); nb = np.cumsum(r.normal(0, 0.9, H))
        na = np.convolve(na - na.mean(), np.ones(5) / 5, 'same'); nb = np.convolve(nb - nb.mean(), np.ones(5) / 5, 'same')
        for y in range(y0, min(H, y1)):
            t = (y - y0) / max(1, y1 - y0 - 1)
            wob = 0.35 + 0.65 * t   # edges wobble more as the water falls
            a = int(round(a0 + (a1 - a0) * t + np.clip(na[y], -4, 4) * wob))
            b = int(round(b0 + (b1 - b0) * t + np.clip(nb[y], -4, 4) * wob))
            a, b = max(0, a), min(W, b)
            k = y - y0
            if k < 4:                                   # rounded lip: narrower crown bulging over the edge
                ins = int((b - a) * [0.2, 0.09, 0.04, 0.01][k]); a += ins; b -= ins
            n1 = y1 - y0; fray = max(0.0, (k / max(1, n1) - 0.4) / 0.6)
            for xx in range(a, b):
                ed = min(xx - a, b - 1 - xx) / max(1, (b - a) / 2)
                if fray > 0 and gate[xx] < fray * 0.7 * (1.2 - ed * 0.6):
                    continue                            # strands separate as the water drops
                mask[y, xx] = True
            if y - y0 < foam_top: white[y, a:b] = 2
    band(0, 31, 30, 122, 24, 128)                     # tier 1: wide sheet
    band(38, 64, 14, 54, 8, 58)                      # tier 2 streams, split by the rocks on shelf A
    band(38, 64, 70, 102, 66, 108)
    band(38, 64, 114, 138, 112, 144)
    band(72, H, 2, 148, 0, 150, 2)                    # tier 3: broad drop into the pool
    base, dashes = streaks(W, seed)
    from spill import frame
    # full-width mossy rock shelves the water pours over (dark rock face shows between the streams)
    shelfA = (shelf(W - 12, 9, 1), 6, 30)
    shelfB = (shelf(W, 9, 3), 0, 64)
    # where water runs over a shelf's top edge: foam across these spans
    overA = [(24, 128)]; overB = [(8, 58), (66, 108), (112, 144)]
    b1, b2, b3 = rock('rock1'), rock('rock10'), rock('rock5')
    boulders = [(b1, 58, 34 - b1.shape[0] + 4), (b2, 118, 34 - b2.shape[0] + 3), (b3, 22, 68 - b3.shape[0] + 3)]
    frames = []
    for f in range(N):
        fr = frame(W, H, mask, white, base, dashes, f)
        rr = np.random.default_rng(seed * 50 + f)
        # churning foam where each tier lands: irregular clusters, not a uniform row
        # 4-tone hard foam clusters where each tier lands (dark rim, mid, light cyan, white core)
        tones = [(44, 106, 154), (116, 184, 226), (194, 230, 246), (248, 253, 255)]
        for (yy, x0, x1, n) in [(38, 16, 136, 9), (72, 4, 148, 11), (H - 3, 0, W, 14)]:
            blobs = [(rr.integers(x0, x1), yy - rr.integers(0, 3), 2 + rr.integers(0, 3)) for _ in range(n)]
            for ring in range(4):
                for (bx, by, br) in blobs:
                    rad = br + 1 - ring * 0.9
                    if rad <= 0: continue
                    for dy in range(-int(np.ceil(rad)), int(np.ceil(rad)) + 1):
                        hw = int(np.sqrt(max(0, rad * rad - dy * dy)))
                        Y = by + dy
                        if 0 <= Y < H: fr[Y, max(0, bx - hw):min(W, bx + hw + 1)] = (*tones[ring], 255)
        for (im, x, y), over in ((shelfA, overA), (shelfB, overB)):
            paste(fr, im, x, y)
            for (a0, a1) in over:          # water sheeting over the lip: white churn on the moss, streaks on the face
                for xx in range(a0, a1):
                    lip = 2 + int(rr.integers(0, 2))
                    for yy in range(y, y + 9):
                        if yy - y < lip or rr.random() < 0.62:
                            fr[yy, xx] = (*BLUES[5 if yy - y < lip or rr.random() < 0.5 else 3], 255)
        for im, x, y in boulders: paste(fr, im, x, y)
        # spray flecks off the boulders
        for im, x, y in boulders:
            for _ in range(8):
                sx = int(x + rr.integers(-3, im.shape[1] + 3)); sy = int(y + rr.integers(-4, 3))
                if 0 <= sx < W and 0 <= sy < H and fr[sy, sx, 3] == 0 or (0 <= sy < H and 0 <= sx < W and mask[sy, sx]):
                    fr[sy, sx] = (*BLUES[5], 255)
        frames.append(fr)
    Image.fromarray(np.concatenate(frames, 1)).save(os.path.join(px.OUT, 'tiers.png'))
    print('tiers', W, H, N)


def churn(W=24, H=7, n=8):
    """a white churn patch that boils on the basin surface (irregular, hard pixels)"""
    frames = []
    for f in range(n):
        rr = np.random.default_rng(300 + f)
        fr = np.zeros((H, W, 4), np.uint8)
        k = 0.6 + 0.4 * np.sin(f / n * 2 * np.pi)
        for _ in range(int(40 * k) + 10):
            x = int(W / 2 + rr.normal(0, W / 5)); y = int(H - 2 - abs(rr.normal(0, 1.6)))
            if 0 <= x < W and 0 <= y < H:
                fr[y, x] = (*BLUES[5 if rr.random() < 0.6 else 4], 255)
        for x in range(W):
            if abs(x - W / 2) < W / 3.4 * k and rr.random() < 0.45: fr[H - 1 - int(rr.integers(0, 2)), x] = (*BLUES[4], 255)
        frames.append(fr)
    Image.fromarray(np.concatenate(frames, 1)).save(os.path.join(px.OUT, 'churn.png'))
    print('churn', W, H, n)


if __name__ == '__main__':
    build(); churn()
    # chain-link panels: visible light diagonal mesh over the dark fill
    for k in ('fence', 'fence-plain'):
        a = np.array(Image.open(os.path.join(px.OUT, k + '.png')).convert('RGBA'))
        for y in range(10, 49):
            for x in range(6, 53):
                if k == 'fence' and 18 <= x <= 38 and 21 <= y <= 31: continue
                if (x + y) % 4 == 0 or (x - y) % 4 == 0:
                    a[y, x] = (150, 162, 168, 255) if (x + y) % 2 == 0 else (108, 118, 126, 255)
                else:
                    a[y, x] = (30, 40, 50, 255)
        Image.fromarray(a).save(os.path.join(px.OUT, k + '-solid.png'))
    print('fences ok')
