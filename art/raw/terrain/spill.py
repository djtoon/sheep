"""Procedural pixel-art cascades (animated spritesheets) that spill off cliff edges into the pools.
Tiered: a stream pours from the lip, breaks on a mossy rock ledge in white spray, then splits and widens below.
python art/raw/terrain/spill.py  -> assets/terrain/spill.png, spill-wide.png (N frames, horizontal strip)"""
import os, sys
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(__file__))
import px

N = 12          # frames
P = 48          # vertical period of the streak pattern (pixels); frame shift = P / N = 4 px
BLUES = np.array([(22, 62, 104), (36, 96, 150), (62, 140, 196), (120, 188, 228), (196, 232, 246), (246, 252, 255)], np.uint8)
OUT = (16, 22, 26)


def streaks(w, seed):
    r = np.random.default_rng(seed)
    base = np.convolve(r.random(w + 8), np.ones(5) / 5, 'same')[4:w + 4]
    base = 1 + np.round((base - base.min()) / (np.ptp(base) + 1e-6) * 2.4).astype(int)  # 1..3
    dashes = []  # per column list of (y0, len, level)
    for x in range(w):
        d = []
        for _ in range(r.integers(2, 4)):
            d.append((int(r.integers(0, P)), int(r.integers(5, 16)), int(min(5, base[x] + r.integers(1, 3)))))
        dashes.append(d)
    return base, dashes


def frame(w, h, mask, foam, base, dashes, f):
    img = np.zeros((h, w, 4), np.uint8)
    for x in range(w):
        col = np.full(h, base[x])
        for (y0, ln, lv) in dashes[x]:
            for k in range(ln):
                y = (y0 + k + f * (P // N)) % P
                for yy in range(y, h, P):
                    col[yy] = max(col[yy], lv if k < ln - 2 else lv - 1)
        for y in range(h):
            if mask[y, x]:
                lv = min(5, col[y] + foam[y, x])
                img[y, x, :3] = BLUES[lv]
                img[y, x, 3] = 255
    # edge treatment: bright rim on the outer edge, dark outline outside
    m = img[..., 3] > 0
    edge = m & ~(np.roll(m, 1, 1) & np.roll(m, -1, 1))
    img[edge, :3] = BLUES[4]
    return img


def build(name, w, h, streams, ledge, seed):
    """streams: list of (y0, y1, xl0, xr0, xl1, xr1) trapezoids; ledge: (rock piece, x, y) drawn on top"""
    r = np.random.default_rng(seed)
    mask = np.zeros((h, w), bool)
    foam = np.zeros((h, w), int)
    for (y0, y1, a0, b0, a1, b1) in streams:
        for y in range(y0, y1):
            t = (y - y0) / max(1, y1 - y0 - 1)
            a = a0 + (a1 - a0) * t + r.integers(-1, 2) * (y % 3 == 0)
            b = b0 + (b1 - b0) * t + r.integers(-1, 2) * (y % 4 == 0)
            a = max(0, a); b = min(w, b)
            mask[y, int(round(a)):int(round(b))] = True
            if y - y0 < 3:
                foam[y, int(round(a)):int(round(b))] = 2  # white where the stream (re)starts
    rock = np.array(Image.open(os.path.join(px.OUT, ledge[0] + '.png')).convert('RGBA')) if ledge else None
    base, dashes = streaks(w, seed)
    frames = []
    for f in range(N):
        fr = frame(w, h, mask, foam, base, dashes, f)
        # spray around the ledge, animated
        rr = np.random.default_rng(seed * 100 + f)
        if rock is None:
            ledge = (None, -100, -100); rock = np.zeros((1, 1, 4), np.uint8)
        ry = ledge[2] + rock.shape[0] - 6
        for _ in range(26):
            x = int(rr.integers(ledge[1] - 6, ledge[1] + rock.shape[1] + 6)); y = int(ry - rr.integers(0, 9))
            if 0 <= x < w and 0 <= y < h:
                fr[y, x] = (*BLUES[5 if rr.random() < 0.6 else 4], 255)
        # rock ledge in front of the upper stream
        rx, ryy = max(0, ledge[1]), max(0, ledge[2])
        sub = rock[:, :, 3] > 0
        region = fr[ryy:ryy + rock.shape[0], rx:rx + rock.shape[1]]
        region[sub[:region.shape[0], :region.shape[1]]] = rock[:region.shape[0], :region.shape[1]][sub[:region.shape[0], :region.shape[1]]]
        # foam burst at the bottom
        for _ in range(40):
            x = int(rr.integers(0, w)); y = int(h - 1 - abs(rr.normal(0, 3)))
            if mask[min(h - 1, y), x] or rr.random() < 0.3:
                fr[max(0, y), x] = (*BLUES[5 if rr.random() < 0.7 else 4], 255)
        frames.append(fr)
    sheet = np.concatenate(frames, 1)
    Image.fromarray(sheet).save(os.path.join(px.OUT, name + '.png'))
    print(name, w, h, N)


def splash(name, w, h, seed):
    frames = []
    for f in range(N):
        fr = np.zeros((h, w, 4), np.uint8); rr = np.random.default_rng(seed + f * 7)
        for _ in range(int(w * 1.6)):
            x = rr.integers(0, w); ph = (f / N + rr.random()) % 1
            y = int(h - 1 - np.sin(ph * np.pi) * rr.integers(2, h))
            lv = 5 if rr.random() < 0.55 else 4 if rr.random() < 0.7 else 3
            fr[y, x] = (*BLUES[lv], 255)
            if rr.random() < 0.4 and x + 1 < w: fr[y, x + 1] = (*BLUES[lv], 255)
        # churning foam line at the bottom
        for x in range(w):
            for y in range(h - 3 - int(rr.integers(0, 3)), h):
                fr[y, x] = (*BLUES[5 if (x + y + f) % 3 else 4], 255)
        frames.append(fr)
    Image.fromarray(np.concatenate(frames, 1)).save(os.path.join(px.OUT, name + '.png'))
    print(name, w, h, N)


if __name__ == '__main__':
    build('fall-tall', 44, 100, [(0, 42, 0, 20, 1, 26), (40, 100, 2, 18, 0, 24), (42, 100, 24, 32, 26, 42)], ('rock10', 10, 32), 7)
    build('fall-curtain', 36, 84, [(0, 84, 9, 25, 2, 34)], None, 11)
    splash('splash', 56, 18, 21)
    # wide two-tier cascade: sheet of water breaks on a rock step in a white band, then fans out to the pool
    build('cascade', 128, 60, [(0, 27, 12, 116, 6, 122), (26, 60, 3, 125, 0, 128)], ('rock4', 38, 16), 31)
    splash('splash-wide', 132, 20, 41)
    # narrow spill off a cliff edge (left side; flip for the right side)
    build('spill', 48, 44, [(0, 22, 0, 18, 1, 24), (20, 44, 2, 16, 0, 20), (22, 44, 22, 30, 24, 40)], ('rock10', 10, 12), 3)
    # wider tiered cascade
    build('spill-wide', 72, 44, [(0, 20, 0, 30, 0, 38), (18, 44, 0, 22, 0, 28), (20, 44, 30, 44, 32, 62)], ('rock7', 16, 8), 5)
