# Curl-cluster fleece: composites a hand-drawn curl stamp on a jittered lattice at pixel scale.
# Each curl: highlight cap top-left, mid body, tan shadow crescent bottom-right. Rim curls make a scalloped silhouette.
import sys, math; sys.path.insert(0, 'art/raw/hero')
from px import *
from px import CH as CHARS
from rast import dil, ring, ero

def _P(t):
    L = t.strip('\n').split('\n'); w = max(map(len, L))
    return np.array([[-1 if c == '.' else CHARS.index(c) for c in l.ljust(w, '.')] for l in L], np.int16)

CURL = _P("""
.AAB.
AAAAB
AABBC
BBBCD
.CDD.
""")
CURL_B = _P("""
..AA..
.AAAB.
AAABBC
ABBBCC
.BCCD.
..DD..
""")
OL = IDX['ol']; W = [IDX[k] for k in ('w0', 'w1', 'w2', 'w3')]

def silhouette(mask, r=2.7, step=4.0, seed=0):
    """eroded core + a ring of bumps along its contour -> scalloped outline"""
    h, w = mask.shape
    core = ero(ero(mask))
    Y, X = np.mgrid[0:h, 0:w] + 0.5
    sil = core.copy()
    # contour points of the core, walked in angle order around the centroid
    edge = core & ~ero(core)
    ys, xs = np.where(edge)
    cy, cx = ys.mean(), xs.mean()
    ang = np.arctan2(ys - cy, xs - cx); order = np.argsort(ang)
    pts = list(zip(xs[order] + 0.5, ys[order] + 0.5))
    acc = 1e9; last = None; bumps = []
    for (x, y) in pts:
        if last is None or math.hypot(x - last[0], y - last[1]) >= step:
            bumps.append((x, y)); last = (x, y)
    rng = np.random.default_rng(seed)
    for (x, y) in bumps:
        rr = r + rng.uniform(-0.3, 0.4)
        sil |= (X - x) ** 2 + (Y - y) ** 2 <= rr * rr
    return sil, bumps

SCALE = _P("""
.AAAA.
AAAAAB
AAABBC
BBBBCC
.CCCC.
""")
def fleece(mask, seed=0, dx=6, dy=4, scallop=True, order='down', stamp=None, r=2.6, step=4.5):
    h, w = mask.shape
    from scipy import ndimage
    mask = ndimage.binary_fill_holes(mask)
    st = SCALE if stamp is None else stamp
    rng = np.random.default_rng(seed)
    sil, bumps = silhouette(mask, seed=seed, r=r, step=step) if scallop else (mask, [])
    cv = np.full((h, w), -1, np.int16); cv[sil] = IDX['w1']
    ys, xs = np.where(sil)
    y0, y1, x0, x1 = ys.min() - 2, ys.max() + 2, xs.min() - 3, xs.max() + 3
    cy, cx = ys.mean(), xs.mean(); ry, rx = (y1 - y0) / 2, (x1 - x0) / 2
    cen = []
    for r_, yy in enumerate(range(y0, y1 + 1, dy)):
        off = ((dx + 1) // 2) if r_ % 2 else 0
        for xx in range(x0 + off, x1 + 1, dx): cen.append((yy, xx + int(rng.integers(-1, 2))))
    cen.sort(key=lambda c: (-c[0] if order == 'up' else c[0], c[1]))
    sh, sw = st.shape
    for (py, px_) in cen:
        g = ((py - cy) / max(ry, 1)) * 1.0 - ((px_ - cx) / max(rx, 1)) * 0.3
        shift = 1 if g > 0.5 else 0
        for j in range(sh):
            for i in range(sw):
                v = st[j, i]; Y_, X_ = py + j, px_ + i
                if v < 0 or not (0 <= Y_ < h and 0 <= X_ < w) or not sil[Y_, X_]: continue
                cv[Y_, X_] = W[min(3, W.index(v) + shift)]
    # rim bumps: highlight cap on each scallop
    for (x, y) in bumps:
        ix, iy = int(x), int(y)
        for (dy_, dx_) in ((-1, 0), (-1, -1), (0, -1), (-2, 0)):
            Y_, X_ = iy + dy_, ix + dx_
            if 0 <= Y_ < h and 0 <= X_ < w and sil[Y_, X_] and y < cy: cv[Y_, X_] = W[0]
    cv[ring(sil)] = OL
    return cv


def curl_blob(h, w, curls, order=None):
    """union of round curls (cx, cy, r) each shaded as a lit bump; painted in list order (later on top)"""
    Y, X = np.mgrid[0:h, 0:w] + 0.5
    cv = np.full((h, w), -1, np.int16)
    for (cx, cy, r) in curls:
        d = (X - cx) ** 2 + (Y - cy) ** 2
        disk = d <= r * r
        u = ((X - cx) * 0.5 + (Y - cy) * 0.87) / r
        t = np.where(u < -0.1, 0, np.where(u < 0.5, 1, 2))
        rim = disk & ~ero(disk) & (u > 0.4)
        t[rim] = 3
        for k in range(4): cv[disk & (t == k)] = W[k]
    m = cv >= 0; cv[ring(m)] = OL
    return cv


def curl_fill(mask, spacing=5.0, r=3.1, seed=0, bottom_first=True):
    """pack round lit curls on a jittered hex lattice inside `mask`; the union of curls is the silhouette"""
    from scipy import ndimage
    h, w = mask.shape
    mask = ndimage.binary_fill_holes(mask)
    rng = np.random.default_rng(seed)
    core = ero(mask)
    ys, xs = np.where(mask); cy, cx = ys.mean(), xs.mean(); ry = (ys.max() - ys.min()) / 2; rx = (xs.max() - xs.min()) / 2
    cen = []
    dy = spacing * 0.87
    for j, yy in enumerate(np.arange(ys.min() + 1.5, ys.max() + 1, dy)):
        for xx in np.arange(xs.min() + 1.5 + (spacing / 2 if j % 2 else 0), xs.max() + 1, spacing):
            y_, x_ = yy + rng.uniform(-0.5, 0.5), xx + rng.uniform(-0.5, 0.5)
            iy, ix = int(y_), int(x_)
            if 0 <= iy < h and 0 <= ix < w and core[iy, ix]: cen.append((x_, y_))
    cen.sort(key=lambda c: (-c[1] if bottom_first else c[1], c[0]))
    Y, X = np.mgrid[0:h, 0:w] + 0.5
    cv = np.full((h, w), -1, np.int16)
    # fill any gaps inside the core first with a mid-shadow tone
    for (x_, y_) in cen:
        rr = r + rng.uniform(-0.2, 0.3)
        d = (X - x_) ** 2 + (Y - y_) ** 2; disk = d <= rr * rr
        u = ((X - x_) * 0.5 + (Y - y_) * 0.87) / rr
        g = ((y_ - cy) / max(ry, 1)) - ((x_ - cx) / max(rx, 1)) * 0.3
        sh = 1 if g > 0.6 else 0
        t = np.where(u < 0.05, 0, np.where(u < 0.62, 1, 2)) + sh
        rim = disk & ~ero(disk) & (u > 0.55)
        t[rim] = 3
        t = np.clip(t, 0, 3)
        for k in range(4): cv[disk & (t == k)] = W[k]
    inside = ndimage.binary_fill_holes(cv >= 0)
    cv[inside & (cv < 0)] = W[2]
    cv[ring(cv >= 0)] = OL
    return cv


def lobe_body(h, w, cx, cy, rx, ry, n=8, lr=3.6, start=-2.2, seed=0, inner=()):
    """few BIG wool lobes around an elliptical core: deep scallops in the silhouette, lit tops,
    tan undersides, lobe boundaries as a darker tone; interior kept nearly flat"""
    Y, X = np.mgrid[0:h, 0:w] + 0.5
    rng = np.random.default_rng(seed)
    cv = np.full((h, w), -1, np.int16)
    core = ((X - cx) / (rx - lr * 0.9)) ** 2 + ((Y - cy) / (ry - lr * 0.9)) ** 2 <= 1
    cv[core] = W[1]
    g = (Y - cy) / ry
    cv[core & (g > 0.45)] = W[2]
    cv[core & (g < -0.35) & ((X - cx) < rx * 0.2)] = W[0]
    lobes = []
    for i in range(n):
        a = start + 2 * math.pi * i / n + rng.uniform(-0.08, 0.08)
        lobes.append((cx + (rx - lr * 0.8) * math.cos(a), cy + (ry - lr * 0.8) * math.sin(a), lr + rng.uniform(-0.3, 0.4)))
    lobes += list(inner)
    lobes.sort(key=lambda l: -l[1])             # bottom first: upper lobes' undersides overlap lower lobes
    for (x_, y_, r) in lobes:
        d = (X - x_) ** 2 + (Y - y_) ** 2; disk = d <= r * r
        u = ((X - x_) * 0.35 + (Y - y_) * 0.94) / r
        low = (y_ - cy) / ry > 0.35
        t = np.where(u < 0.15, 0, np.where(u < 0.62, 1, 2)) + (1 if low else 0)
        t = np.clip(t, 0, 3)
        rim = disk & ~ero(disk) & (u > 0.35)
        t[rim] = 3 if low else 2
        for k in range(4): cv[disk & (t == k)] = W[k]
        # boundary arc: darker line along the lower edge of this lobe where it overlaps others
    cv[ring(cv >= 0)] = OL
    return cv


def curl_body(h, w, cx, cy, rx, ry, cr=2.1, sp=4.0, seed=0):
    """round fleece built from MANY small curls, each with its own darker rim and a light top.
    Rim curls bump the silhouette; overall shape stays round."""
    Y, X = np.mgrid[0:h, 0:w] + 0.5
    rng = np.random.default_rng(seed)
    ell = ((X - cx) / rx) ** 2 + ((Y - cy) / ry) ** 2 <= 1
    cen = []
    dy = sp * 0.87
    for j, yy in enumerate(np.arange(cy - ry, cy + ry + 1, dy)):
        for xx in np.arange(cx - rx + (sp / 2 if j % 2 else 0), cx + rx + 1, sp):
            if ((xx - cx) / (rx - 0.6)) ** 2 + ((yy - cy) / (ry - 0.6)) ** 2 <= 1:
                cen.append((xx + rng.uniform(-0.3, 0.3), yy + rng.uniform(-0.3, 0.3)))
    # rim curls
    n = int(2 * math.pi * math.sqrt((rx * rx + ry * ry) / 2) / (sp * 1.15))
    rims = []
    for i in range(n):
        a = 2 * math.pi * (i + 0.5) / n
        rims.append((cx + (rx - 0.2) * math.cos(a), cy + (ry - 0.2) * math.sin(a), 1))
    cen = [(x, y, 0) for (x, y) in cen] + rims
    cen.sort(key=lambda c: (-c[1], c[0]))           # bottom first: each curl's underside rim stays visible
    cv = np.full((h, w), -1, np.int16)
    cv[ell] = W[1]
    for (x_, y_, isrim) in cen:
        r = cr + rng.uniform(-0.1, 0.25) + (0.5 if isrim else 0)
        disk = (X - x_) ** 2 + (Y - y_) ** 2 <= r * r
        edge = disk & ~ero(disk)
        u = ((X - x_) * 0.4 + (Y - y_) * 0.92) / r
        g = (y_ - cy) / ry
        sh = 1 if g > 0.45 else 0
        t = np.where(u < 0.0, 0, 1) + sh
        t = np.where(edge & (u > -0.35), 2 + sh, t)      # tan rim around the lower 2/3 of each curl
        t = np.clip(t, 0, 3)
        for k in range(4): cv[disk & (t == k)] = W[k]
    cv[ring(cv >= 0)] = OL
    return cv
