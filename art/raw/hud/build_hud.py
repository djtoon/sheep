# Builds every HUD / title pixel asset that is hand-authored (fonts, portrait, life icon, weapon box, gun icons, pips, cursor).
# run: python art/raw/hud/build_hud.py   (from repo root)  -> writes assets/hud/*
import numpy as np, os
from PIL import Image

OUT = 'assets/hud/'
os.makedirs(OUT, exist_ok=True)

def hx(s): return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16), 255)
OUTL = hx('0c0a12')

# ---------------------------------------------------------------- font
G = {
'A': ['.####.', '##..##', '##..##', '######', '##..##', '##..##', '##..##'],
'B': ['#####.', '##..##', '##..##', '#####.', '##..##', '##..##', '#####.'],
'C': ['.####.', '##..##', '##....', '##....', '##....', '##..##', '.####.'],
'D': ['#####.', '##..##', '##..##', '##..##', '##..##', '##..##', '#####.'],
'E': ['######', '##....', '##....', '#####.', '##....', '##....', '######'],
'F': ['######', '##....', '##....', '#####.', '##....', '##....', '##....'],
'G': ['.####.', '##..##', '##....', '##.###', '##..##', '##..##', '.#####'],
'H': ['##..##', '##..##', '##..##', '######', '##..##', '##..##', '##..##'],
'I': ['####', '.##.', '.##.', '.##.', '.##.', '.##.', '####'],
'J': ['...###', '....##', '....##', '....##', '##..##', '##..##', '.####.'],
'K': ['##..##', '##.##.', '####..', '###...', '####..', '##.##.', '##..##'],
'L': ['##....', '##....', '##....', '##....', '##....', '##....', '######'],
'M': ['##...##', '###.###', '#######', '##.#.##', '##...##', '##...##', '##...##'],
'N': ['##..##', '###.##', '######', '##.###', '##..##', '##..##', '##..##'],
'O': ['.####.', '##..##', '##..##', '##..##', '##..##', '##..##', '.####.'],
'P': ['#####.', '##..##', '##..##', '#####.', '##....', '##....', '##....'],
'Q': ['.####.', '##..##', '##..##', '##..##', '##.###', '##..#.', '.##.##'],
'R': ['#####.', '##..##', '##..##', '#####.', '####..', '##.##.', '##..##'],
'S': ['.####.', '##..##', '##....', '.####.', '....##', '##..##', '.####.'],
'T': ['######', '..##..', '..##..', '..##..', '..##..', '..##..', '..##..'],
'U': ['##..##', '##..##', '##..##', '##..##', '##..##', '##..##', '.####.'],
'V': ['##..##', '##..##', '##..##', '##..##', '##..##', '.####.', '..##..'],
'W': ['##...##', '##...##', '##...##', '##.#.##', '#######', '###.###', '##...##'],
'X': ['##..##', '##..##', '.####.', '..##..', '.####.', '##..##', '##..##'],
'Y': ['##..##', '##..##', '##..##', '.####.', '..##..', '..##..', '..##..'],
'Z': ['######', '....##', '...##.', '..##..', '.##...', '##....', '######'],
'0': ['.####.', '##..##', '##..##', '##..##', '##..##', '##..##', '.####.'],
'1': ['..##..', '.###..', '####..', '..##..', '..##..', '..##..', '######'],
'2': ['.####.', '##..##', '....##', '..###.', '.##...', '##....', '######'],
'3': ['.####.', '##..##', '....##', '..###.', '....##', '##..##', '.####.'],
'4': ['...###', '..####', '.##.##', '##..##', '######', '....##', '....##'],
'5': ['######', '##....', '#####.', '....##', '....##', '##..##', '.####.'],
'6': ['.####.', '##....', '##....', '#####.', '##..##', '##..##', '.####.'],
'7': ['######', '##..##', '....##', '...##.', '..##..', '..##..', '..##..'],
'8': ['.####.', '##..##', '##..##', '.####.', '##..##', '##..##', '.####.'],
'9': ['.####.', '##..##', '##..##', '.#####', '....##', '....##', '.####.'],
'!': ['##', '##', '##', '##', '##', '..', '##'],
'.': ['..', '..', '..', '..', '..', '..', '##'],
':': ['..', '##', '##', '..', '##', '##', '..'],
'-': ['....', '....', '....', '####', '....', '....', '....'],
"'": ['##', '##', '.#', '..', '..', '..', '..'],
'/': ['....##', '...##.', '...##.', '..##..', '.##...', '.##...', '##....'],
'?': ['.####.', '##..##', '....##', '..###.', '..##..', '......', '..##..'],
'%': ['##...#', '##..##', '...##.', '..##..', '.##...', '##..##', '#...##'],
'=': ['.....', '.....', '#####', '.....', '#####', '.....', '.....'],
'x': ['.....', '.....', '##.##', '.###.', '.###.', '##.##', '.....'],
',': ['..', '..', '..', '..', '..', '##', '.#'],
'+': ['......', '..##..', '..##..', '######', '..##..', '..##..', '......'],
' ': ['...', '...', '...', '...', '...', '...', '...'],
}

RAMPS = {  # top -> bottom body colours (7 rows)
 'steel':  ['ffffff', 'f4f7fc', 'e6ecf5', 'd0d8e6', 'b8c3d6', 'a4b0c8', '94a0ba'],
 'orange': ['ffe470', 'ffc434', 'ffa41c', 'ff8a0e', 'f47202', 'dc5c00', 'c24a00'],
 'gold':   ['fffbd8', 'fff0a0', 'ffe070', 'ffcc48', 'f8b030', 'ea9420', 'd67c14'],
 'blue':   ['e8f6ff', 'c8e8ff', 'a8d4ff', '8cc0f8', '76aaf0', '6294e0', '5280cc'],
 'ink':    ['16121e', '16121e', '16121e', '16121e', '16121e', '16121e', '16121e'],
 'red':    ['fff0b0', 'ffc050', 'ff8a2c', 'ff5a20', 'e83418', 'c41c14', '9a1010'],
}

def glyph_img(ch, ramp, scale=1, shadow=False, outline=True):
    rows = G[ch]; w = len(rows[0]); h = 7
    body = np.array([[c == '#' for c in r] for r in rows])
    if scale > 1: body = body.repeat(scale, 0).repeat(scale, 1)
    bh, bw = body.shape
    pad = 1 + (1 if shadow else 0)
    W, H = bw + 1 + pad, bh + 1 + pad
    img = np.zeros((H, W, 4), np.uint8)
    m = np.zeros((H, W), bool); m[1:1 + bh, 1:1 + bw] = body
    ring = np.zeros_like(m)
    nb = [(-1, 0), (1, 0), (0, -1), (0, 1)] + ([(-1, -1), (-1, 1), (1, -1), (1, 1)] if scale > 1 else [])
    for dy, dx in nb:   # small font: 4-neighbour outline only (crisper, no heavy diagonal shadow)
        ring |= np.roll(np.roll(m, dy, 0), dx, 1)
    if shadow:  # extra drop shadow to lower-right
        sh = np.zeros_like(m); sh[1:, 1:] = ring[:-1, :-1] | m[:-1, :-1]; ring |= sh
    if outline: img[ring & ~m] = OUTL
    cols = RAMPS[ramp]
    for y in range(bh):
        t = y / max(1, bh - 1)
        c = hx(cols[min(6, int(round(t * 6)))])
        for x in range(bw):
            if body[y, x]: img[1 + y, 1 + x] = c
    if scale > 1 and outline:  # 1px bright rim on top edges for the big font
        for y in range(bh):
            for x in range(bw):
                if body[y, x] and (y == 0 or not body[y - 1, x]):
                    img[1 + y, 1 + x] = hx('ffffff')
    return img, bw

def build_font(name, ramp, scale=1, shadow=False, outline=True):
    chars = list(G.keys())
    imgs = [(c, *glyph_img(c, ramp, scale, shadow, outline)) for c in chars]
    H = max(i.shape[0] for _, i, _ in imgs)
    W = sum(i.shape[1] + 1 for _, i, _ in imgs)
    sheet = np.zeros((H, W, 4), np.uint8); x = 0; xml = []
    for c, im, bw in imgs:
        h, w = im.shape[:2]; sheet[:h, x:x + w] = im
        adv = bw + scale + (1 if scale == 1 else 0)  # body + one (scaled) pixel gap; outline sits in the gap
        if c == ' ': adv = 4 * scale
        xml.append(f'<char id="{ord(c)}" x="{x}" y="0" width="{w}" height="{h}" xoffset="0" yoffset="0" xadvance="{adv}" page="0" chnl="15"/>')
        x += w + 1
    Image.fromarray(sheet, 'RGBA').save(OUT + name + '.png')
    lh = 7 * scale + 2 + (1 if shadow else 0)
    with open(OUT + name + '.xml', 'w') as f:
        f.write(f'<?xml version="1.0"?>\n<font>\n<info face="{name}" size="{lh}" bold="0" italic="0" charset="" unicode="1" stretchH="100" smooth="0" aa="0" padding="0,0,0,0" spacing="0,0"/>\n'
                f'<common lineHeight="{lh + scale}" base="{lh}" scaleW="{W}" scaleH="{H}" pages="1" packed="0"/>\n<pages><page id="0" file="{name}.png"/></pages>\n'
                f'<chars count="{len(xml)}">\n' + '\n'.join(xml) + '\n</chars>\n</font>\n')

for r in ['steel', 'orange', 'gold', 'blue']: build_font('font-' + r, r)
for r in ['steel', 'red', 'gold', 'orange']: build_font('big-' + r, r, 2, True)
build_font('font-ink', 'ink', 1, False, False)          # comic balloon lettering (dark ink on white, no outline)
build_font('big-ink', 'ink', 2, False, False)
for r in ['gold', 'red']: build_font('sfx-' + r, r, 3, True)   # comic SFX lettering

# ---------------------------------------------------------------- ascii art helper
def art(rows, pal):
    h = len(rows); w = max(len(r) for r in rows)
    a = np.zeros((h, w, 4), np.uint8)
    for y, r in enumerate(rows):
        for x, c in enumerate(r):
            if c != '.' and c != ' ': a[y, x] = hx(pal[c])
    return a

SHEEP_PAL = {'K': '120e1a', 'W': 'fff6de', 'w': 'f0d69c', 'v': 'c4995c', 'R': 'e8301c', 'h': 'ff7a4a', 'r': '9a1418',
             'F': '7e829e', 'f': 'a8accb', 'g': '565a74', 'E': 'ffffff', 'e': 'c8d0e0', 'B': '2a62e0', 'b': '1a3fa8', 'c': '3c7cf0', 'p': 'e89aa0',
             'p': 'e89aa0'}

# life icon 13x11
import sys; sys.path.insert(0, 'art/raw/hud')
from life_gen import life_rows
LIFE = life_rows()
Image.fromarray(art(LIFE, SHEEP_PAL)).save(OUT + 'life.png')

# portrait 28x22 (inside the frame), painted with primitives in painter order, each layer outlined
PW, PH = 28, 22
yy, xx = np.mgrid[0:PH, 0:PW]
P = np.full((PH, PW), 'B', dtype='<U1')
P[(xx + yy) < 9] = 'c'
P[yy > 17] = 'b'
def ell(cx, cy, rx, ry): return ((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2 <= 1
def layer(mask, fill, outline=True):
    if outline:
        ring = np.zeros_like(mask)
        for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            sh = np.zeros_like(mask)
            sh[max(0, dy):PH + min(0, dy), max(0, dx):PW + min(0, dx)] = mask[max(0, -dy):PH - max(0, dy), max(0, -dx):PW - max(0, dx)]
            ring |= sh
        P[ring & ~mask] = 'K'
    for k, v in fill(mask): P[v] = k
def wool(m):
    out = [('W', m)]
    lower = m & ~np.roll(m, -1, 0) | m & ~np.roll(m, -2, 0)
    out.append(('w', lower)); out.append(('v', m & ~np.roll(m, -1, 0)))
    out.append(('w', m & ((xx * 7 + yy * 3) % 11 == 0)))
    return out
body = ell(1, 23, 6, 6) | ell(26, 23, 6, 6)
layer(body, wool)
layer(ell(2.5, 14, 4, 5.5) | ell(25.5, 14, 4, 5.5), wool)
ears = ell(4, 10.5, 4, 1.8) | ell(23, 10.5, 4, 1.8)
layer(ears, lambda m: [('F', m), ('g', m & (yy >= 11)), ('p', m & (yy == 10) & ((xx == 3) | (xx == 4) | (xx == 23) | (xx == 24)))])
face = ell(13.5, 14, 7.8, 9)
layer(face, lambda m: [('F', m), ('f', m & ~np.roll(m, 2, 1)), ('g', m & ~np.roll(m, -2, 1)), ('g', m & ~np.roll(m, -1, 0))])
top = np.zeros((PH, PW), bool)
for cx, cy in [(4.5, 4), (8.7, 3), (13.5, 2.9), (18.3, 3), (22.5, 4)]: top |= ell(cx, cy, 3.1, 3)
top &= yy <= 6
layer(top, wool)
band = (yy >= 4) & (yy <= 6) & (xx >= 3) & (xx <= 24)
layer(band, lambda m: [('R', m), ('h', m & (yy == 4)), ('r', m & (yy == 6))], outline=False)
P[4:7, 2] = 'K'; P[4:7, 25] = 'K'
tail = np.zeros((PH, PW), bool)
for x, y in [(2, 5), (1, 5), (0, 5), (2, 6), (1, 6), (0, 6), (0, 7), (1, 7), (0, 8)]: tail[y, x] = True
P[tail] = 'R'; P[6, 0] = 'r'; P[8, 0] = 'r'
eyes = ell(10.4, 11, 2.9, 2.9) | ell(16.6, 11, 2.9, 2.9)
snout = ell(13.5, 18.5, 5, 3.2)
P[snout & face] = 'f'
layer(eyes, lambda m: [('E', m), ('e', m & (yy >= 13))])
for x, y in [(11, 11), (12, 11), (11, 12), (12, 12), (15, 11), (16, 11), (15, 12), (16, 12)]: P[y, x] = 'K'
for x, y in [(9, 10), (18, 10)]: P[y, x] = 'E'
for x, y in [(8, 8), (9, 8), (10, 8), (11, 9), (12, 9), (13, 10),
             (19, 8), (18, 8), (17, 8), (16, 9), (15, 9), (14, 10)]: P[y, x] = 'K'
for x, y in [(12, 20), (13, 19), (14, 19), (15, 20)]: P[y, x] = 'K'
P[17, 12] = 'g'; P[17, 15] = 'g'
HAND = ['rRBKWKgFFFFFFFFFFFFFFFgKWKBB', 'BKKKKKgKKKKFFFFFFKKKKgKKKKKB', 'KFFFFFKFEEEKKFFKKEEEFKFFFFFK', 'KFppFFKKEEEEEFFEEEEEKKFFppFK', 'KgggggKKEEKKEFFEKKEEKKgggggK', 'WKKKKKFKEEKKEFFEKKEEKFKKKKKW', 'WWWWKFFKeEEEeFFeEEEeKFFKWWWW', 'WWWvKFFFKKKKKFFKKKKKFFFKvWWW', 'WWWvKfFFFFFFFFFFFFFFFFgKvWWW', 'WwWvKfFFFFFFFFFFFFFFFFgKvwWW', 'wWWWvKfFFFFgFFgFFFFFFgKvWWwW', 'WWwWvKfFFFFFFFFFFFFFFgKvWWWw', 'vwwwwvKfFFFFKKKKFFFFgKvwwwwv', 'KvvvvKKgFFFKFFFFKFFFgKKvvvvK', 'wKKKKwwKgggggggggggggKwwKKKK']
for i, r in enumerate(HAND): P[7 + i] = list(r)
from portrait_fix import grid as _pgrid
P = np.array([list(r) for r in _pgrid()])
p = art([''.join(r) for r in P], SHEEP_PAL)
# frame: outline K, light ring, dark ring
fw, fh = PW + 6, PH + 6
fr = np.zeros((fh, fw, 4), np.uint8)
fr[:, :] = hx('0c0a12')
fr[1:-1, 1:-1] = hx('dfe4ee'); fr[1, 1:-1] = hx('ffffff'); fr[1:-1, 1] = hx('ffffff'); fr[-2, 1:-1] = hx('9aa4b8'); fr[1:-1, -2] = hx('9aa4b8')
fr[2:-2, 2:-2] = hx('0c0a12')
fr[3:-3, 3:-3] = p
for (y, x) in [(0, 0), (0, fw - 1), (fh - 1, 0), (fh - 1, fw - 1)]: fr[y, x] = 0
Image.fromarray(fr).save(OUT + 'portrait.png')

# ---------------------------------------------------------------- gun icons (40x14), primitive-built with auto shading
GPAL = {1: 'ffffff', 2: 'd4dae6', 3: '9ca4bc', 4: '6a7088', 5: '3e4258', 'K': '0c0a12', 'r': 'd8301c', 'R': 'ff7050', 'c': '40d8ff',
        'C': 'd8ffff', 'y': 'ffcc40', 'Y': 'c07814', 'o': '6c7440', 'O': '8c9458'}
class Gun:
    def __init__(s): s.m = np.zeros((14, 40), bool); s.acc = {}; s.cut = set()
    def rect(s, x, y, w, h): s.m[y:y + h, x:x + w] = True
    def px(s, *pts):
        for x, y in pts: s.m[y, x] = True
    def a(s, col, *pts):
        for x, y in pts: s.acc[(x, y)] = col; s.m[y, x] = True
    def k(s, *pts):
        for p in pts: s.cut.add(p)
    def img(s):
        m = s.m; h, w = m.shape; o = np.zeros((h, w, 4), np.uint8)
        for y in range(h):
            for x in range(w):
                if not m[y, x]: continue
                M = lambda yy, xx: 0 <= yy < h and 0 <= xx < w and m[yy, xx]
                c = 3
                if not M(y + 1, x): c = 5
                elif not M(y + 2, x): c = 4
                if not M(y - 1, x): c = 1
                elif not M(y - 2, x): c = 2 if c == 3 else c
                elif not M(y, x - 1) and c == 3: c = 2
                elif not M(y, x + 1) and c == 3: c = 4
                o[y, x] = hx(GPAL[c])
        for (x, y), col in s.acc.items(): o[y, x] = hx(GPAL[col])
        ring = np.zeros_like(m)
        for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            ring |= np.roll(np.roll(m, dy, 0), dx, 1)
        o[ring & ~m] = hx(GPAL['K'])
        for (x, y) in s.cut: o[y, x] = hx(GPAL['K'])
        return o

def rifle():
    g = Gun()
    g.rect(1, 3, 9, 4); g.rect(1, 7, 5, 2); g.px((6, 7), (7, 7))           # stock
    g.rect(10, 4, 2, 3)                                                      # neck
    g.rect(12, 3, 11, 5)                                                     # receiver
    g.rect(13, 1, 8, 1); g.px((14, 2), (19, 2))                              # carry handle
    g.rect(23, 3, 9, 4)                                                      # handguard
    g.rect(32, 4, 5, 2); g.rect(36, 3, 3, 4)                                 # barrel + muzzle
    g.rect(33, 1, 1, 3)                                                      # front sight
    g.px((14, 8), (15, 8), (14, 9), (15, 9), (13, 10), (14, 10), (13, 11), (14, 11), (13, 12))   # grip
    g.px((18, 8), (19, 8), (20, 8), (21, 8), (18, 9), (19, 9), (20, 9), (21, 9), (19, 10), (20, 10), (21, 10), (22, 10),
         (19, 11), (20, 11), (21, 11), (22, 11), (20, 12), (21, 12), (22, 12), (23, 12))  # mag
    g.k((25, 5), (27, 5), (29, 5), (16, 5), (17, 5), (18, 5), (2, 4), (3, 4), (4, 4), (5, 4))
    g.k((15, 2), (16, 2), (17, 2), (18, 2), (16, 9), (17, 9))
    return g.img()

def mgun():
    g = Gun()
    g.rect(1, 4, 7, 4); g.rect(1, 3, 2, 6)
    g.rect(8, 5, 2, 2); g.rect(10, 3, 12, 5)
    g.rect(13, 1, 6, 1); g.px((13, 2), (18, 2))
    g.rect(22, 4, 10, 3); g.rect(32, 5, 4, 1); g.rect(35, 4, 3, 3); g.px((34, 3))
    g.px((11, 8), (12, 8), (11, 9), (12, 9), (10, 10), (11, 10), (10, 11), (11, 11))
    for x in (23, 25, 27, 29): g.k((x, 5))
    g.px((27, 7), (26, 8), (26, 9), (25, 10), (25, 11), (24, 12), (28, 8), (29, 9), (29, 10), (30, 11), (30, 12))   # bipod
    g.rect(14, 8, 6, 4)
    for y in range(8, 12):
        for x in range(14, 20): g.acc[(x, y)] = 'o' if y > 8 else 'O'
    for i, (x, y) in enumerate([(20, 8), (21, 9), (21, 10), (22, 11)]): g.a('y' if i % 2 == 0 else 'Y', (x, y))
    g.k((16, 9), (17, 9))
    return g.img()

def spread():
    # solid, readable silhouette: butt + stock, tall receiver, rear sight, thick barrel with front sight,
    # pistol grip hanging down, and a solid flared 3-barrel muzzle (slots cut into a widening block). Ends at x=36.
    g = Gun()
    g.rect(1, 3, 3, 6); g.rect(4, 4, 5, 4)                                    # butt + stock
    g.rect(9, 3, 12, 6)                                                       # receiver
    g.rect(12, 1, 3, 2)                                                       # rear sight
    g.rect(21, 4, 9, 4)                                                       # barrel
    g.rect(26, 2, 2, 2)                                                       # front sight
    g.px((13, 9), (14, 9), (15, 9), (13, 10), (14, 10), (12, 11), (13, 11), (12, 12), (13, 12))   # pistol grip
    g.px((17, 9), (17, 10), (16, 11))                                         # trigger guard
    g.rect(30, 3, 2, 6); g.rect(32, 2, 2, 8); g.rect(34, 1, 3, 10)            # flared muzzle block
    g.k((32, 4), (33, 4), (34, 4), (35, 4), (36, 4), (32, 7), (33, 7), (34, 7), (35, 7), (36, 7))   # 3 barrels
    g.k((16, 5), (17, 5), (18, 5))                                            # ejection port
    g.k((23, 6), (25, 6), (27, 6))                                            # barrel vents
    return g.img()

def laser():
    g = Gun()
    g.rect(1, 4, 7, 4); g.rect(1, 3, 2, 6); g.k((3, 5), (4, 5), (5, 5), (3, 6), (4, 6), (5, 6))   # skeleton stock
    g.rect(8, 5, 2, 2); g.rect(10, 3, 14, 6)                                  # body
    g.rect(13, 1, 7, 1); g.px((14, 2), (18, 2))                               # scope
    g.rect(24, 4, 8, 4); g.rect(32, 3, 4, 6); g.rect(36, 5, 2, 2)             # emitter barrel + tip
    g.px((12, 9), (13, 9), (12, 10), (13, 10), (11, 11), (12, 11), (11, 12))  # grip
    g.px((16, 9), (17, 9), (18, 9), (16, 10), (17, 10), (18, 10))             # battery
    g.a('C', (15, 1), (16, 1), (17, 1))
    for x in (13, 15, 17, 19, 21):
        g.a('C', (x, 4)); g.a('c', (x, 5), (x, 6), (x, 7))
    for x in range(25, 32): g.a('c', (x, 5)); g.a('C', (x, 6)) if x % 2 else None
    g.a('C', (33, 4), (34, 4)); g.a('c', (33, 5), (34, 5), (33, 6), (34, 6)); g.a('C', (36, 5), (37, 5))
    g.a('c', (17, 10))
    return g.img()

guns = [rifle(), mgun(), spread(), laser()]
sheet = np.zeros((14, 40 * 4, 4), np.uint8)
for i, gi in enumerate(guns): sheet[:, i * 40:(i + 1) * 40] = gi
Image.fromarray(sheet).save(OUT + 'guns.png')   # frames: 0 R, 1 M, 2 S, 3 L

# ---------------------------------------------------------------- weapon box 64x22
bw_, bh_ = 64, 22
b = np.zeros((bh_, bw_, 4), np.uint8)
b[:, :] = hx('0c0a12')
b[1:-1, 1:-1] = hx('d8dee8'); b[1, 2:-2] = hx('ffffff'); b[2:-2, 1] = hx('ffffff'); b[-2, 2:-2] = hx('8e98ae'); b[2:-2, -2] = hx('8e98ae')
b[2:-2, 2:-2] = hx('05060a')
for (y, x) in [(0, 0), (0, 1), (1, 0), (0, bw_ - 1), (0, bw_ - 2), (1, bw_ - 1), (bh_ - 1, 0), (bh_ - 2, 0), (bh_ - 1, 1), (bh_ - 1, bw_ - 1), (bh_ - 2, bw_ - 1), (bh_ - 1, bw_ - 2)]:
    b[y, x] = 0
b[1, 1] = hx('0c0a12'); b[1, -2] = hx('0c0a12'); b[-2, 1] = hx('0c0a12'); b[-2, -2] = hx('0c0a12')
b[2, 2] = hx('3a4050'); b[2, 3] = hx('20242e'); b[3, 2] = hx('20242e')   # glass glint corner
Image.fromarray(b).save(OUT + 'wbox.png')

# ---------------------------------------------------------------- ammo pips (frame 0 lit, frame 1 empty), 4x8 each
pip = np.zeros((8, 8, 4), np.uint8)
lit = ['fff2a0', 'ffd850', 'ffc030', 'ffa820', 'f89010', 'e07008']
dim = ['5a4a3a', '4a3c30', '42362c', '3a3028', '342a24', '2e2620']
for f, ramp in enumerate([lit, dim]):
    x0 = f * 4
    pip[:, x0:x0 + 4] = hx('0c0a12')
    for y in range(6):
        pip[1 + y, x0 + 1] = hx(ramp[y]); pip[1 + y, x0 + 2] = hx(ramp[min(5, y + 1)])
Image.fromarray(pip).save(OUT + 'pip.png')

# ---------------------------------------------------------------- menu cursor (triangle) 7x9
CUR = ['yK.....', 'yyK....', 'yWyK...', 'yWyyK..', 'yyyyyK.', 'yyyyyyK', 'YYYYYK.', 'YYYYK..', 'YYYK...', 'YYK....', 'YK.....']
Image.fromarray(art(CUR, {'K': '0c0a12', 'W': 'fff0a0', 'y': 'ffb020', 'Y': 'e86010'})).save(OUT + 'cursor.png')
print('ok')
