"""Procedural pixel-art basin water, foam rings and mist puffs (hard-stepped, no blur, no alpha fades).
python art/raw/terrain/basin.py -> assets/terrain/basin.png (N frames of a 128x40 x-wrapping tile),
foamring.png (N frames 48x10), mist.png (N frames 44x28)"""
import os, sys
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(__file__))
import px

N = 8
FOAM = [(250, 253, 255), (214, 238, 248), (160, 212, 236)]
WATER = [(126, 196, 222), (74, 160, 200), (46, 126, 170), (30, 96, 140), (20, 72, 110), (14, 52, 82), (10, 38, 60)]


def noise1(n, seed, smooth=5):
    r = np.random.default_rng(seed)
    v = r.random(n + smooth * 2)
    k = np.ones(smooth) / smooth
    v = np.convolve(np.concatenate([v[-smooth:], v, v[:smooth]]), k, 'same')[smooth:smooth + n]
    return (v - v.min()) / (np.ptp(v) + 1e-6)


def basin(W=128, H=52):
    frames = []
    for f in range(N):
        img = np.zeros((H, W, 4), np.uint8)
        r = np.random.default_rng(100 + f)
        edge = np.round(noise1(W, 3 + f % 2, 9) * 6 + noise1(W, 50 + f, 3) * 3).astype(int)  # broken foam top edge 0..5
        for x in range(W):
            for y in range(edge[x], H):
                d = y - edge[x]
                # depth bands (stepped) with a 2-px dither between them
                t = max(0, (y - 7) / (H - 20))  # light only in the top ~7px, dark teal reached well before the bottom
                b = int(np.clip(1 + t * (len(WATER) - 1.01), 0, len(WATER) - 1)) if y > 7 else 1
                if (x + y) % 2 and y > 4 and (t * (len(WATER) - 1)) % 1 > 0.7:
                    b = min(len(WATER) - 1, b + 1)
                col = WATER[b]
                if d < 3:
                    col = FOAM[0] if d == 0 or (d == 1 and (x + f) % 3) else FOAM[1]
                elif d < 5 and d == 3 and (x + f) % 4 == 0:
                    col = FOAM[1]
                img[y, x, :3] = col; img[y, x, 3] = 255
        # ripple lines: short light dashes drifting, denser near the top
        for _ in range(60):
            y = int(5 + abs(r.normal(0, 3)) + (r.random() < 0.3) * r.integers(4, 30))
            if y >= H: continue
            x = int((r.integers(0, W) + f * 2) % W); ln = int(r.integers(3, 9))
            lv = WATER[0] if y < 9 else WATER[2] if y < 20 else WATER[3] if y < 32 else WATER[4]
            for k in range(ln):
                img[y, (x + k) % W, :3] = lv
        # foam flecks just under the edge
        for _ in range(40):
            x = int(r.integers(0, W)); y = edge[x] + 3 + int(abs(r.normal(0, 2)))
            if y < H: img[y, x, :3] = FOAM[1]
        frames.append(img)
    return np.concatenate(frames, 1)


def foamring(W=48, H=10):
    frames = []
    for f in range(N):
        img = np.zeros((H, W, 4), np.uint8); r = np.random.default_rng(7 + f)
        cx = W / 2
        for x in range(W):
            half = np.sqrt(max(0, 1 - ((x - cx) / (W / 2)) ** 2))
            h = int(round(half * (H - 3) + (r.random() < 0.4)))
            for y in range(H - 1 - h, H):
                if r.random() < 0.14 and y < H - 2: continue  # broken
                img[y, x, :3] = FOAM[0] if y > H - 1 - h + 1 or (x + f) % 2 else FOAM[1]; img[y, x, 3] = 255
        # a couple of flying droplets
        for _ in range(6):
            x = int(r.integers(2, W - 2)); y = int(r.integers(0, H - 5))
            img[y, x] = (*FOAM[0], 255)
        frames.append(img)
    return np.concatenate(frames, 1)


def mist(W=44, H=28):
    """rising, expanding puffs made of 3 stepped tones; the outer ring dithers out instead of fading"""
    frames = []
    puffs = [(10, 1.0, 0), (24, 0.8, 3), (34, 0.9, 5), (18, 0.7, 6)]
    for f in range(N):
        img = np.zeros((H, W, 4), np.uint8)
        for (px_, sz, ph) in puffs:
            t = ((f + ph) % N) / N
            cx, cy = px_, H - 4 - t * (H - 10)
            rad = (3 + t * 6) * sz * (1.0 if t < 0.75 else 0.6)
            for y in range(H):
                for x in range(W):
                    d = np.hypot(x - cx, (y - cy) * 1.2)
                    if d > rad: continue
                    q = d / rad
                    if t > 0.75 and q > 0.5: continue          # shrink away, no dither haze
                    col = FOAM[0] if q < 0.45 else FOAM[1] if q < 0.75 else FOAM[2]
                    if img[y, x, 3] == 0 or col == FOAM[0]:
                        img[y, x, :3] = col; img[y, x, 3] = 255
        frames.append(img)
    return np.concatenate(frames, 1)


if __name__ == '__main__':
    Image.fromarray(basin()).save(os.path.join(px.OUT, 'basin.png'))
    Image.fromarray(foamring()).save(os.path.join(px.OUT, 'foamring.png'))
    Image.fromarray(mist()).save(os.path.join(px.OUT, 'mist.png'))
    # solid chain-link: fill the see-through mesh with a dark backing so the panel reads as a finished object
    for k in ('fence', 'fence-plain'):
        a = np.array(Image.open(os.path.join(px.OUT, k + '.png')).convert('RGBA'))
        hole = a[..., 3] == 0
        hole[:10] = False; hole[49:] = False; hole[:, :6] = False; hole[:, 53:] = False
        a[hole] = (28, 36, 44, 255)
        Image.fromarray(a).save(os.path.join(px.OUT, k + '-solid.png'))
    print('ok')
