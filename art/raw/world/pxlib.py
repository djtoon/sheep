import numpy as np
from PIL import Image
from scipy import ndimage

def load(p): return np.array(Image.open(p).convert('RGBA')).astype(np.float32)/255

def down(a, w, h):
    """premultiplied box downsample of float RGBA array -> float RGBA"""
    rgb = a[..., :3]*a[..., 3:4]
    pre = np.concatenate([rgb, a[..., 3:4]], -1)
    im = Image.fromarray((pre*255+.5).astype(np.uint8), 'RGBA').resize((w, h), Image.BOX)
    s = np.array(im).astype(np.float32)/255
    al = s[..., 3:4]
    col = np.where(al > 1e-3, s[..., :3]/np.maximum(al, 1e-3), 0)
    return np.concatenate([np.clip(col, 0, 1), al], -1)

def quant(a, colors=16, athr=0.5, palette=None):
    """float RGBA -> uint8 RGBA with hard alpha and limited palette"""
    al = a[..., 3] >= athr
    rgb = (a[..., :3]*255+.5).astype(np.uint8)
    out = np.zeros(a.shape[:2]+(4,), np.uint8)
    sel = rgb[al]
    if len(sel):
        strip = Image.fromarray(sel.reshape(1, -1, 3))
        if palette is not None:
            pim = Image.new('P', (1, 1)); flat = list(np.array(palette, np.uint8).reshape(-1))
            pim.putpalette(flat + flat[:3]*(256-len(flat)//3))
            qs = strip.quantize(palette=pim, dither=Image.Dither.NONE).convert('RGB')
        else:
            qs = strip.quantize(colors=colors, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE).convert('RGB')
        out[al, :3] = np.array(qs).reshape(-1, 3)
    out[..., 3] = np.where(al, 255, 0)
    return out

def bbox(a, thr=0.75):
    ys, xs = np.where(a[..., 3] > thr)
    return xs.min(), ys.min(), xs.max()+1, ys.max()+1

def save(arr, p): Image.fromarray(arr, 'RGBA').save(p); print('saved', p, arr.shape[1], 'x', arr.shape[0])

def components(a, thr=0.75, minpix=2000):
    lab, n = ndimage.label(a[..., 3] > thr)
    sl = ndimage.find_objects(lab)
    out = []
    for i, s in enumerate(sl):
        if (lab[s] == i+1).sum() >= minpix: out.append((s[1].start, s[0].start, s[1].stop, s[0].stop))
    return sorted(out)

def paste(dst, src, x, y, wrap=True):
    """alpha-over paste uint8 RGBA src into dst at (x,y); wraps horizontally"""
    H, W = dst.shape[:2]; h, w = src.shape[:2]
    for dx in ([0, -W, W] if wrap else [0]):
        x0 = x+dx
        if x0+w <= 0 or x0 >= W: continue
        sx0 = max(0, -x0); sx1 = min(w, W-x0)
        sy0 = max(0, -y); sy1 = min(h, H-y)
        s = src[sy0:sy1, sx0:sx1]; d = dst[y+sy0:y+sy1, x0+sx0:x0+sx1]
        m = s[..., 3] > 0
        d[m] = s[m]

def pieces(a, thr=0.5, minpix=2000):
    """isolated component crops, alpha masked to that component only (no neighbour bleed)"""
    lab, n = ndimage.label(a[..., 3] > thr)
    out = []
    for i, s in enumerate(ndimage.find_objects(lab)):
        m = lab[s] == i + 1
        if m.sum() < minpix: continue
        c = a[s].copy(); c[..., 3] = np.where(ndimage.binary_dilation(m, iterations=2), c[..., 3], 0)
        out.append((s[1].start, c))
    return [c for _, c in sorted(out, key=lambda t: t[0])]

def crispen(a, radius=1.0, percent=110, threshold=2):
    """unsharp-mask the colour of a small float RGBA image so box-downscaled detail regains hard value steps"""
    from PIL import ImageFilter
    rgb = Image.fromarray((np.clip(a[..., :3], 0, 1) * 255 + .5).astype(np.uint8), 'RGB')
    rgb = rgb.filter(ImageFilter.UnsharpMask(radius=radius, percent=percent, threshold=threshold))
    b = a.copy(); b[..., :3] = np.array(rgb).astype(np.float32) / 255; return b

def outline(im, col, inner=False):
    """1px dark outline around the opaque silhouette (outside ring, or inside edge if inner)"""
    m = im[..., 3] > 0
    n = np.zeros_like(m)
    n[1:, :] |= m[:-1, :]; n[:-1, :] |= m[1:, :]; n[:, 1:] |= m[:, :-1]; n[:, :-1] |= m[:, 1:]
    out = im.copy()
    if inner:
        e = np.zeros_like(m)
        e[1:, :] |= ~m[:-1, :]; e[:-1, :] |= ~m[1:, :]; e[:, 1:] |= ~m[:, :-1]; e[:, :-1] |= ~m[:, 1:]
        ring = m & e
    else:
        ring = n & ~m
    out[ring] = col
    return out

def pixelart(a, w, h, ncol=12, athr=0.5, orphan_pass=2, pal_fn=None):
    """Hand-pixel-style reduction: palette-index the full-res source, then take the MODE index per
    target cell (no colour averaging -> no in-between mush), majority alpha, orphan cleanup.
    pal_fn(palette float Nx3) -> recoloured palette (value treatment applied per colour, keeps count)."""
    H, W = a.shape[:2]
    opaque = a[..., 3] > 0.5
    rgb = (np.clip(a[..., :3], 0, 1) * 255).astype(np.uint8)
    sel = rgb[opaque]
    strip = Image.fromarray(sel.reshape(1, -1, 3))
    q = strip.quantize(colors=ncol, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    pal = np.array(q.getpalette()[:ncol * 3], np.float32).reshape(-1, 3) / 255
    idx = np.full((H, W), -1, np.int32); idx[opaque] = np.array(q).reshape(-1)
    ys = np.linspace(0, H, h + 1).round().astype(int); xs = np.linspace(0, W, w + 1).round().astype(int)
    out = np.full((h, w), -1, np.int32)
    for j in range(h):
        for i in range(w):
            c = idx[ys[j]:ys[j + 1], xs[i]:xs[i + 1]]
            # shrink cell to its central 70% so edge bleed between cells doesn't vote
            ch, cw = c.shape; sy, sx = int(ch * .15), int(cw * .15)
            c = c[sy:ch - sy or None, sx:cw - sx or None].ravel()
            if c.size == 0: continue
            o = c[c >= 0]
            if o.size < c.size * athr: continue
            out[j, i] = np.bincount(o, minlength=ncol).argmax()
    for _ in range(orphan_pass):
        pad = np.pad(out, 1, constant_values=-2)
        nb = np.stack([pad[:-2, 1:-1], pad[2:, 1:-1], pad[1:-1, :-2], pad[1:-1, 2:]])
        for j in range(h):
            for i in range(w):
                v = out[j, i]; n = nb[:, j, i]
                if (n == v).any(): continue
                vals, cnt = np.unique(n, return_counts=True)
                k = cnt.argmax()
                if cnt[k] >= 3 or v >= 0 and cnt[k] >= 2 and vals[k] >= 0:
                    out[j, i] = -1 if vals[k] == -2 else vals[k]
    if pal_fn is not None: pal = np.clip(pal_fn(pal), 0, 1)
    res = np.zeros((h, w, 4), np.uint8)
    m = out >= 0
    res[m, :3] = (pal[out[m]] * 255 + .5).astype(np.uint8); res[m, 3] = 255
    return res

def flatten(im, n=3, cuts=(0.35, 0.72), passes=3, rim=True, keep=None, spread=0.10):
    """Posterize an RGBA uint8 layer into n flat tones (by luminance quantile), majority-filter the tone map
    to kill texture noise (bigger shapes), add a light rim on the top silhouette edge. keep: bool mask of pixels
    left untouched (e.g. waterfalls)."""
    a = im.copy(); m = a[..., 3] > 0
    if keep is None: keep = np.zeros(m.shape, bool)
    work = m & ~keep
    lum = a[..., :3].astype(float) @ np.array([.3, .59, .11])
    qs = np.quantile(lum[work], cuts)
    lvl = np.digitize(lum, qs)
    for _ in range(passes):
        pad = np.pad(np.where(work, lvl, -1), 1, constant_values=-1)
        cnt = np.zeros((n,) + lvl.shape, int)
        for dy in (0, 1, 2):
            for dx in (0, 1, 2):
                nb = pad[dy:dy + lvl.shape[0], dx:dx + lvl.shape[1]]
                for k in range(n): cnt[k] += (nb == k)
        lvl = np.where(work, cnt.argmax(0), lvl)
    cols = []
    for k in range(n):
        sel = work & (lvl == k)
        c = a[sel, :3].astype(float).mean(0) if sel.any() else np.array([128, 128, 128.])
        cols.append(c)
    cols = np.array(cols); mid = cols.mean(0)
    cols = np.clip(mid + (cols - mid) * (1 + spread), 0, 255)
    out = a.copy()
    for k in range(n): out[work & (lvl == k), :3] = cols[k].astype(np.uint8)
    if rim:
        top = m.copy(); top[1:] = m[1:] & ~m[:-1]
        r = work & top
        out[r, :3] = np.clip(cols[-1] * 1.08 + 10, 0, 255).astype(np.uint8)
    return out

def crisp_tone(im, n=4, cuts=(0.25, 0.5, 0.78), spread=0.18, keep=None, rim=True, under=True):
    """Crisp posterize: n flat tones by luminance (no blob filter), 1 orphan-cleanup pass,
    lit 1px lip on every up-facing edge (pixel above is transparent), dark 1px underside on down-facing edges."""
    a = im.copy(); m = a[..., 3] > 0
    if keep is None: keep = np.zeros(m.shape, bool)
    work = m & ~keep
    lum = a[..., :3].astype(float) @ np.array([.3, .59, .11])
    lvl = np.digitize(lum, np.quantile(lum[work], cuts))
    # orphan cleanup: pixel whose 4 neighbours all share another level takes it
    pad = np.pad(np.where(work, lvl, -1), 1, constant_values=-1)
    nb = np.stack([pad[:-2, 1:-1], pad[2:, 1:-1], pad[1:-1, :-2], pad[1:-1, 2:]])
    same = (nb == nb[0]).all(0) & (nb[0] >= 0) & (nb[0] != lvl)
    lvl = np.where(work & same, nb[0], lvl)
    cols = np.array([a[work & (lvl == k), :3].astype(float).mean(0) if (work & (lvl == k)).any() else [128] * 3 for k in range(n)])
    mid = cols.mean(0); cols = np.clip(mid + (cols - mid) * (1 + spread), 0, 255)
    out = a.copy()
    for k in range(n): out[work & (lvl == k), :3] = cols[k].astype(np.uint8)
    up = np.zeros_like(m); up[1:] = ~m[:-1]; up[0] = True
    dn = np.zeros_like(m); dn[:-1] = ~m[1:]
    if rim:
        r = work & up
        out[r, :3] = np.clip(cols[-1] * 1.1 + 12, 0, 255).astype(np.uint8)
    if under:
        u = work & dn & ~up
        out[u, :3] = (cols[0] * 0.85).astype(np.uint8)
    return out

def palm_px(h=40, lean=1, pal=None, seed=0):
    """Hand-pixelled coconut palm: curved trunk + 6 drooping fronds as clean pixel arcs."""
    r = np.random.default_rng(seed)
    p = pal or dict(ol=(20, 40, 30, 255), d=(34, 90, 52, 255), m=(58, 132, 66, 255), l=(110, 180, 84, 255),
                    t=(92, 70, 48, 255), tl=(130, 104, 70, 255))
    W = 40; im = np.zeros((h + 4, W, 4), np.uint8)
    cx = W // 2; top = 10
    # trunk: gentle curve
    pts = []
    for y in range(h + 3, top, -1):
        t = (h + 3 - y) / (h - top)
        x = int(round(cx - lean * 5 * (t ** 2) + lean * 2))
        pts.append((x, y))
        im[y, x] = p['t']; im[y, x + 1] = p['tl'] if y % 3 else p['t']
    hx, hy = pts[-1]
    # fronds: separate drooping arcs (parabolas) with leaflets hanging under them
    fronds = [(1.1, 0.10, 9), (0.55, 0.075, 13), (0.1, 0.07, 14)]
    for side in (-1, 1):
        for rise, droop, ln in fronds:
            ln = ln + int(r.integers(-1, 2))
            for i in range(1, ln):
                x = hx + side * i
                y = hy + int(round(-rise * i + droop * i * i))
                if not (0 <= x < W and 1 <= y < im.shape[0] - 2): continue
                im[y, x] = p['l'] if i < ln * 0.5 else p['m']
                if i % 2 == 1 and i > 1:
                    im[y + 1, x] = p['m']
                    if i > 3: im[y + 2, x] = p['d']
    for i in range(1, 5):   # short upright frond
        if hy - i >= 0: im[hy - i, hx + (i // 3)] = p['m']
    im[hy - 1:hy + 2, hx - 1:hx + 2] = p['d']; im[hy, hx] = p['t']
    return outline(im, p['ol'])
