# Trace the mockup sheep onto the game grid: GrabCut the sheep out of its mockup, then palette-locked mode downsample.
import sys, numpy as np, cv2
sys.path.insert(0, 'art/raw/hero')
from PIL import Image
from px import to_index, downsample, render, IDX, crop_idx
from rast import ring, dil

SRC = {
    # name: (file, rect x0,y0,x1,y1 in mockup px, scale mockup px per game px)
    'run_fire': ('ref/2b740dbd-0be0-42e5-92bb-1abc9aef6bc9.png', (335, 350, 582, 532), 3.85),
    'jump_dup': ('ref/369c595b-d6f6-4f08-9cbb-a2729370ed58.png', (350, 262, 645, 452), 3.85),
    'stand_fire_c0f6': ('ref/c0f6f4b1-4af2-410f-838a-9f2d25a3fa36.png', (395, 398, 562, 540), 3.85),
    'sheet_idle': ('ref/3c485156-1ab2-4472-a273-76e378d5eb05.png', (10, 325, 425, 795), 9.6),
    'sheet_run': ('ref/3c485156-1ab2-4472-a273-76e378d5eb05.png', (485, 355, 965, 795), 9.6),
    'sheet_shoot': ('ref/3c485156-1ab2-4472-a273-76e378d5eb05.png', (955, 355, 1395, 795), 9.6),
}

def grab(name):
    f, (x0, y0, x1, y1), sc = SRC[name]
    im = np.array(Image.open(f).convert('RGB'))
    pad = 12
    X0, Y0, X1, Y1 = max(0, x0 - pad), max(0, y0 - pad), min(im.shape[1], x1 + pad), min(im.shape[0], y1 + pad)
    sub = im[Y0:Y1, X0:X1].copy()
    bgr = cv2.cvtColor(sub, cv2.COLOR_RGB2BGR)
    mask = np.full(sub.shape[:2], cv2.GC_BGD, np.uint8)
    mask[y0 - Y0:y1 - Y0, x0 - X0:x1 - X0] = cv2.GC_PR_FGD
    r, g, b = [sub[..., i].astype(int) for i in range(3)]
    lum = (r + g + b) / 3
    cream = (r > 180) & (g > 160) & (b > 100) & (r - b > 25) & (r - b < 120)
    red = (r > 150) & (g < 70) & (b < 70)
    gold = (r > 170) & (g > 110) & (b < 70) & (r - g < 90)
    grey = (abs(r - g) < 14) & (abs(g - b) < 22) & (lum > 60) & (lum < 150)
    sure = cream | red | gold | grey
    inside = np.zeros_like(sure); inside[y0 - Y0:y1 - Y0, x0 - X0:x1 - X0] = True
    mask[sure & inside & (cv2.erode(sure.astype(np.uint8), np.ones((3, 3))) > 0)] = cv2.GC_FGD
    if 'sheet' in name:
        bg = (lum < 45) & ~((abs(r - g) < 14) & (abs(g - b) < 25) & (lum > 25))
        mask[bg & ~dil(dil(sure))] = cv2.GC_PR_BGD
    bgd = np.zeros((1, 65), np.float64); fgd = np.zeros((1, 65), np.float64)
    cv2.grabCut(bgr, mask, None, bgd, fgd, 6, cv2.GC_INIT_WITH_MASK)
    fg = (mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD)
    n, lab, st, _ = cv2.connectedComponentsWithStats(fg.astype(np.uint8), 8)
    if n > 1:
        big = 1 + np.argmax(st[1:, cv2.CC_STAT_AREA]); fg = lab == big
    # fill holes
    ff = fg.astype(np.uint8).copy(); h, w = ff.shape
    m2 = np.zeros((h + 2, w + 2), np.uint8); cv2.floodFill(ff, m2, (0, 0), 2)
    fg = fg | (ff == 0)
    rgba = np.dstack([sub, (fg * 255).astype(np.uint8)])
    return Image.fromarray(rgba, 'RGBA'), sc

def trace(name, dark_bias=0.42, out=None):
    im, sc = grab(name)
    idx = to_index(im)
    best = None
    for ox in np.arange(0, sc, sc / 4):
        for oy in np.arange(0, sc, sc / 4):
            d = downsample(idx, sc, sc, ox, oy, dark_bias=dark_bias)
            score = (d >= 0).sum()
            best = d if best is None else best
            break
        break
    d = crop_idx(best)
    d = np.pad(d, 1, constant_values=-1)
    # clean: drop stray outline, then a crisp 1px outline all round
    O = IDX['ol']
    body = (d >= 0) & (d != O)
    d[(d == O) & ~dil(body, True)] = -1
    d[ring(d >= 0)] = O
    if out:
        np.save(out, d); render(d).save(out.replace('.npy', '.png'))
    return d, im

if __name__ == '__main__':
    import os
    os.makedirs('art/raw/hero/trace', exist_ok=True)
    for n in (sys.argv[1:] or SRC):
        d, im = trace(n, out=f'art/raw/hero/trace/{n}.npy')
        im.save(f'art/raw/hero/trace/{n}_cut.png')
        print(n, d.shape)
