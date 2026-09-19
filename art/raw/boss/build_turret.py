"""Wool-shredder gatling pods for the Iron Eagle Gate - hard-surface rebuild (round 6).
Two parts so the pod reads at 1x from any angle:
  boss-gun-house.png  26x22 x 3 frames [normal, eye-hot, wreck]: boxy armoured mount, hand-placed pixels,
                      lit top plane / mid front / dark underside, hazard band, twin hard-pixel red eyes, barrel collar.
                      Never rotates. Pivot = cell centre (sits on the facade socket).
  boss-gun-barrel.png 56x56 cells, rows = 3 spin phases, cols = 12 aim angles (-10..45 step 5, + = down-left).
                      Triple barrel cluster + dark muzzle block, drawn big, rotated, downsampled, then hard-snapped
                      to a 7-colour steel ramp (no soft edges). Pivot = cell centre = the collar on the house.
python art/raw/boss/build_turret.py"""
import numpy as np
from PIL import Image, ImageDraw
O = 'assets/boss/'
H = lambda s: tuple(int(s[i:i + 2], 16) for i in (0, 2, 4))
OUT = H('1a1420'); BORE = H('07050a')
ST = [H('1f1e27'), H('34353f'), H('4f525d'), H('737884'), H('a3a8b3'), H('dde1e8')]   # steel ramp dark -> light
YEL, YEL2 = H('e8b632'), H('8a6a1c')
RED0, RED1, RED2, HOT = H('6e0e10'), H('c81c16'), H('ff4a26'), H('fff0c0')

# ------------------------------------------------------------------ housing (26x22), drawn pixel by pixel
def house(eye_hot=False, wreck=False):
    W, Hh = 26, 22
    a = np.zeros((Hh, W, 4), np.uint8)
    def px(x, y, c): a[y, x] = (*c, 255)
    def rect(x0, y0, x1, y1, c):
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1): px(x, y, c)
    # main armoured box x 6..24, y 3..19 (chamfered top-right)
    rect(6, 4, 24, 19, ST[2])                 # mid front
    rect(6, 4, 24, 5, ST[4]); rect(7, 3, 23, 3, ST[5])       # lit top plane
    rect(6, 16, 24, 19, ST[1]); rect(6, 19, 24, 19, ST[0])   # dark underside
    for x in range(6, 25):                    # hazard band on the underside
        if ((x + 16) // 2) % 2 == 0: px(x, 16, YEL); px(x, 17, YEL2)
        else: px(x, 16, ST[0]); px(x, 17, ST[0])
    rect(15, 6, 15, 15, ST[1]); rect(16, 6, 16, 15, ST[3])   # panel seam with lit edge
    rect(24, 4, 24, 18, ST[1])                # shaded right side
    for (x, y) in ((8, 7), (8, 13), (22, 13), (13, 13)): px(x, y, ST[4]); px(x, y + 1, ST[0])   # bolts
    # sensor hood + twin eyes
    rect(17, 6, 23, 10, ST[1]); rect(17, 6, 23, 6, ST[3])
    for ex in (18, 21):
        if eye_hot:
            rect(ex - 1, 7, ex + 2, 10, RED1); rect(ex, 8, ex + 1, 9, HOT)
        else:
            rect(ex, 8, ex + 1, 9, RED1); px(ex, 8, RED2)
    if wreck:
        rect(17, 7, 23, 10, ST[0])
    # top hatch
    rect(10, 1, 15, 2, ST[3]); rect(10, 1, 15, 1, ST[4])
    # barrel collar (left): round-ish ring the barrel cluster pivots in
    for y in range(6, 17):
        for x in range(0, 9):
            dx, dy = (x - 4.5) / 4.6, (y - 11) / 5.6
            if dx * dx + dy * dy <= 1: px(x, y, ST[1])
    rect(1, 7, 7, 7, ST[4]); rect(2, 6, 6, 6, ST[4])     # lit top rim of the collar
    rect(1, 15, 7, 16, ST[0])
    rect(3, 9, 6, 13, ST[0]); rect(4, 10, 5, 12, BORE)  # socket the barrels come out of
    if wreck:
        a[..., :3] = (a[..., :3] * 0.55).astype(np.uint8)
        for (x, y) in ((9, 5), (10, 6), (11, 5), (19, 14), (20, 15), (12, 10), (13, 11)): px(x, y, OUT)
    # 1px outline
    m = a[..., 3] > 0; n = np.zeros_like(m)
    n[1:] |= m[:-1]; n[:-1] |= m[1:]; n[:, 1:] |= m[:, :-1]; n[:, :-1] |= m[:, 1:]
    b = np.zeros((Hh + 2, W + 2, 4), np.uint8); b[1:-1, 1:-1] = a
    mm = b[..., 3] > 0; nn = np.zeros_like(mm)
    nn[1:] |= mm[:-1]; nn[:-1] |= mm[1:]; nn[:, 1:] |= mm[:, :-1]; nn[:, :-1] |= mm[:, 1:]
    b[nn & ~mm] = (*OUT, 255)
    return b                                   # 28x24 with outline


houses = [house(), house(eye_hot=True), house(wreck=True)]
Image.fromarray(np.concatenate(houses, 1)).save(O + 'boss-gun-house.png')
HW, HH = houses[0].shape[1], houses[0].shape[0]

# ------------------------------------------------------------------ barrel cluster
K = 8; CELL = 56; BIG = CELL * K; C = BIG // 2
ANG = list(range(-10, 46, 5))                 # 12 angles


def R(g, x0, y0, x1, y1, col):              # game-px rect relative to pivot, inclusive
    g.rectangle([C + x0 * K, C + y0 * K, C + (x1 + 1) * K - 1, C + (y1 + 1) * K - 1], fill=(*col, 255))


def barrel(ang, spin):
    cv = Image.new('RGBA', (BIG, BIG), (0, 0, 0, 0)); g = ImageDraw.Draw(cv)
    R(g, -27, -5, 1, 5, OUT)                  # cluster silhouette with outline
    shades = [[4, 3, 2], [3, 2, 4], [2, 4, 3]][spin]
    for i, y in enumerate((-4, -1, 2)):
        s = shades[i]
        R(g, -26, y, 0, y + 1, ST[s]); R(g, -26, y, 0, y, ST[min(5, s + 1)])
        if i < 2: R(g, -26, y + 2, 0, y + 2, ST[0])
        gx = -24 + ((spin * 6 + i * 7) % 20); R(g, gx, y, gx + 1, y, ST[5])   # spin glint
    for cx in (-18, -9):                      # clamps
        R(g, cx - 1, -5, cx + 1, 5, OUT); R(g, cx, -5, cx, 5, ST[4]); R(g, cx + 1, -4, cx + 1, 4, ST[2])
    R(g, -32, -6, -27, 6, OUT)                # muzzle block
    R(g, -31, -5, -28, 5, ST[1]); R(g, -31, -5, -28, -5, ST[4]); R(g, -31, 4, -28, 5, ST[0])
    for y in (-4, -1, 2): R(g, -32, y, -30, y + 1, BORE)
    cv = cv.rotate(ang, resample=Image.NEAREST, center=(C, C))
    s = np.array(cv.resize((CELL, CELL), Image.BOX)).astype(np.float32)
    al = s[..., 3] / 255; col = np.where(al[..., None] > 0.01, s[..., :3] / np.maximum(al[..., None], 0.01), 0)
    pal = np.array([OUT, BORE] + ST, np.float32)
    idx = ((col[:, :, None, :] - pal[None, None]) ** 2).sum(-1).argmin(-1)
    o = np.zeros((CELL, CELL, 4), np.uint8); o[..., :3] = pal[idx].astype(np.uint8); o[..., 3] = np.where(al >= 0.5, 255, 0)
    o[o[..., 3] == 0] = 0
    return o


sheet = np.concatenate([np.concatenate([barrel(a, s) for a in ANG], 1) for s in range(3)], 0)
Image.fromarray(sheet).save(O + 'boss-gun-barrel.png')

# ------------------------------------------------------------------ hard-stepped lamps (replace additive glows)
def lamp(core, ring, on):
    a = np.zeros((7, 7, 4), np.uint8)
    if on:
        for y in range(7):
            for x in range(7):
                d = abs(x - 3) + abs(y - 3)
                if d <= 3 and not (abs(x - 3) == 3 or abs(y - 3) == 3): a[y, x] = (*ring, 255)
        a[2:5, 2:5] = (*core, 255); a[3, 3] = (*HOT, 255)
        a[3, 0] = a[3, 6] = a[0, 3] = a[6, 3] = (*ring, 255)
    else:
        a[2:5, 2:5] = (*ring, 255); a[3, 3] = (*core, 255)
    return a


lamps = [lamp(RED1, RED0, False), lamp(RED2, RED1, True), lamp(H('d88a2a'), H('7a4a14'), False), lamp(H('ffd070'), H('d88a2a'), True)]
Image.fromarray(np.concatenate(lamps, 1)).save(O + 'boss-lamp.png')
print('gun house', HW, HH, 'barrel cells', CELL, 'x', len(ANG), 'x 3 spin, lamps 7x7 x4')


# ------------------------------------------------------------------ low "intake cannon" (phase-1 weak point in the standing/prone shot line)
def lowgun(state):   # 0 shut, 1 open (tell / firing), 2 wreck
    W, Hh = 26, 34
    a = np.zeros((Hh, W, 4), np.uint8)
    def px(x, y, c): a[y, x] = (*c, 255)
    def rect(x0, y0, x1, y1, c):
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1): px(x, y, c)
    # sloped armour block
    for y in range(2, 34):
        x0 = max(4, 12 - y) if y < 10 else 4
        rect(x0, y, 25, y, ST[2])
    for y in range(2, 10): px(max(4, 12 - y), y, ST[5]); px(max(4, 12 - y) + 1, y, ST[4])   # lit slope edge
    rect(12, 2, 25, 2, ST[5]); rect(12, 3, 25, 3, ST[4])          # lit top plane
    rect(4, 28, 25, 33, ST[1]); rect(4, 33, 25, 33, ST[0])        # dark foot
    for x in range(4, 26):                                        # hazard band
        c = YEL if ((x // 2) % 2 == 0) else ST[0]; px(x, 28, c); px(x, 29, YEL2 if c == YEL else ST[0])
    rect(25, 4, 25, 27, ST[1]); rect(15, 20, 15, 26, ST[1]); rect(16, 20, 16, 26, ST[3])
    for (x, y) in ((7, 24), (22, 24), (22, 6)): px(x, y, ST[4]); px(x, y + 1, ST[0])
    # red eye in a hood (top)
    rect(15, 5, 22, 9, ST[1]); rect(15, 5, 22, 5, ST[3])
    hot = state == 1
    rect(17, 6, 20, 8, RED1 if hot else RED0); rect(18, 7, 19, 7, HOT if hot else RED1)
    # gun port centred on local y 17 (world ground-24 when the block sits on the ground)
    if state == 0:
        rect(0, 12, 12, 21, OUT); rect(1, 13, 11, 20, ST[1]); rect(1, 13, 11, 13, ST[3])
        for y in (15, 17, 19): rect(2, y, 10, y, ST[0])          # closed shutter slats
    elif state == 1:
        rect(0, 12, 13, 21, OUT); rect(1, 13, 12, 20, ST[0])      # open port
        rect(0, 14, 10, 19, ST[3]); rect(0, 14, 10, 14, ST[5]); rect(0, 19, 10, 19, ST[1])   # stubby cannon
        rect(0, 15, 2, 18, BORE)
    if state == 2:
        rect(0, 12, 12, 21, OUT); rect(1, 13, 11, 20, BORE)
        a[..., :3] = (a[..., :3] * 0.55).astype(np.uint8)
        for (x, y) in ((6, 6), (7, 7), (8, 6), (20, 14), (21, 15), (12, 25), (13, 24)): px(x, y, OUT)
    m = a[..., 3] > 0
    b = np.zeros((Hh + 2, W + 2, 4), np.uint8); b[1:-1, 1:-1] = a
    mm = b[..., 3] > 0; nn = np.zeros_like(mm)
    nn[1:] |= mm[:-1]; nn[:-1] |= mm[1:]; nn[:, 1:] |= mm[:, :-1]; nn[:, :-1] |= mm[:, 1:]
    b[nn & ~mm] = (*OUT, 255)
    return b                                   # 28x36


Image.fromarray(np.concatenate([lowgun(i) for i in range(3)], 1)).save(O + 'boss-gun-low.png')


# ------------------------------------------------------------------ armour ricochet "tink" (grey, hard pixels), 7x7 x 3
def tink(k):
    a = np.zeros((7, 7, 4), np.uint8); G = [ST[5], ST[4], ST[3]][k]
    if k == 0:
        for d in range(-3, 4): a[3, 3 + d] = (*G, 255); a[3 + d, 3] = (*G, 255)
        a[3, 3] = (255, 255, 255, 255)
    elif k == 1:
        for d in (-2, -1, 1, 2): a[3 + d, 3 + d] = (*G, 255); a[3 + d, 3 - d] = (*G, 255)
    else:
        for (x, y) in ((1, 1), (5, 1), (1, 5), (5, 5)): a[y, x] = (*G, 255)
    return a


Image.fromarray(np.concatenate([tink(i) for i in range(3)], 1)).save(O + 'boss-tink.png')
print('low gun 28x36 x3, tink 7x7 x3')
