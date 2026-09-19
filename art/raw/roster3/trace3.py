# Trace the stage-3 roster units from ref/levels/enemy2.png onto a strict game-scale pixel grid.
# grabcut the unit off the dark backdrop -> per-unit k-means palette (+ near-black outline) -> mode downsample -> 1px outline.
import sys, os, numpy as np, cv2
from PIL import Image
REF = 'ref/levels/enemy2.png'
UNITS = {  # name: (x0,y0,x1,y1) in enemy2.png, source px per game px, palette size
    'hazmat':  ((78, 135, 472, 512), 9.3, 13),
    'clawbot': ((560, 88, 948, 448), 10.0, 12),
    'toxic':   ((1035, 105, 1475, 512), 9.8, 14),
    'xeno':    ((40, 610, 548, 955), 9.3, 11),
    'mutant':  ((575, 510, 965, 955), 8.1, 11),
    'walker':  ((1015, 575, 1505, 955), 6.4, 14),
}
OUT = 'art/raw/roster3'

def cut(name):
    (x0, y0, x1, y1), sc, k = UNITS[name]
    im = np.array(Image.open(REF).convert('RGB'))
    pad = 14
    X0, Y0, X1, Y1 = x0 - pad, y0 - pad, x1 + pad, y1 + pad
    sub = im[Y0:Y1, X0:X1].copy()
    r, g, b = [sub[..., i].astype(int) for i in range(3)]
    lum = (r + g + b) / 3; sat = sub.max(-1).astype(int) - sub.min(-1).astype(int)
    mask = np.full(sub.shape[:2], cv2.GC_BGD, np.uint8)
    mask[pad:-pad, pad:-pad] = cv2.GC_PR_FGD
    sure = ((lum > 95) | (sat > 70)) & (lum > 40)
    er = cv2.erode(sure.astype(np.uint8), np.ones((5, 5))) > 0
    mask[er & (mask == cv2.GC_PR_FGD)] = cv2.GC_FGD
    mask[(lum < 22) & (mask == cv2.GC_PR_FGD)] = cv2.GC_PR_BGD
    bgd = np.zeros((1, 65)); fgd = np.zeros((1, 65))
    cv2.grabCut(cv2.cvtColor(sub, cv2.COLOR_RGB2BGR), mask, None, bgd, fgd, 6, cv2.GC_INIT_WITH_MASK)
    fg = (mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD)
    # keep components that are big enough (claw arms can be separate blobs), fill holes
    n, lab, st, _ = cv2.connectedComponentsWithStats(fg.astype(np.uint8), 8)
    keep = np.zeros_like(fg)
    for i in range(1, n):
        if st[i, cv2.CC_STAT_AREA] > 900: keep |= lab == i
    ff = keep.astype(np.uint8); h, w = ff.shape; m2 = np.zeros((h + 2, w + 2), np.uint8)
    cv2.floodFill(ff, m2, (0, 0), 2); keep |= ff == 0
    return sub, keep, sc, k

def palette(sub, fg, k):
    px = sub[fg].reshape(-1, 3).astype(np.float32)
    crit = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 40, 0.5)
    _, lab, cen = cv2.kmeans(px, k, None, crit, 4, cv2.KMEANS_PP_CENTERS)
    cen = cen.astype(np.float32)
    # snap the darkest centre to the shared outline colour
    d = cen.sum(1); i = int(d.argmin()); cen[i] = (12, 10, 18)
    return cen

GEN = {'clawbot': ('art/raw/roster3/src/clawbot_gen_1.png', 42), 'toxic': ('art/raw/roster3/src/toxic_gen_1.png', 41),
       'walker': ('art/raw/roster3/src/walker_gen_1.png', 60)}
def cut_gen(name):
    f, target = GEN[name]
    a = np.array(Image.open(f).convert('RGBA'))
    ys, xs = np.where(a[..., 3] > 128)
    a = a[ys.min() - 4:ys.max() + 5, xs.min() - 4:xs.max() + 5]
    fg = a[..., 3] > 128
    sc = (ys.max() - ys.min() + 1) / target
    return a[..., :3].copy(), fg, sc, UNITS[name][2]
def trace(name, sc_override=None):
    sub, fg, sc, k = cut_gen(name) if name in GEN else cut(name)
    if sc_override: sc = sc_override
    cen = palette(sub, fg, k)
    H, W = fg.shape
    flat = sub.reshape(-1, 3).astype(np.float32)
    dist = ((flat[:, None, :] - cen[None]) ** 2 * np.array([0.3, 0.5, 0.2])).sum(-1)
    idx = dist.argmin(1).reshape(H, W); idx[~fg] = -1
    OL = int(cen.sum(1).argmin())
    gh, gw = int(H / sc), int(W / sc)
    out = np.full((gh, gw), -1, np.int16)
    for j in range(gh):
        for i in range(gw):
            c = idx[int(j * sc):int((j + 1) * sc), int(i * sc):int((i + 1) * sc)].ravel()
            o = c[c >= 0]
            if o.size < c.size * 0.45: continue
            cnt = np.bincount(o, minlength=len(cen))
            out[j, i] = OL if cnt[OL] > o.size * 0.5 else (np.argmax(np.where(np.arange(len(cen)) == OL, 0, cnt)) if cnt.sum() - cnt[OL] > 0 else OL)
    ys, xs = np.where(out >= 0); out = out[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    out = np.pad(out, 1, constant_values=-1)
    body = (out >= 0) & (out != OL)
    dil = lambda m: m | np.roll(m, 1, 0) | np.roll(m, -1, 0) | np.roll(m, 1, 1) | np.roll(m, -1, 1)
    dil8 = lambda m: dil(m) | np.roll(np.roll(m, 1, 0), 1, 1) | np.roll(np.roll(m, 1, 0), -1, 1) | np.roll(np.roll(m, -1, 0), 1, 1) | np.roll(np.roll(m, -1, 0), -1, 1)
    out[(out == OL) & ~dil8(body)] = -1
    out[dil(body) & (out < 0)] = OL
    pal = np.vstack([cen, [[0, 0, 0]]]).astype(np.uint8)
    return out, pal, OL

def render(out, pal):
    h, w = out.shape; a = np.zeros((h, w, 4), np.uint8)
    m = out >= 0; a[m, :3] = pal[out[m]]; a[m, 3] = 255
    return Image.fromarray(a, 'RGBA')

if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    for n in (sys.argv[1:] or UNITS):
        out, pal, OL = trace(n)
        np.save(f'{OUT}/{n}.npy', out); np.save(f'{OUT}/{n}_pal.npy', pal)
        render(out, pal).save(f'{OUT}/{n}.png')
        print(n, out.shape)
