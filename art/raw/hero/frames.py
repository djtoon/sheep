# Builds every hero animation frame from the AI-native key poses + procedural legs / headband tails / wool bounce.
import sys, math, json; sys.path.insert(0, 'art/raw/hero')
from rast import *
import px as _px; CHARS = _px.CH
CW, CH = 96, 80
OL = IDX['ol']; WOOL = [IDX[k] for k in ('w0', 'w1', 'w2', 'w3')]
RED = [IDX[k] for k in ('r0', 'r1', 'r2')]
def C(n): return IDX[n]
PATCH = {  # hand pixel fixes on the sampled key poses: (row, col0, 'chars')
    'v3fwd_1': [(23, 48, '##'), (24, 47, 'yyyy')],
    'v3up_2':  [(r, 40, '#y#') for r in range(3, 7)],
}
def load(n):
    a = np.load(f'art/raw/hero/s/{n}.npy').astype(np.int16)
    for (r, c, t) in PATCH.get(n, []):
        for i, ch in enumerate(t): a[r, c + i] = -1 if ch == '.' else CHARS.index(ch)
    return a
def blank(h=CH, w=CW): return np.full((h, w), -1, np.int16)
def over(dst, src):
    m = src >= 0; dst[m] = src[m]; return dst

def fix_outline(cv):
    """outline every opaque pixel that touches transparency; drop outline pixels that no longer outline anything"""
    body = (cv >= 0) & (cv != OL)
    cv[dil(body) & (cv < 0)] = OL
    o = cv == OL; cv[o & ~dil(body, True)] = -1
    return cv

def remove_tails(p, x_max):
    """delete headband tails: red pixels left of x_max, then orphaned outline"""
    q = p.copy(); h, w = q.shape
    reg = q[:, :x_max]; reg[np.isin(reg, RED)] = -1
    return fix_outline(q)

def cut_legs(p, y0, x0, x1):
    q = p.copy(); reg = q[y0:, x0:x1]; reg[~np.isin(reg, WOOL)] = -1
    return fix_outline(q)

# ---------------- procedural parts, drawn in cell coordinates ----------------
def leg(cv, hip, foot, back=False):
    h, w = cv.shape; X, Y = grid(h, w)
    fx, fy = foot  # fy = row of the hoof's bottom pixel
    shin = seg(h, w, hip, (fx, fy - 2.5), 2.6)
    hoof = (X >= fx - 3.0) & (X < fx + 4.0) & (Y >= fy - 2.5) & (Y < fy + 1.0)
    m = shin | hoof
    col = np.full((h, w), C('f2' if back else 'f1'), np.int16)
    left = m & ~np.roll(m, 1, 1)
    col[left] = C('f3' if back else 'f2')
    col[hoof] = C('k2'); col[hoof & (X >= fx + 0.5) & (Y < fy - 0.5)] = C('k1')
    img = blank(h, w); img[ring(m)] = OL; img[m] = col[m]
    return over(cv, img)

def tails(cv, knot, t, mode='run', dirx=-1):
    """two flowing headband ribbons from the knot; a travelling wave runs down them each cycle"""
    h, w = cv.shape
    kx, ky = knot
    S = {'run':  [(20, 0.0, 0.22, 1.1, -0.5), (16, 1.3, 0.45, 1.0, 2.6)],
         'idle': [(18, 0.0, 0.25, 0.9, -0.5), (15, 1.3, 0.5, 0.8, 2.6)],
         'fall': [(18, 0.0, 0.05, 1.3, -0.5), (15, 1.3, 0.3, 1.2, 2.6)],
         'jump': [(20, 0.0, -0.30, 2.2, 0.0), (16, 1.9, 0.10, 2.0, 1.7)],
         'hurt': [(14, 0.0, -1.2, 1.4, 0.0), (11, 1.9, -0.7, 1.3, 1.4)],
         'prone':[(20, 0.0, -0.05, 1.6, 0.0), (15, 1.9, 0.25, 1.4, 1.6)]}[mode]
    for L, ph0, droop, A, oy in S:
        pts = []
        for k in range(L + 1):
            pts.append((kx + dirx * k * 0.95, ky + oy + droop * k + A * (k / L) * math.sin(2 * math.pi * t + ph0 - k * 0.45)))
        m = np.zeros((h, w), bool)
        for k, (a, b) in enumerate(zip(pts[:-1], pts[1:])):
            r = 2.0 if k < L * 0.35 else (1.6 if k < L * 0.75 else 1.1)
            m |= seg(h, w, a, b, r)
        up = m & ~np.roll(m, 1, 0); dn = m & ~np.roll(m, -1, 0)
        col = np.full((h, w), C('r1'), np.int16); col[dn] = C('r2'); col[up & ~dn] = C('r0')
        img = blank(h, w); img[ring(m)] = OL; img[m] = col[m]
        over(cv, img)
    return cv

def shift_split(p, split, d):
    """move rows above `split` down by d (squash, d>0) or up by -d (stretch, gap filled by repeating the seam row)"""
    q = p.copy()
    if d == 0: return q
    moved = np.full_like(p, -1)
    if d > 0:
        moved[d:split + d] = p[:split]
    else:
        e = -d
        moved[:split - e] = p[e:split]
        for r in range(split - e, split): moved[r] = p[split - 1]
    q[:split] = -1
    m = moved >= 0; q[m] = moved[m]
    return q

# ---------------- key poses ----------------
POSE = {
    #          file        tail cut x, knot(x,y),  leg cut (y,x0,x1), hips(back, front),  wool cx, ground row, split row
    'fwd':  dict(f='v3fwd_1', tx=16, knot=(16, 9),  lc=(39, 4, 45), hips=((14, 38), (30, 38)), cx=22, gy=48, split=33),
    'dup':  dict(f='v3dup_1', tx=17, knot=(17, 10), lc=(42, 4, 40), hips=((14, 41), (31, 41)), cx=22, gy=51, split=35),
    'ddn':  dict(f='v3ddn_1', tx=15, knot=(16, 10), lc=(40, 4, 38), hips=((13, 39), (30, 39)), cx=21, gy=49, split=33),
    'up':   dict(f='v3up_2',  tx=16, knot=(17, 23), lc=(58, 4, 44), hips=((17, 57), (35, 57)), cx=27, gy=67, split=50),
}
BASE = CH - 1   # ground row in the cell

def pose_parts(name):
    P = POSE[name]; p = load(P['f'])
    body = remove_tails(p, P['tx'])
    upper = cut_legs(body, *P['lc'])
    return P, body, upper

def place(cv, img, P, dy=0):
    ox = CW // 2 - P['cx']; oy = BASE - P['gy'] + dy
    paste(cv, img, ox, oy); return ox, oy

RUN_FOOT = [(12, 0), (6, 0), (0, 0), (-6, 0), (-12, 0), (-9, 5), (0, 7), (9, 4)]
RUN_BOB = [1, 1, 0, 0, 1, 1, 0, 0]      # body drop per frame (down = +)
RUN_SQ = [0, 1, 0, 0, 0, 1, 0, 0]     # wool squash/stretch

def stand_frames(name, n=6):
    """idle breathing: upper body sinks 1px and back, tails drift"""
    P, body, upper = pose_parts(name)
    out = []
    breath = [0, 0, 1, 1, 1, 0][:n]
    for i in range(n):
        cv = blank()
        ox, oy = CW // 2 - P['cx'], BASE - P['gy']
        tails(cv, (P['knot'][0] + ox, P['knot'][1] + oy + breath[i]), i / n, 'idle')
        img = shift_split(body, P['split'], breath[i])
        paste(cv, img, ox, oy)
        out.append(fix_outline(cv))
    return out

def run_frames(name, recoil=False):
    P, body, upper = pose_parts(name)
    out = []
    ox, oy0 = CW // 2 - P['cx'], BASE - P['gy']
    for i in range(8):
        cv = blank()
        bob = RUN_BOB[i]; oy = oy0 + bob - 2
        img = shift_split(upper, P['split'], RUN_SQ[i])
        if recoil and i % 2 == 0:
            # recoil kick: everything right of the chest jolts back 1px
            k = img.copy(); cut = P['cx'] + 4
            k[:, cut - 1:-1] = img[:, cut:]; k[:, -1] = -1
            img = np.where(k >= 0, k, np.where(np.arange(img.shape[1])[None, :] < cut, img, -1)).astype(np.int16)
        tails(cv, (P['knot'][0] + ox, P['knot'][1] + oy + max(0, RUN_SQ[i])), i / 8, 'run')
        (hbx, hby), (hfx, hfy) = P['hips']
        for which, (hx, hy), back in (('b', (hbx, hby), True), ('f', (hfx, hfy), False)):
            ph = (i + (4 if back else 0)) % 8
            dx, lift = RUN_FOOT[ph]
            hip = (hx + ox + 0.5, hy + oy - 3)
            foot = (hx + ox + dx, BASE - 1 - lift)
            if back: leg(cv, hip, foot, back=True)
        paste(cv, img, ox, oy)
        # front leg drawn over the wool bottom edge so the stride reads clearly
        hx, hy = P['hips'][1]
        dx, lift = RUN_FOOT[i % 8]
        cvl = blank(); leg(cvl, (hx + ox + 0.5, hy + oy - 3), (hx + ox + dx, BASE - 1 - lift))
        # only the part below the wool shows
        wool = np.isin(cv, WOOL)
        cvl[wool & (np.arange(CH)[:, None] < hy + oy + 1)] = -1
        over(cv, cvl)
        out.append(fix_outline(cv))
    return out


# ---------------- other anims ----------------
def rot_idx(a, deg):
    """RotSprite-lite: 8x nearest upscale, rotate, mode-downsample back"""
    from PIL import Image
    k = 8; h, w = a.shape
    im = Image.fromarray((a + 1).astype(np.uint8), 'L').resize((w * k, h * k), Image.NEAREST)
    im = im.rotate(-deg, resample=Image.NEAREST, expand=True, center=None)
    b = np.array(im).astype(np.int16)
    H, W = b.shape[0] // k, b.shape[1] // k
    b = b[:H * k, :W * k].reshape(H, k, W, k).transpose(0, 2, 1, 3).reshape(H, W, k * k)
    out = np.full((H, W), -1, np.int16)
    for j in range(H):
        for i in range(W):
            c = b[j, i]; opq = c[c > 0]
            if opq.size < k * k * 0.5: continue
            cnt = np.bincount(opq); out[j, i] = cnt.argmax() - 1
    return out

def ball_frames(n=8):
    p = load('v3ball_3')
    p = remove_tails(p, 12)
    ys, xs = np.where(p >= 0); p = p[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    out = []
    for i in range(n):
        r = p if i == 0 else (np.rot90(p, -(i // 2)) if i % 2 == 0 else rot_idx(p, 45 * i))
        r = fix_outline(np.pad(r, 1, constant_values=-1))
        cv = blank()
        h, w = r.shape
        cx, cy = CW // 2, BASE - 20          # ball centre (bottom ~ ground-2)
        # tails stream from the rear-top of the ball, fluttering
        tails(cv, (cx - 10, cy - 12), i / n, 'jump')
        paste(cv, r, int(round(cx - w / 2)), int(round(cy - h / 2)))
        out.append(fix_outline(cv))
    return out

def fall_frames(n=4):
    P, body, upper = pose_parts('fwd')
    out = []
    ox, oy = CW // 2 - P['cx'], BASE - P['gy'] - 3
    kick = [(0, 0), (1, 1), (0, 1), (-1, 0)]
    for i in range(n):
        cv = blank()
        tails(cv, (P['knot'][0] + ox, P['knot'][1] + oy), i / n, 'fall')
        (hbx, hby), (hfx, hfy) = P['hips']
        a, b = kick[i]
        leg(cv, (hbx + ox + 1, hby + oy - 3), (hbx + ox - 3 + a, BASE - 2 + b), back=True)
        paste(cv, upper, ox, oy)
        cvl = blank(); leg(cvl, (hfx + ox, hfy + oy - 3), (hfx + ox + 3 - a, BASE - 3 - b))
        wool = np.isin(cv, WOOL); cvl[wool & (np.arange(CH)[:, None] < hfy + oy + 1)] = -1
        over(cv, cvl)
        out.append(fix_outline(cv))
    return out

def prone_frames(n=4):
    p = remove_tails(load('v3prone_2'), 38)
    out = []
    ox = CW // 2 - 40; oy = BASE - (p.shape[0] - 1)
    breath = [0, 0, 1, 0]
    for i in range(n):
        cv = blank()
        tails(cv, (38 + ox, 10 + oy + breath[i]), i / n, 'prone')
        paste(cv, shift_split(p, 22, breath[i]), ox, oy)
        out.append(fix_outline(cv))
    return out

def hurt_frames(n=4, face_x=False):
    p = load('v3hurt_1')
    q = p.copy(); reg = q[:14, 24:]; reg[np.isin(reg, RED)] = -1; q = fix_outline(q)
    out = []
    ox = CW // 2 - 22; oy = BASE - (p.shape[0] - 1) + 2
    for i in range(n):
        cv = blank()
        tails(cv, (26 + ox, 9 + oy), i / n, 'hurt', dirx=1)
        paste(cv, q, ox + (i % 2), oy - (i % 2))
        out.append(fix_outline(cv))
    return out
