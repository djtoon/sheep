"""Stage-2 boss art: B-02 WARDEN walker mech (from ref/levels/level2 boss.png via gen.mjs edits).
python art/raw/boss2/build_boss2.py -> assets/boss2/*.png ; prints the layout numbers Boss2.js uses."""
import sys, math, random
import numpy as np
from PIL import Image, ImageDraw
sys.path.insert(0, 'art/raw/boss2')
from kit import load, to_game, clean, outline, pad, rotate_hi, sheet, down, smooth, H, OUT, pop, outline2, gray, flatten
R = 'art/raw/boss2/'; O = 'assets/boss2/'
random.seed(3)
S = 6.5; BOX = (10, 20, 1020, 990)                     # hi-res window shared by every body frame
W, Hh = round((BOX[2] - BOX[0]) / S), round((BOX[3] - BOX[1]) / S)
g = lambda x, y: (round((x - BOX[0]) / S) + 2, round((y - BOX[1]) / S) + 2)   # hi-res -> padded frame px (2px outline)
POP = dict(rim=H('e8b868'), rim_mats=('olive', 'concrete', 'yellow'), lift=('olive',), darken=('steel',))

stand, crouch, cdmg, ref = (load(R + f) for f in ('stand.png', 'crouch.png', 'crouch_dmg.png', 'ref_cut.png'))
frames = [outline2(flatten(pop(to_game(a, BOX, S), **POP), tones=(3, 4, 5))) for a in (stand, crouch, cdmg)]
# HUD clearance: with the 3px sink the frame top sits at y=19; the weapon box ends at y=24, so trim the pod lid,
# antenna and anything else above frame row 8 (screen y>=27) and re-close the outline on the cut
TRIM = 8
for f in frames:
    f[:TRIM] = 0
    row = f[TRIM]; op = row[..., 3] > 0; row[op, :3] = OUT
sheet(frames, O + 'b2-body.png')
FW, FH = frames[0].shape[1], frames[0].shape[0]

# ---- gatling arm: pixels the reproduction has and the gun-less edit lacks, left of the shoulder
x0, y0, x1, y1 = 10, 300, 480, 610
diff = np.abs(ref[..., :3] - stand[..., :3]).sum(-1)
m = (ref[..., 3] > 0) & ((stand[..., 3] == 0) | (diff > 0.35))
box = np.zeros_like(m); box[y0:y1, x0:x1] = True; m &= box
from scipy import ndimage
m = ndimage.binary_closing(m, iterations=3); m = ndimage.binary_fill_holes(m); m = ndimage.binary_opening(m, iterations=2)
lab, n = ndimage.label(m); sizes = ndimage.sum(m, lab, range(1, n + 1)); m = lab == (np.argmax(sizes) + 1)
gun = ref.copy(); gun[~m] = 0
ys, xs = np.where(m); GX0, GX1, GY0, GY1 = xs.min(), xs.max(), ys.min(), ys.max()
PIV = (GX1 - 18, (GY0 + GY1) // 2 - 10)                  # shoulder end of the arm
ANG = list(range(-10, 31, 5))
CELL = 150
gcells = []
for a in ANG:
    rot = rotate_hi(gun, PIV, a, int(CELL * S))
    gcells.append(outline(outline(pop(down(smooth(rot), CELL, CELL), **POP))))
sheet(gcells, O + 'b2-gun.png')
tip = (GX0 - PIV[0]) / S                                   # muzzle distance from pivot (game px, negative = left)
bore_y = ((GY0 + GY1) / 2 - 25 - PIV[1]) / S

# ---- warhead overlay (4 red noses) from the reproduction's pod, placed on each frame's empty tubes
WB = (640, 45, 800, 175)
war = ref[WB[1]:WB[3], WB[0]:WB[2]].copy()
red = (war[..., 0] > 0.55) & (war[..., 1] < 0.45) | ((war[..., 0] > 0.75) & (war[..., 1] > 0.75) & (war[..., 2] > 0.75))
war[..., 3] = np.where(red, 1, 0)
wimg = down(war, round((WB[2] - WB[0]) / S), round((WB[3] - WB[1]) / S))
Image.fromarray(outline(pad(clean(wimg)))).save(O + 'b2-warheads.png')


def match(src, dst, win, search):
    """offset (dx,dy) that best maps src[win] onto dst within +-search (grey SSD on a coarse grid)"""
    xa, ya, xb, yb = win
    p = src[ya:yb, xa:xb, :3].mean(-1)
    best, bo = 1e18, (0, 0)
    for dy in range(-search, search + 1, 3):
        for dx in range(-search, search + 1, 3):
            q = dst[ya + dy:yb + dy, xa + dx:xb + dx, :3].mean(-1)
            if q.shape != p.shape: continue
            e = ((p - q) ** 2).sum()
            if e < best: best, bo = e, (dx, dy)
    return bo


pod_c = match(stand, crouch, WB, 110)
pod_d = match(stand, cdmg, WB, 110)
core_s = (490, 360)
# core centre per frame: brightest orange blob near the chest
def core_at(a, near):
    x, y = near; sub = a[y - 120:y + 120, x - 120:x + 120]
    score = sub[..., 0] + sub[..., 1] * 0.8 - sub[..., 2] * 1.2
    yy, xx = np.unravel_index(np.argmax(score), score.shape)
    return (x - 120 + xx, y - 120 + yy)
cores = [core_at(stand, core_s), core_at(crouch, (480, 490)), core_at(cdmg, (470, 500))]

# ---- small procedural sprites
def px_sprite(w, h, rows):
    a = np.zeros((h, w, 4), np.uint8)
    for (x, y, c) in rows: a[y, x] = (*c, 255)
    return a

def missile(k):
    a = np.zeros((14, 7, 4), np.uint8)
    body = [H('3a3b46'), H('555864'), H('7a7f8c')]
    for y in range(3, 11):
        for x in range(1, 6): a[y, x] = (*body[0 if x == 5 else 1 if x >= 3 else 2], 255)
    for x in range(2, 5): a[2, x] = (*H('b01e18'), 255)
    a[1, 3] = (*H('e23a20'), 255); a[2, 2] = (*H('ff7a40'), 255)
    a[10, 0] = a[10, 6] = (*H('262630'), 255)
    fl = [H('fff4c8'), H('ffd070')] if k == 0 else [H('ffd070'), H('d88a2a')]
    a[11, 2:5] = (*fl[0], 255); a[12, 3] = (*fl[1], 255)
    if k == 0: a[13, 3] = (*fl[1], 255)
    return outline(pad(a[::-1].copy()))                   # nose down
sheet([missile(0), missile(1)], O + 'b2-missile.png')

def wave(k):
    # ground shockwave: hard-pixel dust arc + debris, 3 frames
    w, h = 26, 16; a = np.zeros((h, w, 4), np.uint8)
    cols = [H('dcd2bd'), H('b9ae9c'), H('948b7e'), H('6f685f')]
    rng = random.Random(k)
    for x in range(w):
        top = int(h - 2 - (h - 4) * math.sin(math.pi * x / (w - 1)) * (0.8 + 0.2 * rng.random()))
        for y in range(top, h):
            d = (y - top)
            a[y, x] = (*cols[min(3, d // 3 + (k if x % 5 == 0 else 0))], 255)
    for _ in range(5):
        x, y = rng.randrange(2, w - 2), rng.randrange(0, 5); a[y, x] = (*cols[2], 255)
    return outline(a)
sheet([wave(i) for i in range(3)], O + 'b2-wave.png')

# chunks cut from the damaged frame
dm = frames[2]; ch = []
for i in range(8):
    while True:
        cx, cy = random.randint(10, FW - 10), random.randint(10, FH - 10)
        sub = dm[cy - 4:cy + 5, cx - 4:cx + 5].copy()
        if (sub[..., 3] > 0).all(): break
    yy, xx = np.mgrid[:9, :9]; ang = np.arctan2(yy - 4, xx - 4); rr = 2.4 + random.random() * 1.2 + np.sin(ang * 3 + i) * 0.9
    sub[(xx - 4) ** 2 + (yy - 4) ** 2 > rr ** 2] = 0; ch.append(outline(sub))
sheet(ch, O + 'b2-chunks.png')

print('FRAME', FW, FH)
print('GUN cell', CELL, 'pivot', g(*PIV), 'tip', round(tip, 1), 'bore', round(bore_y, 1), 'angles', ANG[0], ANG[-1])
print('WAR size', wimg.shape[1] + 2, wimg.shape[0] + 2, 'stand', g(WB[0], WB[1]), 'crouch', g(WB[0] + pod_c[0], WB[1] + pod_c[1]), 'dmg', g(WB[0] + pod_d[0], WB[1] + pod_d[1]))
print('CORE', [g(*c) for c in cores])

foot = []
for f in frames:
    al = f[..., 3] > 0; rows = al[-22:]; xs = np.where(rows.any(0))[0]; foot.append(int(xs.min()))
print('FOOT', foot)
Image.fromarray(gray(frames[0])).save('art/raw/boss2/_gray0.png')

# vent-open reactor: big hard-pixel orange disc, 2 pulse frames
def coredisc(k):
    d = 19; c = d // 2; a = np.zeros((d, d, 4), np.uint8)
    rings = [(9.3, H('3e0c0e')), (8.2, H('b01e18')), (6.8, H('e23a20')), (5.2 + k, H('ff7a40')), (3.4 + k, H('ffd070')), (1.6 + k * 0.6, H('fff4c8'))]
    for r, col in rings:
        for y in range(d):
            for x in range(d):
                if (x - c) ** 2 + (y - c) ** 2 <= r * r: a[y, x] = (*col, 255)
    a[c, c] = (255, 255, 255, 255)
    return outline(pad(a))
sheet([coredisc(0), coredisc(1)], O + 'b2-core.png')
