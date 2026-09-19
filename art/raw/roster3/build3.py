# Builds the stage-3 roster sheets: key poses traced from enemy2.png, extra poses generated from the key and traced
# onto the SAME palette + scale, packed into equal cells (feet on the bottom row, body centred). Also FX sheets.
import sys, os, json, math, numpy as np, cv2
sys.path.insert(0, 'art/raw/roster3')
from PIL import Image, ImageDraw
import trace3 as T

SRC = 'art/raw/roster3/src'
OUTD = 'assets/roster3'

def load_rgba(f):
    a = np.array(Image.open(f).convert('RGBA'))
    ys, xs = np.where(a[..., 3] > 128)
    a = a[max(0, ys.min() - 4):ys.max() + 5, max(0, xs.min() - 4):xs.max() + 5]
    return a

def to_grid(rgb, fg, cen, sc, OL):
    H, W = fg.shape
    flat = rgb.reshape(-1, 3).astype(np.float32)
    dist = ((flat[:, None, :] - cen[None]) ** 2 * np.array([0.3, 0.5, 0.2])).sum(-1)
    idx = dist.argmin(1).reshape(H, W); idx[~fg] = -1
    gh, gw = int(round(H / sc)), int(round(W / sc))
    out = np.full((gh, gw), -1, np.int16)
    for j in range(gh):
        for i in range(gw):
            c = idx[int(j * sc):int((j + 1) * sc), int(i * sc):int((i + 1) * sc)].ravel()
            o = c[c >= 0]
            if o.size == 0 or o.size < c.size * 0.45: continue
            cnt = np.bincount(o, minlength=len(cen))
            nonol = cnt.copy(); nonol[OL] = 0
            out[j, i] = OL if (cnt[OL] > o.size * 0.5 or nonol.sum() == 0) else int(nonol.argmax())
    return cleanup(out, OL)

def cleanup(out, OL):
    ys, xs = np.where(out >= 0); out = out[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    out = np.pad(out, 1, constant_values=-1)
    dil = lambda m: m | np.roll(m, 1, 0) | np.roll(m, -1, 0) | np.roll(m, 1, 1) | np.roll(m, -1, 1)
    dil8 = lambda m: dil(m) | np.roll(np.roll(m, 1, 0), 1, 1) | np.roll(np.roll(m, 1, 0), -1, 1) | np.roll(np.roll(m, -1, 0), 1, 1) | np.roll(np.roll(m, -1, 0), -1, 1)
    body = (out >= 0) & (out != OL)
    out[(out == OL) & ~dil8(body)] = -1
    # drop 1-px speckle islands of body colour
    out[dil(body) & (out < 0)] = OL
    return out

def trace_pose(f, cen, OL, target_h=None, target_w=None):
    a = load_rgba(f)
    fg = a[..., 3] > 128
    ys, xs = np.where(fg)
    if target_h: sc = (ys.max() - ys.min() + 1) / target_h
    else: sc = (xs.max() - xs.min() + 1) / target_w
    return to_grid(a[..., :3].copy(), fg, cen, sc, OL)

UNIT = {
    # key: from trace3 (enemy2 or its clean regeneration); poses: (file, target height or ('w', width))
    'hazmat': dict(key='trace', poses={'walk1': ('hazmat_walk1.png', 41), 'walk2': ('hazmat_walk2.png', 41)}),
    'toxic': dict(key='trace', poses={'walk1': ('toxic_walk1.png', 43), 'walk2': ('toxic_walk2.png', 43)}),
    'clawbot': dict(key='trace', poses={'grab': ('clawbot_grab.png', 41)}),
    'xeno': dict(key=('xeno_base.png', ('w', 60)), poses={'run': ('xeno_run.png', ('w', 64)), 'leap': ('xeno_leap.png', ('w', 66))}),
    'mutant': dict(key='trace', poses={'walk1': ('mutant_walk1.png', 49), 'walk2': ('mutant_walk2.png', 49), 'slash': ('mutant_slash.png', 53)}),
    'walker': dict(key='trace', poses={'walk1': ('walker_walk1.png', 61), 'walk2': ('walker_walk2.png', 61)}),
}

def build_unit(name):
    U = UNIT[name]
    if U['key'] == 'trace':
        key, pal, OL = T.trace(name)
        cen = pal[:-1].astype(np.float32)
    else:
        f, (kind, v) = U['key']
        a = load_rgba(f'{SRC}/{f}'); fg = a[..., 3] > 128
        cen = T.palette(a[..., :3], fg, T.UNITS[name][2]); OL = int(cen.sum(1).argmin())
        ys, xs = np.where(fg); sc = (xs.max() - xs.min() + 1) / v
        key = to_grid(a[..., :3].copy(), fg, cen, sc, OL)
        pal = np.vstack([cen, [[0, 0, 0]]]).astype(np.uint8)
    frames = {'key': key}
    for k, (f, t) in U['poses'].items():
        if isinstance(t, tuple): frames[k] = trace_pose(f'{SRC}/{f}', cen, OL, target_w=t[1])
        else: frames[k] = trace_pose(f'{SRC}/{f}', cen, OL, target_h=t)
    return frames, pal.astype(np.uint8), OL

def feet_cx(f):
    m = f >= 0; h = f.shape[0]
    ys, xs = np.where(m[int(h * 0.6):]); return xs.mean() if len(xs) else f.shape[1] / 2

def render(f, pal, flash=False):
    h, w = f.shape; a = np.zeros((h, w, 4), np.uint8)
    m = f >= 0; a[m, :3] = pal[f[m]]; a[m, 3] = 255
    if flash:
        rgb = a[..., :3].astype(int); a[..., :3] = np.clip(rgb + 150, 0, 255).astype(np.uint8)
    return a

def shift_up(f, d):
    if d == 0: return f
    o = np.full_like(f, -1); o[:-d] = f[d:]; return o

def pack(name, seq, pal, OL, cw, ch, anchor='feet'):
    """seq: list of (frameArray, dy, flash). Returns sheet image, frame count."""
    cells = []
    for (f, dy, fl) in seq:
        img = post(name, render(f, pal, False))
        if fl: img[..., :3] = np.clip(img[..., :3].astype(int) + 150, 0, 255).astype(np.uint8)
        h, w = img.shape[:2]
        cell = np.zeros((ch, cw, 4), np.uint8)
        f = np.where(img[..., 3] > 0, 0, -1)
        cx = feet_cx(f) if anchor == 'feet' else w / 2
        x0 = int(round(cw / 2 - cx)); y0 = ch - h - dy if anchor == 'feet' else int(round(ch / 2 - h / 2)) - dy
        xs0, ys0 = max(0, -x0), max(0, -y0); xd, yd = max(0, x0), max(0, y0)
        ww, hh = min(w - xs0, cw - xd), min(h - ys0, ch - yd)
        cell[yd:yd + hh, xd:xd + ww] = img[ys0:ys0 + hh, xs0:xs0 + ww]
        cells.append(cell)
    sheet = np.concatenate(cells, 1)
    return Image.fromarray(sheet, 'RGBA'), len(cells)

# ---------------------------------------------------------------- readability post-pass (round 2)
OLC = np.array([12, 10, 18], np.uint8)
def _nb(m, dy, dx):
    o = np.zeros_like(m); H, W = m.shape
    o[max(0, dy):H + min(0, dy), max(0, dx):W + min(0, dx)] = m[max(0, -dy):H - max(0, dy), max(0, -dx):W - max(0, dx)]
    return o
def post(name, a):
    a = np.pad(a, ((1, 1), (1, 1), (0, 0)))
    op = a[..., 3] > 0
    rgb = a[..., :3].astype(int)
    lum = rgb.mean(-1); sat = rgb.max(-1) - rgb.min(-1)
    dark = op & (lum < 40)
    if name in ('hazmat', 'toxic', 'walker', 'clawbot'):
        armour = op & (sat < 40) & (lum > 120)
        solid = op & ~armour                      # outline, dark joints, visor, gun
        up_open = ~_nb(armour, 1, 0)              # pixel above is not armour
        dn_open = ~_nb(armour, -1, 0); rt_open = ~_nb(armour, 0, -1); lf_open = ~_nb(armour, 0, 1)
        dn2 = ~_nb(armour, -2, 0)
        G = {'hi': (248, 250, 252), 'top': (220, 224, 232), 'lt': (200, 204, 212), 'md': (140, 148, 168), 'dk': (82, 90, 112)}
        col = np.zeros_like(rgb); col[:] = G['lt']
        col[armour & (up_open | lf_open)] = G['top']
        col[armour & up_open & lf_open] = G['hi']
        col[armour & rt_open & ~up_open] = G['md']
        col[armour & dn_open] = G['md']
        col[armour & dn_open & rt_open] = G['dk']
        col[armour & dn_open & _nb(dark, -1, 0)] = G['dk']
        rgb[armour] = col[armour]
        if name == 'toxic':
            from scipy import ndimage
            green = op & (rgb[..., 1] > rgb[..., 0] + 40) & (rgb[..., 1] > rgb[..., 2] + 40)
            lab, n = ndimage.label(green)
            if n:
                sizes = ndimage.sum(green, lab, range(1, n + 1)); keep = lab == (1 + int(np.argmax(sizes)))
                other = green & ~keep
                rgb[other] = (150, 154, 168)
            orange = op & (rgb[..., 0] > 170) & (rgb[..., 1] > 70) & (rgb[..., 1] < 190) & (rgb[..., 2] < 90)
            rgb[orange] = (44, 48, 62)
            # 1px glint on the dark visor
            if orange.any():
                ys, xs = np.where(orange); rgb[ys.min() + 1 if ys.min() + 1 <= ys.max() else ys.min(), xs.min() + 1 if xs.min() + 1 <= xs.max() else xs.min()] = (200, 220, 240)
        # visor: bigger and brighter red
        red = op & (rgb[..., 0] > 140) & (rgb[..., 1] < 90) & (rgb[..., 2] < 90)
        if name == 'hazmat' and red.any():
            ys, xs = np.where(red); top = ys.min()
            head = red & (np.arange(red.shape[0])[:, None] < top + 5)
            grow = (head | _nb(head, 0, 1) | _nb(head, 0, -1) | _nb(head, 1, 0)) & op & ~(lum > 200)
            rgb[grow] = (255, 36, 44)
            hy = np.where(grow)[0].min(); hl = grow & (np.arange(grow.shape[0])[:, None] == hy)
            rgb[hl] = (255, 170, 160)
    if name == 'mutant':
        lifted = op & (lum >= 48)
        v = rgb[lifted].astype(float) * np.array([1.5, 1.35, 1.5]) + np.array([34, 22, 34])
        rgb[lifted] = np.clip(v, 0, 255).astype(int)
        rgb[op & (lum >= 30) & (lum < 48)] = np.clip(rgb[op & (lum >= 30) & (lum < 48)] * 1.25, 0, 255)
        lum = rgb.mean(-1); dark = op & (lum < 40)
        hi = op & (lum > np.percentile(lum[op & ~dark], 85)) if (op & ~dark).any() else op & False
        rgb[hi] = (245, 205, 255)
    if name == 'xeno':
        # off the lab's teal: violet-black carapace, bone-white plates, hot-magenta eye
        body = op & (lum >= 30)
        if body.any():
            q = np.percentile(lum[body], [25, 62, 88])
            ramp = [(44, 30, 66), (122, 90, 168), (152, 120, 198), (232, 222, 200)]
            t = np.digitize(lum, q)
            for k in range(4): rgb[body & (t == k)] = ramp[k]
            # eye: 2px hot magenta near the front of the head (sprite faces left)
            cols = np.where(body.any(0))[0]; fx = cols.min()
            rows = np.where(body[:, fx:fx + 6].any(1))[0]
            if len(rows):
                ey, ex = rows.min() + 2, fx + 4
                if ey < rgb.shape[0] and ex + 1 < rgb.shape[1]: rgb[ey, ex:ex + 2] = (255, 40, 200)
        lum = rgb.mean(-1); dark = op & (lum < 40)
    if name in ('xeno', 'mutant'):
        rim = (190, 130, 240) if name == 'xeno' else (225, 150, 255)
        body = op & ~dark
        thick = body & _nb(body, -1, 0) & _nb(body, -2, 0)
        if name == 'xeno':
            top = body & ~_nb(body, 1, 0)
            rgb[top] = (200, 172, 255)
        else:
            top = thick & ~_nb(body, 1, 0)
            rgb[top] = (np.array(rgb[top]) * 0.35 + np.array(rim) * 0.65).astype(int)
    if name == 'clawbot':
        # dome/eye off the lab's cyan: dim steel lens with a red-amber core
        cy = op & (rgb[..., 2] > 140) & (rgb[..., 1] > 110) & (rgb[..., 2] - rgb[..., 0] > 70)
        if cy.any():
            l = lum[cy]; q = np.percentile(l, [40, 75])
            t = np.digitize(lum, q)
            rgb[cy & (t == 0)] = (64, 70, 86)
            rgb[cy & (t == 1)] = (210, 50, 30)
            rgb[cy & (t == 2)] = (255, 190, 90)
    a[..., :3] = np.clip(rgb, 0, 255).astype(np.uint8)
    # thick outline: second ring of near-black around the whole silhouette
    op = a[..., 3] > 0
    ring = (_nb(op, 1, 0) | _nb(op, -1, 0) | _nb(op, 0, 1) | _nb(op, 0, -1)) & ~op
    a[ring, :3] = OLC; a[ring, 3] = 255
    return a

# ---------------------------------------------------------------- FX sheets (projectiles, flame, beam, goo)
def fx_sheets():
    out = {}
    def img(w, h): return np.zeros((h, w, 4), np.uint8)
    def put(a, x, y, c):
        if 0 <= y < a.shape[0] and 0 <= x < a.shape[1]: a[y, x] = (*c, 255)
    OLc = (12, 10, 18)
    # red laser bolt 10x4, 2 frames
    fr = []
    for k in range(2):
        a = img(10, 4)
        for x in range(10):
            put(a, x, 0, OLc); put(a, x, 3, OLc)
            put(a, x, 1, (255, 240, 230) if 2 <= x <= 7 else (255, 70, 60)); put(a, x, 2, (230, 30, 40) if k == 0 else (255, 90, 70))
        put(a, 0, 1, OLc); put(a, 0, 2, OLc); put(a, 9, 1, OLc); put(a, 9, 2, OLc)
        fr.append(a)
    out['r3-laser'] = (np.concatenate(fr, 1), 10, 4)
    # cyan orb 8x8, 3 frames (pulse)
    fr = []
    for k in range(3):
        a = img(8, 8)
        for y in range(8):
            for x in range(8):
                d = math.hypot(x - 3.5, y - 3.5)
                if d < 3.6: a[y, x] = (*((230, 255, 255) if d < 1.3 + 0.5 * (k == 1) else (60, 220, 240) if d < 2.5 else (20, 120, 170)), 255)
                elif d < 4.2: a[y, x] = (*OLc, 255)
        fr.append(a)
    out['r3-orb'] = (np.concatenate(fr, 1), 8, 8)
    # toxic flame cone 48x20, 4 frames (tip on the right = nozzle; drawn facing right, flipped in code)
    rng = np.random.default_rng(3); fr = []
    for k in range(4):
        a = img(48, 20)
        for x in range(48):
            half = 2 + x * 0.17
            for y in range(20):
                dy = abs(y - 9.5)
                n = rng.uniform(-1.2, 1.2)
                if dy < half + n:
                    t = x / 47 + rng.uniform(-0.08, 0.08)
                    c = (240, 255, 170) if t < 0.18 else (170, 255, 60) if t < 0.45 else (90, 210, 40) if t < 0.75 else (40, 120, 30)
                    if dy > half - 1.2 + n: c = (60, 150, 30)
                    a[y, 47 - x] = (*c, 255)
        fr.append(a)
    out['r3-flame'] = (np.concatenate(fr, 1), 48, 20)
    # walker beam segment 16x9 (tiles horizontally), 2 frames + tell line 16x3
    fr = []
    for k in range(2):
        a = img(16, 9)
        for x in range(16):
            for y in range(9):
                dy = abs(y - 4)
                c = (255, 255, 255) if dy == 0 else (160, 250, 255) if dy == 1 else (40, 200, 240) if dy == 2 else (20, 110, 170) if dy == 3 else None
                if k == 1 and dy == 3 and x % 4 == 0: c = (160, 250, 255)
                if c: a[y, x] = (*c, 255)
        fr.append(a)
    out['r3-beam'] = (np.concatenate(fr, 1), 16, 9)
    a = img(16, 3)
    for x in range(16):
        if x % 4 < 3: a[1, x] = (255, 60, 60, 255)
    out['r3-tell'] = (a, 16, 3)
    # goo splats 40x28, 7 frames, two colourways
    for key, pal in (('r3-goo-acid', [(230, 255, 120), (140, 230, 40), (60, 150, 30), (25, 70, 20)]),
                     ('r3-goo-purple', [(240, 190, 255), (170, 90, 200), (100, 50, 130), (45, 20, 60)])):
        rng = np.random.default_rng(7); blobs = [(rng.uniform(-14, 14), rng.uniform(-10, 2), rng.uniform(2, 5)) for _ in range(9)]
        drops = [(rng.uniform(-18, 18), rng.uniform(-22, -6), rng.uniform(-1, 1)) for _ in range(6)]
        fr = []
        for k in range(7):
            a = img(40, 28); t = (k + 1) / 7
            m = np.zeros((28, 40), bool); Y, X = np.mgrid[0:28, 0:40] + 0.5
            if k < 5:
                for (bx, by, br) in blobs:
                    r = br * (0.4 + 1.2 * t) * (1.0 if k < 4 else 0.8)
                    m |= (X - (20 + bx * t * 1.2)) ** 2 + (Y - (22 + by * t)) ** 2 <= r * r
            # puddle on the floor
            pw = 6 + 12 * t; m |= (((X - 20) / pw) ** 2 + ((Y - 26) / 1.8) ** 2 <= 1)
            for (dx, dy, dd) in drops:
                if 0 < k < 6:
                    px_, py_ = 20 + dx * t * 1.1, 22 + dy * math.sin(math.pi * min(1, t * 1.3)) + 10 * t * t
                    m |= (X - px_) ** 2 + (Y - py_) ** 2 <= 1.6 ** 2
            col = np.zeros((28, 40, 3), np.uint8); col[:] = pal[1]
            up = m & ~np.roll(m, 1, 0); col[up] = pal[0]
            dn = m & ~np.roll(m, -1, 0); col[dn] = pal[2]
            a[m, :3] = col[m]; a[m, 3] = 255
            ring = (np.roll(m, 1, 0) | np.roll(m, -1, 0) | np.roll(m, 1, 1) | np.roll(m, -1, 1)) & ~m
            a[ring] = (*pal[3], 255)
            fr.append(a)
        out[key] = (np.concatenate(fr, 1), 40, 28)
    return out

ANIM_SPEC = {
    # name: cell (w,h), anims: key -> (frame list, fps, repeat)
    'hazmat': ((64, 48), [('move', ['walk1', ('walk1', 1), 'walk2', ('walk2', 1)], 8, -1), ('attack', ['key', ('key', 0, 'recoil')], 12, 0), ('aim', ['key'], 1, -1), ('hit', [('key', 0, 'flash')], 12, 0)]),
    'toxic': ((64, 48), [('move', ['walk1', ('walk1', 1), 'walk2', ('walk2', 1)], 7, -1), ('attack', ['key', ('key', 0, 'recoil')], 12, -1), ('aim', ['key'], 1, -1), ('hit', [('key', 0, 'flash')], 12, 0)]),
    'clawbot': ((58, 54), [('move', ['key', ('key', 1), 'key', ('key', -1)], 6, -1), ('attack', ['grab'], 1, -1), ('open', ['key'], 1, -1), ('hit', [('key', 0, 'flash')], 12, 0)]),
    'xeno': ((76, 52), [('move', ['run', ('run', 1), 'run', ('run', 2)], 12, -1), ('crouch', ['key'], 1, -1), ('attack', ['leap'], 1, -1), ('hit', [('key', 0, 'flash')], 12, 0)]),
    'mutant': ((66, 64), [('move', ['walk1', 'key', 'walk2', 'key'], 5, -1), ('attack', ['slash'], 1, -1), ('hit', [('key', 0, 'flash')], 12, 0)]),
    'walker': ((84, 72), [('move', ['walk1', 'key', 'walk2', 'key'], 5, -1), ('charge', ['key', ('key', 0, 'glow')], 10, -1), ('fire', [('key', 0, 'glow')], 1, -1), ('hit', [('key', 0, 'flash')], 12, 0)]),
}

def recoil(f):
    o = np.full_like(f, -1); o[:, 1:] = f[:, :-1]    # facing left: the whole kicks back 1px to the right
    return o

def glow(f, pal):
    # brighten cyan-ish colours (the cannon muzzle / jar) for the charge frame
    g = f.copy(); p2 = pal.copy()
    return g

if __name__ == '__main__':
    os.makedirs(OUTD, exist_ok=True)
    assets, anims, showcase = [], [], []
    for name, ((cw, ch), spec) in ANIM_SPEC.items():
        frames, pal, OL = build_unit(name)
        if name in ('xeno', 'mutant'):   # lift the dark aliens off the dark lab backdrop (keep the outline)
            p2 = pal.astype(int)
            for i in range(len(p2) - 1):
                if i != OL: p2[i] = np.clip(p2[i] * 1.22 + 14, 0, 255)
            pal = p2.astype(np.uint8)
        np.save(f'art/raw/roster3/{name}_frames.npy', frames, allow_pickle=True)
        seq, idxmap = [], {}
        pal_glow = pal.copy()
        if name == 'walker':
            hsv = [(i, c) for i, c in enumerate(pal[:-1]) if c[2] > c[0] + 40 and c[1] > c[0] + 20]
            for i, c in hsv: pal_glow[i] = np.clip(c.astype(int) + 70, 0, 255)
        for (an, lst, fps, rep) in spec:
            ids = []
            for it in lst:
                if isinstance(it, str): it = (it, 0)
                fn, dy = it[0], it[1]; mod = it[2] if len(it) > 2 else None
                f = frames[fn]
                if mod == 'recoil': f = recoil(f)
                seq.append((f, dy, mod == 'flash', mod == 'glow'))
                ids.append(len(seq) - 1)
            anims.append({'key': f'{name}-{an}', 'texture': f'r3-{name}', 'frames': ids, 'frameRate': fps, 'repeat': rep})
        cells = []
        for (f, dy, fl, gl) in seq:
            img, _ = pack(name, [(f, dy, fl)], pal_glow if gl else pal, OL, cw, ch, anchor='center' if name == 'clawbot' else 'feet')
            cells.append(np.array(img))
        sheet = Image.fromarray(np.concatenate(cells, 1), 'RGBA'); sheet.save(f'{OUTD}/{name}.png')
        assets.append({'type': 'spritesheet', 'key': f'r3-{name}', 'url': f'{OUTD}/{name}.png', 'frameWidth': cw, 'frameHeight': ch})
        showcase.append((name, cells))
    for key, (a, fw, fh) in fx_sheets().items():
        Image.fromarray(a, 'RGBA').save(f'{OUTD}/{key}.png')
        assets.append({'type': 'spritesheet', 'key': key, 'url': f'{OUTD}/{key}.png', 'frameWidth': fw, 'frameHeight': fh})
        n = a.shape[1] // fw
        if n > 1: anims.append({'key': key + '-a', 'texture': key, 'frames': list(range(n)), 'frameRate': 14 if 'goo' in key else 12, 'repeat': 0 if 'goo' in key else -1})
    json.dump({'assets': assets, 'anims': anims}, open('assets/parts/roster3.json', 'w'), indent=1)
    # showcase at 4x: one row per unit
    S = 4; rows = []
    W = max(sum(c.shape[1] for c in cells) for _, cells in showcase) + 90
    H = sum(cells[0].shape[0] + 6 for _, cells in showcase)
    sc = Image.new('RGBA', (W, H), (34, 42, 52, 255)); d = ImageDraw.Draw(sc); y = 0
    for name, cells in showcase:
        d.text((4, y + 4), name, fill=(230, 230, 230, 255)); x = 90
        for c in cells:
            im = Image.fromarray(c, 'RGBA'); bg = Image.new('RGBA', im.size, (46, 58, 70, 255) if (x // 10) % 2 else (40, 52, 64, 255)); bg.alpha_composite(im)
            sc.paste(bg, (x, y)); x += c.shape[1]
        y += cells[0].shape[0] + 6
    sc = sc.resize((sc.width * S, sc.height * S), Image.NEAREST); os.makedirs('shots', exist_ok=True); sc.save('shots/roster3_showcase.png')
    print('ok', [a['key'] for a in anims])
