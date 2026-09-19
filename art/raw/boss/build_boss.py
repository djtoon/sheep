"""Build all stage-1 boss art (The Iron Eagle Gate) from the raw generations in art/raw/boss/.
python art/raw/boss/build_boss.py  -> assets/boss/*.png  (hard alpha, shared palette, 1px dark outline)"""
import numpy as np, math, random, sys
sys.path.insert(0, 'art/raw/boss')
from matpal import lock, crisp
from PIL import Image, ImageDraw, ImageFilter
R = 'art/raw/boss/'; O = 'assets/boss/'
OUT = np.array([0x1a, 0x14, 0x20], np.uint8)
S = 10.3; BOX = (16, 28, 1006, 1513)   # 96x144 body: fits between the HUD band and the raised ground (y=168)
F = 7.5 / S                              # region numbers below were measured at S=7.5
def f(v): return round(v * F)
random.seed(7); np.random.seed(7)


def load(f, thr=200):
    a = np.array(Image.open(R + f).convert('RGBA')).astype(np.float32) / 255
    a[..., 3] = (a[..., 3] >= thr / 255).astype(np.float32)
    return a


def down(a, w, h, sharpen=True):
    pre = np.concatenate([a[..., :3] * a[..., 3:4], a[..., 3:4]], -1)
    s = np.array(Image.fromarray((pre * 255).astype(np.uint8), 'RGBA').resize((w, h), Image.BOX)).astype(np.float32) / 255
    al = s[..., 3:4]
    col = np.where(al > 1e-3, s[..., :3] / np.maximum(al, 1e-3), 0)
    if sharpen:
        im = Image.fromarray((np.clip(col, 0, 1) * 255).astype(np.uint8)).filter(ImageFilter.UnsharpMask(radius=1.0, percent=70, threshold=2))
        col = np.array(im).astype(np.float32) / 255
    out = np.zeros((h, w, 4), np.uint8)
    out[..., :3] = (np.clip(col, 0, 1) * 255).astype(np.uint8)
    out[..., 3] = np.where(al[..., 0] >= 0.5, 255, 0)
    return out


W = round((BOX[2] - BOX[0]) / S); H = round((BOX[3] - BOX[1]) / S)
def smooth(a, k=3, n=1):
    # edge-preserving flatten at hi-res: kills the generator's speckle texture so planes downsample to flat ramps
    im = Image.fromarray((a[..., :3] * 255).astype(np.uint8))
    for _ in range(n): im = im.filter(ImageFilter.MedianFilter(k))
    o = a.copy(); o[..., :3] = np.array(im).astype(np.float32) / 255
    return o
def body(f): return down(smooth(load(f)[BOX[1]:BOX[3], BOX[0]:BOX[2]]), W, H, sharpen=False)
intact, dmg, opn = body('body_a_1.png'), body('body_dmg.png'), body('body_open.png')

# ---------- turret (pre-rotated from the hi-res source so every angle is a clean pixel sprite)
T = load('turret.png'); TC = (1000, 520); TS = 28.5; CELL = 72
ANG = [-20, -10, 0, 10, 20, 30, 40, 50, 60]


def tur_frame(src, ang):
    im = Image.fromarray((src * 255).astype(np.uint8), 'RGBA')
    big = int(CELL * TS)
    canvas = Image.new('RGBA', (big, big), (0, 0, 0, 0))
    canvas.paste(im, (int(big / 2 - TC[0]), int(big / 2 - TC[1])), im)
    canvas = canvas.rotate(ang, resample=Image.BICUBIC, center=(big / 2, big / 2))
    a = np.array(canvas).astype(np.float32) / 255
    a[..., 3] = (a[..., 3] > 0.5).astype(np.float32)
    return down(a, CELL, CELL)


tur = [tur_frame(T, a) for a in ANG]
Tw = T.copy()
xs = np.arange(Tw.shape[1])[None, :]; ys = np.arange(Tw.shape[0])[:, None]
cut = 560 + (np.sin(ys / 23.0) * 40 + np.cos(ys / 9.0) * 25)       # jagged break line through the barrels
Tw[..., 3] = np.where(xs < cut, 0, Tw[..., 3])
Tw[..., :3] *= 0.72
tur_wreck = tur_frame(Tw, 18)

# ---------- palette: shared median cut across everything, then remap
parts = [intact, dmg, opn]
px = np.concatenate([p[p[..., 3] > 0][:, :3] for p in parts])
pal_img = Image.fromarray(px.reshape(1, -1, 3)).quantize(colors=30, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)


def deorphan(o, passes=2):
    # a pixel unlike all 4 neighbours, where 3+ neighbours agree, takes the neighbours' colour (no salt-and-pepper)
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


def pq(a, pal=None):
    o = lock(a); o[a[..., 3] == 0] = 0
    o = deorphan(o)
    return lock(crisp(o)) if False else crisp(o)


def outline(a):
    m = a[..., 3] > 0; n = np.zeros_like(m)
    n[1:] |= m[:-1]; n[:-1] |= m[1:]; n[:, 1:] |= m[:, :-1]; n[:, :-1] |= m[:, 1:]
    r = n & ~m; o = a.copy(); o[r, :3] = OUT; o[r, 3] = 255
    return o


def pad(a, p=1):
    h, w = a.shape[:2]; o = np.zeros((h + 2 * p, w + 2 * p, 4), np.uint8); o[p:p + h, p:p + w] = a
    return o


intact, dmg, opn = pq(intact), pq(dmg), pq(opn)

# ---------- regions (game px, in the 132x198 body frame)
DX0, DX1, DY0, DY1 = f(40), f(93), f(124), H  # blast door opening
DM = f(66)                                 # door seam
LX0, LX1, LY1 = f(47), f(86), f(27)        # roof launcher box


def body_final(src):
    b = src.copy()
    b[DY0:DY1, DX0:DX1] = opn[DY0:DY1, DX0:DX1]          # chamber behind the doors
    b[:LY1, LX0:LX1] = 0                                   # launcher lives in its own sprite
    return b


def with_dark(src, k):  # scorched version
    o = src.copy(); o[..., :3] = (o[..., :3].astype(np.float32) * k).astype(np.uint8)
    return o


bI, bD = body_final(intact), body_final(dmg)
bW = with_dark(bD, 0.62)
yy, xx = np.mgrid[:H, :W]
for _ in range(26):
    cx, cy, r = random.randint(4, W - 4), random.randint(20, H - 4), random.randint(3, 8)
    m = ((xx - cx) ** 2 + (yy - cy) ** 2 < r * r) & (bW[..., 3] > 0)
    bW[m, :3] = (bW[m, :3] * 0.45).astype(np.uint8)
bodies = [outline(pad(b)) for b in (bI, bD, bW)]
Image.fromarray(np.concatenate(bodies, 1)).save(O + 'boss-body.png')       # 3 frames of (W+2)x(H+2)


def door(src, x0, x1):
    d = src[DY0:DY1, x0:x1].copy(); d[..., 3] = 255
    return d


dl = [door(intact, DX0, DM), door(dmg, DX0, DM)]; dr = [door(intact, DM, DX1), door(dmg, DM, DX1)]
for d in dl: d[:, -1, :3] = OUT
for d in dr: d[:, 0, :3] = OUT
Image.fromarray(np.concatenate(dl, 1)).save(O + 'boss-door-l.png')
Image.fromarray(np.concatenate(dr, 1)).save(O + 'boss-door-r.png')

# launcher: intact, damaged, wrecked stump
li, ld = intact[:LY1, LX0:LX1].copy(), dmg[:LY1, LX0:LX1].copy()
lw = with_dark(ld, 0.55)
for x in range(lw.shape[1]):
    top = 9 + int(4 * math.sin(x * 0.9) + 3 * math.cos(x * 2.3))
    lw[:top, x] = 0
L = [outline(pad(v)) for v in (li, ld, lw)]
Image.fromarray(np.concatenate(L, 1)).save(O + 'boss-launcher.png')

# core: the glowing eye cut from the open chamber (normal / hot)
CX, CY, CR = f(65), f(154), f(12)
core = opn[CY - CR:CY + CR + 1, CX - CR:CX + CR + 1].copy()
cy, cx = np.mgrid[:2 * CR + 1, :2 * CR + 1]
core[(cx - CR) ** 2 + (cy - CR) ** 2 > (CR + 0.5) ** 2] = 0
hot = core.copy(); f = hot[..., :3].astype(np.float32)
hot[..., :3] = np.clip(f * np.array([1.25, 1.35, 1.3]) + np.array([30, 18, 10]), 0, 255).astype(np.uint8)
hot[core[..., 3] == 0] = 0
def cracked(img, n, seed):
    rr = random.Random(seed); o = img.copy(); D = 2 * CR + 1
    for _ in range(n):
        x, y = rr.randint(CR - 3, CR + 3), rr.randint(CR - 3, CR + 3)
        for _ in range(rr.randint(5, 9)):
            if 0 <= x < D and 0 <= y < D and o[y, x, 3]: o[y, x, :3] = (0x1a, 0x0c, 0x10)
            if 0 <= x + 1 < D and 0 <= y < D and o[y, x + 1, 3] and rr.random() < 0.4: o[y, x + 1, :3] = (0xff, 0xe0, 0x90)
            x += rr.choice([-1, 0, 1]); y += rr.choice([-1, 1])
    return o
c1, c2 = cracked(core, 2, 3), cracked(cracked(core, 2, 3), 3, 9)
h1, h2 = cracked(hot, 2, 3), cracked(cracked(hot, 2, 3), 3, 9)
Image.fromarray(np.concatenate([core, hot, c1, h1, c2, h2], 1)).save(O + 'boss-core.png')   # [ok, ok-hot, crack1, crack1-hot, crack2, crack2-hot]

# turret sheet: 9 angles + wreck
# turret sheet is built by build_turret.py (run at the end)


# ---------- small procedural sprites, drawn big then point-sampled
def pal_render(draw_fn, size, k=8):
    big = Image.new('RGBA', (size * k, size * k), (0, 0, 0, 0)); draw_fn(ImageDraw.Draw(big), k)
    a = np.array(big.resize((size, size), Image.NEAREST)); a[..., 3] = np.where(a[..., 3] > 127, 255, 0)
    return a


STEEL = [(0x2c, 0x2a, 0x33), (0x55, 0x58, 0x63), (0x8d, 0x92, 0x9c), (0xc9, 0xcd, 0xd3)]


def saw(rot):
    def d(g, k):
        c = 9 * k; n = 10; pts = []
        for i in range(n * 2):
            a = rot + i * math.pi / n; r = (8.4 if i % 2 == 0 else 6.2) * k
            a2 = a + (0.18 if i % 2 == 0 else 0)
            pts.append((c + math.cos(a2) * r, c + math.sin(a2) * r))
        g.polygon(pts, fill=(*STEEL[0], 255))
        g.polygon([(c + (x - c) * 0.84, c + (y - c) * 0.84) for x, y in pts], fill=(*STEEL[2], 255))
        g.ellipse([c - 5 * k, c - 5 * k, c + 5 * k, c + 5 * k], fill=(*STEEL[1], 255))
        g.ellipse([c - 3.6 * k, c - 3.6 * k, c + 3.6 * k, c + 3.6 * k], fill=(*STEEL[0], 255))
        g.ellipse([c - 2.4 * k, c - 2.4 * k, c + 2.4 * k, c + 2.4 * k], fill=(0xd8, 0x28, 0x20, 255))
        g.rectangle([c - 0.9 * k, c - 0.9 * k, c + 0.4 * k, c + 0.4 * k], fill=(0xff, 0xd8, 0x70, 255))
        for i in range(3):
            a = rot * 2 + i * 2.1
            g.line([(c + math.cos(a) * 3.8 * k, c + math.sin(a) * 3.8 * k), (c + math.cos(a) * 6.2 * k, c + math.sin(a) * 6.2 * k)], fill=(*STEEL[3], 255), width=k)
    return outline(pal_render(d, 18))


Image.fromarray(np.concatenate([saw(i * math.pi / 20) for i in range(4)], 1)).save(O + 'boss-saw.png')


def shell(hot):
    a = np.zeros((12, 8, 4), np.uint8)
    body_c = [(0x3b, 0x44, 0x2a), (0x5e, 0x6b, 0x3c), (0x8a, 0x96, 0x55)]
    for y in range(2, 10):
        for x in range(1, 7):
            if (x in (1, 6)) and y in (2, 9): continue
            a[y, x] = (*body_c[0 if x >= 5 else 1 if x >= 3 else 2], 255)
    a[10, 2:6] = (*STEEL[1], 255); a[11, 1:7] = (*STEEL[0], 255); a[11, 3:5] = (*STEEL[2], 255)
    a[1, 3:5] = (0xff, 0xe0, 0x80, 255) if hot else (0xc0, 0x20, 0x18, 255)
    a[2, 2:6] = (0xe8, 0x30, 0x20, 255) if hot else (0x90, 0x18, 0x14, 255)
    return outline(pad(a[::-1].copy()))   # nose down


Image.fromarray(np.concatenate([shell(False), shell(True)], 1)).save(O + 'boss-shell.png')


def glow():
    s = 25; a = np.zeros((s, s, 4), np.uint8); c = s // 2
    rings = [(12.5, (0x40, 0x08, 0x06)), (9.5, (0x80, 0x14, 0x0c)), (6.5, (0xd0, 0x38, 0x14)), (4, (0xff, 0x90, 0x40)), (2, (0xff, 0xf0, 0xc0))]
    for r, col in rings:
        for y in range(s):
            for x in range(s):
                if (x - c) ** 2 + (y - c) ** 2 <= r * r: a[y, x] = (*col, 255)
    return a


Image.fromarray(glow()).save(O + 'boss-glow.png')


def glow_s():
    s = 11; a = np.zeros((s, s, 4), np.uint8); c = 5
    for r, col in [(5.5, (0x50, 0x10, 0x06)), (4, (0xa0, 0x30, 0x10)), (2.5, (0xff, 0x80, 0x30)), (1.2, (0xff, 0xf0, 0xb0))]:
        for y in range(s):
            for x in range(s):
                if (x - c) ** 2 + (y - c) ** 2 <= r * r: a[y, x] = (*col, 255)
    return a


Image.fromarray(glow_s()).save(O + 'boss-glow-s.png')


def mark(on):
    a = np.zeros((7, 21, 4), np.uint8); col = (0xff, 0x40, 0x30, 255) if on else (0x9a, 0x18, 0x14, 255)
    for x in range(21):
        dx = (x - 10) / 10.0; h = round(3 * math.sqrt(max(0, 1 - dx * dx)))
        if abs(x - 10) > 4: a[3 + h, x] = col; a[3 - h, x] = col
    a[3, 9:12] = col; a[2:5, 10] = col
    return a


Image.fromarray(np.concatenate([mark(True), mark(False)], 1)).save(O + 'boss-mark.png')

# debris: irregular chunks cut from the damaged facade (9x9 cells)
ch = []
for i in range(8):
    while True:
        cx, cy = random.randint(10, W - 10), random.randint(30, H - 20)
        sub = dmg[cy - 4:cy + 5, cx - 4:cx + 5].copy()
        if (sub[..., 3] > 0).all(): break
    yy2, xx2 = np.mgrid[:9, :9]
    ang = np.arctan2(yy2 - 4, xx2 - 4); rr = 2.4 + random.random() * 1.2 + np.sin(ang * 3 + i) * 0.9
    sub[(xx2 - 4) ** 2 + (yy2 - 4) ** 2 > rr ** 2] = 0
    ch.append(outline(sub))
Image.fromarray(np.concatenate(ch, 1)).save(O + 'boss-chunks.png')
print('F', F, 'DX0', DX0, 'DX1', DX1, 'DY0', DY0, 'DM', DM, 'LX0', LX0, 'LX1', LX1, 'LY1', LY1, 'CX', CX, 'CY', CY, 'CR', CR)
print('body', W + 2, H + 2, 'door', DM - DX0, DX1 - DM, DY1 - DY0, 'launcher', LX1 - LX0 + 2, LY1 + 2, 'core', 2 * CR + 1, 'turret', CELL)

exec(open(R + 'build_turret.py').read())

# foundation / plinth the tower stands on (drawn below the ground line, into the cliff)
OUT = np.array([0x1a, 0x14, 0x20], np.uint8)   # build_turret (exec'd above) rebinds OUT
fa = load('found_2.png')
ys_, xs_ = np.where(fa[..., 3] > 0)
fa = fa[ys_.min():ys_.max() + 1, xs_.min():xs_.max() + 1]
FW = 132; FH = round(fa.shape[0] * FW / fa.shape[1])
fd = down(smooth(fa), FW, FH, sharpen=False)
fpx = fd[fd[..., 3] > 0][:, :3]
fpal = Image.fromarray(fpx.reshape(1, -1, 3)).quantize(colors=24, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
fd = pq(fd, fpal)
Image.fromarray(outline(pad(fd))).save(O + 'boss-found.png')
print('found', FW + 2, FH + 2)
