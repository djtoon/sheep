"""Terrain pixel helpers: crisp downscale + palette lock to the mockups.
Run from repo root. Used by build_terrain.py."""
import os
import numpy as np
from PIL import Image
from scipy import ndimage

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
RAW = os.path.join(ROOT, 'art', 'raw', 'terrain')
OUT = os.path.join(ROOT, 'assets', 'terrain')
REFS = ['2b740dbd-0be0-42e5-92bb-1abc9aef6bc9.png', 'c0f6f4b1-4af2-410f-838a-9f2d25a3fa36.png',
        '369c595b-d6f6-4f08-9cbb-a2729370ed58.png', 'fd55139a-01e5-4131-9ed2-79a9e02c5ecb.png']
_PAL = None


def palette(n=160):
    """Median-cut palette sampled from the four in-game mockups at game scale."""
    global _PAL
    if _PAL is not None:
        return _PAL
    cache = os.path.join(RAW, 'palette.png')
    if os.path.exists(cache):
        _PAL = np.array(Image.open(cache).convert('RGB')).reshape(-1, 3)
        return _PAL
    ims = []
    for r in REFS:
        im = Image.open(os.path.join(ROOT, 'ref', r)).convert('RGB')
        im = im.resize((im.width // 3, im.height // 3), Image.BOX)
        ims.append(np.array(im).reshape(-1, 3))
    allpx = np.concatenate(ims)[None]
    q = Image.fromarray(allpx.astype(np.uint8)).quantize(colors=n, method=Image.Quantize.MEDIANCUT)
    pal = np.array(q.getpalette()[:n * 3]).reshape(-1, 3)
    # concrete greys are under-represented in the mockups' median cut: add a neutral ramp
    extra = [(110, 111, 108), (136, 137, 132), (152, 153, 147), (170, 170, 163), (190, 189, 181), (208, 207, 199), (120, 116, 106), (146, 140, 128)]
    pal = np.concatenate([pal, np.array(extra)])
    Image.fromarray(pal.reshape(1, -1, 3).astype(np.uint8)).save(cache)
    _PAL = pal
    return pal


def load(name):
    p = name if os.path.isabs(name) else os.path.join(RAW, name)
    return np.array(Image.open(p).convert('RGBA'))


def down(arr, w, h, k=4, athr=0.5):
    """Downscale RGBA array to (w,h): box to (w*k,h*k) then per-cell median of opaque pixels."""
    im = Image.fromarray(arr)
    big = np.array(im.resize((w * k, h * k), Image.BOX)).astype(np.float32)
    cells = big.reshape(h, k, w, k, 4).transpose(0, 2, 1, 3, 4).reshape(h, w, k * k, 4)
    a = cells[..., 3]
    op = a > 127
    cov = op.mean(-1)
    rgb = cells[..., :3].copy()
    rgb[~op] = np.nan
    with np.errstate(all='ignore'):
        med = np.nanmedian(rgb, axis=2)
    med = np.nan_to_num(med)
    out = np.zeros((h, w, 4), np.uint8)
    out[..., :3] = np.clip(med, 0, 255)
    out[..., 3] = np.where(cov >= athr, 255, 0)
    return out


def quant(arr, pal=None, sat=1.0, bright=1.0):
    pal = palette() if pal is None else pal
    rgb = arr[..., :3].astype(np.float32)
    if sat != 1.0 or bright != 1.0:
        g = rgb.mean(-1, keepdims=True)
        rgb = np.clip((g + (rgb - g) * sat) * bright, 0, 255)
    flat = rgb.reshape(-1, 3)
    # perceptual-ish weighting
    wgt = np.array([0.30, 0.59, 0.11]) ** 0.5
    d = ((flat[:, None, :] - pal[None, :, :]) * wgt) ** 2
    idx = d.sum(-1).argmin(1)
    out = arr.copy()
    out[..., :3] = pal[idx].reshape(arr.shape[:2] + (3,))
    return out


def outline(arr, col=(18, 20, 28)):
    """Add a 1px dark outline outside the silhouette (grows by 1px each side)."""
    h, w = arr.shape[:2]
    pad = np.zeros((h + 2, w + 2, 4), np.uint8)
    pad[1:-1, 1:-1] = arr
    m = pad[..., 3] > 0
    ring = ndimage.binary_dilation(m, structure=[[0, 1, 0], [1, 1, 1], [0, 1, 0]]) & ~m
    pad[ring] = (*col, 255)
    return pad


def crop_alpha(arr, thr=0):
    ys, xs = np.where(arr[..., 3] > thr)
    return arr[ys.min():ys.max() + 1, xs.min():xs.max() + 1]


def components(arr, min_area=2000, thr=100):
    """Bounding boxes of separate opaque objects in a sprite sheet, reading order."""
    m = arr[..., 3] > thr
    m = ndimage.binary_closing(m, iterations=3)
    lab, n = ndimage.label(m)
    boxes = []
    for i, sl in enumerate(ndimage.find_objects(lab)):
        if sl is None:
            continue
        area = (lab[sl] == i + 1).sum()
        if area < min_area:
            continue
        boxes.append((sl[1].start, sl[0].start, sl[1].stop, sl[0].stop))
    boxes.sort(key=lambda b: (b[1] // 150, b[0]))
    return boxes


def save(arr, name):
    os.makedirs(OUT, exist_ok=True)
    Image.fromarray(arr).save(os.path.join(OUT, name))
    return arr
