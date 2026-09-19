# Builds the comic panel art (assets/story/<id>.png) from the raw generations, sized panel + pan margin,
# with a per-cell median downsample and per-panel palette quantize so every panel is crisp pixel art at game scale.
# run from repo root: python art/raw/story/build_story.py
import json, sys, numpy as np
from PIL import Image, ImageFilter
sys.path.insert(0, 'art/raw/hud')
from px import cellmed, quant
R, O = 'art/raw/story/', 'assets/story/'
ZOOM = {'p3': (0.56, 0.515, 0.56), 'p4': (0.47, 0.44, 0.9)}   # (centre x, centre y, crop width fraction) for tighter framing
LIFT = {'p4': 1.18}                                           # brighten the hero's wool in dark panels
FOCUS = {'p4': (0.5, 0.55), 'p9': (0.5, 0.4), 'p5': (0.5, 0.35), 'p6': (0.5, 0.4), 'e3': (0.5, 0.35), 'p2': (0.5, 0.4)}
L = json.load(open(R + 'layout.json'))
for page in L['pages'] + L['ending']:
    for p in page:
        W = p['w'] + abs(p['pan'][0]); H = p['h'] + abs(p['pan'][1])
        im = Image.open(R + p['src'] + '.png').convert('RGB')
        iw, ih = im.size; s = max(W / iw, H / ih)
        cw, ch = W / s, H / s
        fx, fy = FOCUS.get(p['id'], (0.5, 0.5))
        if p['id'] in ZOOM:
            fx, fy, wf = ZOOM[p['id']]; cw = wf * iw; ch = cw * H / W
            if ch > ih: ch = ih; cw = ch * W / H
        x0 = min(max(0, fx * iw - cw / 2), iw - cw); y0 = min(max(0, fy * ih - ch / 2), ih - ch)
        c = im.crop((round(x0), round(y0), round(x0 + cw), round(y0 + ch)))
        c = c.filter(ImageFilter.UnsharpMask(radius=2, percent=60, threshold=2))
        a = cellmed(c, W, H, core=0.55)
        if p['id'] in LIFT:
            r_, g_, b_ = a[..., 0], a[..., 1], a[..., 2]
            wool = (r_ > 140) & (g_ > 110) & ((r_ - b_) > 25) & ((r_ - g_) < 70)
            a[wool, :3] = np.minimum(255, a[wool, :3] * LIFT[p['id']] + 10)
            a[..., :3] = 255 * (a[..., :3] / 255) ** 0.88           # lift the dark bunker a little
        q = quant(np.clip(a, 0, 255), 64)
        Image.fromarray(q.astype(np.uint8)).save(O + p['id'] + '.png')
        print(p['id'], W, H)
json.dump(L, open(O + 'layout.json', 'w'))

# drop-in chopper: 2 frames (tail rotor on / flickered), main rotor blades removed (drawn animated in code)
sys.path.insert(0, 'art/raw/hud')
from px import sprite
sprite(R + 'chopper_1.png', R + 'chopper_px.png', w=104, colors=32)
c = np.array(Image.open(R + 'chopper_px.png'))
c[1:3, :57] = 0; c[1:3, 69:] = 0            # main rotor blade bar (hub at x 57..68 stays)
c[1:3, 57:69][..., 3] = np.where(c[1:3, 57:69][..., 3] > 0, 255, 0)
f2 = c.copy(); f2[0:11, 0:13] = 0; f2[5:7, 4:8] = c[5:7, 4:8]
Image.fromarray(np.concatenate([c, f2], 1)).save(O + 'chopper.png')
print('chopper', c.shape)

# recon panel: paint out the black officer-silhouette heads rising from the bottom edge by cloning the jungle /
# screen pixels directly above each one (hard pixel copy, no blur).
from scipy import ndimage
a = np.array(Image.open(O + 'p3.png').convert('RGB'))
H3, W3 = a.shape[:2]
dark = a.astype(int).sum(-1) < 70
lab, n = ndimage.label(dark)
for i in range(1, n + 1):
    ys, xs = np.where(lab == i)
    if ys.max() != H3 - 1 or len(xs) < 80: continue
    m = ndimage.binary_dilation(lab == i, iterations=2)
    top = ys.min() - 2; hgt = H3 - top
    for y, x in zip(*np.where(m)):
        sy = y - hgt
        while sy >= 0 and m[sy, x]: sy -= hgt
        if sy >= 0: a[y, x] = a[sy, x]
Image.fromarray(a).save(O + 'p3.png'); print('p3 silhouettes painted out')
