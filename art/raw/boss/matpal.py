"""Per-material palette lock for the boss art: each pixel is classified by hue/saturation into a material
(concrete, steel, hazard yellow, red, moss, olive, amber light) and snapped to that material's short, hard ramp.
Luminance is contrast-stretched per material so planes read as lit top / mid front / dark underside."""
import numpy as np, colorsys
H = lambda s: tuple(int(s[i:i + 2], 16) for i in (0, 2, 4))
RAMPS = {
    'concrete': [H('2e2a28'), H('4d4843'), H('6f685f'), H('948b7e'), H('b9ae9c'), H('dcd2bd')],
    'steel':    [H('16151c'), H('262630'), H('3a3b46'), H('555864'), H('7a7f8c'), H('a6abb6')],
    'yellow':   [H('4a3812'), H('8a6a1c'), H('c99722'), H('f0c54a')],
    'red':      [H('3e0c0e'), H('741414'), H('b01e18'), H('e23a20'), H('ff7a40'), H('ffd89a')],
    'moss':     [H('1b2e16'), H('2f5020'), H('4c7a2a'), H('78a83a')],
    'olive':    [H('2e3320'), H('4a5230'), H('6c7444'), H('949a60')],
    'amber':    [H('7a4a14'), H('d88a2a'), H('ffd070'), H('fff4c8')],
}

CONTRAST = 1.2
RANGE = {'concrete': (40, 200), 'steel': (10, 130), 'yellow': (50, 200), 'red': (25, 230), 'moss': (20, 150), 'olive': (30, 150), 'amber': (110, 255)}


def classify(r, g, b):
    h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255); h *= 360
    if s > 0.45 and v > 0.25 and (h < 18 or h > 335): return 'red'
    if s > 0.5 and v > 0.75 and 18 <= h < 50: return 'amber'
    if s > 0.45 and 30 <= h < 54: return 'yellow'
    if s > 0.3 and 75 <= h < 150: return 'moss' if s > 0.42 else 'olive'
    if s > 0.2 and 40 <= h < 90: return 'olive'
    if v < 0.22: return 'steel'
    return 'concrete' if (r >= b - 2) else 'steel'


def lock(a, gamma=1.0):
    """a: HxWx4 uint8 -> palette-locked copy."""
    o = a.copy(); m = a[..., 3] > 0
    ys, xs = np.where(m)
    mats = np.empty(len(ys), object); lum = np.zeros(len(ys))
    for k, (y, x) in enumerate(zip(ys, xs)):
        r, g, b = (int(c) for c in a[y, x, :3]); mats[k] = classify(r, g, b); lum[k] = 0.3 * r + 0.59 * g + 0.11 * b
    for name, ramp in RAMPS.items():
        sel = mats == name
        if not sel.any(): continue
        L = lum[sel]; mu = L.mean()
        L = mu + (L - mu) * CONTRAST                     # mild per-material contrast boost, values stay absolute
        rl = np.array([0.3 * r + 0.59 * g + 0.11 * b for r, g, b in ramp])
        idx = np.abs(L[:, None] - rl[None, :]).argmin(1)
        cols = np.array(ramp, np.uint8)[idx]
        o[ys[sel], xs[sel], :3] = cols
    return o


def crisp(o):
    """darken 1-px valleys (panel seams) one ramp step so lines read crisply."""
    lum = o[..., :3].astype(np.float32) @ np.array([0.3, 0.59, 0.11]); m = o[..., 3] > 0; out = o.copy()
    h, w = lum.shape
    for y in range(1, h - 1):
        for x in range(1, w - 1):
            if not m[y, x]: continue
            c = lum[y, x]
            if (lum[y, x - 1] - c > 26 and lum[y, x + 1] - c > 26) or (lum[y - 1, x] - c > 26 and lum[y + 1, x] - c > 26):
                out[y, x, :3] = (out[y, x, :3] * 0.72).astype(np.uint8)
    return out
