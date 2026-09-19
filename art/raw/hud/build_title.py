# Builds the layered 480x270 title screen from the generated raws (title_bg_1, logo_2, sheep_rock_2, heli).
# run from repo root: python art/raw/hud/build_title.py
import sys, numpy as np
sys.path.insert(0, 'art/raw/hud')
from px import plate, sprite
from PIL import Image

R, O = 'art/raw/hud/', 'assets/hud/'
plate(R + 'title_bg_1.png', O + 'title-bg.png', 480, 270, 200)
sprite(R + 'logo_2.png', O + 'title-logo.png', w=234, colors=48)
SH_H = 228; SK = SH_H / 214.0                  # hero scale (layout numbers below were measured at h=214)
sprite(R + 'sheep_rock_2.png', O + 'title-sheep.png', h=SH_H, colors=48)
sprite(R + 'heli.png', R + 'heli_px.png', w=60, colors=16)

# darker falloff behind the hero, painted into the plate with HARD value steps: a silhouetted jungle ridge
# (2 flat dark tones that keep the plate's shapes) and a dimmer mist band above it. No dither, no alpha.
pl = np.array(Image.open(O + 'title-bg.png').convert('RGB')).astype(float)
rng = np.random.default_rng(7)
X = np.arange(480)
def ridge(top, rx, bump, spikes):
    # rounded hill silhouette (elliptical dome) whose crest is broken up by blocky treetops and a few palm spikes
    cy = top + 150
    dx = np.clip(np.abs(X - 240) / rx, 0, 1)
    r = cy - 150 * np.sqrt(1 - dx ** 2)
    r = r + np.repeat(rng.integers(-bump, bump + 1, 480 // 5 + 1), 5)[:480]
    for _ in range(spikes):
        c = int(rng.integers(150, 330)); w = int(rng.integers(2, 4)); hgt = int(rng.integers(5, 11))
        r[c - w:c + w] -= hgt; r[c - w - 2:c - w] -= hgt // 2; r[c + w:c + w + 2] -= hgt // 2
    r[np.abs(X - 240) >= rx] = 999
    return r.astype(int)
r1 = ridge(156, 150, 2, 6)
r2 = ridge(134, 190, 2, 0)
yy_ = np.arange(270)[:, None]
lumbg = pl.mean(-1)
sil = yy_ >= r1[None, :]
mist = (yy_ >= r2[None, :]) & ~sil
pl[mist] = pl[mist] * 0.7
pl[sil] = pl[sil] * 0.42 + np.array([4, 6, 14])        # one hard value step down, plate texture kept
edge_ = sil & ~np.roll(sil, 1, 0)
pl[edge_] = pl[edge_] * 0.6                                                      # 1px rim on the ridge top
Image.fromarray(pl.astype(np.uint8)).save(O + 'title-bg.png')

# fire layer: the hot pixels of the plate, used additively to make the burning base flicker
bg = np.array(Image.open(O + 'title-bg.png').convert('RGB')).astype(int)
r, g, b = bg[..., 0], bg[..., 1], bg[..., 2]
hot = (r > 190) & (r - b > 110) & (g > 70)
fire = np.zeros((270, 480, 4), np.uint8)
fire[hot, :3] = np.clip(bg[hot] * [1.0, 0.85, 0.6], 0, 255).astype(np.uint8); fire[hot, 3] = 255
Image.fromarray(fire).save(O + 'title-fire.png')

# helicopter: 2 frames (long rotor / short foreshortened rotor)
h = np.array(Image.open(R + 'heli_px.png').convert('RGBA'))
H, W = h.shape[:2]
f2 = h.copy()
row = 1
xs = np.where(h[row, :, 3] > 0)[0]
cx = 24
f2[row, :, 3] = 0
f2[row, cx - 9:cx + 10] = h[row, xs.min() + 5]
# tail rotor flicker: drop some tail pixels in frame 2
f2[2:10, 52:60, 3] = np.where((np.arange(8)[:, None] + np.arange(8)[None, :]) % 2 == 0, f2[2:10, 52:60, 3], 0)
sheet = np.concatenate([h, f2], 1)
Image.fromarray(sheet).save(O + 'title-heli.png')
print('heli frame', W, H)

# brighten the helicopter a touch so it reads against the night sky (rim light from fires / beams)
hs = np.array(Image.open(O + 'title-heli.png')).astype(int)
hs[..., :3] = np.clip(hs[..., :3] * 1.35 + 14, 0, 255)
Image.fromarray(hs.astype(np.uint8)).save(O + 'title-heli.png')

# ---- fire rim light on the hero: the burning base is to the right, so the right-facing edges of wool/gun/ribbon
# get a hot orange rim, the left side falls into a cool shadow, and the rock top catches the glow + a contact shadow.
sh = np.array(Image.open(O + 'title-sheep.png')).astype(float)
a = sh[..., 3] > 0
Hh, Ww = a.shape
ys, xs = np.mgrid[0:Hh, 0:Ww]
rock_top = int(Hh * 0.655)                      # rows below this are the rock
def empty(dx, dy):
    m = np.zeros_like(a)
    sy = slice(max(0, -dy), Hh - max(0, dy)); ty = slice(max(0, dy), Hh - max(0, -dy))
    sx = slice(max(0, -dx), Ww - max(0, dx)); tx = slice(max(0, dx), Ww - max(0, -dx))
    m[sy, sx] = ~a[ty, tx]
    return m
def mix(mask, col, k):
    sh[mask, :3] = sh[mask, :3] * (1 - k) + np.array(col) * k
HOOVES = [(round(38 * SK), round(61 * SK)), (round(105 * SK), round(131 * SK))]                 # x-ranges of the two hooves (they dip below the rock line)
hoof = np.zeros_like(a)
for x0_, x1_ in HOOVES: hoof |= (xs >= x0_) & (xs < x1_) & (ys >= round(126 * SK)) & (ys <= round(143 * SK))
body = a & ((ys < round(130 * SK)) | hoof)
lum = sh[..., :3].mean(-1)
# overall: warm right half, cool/dim left half (gradient across the sprite)
gx = xs / Ww
warm = body & (gx > 0.45)
sh[body, :3] *= (0.94 + 0.1 * gx[body])[:, None]
# wool: bright, saturated cream (the ref's hero pops off the dark jungle)
rgbv = sh[..., :3]; mx = rgbv.max(-1); mn = rgbv.min(-1)
woolish = body & (lum > 110) & ((rgbv[..., 0] - rgbv[..., 2]) > 22) & ((mx - mn) < 120) & (rgbv[..., 1] > 90)
hi = woolish & (lum > 175); mid = woolish & ~hi
# remap fleece by value onto a bright cream ramp so it is the brightest thing under the logo
RAMP = np.array([(176, 112, 60), (226, 170, 96), (252, 214, 138), (255, 246, 222), (255, 253, 244)], float)   # wider value range = rounder wool
wl = lum[woolish]
q = np.clip(np.searchsorted(np.quantile(wl, [0.1, 0.28, 0.5, 0.74]), wl), 0, 4)
sh[woolish, :3] = RAMP[q]
mix(warm & ~woolish, (255, 150, 60), 0.05)
# grey face/legs a touch darker so the near-white wool reads against them
greyish = body & ~woolish & ((mx - mn) < 40) & (lum > 60)
sh[greyish, :3] *= 0.86
# brass bandolier gleam: one bright highlight pixel at each cartridge's local brightest spot
r_, g_, b_ = rgbv[..., 0], rgbv[..., 1], rgbv[..., 2]
brass = body & (r_ > 120) & (g_ > 70) & (b_ < 90) & ((r_ - b_) > 80) & ~woolish
L2 = sh[..., :3].mean(-1)
from scipy.ndimage import maximum_filter
peak = brass & (L2 >= maximum_filter(np.where(brass, L2, 0), size=3)) & (L2 > 120)
sh[peak, :3] = (255, 248, 196)
cool = body & (gx < 0.5) & ~woolish
mix(cool, (40, 50, 110), 0.15)
# backlit silhouette: the outer outline pixel becomes hot orange (strongest facing the fire on the right),
# the next pixels in pick up a yellow-orange rim; left-facing interior falls into a cool shadow.
edge = body & (empty(1, 0) | empty(-1, 0) | empty(0, 1) | empty(0, -1))
inner = np.zeros_like(a); inner[1:-1, 1:-1] = True
e2 = body & ~edge & (empty(2, 0) | empty(-2, 0) | empty(0, -2) | empty(1, -1) | empty(-1, -1) | empty(1, 1) | empty(-1, 1))
e3 = body & ~edge & ~e2 & (empty(3, 0) | empty(2, -1) | empty(0, -3))
right = gx >= 0.42
facing_r = empty(1, 0) | empty(2, 0) | empty(1, -1) | empty(2, -1) | empty(3, 0)
# firm 1px dark outline all round (sheep, gun, ribbon); the fire rim sits just inside it
sh[edge, :3] = (22, 12, 16)
e4 = body & ~edge & ~e2 & ~e3 & (empty(4, 0) | empty(3, -1) | empty(4, -1))
fr3 = empty(1, 0) | empty(2, 0) | empty(3, 0) | empty(4, 0) | empty(1, -1) | empty(2, -1) | empty(3, -1)
sh[(e2 | e3) & facing_r, :3] = (255, 118, 18)     # solid 3px hot-orange fire rim just inside the outline
sh[e4 & fr3 & (gx > 0.35), :3] = (255, 176, 60)    # 3rd, lighter band blends the rim into the wool
mix(e2 & ~facing_r, (240, 130, 50), 0.7)
# cool shadow on the left-facing interior
s2 = body & ~edge & ~e2 & (empty(-3, 0) | empty(-4, 0) | empty(-5, 0)) & (gx < 0.6)
mix(s2, (40, 36, 80), 0.3)
# rock: lit top surface following its contour, hard contact shadow under each hoof, dark flanks
rock = a & ~body
top = np.full(Ww, Hh, int)
for x in range(Ww):
    r = np.where(rock[:, x])[0]
    if len(r): top[x] = r.min()
depth = ys - top[None, :]
sh[rock, :3] *= 0.72
sh[rock & (gx < 0.35), :3] *= 0.85
rt = rock & (depth <= 4)
sh[rt, :3] = np.minimum(255, sh[rt, :3] * 1.5); mix(rt, (235, 125, 50), 0.3)
rim = rock & (depth == 0)
mix(rim, (255, 170, 70), 0.85)
rim2 = rock & (depth == 1)
mix(rim2, (220, 110, 40), 0.5)
feet = round(143 * SK)
for x0_, x1_ in HOOVES:
    sm = rock & (xs >= x0_ - 3) & (xs < x1_ + 3) & (ys >= feet - 1) & (ys <= feet + 2)
    sh[sm, :3] = (16, 10, 14)
# re-quantise so the result stays a tidy palette
out = np.clip(sh, 0, 255).astype(np.uint8)
rgb = Image.fromarray(out[..., :3]).quantize(colors=200, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE).convert('RGB')
out[..., :3] = np.array(rgb)
Image.fromarray(out).save(O + 'title-sheep.png')
print('sheep lit, feet row', feet)
