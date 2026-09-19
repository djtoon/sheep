"""Build all enemy game art from the chosen raw generations.
python art/raw/enemies/build.py  -> assets/enemies/*.png, frames preview in art/raw/enemies/out/
"""
import os, json
from proc import *

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
A = os.path.join(ROOT, 'assets', 'enemies'); os.makedirs(A, exist_ok=True)
O = os.path.join(HERE, 'out'); os.makedirs(O, exist_ok=True)
os.chdir(HERE)
OL = np.array(OUT)


def keep_largest(f, frac=0.0):
    m = f[..., 3] > 0
    lab, n = ndi.label(m, structure=np.ones((3, 3)))
    if n <= 1: return f
    sizes = ndi.sum(m, lab, range(1, n + 1))
    keep = [i + 1 for i, s in enumerate(sizes) if s == sizes.max() or s >= sizes.max() * frac and frac > 0]
    f = f.copy(); f[~np.isin(lab, keep)] = 0
    al = f[..., 3] > 0
    r = np.where(al.any(1))[0]; c = np.where(al.any(0))[0]
    return f[r.min():r.max() + 1, c.min():c.max() + 1]


def fix_outline(f, lum=60):
    """edge pixels (touching transparency) that are already dark -> canonical outline colour;
    edge pixels that are light get an outline ring outside."""
    f = f.copy()
    m = f[..., 3] > 0
    pad = np.pad(m, 1)
    edge_in = m & ~(pad[:-2, 1:-1] & pad[2:, 1:-1] & pad[1:-1, :-2] & pad[1:-1, 2:])
    L = f[..., :3].astype(int).mean(-1)
    f[edge_in & (L < lum), :3] = OUT
    light_edge = edge_in & (L > 80)
    if light_edge.any():
        g = np.pad(f, ((1, 1), (1, 1), (0, 0)))
        lm = np.pad(light_edge, 1)
        ring = np.zeros_like(lm)
        ring[1:, :] |= lm[:-1, :]; ring[:-1, :] |= lm[1:, :]; ring[:, 1:] |= lm[:, :-1]; ring[:, :-1] |= lm[:, 1:]
        ring &= g[..., 3] == 0
        g[ring] = (*OUT, 255)
        f = g
        al = f[..., 3] > 0
        r = np.where(al.any(1))[0]; c = np.where(al.any(0))[0]
        f = f[r.min():r.max() + 1, c.min():c.max() + 1]
    return f


def pop_goggles(f):
    """make the red goggles/eyes glow: saturate reds, brightest -> hot core"""
    rgb = f[..., :3].astype(int)
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    red = (f[..., 3] > 0) & (r > 130) & (g < 95) & (b < 95) & (r > g * 2.2)
    f = f.copy()
    hot = (f[..., 3] > 0) & (r > 220) & (g > 110) & (g < 240) & (b < 190) & (r > b + 60)
    f[red & (r >= 130), :3] = (255, 34, 30)
    f[hot, :3] = (255, 228, 150)
    return f


def mirror_ok(f):
    return f


def pack(frames, cw, ch, anchors, name):
    sheet = cells(frames, cw, ch, anchors)
    Image.fromarray(sheet, 'RGBA').save(os.path.join(A, name + '.png'))
    return sheet


def pick(sheet, n, px, idx=None, pre=None, gap=None):
    a = load(sheet)
    if pre: a = pre(a)
    segs = split_n(a, n) if gap is None else split(a, gap=gap)
    out = []
    for k, (s, e) in enumerate(segs):
        if idx and k not in idx: continue
        out.append(grid_sample(a[:, s:e], px))
    return out



import colorsys
def _ramp(h, sv):
    return [tuple(int(round(c * 255)) for c in colorsys.hsv_to_rgb(h / 360, s_, v_)) for s_, v_ in sv]
PAL = os.environ.get('SOLDIER_PAL', 'okhaki')
# ---- round 2: controlled palette ramp + real outline so soldiers read on busy jungle ----
INK = (14, 10, 18)
FAT = [(30, 42, 26), (58, 80, 42), (96, 122, 60), (150, 174, 92)]
if PAL == 'khaki':   # round 5: out of the foliage hue/sat band (jungle greens are hue 60-160, S 0.28-0.79)
    FAT = _ramp(48, [(0.50, 0.20), (0.44, 0.38), (0.40, 0.56), (0.32, 0.74)])
elif PAL == 'okhaki':
    FAT = _ramp(56, [(0.50, 0.11), (0.50, 0.25), (0.40, 0.55), (0.32, 0.74)])   # round 7: shadows pushed near ink
elif PAL == 'drab':
    FAT = _ramp(70, [(0.30, 0.20), (0.24, 0.38), (0.22, 0.56), (0.18, 0.74)])     # fatigue: shadow, mid, light, highlight
GUN = [(22, 22, 28), (58, 62, 74), (128, 134, 148)]
HELM = [(52, 70, 34), (92, 116, 54), (140, 164, 80), (204, 220, 132)]
if PAL == 'khaki':
    HELM = _ramp(54, [(0.44, 0.32), (0.40, 0.52), (0.34, 0.72), (0.24, 0.90)])
elif PAL == 'okhaki':
    HELM = _ramp(60, [(0.44, 0.34), (0.40, 0.55), (0.34, 0.74), (0.24, 0.92)])
elif PAL == 'drab':
    HELM = _ramp(72, [(0.26, 0.32), (0.22, 0.52), (0.18, 0.72), (0.12, 0.90)])
BOOT = [(52, 30, 20), (98, 60, 34)]
SKIN = [(150, 92, 60), (222, 162, 112)]
MASK = [(28, 30, 34), (52, 56, 62)]

def lum(c): return 0.3 * c[..., 0] + 0.59 * c[..., 1] + 0.11 * c[..., 2]

def soldier_ramp(f):
    f = f.copy(); a = f[..., 3] > 0
    rgb = f[..., :3].astype(float); r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    L = lum(rgb); mx = rgb.max(-1); mn = rgb.min(-1); sat = (mx - mn) / np.maximum(mx, 1)
    goggle = a & (r > 180) & (r > g * 1.6)
    green = a & ~goggle & (g >= r * 0.92) & (g > b * 1.15) & (sat > 0.18)
    skin = a & ~goggle & (r > g * 1.12) & (r > b * 1.3) & (L > 95)
    boot = a & ~goggle & ~skin & (r > g * 1.1) & (r > b * 1.2) & ~green
    neutral = a & ~goggle & ~green & ~skin & ~boot
    out = f.copy()
    # fatigue: quantile thresholds per frame -> guaranteed value gaps
    if green.any():
        gl = L[green]
        t0, t1, t2, t3 = np.percentile(gl, [7, 38, 72, 93])
        for sel, col in [(green & (L < t0), INK), (green & (L >= t0) & (L < t1), FAT[0]), (green & (L >= t1) & (L < t2), FAT[1]),
                         (green & (L >= t2) & (L < t3), FAT[2]), (green & (L >= t3), FAT[3])]:
            out[sel, :3] = col
    out[neutral & (L < 34), :3] = INK
    out[neutral & (L >= 34) & (L < 62), :3] = GUN[0]
    out[neutral & (L >= 62) & (L < 100), :3] = GUN[1]
    out[neutral & (L >= 100), :3] = GUN[2]
    out[boot & (L < 55), :3] = BOOT[0]; out[boot & (L >= 55), :3] = BOOT[1]
    out[skin & (L < 150), :3] = SKIN[0]; out[skin & (L >= 150), :3] = SKIN[1]
    out[goggle, :3] = (255, 36, 28)
    hot = goggle & (g > 110)
    out[hot, :3] = (255, 226, 150)
    # helmet rim: ink line over the goggles, bright rim pixel above that
    H, W = a.shape
    gy, gx = np.where(goggle)
    if len(gy):
        top = gy.min(); cols = np.unique(gx[gy <= top + 1])
        x0, x1 = cols.min(), cols.max()
        for x in range(max(0, x0 - 1), min(W, x1 + 3)):
            if top - 1 >= 0 and a[top - 1, x]: out[top - 1, x, :3] = INK
            if top - 2 >= 0 and a[top - 2, x] and green[top - 2, x]: out[top - 2, x, :3] = FAT[3]
            if top - 3 >= 0 and a[top - 3, x] and green[top - 3, x]: out[top - 3, x, :3] = FAT[2]
        # the goggle glass: every goggle row gets full bright red, with a 1px hot highlight at the front
        rows = np.unique(gy)
        out[rows.min(), gx[gy == rows.min()].min(), :3] = (255, 226, 150)
    # edge pixels -> ink, then an exterior 1px ink ring
    pad = np.pad(a, 1)
    edge = a & ~(pad[:-2, 1:-1] & pad[2:, 1:-1] & pad[1:-1, :-2] & pad[1:-1, 2:])
    Lo = lum(out[..., :3].astype(float))
    out[edge & (Lo < 70) & ~goggle, :3] = INK
    g2 = np.pad(out, ((1, 1), (1, 1), (0, 0)))
    m = g2[..., 3] > 0
    ring = np.zeros_like(m)
    ring[1:, :] |= m[:-1, :]; ring[:-1, :] |= m[1:, :]; ring[:, 1:] |= m[:, :-1]; ring[:, :-1] |= m[:, 1:]
    ring &= ~m
    g2[ring] = (*INK, 255)
    return g2

import sys
POSE_PX = float(os.environ.get('POSE_PX', '12.6'))
TUR_PX = float(os.environ.get('TUR_PX', '9.4'))
# ---------------- soldier ----------------
run = [keep_largest(f) for f in pick('run5_2.png', 8, 7.6)]
up = [keep_largest(f) for f in pick('pose4_3.png', 4, POSE_PX)]
pose = [keep_largest(f) for f in pick('pose_1.png', 8, 6.2, pre=remove_flash)]
stand_aim, _sf, kneel_aim, _kf, d1, d2, d3, d4 = pose
def recoil_body(f, rows_frac=0.62, d=1):
    # upper body (helmet, arms, rifle) kicks back d px; legs stay planted
    g = np.zeros((f.shape[0], f.shape[1] + d, 4), f.dtype); g[:, :f.shape[1]] = f
    cut = int(f.shape[0] * rows_frac)
    top = f[:cut].copy(); g[:cut] = 0; g[:cut, d:] = top
    return g
stand_aim, stand_fire, kneel_aim, kneel_fire = up
d1, d2, d3, d4 = [keep_largest(f) for f in pick('die5_1.png', 4, 10.5)]
sold = [soldier_ramp(f) for f in run + [stand_aim, stand_fire, kneel_aim, kneel_fire, d1, d2, d3, d4]]
def paint_face(f):
    # round 3: light olive helmet, big black mask, two chunky glowing red eyes
    f = f.copy(); a = f[..., 3] > 0; H, W = a.shape
    red = a & (f[..., 0] == 255) & (f[..., 1] < 60)
    ys, xs = np.where(red)
    if not len(ys): return f
    y = int(ys.min())
    row = np.where(a[y])[0]; xf = int(row.min())
    f[red, :3] = (20, 18, 24)
    # helmet: rows above the brim get the lighter helmet ramp
    top = np.where(a.any(1))[0][0]
    for yy in range(top, y - 1):
        for xx in range(W):
            c = tuple(f[yy, xx, :3])
            if c in FAT: f[yy, xx, :3] = HELM[FAT.index(c)]
    # bright top highlight arc on the helmet
    for yy in range(top, y - 1):
        cols = [xx for xx in range(W) if a[yy, xx] and tuple(f[yy, xx, :3]) != INK]
        if cols and yy <= top + 2:
            for xx in cols[: max(1, len(cols) // 2)]:
                if tuple(f[yy, xx, :3]) in HELM: f[yy, xx, :3] = HELM[3] if yy == top + 1 else HELM[2]
    INKA = (*INK, 255); MASK_C = (18, 16, 22, 255); MASK2 = (40, 40, 48, 255)
    E, EH, GL = (255, 40, 30, 255), (255, 236, 160, 255), (150, 18, 24, 255)
    MW = 9
    for x in range(xf, min(W, xf + MW + 1)):
        if a[y - 1, x]: f[y - 1, x] = INKA                     # brim
    for yy in range(y, min(H, y + 5)):
        for x in range(xf + 1, min(W, xf + MW)):
            if a[yy, x]: f[yy, x] = MASK_C
        if a[yy, xf]: f[yy, xf] = INKA
    for x in range(xf + 2, min(W, xf + MW - 1)):
        if a[y + 4, x]: f[y + 4, x] = MASK2                     # chin edge
    # two 3x2 eyes with glow
    for ex in (xf + 1, xf + 5):
        for yy in (y + 1, y + 2):
            for x in range(ex, ex + 3):
                if yy == y + 2 and x == ex + 2: continue
                f[yy, x] = E
        f[y + 1, ex] = EH; f[y + 1, ex + 1] = EH
        for (gy, gx) in [(y, ex), (y, ex + 1), (y, ex + 2), (y + 3, ex), (y + 3, ex + 1), (y + 2, ex + 2)]:
            if 0 <= gx < W and a[gy, gx] and tuple(f[gy, gx]) == MASK_C: f[gy, gx] = GL
    return f

def rifle_edges(f):
    # light top edge on gun metal so the rifle reads as a clear dark diagonal with a glint
    f = f.copy(); H, W = f.shape[:2]
    gun = np.zeros((H, W), bool)
    for c in GUN[:2]: gun |= (f[..., 0] == c[0]) & (f[..., 1] == c[1]) & (f[..., 2] == c[2]) & (f[..., 3] > 0)
    above = np.zeros_like(gun); above[1:] = gun[:-1]
    topedge = gun & ~np.vstack([np.zeros((1, W), bool), gun[:-1]])
    f[topedge & (np.arange(W)[None, :] < W * 0.55), :3] = GUN[2]
    return f
def rim_light(f):
    # bright rim on any helmet/fatigue pixel whose upper neighbour is ink or empty (helmet top, shoulders, arms)
    f = f.copy(); H, W = f.shape[:2]
    a = f[..., 3] > 0
    top = np.where(a.any(1))[0][0]; lim = top + (H - top) * 0.6
    src = f.copy()
    for y in range(1, H):
        if y > lim: break
        for x in range(W):
            if not a[y, x]: continue
            c = tuple(src[y, x, :3]); up = tuple(src[y - 1, x, :3])
            if a[y - 1, x] and up != INK: continue
            if c in HELM[1:3]: f[y, x, :3] = HELM[3]
            elif c in FAT[1:3]: f[y, x, :3] = FAT[3]
    # back rim (figure faces left, so the back is the right edge): helmet back + shoulders, upper 55%
    for y in range(top, int(top + (H - top) * 0.55)):
        xs = np.where(a[y])[0]
        if not len(xs): continue
        for x in range(xs.max(), xs.min(), -1):
            c = tuple(src[x and y, x, :3]) if False else tuple(f[y, x, :3])
            if c == INK: continue
            if c in HELM[:3]: f[y, x, :3] = HELM[3]
            elif c in FAT[:3]: f[y, x, :3] = FAT[3]
            break
    return f

def inner_contours(f):
    # ink separation where a light fatigue/helmet pixel directly touches boots, gun or skin (limbs over body)
    f = f.copy(); a = f[..., 3] > 0; H, W = a.shape
    def is_(cols):
        m = np.zeros((H, W), bool)
        for c in cols: m |= (f[..., 0] == c[0]) & (f[..., 1] == c[1]) & (f[..., 2] == c[2]) & a
        return m
    cloth = is_(FAT[1:] + HELM[1:])
    other = is_(BOOT + GUN[:2])
    near = np.zeros_like(other)
    near[1:] |= other[:-1]; near[:-1] |= other[1:]; near[:, 1:] |= other[:, :-1]; near[:, :-1] |= other[:, 1:]
    f[cloth & near & ~is_(FAT[3:] + HELM[3:]), :3] = FAT[0]
    return f
sold = [rim_light(inner_contours(rifle_edges(paint_face(f)))) if i < 12 else inner_contours(f) for i, f in enumerate(sold)]

# anchor: head centre for upright frames; bbox centre for death frames
anch = [head_x(f) for f in sold[:12]] + [f.shape[1] // 2 for f in sold[12:]]
CW, CH = 56, 44
# upright frames: shift anchor so body centre sits in the cell centre (head is slightly ahead)
anch = [a + 3 if i < 12 else a for i, a in enumerate(anch)]
pack(sold, CW, CH, anch, 'soldier')
show(sold, os.path.join(O, 'soldier.png'))

# ---------------- turret ----------------
tur = pick('tur4_2.png', 4, TUR_PX)
tur = [keep_largest(fix_outline(f)) for f in tur]
def turret_red(f):
    f = f.copy(); rgb = f[..., :3].astype(int); r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    a = f[..., 3] > 0
    red = a & (r > 80) & (r > g * 1.7) & (r > b * 1.7)
    f[red & (r >= 130), :3] = (255, 40, 30)
    f[red & (r < 130), :3] = (190, 18, 24)
    lab, n = ndi.label(red)
    for k in range(1, n + 1):
        ys, xs = np.where(lab == k)
        if len(ys) >= 3: f[ys.min(), xs.min(), :3] = (255, 230, 160)
    return f
WARM = [(40, 34, 32), (70, 60, 54), (106, 92, 80), (148, 132, 112), (204, 188, 160)]
def turret_warm(f):
    # warmer gunmetal ramp so the turret separates from cool grey rock/concrete; bright hazard band
    f = f.copy(); a = f[..., 3] > 0
    rgb = f[..., :3].astype(float); r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    L = lum(rgb); mx = rgb.max(-1); mn = rgb.min(-1); sat = (mx - mn) / np.maximum(mx, 1)
    red = a & (r > 80) & (r > g * 1.7) & (r > b * 1.7)
    yel = a & ~red & (r > 120) & (g > 90) & (b < g * 0.7) & (sat > 0.35)
    ink = a & (L < 30)
    grey = a & ~red & ~yel & ~ink
    t = np.percentile(L[grey], [15, 45, 75, 94])
    idx = (L >= t[0]).astype(int) + (L >= t[1]) + (L >= t[2]) + (L >= t[3])
    for v in range(5): f[grey & (idx == v), :3] = WARM[v]
    f[ink, :3] = INK
    f[yel & (L >= 110), :3] = (246, 196, 44); f[yel & (L < 110), :3] = (196, 140, 24)
    return f
HEADR = [(34, 32, 36), (74, 72, 76), (118, 114, 112), (170, 164, 152), (222, 214, 196)]   # lighter top-lit head
MOUNTR = [(26, 24, 26), (46, 42, 42), (70, 64, 60), (98, 90, 82), (132, 122, 108)]      # darker mount
def turret_hard(f):
    f = f.copy(); a = f[..., 3] > 0; H, W = a.shape
    rgb = f[..., :3].astype(float); r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    L = lum(rgb); mx = rgb.max(-1); mn = rgb.min(-1); sat = (mx - mn) / np.maximum(mx, 1)
    red = a & (r > 80) & (r > g * 1.7) & (r > b * 1.7)
    yel = a & ~red & (r > 110) & (g > 75) & (r >= g) & (b < g * 0.6) & (sat > 0.45)
    ink = a & (L < 28)
    grey = a & ~red & ~yel & ~ink
    # head/mount split: narrowest row (the neck) in the middle band, measured right of the barrel
    x0 = int(W * 0.35)
    widths = [a[y, x0:].sum() for y in range(H)]
    lo, hi = int(H * 0.40), int(H * 0.68)
    neck = lo + int(np.argmin(widths[lo:hi]))
    rows = np.arange(H)[:, None] * np.ones((1, W), int)
    for region, ramp in [(rows < neck, HEADR), (rows >= neck, MOUNTR)]:
        m = grey & region
        if not m.any(): continue
        t = np.percentile(L[m], [30, 70])
        idx = 1 + (L >= t[0]).astype(int) + (L >= t[1])          # 1..3 = dark-mid, mid, mid-light
        # hard planes: exposed top -> light plane (2 rows), exposed bottom -> dark underside
        up = np.zeros_like(a); up[1:] = ~a[:-1] | ink[:-1] | (~region[:-1] & a[:-1]); up[0] = True
        up2 = np.zeros_like(a); up2[1:] = up[:-1] & grey[:-1]
        dn = np.zeros_like(a); dn[:-1] = ~a[1:] | ink[1:] | (~region[1:] & a[1:]); dn[-1] = True
        idx = np.where(dn, 0, idx)
        idx = np.where(up2 & ~dn, np.maximum(idx, 3), idx)
        idx = np.where(up, 4, idx)
        for v in range(5): f[m & (idx == v), :3] = ramp[v]
    f[ink, :3] = INK
    f[yel & (L >= 110), :3] = (250, 200, 40); f[yel & (L < 110), :3] = (40, 34, 30)
    # neck shadow line separating head from mount
    for x in range(W):
        if a[neck, x] and not red[neck, x]: f[neck, x, :3] = INK
    # sensor eyes: the 3 biggest red clusters become 3x3 glowing eyes
    f[red, :3] = HEADR[1]
    lab, n = ndi.label(ndi.binary_dilation(red, iterations=1) & red)
    if n:
        sizes = ndi.sum(red, lab, range(1, n + 1)); order = np.argsort(-sizes)[:3]
        for rank, k in enumerate(order):
            ys, xs = np.where(lab == k + 1); cy, cx = int(round(ys.mean())), int(round(xs.mean()))
            big = rank == 0
            core = (range(-1, 3), range(-1, 3)) if big else (range(-1, 2), range(-1, 2))
            for dy in range(-2, 4 if big else 3):
                for dx in range(-2, 4 if big else 3):
                    y, x = cy + dy, cx + dx
                    if not (0 <= y < H and 0 <= x < W) or not a[y, x]: continue
                    if dy in core[0] and dx in core[1]: f[y, x, :3] = (255, 40, 30)
                    elif tuple(f[y, x, :3]) != INK: f[y, x, :3] = (150, 20, 26)
            f[cy - 1, cx - 1, :3] = (255, 236, 170); f[cy - 1, cx, :3] = (255, 150, 100)
    # thick outline: exterior ink ring
    g2 = np.pad(f, ((1, 1), (1, 1), (0, 0))); m2 = g2[..., 3] > 0
    ring = np.zeros_like(m2)
    ring[1:, :] |= m2[:-1, :]; ring[:-1, :] |= m2[1:, :]; ring[:, 1:] |= m2[:, :-1]; ring[:, :-1] |= m2[:, 1:]
    g2[ring & ~m2] = (*INK, 255)
    return g2
tur = [turret_hard(f) for f in tur]
def blink(f, on):
    g = f.copy(); rgb = g[..., :3].astype(int)
    red = (g[..., 3] > 0) & (rgb[..., 0] > 150) & (rgb[..., 1] < 90)
    g[red & (rgb[..., 0] > 240) & (rgb[..., 1] < 60), :3] = (255, 120, 96) if on else (150, 16, 20)
    return g
turf = [tur[0], blink(tur[0], True), tur[2], tur[3]]
TW, TH = max(f.shape[1] for f in turf) + 2, max(f.shape[0] for f in turf)
def base_anchor(f):
    r = np.where(f[-1, :, 3] > 0)[0]; return int((r.min() + r.max()) // 2)
TW = max(max(f.shape[1] - base_anchor(f), base_anchor(f)) for f in turf) * 2 + 2
pack(turf, TW, TH, [base_anchor(f) for f in turf], 'turret')
show(turf, os.path.join(O, 'turret.png'))

# ---------------- drone ----------------
dr = pick('drone_2.png', 4, 11.3, gap=10)
dr = [keep_largest(f, frac=0.05) for f in dr]
METAL = [(20, 22, 28), (44, 48, 58), (80, 86, 100), (132, 140, 156), (200, 206, 216)]
def drone_ramp(f):
    f = f.copy(); a = f[..., 3] > 0
    rgb = f[..., :3].astype(float); r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    L = lum(rgb)
    red = a & (r > 90) & (r > g * 1.7) & (r > b * 1.7)
    hot = a & (r > 200) & (g > 120) & (r > b + 40)
    warm = a & ~red & ~hot & (r > b + 25) & (g > b + 10) & (L > 60)     # small yellow/brass details
    metal = a & ~red & ~hot & ~warm
    ml = L[metal]
    t = np.percentile(ml, [15, 50, 82])
    idx = np.zeros(L.shape, int)
    idx[L >= t[0]] = 1; idx[L >= t[1]] = 2; idx[L >= t[2]] = 3
    # eye cluster -> body extent; add rounded top-lit shading on the body
    lab, n = ndi.label(red | hot)
    eye = None
    if n:
        sizes = ndi.sum(red | hot, lab, range(1, n + 1)); k = int(np.argmax(sizes)) + 1
        ey, ex = np.where(lab == k); eye = (int(round(ey.mean())), int(round(ex.mean())))
    H = f.shape[0]
    if eye:
        top = eye[0] - 6
        rows = np.arange(H)[:, None] * np.ones((1, f.shape[1]), int)
        body = metal & (rows >= top)
        yrel = (rows - top) / max(1, H - top)
        idx = np.where(body & (yrel < 0.28), idx + 1, idx)
        idx = np.where(body & (yrel > 0.72), idx - 1, idx)
    idx = np.clip(idx, -1, 4)
    for v, col in [(0, INK), (1, METAL[0]), (2, METAL[1]), (3, METAL[2]), (4, METAL[3])]:
        f[metal & (idx == v), :3] = col
    f[metal & (idx < 0), :3] = INK
    f[metal & (L > 175), :3] = METAL[4]
    f[warm, :3] = METAL[2]
    f[red, :3] = (255, 34, 28)
    f[hot, :3] = (255, 150, 100)
    if eye:
        cy, cx = eye
        P = ["..KKK..", ".KWWWK.", "KWRRRGK", "KWRHRGK", "KWRRRGK", ".KGGGK.", "..KKK.."]
        C = {'K': INK, 'W': METAL[4], 'G': METAL[2], 'R': (255, 34, 28), 'H': (255, 236, 170)}
        # clear stray eye pixels around the pattern
        for y in range(max(0, cy - 5), min(H, cy + 6)):
            for x in range(max(0, cx - 5), min(f.shape[1], cx + 6)):
                if (red | hot)[y, x]: f[y, x, :3] = METAL[1]
        for j, row in enumerate(P):
            for i, ch in enumerate(row):
                y, x = cy - 3 + j, cx - 3 + i
                if ch != '.' and 0 <= y < H and 0 <= x < f.shape[1] and a[y, x]: f[y, x, :3] = C[ch]
        f[cy - 1, cx - 1, :3] = (255, 150, 110)
    pad = np.pad(a, 1)
    edge = a & ~(pad[:-2, 1:-1] & pad[2:, 1:-1] & pad[1:-1, :-2] & pad[1:-1, 2:])
    f[edge & (lum(f[..., :3].astype(float)) < 90), :3] = INK
    return f
dr = [drone_ramp(f) for f in dr]
DW, DH = max(f.shape[1] for f in dr) + 2, max(f.shape[0] for f in dr) + 1
pack(dr, DW, DH, [f.shape[1] // 2 for f in dr], 'drone')
show(dr, os.path.join(O, 'drone.png'))

# ---------------- capsule ----------------
cp = pick('caps_2.png', 4, 14.5, gap=10, idx=[0])
cp = [pop_goggles(keep_largest(fix_outline(f), frac=0.05)) for f in cp]
cp = quantize(cp, 20)
Image.fromarray(cp[0].astype(np.uint8), 'RGBA').save(os.path.join(A, 'capsule.png'))
show(cp, os.path.join(O, 'capsule.png'))

# ---------------- pickups: AI eagle wings + hand-drawn shield & bold letter ----------------
LET = {
 'M': ["XX...XX", "XXX.XXX", "XXXXXXX", "XX.X.XX", "XX...XX", "XX...XX", "XX...XX", "XX...XX"],
 'S': [".XXXXX.", "XX...XX", "XX.....", ".XXXXX.", ".....XX", ".....XX", "XX...XX", ".XXXXX."],
 'L': ["XX.....", "XX.....", "XX.....", "XX.....", "XX.....", "XX.....", "XXXXXXX", "XXXXXXX"],
}
wings = pick('pick_2.png', 3, 17.0, gap=10, idx=[0])[0]
wings = keep_largest(fix_outline(wings), frac=0.05)
wings = quantize([wings], 12)[0]
GOLD, GOLDD, RED, REDD, WHITE = (255, 214, 72, 255), (200, 130, 30, 255), (208, 30, 36, 255), (120, 10, 20, 255), (255, 255, 255, 255)
for k, pat in LET.items():
    w = wings.copy()
    H, W = w.shape[:2]
    sw, sh = 13, 15
    x0 = W // 2 - sw // 2; y0 = max(0, H // 2 - sh // 2)
    need = y0 + sh
    if need > H:
        w = np.pad(w, ((0, need - H), (0, 0), (0, 0))); H = need
    for j in range(sh):
        inset = max(0, j - (sh - 5))
        for i in range(inset, sw - inset):
            edge = i == inset or i == sw - 1 - inset or j == 0 or j == sh - 1
            rim = (i == inset + 1 or i == sw - 2 - inset or j == 1 or j == sh - 2) and not edge
            w[y0 + j, x0 + i] = (*OUT, 255) if edge else (GOLD if (rim and (i < sw // 2 or j == 1)) else GOLDD) if rim else RED
    lx, ly = x0 + 3, y0 + 2
    for j, row in enumerate(pat):
        for i, ch in enumerate(row):
            if ch == 'X' and tuple(w[ly + j + 1, lx + i + 1]) == RED: w[ly + j + 1, lx + i + 1] = REDD
    for j, row in enumerate(pat):
        for i, ch in enumerate(row):
            if ch == 'X':
                w[ly + j, lx + i] = WHITE
                if tuple(w[ly + j + 1, lx + i]) == RED: w[ly + j + 1, lx + i] = REDD
    Image.fromarray(w.astype(np.uint8), 'RGBA').save(os.path.join(A, f'pickup-{k}.png'))
    show([w], os.path.join(O, f'pickup-{k}.png'))

print('soldier cell', CW, CH, 'frames', len(sold), [f.shape for f in sold])
print('turret cell', TW, TH, [f.shape for f in turf])
print('drone cell', DW, DH, [f.shape for f in dr])
print('capsule', cp[0].shape, 'pickup', w.shape)
json.dump({'soldier': [CW, CH], 'turret': [TW, TH], 'drone': [DW, DH]}, open(os.path.join(O, 'sizes.json'), 'w'))
