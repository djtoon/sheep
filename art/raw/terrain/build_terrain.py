"""Build all terrain art in assets/terrain from the raw generations in art/raw/terrain.
python art/raw/terrain/build_terrain.py  (writes PNGs + assets/terrain/pieces.json with sizes/anchors)"""
import json, os, sys
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(__file__))
import px

META = {}


def piece(name, arr, **meta):
    px.save(arr, name + '.png')
    META[name] = {'w': int(arr.shape[1]), 'h': int(arr.shape[0]), **meta}
    return arr


def sc(arr, f):
    """downscale by factor f (raw px per game px)"""
    h, w = arr.shape[:2]
    return px.down(arr, max(1, round(w / f)), max(1, round(h / f)))


def comp(sheet, box, f, q=True, **kw):
    a = sheet[box[1]:box[3], box[0]:box[2]]
    a = sc(a, f)
    a = px.quant(a, **kw) if q else a
    return px.crop_alpha(a)


def seamless_x(a, blend=12):
    """make a horizontally wrapping strip by cross-blending the ends (opaque rows) then trimming"""
    h, w = a.shape[:2]
    out = a[:, :w - blend].copy()
    for i in range(blend):
        t = (i + 0.5) / blend
        src = a[:, w - blend + i].astype(np.float32)
        dst = out[:, i].astype(np.float32)
        mix = src * (1 - t) + dst * t
        # alpha: take whichever dominates
        mix[:, 3] = np.where(t < 0.5, src[:, 3], dst[:, 3])
        out[:, i] = mix.astype(np.uint8)
    return out


def seamless_y(a, blend=16):
    return np.ascontiguousarray(seamless_x(a.transpose(1, 0, 2), blend).transpose(1, 0, 2))


def main():
    L = px.load
    # ---- cliff face (seamless 256 tile) and a darker variant
    cliff = px.quant(px.down(L('cliff_1.png'), 256, 256))
    piece('cliff', cliff)
    # ---- grass strip (native ~8px grid) ; wrap-blend the ends
    g = L('grass_1.png')[370:830]
    g = px.down(g, 256, round(460 / 8))
    g = seamless_x(g, 16)
    g = px.quant(g, sat=1.05)
    piece('grass', g, top=int(np.where(g[..., 3].any(1))[0].min()))
    # ---- grass corner caps from the cliff block (green pixels only)
    cb = L('cliffblock_1.png')[223:911, 39:1497]
    cbs = px.quant(px.down(cb, 182, 86))
    r, gg, b = [cbs[..., i].astype(int) for i in range(3)]
    green = (gg > r + 8) & (gg > b + 8) & (cbs[..., 3] > 0)
    dark = (r + gg + b < 110) & (cbs[..., 3] > 0)
    cap = cbs.copy(); cap[..., 3] = np.where(green | (dark & np.roll(green, 1, 0)), 255, 0)
    piece('cap-l', px.crop_alpha(cap[:, :30]))
    piece('cap-r', px.crop_alpha(cap[:, -30:]))
    piece('cliffblock', cbs)
    # ---- concrete tile
    con = px.quant(px.down(L('concrete_1.png'), 128, 128))
    piece('concrete', con)
    # ---- waterfall: lip strip + vertically-wrapping fall column
    fl = L('falllip_1.png')
    lip = px.quant(px.down(fl[250:1152], 256, round(902 / 8)))
    piece('falls-lip', lip)
    col = fl[560:1152]
    colp = px.down(col, 256, round(592 / 8))
    colp[..., 3] = 255
    colp = seamless_y(colp, 26)
    piece('falls', px.quant(colp))
    # ---- pool strip
    pl = L('pool_1.png')[590:1152]
    pls = px.down(pl, 256, round(562 / 8))
    pls = seamless_x(pls, 16)
    piece('pool', px.quant(pls))
    # ---- sprite sheets -> individual pieces
    vines = L('vines_1.png')
    for i, bx in enumerate(px.components(vines, 800)):
        piece(f'vine{i}', comp(vines, bx, 8))
    bushes = L('bushes_1.png')
    for i, bx in enumerate(px.components(bushes, 800)):
        piece(f'bush{i}', comp(bushes, bx, 9))
    rocks = L('rocks_1.png')
    for i, bx in enumerate(px.components(rocks, 800)):
        piece(f'rock{i}', comp(rocks, bx, 8))
    bun = L('bunker_1.png')
    piece('bunker', comp(bun, (44, 36, 1500, 977), 7.2))
    bun2 = L('bunker_2.png')
    piece('bunker2', comp(bun2, (61, 36, 1475, 976), 7.2))
    # props1: crate, eagle crate, ammo, sandbags, drum, ladder, banner, stack
    p1 = L('props1_1.png')
    b = px.components(p1)
    names = {0: ('crate-eagle', 8.5), 1: ('crate', 9), 2: ('ammo', 7), 3: ('sandbags', 8),
             4: ('drum', 15), 5: ('ladder', 10), 6: ('banner', 8.5), 7: ('crates2', 9)}
    for i, bx in enumerate(b):
        if i in names:
            n, f = names[i]
            piece(n, comp(p1, bx, f))
    p1b = L('props1_2.png')
    b2 = px.components(p1b)
    print('props1_2', b2)
    # props2
    p2 = L('props2_1.png')
    for i, (n, f) in enumerate([('doorway', 7), ('door-eagle', 7), ('fence', 6.5), ('catwalk-raw', 5.5), ('tower', 6), ('lamp', 9)]):
        piece(n, comp(p2, px.components(p2)[i], f))
    # chain-link: replace the (opaque after downscale) mesh with a see-through diamond lattice
    f = px.load(os.path.join(px.OUT, 'fence.png'))
    for y in range(10, 49):
        for x in range(6, 53):
            if 18 <= x <= 38 and 21 <= y <= 31:
                continue  # A-01 sign
            wire = (x + y) % 4 == 0 or (x - y) % 4 == 0
            f[y, x] = (104, 112, 118, 255) if wire and (x + y) % 2 == 0 else (66, 72, 80, 255) if wire else (0, 0, 0, 0)
    piece('fence', f)
    fp = f.copy()
    for y in range(10, 49):
        for x in range(6, 53):
            if 18 <= x <= 38 and 20 <= y <= 32:
                wire = (x + y) % 4 == 0 or (x - y) % 4 == 0
                fp[y, x] = (104, 112, 118, 255) if wire and (x + y) % 2 == 0 else (66, 72, 80, 255) if wire else (0, 0, 0, 0)
    piece('fence-plain', fp)
    p22 = L('props2_2.png')
    for i, (n, f) in enumerate([('bigdoor', 6.5), ('door2', 7), ('tower2', 7), ('fence2', 7), ('catwalk2-raw', 6), ('lamp2', 6)]):
        piece(n, comp(p22, px.components(p22)[i], f))
    # bridges
    br = L('bridges_1.png')
    piece('ropebridge', comp(br, (66, 112, 1467, 536), 8))
    piece('steelbridge-raw', comp(br, (66, 684, 1468, 909), 8))
    # foreground leaves
    lv = L('leaves_1.png')
    piece('fg-leaves-l', comp(lv, (3, 169, 676, 1021), 6.5))
    piece('fg-leaves-r', comp(lv, (937, 219, 1533, 1021), 6.5))
    lv2 = L('leaves_2.png')
    piece('fg-leaves-l2', comp(lv2, (3, 217, 662, 1021), 6.5))
    piece('fg-leaves-r2', comp(lv2, (959, 384, 1533, 1021), 6.5))
    json.dump(META, open(os.path.join(px.OUT, 'pieces.json'), 'w'), indent=1)
    print(len(META), 'pieces')


if __name__ == '__main__':
    main()
