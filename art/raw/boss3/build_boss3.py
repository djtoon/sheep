"""Stage-3 boss art: SPECIMEN X, the xeno-cyborg queen (ref/levels/level3 boss.png via gen.mjs edits).
python art/raw/boss3/build_boss3.py -> assets/boss3/*.png ; prints layout numbers used by Boss3.js"""
import sys, math, random
import numpy as np
from PIL import Image
from scipy import ndimage
sys.path.insert(0, 'art/raw/boss2')
from kit import load, to_game, clean, outline, pad, rotate_hi, sheet, down, smooth, H, OUT, pop, outline2
R = 'art/raw/boss3/'; O = 'assets/boss3/'
random.seed(5)
S = 7.3; BOX = (15, 55, 1010, 985)                      # ~132px tall: the whole queen stays below the HUD band (y>=34)
g = lambda x, y: (round((x - BOX[0]) / S) + 2, round((y - BOX[1]) / S) + 2)
POP = dict(rim=H('e070f0'), rim_mats=('purple',), lift=('concrete',), darken=('steel',))
from kit import load as _l
def heavy(a):  # the wounded edit is full of drip speckle: flatten harder before downsampling
    return smooth(smooth(a, 5, 2), 3, 1)

body, hurt, lunge, ref = (load(R + f) for f in ('body.png', 'hurt.png', 'lunge.png', 'ref_cut.png'))
def gm(a, hv=False):
    x0, y0, x1, y1 = BOX; w, h = round((x1 - x0) / S), round((y1 - y0) / S)
    return down(heavy(a[y0:y1, x0:x1]) if hv else smooth(a[y0:y1, x0:x1]), w, h)
frames = [outline2(pop(gm(a, hv), **POP)) for a, hv in ((body, False), (hurt, True), (lunge, False))]
sheet(frames, O + 'b3-body.png'); FW, FH = frames[0].shape[1], frames[0].shape[0]


def extract(region, thr=0.35, grow=3):
    x0, y0, x1, y1 = region
    diff = np.abs(ref[..., :3] - body[..., :3]).sum(-1)
    m = (ref[..., 3] > 0) & ((body[..., 3] == 0) | (diff > thr))
    box = np.zeros_like(m); box[y0:y1, x0:x1] = True; m &= box
    m = ndimage.binary_closing(m, iterations=grow); m = ndimage.binary_fill_holes(m); m = ndimage.binary_opening(m, iterations=2)
    lab, n = ndimage.label(m); sizes = ndimage.sum(m, lab, range(1, n + 1)); m = lab == (np.argmax(sizes) + 1)
    a = ref.copy(); a[~m] = 0
    return a, m


# ---- plasma cannon arm (static; the beam is horizontal)
can, cm = extract((10, 380, 440, 680))
ys, xs = np.where(cm); CB = (xs.min() - 2, ys.min() - 2, xs.max() + 3, ys.max() + 3)
cimg = outline2(pop(to_game(can, CB, S), **POP))
Image.fromarray(cimg).save(O + 'b3-cannon.png')
muzzle = g(xs.min(), (ys.min() + ys.max()) / 2 - 12)
mx, my = muzzle[0] - g(CB[0], CB[1])[0] + 2, muzzle[1] - g(CB[0], CB[1])[1] + 2   # muzzle in cannon-sprite px (2px outline pad)
for dy in range(-2, 3):
    for dx in range(0, 3):
        yy_, xx_ = my + dy, mx + dx
        if 0 <= yy_ < cimg.shape[0] and 0 <= xx_ < cimg.shape[1]: cimg[yy_, xx_] = (*H('46dcd8'), 255)
cimg[my - 1:my + 2, mx:mx + 2] = (*H('a8fff4'), 255); cimg[my, mx] = (255, 255, 255, 255)   # hot-white muzzle
Image.fromarray(cimg).save(O + 'b3-cannon.png')
print('MUZ local', mx, my)

# ---- scorpion tail, pre-rotated around its root (rears back / whips forward)
tail, tm = extract((690, 40, 1012, 600), thr=0.3)
ys, xs = np.where(tm)
ROOT = (int(np.percentile(xs[ys > ys.max() - 60], 50)), ys.max() - 10)
TA = [-25, -12, 0, 12, 25]
CELLT = 190
tcells = [outline(outline(pop(down(smooth(rotate_hi(tail, ROOT, a, int(CELLT * S))), CELLT, CELLT), **POP))) for a in TA]
sheet(tcells, O + 'b3-tail.png')
# stinger tip relative to root (unrotated), game px
tipx, tipy = (xs[ys == ys.min()].mean() - ROOT[0]) / S, (ys.min() - ROOT[1]) / S

# ---- organ (cyan honeycomb heart): cut from the body frame, with hot + 2 crack stages
def organ_at(a, near):
    x, y = near; sub = a[y - 110:y + 110, x - 110:x + 110]
    sc = sub[..., 1] + sub[..., 2] - sub[..., 0] * 1.6
    yy, xx = np.unravel_index(np.argmax(ndimage.uniform_filter(sc, 25)), sc.shape)
    return (x - 110 + xx, y - 110 + yy)
org_hi = [organ_at(body, (470, 470)), organ_at(hurt, (470, 470)), organ_at(lunge, (470, 565))]
OR = 8
f0 = frames[0]; ocx, ocy = g(*org_hi[0])
org = f0[ocy - OR:ocy + OR + 1, ocx - OR:ocx + OR + 1].copy()
yy, xx = np.mgrid[:2 * OR + 1, :2 * OR + 1]
cyanish = (org[..., 2].astype(int) + org[..., 1] - 2 * org[..., 0].astype(int)) > 80
org[~cyanish] = 0
hot = org.copy(); hot[..., :3] = np.clip(hot[..., :3].astype(int) + [60, 60, 40], 0, 255).astype(np.uint8); hot[~cyanish] = 0
def crack(img, n, seed):
    rr = random.Random(seed); o = img.copy(); D = 2 * OR + 1
    for _ in range(n):
        x, y = rr.randint(OR - 3, OR + 3), rr.randint(OR - 3, OR + 3)
        for _ in range(rr.randint(5, 9)):
            if 0 <= x < D and 0 <= y < D and o[y, x, 3]: o[y, x, :3] = (0x10, 0x10, 0x1c)
            if 0 <= x + 1 < D and 0 <= y < D and o[y, x + 1, 3] and rr.random() < 0.4: o[y, x + 1, :3] = (0xe8, 0xff, 0xff)
            x += rr.choice([-1, 0, 1]); y += rr.choice([-1, 1])
    return o
def whitecore(img):
    o = img.copy(); c = OR
    o[c - 1:c + 2, c - 1:c + 2, :3] = (0xa8, 0xff, 0xf4); o[c - 1:c + 2, c - 1:c + 2, 3] = 255
    o[c, c, :3] = (255, 255, 255); return o
sheet([whitecore(f) for f in (org, hot, crack(org, 2, 3), crack(hot, 2, 3), crack(crack(org, 2, 3), 3, 9), crack(crack(hot, 2, 3), 3, 9))], O + 'b3-organ.png')

# ---- canisters: cut from the body frame; broken variant = dark, drained, cracked
def can_box(a, cx, cy, w=16, h=22):
    x0, y0 = cx - w // 2, cy - h // 2; return (x0, y0, x0 + w, y0 + h)
cans = []
for (hx, hy) in ((650, 215), (760, 320)):
    cx, cy = g(hx, hy); bx = can_box(f0, cx, cy)
    c = f0[bx[1]:bx[3], bx[0]:bx[2]].copy()
    br = c.copy(); cy_m = (br[..., 1].astype(int) + br[..., 2] - 2 * br[..., 0].astype(int)) > 60
    br[cy_m, :3] = (0x14, 0x22, 0x28)
    for k in range(10): br[random.randrange(2, 20), random.randrange(2, 14), :3] = (0xa8, 0xff, 0xf4)
    cans.append((bx, c, br))
sheet([cans[0][1], cans[0][2], cans[1][1], cans[1][2]], O + 'b3-cans.png')

# ---- specimen window: steel frame + hard-dithered teal glass with 4 crack stages
GW, GHt = 172, 118
def window_frame():
    a = np.zeros((GHt + 16, GW + 12, 4), np.uint8); h, w = a.shape[:2]
    ST = [H('16151c'), H('262630'), H('3a3b46'), H('555864'), H('7a7f8c'), H('a6abb6')]
    def rect(x0, y0, x1, y1, c): a[y0:y1 + 1, x0:x1 + 1] = (*c, 255)
    rect(0, 0, w - 1, h - 1, OUT)
    rect(1, 1, w - 2, 9, ST[2]); rect(1, 1, w - 2, 1, ST[4]); rect(1, 9, w - 2, 9, ST[0])        # header
    rect(1, h - 7, w - 2, h - 2, ST[2]); rect(1, h - 7, w - 2, h - 7, ST[4]); rect(1, h - 2, w - 2, h - 2, ST[0])   # sill
    rect(1, 10, 5, h - 8, ST[3]); rect(w - 6, 10, w - 2, h - 8, ST[1]); rect(5, 10, 5, h - 8, ST[0]); rect(w - 6, 10, w - 6, h - 8, ST[0])
    for x in range(8, w - 8, 12): a[5, x] = (*ST[5], 255); a[h - 4, x] = (*ST[5], 255)
    for x in range(1, w - 1):                                # hazard band on the sill
        c = H('e8b632') if ((x // 3) % 2 == 0) else ST[0]; a[h - 5, x] = (*c, 255)
    a[11:h - 7, 6:w - 6] = 0                                 # the glass opening
    return a
Image.fromarray(window_frame()).save(O + 'b3-window.png')

def glass(stage):
    a = np.zeros((GHt, GW, 4), np.uint8)
    hi, mid = H('bffff6'), H('46dcd8')
    for (x0, L, wd) in ((6, 18, 2), (12, 10, 1)):     # two short corner glints only (never across her body)
        for i in range(L):
            for k in range(wd):
                x, y = x0 + i // 2 + k, 6 + i
                if 0 <= x < GW and y < GHt: a[y, x] = (*(hi if k == 0 else mid), 255)
    for x in range(GW): a[0, x] = (*mid, 255); a[GHt - 1, x] = (*H('13727a'), 255)   # solid glass edge
    rr = random.Random(21)
    hits = [(60, 55), (112, 75), (86, 28), (40, 90)]
    ink, lit = H('0a1a20'), H('d8fffa')
    for k in range(stage):
        x0, y0 = hits[k]
        for arm in range(5 + 2 * k):
            x, y = float(x0), float(y0); ang = arm * math.tau / (5 + 2 * k) + rr.uniform(-0.3, 0.3); L = rr.randint(16, 32 + 8 * k)
            for i in range(L):
                ang += rr.uniform(-0.12, 0.12); x += math.cos(ang); y += math.sin(ang)
                xi, yi = int(round(x)), int(round(y))
                if 0 <= xi < GW and 0 <= yi < GHt: a[yi, xi] = (*ink, 255)
                if 0 <= xi < GW and 0 <= yi - 1 < GHt and a[yi - 1, xi, 3] == 0: a[yi - 1, xi] = (*lit, 255)   # 1px lit lip
        a[y0 - 2:y0 + 3, x0 - 2:x0 + 3] = (*ink, 255); a[y0 - 1:y0 + 2, x0 - 1:x0 + 2] = (*H('13727a'), 255)
    return a
sheet([glass(k) for k in range(4)], O + 'b3-glass.png')

# ---- small procedural sprites
def acid(k):
    a = np.zeros((8, 8, 4), np.uint8); cols = [H('2f5020'), H('4c7a2a'), H('78a83a'), H('b0e060')]
    for y in range(8):
        for x in range(8):
            d = (x - 3.5) ** 2 + (y - 3.5 - (0.5 if k else 0)) ** 2
            if d < 12: a[y, x] = (*cols[0 if d > 8 else 1 if d > 4 else 2], 255)
    a[2, 3] = (*cols[3], 255); a[2, 4 - k] = (*cols[3], 255)
    return outline(pad(a))
sheet([acid(0), acid(1)], O + 'b3-acid.png')

def bolt(k):
    a = np.zeros((6, 16, 4), np.uint8); c = [H('13727a'), H('46dcd8'), H('a8fff4'), H('ffffff')]
    a[1:5, 2:15] = (*c[0], 255); a[2:4, 1:16] = (*c[1], 255); a[2:4, 4:14 - k * 2] = (*c[2], 255); a[2:4, 1:4] = (*c[3], 255)
    return a
sheet([bolt(0), bolt(1)], O + 'b3-bolt.png')

def charge(k):
    s = 5 + 4 * k; a = np.zeros((s, s, 4), np.uint8); c = s // 2
    ring = [H('13727a'), H('46dcd8'), H('a8fff4')]
    for y in range(s):
        for x in range(s):
            d = abs(x - c) + abs(y - c)
            if d <= c: a[y, x] = (*ring[0 if d == c else 1 if d > c // 2 else 2], 255)
    b = np.zeros((13, 13, 4), np.uint8); o = (13 - s) // 2; b[o:o + s, o:o + s] = a
    return b
sheet([charge(k) for k in range(3)], O + 'b3-charge.png')

def needle(k):
    a = np.zeros((4, 10, 4), np.uint8)
    a[1:3, 1:9] = (*H('dcd2bd'), 255); a[1, 1:4] = (*H('f0ead8'), 255); a[1:3, 0] = (*H('b07ab4'), 255); a[1:3, 9] = (*H('6c3a75'), 255)
    return a
sheet([needle(0)], O + 'b3-needle.png')

def shard(k):
    a = np.zeros((6, 6, 4), np.uint8); rr = random.Random(k)
    pts = [(rr.randrange(0, 6), rr.randrange(0, 6)) for _ in range(3)]
    for y in range(6):
        for x in range(6):
            if sum(1 for (px, py) in pts if abs(px - x) + abs(py - y) <= 2) >= 2: a[y, x] = (*(H('a8fff4') if (x + y) % 3 else H('46dcd8')), 255)
    return a
sheet([shard(k) for k in range(8)], O + 'b3-shards.png')

hm = frames[1]; ch = []
for i in range(8):
    while True:
        cx, cy = random.randint(10, FW - 10), random.randint(10, FH - 10)
        sub = hm[cy - 4:cy + 5, cx - 4:cx + 5].copy()
        if (sub[..., 3] > 0).all(): break
    yy, xx = np.mgrid[:9, :9]; ang = np.arctan2(yy - 4, xx - 4); rr = 2.4 + random.random() * 1.2 + np.sin(ang * 3 + i) * 0.9
    sub[(xx - 4) ** 2 + (yy - 4) ** 2 > rr ** 2] = 0; ch.append(outline(sub))
sheet(ch, O + 'b3-chunks.png')

print('FRAME', FW, FH)
print('CANNON size', cimg.shape[1], cimg.shape[0], 'at', g(CB[0], CB[1]), 'muzzle', muzzle)
print('TAIL cell', CELLT, 'root', g(*ROOT), 'tip', round(tipx, 1), round(tipy, 1), 'angles', TA)
print('ORGAN', [g(*o) for o in org_hi], 'r', OR)
print('CANS', [(c[0][0], c[0][1]) for c in cans], 'size 16x22')
print('WINDOW', GW + 12, GHt + 16, 'glass', GW, GHt)

# hot-white lens centre on the cannon (the beam's source reads as a target)
_a = np.array(Image.open(O + 'b3-cannon.png').convert('RGBA'))
_c = (_a[..., 2].astype(int) + _a[..., 1] - 2 * _a[..., 0].astype(int) > 120) & (_a[..., 3] > 0)
_ys, _xs = np.where(_c[:, :10]); _cx, _cy = int(round(_xs.mean())), int(round(_ys.mean()))
_a[_cy - 2:_cy + 3, _cx - 1:_cx + 2, :3] = (0xa8, 0xff, 0xf4); _a[_cy - 1:_cy + 2, _cx - 1:_cx + 1, :3] = (255, 255, 255)
Image.fromarray(_a).save(O + 'b3-cannon.png')
