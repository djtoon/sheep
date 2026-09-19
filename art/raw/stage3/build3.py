"""Build STAGE 03 (underground lab) art into assets/stage3/.
Run from repo root: python art/raw/stage3/build3.py
All sprites are reduced with the native-pixel reducer (mode colour per cell, small palettes, orphan cleanup),
hard alpha, 1px outlines. The play plane is composited in world space from src/level/stage3/stage3.js and cut into chunks."""
import sys, os, json, re, subprocess
sys.path.insert(0, 'art/raw/world'); sys.path.insert(0, 'art/raw/stage3')
from pxlib import *
from build import panorama, join, crop, scaled, pxpiece, haze, bgstep, bgstep8, C, draw_line, quant as _q

RAW = 'art/raw/stage3/'; OUT = 'assets/stage3/'
os.makedirs(OUT, exist_ok=True)
rng = np.random.default_rng(3)
OL = (10, 16, 20, 255)


def stage():
    src = open('src/level/stage3/stage3.js').read()
    src = re.sub(r"^import .*$", "", src, flags=re.M).replace('spawns: spawns3', 'spawns: []')
    js = src + "\nconsole.log(JSON.stringify(stage3));"
    out = subprocess.run(['node', '--input-type=module', '-e', js], capture_output=True, text=True, check=True).stdout
    return json.loads(out)


def f2u(a): return (np.clip(a, 0, 1) * 255 + .5).astype(np.uint8)


def tone(im, k=1.0, amt=0.0, col=(0, 0, 0)):
    """contrast k around the object mean, then mix amt toward col (hard per-pixel palette shift)"""
    out = im.copy(); m = im[..., 3] > 0
    if not m.any(): return out
    f = im[..., :3].astype(float); mu = f[m].mean(0)
    f = np.clip(mu + (f - mu) * k, 0, 255) * (1 - amt) + np.array(col, float) * amt
    out[..., :3] = np.clip(f + .5, 0, 255).astype(np.uint8); return out


def rect(im, x0, y0, x1, y1, c):
    H, W = im.shape[:2]
    im[max(0, y0):min(H, y1), max(0, x0):min(W, x1)] = c


# ------------------------------------------------------------------ 5x7 stencil font
FONT = {
 'A': ["01110", "10001", "10001", "11111", "10001", "10001", "10001"],
 'B': ["11110", "10001", "10001", "11110", "10001", "10001", "11110"],
 'C': ["01111", "10000", "10000", "10000", "10000", "10000", "01111"],
 'E': ["11111", "10000", "10000", "11110", "10000", "10000", "11111"],
 'L': ["10000", "10000", "10000", "10000", "10000", "10000", "11111"],
 'O': ["01110", "10001", "10001", "10001", "10001", "10001", "01110"],
 'R': ["11110", "10001", "10001", "11110", "10100", "10010", "10001"],
 'S': ["01111", "10000", "10000", "01110", "00001", "00001", "11110"],
 'T': ["11111", "00100", "00100", "00100", "00100", "00100", "00100"],
 'U': ["10001", "10001", "10001", "10001", "10001", "10001", "01110"],
 'V': ["10001", "10001", "10001", "10001", "01010", "01010", "00100"],
 '0': ["01110", "10011", "10101", "10101", "10101", "11001", "01110"],
 '3': ["11110", "00001", "00001", "01110", "00001", "00001", "11110"],
 '5': ["11111", "10000", "11110", "00001", "00001", "10001", "01110"],
 '7': ["11111", "00001", "00010", "00100", "01000", "01000", "01000"],
 '-': ["00000", "00000", "00000", "01110", "00000", "00000", "00000"],
 ' ': ["000", "000", "000", "000", "000", "000", "000"],
}


def text(im, x, y, s, c, shadow=None):
    for ch in s:
        g = FONT[ch]
        for j, row in enumerate(g):
            for i, v in enumerate(row):
                if v == '1':
                    if shadow is not None and 0 <= y + j + 1 < im.shape[0]: im[y + j + 1, x + i + 1] = shadow
                    if 0 <= y + j < im.shape[0] and 0 <= x + i < im.shape[1]: im[y + j, x + i] = c
        x += len(g[0]) + 1
    return x


def text_w(s): return sum(len(FONT[c][0]) + 1 for c in s) - 1


# ------------------------------------------------------------------ source pieces
def props():
    p = pieces(load(RAW + 'props_1.png'), 0.5, 2000)   # sorted by x: terminal, steel crate, console, lamp, strip, crates
    d = dict(terminal=p[0], crate=p[1], console=p[2], lamp=p[3], strip=p[4], crates=p[5])
    return d


def px(src, h=None, w=None, n=12, ol=True):
    H, W = src.shape[:2]
    if h and not w: w = round(W * h / H)
    if w and not h: h = round(H * w / W)
    im = pixelart(src, w, h, n)
    return outline(im, OL) if ol else im


# ------------------------------------------------------------------ parallax layers
def build_back():
    segs = [pxpiece(crop(load(RAW + f'backwall_{i}.png')), h=270, ncol=16) for i in (1, 2)]
    pano = panorama(segs, 270, 40)
    im = f2u(pano); im[..., 3] = 255
    im = tone(im, 0.8, 0.16, (6, 18, 24))                   # far plane: darker, lower contrast, teal-black
    f = im[..., :3].astype(float); g = f.mean(-1, keepdims=True)
    im[..., :3] = np.clip((g + (f - g) * 0.7) * 0.8, 0, 255).astype(np.uint8)   # r3: 20% darker, 30% less saturated
    save(im, OUT + 'back.png')


def build_machines():
    segs = [pxpiece(crop(load(RAW + f'machines_{i}.png')), h=h, ncol=16) for i, h in ((1, 104), (2, 112))]
    pano = panorama(segs, 120, 30)
    im = f2u(pano); im[..., 3] = np.where(pano[..., 3] > 0.5, 255, 0)
    im = tone(im, 1.05, 0.0)
    im[..., :3] = np.clip(im[..., :3].astype(int) * 1.25 + 6, 0, 255).astype(np.uint8)   # mid plane lifted off the far wall
    save(outline(im, (6, 12, 16, 255)), OUT + 'machines.png')


# ------------------------------------------------------------------ animated set pieces
def glass_mask(im):
    f = im[..., :3].astype(int)
    return (im[..., 3] > 0) & (f[..., 1] > 120) & (f[..., 2] > 110) & (f[..., 0] < 150)


def build_tank():
    base = px(crop(load(RAW + 'tank_1.png')), h=128, n=14)
    H, W = base.shape[:2]
    g = glass_mask(base)
    ys, xs = np.where(g)
    rw = g.sum(1); full = np.where(rw > rw.max() * 0.6)[0]
    gy0, gy1 = full.min(), full.max(); xs = np.where(g[gy0:gy1].any(0))[0]; gx0, gx1 = xs.min(), xs.max()
    body, rim, eye = np.array([6, 30, 36]), np.array([20, 84, 88]), np.array([150, 255, 230])
    gw = gx1 - gx0; hw, hh = max(8, gw // 3), max(8, int(gw * 0.34))
    frames = []
    n = 8
    bub = [(int(rng.integers(gx0 + 2, gx1 - 2)), int(rng.integers(gy0, gy1))) for _ in range(7)]
    for f in range(n):
        im = base.copy()
        bob = [0, 0, 1, 2, 2, 2, 1, 0][f]; sway = [0, 0, 0, 1, 1, 1, 0, 0][f]
        cx = (gx0 + gx1) // 2 + sway; hy = gy0 + hh + 5 + bob
        cre = np.zeros((H, W), np.uint8)   # 1 body, 2 rim
        for y in range(-hh, hh + 1):
            for x in range(-hw, hw + 1):
                if (x / hw) ** 2 + (y / hh) ** 2 <= 1: cre[hy + y, cx + x] = 1
        for y in range(-hh, 1):
            for x in range(-hw, hw + 1):
                if cre[hy + y, cx + x] == 1 and (hy + y - 1 < 0 or cre[hy + y - 1, cx + x] == 0) and x < hw // 2: cre[hy + y, cx + x] = 2
        for k in range(6):
            x0 = cx - hw + 2 + k * (2 * hw - 4) // 5; ln = int((gy1 - hy) * (0.62 + 0.1 * (k % 3)))
            for i in range(ln):
                t = i / ln
                x = int(round(x0 + (k - 2.5) * 0.9 * t * 6 + 2.2 * t * np.sin(i / 5.0 + f * 0.8 + k)))
                y = hy + hh - 2 + i
                if y > gy1 - 3: break
                for dx in ((0, 1) if t < 0.8 else (0,)):
                    if 0 <= x + dx < W and g[y, x + dx]: cre[y, x + dx] = 1
        m1 = (cre == 1) & g; m2 = (cre == 2) & g
        im[m1, :3] = body; im[m2, :3] = rim
        for ex in (-hw // 2, hw // 2 - 1):
            if f not in (5,): im[hy + 1, cx + ex, :3] = eye
        for i, (bx, by) in enumerate(bub):
            yy = gy0 + (by - gy0 - f * 3 - i) % (gy1 - gy0)
            for dy, c in ((0, (200, 255, 246)), (1, (140, 230, 220))):
                if g[min(H - 1, yy + dy), bx]: im[yy + dy, bx, :3] = c
        frames.append(im)
    sheet = np.concatenate(frames, 1)
    save(sheet, OUT + 'tank.png')
    return W, H


def build_window():
    base = px(crop(load(RAW + 'window_1.png')), w=116, n=16)
    H, W = base.shape[:2]
    g = glass_mask(base)
    frames = []
    cols = [x for x in range(W) if g[:, x].sum() > H * 0.3]
    streak_x = cols[::9]
    bub = [(int(rng.choice(cols)), int(rng.integers(0, H))) for _ in range(9)]
    ys = np.where(g.any(1))[0]; y0, y1 = ys.min(), ys.max()
    for f in range(4):
        im = base.copy()
        for i, sx in enumerate(streak_x):   # light streaks drift one column per frame
            x = sx + (f if i % 2 else -f)
            if 0 <= x < W:
                m = g[:, x] & (im[:, x, 1] > 150)
                im[m, x, :3] = np.clip(im[m, x, :3].astype(int) + 26, 0, 255)
        for i, (bx, by) in enumerate(bub):
            yy = y0 + (by - f * 4 - i * 3) % (y1 - y0)
            if g[yy, bx]: im[yy, bx, :3] = (210, 255, 248)
        frames.append(im)
    save(np.concatenate(frames, 1), OUT + 'window.png')
    return W, H


def build_door(label='LAB 07'):
    im = px(crop(load(RAW + 'door_1.png')), w=104, n=14)
    H, W = im.shape[:2]
    # "LAB 07" stencil on the upper plate (plate centre found as the brightest flat grey band)
    s = label; tw = text_w(s)
    ty = int(H * 0.33)
    # find the upper door plate: widest light-grey run in the upper half
    lum = im[..., :3].astype(int).mean(-1)
    rows = [(np.sum((lum[y] > 95) & (lum[y] < 170)), y) for y in range(int(H * 0.2), int(H * 0.5))]
    ty = max(rows)[1] - 3
    px0 = W // 2 - tw // 2 - 4
    rect(im, px0 - 1, ty - 4, px0 + tw + 9, ty + 12, OL); rect(im, px0, ty - 3, px0 + tw + 8, ty + 11, (132, 140, 144, 255))
    rect(im, px0, ty - 3, px0 + tw + 8, ty - 2, (176, 184, 186, 255)); rect(im, px0, ty + 10, px0 + tw + 8, ty + 11, (84, 92, 96, 255))
    text(im, W // 2 - tw // 2, ty, s, (22, 26, 30, 255))
    # red lights: 2-frame blink (bright / dim) for the lamp pixels
    red = (im[..., 0] > 170) & (im[..., 1] < 110) & (im[..., 3] > 0)
    dim = im.copy(); dim[red, :3] = (dim[red, :3] * 0.45).astype(np.uint8)
    save(np.concatenate([im, dim], 1), OUT + 'door-' + label.replace(' ', '_') + '.png')
    return W, H


def build_toxic(w):
    """toxic pool surface: w x 60, 4 frames; bright teal-green surface line that ripples, darker body with glints"""
    H = 60; frames = []
    body = [(30, 150, 130), (18, 96, 90), (10, 58, 60), (6, 34, 38), (4, 20, 24)]
    for f in range(4):
        im = np.zeros((H, w, 4), np.uint8)
        for x in range(w):
            top = 14 + int(round(1.2 * np.sin((x + f * 4) / 5.0) + 0.8 * np.sin((x - f * 3) / 11.0)))
            for y in range(top, H):
                k = min(len(body) - 1, (y - top) // 6)
                im[y, x] = (*body[k], 255)
            im[top, x] = (236, 255, 240, 255)
            if top + 1 < H: im[top + 1, x] = (120, 250, 200, 255)
            if top + 2 < H: im[top + 2, x] = (60, 200, 160, 255)
            for yy in range(top + 3, min(H, top + 7)): im[yy, x] = (44, 176, 146, 255)   # lighter band under the surface
        for i in range(w // 10):
            gx = (i * 37 + f * 3) % w; gy = 10 + (i * 13) % (H - 16)
            im[gy, gx] = (60, 210, 170, 255)
        for i in range(w // 9):   # bubbles rising 4px/frame, popping as a 3px ring on the surface
            bx = (i * 53 + 7) % w; ph = (i * 5) % 4
            by = 44 - ((f + ph) % 4) * 8
            if (f + ph) % 4 == 3:
                t = 14 + int(round(1.2 * np.sin((bx + f * 4) / 5.0) + 0.8 * np.sin((bx - f * 3) / 11.0)))
                for dx in (-1, 0, 1):
                    if 0 <= bx + dx < w: im[t - 1, bx + dx] = (200, 255, 230, 255)
            else:
                by = 16 + ((3 - (f + ph) % 4)) * 6
                rect(im, bx, by, bx + 2, by + 2, (200, 255, 230, 255)); im[by + 1, min(w - 1, bx + 1)] = (90, 220, 180, 255)
                if by + 2 < H: rect(im, bx, by + 2, bx + 2, by + 3, (30, 120, 100, 255))
        frames.append(im)
    return np.concatenate(frames, 1)


# ------------------------------------------------------------------ heavy sub-floor (girders + big pipes), 256px seamless tile
def subfloor_tiles(Wt=256, Ht=110):
    """3 layered sub-floor variants (back pipe bundles / trusses / lit front pipes / hazard posts + lights).
    Every variant starts with a riveted post at x 0..9 so horizontal runs end cleanly at tile joins."""
    tiles = []
    BG = [(22, 30, 36), (16, 22, 28), (11, 16, 20), (7, 10, 13)]
    def base():
        im = np.zeros((Ht, Wt, 4), np.uint8)
        for y in range(Ht): im[y, :] = (*BG[min(3, y // 28)], 255)
        return im
    def bundle(im, x0, x1, y, n=3, vert=None):   # back layer: dark thin pipes, 1px dim highlight
        for i in range(n):
            yy = y + i * 5
            rect(im, x0, yy, x1, yy + 4, (30, 40, 46, 255)); rect(im, x0, yy, x1, yy + 1, (50, 64, 70, 255)); rect(im, x0, yy + 3, x1, yy + 4, (14, 18, 22, 255))
        if vert is not None:   # elbow down
            for i in range(n):
                xx = vert + i * 5
                rect(im, xx, y + i * 5, xx + 4, Ht, (30, 40, 46, 255)); rect(im, xx, y + i * 5, xx + 1, Ht, (50, 64, 70, 255)); rect(im, xx + 3, y + i * 5, xx + 4, Ht, (14, 18, 22, 255))
    def truss(im, x0, x1, ya, yb, step=26):     # mid layer: chords + X bracing
        c, hi, dk = (54, 66, 72, 255), (100, 116, 122, 255), (24, 30, 34, 255)
        for yy in (ya, yb):
            rect(im, x0, yy, x1, yy + 4, c); rect(im, x0, yy, x1, yy + 1, hi); rect(im, x0, yy + 3, x1, yy + 4, dk)
        for x in range(x0, x1 - step + 1, step):
            draw_line(im, x, ya + 4, x + step, yb - 1, c); draw_line(im, x + 1, ya + 4, x + step + 1, yb - 1, dk)
            draw_line(im, x + step, ya + 4, x, yb - 1, c); draw_line(im, x + step - 1, ya + 4, x - 1, yb - 1, hi)
            rect(im, x, ya + 4, x + 2, yb, c); rect(im, x, ya + 4, x + 1, yb, hi)
            im[ya + 1, x + 1] = (170, 184, 188, 255); im[yb + 1, x + 1] = (170, 184, 188, 255)
    def pipe(im, x0, x1, y, r, col, hi):         # front layer: lit pipe, rim light, flanges with bolts
        sh = tuple(int(c * 0.5) for c in col[:3]) + (255,)
        rect(im, x0, y - r - 1, x1, y + r + 2, OL)
        rect(im, x0, y - r, x1, y + r + 1, col); rect(im, x0, y - r, x1, y - r + 2, hi)
        rect(im, x0, y - r + 2, x1, y - r + 3, tuple(min(255, int(c * 1.15)) for c in col[:3]) + (255,))
        rect(im, x0, y + r - 1, x1, y + r + 1, sh); rect(im, x0, y + r, x1, y + r + 1, (60, 150, 150, 255))   # teal bounce light
        for x in range(x0 + 30, x1 - 8, 70):
            rect(im, x - 1, y - r - 3, x + 7, y + r + 4, OL); rect(im, x, y - r - 2, x + 6, y + r + 3, (76, 88, 94, 255))
            rect(im, x, y - r - 2, x + 6, y - r - 1, (160, 172, 176, 255))
            for by in (y - r, y, y + r): im[by, x + 1] = (190, 200, 204, 255); im[by, x + 4] = (190, 200, 204, 255)
    def hpost(im, x, y0):
        rect(im, x - 1, y0, x + 9, Ht, OL); hazard(im, x, y0, x + 8, Ht, 1)
        rect(im, x, y0, x + 8, y0 + 2, (120, 130, 134, 255))
    def rivpost(im, x, w=10):
        rect(im, x, 0, x + w, Ht, (44, 54, 60, 255)); rect(im, x, 0, x + 2, Ht, (96, 110, 116, 255))
        rect(im, x + w - 2, 0, x + w, Ht, (20, 26, 30, 255)); rect(im, x + w, 0, x + w + 1, Ht, OL)
        for y in range(6, Ht, 12): im[y, x + w // 2] = (160, 172, 176, 255); im[y + 1, x + w // 2] = OL
    def grate_light(im, x, y, w=40):             # glowing floor grate: lit teal slats + stepped spill below
        rect(im, x - 1, y - 1, x + w + 1, y + 7, OL)
        for i in range(w):
            im[y:y + 6, x + i] = (130, 250, 230, 255) if i % 3 else (30, 90, 90, 255)
        rect(im, x, y, x + w, y + 1, (220, 255, 250, 255))
        for dy, k in ((range(7, 13), 0.35), (range(13, 20), 0.16)):
            for yy in dy:
                if y + yy < Ht:
                    f = im[y + yy, x - 4:x + w + 4, :3].astype(float)
                    im[y + yy, x - 4:x + w + 4, :3] = (f * (1 - k) + np.array((80, 230, 210)) * k).astype(np.uint8)
    def leds(im, x, y, n=3):
        rect(im, x - 1, y - 1, x + n * 3, y + 3, OL); rect(im, x, y, x + n * 3 - 1, y + 2, (40, 46, 50, 255))
        for i in range(n): im[y, x + i * 3] = (255, 60, 50, 255); im[y + 1, x + i * 3] = (150, 20, 20, 255)
    def caged_lamp(im, x, y):
        for dy, k, r in ((0, 0.3, 14), (0, 0.15, 22)):   # two stepped amber rings on the surroundings
            pass
        for yy in range(max(0, y - 16), min(Ht, y + 20)):
            for xx in range(x - 18, x + 24):
                d = ((xx - x - 3) ** 2 / 1.6 + (yy - y - 3) ** 2) ** 0.5
                k = 0.28 if d < 8 else 0.12 if d < 14 else 0
                if k: im[yy, xx, :3] = (im[yy, xx, :3] * (1 - k) + np.array((255, 170, 70)) * k).astype(np.uint8)
        rect(im, x - 1, y - 2, x + 8, y + 9, OL); rect(im, x, y - 1, x + 7, y + 8, (255, 190, 90, 255))
        rect(im, x + 2, y + 1, x + 5, y + 5, (255, 244, 200, 255))
        for bx in (x + 1, x + 3, x + 5): rect(im, bx, y - 1, bx + 1, y + 8, (60, 50, 40, 255))
        rect(im, x, y + 3, x + 7, y + 4, (60, 50, 40, 255)); rect(im, x + 2, y - 4, x + 5, y - 2, (60, 66, 70, 255))
    # variant A: high back bundle, truss, big steel pipe, grate light
    a = base(); bundle(a, 0, Wt, 6, 3); truss(a, 0, Wt, 26, 50); pipe(a, 0, Wt, 72, 7, (62, 78, 86, 255), (150, 172, 178, 255))
    hpost(a, 120, 20); grate_light(a, 160, 60); leds(a, 60, 40); rivpost(a, 0)
    tiles.append(a)
    # variant B: two front pipes (steel + rust), low back bundle with elbow, hazard posts, LEDs
    b = base(); bundle(b, 0, Wt, 60, 4, vert=200); pipe(b, 0, Wt, 22, 6, (62, 78, 86, 255), (150, 172, 178, 255))
    pipe(b, 0, 190, 44, 5, (84, 44, 38, 255), (170, 104, 88, 255)); hpost(b, 90, 30); hpost(b, 170, 30)
    leds(b, 130, 60); leds(b, 30, 58, 2); caged_lamp(b, 226, 34); rivpost(b, 0)
    tiles.append(b)
    # variant C: truss low, vertical riser pipe, caged lamp, grate
    c = base(); bundle(c, 0, Wt, 14, 2); truss(c, 0, Wt, 50, 78, 32)
    pipe(c, 0, Wt, 30, 5, (62, 78, 86, 255), (150, 172, 178, 255))
    rect(c, 146, 30, 160, Ht, OL); rect(c, 147, 30, 159, Ht, (62, 78, 86, 255)); rect(c, 147, 30, 150, Ht, (150, 172, 178, 255)); rect(c, 157, 30, 159, Ht, (31, 39, 43, 255))
    caged_lamp(c, 90, 36); leds(c, 200, 60); grate_light(c, 186, 62, 34); rivpost(c, 0)
    tiles.append(c)
    return tiles


def subfloor_tile(Wt=256, Ht=110):
    return subfloor_tiles(Wt, Ht)[0]


# ------------------------------------------------------------------ hand-pixelled structure pieces
STEEL = dict(lip=(206, 222, 226, 255), top=(96, 112, 118, 255), plate=(62, 74, 80, 255), dk=(38, 46, 52, 255),
             edge=(20, 26, 30, 255), rivet=(120, 136, 142, 255))
HZ_Y, HZ_K = (240, 164, 24, 255), (22, 18, 14, 255)


def hazard(im, x0, y0, x1, y1, phase=0):
    for y in range(max(0, y0), min(im.shape[0], y1)):
        for x in range(max(0, x0), min(im.shape[1], x1)):
            im[y, x] = HZ_Y if ((x + y + phase) // 5) % 2 == 0 else HZ_K


def floor_plate(im, x0, x1, y):
    """riveted steel floor plate with a lit walk lip: rows y..y+8"""
    rect(im, x0, y, x1, y + 1, STEEL['lip'])
    rect(im, x0, y + 1, x1, y + 3, STEEL['top'])
    rect(im, x0, y + 3, x1, y + 8, STEEL['plate'])
    rect(im, x0, y + 8, x1, y + 9, STEEL['edge'])
    for x in range(x0 - x0 % 32, x1, 32):
        if x0 <= x < x1: rect(im, x, y + 1, x + 1, y + 8, STEEL['dk'])
        for rx in (x + 4, x + 16, x + 27):
            if x0 <= rx < x1 - 1:
                im[y + 4, rx] = (190, 204, 208, 255); im[y + 4, rx + 1] = STEEL['rivet']
                im[y + 5, rx] = STEEL['rivet']; im[y + 5, rx + 1] = STEEL['dk']; im[y + 6, rx:rx + 2] = STEEL['edge']


def catwalk(im, x0, x1, y, floor_at):
    rect(im, x0, y, x1, y + 1, STEEL['lip']); rect(im, x0, y + 1, x1, y + 3, STEEL['top'])
    rect(im, x0, y + 3, x1, y + 4, STEEL['edge'])
    hazard(im, x0, y + 4, x1, y + 12)
    rect(im, x0, y + 12, x1, y + 14, STEEL['edge'])
    rect(im, x0, y + 4, x0 + 1, y + 12, STEEL['edge']); rect(im, x1 - 1, y + 4, x1, y + 12, STEEL['edge'])
    # railing
    for x in list(range(x0 + 2, x1 - 2, 22)) + [x1 - 3]:
        rect(im, x, y - 13, x + 2, y, STEEL['dk']); rect(im, x, y - 13, x + 1, y, STEEL['top'])
    rect(im, x0 + 2, y - 14, x1 - 1, y - 12, STEEL['top']); rect(im, x0 + 2, y - 12, x1 - 1, y - 11, STEEL['edge'])
    rect(im, x0 + 2, y - 7, x1 - 1, y - 6, STEEL['dk'])
    # support columns down to the floor
    for x in (x0 + 6, x1 - 10):
        fy = floor_at(x + 2)
        if fy > y + 14:
            rect(im, x, y + 14, x + 4, fy, STEEL['dk']); rect(im, x, y + 14, x + 1, fy, STEEL['top'])
            rect(im, x + 3, y + 14, x + 4, fy, STEEL['edge'])


def grate(im, x0, x1, y):
    rect(im, x0, y, x1, y + 1, STEEL['lip'])
    for x in range(x0, x1):
        for yy in range(y + 1, y + 4):
            im[yy, x] = STEEL['top'] if (x % 3 and yy != y + 2) else STEEL['edge']
    hazard(im, x0, y + 4, x1, y + 7, 2)
    rect(im, x0, y + 7, x1, y + 8, STEEL['edge'])
    for x in range(x0 + 10, x1 - 6, 40):   # hanger struts
        rect(im, x, y + 8, x + 2, y + 16, STEEL['dk'])


def ladder(im, x, top, bot):
    rect(im, x, top - 6, x + 2, bot, STEEL['top']); rect(im, x + 12, top - 6, x + 14, bot, STEEL['top'])
    rect(im, x + 2, top - 6, x + 3, bot, STEEL['edge']); rect(im, x + 14, top - 6, x + 15, bot, STEEL['edge'])
    for y in range(top + 2, bot, 6):
        rect(im, x + 2, y, x + 12, y + 1, STEEL['lip']); rect(im, x + 2, y + 1, x + 12, y + 2, STEEL['edge'])


def sign(im, x, fy):
    w, h = 76, 44; y = fy - 118
    rect(im, x, y, x + w, y + h, (40, 50, 56, 255)); rect(im, x, y, x + w, y + 1, (70, 82, 88, 255))
    rect(im, x, y + h - 1, x + w, y + h, OL); rect(im, x, y, x + 1, y + h, OL); rect(im, x + w - 1, y, x + w, y + h, OL)
    for rx in (x + 3, x + w - 4):
        for ry in (y + 3, y + h - 4): im[ry, rx] = (96, 110, 116, 255)
    c = (118, 130, 134, 255); sh = (24, 30, 34, 255)
    text(im, x + w // 2 - text_w('SUB-LEVEL B') // 2, y + 7, 'SUB-LEVEL B', c, sh)
    text(im, x + w // 2 - text_w('SECTOR 3') // 2, y + 17, 'SECTOR 3', c, sh)
    # stencilled triangle emblem
    cx = x + w // 2
    for j in range(9):
        for i in range(-8 + j, 9 - j):
            if j in (0, 8 - abs(i)) or abs(i) == 8 - j: im[y + 28 + j, cx + i] = c


def ceiling(im, W, lights):
    rect(im, 0, 0, W, 10, (22, 28, 32, 255)); rect(im, 0, 10, W, 12, (60, 72, 78, 255)); rect(im, 0, 12, W, 13, OL)
    for x in range(0, W, 48):
        rect(im, x, 0, x + 3, 12, (34, 42, 46, 255)); im[4, x + 1] = STEEL['rivet']; im[8, x + 1] = STEEL['rivet']
    # pipe run along the ceiling
    rect(im, 0, 2, W, 5, (44, 54, 60, 255)); rect(im, 0, 2, W, 3, (78, 92, 98, 255))
    # hanging cable loops
    x = 20
    while x < W - 60:
        span = int(rng.integers(40, 80)); sag = int(rng.integers(8, 20)); col = (18, 24, 28, 255)
        span = min(span, W - 1 - x)
        for i in range(span):
            t = i / span; y = 12 + int(round(sag * 4 * t * (1 - t)))
            im[y, x + i] = col; im[y + 1, x + i] = (30, 38, 44, 255)
        x += span + int(rng.integers(30, 120))


# ------------------------------------------------------------------ landmarks: lit bays, light pools, DNA bank
LIGHT = dict(cyan=(80, 230, 220), green=(90, 230, 120), red=(230, 70, 60))


def mixpx(im, m, col, amt):
    f = im[..., :3].astype(float)
    im[m, :3] = np.clip(f[m] * (1 - amt) + np.array(col) * amt + .5, 0, 255).astype(np.uint8)


def bay(im, x0, x1, top, fy, col):
    """recessed lit wall bay behind a landmark: steel plates, hard-stepped light bands brighter toward the centre"""
    base = np.array([22, 34, 40]); c = np.array(col)
    cx = (x0 + x1) / 2; hw = (x1 - x0) / 2
    for x in range(max(0, x0), min(im.shape[1], x1)):
        d = abs(x - cx) / hw
        k = 0.30 if d < 0.4 else 0.18 if d < 0.72 else 0.07
        for y in range(top, fy):
            v = base * (1 - k) + c * k * 0.55
            if (y - top) % 24 == 0 or (x - x0) % 36 == 0: v = v * 0.62
            if (y - top) % 24 == 1: v = v * 1.18
            im[y, x] = (*np.clip(v, 0, 255).astype(int), 255)
    rect(im, x0, top, x1, top + 1, OL); rect(im, x0, top + 1, x1, top + 2, (90, 110, 116, 255))
    rect(im, x0, top, x0 + 1, fy, OL); rect(im, x1 - 1, top, x1, fy, OL)
    rect(im, x0 + 1, top, x0 + 3, fy, (70, 86, 92, 255)); rect(im, x1 - 3, top, x1 - 1, fy, (22, 28, 32, 255))


def light_pool(im, x0, x1, fy, col):
    """hard-stepped light spill on the floor plate and the first sub-floor rows in front of a landmark"""
    cx = (x0 + x1) / 2; hw = (x1 - x0) / 2 + 16
    for x in range(int(cx - hw), int(cx + hw)):
        if not (0 <= x < im.shape[1]): continue
        d = abs(x - cx) / hw
        k = 0.55 if d < 0.45 else 0.28 if d < 0.8 else 0.0
        for y0, y1, kk in ((fy, fy + 8, k),):
            seg = im[y0:y1, x, :3].astype(float)
            off = kk * 0.8 * (np.array(col, float) - 110)
            im[y0:y1, x, :3] = np.clip(seg + off, 0, 255).astype(np.uint8)


def dnabank(im, x, fy, img):
    w = 150; top = fy - 96
    bay(im, x, x + w, top, fy, LIGHT['green'])
    for i in range(3):
        sx = x + 10 + i * 46; sy = top + 10
        rect(im, sx - 1, sy - 1, sx + 37, sy + 25, OL); rect(im, sx, sy, sx + 36, sy + 24, (16, 60, 30, 255))
        if i == 1:
            rect(im, sx, sy, sx + 36, sy + 24, (12, 48, 24, 255))
            for j in range(22):
                a = int(round(6 * np.sin(j / 3.2)))
                if j % 3 == 0: rect(im, sx + 18 - abs(a), sy + 1 + j, sx + 18 + abs(a) + 1, sy + 2 + j, (40, 150, 80, 255))
                im[sy + 1 + j, sx + 18 + a] = (120, 255, 160, 255); im[sy + 1 + j, sx + 18 - a] = (60, 200, 110, 255)
        else:
            for j in range(0, 20, 3): rect(im, sx + 3, sy + 3 + j, sx + 3 + int(rng.integers(8, 30)), sy + 4 + j, (70, 220, 110, 255))
        rect(im, sx, sy + 24, sx + 36, sy + 26, (70, 86, 92, 255))
    t, c = img['terminal'], img['console']
    paste(im, t, x + 6, fy - t.shape[0] + 1, wrap=False)
    paste(im, c, x + 50, fy - c.shape[0] + 1, wrap=False)
    paste(im, t, x + w - 6 - t.shape[1], fy - t.shape[0] + 1, wrap=False)
    light_pool(im, x, x + w, fy, LIGHT['green'])


def red_lamp(im, x, y):
    rect(im, x, y + 3, x + 3, y + 5, (60, 70, 76, 255))
    rect(im, x + 2, y - 1, x + 10, y + 8, OL); rect(im, x + 3, y, x + 9, y + 7, (150, 22, 20, 255))
    rect(im, x + 4, y + 1, x + 8, y + 6, (236, 44, 36, 255)); rect(im, x + 5, y + 2, x + 7, y + 4, (255, 190, 170, 255))


# ------------------------------------------------------------------ world composite
def build_world():
    L = stage(); W, H = L['width'], L['height']
    P = props()
    img = {k: px(v, **a) for k, v, a in [
        ('terminal', P['terminal'], dict(h=44)), ('console', P['console'], dict(h=36)), ('crates', P['crates'], dict(h=60)),
        ('crate', P['crate'], dict(h=26)), ('lamp', P['lamp'], dict(h=12)), ('strip', P['strip'], dict(w=40))]}
    rock = px(crop(load(RAW + 'rock.png')), h=270, n=10)
    rock = tone(rock, 0.9, 0.12, (20, 26, 30))
    tiles = subfloor_tiles(); subt = tiles[0]
    ORDER = [0, 1, 2, 1, 0, 2, 2, 0, 1]
    def sub_col(x):
        return tiles[ORDER[(x // 256) % len(ORDER)]][:, x % 256]

    world = np.zeros((H, W, 4), np.uint8)
    back = np.zeros((H, W, 4), np.uint8)   # wall bays behind the animated set pieces (depth below the sprites)
    ground = sorted(L['ground'], key=lambda g: g['x'])
    def floor_at(x):
        for g in ground:
            if g['x'] <= x < g['x'] + g['w']: return g['y']
        for p in L['platforms']:
            if p['style'] == 'grate' and p['x'] <= x < p['x'] + p['w']: return p['y']
        return 999
    acid = []
    # sub-floor + plates
    for g in ground:
        x0, x1, y = g['x'], g['x'] + g['w'], g['y']
        for x in range(x0, x1):
            col = sub_col(x)
            world[y + 9:H, x] = np.concatenate([col, col])[:H - y - 9]
        floor_plate(world, x0, x1, y)
        for dy, k in ((9, 0.2), (10, 0.35), (11, 0.55), (12, 0.75)):   # occlusion under the walk lip
            world[y + dy, x0:x1, :3] = (world[y + dy, x0:x1, :3] * k).astype(np.uint8)
    rocksrc = px(crop(load(RAW + 'rock.png')), h=270, n=8)
    rocksrc = tone(rocksrc, 1.1, 0.0)
    rocksrc[..., :3] = np.clip(rocksrc[..., :3].astype(int) * 1.35 + 8, 0, 255).astype(np.uint8)
    for g in ground:
        for rx in range(g['x'] + 4, g['x'] + g['w'] - 20, 26):
            hh = int(rng.integers(20, 34)); ww = int(rng.integers(30, 48)); oy = int(rng.integers(0, 200))
            chunk = rocksrc[oy:oy + hh, :ww].copy()
            m = np.zeros(chunk.shape[:2], bool)   # rounded boulder silhouette
            for yy in range(hh):
                for xx in range(ww):
                    m[yy, xx] = ((xx - ww / 2) / (ww / 2)) ** 2 + ((yy - hh) / hh) ** 2 <= 1
            chunk[~m] = 0
            top = np.zeros_like(m); top[1:] = m[1:] & ~m[:-1]; top[0] = m[0]
            chunk[top, :3] = np.clip(chunk[top, :3].astype(int) + 60, 0, 255).astype(np.uint8)   # lit top rim
            chunk = outline(chunk, OL)
            paste(world, chunk, rx, H - int(rng.integers(7, 15)), wrap=False)   # sunk: only the lumpy tops show
    # risers at steps (hazard edge) and pit walls
    for a, b in zip(ground, ground[1:]):
        xa = a['x'] + a['w']
        if xa == b['x'] and a['y'] != b['y']:
            hi, lo = min(a['y'], b['y']), max(a['y'], b['y'])
            xe = xa if b['y'] < a['y'] else xa - 3
            hazard(world, xe, hi, xe + 3, lo + 9)
        elif b['x'] > xa:
            for xw, d in ((xa, 1), (b['x'] - 1, -1)):   # pit walls
                rect(world, min(xw, xw + d * 4), a['y'] if d == 1 else b['y'], max(xw, xw + d * 4) + 1, H, STEEL['dk'])
                rect(world, xw, a['y'] if d == 1 else b['y'], xw + 1, H, STEEL['edge'])
            # dark shaft behind the pool
            for x in range(xa + 5, b['x'] - 5):
                col = subt[:, x % subt.shape[1]].astype(int)
                col = np.concatenate([col, col])[:H - 150]
                world[150:H, x, :3] = (col[:, :3] * 0.35).astype(np.uint8); world[150:H, x, 3] = 255
            rect(world, xa + 5, 150, b['x'] - 5, 151, OL)
            ac = (60, 220, 170)
            for y0, y1, k in ((223, 225, 0.2), (225, 228, 0.4)):   # thin stepped glow just above the surface (y~228)
                m = np.zeros(world.shape[:2], bool); m[y0:y1, xa:b['x']] = True; m &= world[..., 3] > 0
                mixpx(world, m, ac, k)
            for y0, y1, k in ((150, 180, 0.28), (180, 206, 0.5), (206, 270, 0.62)):   # teal bleed up the pit walls
                for xw0, xw1 in ((xa, xa + 10), (b['x'] - 10, b['x'])):
                    m = np.zeros(world.shape[:2], bool); m[max(y0, a['y'] + 9):y1, xw0:xw1] = True; m &= world[..., 3] > 0
                    mixpx(world, m, ac, k)
            acid.append((xa, b['x']))
    lamps = []; pillars = []
    ceiling(world, W, [])
    # bulkhead pillars with a hazard panel and a red warning lamp, placed where no big prop stands
    busy = [(d['x'] - 18, d['x'] + {'tank': 56, 'window': 132, 'door': 116, 'sign': 80, 'tankpair': 130, 'dnabank': 152}[d['k']]) for d in L['decor'] if d['k'] in ('tank', 'window', 'door', 'sign', 'tankpair', 'dnabank')]
    busy += [(g['x'] + g['w'] - 20, g['x'] + g['w'] + 20) for g in ground]
    x = 120
    while x < W - 120:
        if any(a <= x <= b or a <= x + 16 <= b for a, b in busy): x += 20; continue
        fy = floor_at(x + 8)
        if fy > 200: x += 20; continue
        pillars.append((x, fy))
        rect(world, x, 13, x + 16, fy, (30, 38, 44, 255)); rect(world, x + 1, 13, x + 3, fy, (70, 84, 90, 255))
        rect(world, x + 13, 13, x + 15, fy, (18, 24, 28, 255)); rect(world, x, 13, x + 1, fy, OL); rect(world, x + 15, 13, x + 16, fy, OL)
        for ry in range(24, fy - 4, 18): world[ry, x + 7] = STEEL['rivet']; world[ry + 1, x + 7] = OL
        hazard(world, x + 3, fy - 40, x + 13, fy - 12)
        ly = 60
        rect(world, x + 4, ly - 1, x + 12, ly + 8, OL); rect(world, x + 5, ly, x + 11, ly + 7, (140, 20, 20, 255))
        rect(world, x + 6, ly + 1, x + 10, ly + 6, (230, 40, 36, 255)); rect(world, x + 7, ly + 2, x + 9, ly + 4, (255, 170, 150, 255))
        lamps.append((x + 4, ly - 1))
        x += int(rng.integers(200, 300))
    # decor (back): rock, sign, landmarks, crates (tanks/window/door are animated sprites)
    sprites = []; feet = []
    for d in L['decor']:
        k, x = d['k'], d['x']; fy = d.get('y', floor_at(x + 10))
        if k == 'rock':
            xx = x if x < W // 2 else W - rock.shape[1]
            paste(world, rock, xx, 0, wrap=False)
        elif k == 'sign': sign(world, x, fy)
        elif k == 'tankpair':
            bay(back, x - 14, x + 126, 26, fy, LIGHT['cyan'])
            sprites += [dict(k='tank', x=x, y=fy), dict(k='tank', x=x + 60, y=fy)]
        elif k == 'window':
            bay(back, x - 14, x + 130, 22, 118, LIGHT['cyan'])
            sprites.append(dict(k='window', x=x, y=fy))
        elif k == 'door':
            bay(back, x - 10, x + 114, fy - 120, fy, LIGHT['red'])
            sprites.append(dict(k='door', x=x, y=fy, label=d.get('label', 'LAB 07')))
        elif k == 'dnabank': dnabank(back, x, fy, img)
        elif k == 'tank': sprites.append(dict(k='tank', x=x, y=fy))
        elif k in img:
            s_ = img[k]
            paste(world, s_, x, fy - s_.shape[0] + 1, wrap=False)
            feet.append((x + 1, x + s_.shape[1] - 1, fy))
    lampbusy = busy + [(d['x'] - 16, d['x'] + 160) for d in L['decor'] if d['k'] in ('tankpair', 'dnabank')]
    for x in range(90, W - 40, 240):
        xx = x
        while any(a_ <= xx <= b_ for a_, b_ in lampbusy) and xx < x + 200: xx += 12
        if xx < x + 200 and floor_at(xx) < 200: red_lamp(world, xx, 52)
    for d in L['decor']:
        if d['k'] == 'ladder': ladder(world, d['x'], d['top'], floor_at(d['x'] + 7))
    for p in L['platforms']:
        (grate if p['style'] == 'grate' else catwalk)(world, p['x'], p['x'] + p['w'], p['y'], *( [] if p['style'] == 'grate' else [floor_at]))
    # ceiling strip lights every ~220px, over the gaps between big props
    for x in range(60, W - 60, 220):
        paste(world, img['strip'], x, 12, wrap=False)
        st = img['strip']; hy = 12 + st.shape[0] - 5
        rect(world, x + 5, hy, x + st.shape[1] - 5, hy + 2, (236, 255, 255, 255)); rect(world, x + 5, hy + 2, x + st.shape[1] - 5, hy + 3, (120, 230, 240, 255))
    # light sources light their surroundings: stepped colour spill on front-layer pixels (pillars, crates, catwalks)
    def spill(x0, x1, y0, y1, col, reach=40):
        for dist, k in ((12, 0.34), (26, 0.2), (reach, 0.1)):
            for xa_, xb_ in ((x0 - dist, x0), (x1, x1 + dist)):
                m = np.zeros(world.shape[:2], bool); m[y0:y1, max(0, xa_):min(W, xb_)] = True; m &= world[..., 3] > 0
                mixpx(world, m, col, k)
    # rim-light platform lips that face a light source (lip row takes the light colour)
    lit = []
    for d in L['decor']:
        c = {'tankpair': LIGHT['cyan'], 'window': LIGHT['cyan'], 'door': LIGHT['red'], 'dnabank': LIGHT['green']}.get(d['k'])
        if c: lit.append((d['x'] - 30, d['x'] + 170, c))
    lit += [(a_ - 10, b_ + 10, (60, 220, 170)) for a_, b_ in acid]
    marks = sorted([d['x'] for d in L['decor'] if d['k'] in ('tankpair', 'window', 'door', 'dnabank', 'sign')] + [0, W])
    for a_, b_ in zip(marks, marks[1:]):
        gap0 = a_ + 150; gap1 = b_ - 20
        n_ = int((gap1 - gap0) // 190)
        for j in range(n_):
            sx = int(gap0 + (j + 0.5) * (gap1 - gap0) / n_) - 14
            fy_ = floor_at(sx + 14)
            if fy_ > 200: continue
            bay(back, sx, sx + 30, 34, fy_, LIGHT['cyan'])
            rect(back, sx + 13, 44, sx + 17, 110, (236, 255, 255, 255)); rect(back, sx + 12, 44, sx + 13, 110, (120, 230, 240, 255))
            rect(back, sx + 17, 44, sx + 18, 110, (120, 230, 240, 255)); rect(back, sx + 11, 42, sx + 19, 44, OL); rect(back, sx + 11, 110, sx + 19, 112, OL)
            lit.append((sx - 20, sx + 50, LIGHT['cyan']))
    # re-draw floor lips last so props never cover the walk line

    for g in ground: floor_plate(world, g['x'], g['x'] + g['w'], g['y'])
    for fx0, fx1, fy in feet:   # contact shadow: 2 rows on the floor lip under props
        for dy, k in ((0, 0.35), (1, 0.55)):
            world[fy + dy, fx0:fx1, :3] = (world[fy + dy, fx0:fx1, :3] * k).astype(np.uint8)
        world[fy - 1, fx0:fx1, :3] = (world[fy - 1, fx0:fx1, :3] * 0.5).astype(np.uint8)
    for d in L['decor']:
        c = {'tankpair': LIGHT['cyan'], 'window': LIGHT['cyan'], 'door': LIGHT['red'], 'dnabank': LIGHT['green']}.get(d['k'])
        if not c: continue
        x = d['x']; fy = d.get('y', floor_at(x + 10)); w_ = {'tankpair': 116, 'window': 116, 'door': 104, 'dnabank': 150}[d['k']]
        light_pool(world, x, x + w_, fy, c)
    for x0_, x1_, c in lit:
        for p in L['platforms'] + ground:
            a_, b_ = max(x0_, p['x']), min(x1_, p['x'] + p['w'])
            if a_ < b_:
                y = p['y']; rim = tuple(int(min(255, v * 0.55 + 120)) for v in c) + (255,)
                world[y, a_:b_] = rim
                m = np.zeros(world.shape[:2], bool); m[y + 1:y + 3, a_:b_] = True; mixpx(world, m, c, 0.3)
    CW = 480; n = (W + CW - 1) // CW
    for i in range(n):
        save(world[:, i * CW:(i + 1) * CW], OUT + f'chunk{i}.png')
        save(back[:, i * CW:(i + 1) * CW], OUT + f'bchunk{i}.png')
    return n, sprites


if __name__ == '__main__':
    build_back(); build_machines()
    tw, th = build_tank(); ww, wh = build_window()
    labels = sorted({d.get('label', 'LAB 07') for d in stage()['decor'] if d['k'] == 'door'})
    for lb in labels: dw, dh = build_door(lb)
    L = stage()
    for i, w in enumerate(L['water']):
        save(build_toxic(w['w']), OUT + f'toxic{i}.png')
    n, sprites = build_world()
    meta = dict(sprites=sprites, chunks=n, tank=[tw, th], window=[ww, wh], door=[dw, dh], toxic=[w['w'] for w in L['water']])
    json.dump(meta, open(OUT + 'meta.json', 'w'))
    open('src/level/stage3/meta3.js', 'w').write('// generated by art/raw/stage3/build3.py - do not edit' + chr(10) + 'export const meta3 = ' + json.dumps(meta) + ';' + chr(10))
    assets = [{"type": "image", "key": "s3-back", "url": "assets/stage3/back.png"},
              {"type": "image", "key": "s3-machines", "url": "assets/stage3/machines.png"},
              {"type": "spritesheet", "key": "s3-tank", "url": "assets/stage3/tank.png", "frameWidth": tw, "frameHeight": th},
              {"type": "spritesheet", "key": "s3-window", "url": "assets/stage3/window.png", "frameWidth": ww, "frameHeight": wh},
              ] + [{"type": "spritesheet", "key": "s3-door-" + lb.replace(' ', '_'), "url": "assets/stage3/door-" + lb.replace(' ', '_') + ".png", "frameWidth": dw, "frameHeight": dh} for lb in labels]
    for i in range(n): assets.append({"type": "image", "key": f"s3-chunk{i}", "url": f"assets/stage3/chunk{i}.png"})
    for i in range(n): assets.append({"type": "image", "key": f"s3-bchunk{i}", "url": f"assets/stage3/bchunk{i}.png"})
    for i, w in enumerate(L['water']):
        assets.append({"type": "spritesheet", "key": f"s3-toxic{i}", "url": f"assets/stage3/toxic{i}.png", "frameWidth": w['w'], "frameHeight": 60})
    json.dump({"assets": assets, "anims": []}, open('assets/parts/stage3.json', 'w'), indent=1)
    print('meta', meta)
