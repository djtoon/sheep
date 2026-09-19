"""Armed and Fluffy - FX sheet builder.
Hand-built pixel FX at game scale (1 px = 1 game px), palette-locked to the fire colours sampled from the
ref mockups (c0f6 / fd55) and styled after the gen.mjs studies in art/raw/fx/gen_*.png.
Run from repo root:  python art/raw/fx/build_fx.py   -> assets/fx/*.png + shots/fx_showcase.png
"""
import math, os, random, json
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
OUT = os.path.join(ROOT, 'assets', 'fx')
os.makedirs(OUT, exist_ok=True)

def hx(s): s = s.lstrip('#'); return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4)) + (255,)

# ---- palettes (sampled from the mockups' muzzle flashes / explosion) ----
W, CR, Y, O, R1, R2, DR, DK = [hx(c) for c in ('fffcee', 'fdf1b4', 'fcd437', 'fb9309', 'f34b05', 'c9340e', '9c1a10', '4a1614')]
FIRE = [W, CR, Y, O, R1, R2, DR]
SMK = [hx(c) for c in ('8f8a86', '6c6666', '4d4749', '353033', '231e22')]          # light -> dark smoke
DUST = [hx(c) for c in ('e6d2a4', 'c4a676', '957a55', '66513b')]
CYAN = [hx(c) for c in ('ffffff', 'd4fbff', '7fe6ff', '2fb4f0', '1c6cc8', '17307a')]
PINK = [hx(c) for c in ('ffffff', 'ffc6e2', 'ff4c9e', 'd41468', '7a0636', '2a0414')]
BRASS = [hx(c) for c in ('fff0a0', 'e0b040', '9a6a1c', '4a3010')]
METAL = [hx(c) for c in ('c8ccd0', '8a9098', '575c64', '2c2f35')]
ROCK = [hx(c) for c in ('a08a66', '74603f', '4c3d28', '2a2118')]
CLEAR = (0, 0, 0, 0)

def canvas(w, h): return np.zeros((h, w, 4), np.uint8)
def put(a, x, y, c):
    if 0 <= x < a.shape[1] and 0 <= y < a.shape[0]: a[y, x] = c

def vnoise(seed):
    rnd = random.Random(seed); ph = [rnd.uniform(0, 6.283) for _ in range(6)]
    def f(t, k=1.0):
        return (math.sin(t * 3 * k + ph[0]) * .5 + math.sin(t * 5 * k + ph[1]) * .3 + math.sin(t * 9 * k + ph[2]) * .2)
    return f

def outline(a, col, only_fire=False):
    """1px outline around opaque pixels (4-neighbour)."""
    al = a[..., 3] > 0
    n = np.zeros_like(al)
    n[1:] |= al[:-1]; n[:-1] |= al[1:]; n[:, 1:] |= al[:, :-1]; n[:, :-1] |= al[:, 1:]
    edge = n & ~al
    a[edge] = col
    return a

def rim(a, col, match=None):
    """Recolour the outermost opaque pixels (inside edge)."""
    al = a[..., 3] > 0
    inner = al.copy()
    inner[1:] &= al[:-1]; inner[:-1] &= al[1:]; inner[:, 1:] &= al[:, :-1]; inner[:, :-1] &= al[:, 1:]
    e = al & ~inner
    a[e] = col
    return a

def sheet(frames, cols=None):
    """frames: list of rows (list of arrays, equal size) -> grid image"""
    rows = frames if isinstance(frames[0], list) else [frames]
    h, w = rows[0][0].shape[:2]
    n = max(len(r) for r in rows)
    out = canvas(w * n, h * len(rows))
    for j, r in enumerate(rows):
        for i, f in enumerate(r): out[j * h:(j + 1) * h, i * w:(i + 1) * w] = f
    return out

def save(a, name):
    Image.fromarray(a, 'RGBA').save(os.path.join(OUT, name + '.png'))
    return a

# ------------------------------------------------------------------ star (muzzle flashes, hit sparks)
def star(w, h, cx, cy, base, spikes, pal, bands=(0.28, 0.44, 0.6, 0.74, 0.86, 1.0), seed=0, rough=0.0, holes=0.0):
    """spikes: list of (angle_rad, length, sharpness). Pixel is inside if d < R(theta).
    Colour by t = d/R (core -> rim) using pal/bands."""
    a = canvas(w, h); nz = vnoise(seed); rnd = random.Random(seed * 7 + 1)
    for y in range(h):
        for x in range(w):
            dx, dy = x + .5 - cx, y + .5 - cy
            d = math.hypot(dx, dy); th = math.atan2(dy, dx)
            R = base * (1 + rough * nz(th, 1.3))
            for (ang, L, p) in spikes:
                dth = abs((th - ang + math.pi) % (2 * math.pi) - math.pi)
                wdt = 1.6 / math.sqrt(p)
                if dth < wdt: R += L * (1 - dth / wdt) ** 1.4
            if R <= 0: continue
            t = d / R
            if t >= 1: continue
            if holes and t > 0.55 and rnd.random() < holes: continue
            for b, col in zip(bands, pal):
                if t < b: a[y, x] = col; break
    return a

def muzzle_set(w, h, ox, oy, fwd, kind='fire', seed=1, k=1.0):
    """4-frame flash with its base at (ox,oy), pointing along angle fwd."""
    f = fwd; P = math.pi
    pal = FIRE if kind != 'laser' else CYAN
    out = []
    if kind in ('fire', 'fireB', 'spread'):
        rot = 0.0 if kind != 'fireB' else 0.22
        big = [(f, 20, 12), (f + 0.42, 9, 20), (f - 0.42, 9, 20), (f + P / 4 + 0.35, 9, 16), (f - P / 4 - 0.35, 9, 16),
               (f + P / 2 + 0.3, 6, 18), (f - P / 2 - 0.3, 6, 18), (f + 3 * P / 4, 3, 14), (f - 3 * P / 4, 3, 14)]
        if kind == 'fireB':
            big = [(f, 19, 14), (f + 0.62, 10, 14), (f - 0.62, 10, 14), (f + 1.25, 7, 16), (f - 1.25, 7, 16), (f + 1.9, 4, 16), (f - 1.9, 4, 16), (f + P, 2, 8)]
        if kind == 'spread':
            big = [(f, 12, 10), (f + 0.36, 13, 26), (f - 0.36, 13, 26), (f + 0.75, 9, 20), (f - 0.75, 9, 20), (f + P / 2, 5, 14), (f - P / 2, 5, 14)]
        big = [(a_, L * k, p) for (a_, L, p) in big]
        cx, cy = ox + math.cos(f) * 5 * k, oy + math.sin(f) * 5 * k
        out.append(star(w, h, cx, cy, 6.0 * k, big, FIRE, bands=(0.4, 0.55, 0.68, 0.8, 0.9, 1.0), seed=seed, rough=0.12))
        mid = [(a_, L * 0.78, p) for (a_, L, p) in big]
        out.append(star(w, h, cx + math.cos(f), cy + math.sin(f), 5.0 * k, [(a_ + 0.12, L, p) for a_, L, p in mid], FIRE[1:], seed=seed + 1, rough=0.2))
        sm = [(a_, L * 0.4, p) for (a_, L, p) in big]
        out.append(star(w, h, cx + 2 * math.cos(f), cy + 2 * math.sin(f), 3.4 * k, sm, [Y, O, R1, R2, DR], bands=(0.3, 0.55, 0.75, 0.9, 1.0), seed=seed + 2, rough=0.35, holes=0.15))
        # fading puff: smoke + ember
        p = star(w, h, cx + 3 * math.cos(f), cy + 3 * math.sin(f) - 1, 2.8 * k, [(f, 2, 4)], [O, SMK[2], SMK[3]], bands=(0.25, 0.7, 1.0), seed=seed + 3, rough=0.4)
        out.append(p)
    elif kind == 'laser':
        cx, cy = ox + math.cos(f) * 4, oy + math.sin(f) * 4
        spikes = [(f, 10 * k, 30), (f + P / 2, 7 * k, 60), (f - P / 2, 7 * k, 60), (f + P, 2, 30)]
        out.append(star(w, h, cx, cy, 3.8, spikes, CYAN, bands=(0.3, 0.45, 0.62, 0.8, 0.92, 1.0), seed=seed))
        out.append(star(w, h, cx, cy, 4.8, [(a_, L * 1.2, p) for a_, L, p in spikes], CYAN[1:], bands=(0.3, 0.55, 0.78, 0.9, 1.0), seed=seed, holes=0.0))
        # ring
        a = canvas(w, h)
        for y in range(h):
            for x in range(w):
                d = math.hypot(x + .5 - cx, y + .5 - cy)
                if 4.5 < d < 6.3: a[y, x] = CYAN[2] if d < 5.4 else CYAN[4]
                elif d < 2: a[y, x] = CYAN[1]
        out.append(a)
        a = canvas(w, h)
        for y in range(h):
            for x in range(w):
                d = math.hypot(x + .5 - cx, y + .5 - cy)
                if 6.2 < d < 7.4 and (x + y) % 2 == 0: a[y, x] = CYAN[4]
        out.append(a)
    return out

def build_muzzles():
    # horizontal (right): 32x24, base at (3,12)
    specs = {
        'muzzle': (44, 32, 3, 16, 0.0),
        'muzzle-d': (38, 38, 4, 34, -math.pi / 4),
        'muzzle-u': (32, 44, 16, 41, -math.pi / 2),
    }
    meta = {}
    for key, (w, h, ox, oy, f) in specs.items():
        rows = [muzzle_set(w, h, ox, oy, f, kd, seed=s, k=1.35) for kd, s in (('fire', 3), ('fireB', 11), ('spread', 17), ('laser', 23))]
        for r_ in rows[:3]:
            for fr_ in r_[:2]: outline(fr_, DK)
        save(sheet(rows), key); meta[key] = (w, h, ox, oy)
    # enemy/small horizontal: 20x14, base (2,7)
    w, h = 20, 14
    f = 0.0; cx, cy = 5, 7
    fr = [star(w, h, cx, cy, 3.4, [(0, 12, 16), (0.8, 4, 10), (-0.8, 4, 10), (1.57, 3, 14), (-1.57, 3, 14)], FIRE, seed=5, rough=0.1),
          star(w, h, cx + 1, cy, 2.9, [(0.1, 8, 14), (0.9, 3, 10), (-0.7, 3, 10)], FIRE[1:], seed=6, rough=0.2),
          star(w, h, cx + 2, cy, 2.4, [(0, 3, 6)], [Y, O, R1, DR], bands=(0.35, 0.6, 0.85, 1.0), seed=7, rough=0.3, holes=0.15),
          star(w, h, cx + 3, cy - 1, 2.0, [], [O, SMK[2], SMK[3]], bands=(0.2, 0.7, 1.0), seed=8, rough=0.4)]
    save(sheet(fr), 'muzzle-sm'); meta['muzzle-sm'] = (w, h, 2, 7)
    return meta

# ------------------------------------------------------------------ bullets
def capsule(w, h, L, T, pal, cx=None, cy=None, ang=0.0, tail=0, tailpal=None):
    """Draw a rounded capsule of length L, thickness T along angle ang, centred; colour by distance from axis.
    pal: [core, inner, mid, rim] ; tail: extra fading length behind (tracer)"""
    a = canvas(w, h)
    cx = w / 2 if cx is None else cx; cy = h / 2 if cy is None else cy
    ux, uy = math.cos(ang), math.sin(ang)
    for y in range(h):
        for x in range(w):
            px, py = x + .5 - cx, y + .5 - cy
            s = px * ux + py * uy; n = -px * uy + py * ux
            hl = L / 2 - T / 2
            sc = max(-hl, min(hl, s))
            d = math.hypot(s - sc, n) / (T / 2)
            if d < 1:
                k = min(len(pal) - 1, int(d * len(pal)))
                # slightly hotter toward the head
                if k > 0 and s > hl * 0.3 and d < 0.5: k -= 1
                a[y, x] = pal[k]
            elif tail and s < -hl and s > -hl - tail and abs(n) < T / 2 * (1 - (-hl - s) / tail) + 0.3:
                q = (-hl - s) / tail
                a[y, x] = tailpal[min(len(tailpal) - 1, int(q * len(tailpal)))]
    return a

def orb(w, h, r, pal, cx=None, cy=None, ring=None):
    a = canvas(w, h); cx = w / 2 if cx is None else cx; cy = h / 2 if cy is None else cy
    for y in range(h):
        for x in range(w):
            d = math.hypot(x + .5 - cx, y + .5 - cy) / r
            # light from top-left
            d2 = math.hypot(x + .5 - cx + r * 0.25, y + .5 - cy + r * 0.25) / r
            if d < 1:
                k = min(len(pal) - 1, int(min(d2, 0.999) * len(pal)))
                if d > 0.78: k = len(pal) - 1
                a[y, x] = pal[k]
            elif ring and d < ring[0]:
                a[y, x] = ring[1]
    return a

def build_bullets():
    C = 24  # cell
    dirs = [0.0, -math.pi / 4, -math.pi / 2]
    rows = []
    # R rifle: fat glowing capsule (mockup: orange capsule, white core, red rim) ~12x5
    rpal_a = [W, W, Y, O, O]
    rpal_b = [W, W, W, Y, O]
    rows.append([outline(capsule(C, C, 11, 6.0, p, ang=a, tail=5, tailpal=[O, R1, R1]), DK) for p in (rpal_a, rpal_b) for a in dirs])
    # M machine gun: thinner, longer tracer with a fading tail
    mpal = [W, CR, Y, O]
    # MG: short fat discrete slugs (two variants alternated per shot), white core, dark outline, 2px stub tail
    rows.append([outline(capsule(C, C, 10, 6.2, [W, W, Y, O], ang=a, tail=5, tailpal=[O, R1, R1]), DK) for a in dirs] +
                [outline(capsule(C, C, 9, 6.2, [W, CR, Y, O], ang=a, tail=5, tailpal=[O, R1, R1]), DK) for a in dirs])
    # S spread: red-orange fireball orbs (Contra red balls), pulse
    s_a = orb(C, C, 4.2, [W, CR, Y, O, R1, DR])
    s_b = orb(C, C, 4.8, [W, Y, O, R1, R2, DR], ring=(1.25, (243, 75, 5, 255)))
    rows.append([s_a, s_a, s_a, s_b, s_b, s_b])
    # L laser: long cyan beam with white core
    lpal = [W, W, CYAN[1], CYAN[2], CYAN[3], CYAN[4]]
    rows.append([capsule(C, C, 22, 5.0, lpal, ang=a) for a in dirs] + [capsule(C, C, 22, 4.2, [W, CYAN[1], CYAN[2], CYAN[3], CYAN[4]], ang=a) for a in dirs])
    # E enemy: hot-pink orb, dark outline, 2-frame pulse -> readable on green + blue
    e_a = orb(C, C, 3.6, [W, PINK[1], PINK[2], PINK[3], PINK[4]]); outline(e_a, PINK[5])
    e_b = orb(C, C, 3.6, [W, W, PINK[1], PINK[2], PINK[3]]); outline(e_b, PINK[4]); outline(e_b, (42, 4, 20, 255))
    rows.append([e_a, e_a, e_a, e_b, e_b, e_b])
    save(sheet(rows), 'fxb')
    # enemy bolts: strict 3-colour pixel slugs (white core, hot pink, near-black outline) at 16 angles.
    # Built by stamping integer pixel discs along a Bresenham line -> clean stair-steps, no in-between tones.
    # Tail = 2 separate stepped blocks behind the slug (no taper ramp).
    def bres(x0, y0, x1, y1):
        pts = []; dx, dy = abs(x1 - x0), -abs(y1 - y0); sx = 1 if x0 < x1 else -1; sy = 1 if y0 < y1 else -1; e = dx + dy
        while True:
            pts.append((x0, y0))
            if x0 == x1 and y0 == y1: break
            e2 = 2 * e
            if e2 >= dy: e += dy; x0 += sx
            if e2 <= dx: e += dx; y0 += sy
        return pts
    def disc(r): return [(dx, dy) for dy in range(-3, 4) for dx in range(-3, 4) if dx * dx + dy * dy <= r * r]
    # enemy ball-tracers (round 11): round red-orange head, white-yellow core, dark-red rim + outline,
    # short streak with 2 fading hard steps behind. Redder and rounder than the player's yellow slugs.
    HEAD, CORE2, STREAK = disc(3.2), disc(1.6), disc(1.6)
    eb = []; E = 40; INK = DK
    for shim in (0, 1):
        row = []
        for i in range(16):
            ang = i * math.pi / 8; ux, uy = math.cos(ang), math.sin(ang)
            c0 = E // 2
            hx_, hy_ = c0 + round(ux * 4), c0 + round(uy * 4)
            a_ = canvas(E, E)
            # streak: short tapered segment behind the head (2 fading hard steps)
            for dist, col, disc_ in ((4, R2, STREAK), (7, DR, disc(1.0))):
                for (x, y) in bres(hx_, hy_, hx_ - round(ux * dist), hy_ - round(uy * dist)):
                    for dx, dy in disc_:
                        if a_[y + dy, x + dx, 3] == 0: put(a_, x + dx, y + dy, col)
            for dx, dy in HEAD: put(a_, hx_ + dx, hy_ + dy, R1)
            core = CORE2 if not shim else disc(2.0)
            for dx, dy in core: put(a_, hx_ + dx + (1 if ux > 0.3 else -1 if ux < -0.3 else 0) * 0, hy_ + dy, Y if (dx * dx + dy * dy) > 1 else W)
            outline(a_, INK)
            # 2 detached fading pixels behind the streak
            for dist, col, sz in ((11, R2, 2), (14, DR, 1)):
                bx, by = hx_ - round(ux * dist), hy_ - round(uy * dist)
                for oy in range(sz):
                    for ox in range(sz): put(a_, bx + ox - sz // 2, by + oy - sz // 2, col)
            row.append(a_)
        eb.append(row)
    save(sheet(eb), 'ebolt')
    # contract textures (fallback / first frame), trimmed to the small sizes the physics expects
    def crop(a, w, h):
        y0 = (a.shape[0] - h) // 2; x0 = (a.shape[1] - w) // 2
        return a[y0:y0 + h, x0:x0 + w]
    save(crop(rows[0][0], 14, 6), 'bullet-player')
    save(crop(rows[2][0], 10, 10), 'bullet-spread')
    save(crop(rows[3][0], 22, 6), 'bullet-laser')
    save(crop(rows[4][0], 6, 6), 'bullet-enemy')
    return rows

# ------------------------------------------------------------------ impacts
def build_hits():
    # 24px cell, 4 frames: big hard 4+4 point star (~20px) -> 8-point star -> broken ring -> specks
    S = 24; c = 12
    rows = []
    for pal in (FIRE, CYAN, PINK):
        fr = []; dk = pal[-1]
        f0 = star(S, S, c, c, 3.6, [(k * math.pi / 2, 8.0, 10) for k in range(4)] + [(k * math.pi / 2 + math.pi / 4, 3.2, 14) for k in range(4)],
                  [pal[0], pal[0], pal[2], pal[3]], bands=(0.35, 0.55, 0.78, 1.0))
        fr.append(outline(f0, dk))
        f1 = star(S, S, c, c, 4.4, [(k * math.pi / 4 + 0.39, 4.6, 12) for k in range(8)], [pal[0], pal[2], pal[3]],
                  bands=(0.35, 0.7, 1.0), seed=4)
        fr.append(outline(f1, dk))
        a = star(S, S, c, c, 8.2, [(k * math.pi / 4, 2, 10) for k in range(8)], [pal[2], pal[3], pal[4]], bands=(0.6, 0.82, 1.0), seed=5, rough=0.15)
        a[star(S, S, c, c, 6.2, [], [W], bands=(1.0,))[..., 3] > 0] = 0
        for k in range(8):   # break the ring into chunks
            ang = k * math.pi / 4 + math.pi / 8
            for r in range(5, 11): put(a, int(round(c + math.cos(ang) * r)), int(round(c + math.sin(ang) * r)), CLEAR)
        fr.append(a)
        a = canvas(S, S)
        for k in range(8):
            ang = k * math.pi / 4 + 0.2; r = 9.5
            x, y = int(round(c + math.cos(ang) * r)), int(round(c + math.sin(ang) * r))
            put(a, x, y, pal[3]); put(a, x + 1, y, pal[4] if k % 2 else pal[3])
        fr.append(a)
        rows.append(fr)
    save(sheet(rows), 'hit')
    # kill flash 56px, 2 frames: native-res white-hot 4+4 point star for big kills (never upscaled)
    S = 56; c = 28; kf = []
    for k_, base in ((1.0, 7.0), (0.75, 9.0)):
        f_ = star(S, S, c, c, base, [(q * math.pi / 2, 19 * k_, 10) for q in range(4)] + [(q * math.pi / 2 + math.pi / 4, 8 * k_, 14) for q in range(4)],
                  [W, W, CR, Y, O], bands=(0.3, 0.45, 0.62, 0.82, 1.0))
        kf.append(outline(f_, DR))
    save(sheet(kf), 'killflash')
    # terrain hit: spark + dirt kick (base at bottom-centre)
    S2 = 20
    fr = []
    rnd = random.Random(9)
    for i in range(6):
        a = canvas(S2, S2)
        if i < 2:
            sp = star(S2, S2, 10, 16, 2 + i, [(-math.pi / 2, 5 + 2 * i, 14), (-math.pi / 4 - 0.3, 3, 14), (-3 * math.pi / 4 + 0.3, 3, 14)], [W, Y, O, R1], bands=(0.3, 0.55, 0.8, 1.0))
            a = sp
        # dirt clods puff
        for (px, py, r) in [(10, 17 - i * 1.6, 2.4 + i * 0.7), (7 - i * 0.6, 17 - i * 0.8, 1.8 + i * 0.5), (13 + i * 0.6, 17 - i, 1.8 + i * 0.5)]:
            if i >= 5 and r > 3: r -= 1
            for y in range(S2):
                for x in range(S2):
                    d = math.hypot(x + .5 - px, y + .5 - py) / r
                    if d < 1 and (i < 4 or (x + y + i) % 3):
                        k = 1 if d < 0.5 and y < py else 2 if d < 0.8 else 3
                        if a[y, x, 3] == 0 or i >= 2: a[y, x] = DUST[k - (1 if i < 2 else 0)]
        # clods flying
        for k in range(3):
            ang = -math.pi / 2 + (k - 1) * 0.8
            r = 4 + i * 2.2
            x = int(10 + math.cos(ang) * r); y = int(16 + math.sin(ang) * r + i * i * 0.35)
            if i < 5: put(a, x, y, ROCK[2]); put(a, x + 1, y, ROCK[3])
        fr.append(a)
    save(sheet(fr), 'hit-dirt')

# ------------------------------------------------------------------ explosions
def explosion(S, N, seed, big=False):
    rnd = random.Random(seed)
    c = S / 2; frames = []
    nb = 7 if S < 40 else 9 if S < 60 else 12
    blobs = []
    for i in range(nb):
        ang = i / nb * 6.283 + rnd.uniform(-0.3, 0.3)
        dist = rnd.uniform(0.35, 0.8) if i else 0
        blobs.append(dict(ang=ang, dist=dist, r=rnd.uniform(0.55, 0.85), rise=rnd.uniform(0.6, 1.3), cool=rnd.uniform(0.8, 1.25),
                          ph=rnd.uniform(0, 6.28)))
    embers = [(rnd.uniform(0, 6.283), rnd.uniform(0.5, 1.0), rnd.random()) for _ in range(10 + S // 6)]
    nz = vnoise(seed)
    Rmax = S * 0.33
    for f in range(N):
        t = f / (N - 1)
        a = canvas(S, S)
        if t < 0.2:
            # flash -> spiky star
            k = t / 0.2
            base = Rmax * (0.25 + 0.55 * k)
            sp = [(i * math.pi / 4 + (0.39 if f % 2 else 0), base * (0.55 - 0.2 * k), 6 + 8 * k) for i in range(8)]
            pal = [W, CR, Y, O, R1, DR] if f == 0 else [W, CR, Y, O, R1, DR]
            a = star(S, S, c, c, base, sp, pal, bands=((0.45, 0.6, 0.74, 0.86, 0.94, 1.0) if f == 0 else (0.3, 0.45, 0.62, 0.78, 0.9, 1.0)), seed=seed + f, rough=0.15)
            frames.append(a); continue
        # blob phase
        k = (t - 0.2) / 0.8                                 # 0..1
        grow = min(1.0, 0.8 + k * 0.9)
        best = np.zeros((S, S)); heat = np.zeros((S, S)); second = np.zeros((S, S)); shade = np.zeros((S, S))
        for b in blobs:
            spread = Rmax * b['dist'] * (0.75 + 0.55 * min(1, k * 1.6))
            bx = c + math.cos(b['ang']) * spread
            by = c + S * 0.06 + math.sin(b['ang']) * spread * 0.8 - (k ** 1.4) * S * 0.2 * b['rise']
            br = Rmax * b['r'] * grow * (1.0 if k < 0.55 else max(0.0, 1 - (k - 0.55) * 1.7 * b['cool']))
            if br < 1.2: continue
            h = max(0.0, 1.0 - k * 1.55 * b['cool'])        # blob heat
            for y in range(S):
                for x in range(S):
                    dx, dy = x + .5 - bx, y + .5 - by
                    th = math.atan2(dy, dx)
                    rr = br * (1 + 0.13 * nz(th + b['ph'], 1.0) + (0.22 * max(0.0, 1 - k * 3.5)) * (abs(math.cos(th * 4 + b['ph'])) ** 6))
                    v = 1 - math.hypot(dx, dy) / rr
                    if v <= 0: continue
                    if v > best[y, x]:
                        second[y, x] = best[y, x]; best[y, x] = v; heat[y, x] = h
                        shade[y, x] = v + 0.35 * (-dx - dy) / rr
                    elif v > second[y, x]: second[y, x] = v
        for y in range(S):
            for x in range(S):
                v = best[y, x]
                if v <= 0: continue
                if k > 0.7 and ((x * 7 + y * 13 + f * 5) % 11) / 11 < (k - 0.7) * 2.4 and v < 0.45: continue  # dissipating holes
                lh = heat[y, x] * (0.3 + 0.78 * v)
                if lh > 0.96: col = W
                elif lh > 0.86: col = CR
                elif lh > 0.66: col = Y
                elif lh > 0.52: col = O
                elif lh > 0.4: col = R1
                elif lh > 0.3: col = R2
                elif lh > 0.22: col = DR
                elif lh > 0.14: col = DK
                else:
                    s_ = shade[y, x]
                    col = SMK[0] if s_ > 0.75 else SMK[1] if s_ > 0.45 else SMK[2] if s_ > 0.18 else SMK[3]
                # seam between smoke balls
                if lh <= 0.3 and second[y, x] > 0 and best[y, x] - second[y, x] < 0.07: col = SMK[4]
                a[y, x] = col
        # rim: fire edges dark red, smoke edges dark
        al = a[..., 3] > 0
        inner = al.copy(); inner[1:] &= al[:-1]; inner[:-1] &= al[1:]; inner[:, 1:] &= al[:, :-1]; inner[:, :-1] &= al[:, 1:]
        edge = al & ~inner
        for y, x in zip(*np.nonzero(edge)):
            col = tuple(a[y, x])
            a[y, x] = DR if col in (W, CR, Y, O, R1) else SMK[4] if col in SMK else DK
        # embers
        if k > 0.1:
            for (ang, rr, ph) in embers:
                if (ph + k) % 1 > 0.75 and k > 0.6: continue
                d = Rmax * (0.9 + rr * 0.6 * k + 0.25)
                x = int(c + math.cos(ang) * d); y = int(c + math.sin(ang) * d * 0.9 - k * S * 0.1 + k * k * S * 0.12)
                colr = Y if k < 0.35 else O if k < 0.65 else R1
                if 0 <= x < S and 0 <= y < S and a[y, x, 3] == 0:
                    put(a, x, y, colr)
                    if k < 0.4 and big: put(a, x + 1, y, O)
        frames.append(a)
    return frames

def _smoothstep(a, b, x): x = min(1.0, max(0.0, (x - a) / (b - a))); return x * x * (3 - 2 * x)

def explosion2(S, N, seed, big=False):
    """Metal Slug / mockup blast: spiky starburst with a white-yellow hot core, orange body, dark-red stepped rim,
    flying spark shards; holds hot for ~half the anim, then breaks into round 4-tone grey smoke puffs + embers."""
    rnd = random.Random(seed)
    c = (S - 1) / 2.0
    Y_, X_ = np.mgrid[0:S, 0:S].astype(float)
    DX, DY = X_ - c, Y_ - c
    D = np.hypot(DX, DY); TH = np.arctan2(DY, DX)
    Rmax = S * 0.31
    K = 11 if S >= 48 else 9
    spikes = [(i / K * 2 * math.pi + rnd.uniform(-0.18, 0.18), rnd.uniform(0.55, 1.0), rnd.uniform(0.22, 0.34)) for i in range(K)]
    prof = np.zeros((S, S))
    for ang, ln, w in spikes:
        dth = np.abs((TH - ang + math.pi) % (2 * math.pi) - math.pi)
        prof = np.maximum(prof, ln * np.clip(1 - dth / w, 0, 1) ** 1.3)
    nz = vnoise(seed); NZ = np.vectorize(lambda t: nz(t, 1.6))(TH)
    lumps = [(rnd.uniform(-0.55, 0.55), rnd.uniform(-0.55, 0.45), rnd.uniform(0.22, 0.4)) for _ in range(6 + S // 16)]
    LUMP = np.zeros((S, S))
    for lx, ly, lr in lumps:
        LUMP = np.maximum(LUMP, np.clip(1 - np.hypot(DX - lx * Rmax, DY - ly * Rmax) / (lr * Rmax), 0, 1))
    shards = [(rnd.uniform(0, 2 * math.pi), rnd.uniform(0.8, 1.2), rnd.choice((3, 4, 4, 5))) for _ in range(7 if S < 48 else 10)]
    puffs = []
    for i in range(5 if S < 40 else 7 if S < 60 else 10):
        ang = rnd.uniform(math.pi * 0.95, math.pi * 2.05)  # mostly upper half
        puffs.append(dict(x=math.cos(ang) * rnd.uniform(0.1, 0.65), y=math.sin(ang) * rnd.uniform(0.1, 0.55) + 0.15,
                          r=rnd.uniform(0.3, 0.46), t0=rnd.uniform(0.34, 0.55), rise=rnd.uniform(0.25, 0.45)))
    embers = [(rnd.uniform(0, 2 * math.pi), rnd.uniform(0.9, 1.4)) for _ in range(8 + S // 8)]
    frames = []
    for f in range(N):
        t = f / (N - 1)
        a = canvas(S, S)
        # ---------- fire body
        grow = 0.34 + 0.66 * _smoothstep(0.0, 0.28, t) + 0.08 * _smoothstep(0.28, 0.55, t)
        shrink = 1 - _smoothstep(0.5, 0.84, t)
        R0 = Rmax * grow * shrink * (1 - 0.3 * _smoothstep(0.5, 0.84, t))
        spik = 0.55 * (1 - 0.6 * _smoothstep(0.3, 0.7, t))
        R = R0 * (0.72 + spik * prof + 0.07 * NZ)
        cool = 0.9 * _smoothstep(0.4, 0.84, t)
        H = 1 - D / np.maximum(R, 0.1) + 0.28 * LUMP * (1 - 0.5 * cool) - cool
        inside = D < R
        if R0 > 2.0:
            cols = [(0.72, W), (0.58, CR), (0.44, Y), (0.3, O), (0.17, R1), (0.06, R2), (-0.25, DR), (-9, DK)]
            if t < 0.08: cols = [(0.5, W), (0.3, CR), (0.12, Y), (-9, O)]
            for y, x in zip(*np.nonzero(inside)):
                h = H[y, x]
                for th_, col in cols:
                    if h > th_: a[y, x] = col; break
            # stepped rim: outermost pixels dark red (hot phase) / near-black red (cooling)
            al = a[..., 3] > 0
            inner = al.copy(); inner[1:] &= al[:-1]; inner[:-1] &= al[1:]; inner[:, 1:] &= al[:, :-1]; inner[:, :-1] &= al[:, 1:]
            a[al & ~inner] = DR if t < 0.5 else DK
        # ---------- smoke puffs (behind hot fire, rise and break up)
        sm = canvas(S, S)
        for p_ in puffs:
            age = (t - p_['t0']) / (1 - p_['t0'] + 1e-6)
            if age < 0: continue
            px = c + p_['x'] * Rmax * (1 + 0.3 * age)
            py = c + p_['y'] * Rmax - age * p_['rise'] * S
            pr = Rmax * p_['r'] * (0.7 + 0.6 * min(1, age * 2)) * (1 - 0.55 * _smoothstep(0.6, 1.0, age))
            if pr < 1.3: continue
            dd = np.hypot(X_ - px, Y_ - py) / pr
            m = dd < 1
            shade = 0.75 * (1 - dd) + 0.8 * (-(X_ - px) - (Y_ - py)) / pr / 1.41 + 0.12
            brk = ((X_ * 7 + Y_ * 13 + f * 3) % 9) / 9 < _smoothstep(0.45, 1.0, age) * 0.9
            m &= ~((dd > 0.62) & brk)
            m &= ~((dd > 0.3) & brk & (age > 0.8))
            for y, x in zip(*np.nonzero(m)):
                sh = shade[y, x]
                col = SMK[0] if sh > 0.72 else SMK[1] if sh > 0.42 else SMK[2] if sh > 0.14 else SMK[3]
                if age < 0.3 and sh < 0.3: col = R2 if sh > 0.05 else DR   # fire-lit underside early
                sm[y, x] = col
            # dark rim on each puff edge
            edge = m & (dd > 0.82)
            sm[edge & (sm[..., 3] > 0)] = SMK[4]
        # composite: fire over smoke while hot, smoke over fire once cooling
        fa = a[..., 3] > 0; sa = sm[..., 3] > 0
        if t < 0.62: a[sa & ~fa] = sm[sa & ~fa]
        else:
            keep_fire_core = fa & np.isin(a[..., 0], [W[0], CR[0], Y[0], O[0]]) & (a[..., 1] > 120)
            a[sa & ~keep_fire_core] = sm[sa & ~keep_fire_core]
        # ---------- spark shards (hard streaks flying out)
        if 0.06 <= t <= 0.55:
            k = (t - 0.06) / 0.49
            for ang, spd, ln in shards:
                d0 = min(S / 2 - 1.5, Rmax * (0.85 + 1.0 * k * spd))
                ux, uy = math.cos(ang), math.sin(ang)
                L = max(2, int(round(ln * (1 - 0.5 * k))))
                for j in range(L):
                    x = int(round(c + ux * (d0 - j))); y = int(round(c + uy * (d0 - j) + k * k * 2))
                    col = W if j == 0 and k < 0.4 else Y if j <= 1 else O if j <= 2 else R1
                    if 0 <= x < S and 0 <= y < S and (a[y, x, 3] == 0 or j == 0): a[y, x] = col
        # ---------- embers late
        if t > 0.45:
            k = (t - 0.45) / 0.55
            for ang, rr in embers:
                d = Rmax * rr * (1 + 0.5 * k)
                x = int(round(c + math.cos(ang) * d)); y = int(round(c + math.sin(ang) * d * 0.8 - k * S * 0.12))
                if 0 <= x < S and 0 <= y < S and a[y, x, 3] == 0 and ((x + y + f) % 3):
                    put(a, x, y, Y if k < 0.3 else O if k < 0.65 else R1)
        frames.append(a)
    return frames

def quantize_blast(frames):
    # hard 3-4 colour ramp + 1px near-black rim; <= ~6 colours even in fire->smoke frames
    FIREMAP = {W: W, CR: W, Y: Y, O: O, R1: O, R2: DR, DR: DR, DK: DR}
    out = []
    for a in frames:
        a = a.copy(); px = a.reshape(-1, 4)
        cols = {tuple(p) for p in px if p[3]}
        smoky = any(c in SMK for c in cols)
        fm = dict(FIREMAP)
        if smoky: fm[W] = Y; fm[CR] = Y
        for i in range(len(px)):
            if not px[i][3]: continue
            c = tuple(px[i])
            if c in fm: px[i] = fm[c]
            elif c in SMK: px[i] = SMK[1] if SMK.index(c) <= 1 else SMK[3]
        # drop the old inner rim, then outline with near-black
        outline(a, (26, 12, 14, 255))
        out.append(a)
    return out

def build_explosions():
    save(sheet(quantize_blast(explosion2(32, 8, 21))), 'explosion-sm')
    save(sheet(quantize_blast(explosion2(48, 11, 7))), 'explosion')
    save(sheet(quantize_blast(explosion2(64, 12, 33, big=True))), 'explosion-big')

# ------------------------------------------------------------------ small particles, puffs, debris, casings
def build_particles():
    # 'px' sheet: 4x4 cells. 0 spark-plus white, 1 yellow 2x2, 2 orange 2x2, 3 orange 1px, 4 red 1px, 5 dark 1px,
    # 6 cyan plus, 7 cyan 2x2, 8 blue 1px, 9 grey 2x2, 10 grey 1px, 11 dust 2x2, 12 pink plus, 13 pink 1px
    S = 4
    def cell(pts): a = canvas(S, S); [put(a, x, y, c) for x, y, c in pts]; return a
    plus = lambda c0, c1: cell([(1, 1, c0), (2, 1, c0), (1, 2, c0), (2, 2, c0), (1, 0, c1), (0, 1, c1), (3, 2, c1), (2, 3, c1)])
    sq = lambda c0, c1: cell([(1, 1, c0), (2, 1, c1), (1, 2, c1), (2, 2, c1)])
    one = lambda c0: cell([(1, 1, c0)])
    fr = [plus(W, Y), sq(Y, O), sq(O, R1), one(O), one(R1), one(DR),
          plus(W, CYAN[2]), sq(CYAN[1], CYAN[3]), one(CYAN[4]), sq(SMK[1], SMK[2]), one(SMK[2]), sq(DUST[1], DUST[2]),
          plus(W, PINK[2]), one(PINK[3]), sq(W, CR), one(CR)]
    save(sheet(fr), 'px')
    # shards: 7x3 streaks (head at right), 3 cooling frames; rotated along velocity at runtime
    sh = []
    for cols in ((W, CR, Y, Y, O, R1), (CR, Y, O, O, R1), (Y, O, R1, R2)):
        c_ = canvas(7, 3)
        for i, col in enumerate(cols): c_[1, 6 - i] = col
        sh.append(c_)
    save(sheet(sh), 'shard')
    # rotor blade 16x4 (hub + two blades) for drone wrecks; spun at runtime
    r_ = canvas(16, 4)
    for x in range(16):
        r_[1, x] = METAL[1]; r_[2, x] = METAL[2]
    r_[1, 0:2] = METAL[3]; r_[2, 14:16] = METAL[3]
    r_[0:4, 6:10] = METAL[3]; r_[1:3, 7:9] = METAL[0]
    outline(r_, METAL[3]) if False else None
    save(r_, 'rotor')
    save(sheet([plus(W, Y)])[0:3, 0:3] if False else cell([(1, 0, Y), (0, 1, Y), (1, 1, W), (2, 1, Y), (1, 2, Y)])[0:3, 0:3], 'spark')

    # puffs: 16x16, rows: smoke(grey), dust(tan), fire-smoke (dark w/ ember core). 6 frames grow + break up
    S = 16
    rows = []
    for pal, hot in ((SMK, False), (DUST, False), (SMK, True)):
        fr = []
        for i in range(6):
            a = canvas(S, S); r = 2.6 + i * 1.0
            if i >= 4: r -= (i - 3) * 0.6
            for y in range(S):
                for x in range(S):
                    dx, dy = x + .5 - 8, y + .5 - 8
                    d = math.hypot(dx, dy * 1.1) / r
                    if d >= 1: continue
                    if i >= 3 and ((x * 5 + y * 3 + i) % 7) < (i - 2) * 1.6 and d > 0.35: continue
                    s_ = (1 - d) + 0.45 * (-dx - dy) / r
                    k = 0 if s_ > 0.8 else 1 if s_ > 0.35 else 2
                    if pal is DUST: k = min(3, k + (1 if i > 3 else 0))
                    col = pal[k + (1 if pal is SMK else 0)]
                    if hot and d < 0.45 and i < 3: col = O if i == 0 else R1 if i == 1 else DR
                    a[y, x] = col
            rim(a, pal[-1] if pal is SMK else pal[3])
            fr.append(a)
        rows.append(fr)
    save(sheet(rows), 'puff')
    # contract 'smoke' 12x12 = a mid puff
    save(rows[0][2][2:14, 2:14].copy(), 'smoke')

    # land/jump dust: 32x12, base at bottom centre (16,11); two puffs spreading out + a few pebbles
    fr = []
    for i in range(6):
        a = canvas(32, 12)
        for side in (-1, 1):
            px = 16 + side * (3 + i * 2.2); py = 9 - i * 0.5; r = 2.2 + i * 0.55
            if i >= 4: r -= (i - 3) * 0.5
            for y in range(12):
                for x in range(32):
                    dx, dy = x + .5 - px, y + .5 - py
                    d = math.hypot(dx, dy * 1.25) / r
                    if d >= 1 or y > 11: continue
                    if i >= 3 and ((x * 3 + y * 5 + i) % 5) < (i - 2) and d > 0.3: continue
                    s_ = (1 - d) + 0.4 * (-dy) / r
                    a[y, x] = DUST[0] if s_ > 0.8 else DUST[1] if s_ > 0.35 else DUST[2]
            # small trailing puff
            px2 = 16 + side * (1 + i * 1.1)
            for y in range(12):
                for x in range(32):
                    if i < 4 and math.hypot(x + .5 - px2, (y + .5 - 10.5) * 1.3) < 1.6 + i * 0.3: a[y, x] = DUST[1]
        rim(a, DUST[3])
        fr.append(a)
    save(sheet(fr), 'dust')

    # debris 6x6, 8 frames: metal shards / rock chunks / burning chunk
    S = 6
    def poly(pts, pal):
        im = Image.new('RGBA', (S, S)); d = ImageDraw.Draw(im); d.polygon(pts, fill=pal[1], outline=pal[3])
        a = np.array(im); return a
    fr = [poly([(0, 1), (4, 0), (5, 3), (2, 5)], METAL), poly([(1, 0), (5, 2), (3, 5), (0, 3)], METAL),
          poly([(0, 2), (5, 1), (4, 4)], METAL), poly([(1, 1), (4, 1), (4, 4), (1, 4)], ROCK),
          poly([(0, 1), (3, 0), (5, 4), (1, 5)], ROCK), poly([(2, 0), (5, 3), (1, 5)], ROCK)]
    for a in fr[:3]: a[1, 2] = METAL[0] if a[1, 2, 3] else a[1, 2]
    burn = poly([(0, 1), (4, 0), (5, 4), (1, 5)], [DK, DK, DK, (30, 10, 10, 255)]); burn[2, 2] = O; burn[2, 3] = Y; burn[3, 2] = R1
    fr += [burn, burn.copy()]
    fr[-1][2, 3] = O; fr[-1][3, 3] = R1
    save(sheet(fr), 'debris')

    # shell casing 5x5 cells, 4 spin frames
    S = 5
    fr = []
    for pts in ([(1, 2, 0), (2, 2, 1), (3, 2, 2)], [(1, 3, 0), (2, 2, 1), (3, 1, 2)], [(2, 1, 0), (2, 2, 1), (2, 3, 2)], [(1, 1, 0), (2, 2, 1), (3, 3, 2)]):
        a = canvas(S, S)
        for x, y, k in pts: put(a, x, y, BRASS[k])
        fr.append(a)
    save(sheet(fr), 'casing')

    # twinkle 11x11, 5 frames (pickup sparkle)
    S = 11
    fr = []
    for L, col_core in ((1, CR), (3, W), (5, W), (3, CR), (1, Y)):
        a = canvas(S, S)
        for i in range(-L, L + 1):
            c = W if abs(i) < 1 else CR if abs(i) < L * 0.5 + 1 else Y
            put(a, 5 + i, 5, c); put(a, 5, 5 + i, c)
        if L >= 3: [put(a, 5 + dx, 5 + dy, Y) for dx in (-1, 1) for dy in (-1, 1)]
        put(a, 5, 5, col_core); fr.append(a)
    save(sheet(fr), 'twinkle')
    # glint 7x7, 2 frames, 2 colours: tiny brief wind-up tell
    fr = []
    for L in (1, 2):
        a = canvas(7, 7)
        for k in range(-L, L + 1): put(a, 3 + k, 3, R1); put(a, 3, 3 + k, R1)
        put(a, 3, 3, W); fr.append(a)
    save(sheet(fr), 'glint')
    # digits 0-9: 5x7 chunky pixel font, white face + yellow lower half, 1px dark outline -> 7x9 cells
    G = ['01110 10001 10011 10101 11001 10001 01110', '00100 01100 00100 00100 00100 00100 01110', '01110 10001 00001 00110 01000 10000 11111',
         '11110 00001 00001 01110 00001 00001 11110', '00010 00110 01010 10010 11111 00010 00010', '11111 10000 11110 00001 00001 10001 01110',
         '00110 01000 10000 11110 10001 10001 01110', '11111 00001 00010 00100 01000 01000 01000', '01110 10001 10001 01110 10001 10001 01110',
         '01110 10001 10001 01111 00001 00010 01100']
    fr = []
    for g in G:
        a = canvas(7, 9)
        for y, row in enumerate(g.split()):
            for x, ch in enumerate(row):
                if ch == '1': a[y + 1, x + 1] = W if y < 3 else CR if y < 5 else Y
        outline(a, (26, 20, 32, 255)); fr.append(a)
    save(sheet(fr), 'digits')

    # ring 32x32, 5 frames (capsule pop / big hit)
    S = 32; fr = []
    for i in range(5):
        a = canvas(S, S); r = 4 + i * 3.2; th = 2.2 - i * 0.35
        for y in range(S):
            for x in range(S):
                d = math.hypot(x + .5 - 16, y + .5 - 16)
                if abs(d - r) < th / 2:
                    if i >= 3 and (x + y) % 2: continue
                    a[y, x] = W if i == 0 else CR if i == 1 else Y if i == 2 else O
        fr.append(a)
    save(sheet(fr), 'ring')

    # glow: 64x64 stepped-alpha additive disc (drawn with ADD blend, so it only brightens)
    S = 64; a = canvas(S, S)
    for y in range(S):
        for x in range(S):
            d = math.hypot(x + .5 - 32, y + .5 - 32) / 32
            if d < 1:
                lvl = 6 - min(5, int(d * 6))  # 6 soft steps, faint edge
                a[y, x] = (255, 140 + 18 * lvl, 50 + 25 * lvl, int(6 + 3.2 * lvl * lvl))
    save(a, 'glow')

# ------------------------------------------------------------------ showcase
def showcase():
    names = ['muzzle', 'muzzle-d', 'muzzle-u', 'muzzle-sm', 'fxb', 'hit', 'hit-dirt', 'explosion-sm', 'explosion', 'explosion-big',
             'puff', 'dust', 'debris', 'casing', 'twinkle', 'ring', 'px', 'glow', 'bullet-player', 'bullet-spread', 'bullet-laser', 'bullet-enemy', 'spark', 'smoke']
    Z = 4; pad = 10
    ims = [(n, Image.open(os.path.join(OUT, n + '.png')).convert('RGBA')) for n in names]
    Wd = max(im.width for _, im in ims) * Z + 2 * pad + 160
    Wd = max(Wd, 1200)
    Ht = sum(im.height * Z + pad * 2 for _, im in ims)
    bg = Image.new('RGBA', (Wd, Ht), (24, 28, 34, 255))
    d = ImageDraw.Draw(bg)
    y = 0
    for n, im in ims:
        h = im.height * Z + pad * 2
        # half jungle-green / half sky backdrop so readability is visible
        d.rectangle([160, y, Wd, y + h // 2], fill=(46, 92, 60, 255))
        d.rectangle([160, y + h // 2, Wd, y + h], fill=(70, 128, 170, 255))
        d.text((8, y + 8), f'{n}\n{im.width}x{im.height}', fill=(230, 230, 230, 255))
        big = im.resize((im.width * Z, im.height * Z), Image.NEAREST)
        bg.alpha_composite(big, (160 + pad, y + pad))
        y += h
    os.makedirs(os.path.join(ROOT, 'shots'), exist_ok=True)
    bg.convert('RGB').save(os.path.join(ROOT, 'shots', 'fx_showcase.png'))

if __name__ == '__main__':
    meta = build_muzzles()
    build_bullets(); build_hits(); build_explosions(); build_particles()
    showcase()
    print('ok', meta)
