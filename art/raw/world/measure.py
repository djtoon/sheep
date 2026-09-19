"""Measure value/saturation/hue/local-contrast per depth band. Rects are in 480x270 game px.
python art/raw/world/measure.py [shot_1x.png ...]"""
import sys, colorsys, numpy as np
from PIL import Image
R = 'ref/'
REFS = {
 '2b74': ('2b740dbd-0be0-42e5-92bb-1abc9aef6bc9', {'far': [(190, 0, 350, 30)], 'mid': [(180, 30, 360, 100), (190, 100, 300, 140)], 'near': [(0, 150, 190, 210)]}),
 'c0f6': ('c0f6f4b1-4af2-410f-838a-9f2d25a3fa36', {'far': [(85, 30, 165, 75)], 'mid': [(180, 40, 270, 125), (270, 45, 330, 90)], 'near': [(0, 155, 185, 235)]}),
 '369c': ('369c595b-d6f6-4f08-9cbb-a2729370ed58', {'far': [(280, 20, 350, 55)], 'mid': [(280, 55, 350, 165)], 'near': [(0, 160, 130, 235), (270, 215, 480, 270)]}),
 'fd55': ('fd55139a-01e5-4131-9ed2-79a9e02c5ecb', {'far': [(215, 20, 325, 50)], 'mid': [(210, 50, 330, 75), (0, 60, 160, 130)], 'near': [(0, 195, 220, 260)]}),
}
OURS = {  # per x position (re-picked for the raised ground, round 12). bg1 = closest backdrop jungle band
 '2300': {'far': [(280, 47, 320, 65)], 'mid': [(187, 95, 350, 147)], 'bg1': [(5, 45, 65, 140)], 'near': [(20, 160, 130, 260)]},
 '900': {'far': [(200, 43, 266, 67)], 'mid': [(230, 50, 300, 130)], 'near': [(310, 160, 470, 260)]},
 '3900': {'far': [(157, 43, 207, 83)], 'mid': [(430, 60, 480, 160)], 'near': [(0, 160, 190, 265)]},
}
def g480(path):
    im = Image.open(path).convert('RGB')
    if im.size != (480, 270): im = im.resize((480, 270), Image.BOX)
    return np.array(im).astype(np.float32) / 255
def stats(a, rects):
    px = []; lc = []
    for x0, y0, x1, y1 in rects:
        c = a[y0:y1, x0:x1]
        hsv = np.array([colorsys.rgb_to_hsv(*p) for p in c.reshape(-1, 3)])
        px.append(hsv)
        v = c.max(-1)
        for y in range(0, v.shape[0] - 7, 8):
            for x in range(0, v.shape[1] - 7, 8): lc.append(v[y:y + 8, x:x + 8].std())
    h = np.concatenate(px)
    ang = h[:, 0] * 2 * np.pi; w = h[:, 1]
    hue = (np.degrees(np.arctan2((np.sin(ang) * w).sum(), (np.cos(ang) * w).sum())) + 360) % 360
    q = lambda x: (np.percentile(x, 10), np.median(x), np.percentile(x, 90))
    return dict(V=q(h[:, 2]), S=q(h[:, 1]), hue=hue, lc=np.median(lc))
def fmt(d):
    return 'V %.2f [%.2f-%.2f] | S %.2f [%.2f-%.2f] | hue %3.0f | lc %.3f' % (d['V'][1], d['V'][0], d['V'][2], d['S'][1], d['S'][0], d['S'][2], d['hue'], d['lc'])
if __name__ == '__main__':
    if len(sys.argv) == 1:
        for k, (f, bands) in REFS.items():
            a = g480(R + f + '.png')
            for b, r in bands.items(): print(k, b.ljust(4), fmt(stats(a, r)))
    else:
        for p in sys.argv[1:]:
            key = [k for k in OURS if ('x' + k + '_') in p][0]
            a = g480(p)
            for b, r in OURS[key].items(): print(key, b.ljust(4), fmt(stats(a, r)))
