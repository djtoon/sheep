"""Stage-2 roster art: raw AI sheets -> crisp game-scale spritesheets in assets/roster2/.
python art/raw/roster2/build2.py   (also writes art/raw/roster2/out/meta.json with cell sizes / muzzle points)
"""
import os, sys, json
import numpy as np
from PIL import Image
from scipy import ndimage as ndi
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'enemies'))
from proc import load, split_n, grid_sample, to_img, show   # noqa

ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
A = os.path.join(ROOT, 'assets', 'roster2'); os.makedirs(A, exist_ok=True)
O = os.path.join(HERE, 'out'); os.makedirs(O, exist_ok=True)
INK = (14, 10, 18)

# unit: (raw sheet, frames, target height of frame 0 in game px, cell pad, keep-fraction for detached parts)
UNITS = {
    'trooper': ('trooper_2.png', 8, 42, 0.02),
    'shield':  ('shield_2.png', 8, 44, 0.02),
    'sniper':  ('sniper_1.png', 8, 44, 0.06),
    'tank':    ('tank_1.png', 6, 56, 0.02),
    'drone2':  ('drone2_2.png', 6, 36, 0.03),
    'mech':    ('mech_1.png', 8, 64, 0.02),
}


def lum(c): return 0.3 * c[..., 0] + 0.59 * c[..., 1] + 0.11 * c[..., 2]


def keep(f, frac):
    m = f[..., 3] > 0
    lab, n = ndi.label(m, structure=np.ones((3, 3)))
    if n > 1:
        s = ndi.sum(m, lab, range(1, n + 1))
        ok = [i + 1 for i, v in enumerate(s) if v >= s.max() * max(frac, 1e-9)]
        f = f.copy(); f[~np.isin(lab, ok)] = 0
    al = f[..., 3] > 0
    r = np.where(al.any(1))[0]; c = np.where(al.any(0))[0]
    return f[r.min():r.max() + 1, c.min():c.max() + 1]


def remove_smoke(a):
    # desaturated mid-grey soft smoke puffs/fog from the generations
    rgb = a[..., :3].astype(float); mx = rgb.max(-1); mn = rgb.min(-1)
    fog = (a[..., 3] < 235) & (a[..., 3] > 0)
    a = a.copy(); a[fog, 3] = 0
    return a


def quant(frames, n):
    allpx = np.concatenate([f[(f[..., 3] > 0) & ~((f[..., 0] == 255) & (f[..., 1] == 38))][:, :3] for f in frames])
    pal = Image.fromarray(allpx.reshape(1, -1, 3).astype(np.uint8)).quantize(colors=n, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    out = []
    for f in frames:
        f = f.copy(); sel = (f[..., 3] > 0) & ~((f[..., 0] == 255) & (f[..., 1] == 38) & (f[..., 2] == 30))
        q = Image.fromarray(f[sel][:, :3].reshape(1, -1, 3).astype(np.uint8)).quantize(palette=pal, dither=Image.Dither.NONE).convert('RGB')
        f[sel, :3] = np.array(q).reshape(-1, 3); out.append(f)
    return out


WALK = {'trooper': 'trooper_walk_1.png', 'shield': 'shield_walk_1.png', 'mech': 'mech_walk_1.png'}
WALK_ADJ = {'trooper': 0, 'shield': 0, 'mech': -2}
LIFT = {'shield': (1.32, 14), 'drone2': (1.2, 10)}
EYE = {'trooper': (7, 2), 'shield': (6, 2), 'sniper': (3, 2), 'mech': (6, 2)}   # visor bar w x h painted on the head light


def eyes(f, name, nframes_upright):
    # the head's light becomes a chunky glowing visor: ink frame, bright red bar, hot pixel at the front
    if name not in EYE: return f
    f = f.copy(); a = f[..., 3] > 0; H, W = a.shape
    red = a & (f[..., 0] == 255) & (f[..., 1] == 38)
    top = np.where(a.any(1))[0][0]
    zone = np.zeros_like(red); zone[top:top + int(H * (0.28 if name != 'mech' else 0.22))] = True
    ys, xs = np.where(red & zone)
    if not len(ys): return f
    # choose the leftmost cluster in the head zone (visor faces left); skip the antenna tip (topmost 2 rows)
    ok = ys > top + 1
    if ok.any(): ys, xs = ys[ok], xs[ok]
    hx = np.median(np.where(a[top:top + 6])[1])
    i = np.argmin(np.abs(xs - (hx - 3)) + np.abs(ys - (top + 7)) * 0.7); cy, cx = ys[i], xs[i]
    w, h = EYE[name]
    for y in range(cy - 1, cy + h + 1):
        for x in range(cx - 1, cx + w + 1):
            if 0 <= y < H and 0 <= x < W and a[y, x]:
                inside = cy <= y < cy + h and cx <= x < cx + w
                # ink brim above, dark-red glow spill on the sides and below
                f[y, x, :3] = (255, 38, 30) if inside else (INK if y < cy else (150, 18, 24))
    f[cy, cx, :3] = (255, 232, 160); f[cy, cx + 1, :3] = (255, 232, 160)
    if w > 3: f[cy, cx + 2, :3] = (255, 150, 100)
    return f


def prered(f):
    # lock lights before quantising so the palette can't swallow them
    f = f.copy(); a = f[..., 3] > 0; rgb = f[..., :3].astype(int); r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    red = a & (r > 150) & (r > g * 1.8) & (r > b * 1.8)
    f[red, :3] = (255, 38, 30)
    # night stage: lift the body values a step so units separate from the dark base
    body = a & ~red
    k, o = LIFT.get(CUR, (1.14, 10))
    f[body, :3] = np.clip(rgb[body] * k + o, 0, 255).astype(np.uint8)
    return f


# ---- round 2: night ramps. Crates sit at L 55-80 (olive), steel floors L 23-45 (grey): unit mids sit above both,
# shadows sit near ink, so every unit has a real light/dark split and reads off crates and steel by value.
RAMPS = {
    'olive': [(20, 24, 12), (46, 52, 26), (100, 108, 54), (156, 162, 90), (216, 212, 146)],
    'grey':  [(16, 16, 22), (36, 38, 48), (78, 82, 96), (132, 136, 150), (200, 204, 214)],
    'tan':   [(40, 30, 18), (92, 76, 50), (158, 138, 100), (206, 188, 148), (242, 232, 200)],
}
METAL = [(14, 14, 18), (32, 33, 40), (112, 116, 130)]   # near-black metal with one grey highlight
UNIT_RAMP = {'trooper': 'olive', 'shield': 'grey', 'sniper': 'tan', 'tank': 'olive', 'drone2': 'olive', 'mech': 'olive'}
LAMP = np.array([253, 236, 168])


def night_ramp(f, name):
    f = f.copy(); a = f[..., 3] > 0
    rgb = f[..., :3].astype(float); r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    L = lum(rgb); mx = rgb.max(-1); mn = rgb.min(-1); sat = (mx - mn) / np.maximum(mx, 1)
    red = a & (r == 255) & (g == 38)
    yel = a & ~red & (r > 105) & (g > 80) & (r >= g * 0.95) & (b < g * 0.62) & (sat > {'shield': 0.35, 'tank': 0.5, 'mech': 0.66}.get(name, 0.64))
    rest = a & ~red & ~yel
    ramp = RAMPS[UNIT_RAMP[name]]
    if UNIT_RAMP[name] == 'grey':
        metal = np.zeros_like(a)
    else:
        metal = rest & (sat < 0.13)
    if name == 'drone2':   # enemy1 drone: olive body box only; arms, rotors, eye housing and gatling pod are black metal
        H_, W_ = a.shape; rows = np.arange(H_)[:, None]; cols = np.arange(W_)[None, :]
        ys_, xs_ = np.where(a); cx_ = np.median(xs_); top_ = ys_.min(); h_ = ys_.max() - top_
        body = (rows > top_ + h_ * 0.22) & (rows < top_ + h_ * 0.62) & (np.abs(cols - cx_) < W_ * 0.17)
        metal = rest & ~body
    if name in ('mech', 'tank'):   # gatling arm / twin barrels and tracks are black metal in enemy1
        H_, W_ = a.shape; rows = np.arange(H_)[:, None]; cols = np.arange(W_)[None, :]
        ys_, xs_ = np.where(a); top_ = ys_.min(); h_ = ys_.max() - top_; x0_ = xs_.min(); w_ = xs_.max() - x0_
        if name == 'mech':
            gun = (cols < x0_ + w_ * 0.36) & (rows > top_ + h_ * 0.36) & (rows < top_ + h_ * 0.66)
        else:
            gun = ((cols < x0_ + w_ * 0.30) & (rows > top_ + h_ * 0.25) & (rows < top_ + h_ * 0.62)) | (rows > top_ + h_ * 0.72)
        metal = metal | (rest & gun & ~yel)
    main = rest & ~metal
    # smooth the value map inside each material so the ramp reads as clean planes, not AI noise
    Lm = np.where(main, L, np.nan)
    from scipy.ndimage import generic_filter
    Ls = generic_filter(Lm, lambda v: np.nanmedian(v) if np.isfinite(v).any() else np.nan, size=3, mode='constant', cval=np.nan)
    L = np.where(main & np.isfinite(Ls), Ls * 0.6 + L * 0.4, L)
    if main.any():
        t = np.percentile(L[main], [18, 40, 68, 90])
        idx = (L >= t[0]).astype(int) + (L >= t[1]) + (L >= t[2]) + (L >= t[3])
        for v in range(5): f[main & (idx == v), :3] = ramp[v]
    if metal.any():
        t = np.percentile(L[metal], [40, 78])
        idx = (L >= t[0]).astype(int) + (L >= t[1])
        for v in range(3): f[metal & (idx == v), :3] = METAL[v]
    f[yel, :3] = (240, 190, 40)
    return f


def finish(f):
    """ink edges + unbroken exterior ring, glowing reds with hot cores, rim light on upward-facing edges"""
    f = f.copy(); a = f[..., 3] > 0; H, W = a.shape
    rgb = f[..., :3].astype(float); r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    L = lum(rgb)
    red = a & (r > 200) & (g < 90) & (b < 90)
    f[red, :3] = (255, 38, 30)
    lab, n = ndi.label(red)
    for k in range(1, n + 1):
        ys, xs = np.where(lab == k)
        f[ys.min(), xs.min(), :3] = (255, 232, 160)   # hot pixel, top-left of every light
    # dark pixels on the silhouette edge -> ink
    pad = np.pad(a, 1)
    edge = a & ~(pad[:-2, 1:-1] & pad[2:, 1:-1] & pad[1:-1, :-2] & pad[1:-1, 2:])
    f[edge & (L < 70) & ~red, :3] = INK
    f[a & (L < 22) & ~red, :3] = INK
    # rim light: first non-ink pixel under an exposed top edge gets lifted toward a warm white
    src = f.copy()
    for y in range(1, H):
        for x in range(W):
            if not a[y, x] or red[y, x]: continue
            c = src[y, x, :3].astype(int)
            if tuple(c) == INK: continue
            up_open = (not a[y - 1, x]) or (tuple(src[y - 1, x, :3]) == INK and (y < 2 or not a[y - 2, x]))
            if up_open and (y < 2 or not a[y - 2, x] or tuple(src[y - 2, x, :3]) == INK or True):
                if lum(c[None].astype(float))[0] > 40:
                    f[y, x, :3] = np.clip(c * 0.35 + LAMP * 0.65, 0, 255).astype(np.uint8)
    # exterior ink ring
    g2 = np.pad(f, ((1, 1), (1, 1), (0, 0))); m2 = g2[..., 3] > 0
    ring = np.zeros_like(m2)
    ring[1:, :] |= m2[:-1, :]; ring[:-1, :] |= m2[1:, :]; ring[:, 1:] |= m2[:, :-1]; ring[:, :-1] |= m2[:, 1:]
    g2[ring & ~m2] = (*INK, 255)
    # second ink pixel on the lower 45% of the silhouette (feet, legs, tracks): heavier base, Metal Slug style
    m3 = g2[..., 3] > 0; H2 = m3.shape[0]
    rows = np.where(m3.any(1))[0]; cut = rows.min() + int((rows.max() - rows.min()) * 0.55)
    g3 = np.pad(g2, ((0, 1), (1, 1), (0, 0))); m4 = g3[..., 3] > 0
    ring2 = np.zeros_like(m4)
    ring2[:, 1:] |= m4[:, :-1]; ring2[:, :-1] |= m4[:, 1:]   # sideways only: feet keep a single ink row
    ring2 &= ~m4; ring2[:cut + 1] = False
    g3[ring2] = (*INK, 255)
    return g3


def pack(frames, anchors, name):
    lw = max(ax for ax in anchors); rw = max(f.shape[1] - ax for f, ax in zip(frames, anchors))
    cw = 2 * max(lw, rw) + 2; ch = max(f.shape[0] for f in frames) + 1
    sheet = np.zeros((ch, cw * len(frames), 4), np.uint8)
    for k, (f, ax) in enumerate(zip(frames, anchors)):
        h, w = f.shape[:2]; x0 = k * cw + cw // 2 - ax; y0 = ch - h
        sub = sheet[y0:y0 + h, x0:x0 + w]; m = f[..., 3] > 0; sub[m] = f[m]
    Image.fromarray(sheet, 'RGBA').save(os.path.join(A, name + '.png'))
    return cw, ch


def centroid_x(f):
    ys, xs = np.where(f[..., 3] > 0); return int(round(np.median(xs)))


meta = {}
os.chdir(HERE)
for name, (sheet, n, tgt, frac) in UNITS.items():
    CUR = name
    a = load(sheet)
    a = remove_smoke(a)
    segs = split_n(a, n)
    s0, e0 = segs[0]; m0 = a[:, s0:e0, 3] > 160; ys = np.where(m0.any(1))[0]
    px = (ys.max() - ys.min() + 1) / (tgt - 2)
    frames = [keep(grid_sample(a[:, s:e], px), frac) for s, e in segs]
    nwalk = 0
    if name in WALK:   # dedicated 8-frame walk cycle replaces the pose sheet's 4 walk frames
        w = remove_smoke(load(WALK[name])); wsegs = split_n(w, 8)
        ws0, we0 = wsegs[0]; wm = w[:, ws0:we0, 3] > 160; wys = np.where(wm.any(1))[0]
        wpx = (wys.max() - wys.min() + 1) / (frames[4].shape[0] + WALK_ADJ.get(name, 0))
        frames = [keep(grid_sample(w[:, s_:e_], wpx), frac) for s_, e_ in wsegs] + frames[4:]
        nwalk = 4
    frames = [prered(f) for f in frames]
    frames = quant(frames, 26)
    frames = [night_ramp(f, name) for f in frames]
    frames = [eyes(f, name, 6) if k < 6 + nwalk else f for k, f in enumerate(frames)]
    frames = [finish(f) for f in frames]
    # anchor: median column of the lower half (legs / tracks) for upright frames, bbox centre for wrecks
    anchors = []
    for f in frames:
        lo = f[f.shape[0] // 2:]
        ys_, xs_ = np.where(lo[..., 3] > 0)
        anchors.append(int(round(np.median(xs_))) if len(xs_) else f.shape[1] // 2)
    cw, ch = pack(frames, anchors, name)
    # muzzle: leftmost opaque pixel of the fire frame relative to bottom-centre
    fire_idx = {'trooper': 5, 'shield': 5, 'sniper': 5, 'tank': 3, 'drone2': 4, 'mech': 5}[name] + nwalk
    sheet_img = np.array(Image.open(os.path.join(A, name + '.png')))
    fr = sheet_img[:, fire_idx * cw:(fire_idx + 1) * cw]
    al = fr[..., 3] > 0; xs = np.where(al.any(0))[0]; x = xs.min(); yy = np.where(al[:, x])[0]
    meta[name] = {'cell': [cw, ch], 'frames': len(frames), 'walk': 4 + nwalk, 'muzzle': [int(x - cw // 2), int(round(yy.mean())) - ch],
                  'sizes': [list(f.shape[:2]) for f in frames]}
    show(frames, os.path.join(O, name + '.png'), 4, (40, 44, 60))
    print(name, 'px', round(px, 2), 'cell', cw, ch, 'muzzle', meta[name]['muzzle'])
json.dump(meta, open(os.path.join(O, 'meta.json'), 'w'), indent=1)
