"""Build all backdrop layers for Armed and Fluffy into assets/world/.
Run from repo root: python art/raw/world/build.py
Every layer is made at game scale (480x270 canvas), hard alpha, limited palette, horizontally seamless."""
import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))
from pxlib import *

RAW = 'art/raw/world/'; OUT = 'assets/world/'
os.makedirs(OUT, exist_ok=True)
rng = np.random.default_rng(7)
HAZE = np.array([150, 200, 226]) / 255.0
STEP = np.array([176, 206, 222]) / 255.0   # modest lighter/cooler value step for the close layer
OL_NEAR = (40, 56, 78, 255); OL_MID = (40, 66, 72, 255)
NEARHAZE = np.array([128, 178, 206]) / 255.0


def crop(a, thr=0.5):
    x0, y0, x1, y1 = bbox(a, thr); return a[y0:y1, x0:x1]


def scaled(a, h=None, w=None, s=None):
    H, W = a.shape[:2]
    if s: h, w = round(H * s), round(W * s)
    elif h and not w: w = round(W * h / H)
    elif w and not h: h = round(H * w / W)
    return down(a, w, h)


def haze(a, amt, col=HAZE):
    b = a.copy(); b[..., :3] = b[..., :3] * (1 - amt) + col * amt; return b


def vhaze(a, y0, y1, amt0, amt1, col=HAZE):
    """vertical haze ramp: amount goes amt0 at row y0 -> amt1 at row y1 (clamped)"""
    H = a.shape[0]; y = np.arange(H)[:, None, None]
    t = np.clip((y - y0) / max(1, y1 - y0), 0, 1); k = amt0 + (amt1 - amt0) * t
    b = a.copy(); b[..., :3] = b[..., :3] * (1 - k) + col * k; return b


def seam_path(cost):
    """min-cost vertical path through cost[h, w]; returns x index per row"""
    h, w = cost.shape; M = cost.copy(); back = np.zeros((h, w), int)
    for y in range(1, h):
        prev = np.stack([np.r_[np.inf, M[y - 1, :-1]], M[y - 1], np.r_[M[y - 1, 1:], np.inf]])
        k = prev.argmin(0); back[y] = k - 1; M[y] += prev.min(0)
    p = np.zeros(h, int); p[-1] = M[-1].argmin()
    for y in range(h - 1, 0, -1): p[y - 1] = p[y] + back[y, p[y]]
    return p


def join(A, B, ov):
    """quilt B onto the right of A with overlap ov using a min-error cut"""
    a, b = A[:, -ov:], B[:, :ov]
    diff = ((a[..., :3] * a[..., 3:4] - b[..., :3] * b[..., 3:4]) ** 2).sum(-1) + (a[..., 3] - b[..., 3]) ** 2
    diff[:, :2] += 5; diff[:, -2:] += 5   # keep the cut away from the overlap edges
    p = seam_path(diff)
    mid = b.copy()
    for y in range(a.shape[0]): mid[y, :p[y]] = a[y, :p[y]]
    return np.concatenate([A[:, :-ov], mid, B[:, ov:]], 1)


def panorama(segs, H, ov, bottoms=None):
    """segments (float RGBA, bottom-aligned into height H) -> seamless tile"""
    cols = []
    for i, s in enumerate(segs):
        c = np.zeros((H, s.shape[1], 4), np.float32); bt = (bottoms[i] if bottoms else H)
        s = s[-bt:]; c[bt - s.shape[0]:bt] = s; cols.append(c)
    S = cols[0]
    for c in cols[1:]: S = join(S, c, ov)
    # wrap: overlap end with start
    W = S.shape[1]
    wrapped = join(S[:, W - ov - 60:], S[:, :ov + 60], ov)   # tail + head
    # wrapped = tail[:-ov] + mid + head[ov:] ; put mid back at start
    mid = wrapped[:, 60:60 + ov]
    S2 = S[:, :W - ov].copy(); S2[:, :ov] = mid
    return S2


def draw_line(img, x0, y0, x1, y1, col):
    dx, dy = abs(x1 - x0), -abs(y1 - y0); sx = 1 if x0 < x1 else -1; sy = 1 if y0 < y1 else -1; e = dx + dy
    while True:
        if 0 <= y0 < img.shape[0] and 0 <= x0 < img.shape[1]: img[y0, x0] = col
        if x0 == x1 and y0 == y1: break
        e2 = 2 * e
        if e2 >= dy: e += dy; x0 += sx
        if e2 <= dx: e += dx; y0 += sy


def C(h, a=255): return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), a)


def tower(W=21, H=36, pal=None, roof='thatch'):
    p = pal or dict(ol=C('263440'), wd=C('3c4a50'), wl=C('5e6a66'), rd=C('35524c'), rl=C('587a66'),
                    win=C('ffab3c'), hot=C('ffe28a'))
    im = np.zeros((H, W, 4), np.uint8); cx = W // 2
    # legs + bracing
    top, bot = 15, H - 1
    lx0, lx1 = 4, 1; rx0, rx1 = W - 5, W - 2
    draw_line(im, lx0, top, lx1, bot, p['wl']); draw_line(im, rx0, top, rx1, bot, p['wd'])
    draw_line(im, lx0 + 1, top, lx1 + 1, bot, p['wd']); draw_line(im, rx0 - 1, top, rx1 - 1, bot, p['wd'])
    segs = [top + 1, top + 7, top + 14, bot + 1]
    for i in range(len(segs) - 1):
        ya, yb = segs[i], min(segs[i + 1], bot)
        la = round(lx0 + (lx1 - lx0) * (ya - top) / (bot - top)) + 1; lb = round(lx0 + (lx1 - lx0) * (yb - top) / (bot - top)) + 1
        ra = round(rx0 + (rx1 - rx0) * (ya - top) / (bot - top)) - 1; rb = round(rx0 + (rx1 - rx0) * (yb - top) / (bot - top)) - 1
        draw_line(im, la, ya, rb, yb, p['wd']); draw_line(im, ra, ya, lb, yb, p['ol'])
        if yb < bot: draw_line(im, lb, yb, rb, yb, p['wl'])
    # platform + railing
    im[top - 1, 1:W - 1] = p['wl']; im[top, 1:W - 1] = p['ol']
    for x in range(1, W - 1, 3): im[top - 4:top - 1, x] = p['wd']
    im[top - 4, 1:W - 1] = p['wd']
    # cabin
    im[top - 10:top - 1, 3:W - 3] = p['wd']
    for y in range(top - 10, top - 1, 2): im[y, 3:W - 3] = p['wl'] if y % 4 else p['wd']
    im[top - 10:top - 1, 3] = p['ol']; im[top - 10:top - 1, W - 4] = p['ol']
    for wx in (5, W - 9):
        im[top - 8:top - 5, wx:wx + 4] = p['win']; im[top - 7, wx + 1:wx + 3] = p['hot']
        im[top - 8:top - 5, wx + 2] = p['win'] if W < 18 else p['wd']
    im[top - 4, 1:W - 1] = p['wl']; im[top - 3:top - 1, 1] = p['wd']; im[top - 3:top - 1, W - 2] = p['wd']
    # roof (hip / thatch) rows 0..top-11
    rt = top - 11
    for y in range(rt + 1):
        half = 3 + round((W // 2 - 1 - 3) * y / max(rt, 1)) + (1 if y == rt else 0)
        x0, x1 = max(0, cx - half), min(W, cx + half + 1)
        im[y, x0:x1] = p['rd']; im[y, x0:max(x0 + 1, cx - 1)] = p['rl'] if y < rt else p['rd']
        im[y, x0] = p['ol']; im[y, x1 - 1] = p['ol']
    im[rt, :] = np.where(im[rt, :, 3:4] > 0, np.array(p['ol'], np.uint8), im[rt, :])
    if roof == 'thatch':
        for x in range(1, W - 1, 2):
            if im[rt, x, 3]: im[rt, x] = p['rl']
    im[0, cx - 3:cx + 4] = p['ol']
    return im


def rope_bridge(img, x0, y0, x1, y1, sag, pal=None):
    p = pal or dict(post=C('3a3430'), rope=C('5a4c3e'), plank=C('6e5a42'), dark=C('2e2a28'))
    n = x1 - x0
    def yat(x, s): t = (x - x0) / n; return round(y0 + (y1 - y0) * t + s * 4 * t * (1 - t))
    for x in range(x0, x1 + 1):
        yd = yat(x, sag); yr = yat(x, sag * 0.7) - 5
        x = x % img.shape[1]
        if True:
            img[yd, x] = p['plank'] if x % 2 else p['dark']; img[yd + 1, x] = p['dark']
            img[yr, x] = p['rope']
            if (x - x0) % 4 == 0:
                for y in range(yr + 1, yd): img[y, x] = p['rope']
    for (x, y) in ((x0, y0), (x1, y1)):
        x = x % img.shape[1]
        img[y - 7:y + 2, x - 1:x + 1] = p['post']; img[y - 7, x - 1] = p['dark']


def hz8(im, amt, col=None):
    col = NEARHAZE if col is None else col
    out = im.copy(); f = im[..., :3].astype(float) / 255 * (1 - amt) + col * amt
    out[..., :3] = (f * 255 + .5).astype(np.uint8); return out


def sat(a, k):
    b = a.copy(); g = b[..., :3].mean(-1, keepdims=True); b[..., :3] = np.clip(g + (b[..., :3] - g) * k, 0, 1); return b


BGBLUE = np.array([112, 156, 196]) / 255.0   # sky-ward blue, darker-mid so objects don't read pale
# Round 10: measured targets (art/raw/world/targets.md). Mid band in the mockups is a SATURATED, darker teal-blue
# (V~0.5, S~0.6, hue~197), not a pale haze. MIDTINT is that colour; T holds the per-layer mix amounts.
MIDTINT = np.array([34, 104, 146]) / 255.0
T = dict(cliffs=0.30, midtrees=0.26, canopy=0.20, near_k=0.85, near_amt=0.24, out0=0.34, out1=0.30, out2=0.24, far_k=1.25)
FARTINT = np.array([76, 146, 198]) / 255.0   # far band: V~0.75 S~0.6 hue~205 (measured)
# Round 12: three explicit depth steps behind the play plane, each lighter, bluer and lower-contrast than the one in front.
#  A = closest backdrop (bg-near, midset, canopy, outpost2, base)   teal,       contrast .80
#  B = middle (mid cliffs, midtrees, outpost1, far bridge)          light teal, contrast .60
#  C = far (far cliffs, hills, outpost0)                            pale blue,  contrast .45
STEPS = {'A': (0.80, 0.36, np.array([40, 110, 148]) / 255.0),
         'B': (0.78, 0.40, np.array([34, 118, 112]) / 255.0),   # r18: richer, darker teal-green mid-ground
         'C': (0.40, 0.70, np.array([166, 208, 230]) / 255.0)}
OL_STEP = {'A': (24, 44, 60, 255), 'B': (20, 56, 58, 255), 'C': (112, 156, 180, 255)}


def step(a, n):
    k, amt, col = STEPS[n]; return bgstep(a, k, amt, col)


def stepped_pal(n, pal=None):
    pal = pal or dict(post=C('3a3430'), rope=C('5a4c3e'), plank=C('6e5a42'), dark=C('2e2a28'))
    arr = np.array([list(v) for v in pal.values()], np.uint8).reshape(1, -1, 4)
    k, amt, col = STEPS[n]
    f = arr[..., :3].astype(float) / 255 * (1 - amt) + col * amt
    return {kk: (*(f[0, i] * 255 + .5).astype(int).tolist(), 255) for i, kk in enumerate(pal)}


def add_palms(im, stp, every=140, hs=(28, 40)):
    """stamp hand-pixelled palms rising from the layer's top silhouette (behind: drawn only where empty)"""
    H, W = im.shape[:2]; out = im.copy(); x = int(rng.integers(10, every))
    k = 0
    while x < W - 20:
        h = int(rng.integers(*hs)); pl = step8(palm_px(h, 1 if k % 2 else -1, seed=k + x), stp, 0.25)
        col = out[:, x + 20, 3]
        if col.any():
            ytop = int(np.argmax(col > 0))
            y = ytop + 8 - pl.shape[0]
            if y > 0:
                sub = out[y:y + pl.shape[0], x:x + pl.shape[1]]; m = (pl[..., 3] > 0) & (sub[..., 3] == 0)
                sub[m] = pl[:sub.shape[0], :sub.shape[1]][m]
        x += every + int(rng.integers(-30, 30)); k += 1
    return out


def step8(im, n, kbonus=0.0):
    k, amt, col = STEPS[n]; return bgstep8(im, min(1.0, k + kbonus), amt, col)


def bgstep(a, k=0.65, amt=0.25, col=None):
    """background value band: squeeze internal contrast around the object's mean, then shift toward sky blue"""
    col = BGBLUE if col is None else col
    b = a.copy(); m = b[..., 3] > 0.5
    mu = b[..., :3][m].mean(0) if m.any() else 0.5
    b[..., :3] = np.clip(mu + (b[..., :3] - mu) * k, 0, 1) * (1 - amt) + col * amt
    return b


def bgstep8(im, k=0.65, amt=0.25, col=None):
    f = im.astype(np.float32) / 255; f = bgstep(f, k, amt, col)
    out = im.copy(); out[..., :3] = (f[..., :3] * 255 + .5).astype(np.uint8); return out


def pxpiece(src, h=None, w=None, ncol=12):
    """hand-pixel-style reduction (mode per cell from a small palette, orphan cleanup) -> float RGBA, hard alpha"""
    H, W = src.shape[:2]
    if h and not w: w = round(W * h / H)
    if w and not h: h = round(H * w / W)
    return pixelart(src, w, h, ncol).astype(np.float32) / 255


def to_u8(a): return (np.clip(a, 0, 1) * 255 + .5).astype(np.uint8)


def quant_layer(a, colors, athr=0.5):
    return quant(a, colors, athr)


# ---------------------------------------------------------------- SKY (static, 480x270)
def build_sky():
    a = load(RAW + 'sky_1.png'); a[..., 3] = 1
    s = down(a, 480, 270)
    tgt = np.array([150, 205, 232]) / 255
    s[..., :3] = s[..., :3] * 0.55 + tgt * 0.45
    # lift the cloud bank so it peeks over the far mountains
    shift = 96
    out = np.concatenate([s[shift:], np.repeat(s[-1:], shift, 0)], 0)
    save(quant(out, 20), OUT + 'sky.png')


# ---------------------------------------------------------------- CLOUDS (drifting, 960 wide)
def build_clouds():
    a = load(RAW + 'clouds.png')
    comps = components(a, 0.5, 3000)
    W, H = 960, 110
    L = np.zeros((H, W, 4), np.uint8)
    plan = [(0, 104, 60, 28), (3, 70, 250, 6), (1, 60, 420, 40), (2, 44, 560, 14), (5, 36, 700, 50), (4, 42, 820, 20), (0, 74, 880, 60)]
    for ci, w, x, y in plan:
        x0, y0, x1, y1 = comps[ci]
        c = a[y0:y1, x0:x1]
        s = scaled(c, w=w)
        s[..., :3] = s[..., :3] * 0.75 + np.array([170, 210, 235]) / 255 * 0.25
        paste(L, quant(s, 8, 0.55), x, y)
    save(L, OUT + 'clouds.png')


# ---------------------------------------------------------------- FAR MOUNTAINS
def build_far():
    s1 = scaled(crop(load(RAW + 'far_1.png')), h=215)
    s2 = scaled(crop(load(RAW + 'far_2.png')), h=200)
    s3 = scaled(crop(load(RAW + 'far_2.png'))[:, ::-1], h=190)
    pano = panorama([s1, s2, s3], 270, 36, bottoms=[250, 250, 250])
    pano = bgstep(haze(pano, 0.40, FARTINT), T['far_k'], 0.0)
    save(flatten(quant(pano, 28), 3, (0.35, 0.75), rim=True, spread=0.25), OUT + 'far.png')


# ---------------------------------------------------------------- HILLS
def build_hills():
    s1 = scaled(crop(load(RAW + 'hills_1.png')), h=130)
    s2 = scaled(crop(load(RAW + 'hills_2.png')), h=142)
    s3 = scaled(crop(load(RAW + 'hills_1.png'))[:, ::-1], h=124)
    pano = panorama([s1, s2, s3], 160, 30)
    pano = step(pano, 'C')
    im = quant(pano, 28)
    # a few distant towers on ridge tops
    small = dict(ol=C('2c4652'), wd=C('3e5660'), wl=C('567078'), rd=C('3c5e5e'), rl=C('5a7e78'), win=C('f0a048'), hot=C('ffd890'))
    for x in ():
        t = tower(13, 26, small)
        ytop = max(int(np.argmax(im[:, c, 3] > 0)) for c in range(x + 1, x + 12))
        paste(im, t, x, ytop - 26 + 3)
    save(outline(flatten(im, 2, (0.5,)), OL_STEP['C']), OUT + 'hills.png')


# ---------------------------------------------------------------- CLIFFS with waterfalls (animated)
def wf_mask(a):
    r, g, b, al = a[..., 0], a[..., 1], a[..., 2], a[..., 3]
    mn = np.minimum(np.minimum(r, g), b); mx = np.maximum(np.maximum(r, g), b)
    return (al > 0.5) & (mn > 0.55) & (b >= r) & ((mx - mn) < 0.35)


def build_cliffs():
    W, H = 1280, 270
    pcs = []
    for f in ('cliffs_1', 'cliffs_2', 'cliffs_3'):
        pcs += pieces(load(RAW + f + '.png'), 0.5, 3000)
    # (piece, height, x, bottom, haze)
    plan = [(4, 205, 0, 266, .08), (1, 170, 150, 262, .16), (6, 214, 290, 268, .06), (8, 176, 450, 262, .15),
            (3, 200, 600, 266, .08), (7, 160, 770, 258, .18), (0, 210, 910, 268, .06), (5, 178, 1085, 262, .14)]
    layer = np.zeros((H, W, 4), np.float32)
    anim = np.zeros((H, W), bool)
    placed = []
    for pi, h, x, bt, hz in sorted(plan, key=lambda p: -p[4]):   # far (hazier) first
        s = step(pxpiece(pcs[pi % len(pcs)], h=h, ncol=12), 'B')
        hh, ww = s.shape[:2]; y = bt - hh
        m = s[..., 3] >= 0.5
        wm = wf_mask(scaled(pcs[pi % len(pcs)], h=h)) & m
        for dx in (0, -W, W):
            xs = x + dx
            if xs + ww <= 0 or xs >= W: continue
            sx0, sx1 = max(0, -xs), min(ww, W - xs)
            sub = layer[max(0, y):y + hh, xs + sx0:xs + sx1]
            mm = m[max(0, -y):, sx0:sx1]
            sub[mm] = s[max(0, -y):, sx0:sx1][mm]
            am = anim[max(0, y):y + hh, xs + sx0:xs + sx1]
            am[mm] = wm[max(0, -y):, sx0:sx1][mm]
        placed.append((x, y, ww, hh))
    base = outline(crisp_tone(quant(layer, 64), 4, keep=anim), OL_STEP['B'])
    # towers on some cliff tops, rope bridges between neighbours
    def top_at(img, x):
        col = img[:, x % W, 3]; return int(np.argmax(col > 0)) if col.any() else H
    pre = base.copy()
    pl = sorted(placed)
    for i, fx in ((3, .3),):   # one tower per tile (round 17: max 2 towers on screen)
        xa, ya_, wa, ha = pl[i]; x = int(xa + wa * fx)
        yt = max(top_at(base, c) for c in range(x + 4, x + 17))
        paste(base, outline(step8(tower(21, 40), 'B', 0.15), OL_STEP['B']), x, yt - 40 + 5)
    for i in range(len(pl)):
        (xa, ya_, wa, ha), (xb, yb_, wb, hb) = pl[i], pl[(i + 1) % len(pl)]
        if xb < xa: xb += W
        yy = max(ya_, yb_) + 26
        mid = (xa + wa + xb) // 2
        x0 = mid
        while x0 > mid - 120 and pre[yy, x0 % W, 3] == 0: x0 -= 1
        x1 = mid
        while x1 < mid + 120 and pre[yy + 3, x1 % W, 3] == 0: x1 += 1
        if x1 - x0 < 12 or x1 - x0 > 150 or i % 2: continue
        rope_bridge(base, x0 + 2, yy, x1 - 2, yy + 3, 7, stepped_pal('B'))
    anim &= (base == pre).all(-1)
    save(base, OUT + 'cliffs.png')
    wf_frames(base, anim, 'cliffs', ('8ab8dc', 'bcdcf2', 'e6f4fc', 'ffffff'))


# ---------------------------------------------------------------- CANOPY (mid-ground palms + jungle)
def build_canopy():
    segs = []
    for f, h in (('canopy_1', 136), ('canopy_2', 146), ('canopyB_1', 140), ('canopyB_2', 130)):
        if os.path.exists(RAW + f + '.png'):
            segs.append(pxpiece(crop(load(RAW + f + '.png')), h=h, ncol=16))
    pano = panorama(segs, 160, 34)
    pano = step(pano, 'A')
    im = quant(pano, 40)
    # carve rounded dips in the canopy band (periodic, so the tile stays seamless) so the plane behind shows through:
    # a smooth window w(x) blends full height into a low line of round tree-top bumps
    Wd, Hd = im.shape[1], im.shape[0]; xs = np.arange(Wd)
    w = np.clip((np.sin(2 * np.pi * xs / Wd * 3 + 0.4) + 0.3) * 1.1, 0, 1)
    w = w * w * (3 - 2 * w)
    base_cut = (Hd - 22) * (1 - w)          # row above which to cut (0 = keep all)
    cut = np.full(Wd, 1e9)
    cx = 0
    while cx < Wd + 30:
        r = int(rng.integers(9, 17))
        c0 = base_cut[cx % Wd] + r * 0.6       # dome centre row
        for x in range(cx - r, cx + r + 1):
            cut[x % Wd] = min(cut[x % Wd], c0 - np.sqrt(max(0, r * r - (x - cx) ** 2)))
        cx += int(rng.integers(10, 17))
    for x in range(Wd):
        k = int(round(cut[x]))
        if w[x] < 0.98 and k > 0: im[:k, x] = 0
    lab, n = ndimage.label(im[..., 3] > 0)
    big = np.bincount(lab.ravel()); big[0] = 0
    im[(big[lab] < 40)] = 0
    im = crisp_tone(im, 4)
    im = add_palms(im, 'A', every=150, hs=(30, 44))
    save(outline(im, OL_STEP['A']), OUT + 'canopy.png')


# ---------------------------------------------------------------- BASE strip (world-placed, late stage)
def build_base():
    parts = [(mast_px(98), 0), (bunker_px(64, 34), 8), (fence_px(80), 0), (tanks_px(), 6),
             (tower(23, 60), 4), (bunker_px(52, 28), 6), (fence_px(64), 0), (mast_px(84), 10)]
    H = max(p.shape[0] for p, _ in parts)
    W = sum(p.shape[1] + g for p, g in parts) + 20
    S = np.zeros((H, W, 4), np.uint8); x = 10
    for p_, g in parts:
        x += g; paste(S, p_, x, H - p_.shape[0], wrap=False); x += p_.shape[1]
    S = step8(S, 'B', 0.3)
    save(outline(S, OL_STEP['A']), OUT + 'base.png')



# ---------------------------------------------------------------- FAR CLIFFS (distant mesas sinking into haze)
def build_farcliffs():
    segs = [scaled(crop(load(RAW + 'farcliffs_1.png')), h=118), scaled(crop(load(RAW + 'farcliffs_2.png')), h=104),
            scaled(crop(load(RAW + 'farcliffs_1.png'))[:, ::-1], h=110)]
    pano = panorama(segs, 130, 30)
    pano = step(pano, 'C')
    save(outline(flatten(quant(pano, 28), 3, (0.3, 0.7)), OL_STEP['C']), OUT + 'farcliffs.png')


# ---------------------------------------------------------------- MID TREES (overlap cliffs)
def build_midtrees():
    pcs = []
    for f in ('midtrees_1', 'midtrees_2'):
        pcs += pieces(load(RAW + f + '.png'), 0.5, 4000)
    W, H = 1400, 250
    L = np.zeros((H, W, 4), np.uint8)
    # (piece, height, x) ; bottom at H, flipped every other one
    plan = [(0, 196, 20), (7, 150, 190), (2, 214, 330), (5, 176, 520), (9, 206, 700), (3, 168, 880),
            (6, 190, 1010), (4, 222, 1170)]
    for k, (pi, h, x) in enumerate(plan):
        c = pcs[pi % len(pcs)]
        if k % 2: c = c[:, ::-1]
        sc = haze(step(pxpiece(c, h=h, ncol=12), 'B'), 0.24, np.array([96, 168, 150]) / 255.0)
        paste(L, outline(quant(sc, 12), OL_STEP['B']), x, H - sc.shape[0])
    L = add_palms(crisp_tone(L, 4), 'B', every=120, hs=(26, 38))
    save(outline(L, OL_STEP['B']), OUT + 'midtrees.png')


# ---------------------------------------------------------------- OVERHANG (foreground canopy + vines at the top)
def build_overhang():
    segs = []
    for f in ('overhang_2', 'overhang_1', 'overhang_3'):
        a = load(RAW + f + '.png')
        mn = a[..., :3].min(-1)
        a[..., 3] = np.where((a[..., 3] > 0.5) & (mn < 0.62), 1, 0)   # drop the white haze some gens added
        # keep only pixels connected to the top edge
        lab, n = ndimage.label(a[..., 3] > 0)
        keep = np.isin(lab, np.unique(lab[:12][lab[:12] > 0]))
        a[..., 3] = keep
        a = a[:600]
        segs.append(scaled(a, s=0.125))
    H = max(x.shape[0] for x in segs)
    cols = []
    for x in segs:
        c = np.zeros((H, x.shape[1], 4), np.float32); c[:x.shape[0]] = x; cols.append(c)
    S = cols[0]
    for c in cols[1:]: S = join(S, c, 16)
    W = S.shape[1]; ov = 16
    wrapped = join(S[:, W - ov - 40:], S[:, :ov + 40], ov)
    S2 = S[:, :W - ov].copy(); S2[:, :ov] = wrapped[:, 40:40 + ov]
    im = quant(S2, 24)
    # vary the depth of the overhang so sky shows through in places (wraps seamlessly: periodic profile)
    Wd = im.shape[1]; xs = np.arange(Wd)
    prof = 40 + 16 * np.sin(2 * np.pi * xs / Wd * 2 + 0.6) + 10 * np.sin(2 * np.pi * xs / Wd * 5 + 2.0)
    prof = np.clip(prof, 27, 62) + rng.integers(-2, 3, Wd)
    for x in range(Wd): im[int(prof[x]):, x] = 0
    # drop tiny detached leftovers after the cut
    lab, n = ndimage.label(im[..., 3] > 0)
    top_ids = np.unique(lab[:3][lab[:3] > 0])
    im[~np.isin(lab, top_ids)] = 0
    # force a 1px dark outline under the foliage for Contra-style readability
    a = im[..., 3] > 0
    below = np.zeros_like(a); below[1:] = a[:-1]
    ring = below & ~a
    im[ring] = (18, 36, 24, 255)
    save(im, OUT + 'overhang.png')
    # thin variant for the boss arena: only the top foliage fringe, no hanging vines
    thin = im.copy(); thin[11:] = 0
    lab, n = ndimage.label(thin[..., 3] > 0)
    thin[~np.isin(lab, np.unique(lab[:2][lab[:2] > 0]))] = 0
    a = thin[..., 3] > 0; below = np.zeros_like(a); below[1:] = a[:-1]; thin[below & ~a] = (18, 36, 24, 255)
    save(thin[:13], OUT + 'overhang-thin.png')


# ---------------------------------------------------------------- NEAR set pieces (close cliffs right behind the play plane)
def wf_frames(base, anim, name, wpal_hex=('4f7fae', '8ab6da', 'c6e0f2', 'ffffff')):
    """clean falling-water frames: per-column streak tone (runs of 2-3 columns) + short bright dashes
    sliding down 3px per frame (period 12 -> seamless 4-frame loop). No per-pixel noise."""
    W = base.shape[1]
    wpal = np.array([C(c)[:3] for c in wpal_hex], np.uint8)
    col = np.zeros(W, int); x = 0
    while x < W:
        run = int(rng.integers(2, 4)); col[x:x + run] = rng.choice([1, 2, 2, 3]); x += run
    off = rng.integers(0, 12, W)
    ys, xs = np.where(anim & (base[..., 3] > 0))
    # edge columns of each fall get the darker tone
    left = ~anim[ys, np.maximum(xs - 1, 0)]; right = ~anim[ys, np.minimum(xs + 1, W - 1)]
    for f in range(4):
        im = base.copy()
        lvl = col[xs].copy()
        dash = ((ys - f * 3 + off[xs]) % 12) < 2
        lvl = np.where(dash, np.minimum(3, lvl + 1), lvl)
        lvl = np.where(left | right, 0, lvl)
        im[ys, xs, :3] = wpal[lvl]
        save(im, OUT + (name + '.png' if f == 0 else f'{name}-{f}.png'))


def build_near():
    W, H = 1760, 270
    src = {}
    for f in ('near_1', 'near_2', 'near_3', 'near2_1', 'near2_2'):
        src[f] = pieces(load(RAW + f + '.png'), 0.5, 20000)[0]
    # (piece, height, x, flip, topper)
    plan = [('near_1', 196, 30, False, 'tower'), ('near2_1', 214, 330, False, None),
            ('near_3', 186, 800, True, 'bunker'), ('near2_2', 206, 1130, False, None), ('near_2', 176, 1440, True, None)]
    layer = np.zeros((H, W, 4), np.float32); anim = np.zeros((H, W), bool); placed = []
    for f, h, x, flip, top in plan:
        c = src[f][:, ::-1] if flip else src[f]
        sc = pxpiece(c, h=h, ncol=14)
        # sit a step behind the play plane: a little darker and cooler than the terrain, more contrast
        # pushed back behind the play plane: lower contrast, lighter and cooler (haze), but still solid shapes
        wm = wf_mask(scaled(c, h=h)) & (sc[..., 3] >= 0.5)
        sc = step(sc, 'A')
        m = sc[..., 3] >= 0.5
        hh, ww = sc.shape[:2]; y = H - hh
        for dx in (0, -W):
            xs = x + dx
            if xs + ww <= 0 or xs >= W: continue
            a0, a1 = max(0, -xs), min(ww, W - xs)
            sub = layer[y:, xs + a0:xs + a1]; mm = m[:, a0:a1]; sub[mm] = sc[:, a0:a1][mm]
            anim[y:, xs + a0:xs + a1][mm] = wm[:, a0:a1][mm]
        placed.append((x, y, ww, hh, top))
    base = outline(crisp_tone(quant(layer, 64), 5, (0.18, 0.4, 0.62, 0.82), keep=anim), OL_STEP['A'])
    pre = base.copy()
    def top_at(x): col = pre[:, x % W, 3]; return int(np.argmax(col > 0))
    bk = pieces(load(RAW + 'baseB_1.png'), 0.5, 4000)[0][:, 190:]; bk = crop(bk)
    bunker = outline(step8(bunker_px(60, 30), 'A', 0.2), OL_STEP['A'])
    wfcol = anim.any(0)
    def flat_spot(x, ww, w, pref):
        best, bx = 1e9, x
        for cx in range(x + 4, x + ww - w - 4):
            cols = [c % W for c in range(cx, cx + w)]
            if wfcol[cols].any(): continue
            tops = np.array([top_at(c) for c in cols])
            cost = tops.std() + abs(cx - (x + ww * pref - w / 2)) * 0.05 + (tops.mean() - y) * 0.02
            if cost < best: best, bx = cost, cx
        return bx, int(np.median([top_at(c) for c in range(bx, bx + w)]))
    for (x, y, ww, hh, top) in placed:
        if top == 'tower':
            tx, yt = flat_spot(x, ww, 25, 0.75)
            paste(base, outline(step8(tower(25, 54), 'A', 0.1), OL_STEP['A']), tx, yt - 54 + 6)
        elif top == 'bunker':
            tx, yt = flat_spot(x, ww, bunker.shape[1], 0.7)
            paste(base, bunker, tx, yt - bunker.shape[0] + 6)
    # close rope bridges between neighbouring set pieces (anchored on rock at both ends)
    for i in (0, 2):
        xa, ya, wa, ha, _ = placed[i]; xb, yb, wb, hb, _ = placed[i + 1]
        yy = max(ya, yb) + 30
        x0 = xa + wa - 1
        while x0 > xa and pre[yy, x0, 3] == 0: x0 -= 1
        x1 = xb
        while x1 < xb + wb and pre[yy + 4, x1, 3] == 0: x1 += 1
        big = stepped_pal('A', dict(post=C('3a2e26'), rope=C('7a5c3c'), plank=C('9a7a50'), dark=C('2a2220')))
        rope_bridge(base, x0 - 3, yy, x1 + 3, yy + 4, 14, big)
        rope_bridge(base, x0 - 3, yy + 1, x1 + 3, yy + 5, 14, big)
    anim &= (base == pre).all(-1)
    wf_frames(base, anim, 'near', ('6c94bc', '8cb0d2', 'b0cce4', 'd6e6f2'))


# ---------------------------------------------------------------- FORT landmark (world-placed, jungle mid-stage)
def build_fort():
    a = crop(load(RAW + 'fort_1.png'))
    sc0 = crispen(scaled(a, w=250), 1.0, 120)
    sc = bgstep(sc0, 0.72, 0.22)
    # keep accents readable: warm lit windows and the red banner stay vivid (only a light step)
    r, g, bl = sc0[..., 0], sc0[..., 1], sc0[..., 2]
    warm = (r > g + 0.12) & (r > bl + 0.15) & (sc0[..., 3] > 0.5)
    acc = bgstep(sat(sc0, 1.15), 0.95, 0.08)
    sc[warm] = acc[warm]
    im = quant(sc, 40)
    # light top edge on battlements / roofs: first opaque pixel below transparency
    m = im[..., 3] > 0
    top = m.copy(); top[1:] = m[1:] & ~m[:-1]; top[0] = m[0]
    wk = ~warm[:im.shape[0], :im.shape[1]]
    hi = top & wk
    im[hi, :3] = np.clip(im[hi, :3].astype(int) + 46, 0, 255).astype(np.uint8)
    save(outline(im, OL_NEAR), OUT + 'fort.png')
    # hazy mountain directly behind the fort so its silhouette reads against a bright, calm value
    mtn = crop(load(RAW + 'far_1.png'))
    mw = 380
    ms = scaled(mtn, w=mw)
    ms = haze(bgstep(ms, 0.45, 0.0), 0.58, np.array([170, 206, 228]) / 255.0)
    save(quant(ms, 12), OUT + 'fortback.png')



# ---------------------------------------------------------------- OUTPOSTS: layered watchtowers on cliffs (x~2300)
def build_outposts():
    cl = []
    for f in ('cliffs_1', 'cliffs_2', 'cliffs_3'): cl += pieces(load(RAW + f + '.png'), 0.5, 3000)
    nr = pieces(load(RAW + 'near2_1.png'), 0.5, 20000)[0]
    # (name, source, cliff height, tower w, tower h, contrast k, blue amt, haze amt, outline)
    specs = [('outpost0', cl[2], 112, 13, 24, 'C'), ('outpost1', cl[4], 150, 17, 32, 'B'), ('outpost2', nr, 170, 23, 46, 'A')]
    for name, src, ch, tw, th, stp in specs:
        k, amt, _ = STEPS[stp]; hz = 0.0; ol = OL_STEP[stp]
        c = step(pxpiece(src, h=ch, ncol=12), stp)
        cim = quant(c, 12)
        if stp == 'B':   # r18: bright white waterfalls on the mid plane for contrast
            rw = scaled(src, h=ch); wmask = wf_mask(rw) & (cim[..., 3] > 0)
            lum = rw[..., :3].mean(-1)
            lv = np.clip(((lum - 0.45) / 0.55 * 3.2), 0, 3).astype(int)
            wp = np.array([C(x)[:3] for x in ('8ab8dc', 'bcdcf2', 'e6f4fc', 'ffffff')], np.uint8)
            cim[wmask, :3] = wp[lv[wmask]]
        H = ch + th; W = cim.shape[1] + 4
        im = np.zeros((H, W, 4), np.uint8)
        paste(im, cim, 2, th, wrap=False)
        # tower on the flattest non-waterfall top span
        raw = scaled(src, h=ch); wm = wf_mask(raw); wm[int(ch * 0.3):] = False
        tops = [int(np.argmax(cim[:, x, 3] > 0)) if cim[:, x, 3].any() else 999 for x in range(cim.shape[1])]
        tv = np.array(tops); mn = tv.min(); best, bx = 1e9, 0
        wcols = wm.any(0)
        for x in range(2, cim.shape[1] - tw - 2):
            t = tv[x:x + tw]
            if (t > 900).any() or wcols[x:x + tw].any(): continue
            cost = (t.max() - mn) + t.std() * 2
            if cost < best: best, bx = cost, x
        yt = int(tv[bx:bx + tw].max()) - 2
        t8 = tower(tw, th)
        f = t8[..., :3].astype(float) / 255
        t8f = np.concatenate([f, (t8[..., 3:4] > 0).astype(float)], -1)
        t8f = step(t8f, stp)
        warm = (t8[..., 0] > 200) & (t8[..., 3] > 0)
        t8o = t8.copy(); t8o[..., :3] = (t8f[..., :3] * 255 + .5).astype(np.uint8)
        t8o[warm, :3] = np.clip(t8[warm, :3].astype(int) * (1 - hz * 0.6) + np.array([170, 206, 228]) * hz * 0.6, 0, 255).astype(np.uint8)
        paste(im, t8o, bx + 2, th + yt - th + 4, wrap=False)
        # crop empty top
        ys = np.where(im[..., 3].any(1))[0]; im = im[ys[0]:]
        save(outline(im, ol), OUT + name + '.png')
    # distant rope bridge, hazy
    br = np.zeros((20, 54, 4), np.uint8)
    rope_bridge(br, 2, 9, 51, 9, 6, stepped_pal('B'))
    save(br, OUT + 'outbridge.png')


# ---------------------------------------------------------------- hand-pixelled military props (native 1x)
MIL = dict(ol=C('263444'), c0=C('4a5a6a'), c1=C('66788a'), c2=C('8496a6'), c3=C('a6b6c2'),
           dk=C('202a36'), win=C('ffb040'), hot=C('ffe29a'), red=C('c8382c'), yel=C('d8b040'), st=C('3a4652'))


def rect(im, x0, y0, x1, y1, col):
    im[max(0, y0):max(0, y1), max(0, x0):max(0, x1)] = col


def bunker_px(w=60, h=32, p=MIL):
    im = np.zeros((h + 10, w, 4), np.uint8); t = 10
    rect(im, 1, t + 3, w - 1, t + h, p['c1'])                 # body
    rect(im, 0, t + 1, w, t + 4, p['c2']); rect(im, 0, t, w, t + 1, p['c3'])   # roof slab + lit top edge
    rect(im, 1, t + 4, w - 1, t + 5, p['c0'])                 # shadow under slab
    for x in range(1, w - 1, 12): rect(im, x, t + 5, x + 1, t + h, p['c0'])   # panel seams
    rect(im, w - 5, t + 5, w - 1, t + h, p['c0'])             # right side shade
    # slit windows (lit)
    for wx in (5, w - 17):
        rect(im, wx, t + 9, wx + 10, t + 12, p['dk']); rect(im, wx + 1, t + 10, wx + 9, t + 11, p['win'])
        rect(im, wx + 3, t + 10, wx + 6, t + 11, p['hot'])
    # door with hazard frame
    dx = w // 2 - 6
    rect(im, dx - 2, t + 14, dx + 14, t + h, p['yel'])
    for y in range(t + 14, t + h):
        for x in (dx - 2, dx - 1, dx + 12, dx + 13):
            if (x + y) % 4 < 2: im[y, x] = p['dk']
    rect(im, dx, t + 15, dx + 12, t + h, p['st']); rect(im, dx + 5, t + 15, dx + 7, t + h, p['dk'])
    rect(im, dx, t + 15, dx + 12, t + 16, p['c0'])
    # roof antenna + red light
    ax = w - 12
    rect(im, ax, 1, ax + 1, t, p['st']); rect(im, ax - 2, 4, ax + 3, 5, p['st']); im[0, ax] = p['red']
    rect(im, 8, t - 3, 16, t, p['c1']); rect(im, 8, t - 3, 16, t - 2, p['c2'])   # roof vent
    return outline(im, p['ol'])


def mast_px(h=96, p=MIL):
    w = 26; im = np.zeros((h, w, 4), np.uint8); cx = w // 2
    top = 22
    for side in (-1, 1):
        draw_line(im, cx + side * 2, top, cx + side * 9, h - 1, p['st'])
    y = top + 2; k = 0
    while y < h - 6:
        y2 = min(h - 1, y + 10)
        la = cx - 2 - round(7 * (y - top) / (h - top)); lb = cx - 2 - round(7 * (y2 - top) / (h - top))
        ra = cx + 2 + round(7 * (y - top) / (h - top)); rb = cx + 2 + round(7 * (y2 - top) / (h - top))
        draw_line(im, la, y, rb, y2, p['c0']); draw_line(im, ra, y, lb, y2, p['c0'])
        draw_line(im, lb, y2, rb, y2, p['c1']); y = y2
    # platform + dish
    rect(im, cx - 5, top - 2, cx + 6, top, p['c1'])
    for yy in range(0, 16):
        half = int(round(11 * np.sqrt(max(0, 1 - ((yy - 8) / 8.5) ** 2))))
        rect(im, cx - 3 - half // 3, yy + 4, cx - 3 - half // 3 + max(2, half // 2), yy + 5, p['c2'] if yy < 8 else p['c1'])
    draw_line(im, cx - 1, 12, cx + 5, 6, p['st']); im[5, cx + 6] = p['red']
    rect(im, cx, top - 6, cx + 1, top - 2, p['st'])
    return outline(im, p['ol'])


def tanks_px(p=MIL):
    im = np.zeros((34, 44, 4), np.uint8)
    for x0 in (0, 22):
        rect(im, x0 + 1, 4, x0 + 19, 34, p['c1'])
        rect(im, x0 + 3, 4, x0 + 6, 34, p['c3']); rect(im, x0 + 6, 4, x0 + 8, 34, p['c2'])
        rect(im, x0 + 15, 4, x0 + 19, 34, p['c0'])
        rect(im, x0 + 3, 2, x0 + 17, 4, p['c2']); rect(im, x0 + 6, 0, x0 + 14, 2, p['c1'])
        for y in (12, 24): rect(im, x0 + 1, y, x0 + 19, y + 1, p['c0'])
        rect(im, x0 + 7, 16, x0 + 13, 20, p['red']); rect(im, x0 + 9, 17, x0 + 11, 19, p['c3'])
    return outline(im, p['ol'])


def fence_px(w=96, p=MIL):
    h = 30; im = np.zeros((h, w, 4), np.uint8)
    for y in range(6, h):
        for x in range(w):
            if (x + y) % 4 == 0 or (x - y) % 4 == 0: im[y, x] = p['c0']
    for x in range(2, w, 16): rect(im, x, 2, x + 2, h, p['c1']); rect(im, x, 2, x + 1, h, p['c2'])
    for x in range(w):
        im[4, x] = p['st']
        if x % 3 == 0: im[3, x] = p['st']; im[5, (x + 1) % w] = p['st']
    rect(im, 0, h - 2, w, h, p['c0'])
    return im


# ---------------------------------------------------------------- MIDSET: crisp mid-distance cliff pair + bridge + tower (x~2300)
def build_midset():
    cl = []
    for f in ('cliffs_1', 'cliffs_2', 'cliffs_3'): cl += pieces(load(RAW + f + '.png'), 0.5, 3000)
    W, H = 230, 190
    im = np.zeros((H, W, 4), np.uint8)
    def cliff(src, h, flip=False):
        c = src[:, ::-1] if flip else src
        f = step(pxpiece(c, h=h, ncol=10), 'A')
        return outline(quant(f, 10), OL_STEP['A'])
    a = cliff(cl[0], 138); b = cliff(cl[6], 124, True)
    paste(im, a, 0, H - a.shape[0], wrap=False)
    paste(im, b, W - b.shape[1], H - b.shape[0], wrap=False)
    def top(x): col = im[:, x, 3]; return int(np.argmax(col > 0))
    # bridge between the inner edges, anchored on rock
    yy = max(H - a.shape[0], H - b.shape[0]) + 34
    x0 = a.shape[1] - 1
    while x0 > 0 and im[yy, x0, 3] == 0: x0 -= 1
    x1 = W - b.shape[1]
    while x1 < W - 1 and im[yy + 3, x1, 3] == 0: x1 += 1
    dark = stepped_pal('A', dict(post=C('2a2a2e'), rope=C('5a4a3a'), plank=C('7a6448'), dark=C('241e1c')))
    rope_bridge(im, x0 - 3, yy, x1 + 3, yy + 3, 10, dark); rope_bridge(im, x0 - 3, yy + 1, x1 + 3, yy + 4, 10, dark)
    # tower on the left cliff's crest
    tops = np.array([top(x) for x in range(a.shape[1])])
    best, bx = 1e9, 4
    for x in range(4, a.shape[1] - 26):
        t = tops[x:x + 21]; c = t.max() - tops.min() + t.std() * 2
        if c < best: best, bx = c, x
    # (round 17) no tower on the midset: too many towers on screen at x~2300
    ys = np.where(im[..., 3].any(1))[0]; im = im[ys[0]:]
    save(im, OUT + 'midset.png')

# ---------------------------------------------------------------- BIRDS (2 frames, 9x5)
def build_birds():
    d = C('26303a'); l = C('4a5866')
    f0 = ["d.......d", ".d.....d.", "..d.d.d..", "...ddd...", "........."]
    f1 = [".........", ".........", "ddddddddd", "l..ddd..l", "........."]
    sheet = np.zeros((5, 18, 4), np.uint8)
    for k, f in enumerate((f0, f1)):
        for y, row in enumerate(f):
            for x, ch in enumerate(row):
                if ch == 'd': sheet[y, k * 9 + x] = d
                if ch == 'l': sheet[y, k * 9 + x] = l
    save(sheet, OUT + 'bird.png')


if __name__ == '__main__':
    only = sys.argv[1:]
    for n, fn in [('sky', build_sky), ('clouds', build_clouds), ('far', build_far), ('hills', build_hills),
                  ('cliffs', build_cliffs), ('canopy', build_canopy), ('base', build_base), ('birds', build_birds),
                  ('farcliffs', build_farcliffs), ('midtrees', build_midtrees), ('overhang', build_overhang), ('near', build_near), ('fort', build_fort), ('outposts', build_outposts), ('midset', build_midset)]:
        if not only or n in only: fn()
