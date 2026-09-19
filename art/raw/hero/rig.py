# Paper-doll rig for the commando sheep: every part is drawn in pixel space so all frames share one design.
import sys, math; sys.path.insert(0, 'art/raw/hero')
from rast import *
from heads import head
CW, CH = 80, 80; BASE = 79
OL = IDX['ol']
def C(n): return IDX[n]
def blank(): return np.full((CH, CW), -1, np.int16)
X, Y = grid(CH, CW)
def over(dst, src):
    m = src >= 0; dst[m] = src[m]; return dst
def outlined(mask, colours):
    cv = blank(); r = ring(mask); cv[r] = OL; cv[mask] = colours[mask]; return cv
def place(src, x, y):
    cv = blank(); paste(cv, src, x, y); return cv

# ---------- wool ----------
def cloud(cx, cy, rx, ry, lump=3.0, squash=0.0, seed=0, n=None):
    """cloud-shaped wool blob with curl shading. returns (mask, colour)"""
    ry2 = ry * (1 - squash); rx2 = rx * (1 + squash * 0.6); cy2 = cy + ry * squash
    core = ((X - cx) / (rx2 - lump * 0.6)) ** 2 + ((Y - cy2) / (ry2 - lump * 0.6)) ** 2 <= 1
    m = core.copy(); cen = []
    n = n or int(2 * math.pi * math.sqrt((rx2 * rx2 + ry2 * ry2) / 2) / (lump * 1.25))
    for i in range(n):
        a = 2 * math.pi * (i + 0.37 * seed) / n
        px = cx + (rx2 - lump * 0.9) * math.cos(a); py = cy2 + (ry2 - lump * 0.9) * math.sin(a)
        r = lump * (1.0 + 0.15 * math.sin(i * 2.3 + seed))
        m |= ((X - px) ** 2 + (Y - py) ** 2) <= r * r; cen.append((px, py, r))
    for j in range(-6, 7):
        for i in range(-7, 8):
            px = cx + i * 4.4 + (j % 2) * 2.2; py = cy2 + j * 3.7
            if ((px - cx) / (rx2 - lump * 1.3)) ** 2 + ((py - cy2) / (ry2 - lump * 1.3)) ** 2 <= 1: cen.append((px, py, 2.5))
    col = np.full((CH, CW), C('w0'), np.int16)
    best = np.full((CH, CW), 1e9); rel = np.zeros((CH, CW, 2))
    for (px, py, r) in cen:
        d = ((X - px) ** 2 + (Y - py) ** 2) / (r * r)
        s = d < best; best[s] = d[s]; rel[s, 0] = (X - px)[s] / r; rel[s, 1] = (Y - py)[s] / r
    lit = rel[..., 0] * 0.45 + rel[..., 1] * 0.9
    col[lit > 0.2] = C('w1'); col[lit > 0.68] = C('w2')
    g = ((X - cx) * -0.2 + (Y - cy2) * 1.0) / ry2
    col[(g > 0.5) & (col == C('w1'))] = C('w2'); col[(g > 0.5) & (col == C('w0'))] = C('w1')
    col[(g > 0.8) & (col == C('w2'))] = C('w3')
    return m, col

# ---------- gun: oriented boxes in gun space (u along barrel, v down), origin at the trigger ----------
GUN = [
    (-11, -5, -1.5, 2.5, 'k2', 0),     # stock
    (-12.5, -10.5, -1.8, 3.4, 'k2', 0),  # butt plate
    (-6, 5, -2.5, 1.5, 'k2', 0),       # receiver
    (-3, 2, -4.0, -2.2, 'k1', 0),      # carry handle / rear sight
    (5, 12, -2.0, 1.0, 'k2', 0),       # handguard
    (12, 19, -1.0, 0.7, 'k2', 0),      # barrel
    (10.5, 12, -3.8, -1.5, 'k2', 0),   # front sight
    (18, 20.5, -1.7, 1.3, 'k1', 0),    # muzzle brake
    (0, 3, 1.0, 5.8, 'k2', 0.35),      # magazine (slants forward)
    (-4.5, -2.5, 1.0, 4.4, 'k2', -0.4),  # pistol grip (slants back)
]
def gun_layer(ox, oy, ang_deg):
    a = math.radians(ang_deg); ca, sa = math.cos(a), math.sin(a)
    dx = X - ox; dy = Y - oy
    u = dx * ca + dy * sa; v = -dx * sa + dy * ca
    m = np.zeros((CH, CW), bool); col = np.full((CH, CW), C('k2'), np.int16)
    for (u0, u1, v0, v1, c, slant) in GUN:
        uu = u - (v - 1.0) * slant if slant else u
        b = (uu >= u0) & (uu < u1) & (v >= v0) & (v < v1)
        m |= b; col[b] = C(c)
    col[m & (v > -2.6) & (v < -1.5) & (u > -6) & (u < 12)] = C('k1')
    col[m & (v > -1.1) & (v < -0.3) & (u > 12) & (u < 18)] = C('k0')
    col[m & (v > -2.6) & (v < -1.9) & (u > -5) & (u < 11)] = C('k0')
    col[m & (v > -1.6) & (v < -0.8) & (u > -11) & (u < -6)] = C('k1')
    return m, col
def muzzle_point(ox, oy, ang_deg):
    a = math.radians(ang_deg); return (ox + 20.5 * math.cos(a), oy + 20.5 * math.sin(a))

def leg(cv, hip, foot, back=False, r=1.9):
    m = seg(CH, CW, hip, foot, r)
    fx, fy = foot
    hoof = (((X - (fx + 0.8)) / 2.4) ** 2 + ((Y - (fy - 0.8)) / 1.8) ** 2 <= 1) & (Y < fy + 0.2)
    m |= hoof
    col = np.full((CH, CW), C('f2' if back else 'f1'), np.int16)
    if not back: col[m & ~np.roll(m, -1, 1) & ~hoof] = C('f0')
    col[hoof] = C('k1'); col[hoof & (Y > fy - 0.9)] = C('k2')
    return over(cv, outlined(m, col))

def tails(cv, knot, t, mode='run'):
    kx, ky = knot
    if mode == 'run':    specs = [(14, 0.0, -0.30, 1.4), (11, 2.2, 0.30, 1.3)]
    elif mode == 'idle': specs = [(12, 0.0, 0.45, 0.8), (10, 2.2, 0.95, 0.7)]
    elif mode == 'fall': specs = [(12, 0.0, -1.0, 0.9), (10, 2.2, -0.55, 0.9)]
    else:                specs = [(12, 0.0, -0.10, 1.6), (10, 2.2, 0.40, 1.6)]
    for L, ph0, droop, amp0 in specs:
        pts = []
        for k in range(L + 1):
            amp = amp0 * (k / L) ** 0.9 * 2.2
            pts.append((kx - k * 0.95, ky + droop * k + amp * math.sin(2 * math.pi * t + ph0 - k * 0.6)))
        m = np.zeros((CH, CW), bool)
        for k, (a, b) in enumerate(zip(pts[:-1], pts[1:])):
            r = 1.3 if k < L * 0.5 else (1.0 if k < L * 0.8 else 0.65)
            m |= seg(CH, CW, a, b, r)
        up = m & ~np.roll(m, 1, 0); dn = m & ~np.roll(m, -1, 0)
        col = np.full((CH, CW), C('r1'), np.int16); col[dn] = C('r2'); col[up] = C('r0')
        over(cv, outlined(m, col))
    return cv

def bandolier(m_body, p0, p1, w=2.3):
    s = seg(CH, CW, p0, p1, w) & ero(m_body)
    (x0, y0), (x1, y1) = p0, p1; L = math.hypot(x1 - x0, y1 - y0); ux, uy = (x1 - x0) / L, (y1 - y0) / L
    along = (X - x0) * ux + (Y - y0) * uy; across = -(X - x0) * uy + (Y - y0) * ux
    col = np.full((CH, CW), C('g1'), np.int16)
    k = np.floor(along / 2.0).astype(int) % 2
    col[k == 1] = C('g2')
    col[(across < -w + 1.1) & (k == 0)] = C('g0')
    col[np.abs(across) < 0.5] = C('g2')
    rim = ring(s) & m_body
    return s, col, rim

def torso(cv, cx, cy, rx=13.5, ry=12.5, squash=0.0, seed=0, belt=True):
    m, col = cloud(cx, cy, rx, ry, 3.0, squash=squash, seed=seed)
    img = outlined(m, col)
    if belt:
        cyy = cy + ry * squash
        b, bc, rim = bandolier(m, (cx - 13, cyy + 5), (cx + 7, cyy - 8))
        img[rim] = OL; img[b] = bc[b]
    over(cv, img)
    return m

def arm(cv, shoulder, hand, back=False, r=1.7):
    m = seg(CH, CW, shoulder, hand, r)
    h = ((X - hand[0]) ** 2 + (Y - hand[1]) ** 2) <= 2.2 ** 2
    col = np.full((CH, CW), C('f2' if back else 'f1'), np.int16)
    m |= h; col[h] = C('k1')
    return over(cv, outlined(m, col))

def head_at(cv, kind, x, y):
    return over(cv, place(head(kind), x, y))
