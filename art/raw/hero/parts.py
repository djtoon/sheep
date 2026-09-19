# Hand-authored hero parts (pixel text). Chars: # ol  A-D wool(light->dark)  a-d grey(light->dark)  W white
#   p q pink  R S T red(light->dark)  G H I gold  x y z steel(highlight, mid, body)
import sys; sys.path.insert(0, 'art/raw/hero')
from px import *
from px import CH

def P(txt):
    L = [l for l in txt.strip('\n').split('\n')]
    w = max(len(l) for l in L); L = [l.ljust(w, '.') for l in L]
    return parse(L)

# head, facing right. 25 wide. Big eyes (5x6 whites), angry brows cutting the inner corners.
HEAD = {}
_CAP = """
.......####..####..###...
.....##AAAA##AAAA##AAA#..
....#AAAAAAAAAAAAAAAAAA#.
...#AABBAAAABBBAAAABBAA#.
..#AABCCBAABCCCBAABCCBA#.
..#BBCCBBBBCCBCCBBCCBBB#.
.#RRRRRRRRRRRRRRRRRRRRR#.
#RSSSSSSSSSSSSSSSSSSSSSS#
#TTTTTTTTTTTTTTTTTTTTTTT#
"""
def _overlay(base, txt, row0):
    L = [l for l in txt.strip(chr(10)).split(chr(10))]
    w = max(len(l) for l in L); o = np.full((max(row0 + len(L), base.shape[0]), max(w, base.shape[1])), -1, np.int16)
    o[:base.shape[0], :base.shape[1]] = base
    for j, l in enumerate(L):
        for i, ch in enumerate(l):
            if ch != '.' or j + row0 >= base.shape[0]: o[j + row0, i] = -1 if ch == '.' else CH.index(ch)
    return o
_capA = P(_CAP)
_capA = np.pad(_capA, ((0, 0), (0, 27 - _capA.shape[1])), constant_values=-1)
_BROWS = """
........##.........##......
..........###...###........
"""
_FACE_ANGRY = """
.#cc#bbbb#WW##b##WW#bbbb#..
#cpq#bbb#WWWWW#WWWWW#bbbb#.
#cpp#bbb#WW##W#WW##W#bbbbb#
.#pc#bbb#WW##W#WW##W#bbbab#
..#c#bbbb#WWW#b#WWW#bbbbbb#
...##bbbbb###bbb###bbbbbbd#
....#cbbbbbbbbbbbbbbbbb#d#.
.....#cbbbbbbbbbbbbbbbbbd#.
......#ccbbbbbbbbbb#####b#.
.......##cccbbbbbbbbbbbb#..
.........############......
"""
_FACE_UP = """
.#cc#bbbb#WW##b#W##W#bbbb#.
#cpq#bbb#WW##W#WW##W#bbbb#.
#cpp#bbb#WW##W#WWWWW#bbbbb#
.#pc#bbb#WWWWW#WWWWW#bbbab#
..#c#bbbb#WWW#b#WWW#bbbbbb#
...##bbbbb###bbb###bbbbbbd#
....#cbbbbbbbbbbbbbbbbb#d#.
.....#cbbbbbbbbbbbbbbbbbd#.
......#ccbbbbbbbbbb#####b#.
.......##cccbbbbbbbbbbbb#..
.........############......
"""
def _fleece_cap(c):
    """wool cap = small outlined curls in a dome on the headband"""
    from wool import curl_body
    pad = 3
    c = np.pad(c, ((pad, 0), (0, 0)), constant_values=-1)
    band = 6 + pad
    blob = curl_body(c.shape[0] + 6, c.shape[1], 13.2, band + 1.5, 11.6, 4.8, cr=2.1, sp=4.0, seed=7)[:c.shape[0]]
    o = np.full_like(c, -1)
    o[:band] = blob[:band]
    o[band:] = c[band:]
    o[band - 1][(o[band - 1] < 0) & (c[band] >= 0)] = CH.index('#')
    return o
_capA = _fleece_cap(_capA)
def _mk(face, brows=True):
    h = _capA.copy()
    if brows: h = _overlay(h, _BROWS, 10)
    return _overlay(h, face, 12)
HEAD['angry'] = _mk(_FACE_ANGRY)
HEAD['up'] = _mk(_FACE_UP.replace('#WW##b#W##W#', '#WW##b##WW#', 1))
HEAD['grit'] = HEAD['angry']

# rifle, facing right, grip/trigger origin marked in GUN_ORIGIN. body z, mid y, top highlight x.
GUN = P("""
.......####.........##.......
......#yyyy#........#x#......
#####.#y##y#.......##y#......
#uuuu############################
#uvvvzxxxxxxxxxxxxxxxxxxxxxxxxzx#
#uvvvzzzzzzzzzyzyzyzzzzzzzzzzzzz#
.####zzzz#zzzzzzzzzzz#####yy####.
.....#vv##zzzzzz#######...####...
.....#vv#.#zzzy#.................
.....####.#zzzy#.................
..........#zzy#..................
..........####...................
""")
GUN_GRIP = (7, 7)      # where the rear hoof holds (col,row)
GUN_FORE = (19, 6)     # where the front hoof holds
GUN_MUZZLE = (32, 4)

# hoof (hand) blob, light grey with dark tip so it separates from the black gun
HOOF = P("""
.####.
#aaab#
#aabc#
#bbcd#
.####.
""")

# ---- round 5: big chunky assault rifle, drawn from parts in pixel space ----
def _big_gun():
    H, W = 15, 37
    g = np.full((H, W), -1, np.int16)
    def R(x0, x1, y0, y1, c):
        g[y0:y1, x0:x1] = CH.index(c)
    ox, oy = 1, 1                                   # room for outline
    def r(x0, x1, y0, y1, c): R(x0 + ox, x1 + ox, y0 + oy, y1 + oy, c)
    # stock (wood), slanted butt
    r(0, 7, 3, 7, 'u'); r(0, 7, 6, 7, 'v'); r(0, 2, 3, 8, 'v'); r(2, 5, 7, 8, 'v')
    # receiver 5 tall
    r(7, 20, 2, 7, 'z'); r(8, 20, 2, 3, 'x'); r(7, 20, 6, 7, 'y')
    r(9, 12, 1, 2, 'y')                              # rear sight
    # handguard (wood)
    r(20, 26, 3, 7, 'u'); r(20, 26, 6, 7, 'v'); r(20, 27, 2, 3, 'y')   # gas tube over it
    # barrel + front sight + muzzle
    r(26, 33, 3, 5, 'z'); r(26, 33, 3, 4, 'x')
    r(28, 30, 0, 3, 'z'); r(28, 29, 0, 1, 'x')
    r(32, 35, 2, 6, 'y'); r(32, 35, 2, 3, 'x')
    # curved magazine drooping forward
    for k, (x0, y0) in enumerate([(14, 7), (14, 8), (15, 9), (15, 10), (16, 11), (17, 12)]):
        r(x0, x0 + 4, y0, y0 + 1, 'z'); r(x0 + 3, x0 + 4, y0, y0 + 1, 'y')
    # pistol grip slanting back
    for (x0, y0) in [(9, 7), (9, 8), (8, 9), (8, 10)]:
        r(x0, x0 + 3, y0, y0 + 1, 'z')
    # trigger guard
    r(12, 14, 8, 9, 'z')
    m = g >= 0
    from rast import ring as _ring
    g[_ring(m)] = CH.index('#')
    return g
GUN = _big_gun()
GUN_GRIP = (10, 10)
GUN_FORE = (23, 8)
GUN_MUZZLE = (36, 5)

# ---- round 6: readable angry face (2px V brows, forward pupils, scowl) + cap outline fix ----
def _angrify(h, look='fwd'):
    from rast import seg, ring as _ring, grid as _grid
    h = h.copy(); H, W_ = h.shape
    O = CH.index('#'); Wc = CH.index('W'); B = CH.index('b')
    # clear the old eyes/brows
    reg = h[12:18, 8:21]; reg[(reg == Wc) | (reg == O)] = B
    h[10, 8:21][h[10, 8:21] == O] = CH.index('S'); h[11, 8:21][h[11, 8:21] == O] = CH.index('T')
    h = np.concatenate([h[:18], h[17:18], h[18:]], 0); H = h.shape[0]   # one row taller face
    X, Y = _grid(H, W_)
    for (cx, cy) in ((11.0, 16.0), (17.4, 16.0)):
        e = ((X - cx) / 3.0) ** 2 + ((Y - cy) / 3.4) ** 2 <= 1
        h[_ring(e)] = O; h[e] = Wc
    if look == 'up':
        for (px, py) in ((11, 14), (17, 14)): h[py:py + 2, px:px + 2] = O
    else:
        for (px, py) in ((12, 16), (18, 16)): h[py:py + 2, px:px + 3 if px == 18 else px + 2] = O
    # 2px angry V brows, inner ends low
    br = seg(H, W_, (7.6, 12.2), (14.2, 14.6), 0.95) | seg(H, W_, (14.2, 14.6), (20.8, 12.2), 0.95)
    h[br & (Y > 12)] = O
    # scowl: downturned mouth on the muzzle
    h[21, 18:25][h[21, 18:25] == O] = B
    for (x, y) in ((18, 22), (19, 21), (20, 21), (21, 21), (22, 21), (23, 22)):
        h[y, x] = O
    return h
def _fix_cap(h):
    from rast import ring as _ring
    O = CH.index('#')
    cap = h[:9].copy()
    m = cap >= 0
    m[:, 0] = False; m[:, -1] = False; m[:, 1] &= False
    cap[~m] = -1
    cap[:, 25:] = -1
    mm = cap >= 0
    cap[_ring(mm) & (cap < 0)] = O
    h = h.copy(); h[:9] = cap
    return h
for _k in ('angry', 'up'):
    HEAD[_k] = _angrify(_fix_cap(HEAD[_k]), 'up' if _k == 'up' else 'fwd')
HEAD['grit'] = HEAD['angry']

# ---- round 8: gritted-teeth firing face ----
def _grit(h):
    h = h.copy(); O = CH.index('#'); Wc = CH.index('W'); B = CH.index('b')
    h[20:23, 16:25][h[20:23, 16:25] == O] = B
    for x in range(17, 24): h[20, x] = O; h[22, x] = O
    for x in range(17, 24): h[21, x] = O if x in (17, 20, 23) else Wc
    return h
HEAD['grit'] = _grit(HEAD['angry'])

# ---- round 10: rifle re-derived for the 46px rig (~31x11 incl. outline) ----
def _gun46():
    H, W = 11, 31
    g = np.full((H, W), -1, np.int16)
    def r(x0, x1, y0, y1, c): g[y0 + 1:y1 + 1, x0 + 1:x1 + 1] = CH.index(c)
    r(0, 5, 2, 5, 'u'); r(0, 5, 4, 5, 'v'); r(0, 1, 2, 6, 'v'); r(1, 4, 5, 6, 'v')       # stock
    r(5, 17, 1, 5, 'z'); r(6, 17, 1, 2, 'x'); r(5, 17, 4, 5, 'y')                         # receiver
    r(7, 9, 0, 1, 'y')                                                                    # rear sight
    r(17, 22, 2, 5, 'u'); r(17, 22, 4, 5, 'v'); r(17, 23, 1, 2, 'y')                      # handguard + gas tube
    r(22, 27, 2, 4, 'z'); r(22, 27, 2, 3, 'x')                                            # barrel
    r(24, 25, 0, 2, 'z')                                                                  # front sight
    r(27, 29, 1, 5, 'y'); r(27, 29, 1, 2, 'x')                                            # muzzle brake
    for (x0, y0) in [(11, 5), (11, 6), (12, 7), (13, 8)]:                                 # curved magazine
        r(x0, x0 + 3, y0, y0 + 1, 'z'); r(x0 + 2, x0 + 3, y0, y0 + 1, 'y')
    for (x0, y0) in [(7, 5), (7, 6), (6, 7)]:                                             # pistol grip
        r(x0, x0 + 2, y0, y0 + 1, 'z')
    r(9, 11, 6, 7, 'z')                                                                   # trigger guard
    from rast import ring as _ring
    g[_ring(g >= 0)] = CH.index('#')
    return g
GUN = _gun46()
GUN_GRIP = (8, 8)
GUN_FORE = (20, 6)
GUN_MUZZLE = (30, 3)

from rast import dil as _dil
for _k in list(HEAD):
    _h = HEAD[_k].copy(); _O = CH.index('#')
    _body = (_h >= 0) & (_h != _O)
    _h[(_h == _O) & ~_dil(_body, True)] = -1
    HEAD[_k] = _h
# crop empty rows above the cap (same amount for every variant so the band row stays aligned)
_top = int(np.where((HEAD['angry'] >= 0).any(1))[0][0])
for _k in list(HEAD): HEAD[_k] = HEAD[_k][_top:]
HEAD_BAND = 9 - _top          # first headband row inside the head sprite


# ---- round 11: r7 big rifle with a bright steel line along its whole top edge; light hooves ----
def _topline(g):
    g = g.copy(); O = CH.index('#'); X0 = CH.index('x')
    for x in range(g.shape[1]):
        col = g[:, x]
        ys = [y for y in range(len(col)) if col[y] >= 0 and col[y] != O]
        if ys: g[ys[0], x] = X0
    return g
GUN = _topline(_big_gun())
GUN_GRIP = (10, 10)
GUN_FORE = (23, 8)
GUN_MUZZLE = (36, 5)
HOOF = P("""
.####.
#LLLa#
#LLab#
#aabb#
.####.
""")

# ---- round 12: sheep face rebuilt: round eyes + pupils + glint, brows ON TOP, lighter protruding snout ----
def _face12(kind='angry'):
    from rast import ring as _ring, grid as _grid
    H, W_ = 16, 28
    f = np.full((H, W_), -1, np.int16)
    X, Y = _grid(H, W_)
    C_ = lambda c: CH.index(c)
    O = C_('#')
    ear = ((X - 2.8) / 2.7) ** 2 + ((Y - 5.0) / 2.2) ** 2 <= 1
    f[ear] = C_('c'); f[((X - 3.0) / 1.5) ** 2 + ((Y - 5.1) / 1.0) ** 2 <= 1] = C_('p')
    f[_ring(ear) & (f < 0)] = O
    # face: full width under the band, rounded jaw below
    face = (((X - 12.5) / 10.0) ** 2 + (np.maximum(Y - 5.0, 0) / 10.0) ** 2 <= 1)
    f[face] = C_('b')
    f[face & (((X - 9) * 0.35 + (Y - 8) * 0.95) > 4.2)] = C_('c')
    sn = ((X - 21.8) / 5.0) ** 2 + ((Y - 10.0) / 3.6) ** 2 <= 1
    f[sn] = C_('a'); f[sn & (Y > 12.3)] = C_('b')
    f[_ring(face | sn) & ~ear] = O
    EYE = ['.#####.', '#WWWWW#', '#WWW#W#', '#WW##W#', '#WW##W#', '#WWWWW#', '.#####.']
    EYE_UP = ['.#####.', '#WW#WW#', '#WW##W#', '#WWWWW#', '#WWWWW#', '#WWWWW#', '.#####.']
    E = EYE_UP if kind == 'up' else EYE
    for (ex, ey) in ((6, 3), (12, 3)):
        for j, row in enumerate(E):
            for i, ch in enumerate(row):
                if ch != '.': f[ey + j, ex + i] = C_(ch)
    # 2px angry brows ABOVE each eye, slanting down toward the nose
    for (x, y) in ((5, 1), (6, 1), (7, 1), (7, 2), (8, 2), (9, 2), (9, 3), (10, 3), (11, 3)):
        f[y, x] = O
    for (x, y) in ((19, 1), (18, 1), (17, 1), (17, 2), (16, 2), (15, 2), (15, 3), (14, 3), (13, 3)):
        f[y, x] = O
    f[9, 25] = O                                   # nostril
    if kind == 'grit':
        for x in range(20, 26): f[12, x] = O; f[14, x] = O
        for x in range(20, 26): f[13, x] = O if x in (20, 23) else C_('W')
    else:
        for (x, y) in ((21, 13), (22, 13), (23, 13), (24, 13), (20, 14), (25, 14)):
            f[y, x] = O
    return f
def _mk12(kind):
    top = HEAD['angry'][:HEAD_BAND + 3].copy()
    fc = _face12(kind)
    h = np.full((top.shape[0] + fc.shape[0] - 1, max(top.shape[1], fc.shape[1])), -1, np.int16)
    h[:fc.shape[0] - 1 + top.shape[0], :][top.shape[0] - 1:top.shape[0] - 1 + fc.shape[0], :fc.shape[1]] = np.where(fc >= 0, fc, -1)
    reg = h[:top.shape[0], :top.shape[1]]; m = top >= 0; reg[m] = top[m]
    return h
_H12 = {k: _mk12(k) for k in ('angry', 'up', 'grit')}
HEAD.update(_H12)

# ---- round 13: cute-angry sheep face: round oval head, big round eyes, one brow bar, short muzzle, no teeth ----
def _face13(kind='angry'):
    from rast import ring as _ring, grid as _grid
    H, W_ = 14, 22
    f = np.full((H, W_), -1, np.int16)
    X, Y = _grid(H, W_)
    C_ = lambda c: CH.index(c); O = C_('#')
    # head: flat top under the band, straight sides, rounded jaw  (~16w x 13h)
    rows = {0: (3, 16), 1: (2, 17), 2: (2, 17), 3: (2, 17), 4: (2, 17), 5: (2, 17), 6: (2, 17), 7: (2, 17),
            8: (2, 17), 9: (3, 16), 10: (3, 16), 11: (4, 15), 12: (6, 13)}
    head = np.zeros((H, W_), bool)
    for y, (a_, b_) in rows.items(): head[y, a_:b_ + 1] = True
    mz = ((X - 17.6) / 3.2) ** 2 + ((Y - 8.6) / 2.8) ** 2 <= 1        # short muzzle, 3px past the face
    ear = ((X - 1.6) / 2.2) ** 2 + ((Y - 5.2) / 1.9) ** 2 <= 1
    f[ear] = C_('c'); f[((X - 1.6) / 1.2) ** 2 + ((Y - 5.3) / 0.8) ** 2 <= 1] = C_('p')
    f[_ring(ear) & ~head] = O
    f[head] = C_('b')
    f[head & (((X - 8) * 0.3 + (Y - 7) * 0.95) > 4.0)] = C_('c')
    f[mz] = C_('a'); f[mz & (Y > 10.3)] = C_('b')
    r = _ring(head | mz); r[0, :] = False
    f[r & ~ear] = O
    f[0, 2] = f[0, 17] = O
    EYE = ['..###..', '.#WWW#.', '#WWW###', '#WW####', '#WW####', '.#WWW#.', '..###..']
    EYE_UP = ['..###..', '.#W###.', '#WW###W', '#WWWWW#', '#WWWWW#', '.#WWW#.', '..###..']
    E = EYE_UP if kind == 'up' else EYE
    for (ex, ey) in ((4, 3), (10, 3)):
        for j, row in enumerate(E):
            for i, ch in enumerate(row):
                if ch != '.': f[ey + j, ex + i] = C_(ch)
    # one 2px brow bar across both eyes, slanting down toward the front
    # heavy 3px brow bar pushed down over the eye tops, slanting down toward the front
    for x in range(3, 11):
        for y in (1, 2, 3): f[y, x] = O
    for x in range(11, 18):
        for y in (2, 3, 4): f[y, x] = O
    f[8, 20] = O                                                     # nostril
    for (x, y) in ((15, 11), (16, 10), (17, 10), (18, 10), (19, 10), (20, 11)):   # determined mouth line
        f[y, x] = O
    return f
def _mk13(kind):
    top = HEAD_TOP13.copy()
    fc = _face13(kind)
    ox = 5
    y0 = top.shape[0]                          # face starts right under the headband
    h = np.full((y0 + fc.shape[0], max(top.shape[1], ox + fc.shape[1])), -1, np.int16)
    h[:top.shape[0], :top.shape[1]] = top
    reg = h[y0:y0 + fc.shape[0], ox:ox + fc.shape[1]]
    m = fc >= 0
    if True:
        # on the band's last row keep the red band except where the brow/eyes are drawn dark/white
        reg[m] = fc[m]
    return h
HEAD_TOP13 = HEAD['angry'][:HEAD_BAND + 3].copy()
for _k in ('angry', 'up'):
    HEAD[_k] = _mk13(_k)
HEAD['grit'] = HEAD['angry']       # no teeth in any pose

# ---- round 14: rifle sized to the traced 2b74 gun (thick receiver + drooping mag) ----
GUN = _topline(_big_gun())
GUN_GRIP = (10, 10)
GUN_FORE = (23, 8)
GUN_MUZZLE = (36, 5)
