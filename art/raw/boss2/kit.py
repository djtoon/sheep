"""Shared pixel-cleaning kit for the stage-2/3 bosses (copy of the stage-1 boss pipeline, extended material ramps).
load -> smooth (hi-res median) -> down (premultiplied area) -> lock (per-material hard ramps) -> deorphan -> crisp -> outline."""
import numpy as np, colorsys
from PIL import Image, ImageFilter

OUT = np.array([0x1a, 0x14, 0x20], np.uint8)
H = lambda s: tuple(int(s[i:i + 2], 16) for i in (0, 2, 4))
RAMPS = {
    'concrete': [H('2e2a28'), H('4d4843'), H('6f685f'), H('948b7e'), H('b9ae9c'), H('dcd2bd'), H('f0ead8')],
    'steel':    [H('16151c'), H('262630'), H('3a3b46'), H('555864'), H('7a7f8c'), H('a6abb6'), H('d0d4dc')],
    'yellow':   [H('4a3812'), H('8a6a1c'), H('c99722'), H('f0c54a')],
    'red':      [H('3e0c0e'), H('741414'), H('b01e18'), H('e23a20'), H('ff7a40'), H('ffd89a')],
    'olive':    [H('23271a'), H('363c24'), H('4c5433'), H('656e42'), H('838a55'), H('a6aa70'), H('c9c996')],
    'moss':     [H('1b2e16'), H('2f5020'), H('4c7a2a'), H('78a83a'), H('b0e060')],
    'amber':    [H('7a4a14'), H('d88a2a'), H('ffd070'), H('fff4c8')],
    'purple':   [H('1e1026'), H('34183f'), H('4e2658'), H('6c3a75'), H('8e5494'), H('b07ab4'), H('d2a6d4')],
    'cyan':     [H('0a2a30'), H('0f4a52'), H('13727a'), H('20a8ac'), H('46dcd8'), H('a8fff4')],
}


def classify(r, g, b):
    h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255); h *= 360
    if s > 0.45 and v > 0.25 and (h < 18 or h > 340): return 'red'
    if s > 0.5 and v > 0.75 and 18 <= h < 50: return 'amber'
    if s > 0.45 and 30 <= h < 54: return 'yellow'
    if s > 0.35 and 150 <= h < 200 and v > 0.2: return 'cyan'
    if s > 0.22 and 255 <= h < 340: return 'purple'
    if s > 0.45 and 88 <= h < 150: return 'moss'
    if s > 0.18 and 40 <= h < 100: return 'olive'
    if v < 0.22: return 'steel'
    return 'concrete' if (r >= b - 2) else 'steel'


def lock(a, contrast=1.2):
    o = a.copy(); m = a[..., 3] > 0
    ys, xs = np.where(m)
    mats = np.empty(len(ys), object); lum = np.zeros(len(ys))
    for k, (y, x) in enumerate(zip(ys, xs)):
        r, g, b = (int(c) for c in a[y, x, :3]); mats[k] = classify(r, g, b); lum[k] = 0.3 * r + 0.59 * g + 0.11 * b
    for name, ramp in RAMPS.items():
        sel = mats == name
        if not sel.any(): continue
        L = lum[sel]; mu = L.mean(); L = mu + (L - mu) * contrast
        rl = np.array([0.3 * r + 0.59 * g + 0.11 * b for r, g, b in ramp])
        idx = np.abs(L[:, None] - rl[None, :]).argmin(1)
        o[ys[sel], xs[sel], :3] = np.array(ramp, np.uint8)[idx]
    return o


def load(f, thr=200):
    a = np.array(Image.open(f).convert('RGBA')).astype(np.float32) / 255
    a[..., 3] = (a[..., 3] >= thr / 255).astype(np.float32)
    return a


def smooth(a, k=3, n=1):
    im = Image.fromarray((a[..., :3] * 255).astype(np.uint8))
    for _ in range(n): im = im.filter(ImageFilter.MedianFilter(k))
    o = a.copy(); o[..., :3] = np.array(im).astype(np.float32) / 255
    return o


def down(a, w, h):
    pre = np.concatenate([a[..., :3] * a[..., 3:4], a[..., 3:4]], -1)
    s = np.array(Image.fromarray((pre * 255).astype(np.uint8), 'RGBA').resize((w, h), Image.BOX)).astype(np.float32) / 255
    al = s[..., 3:4]; col = np.where(al > 1e-3, s[..., :3] / np.maximum(al, 1e-3), 0)
    out = np.zeros((h, w, 4), np.uint8)
    out[..., :3] = (np.clip(col, 0, 1) * 255).astype(np.uint8); out[..., 3] = np.where(al[..., 0] >= 0.5, 255, 0)
    return out


def deorphan(o, passes=2):
    h, w = o.shape[:2]
    for _ in range(passes):
        src = o.copy(); key = (src[..., 0].astype(np.int32) << 16) | (src[..., 1].astype(np.int32) << 8) | src[..., 2]
        for y in range(1, h - 1):
            for x in range(1, w - 1):
                if src[y, x, 3] == 0: continue
                nb = [(y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)]
                if any(src[j, i, 3] == 0 for j, i in nb): continue
                ks = [key[j, i] for j, i in nb]
                if key[y, x] in ks: continue
                best = max(set(ks), key=ks.count)
                if ks.count(best) >= 3:
                    j, i = nb[ks.index(best)]; o[y, x, :3] = src[j, i, :3]
    return o


def crisp(o):
    lum = o[..., :3].astype(np.float32) @ np.array([0.3, 0.59, 0.11]); m = o[..., 3] > 0; out = o.copy()
    h, w = lum.shape
    for y in range(1, h - 1):
        for x in range(1, w - 1):
            if not m[y, x]: continue
            c = lum[y, x]
            if (lum[y, x - 1] - c > 26 and lum[y, x + 1] - c > 26) or (lum[y - 1, x] - c > 26 and lum[y + 1, x] - c > 26):
                out[y, x, :3] = (out[y, x, :3] * 0.72).astype(np.uint8)
    return out


def outline(a):
    m = a[..., 3] > 0; n = np.zeros_like(m)
    n[1:] |= m[:-1]; n[:-1] |= m[1:]; n[:, 1:] |= m[:, :-1]; n[:, :-1] |= m[:, 1:]
    r = n & ~m; o = a.copy(); o[r, :3] = OUT; o[r, 3] = 255
    return o


def pad(a, p=1):
    h, w = a.shape[:2]; o = np.zeros((h + 2 * p, w + 2 * p, 4), np.uint8); o[p:p + h, p:p + w] = a
    return o


def clean(a):
    """full clean of a downsampled RGBA sprite"""
    o = lock(a); o[a[..., 3] == 0] = 0
    return crisp(deorphan(o))


def to_game(a_hi, box, S):
    """crop hi-res float RGBA to box (x0,y0,x1,y1) and downsample by scale S -> uint8 RGBA"""
    x0, y0, x1, y1 = box
    w, h = round((x1 - x0) / S), round((y1 - y0) / S)
    return down(smooth(a_hi[y0:y1, x0:x1]), w, h)


def rotate_hi(a_hi, pivot, ang, size):
    """paste hi-res float RGBA with pivot at canvas centre, rotate (deg, CCW), return float RGBA canvas (size x size)"""
    im = Image.fromarray((a_hi * 255).astype(np.uint8), 'RGBA')
    cv = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    cv.paste(im, (int(size / 2 - pivot[0]), int(size / 2 - pivot[1])), im)
    cv = cv.rotate(ang, resample=Image.NEAREST, center=(size / 2, size / 2))
    return np.array(cv).astype(np.float32) / 255


def sheet(frames, path):
    Image.fromarray(np.concatenate(frames, 1)).save(path)


# ---------------------------------------------------------------- round-2 readability pass (boss2 / boss3)
def matmap(a):
    """material name per opaque pixel (on an un-locked RGBA)"""
    m = np.full(a.shape[:2], '', object)
    ys, xs = np.where(a[..., 3] > 0)
    for y, x in zip(ys, xs): m[y, x] = classify(*(int(c) for c in a[y, x, :3]))
    return m


def pop(a, rim=None, rim_mats=('olive',), lift=(), darken=('steel',), lift_steps=1):
    """a: downsampled RGBA (not yet locked). Lock to ramps, then:
       lift: lit-plate materials shifted up the ramp (min 3 distinct values kept);
       darken: joint materials pushed toward near-black, keeping one grey highlight on their top edge;
       rim: top-edge pixels of rim_mats get a warm/violet rim colour."""
    mats = matmap(a)
    o = lock(a); o[a[..., 3] == 0] = 0
    o = deorphan(o)
    op = o[..., 3] > 0
    def idx_of(name, px):
        ramp = np.array(RAMPS[name]); return int(np.abs(ramp.astype(int) - px.astype(int)).sum(1).argmin())
    h, w = op.shape
    out = o.copy()
    for y in range(h):
        for x in range(w):
            if not op[y, x]: continue
            m = mats[y, x]; top = y == 0 or not op[y - 1, x]
            if m in lift:
                r = RAMPS[m]; i = idx_of(m, o[y, x, :3]); out[y, x, :3] = r[min(len(r) - 1, i + lift_steps)]
            elif m in darken:
                r = RAMPS[m]; i = idx_of(m, o[y, x, :3])
                if top and i >= 2: out[y, x, :3] = r[4]
                else: out[y, x, :3] = r[max(0, min(i, 2) - 1)]
            if rim is not None and top and m in rim_mats: out[y, x, :3] = rim
    return crisp(out)


def outline2(a):
    """2px near-black outline (inner ring = OUT, outer ring = OUT)"""
    return outline(outline(pad(a, 2)))


def gray(img):
    g = np.dot(img[..., :3].astype(np.float32), [0.3, 0.59, 0.11]).astype(np.uint8)
    o = img.copy(); o[..., 0] = o[..., 1] = o[..., 2] = g; return o


def flatten(o, mat='olive', tones=(2, 3, 4), k=1):
    """clean 3-tone planes: pixels whose (2k+1)^2 window is all `mat` get the ramp tone nearest the window median;
    plate edges, bolts and seams (anything with a non-`mat` neighbour) keep their detail."""
    ramp = np.array(RAMPS[mat]); rl = ramp.astype(float) @ [0.3, 0.59, 0.11]
    rgb = o[..., :3].astype(int); h, w = o.shape[:2]
    ismat = np.zeros((h, w), bool)
    for y in range(h):
        for x in range(w):
            if o[y, x, 3] and (np.abs(ramp - rgb[y, x]).sum(1).min() == 0): ismat[y, x] = True
    lum = o[..., :3].astype(float) @ [0.3, 0.59, 0.11]; out = o.copy()
    for y in range(k, h - k):
        for x in range(k, w - k):
            if not ismat[y - k:y + k + 1, x - k:x + k + 1].all(): continue
            med = np.median(lum[y - k:y + k + 1, x - k:x + k + 1])
            t = min(tones, key=lambda i: abs(rl[i] - med)); out[y, x, :3] = ramp[t]
    # lone scratch / grime pixels inside a plate (not red lamps) take the plate tone
    for y in range(1, h - 1):
        for x in range(1, w - 1):
            if ismat[y, x] or not o[y, x, 3]: continue
            nb = ismat[y - 1:y + 2, x - 1:x + 2].sum()
            if nb >= 6 and classify(*rgb[y, x]) != 'red':
                vals = [out[j, i, :3] for j in range(y - 1, y + 2) for i in range(x - 1, x + 2) if ismat[j, i]]
                out[y, x, :3] = vals[len(vals) // 2]
    return out
