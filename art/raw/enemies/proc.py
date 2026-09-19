"""Enemy sprite pipeline: split AI sheets into frames, sample the native pixel grid, palette-lock, outline, pack.
usage: python art/raw/enemies/proc.py split SHEET OUTPREFIX --px 7.5 [--noflash]
"""
import sys, os, argparse
import numpy as np
from PIL import Image
from scipy import ndimage as ndi

OUT = (26, 20, 32)  # outline 1a1420


def load(p):
    return np.array(Image.open(p).convert('RGBA')).astype(np.int32)


def split(a, minw=20, gap=6, athr=160):
    m = a[..., 3] > athr
    cols = m.sum(0) > 0
    # group column runs separated by >= gap empty columns
    runs, x, W = [], 0, len(cols)
    while x < W:
        if cols[x]:
            s = x
            e = x
            while x < W:
                if cols[x]: e = x; x += 1
                elif x - e < gap: x += 1
                else: break
            runs.append((s, e + 1))
        else:
            x += 1
    return [r for r in runs if r[1] - r[0] >= minw]


def sample(a, px, athr=160, ox=None, oy=None):
    """sample the native pixel grid: for each cell take the median colour of the central area."""
    m = a[..., 3] > athr
    ys, xs = np.where(m)
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    # anchor grid at the bottom-left of the bbox
    H = int(round((y1 - y0) / px)); W = int(round((x1 - x0) / px))
    out = np.zeros((H, W, 4), np.uint8)
    for j in range(H):
        for i in range(W):
            cy0 = y1 - (H - j) * px; cx0 = x0 + i * px
            sy0, sy1 = int(cy0 + px * .25), int(cy0 + px * .75) + 1
            sx0, sx1 = int(cx0 + px * .25), int(cx0 + px * .75) + 1
            blk = a[max(sy0, 0):sy1, max(sx0, 0):sx1].reshape(-1, 4)
            if not len(blk): continue
            on = blk[blk[:, 3] > athr]
            if len(on) * 2 < len(blk): continue
            out[j, i, :3] = np.median(on[:, :3], 0)
            out[j, i, 3] = 255
    return out


def outline(fr, col=OUT):
    h, w = fr.shape[:2]
    pad = np.zeros((h + 2, w + 2, 4), np.uint8); pad[1:-1, 1:-1] = fr
    m = pad[..., 3] > 0
    n = np.zeros_like(m)
    n[1:, :] |= m[:-1, :]; n[:-1, :] |= m[1:, :]; n[:, 1:] |= m[:, :-1]; n[:, :-1] |= m[:, 1:]
    ring = n & ~m
    pad[ring] = (*col, 255)
    return pad


def darken_edges(fr, col=OUT, lum=70):
    """any existing near-black pixel becomes the canonical outline colour"""
    rgb = fr[..., :3].astype(int)
    L = rgb.mean(-1)
    sel = (fr[..., 3] > 0) & (L < lum) & (np.abs(rgb - rgb.mean(-1, keepdims=True)).max(-1) < 30)
    fr[sel, :3] = col
    return fr


def quantize(frames, n=28, keep=()):
    allpx = np.concatenate([f[f[..., 3] > 0][:, :3] for f in frames])
    strip = Image.fromarray(allpx.reshape(1, -1, 3).astype(np.uint8))
    pal = strip.quantize(colors=n, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    out = []
    for f in frames:
        f = f.copy(); sel = f[..., 3] > 0
        px = Image.fromarray(f[sel][:, :3].reshape(1, -1, 3).astype(np.uint8))
        q = px.quantize(palette=pal, dither=Image.Dither.NONE).convert('RGB')
        f[sel, :3] = np.array(q).reshape(-1, 3)
        out.append(f)
    return out


def remove_flash(a):
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    fl = (r > 190) & (g > 110) & (b < 170) & (a[..., 3] > 0)
    a = a.copy(); a[fl, 3] = 0
    return a


def largest(a, athr=160, keepfrac=0.08):
    m = a[..., 3] > athr
    lab, n = ndi.label(ndi.binary_dilation(m, iterations=3))
    if n <= 1: return a
    sizes = ndi.sum(m, lab, range(1, n + 1))
    big = sizes.max()
    keep = np.isin(lab, [i + 1 for i, s in enumerate(sizes) if s >= big * keepfrac])
    a = a.copy(); a[~keep, 3] = 0
    return a


def to_img(f, scale=1):
    im = Image.fromarray(f.astype(np.uint8), 'RGBA')
    return im.resize((im.width * scale, im.height * scale), Image.NEAREST) if scale > 1 else im


def cells(frames, cw, ch, anchors=None):
    """place frames in equal cells: bottom aligned, anchor x (column in frame) at cell centre"""
    sheet = np.zeros((ch, cw * len(frames), 4), np.uint8)
    for k, f in enumerate(frames):
        h, w = f.shape[:2]
        ax = anchors[k] if anchors else w // 2
        x0 = k * cw + cw // 2 - ax; y0 = ch - h
        for j in range(h):
            for i in range(w):
                if f[j, i, 3] and 0 <= x0 + i - k * cw < cw and 0 <= y0 + j:
                    sheet[y0 + j, x0 + i] = f[j, i]
    return sheet


def show(frames, path, scale=4, bg=(90, 120, 70)):
    W = sum(f.shape[1] + 2 for f in frames); H = max(f.shape[0] for f in frames)
    c = Image.new('RGBA', (W, H), (*bg, 255)); x = 0
    for f in frames:
        c.alpha_composite(to_img(f), (x, H - f.shape[0])); x += f.shape[1] + 2
    c.resize((W * scale, H * scale), Image.NEAREST).save(path)


def split_n(a, n, athr=160, win=0.18):
    m = a[..., 3] > athr
    cov = m.sum(0).astype(float)
    xs = np.where(cov > 0)[0]; L, R = xs.min(), xs.max() + 1
    step = (R - L) / n
    bounds = [L]
    for k in range(1, n):
        c = int(L + k * step); w = int(step * win)
        seg = cov[c - w:c + w]
        bounds.append(c - w + int(np.argmin(seg)))
    bounds.append(R)
    return [(bounds[k], bounds[k + 1]) for k in range(n)]


def pitch(a, lo=5, hi=12):
    """estimate native pixel size from edge periodicity"""
    rgb = a[..., :3].astype(float) * (a[..., 3:4] > 160)
    best = None
    for axis in (0, 1):
        d = np.abs(np.diff(rgb, axis=axis)).sum(-1).sum(1 - axis)
        d = d - d.mean()
        sc = []
        for p10 in range(lo * 10, hi * 10 + 1):
            p = p10 / 10; ph = np.exp(2j * np.pi * np.arange(len(d)) / p)
            sc.append((abs((d * ph).sum()), p))
        sc.sort(reverse=True); print('axis', axis, sc[:3])


def grid_sample(a, px, athr=160, steps=6):
    """sample at native pitch px, choosing the grid phase with minimal within-cell colour variance"""
    m = a[..., 3] > athr
    ys, xs = np.where(m)
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    best = None
    for oy in np.linspace(0, px, steps, endpoint=False):
        for ox in np.linspace(0, px, steps, endpoint=False):
            H = int(np.ceil((y1 - y0 + px) / px)); W = int(np.ceil((x1 - x0 + px) / px))
            cost = 0.0
            for j in range(0, H, 2):
                for i in range(0, W, 2):
                    cy, cx = y0 - px + oy + j * px, x0 - px + ox + i * px
                    blk = a[max(int(cy + 1), 0):max(int(cy + px - 1), 0), max(int(cx + 1), 0):max(int(cx + px - 1), 0)]
                    if blk.size == 0: continue
                    b = blk.reshape(-1, 4); b = b[b[:, 3] > athr]
                    if len(b) > 2: cost += b[:, :3].var(0).sum() * len(b)
            if best is None or cost < best[0]: best = (cost, oy, ox, H, W)
    _, oy, ox, H, W = best
    out = np.zeros((H, W, 4), np.uint8)
    for j in range(H):
        for i in range(W):
            cy, cx = y0 - px + oy + j * px, x0 - px + ox + i * px
            sy0, sy1 = int(cy + px * .2), int(cy + px * .8) + 1
            sx0, sx1 = int(cx + px * .2), int(cx + px * .8) + 1
            blk = a[max(sy0, 0):max(sy1, 0), max(sx0, 0):max(sx1, 0)].reshape(-1, 4)
            if not len(blk): continue
            on = blk[blk[:, 3] > athr]
            if len(on) * 2 < len(blk): continue
            out[j, i, :3] = np.median(on[:, :3], 0); out[j, i, 3] = 255
    # trim
    al = out[..., 3] > 0
    r = np.where(al.any(1))[0]; c = np.where(al.any(0))[0]
    return out[r.min():r.max() + 1, c.min():c.max() + 1]


def head_x(f, rows=10):
    al = f[:rows, :, 3] > 0
    xs = np.where(al)[1]
    return int(round(xs.mean())) if len(xs) else f.shape[1] // 2
