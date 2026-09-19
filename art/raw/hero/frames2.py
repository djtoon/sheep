# Round 2 hero builder: one AI wool torso + hand-drawn head / rifle / hooves + procedural arms, legs, headband tails.
import sys, math; sys.path.insert(0, 'art/raw/hero')
from rast import *
from frames import (CW, CH, BASE, OL, WOOL, RED, C, load, blank, over, fix_outline, tails, leg,
                    shift_split, rot_idx, RUN_FOOT, RUN_BOB, RUN_SQ, remove_tails)
from parts import HEAD, GUN, GUN_GRIP, GUN_FORE, GUN_MUZZLE, HOOF
GOLD = [IDX[k] for k in ('g0', 'g1', 'g2')]

# ---------- torso (from the unarmed AI body) ----------
CART = [  # one fat cartridge, 3 wide x 5 tall (tip on top), followed by a 1px dark gap
    ('.', 'g2', '.'),
    ('g0', 'g1', 'g2'),
    ('g0', 'g1', 'g2'),
    ('g1', 'g1', 'g2'),
    ('g2', 'g2', 'g2'),
]
def cartridges(cv, p0, p1):
    h, w = cv.shape
    wool = cv >= 0
    (x0, y0), (x1, y1) = p0, p1
    m = np.zeros((h, w), bool); col = np.full((h, w), -1, np.int16)
    x = int(x0)
    while x <= x1:
        yb = int(round(y0 + (y1 - y0) * (x - x0) / max(x1 - x0, 1)))
        for j, row in enumerate(CART):
            for i, c in enumerate(row):
                Y_, X_ = yb - 3 + j, x + i
                if c == '.' or not (0 <= Y_ < h and 0 <= X_ < w): continue
                m[Y_, X_] = True; col[Y_, X_] = C(c)
        # dark strap/gap column
        for j in range(1, 5):
            Y_, X_ = yb - 3 + j, x + 3
            if 0 <= Y_ < h and 0 <= X_ < w: m[Y_, X_] = True; col[Y_, X_] = OL
        x += 4
    m &= wool
    cv[ring(m) & wool] = OL
    cv[m] = col[m]
    return cv
def make_torso():
    """round fleece of many small outlined curls + a band of fat brass cartridges across the front"""
    from wool import curl_body
    H_, W_ = 64, 70
    cx, cy = BODY_C[0] + TP, BODY_C[1] + TP
    rx, ry = BODY_R
    fl = curl_body(H_, W_, cx, cy, rx, ry, cr=2.3, sp=4.4, seed=3)
    fl = cartridges(fl, (BELT[0][0] + TP, BELT[0][1] + TP), (BELT[1][0] + TP, BELT[1][1] + TP))
    return fl
WIDEN = (9, 15, 21, 27, 33)
def sx(x): return x + sum(1 for c in WIDEN if c < x)
TP = 6   # torso canvas padding
T_CX, T_GY = sx(24), 51           # torso centre column, ground row in torso coords
# layout traced from the 2b74 mockup sheep (trace coords + 5 rows)
BODY_R = (17.5, 13.5)
BODY_C = (29, 33)
BELT = ((13, 34), (41, 27))
TORSO = make_torso()
HIPS = ((14, 37), (40, 40))
HEAD_AT = (21, 5)             # head top-left in torso coords
from parts import HEAD_BAND
KNOT = (HEAD_AT[0] + 1, HEAD_AT[1] + HEAD_BAND + 1)

# ---------- rotated rifle with tracked anchors ----------
def rot_point(p, shape, deg, k=8):
    h, w = shape
    th = math.radians(deg)
    # PIL expand size
    W = abs(w * k * math.cos(th)) + abs(h * k * math.sin(th)); H = abs(w * k * math.sin(th)) + abs(h * k * math.cos(th))
    W = int(math.ceil(W - 1e-6)); H = int(math.ceil(H - 1e-6))
    x, y = (p[0] + 0.5) * k - w * k / 2, (p[1] + 0.5) * k - h * k / 2
    xr = x * math.cos(th) - y * math.sin(th) + W / 2; yr = x * math.sin(th) + y * math.cos(th) + H / 2
    return (xr / k - 0.5, yr / k - 0.5)
def gun_at(deg):
    """returns (sprite, grip, fore, muzzle) with anchors in sprite coords"""
    anchors = [GUN_GRIP, GUN_FORE, GUN_MUZZLE]
    if deg == 0: return GUN, *anchors
    if deg == -90:
        g = np.rot90(GUN, 1)            # CCW: (x,y) -> (y, w-1-x)
        w = GUN.shape[1]
        return g, *[(a[1], w - 1 - a[0]) for a in anchors]
    # inverse-mapped nearest rotation about the grip, supersampled 3x3 per pixel with priority to steel
    th = math.radians(deg); h, w = GUN.shape; cx, cy = GUN_GRIP[0] + 0.5, GUN_GRIP[1] + 0.5
    R = 40; out = np.full((2 * R, 2 * R), -1, np.int16)
    ca, sa = math.cos(th), math.sin(th)
    for j in range(2 * R):
        for i in range(2 * R):
            votes = []
            for sy in (0.25, 0.5, 0.75):
                for sx in (0.25, 0.5, 0.75):
                    dx, dy = i + sx - R, j + sy - R
                    u = dx * ca + dy * sa + cx; v = -dx * sa + dy * ca + cy
                    ui, vi = int(math.floor(u)), int(math.floor(v))
                    if 0 <= ui < w and 0 <= vi < h and GUN[vi, ui] >= 0: votes.append(GUN[vi, ui])
            if len(votes) >= 3:
                steel = [v for v in votes if v != OL]
                out[j, i] = max(set(steel), key=steel.count) if len(steel) >= 3 else OL
    # re-outline
    m = (out >= 0) & (out != OL); out[out == OL] = -1; out[ring(m)] = OL
    def tr(a):
        dx, dy = a[0] + 0.5 - cx, a[1] + 0.5 - cy
        return (R + dx * ca - dy * sa - 0.5, R + dx * sa + dy * ca - 0.5)
    ys, xs = np.where(out >= 0); y0, x0 = ys.min(), xs.min()
    out = out[y0:ys.max() + 1, x0:xs.max() + 1]
    return out, *[(tr(a)[0] - x0, tr(a)[1] - y0) for a in anchors]
GUNS = {d: gun_at(d) for d in (0, -45, 45, -90)}

AIM = {  # angle, grip position (torso coords), near shoulder, far shoulder, head
    'fwd': (0,   (45, 38), (35, 34), (39, 32), 'angry'),
    'dup': (-45, (49, 38), (36, 34), (40, 32), 'angry'),
    'ddn': (45,  (44, 36), (35, 34), (39, 32), 'angry'),
    'up':  (-90, (52, 22), (38, 30), (42, 27), 'up'),
}

def arm(cv, shoulder, hand, back=False):
    m = seg(CH, CW, shoulder, hand, 1.6)
    col = np.full((CH, CW), C('f2' if back else 'f1'), np.int16)
    img = blank(); img[ring(m)] = OL; img[m] = col[m]
    return over(cv, img)
def hoof(cv, at, back=False):
    h = HOOF.copy()
    if back: h[h == C('f0')] = C('f1'); h[h == C('f1')] = C('f2')
    paste(cv, h, int(round(at[0] - 2.5)), int(round(at[1] - 2)))
    return cv

def lean_body(b, lean):
    if not lean: return b
    o = np.full_like(b, -1)
    for y in range(b.shape[0]):
        d = lean if y < 22 + TP else (lean // 2 if y < 33 + TP else 0)
        if d: o[y, d:] = b[y, :-d]
        else: o[y] = b[y]
    return o
def draw_upper(cv, ox, oy, aim='fwd', sq=0, recoil=0, face=None, t=0.0, tail_mode='run', head_dy=0, lean=0):
    ang, grip, sh_n, sh_f, hk = AIM[aim]
    face = face or hk
    body = lean_body(shift_split(TORSO, 34 + TP, sq), lean)
    if lean:
        grip = (grip[0] + lean, grip[1]); sh_n = (sh_n[0] + lean // 2, sh_n[1]); sh_f = (sh_f[0] + lean, sh_f[1])
    g, gg, gf, gm = GUNS[ang]
    gx = grip[0] + ox - recoil; gy = grip[1] + oy + max(0, sq)
    gpos = (int(round(gx - gg[0])), int(round(gy - gg[1])))
    fore = (gpos[0] + gf[0], gpos[1] + gf[1])
    # far arm behind the torso's front edge, reaching the fore-grip
    arm(cv, (sh_f[0] + ox, sh_f[1] + oy + max(0, sq)), fore, back=True)
    paste(cv, body, ox - TP, oy - TP)
    arm(cv, (sh_f[0] + ox, sh_f[1] + oy + max(0, sq)), fore, back=True) if aim == 'up' else None
    tails(cv, (KNOT[0] + ox + lean + 1 * bool(lean), KNOT[1] + oy + head_dy + max(0, sq)), t, tail_mode)
    hx, hy = HEAD_AT[0] + ox + lean + 1 * bool(lean), HEAD_AT[1] + oy + head_dy + max(0, sq)
    hm = blank(); paste(hm, HEAD[face], hx, hy); hmask = hm >= 0
    r1 = dil(hmask) & ~hmask; r2 = dil(r1 | hmask) & ~(r1 | hmask)
    Yg = np.arange(CH)[:, None]; Xg = np.arange(CW)[None, :]
    under = (Yg > hy + HEAD_BAND + 4) | (Xg < hx + 9)          # jaw underside + back of the head (below the band)
    under = under & (Yg > hy + HEAD_BAND)
    wooly = np.isin(cv, WOOL)
    cv[r1 & wooly] = OL
    cv[r2 & wooly & under] = OL
    paste(cv, HEAD[face], hx, hy)
    # rifle with its own outline ring
    gl = blank(); paste(gl, g, *gpos)
    gm_ = gl >= 0; ring_ = ring(gm_) & (cv >= 0)
    over(cv, gl); cv[ring_ & (cv != OL) & ~np.isin(cv, [C('k0'), C('k1'), C('k2')])] = OL
    hoof(cv, fore, back=True)
    arm(cv, (sh_n[0] + ox, sh_n[1] + oy + max(0, sq)), (gx - 1, gy + 1))
    hoof(cv, (gx, gy + 1))
    muzzle = (gpos[0] + gm[0], gpos[1] + gm[1])
    return muzzle

def stand_frames(aim='fwd', n=6):
    out = []
    breath = [0, 0, 1, 1, 1, 0]
    ox, oy = CW // 2 - T_CX, BASE - T_GY + 1
    for i in range(n):
        cv = blank()
        (hbx, hby), (hfx, hfy) = HIPS
        # wide, forward-leaning stance: back leg braced far behind, front leg planted ahead
        # lunge: back leg extended far behind, front knee forward, upper body leaning into the gun
        leg(cv, (hbx + ox + 1, hby + oy - 1), (hbx + ox - 9, BASE - 1), back=True)
        leg(cv, (hfx + ox, hfy + oy - 1), (hfx + ox + 4, BASE - 1))
        m = draw_upper(cv, ox - 1, oy, aim, sq=breath[i], t=i / n, tail_mode='idle', lean=2 if aim == 'fwd' else 1)
        # front leg re-drawn on top of the wool hem
        out.append(fix_outline(cv))
    return out, m

def run_frames(aim='fwd', recoil=False):
    out = []
    ox, oy0 = CW // 2 - T_CX, BASE - T_GY
    for i in range(8):
        cv = blank()
        oy = oy0 + RUN_BOB[i] - 2
        (hbx, hby), (hfx, hfy) = HIPS
        dx, lift = RUN_FOOT[(i + 4) % 8]
        leg(cv, (hbx + ox + 0.5, hby + oy - 2), (hbx + ox + dx, BASE - 1 - lift), back=True)
        m = draw_upper(cv, ox - 1, oy, aim, sq=RUN_SQ[i], recoil=(1 if recoil and i % 2 == 0 else 0), t=i / 8,
                       lean=(2 if i % 4 == 0 else 0), face=('grit' if recoil and i % 4 < 2 else None))
        dx, lift = RUN_FOOT[i]
        cvl = blank(); leg(cvl, (hfx + ox + 0.5, hfy + oy - 2), (hfx + ox + dx, BASE - 1 - lift))
        wool = np.isin(cv, WOOL); cvl[wool & (np.arange(CH)[:, None] < hfy + oy + 1)] = -1
        over(cv, cvl)
        out.append(fix_outline(cv))
    return out, m

def fall_frames(n=4):
    """airborne pose traced from 369c: rifle up-diagonal at the shoulder, legs tucked and trailing"""
    out = []
    ox, oy = CW // 2 - T_CX, BASE - T_GY - 4
    kick = [(0, 0), (1, 1), (0, 1), (-1, 0)]
    for i in range(n):
        cv = blank(); a, b = kick[i]
        (hbx, hby), (hfx, hfy) = HIPS
        leg(cv, (hbx + ox + 2, hby + oy), (hbx + ox - 6 + a, hby + oy + 7 + b), back=True)
        draw_upper(cv, ox, oy, 'dup', t=i / n, tail_mode='fall')
        cvl = blank(); leg(cvl, (hfx + ox - 2, hfy + oy - 1), (hfx + ox + 2 - a, hfy + oy + 6 - b))
        wool = np.isin(cv, WOOL); cvl[wool & (np.arange(CH)[:, None] < hfy + oy + 1)] = -1
        over(cv, cvl)
        out.append(fix_outline(cv))
    return out

def prone_frames(n=4):
    """prone: flat curl-wool body on the ground, head low at the front, rifle flat ahead, hind legs trailing"""
    from wool import curl_body
    out = []
    for i in range(n):
        br = [0, 0, 1, 0][i]
        cv = blank()
        # hind legs trailing behind, hooves up
        leg(cv, (22, 73), (9, 77), back=True)
        leg(cv, (25, 75), (13, 78))
        body = curl_body(CH, CW, 32, 71 + br * 0.5, 15.0, 7.0, cr=2.1, sp=4.0, seed=5)
        body = cartridges(body, (21, 74), (40, 70))
        over(cv, body)
        tails(cv, (38 + 1, 52 + HEAD_BAND + 1 + br), i / n, 'prone')
        paste(cv, HEAD['angry'], 38, 52 + br)
        # rifle flat along the ground in front of the chin, hooves on it
        g, gg, gf, gm = GUNS[0]
        gx, gy = 67, 77
        gpos = (gx - gg[0], gy - gg[1])
        gl = blank(); paste(gl, g, *gpos); over(cv, gl)
        hoof(cv, (gpos[0] + gf[0], gpos[1] + gf[1]), back=True)
        hoof(cv, (gx, gy))
        out.append(fix_outline(cv))
    return out

def shoot_frames():
    """standing fire: 2-frame recoil (lean into the shot / kick back), gritted teeth, tails snapping"""
    out = []
    ox, oy = CW // 2 - T_CX, BASE - T_GY + 1
    for i, (lean, rec, face) in enumerate(((3, 0, 'grit'), (2, 2, 'grit'))):
        cv = blank()
        (hbx, hby), (hfx, hfy) = HIPS
        leg(cv, (hbx + ox + 1, hby + oy - 1), (hbx + ox - 9, BASE - 1), back=True)
        leg(cv, (hfx + ox, hfy + oy - 1), (hfx + ox + 4, BASE - 1))
        m = draw_upper(cv, ox - 1, oy, 'fwd', sq=0, recoil=rec, t=0.25 + i * 0.5, tail_mode='run', lean=lean, face=face)
        out.append(fix_outline(cv))
    return out, m

def ball_frames(n=8):
    """spin-jump: a round ball of outlined curls with the angry face peeking out, tucked hooves, rolling"""
    from wool import curl_body
    from parts import HEAD
    S = 34
    b = curl_body(S, S, S / 2, S / 2, 13.0, 13.0, cr=2.4, sp=4.6, seed=11)
    X_, Y_ = np.mgrid[0:S, 0:S][::-1] if False else (np.mgrid[0:S, 0:S][1] + 0.5, np.mgrid[0:S, 0:S][0] + 0.5)
    circ = ((X_ - S / 2) ** 2 + (Y_ - S / 2) ** 2) <= 12.6 ** 2
    # grey face peeking out on the front-right, clipped to the ball
    fe = (((X_ - 23.5) / 8.0) ** 2 + ((Y_ - 17.5) / 6.5) ** 2 <= 1) & circ
    b[ring(fe) & circ] = OL; b[fe] = C('f1')
    eyes = HEAD['angry'][14:21, 9:23]
    for j in range(eyes.shape[0]):
        for i in range(eyes.shape[1]):
            v = eyes[j, i]; y, x = 13 + j, 16 + i
            if v >= 0 and fe[y, x] and v in (OL, C('ew')): b[y, x] = v
    # muzzle + scowl
    b[20, 27:30] = OL
    # headband wraps the ball
    band = (Y_ > 8) & (Y_ < 11.5) & circ
    b[band] = C('r1'); b[band & (Y_ < 9.5)] = C('r0'); b[band & (Y_ > 10.5)] = C('r2')
    b[ring(band) & circ & ~band & (Y_ > 7) & (Y_ < 13)] = OL
    # tucked hooves at the bottom-front
    from parts import HOOF
    paste(b, HOOF, 17, 25); paste(b, HOOF, 11, 26)
    b = fix_outline(np.pad(b, 2, constant_values=-1))
    out = []
    import math as _m
    for i in range(n):
        r = b if i == 0 else (np.rot90(b, -(i // 2)) if i % 2 == 0 else rot_idx(b, 45 * i))
        r = fix_outline(np.pad(r, 1, constant_values=-1))
        cv = blank(); h_, w_ = r.shape
        cx, cy = CW // 2, BASE - 20
        # headband knot rides around the ball with the spin; tails stream behind
        a = _m.radians(-160 + 12 * _m.sin(2 * _m.pi * i / n))   # tails always stream off the trailing side
        kx, ky = cx + 11 * _m.cos(a), cy + 11 * _m.sin(a)
        tails(cv, (kx, ky), i / n, 'jump')
        paste(cv, r, int(round(cx - w_ / 2)), int(round(cy - h_ / 2)))
        out.append(fix_outline(cv))
    return out
