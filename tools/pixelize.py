"""Clean an AI-generated image into a pixel-perfect sprite.
usage: python tools/pixelize.py IN OUT --h 44 [--w W] [--colors 24] [--alpha 128] [--outline 1a1420] [--crop] [--palette pal.png]
 - crops to the opaque bounding box (--crop, default on for alpha images)
 - downsamples to the target size (height or width; aspect kept) with a mode-preserving box filter
 - hard alpha threshold, palette quantization (median cut, or a supplied palette image)
 - optional 1px dark outline around the silhouette
Also: --sheet a,b,c  packs several already-clean frames into one horizontal strip with equal cell size (bottom-aligned).
"""
import argparse, sys
import numpy as np
from PIL import Image

def load(p):
    return Image.open(p).convert('RGBA')

def bbox(im, thr=40):
    a = np.array(im)[..., 3]
    ys, xs = np.where(a > thr)
    if not len(xs): return (0, 0, im.width, im.height)
    return (xs.min(), ys.min(), xs.max() + 1, ys.max() + 1)

def downsample(im, w, h):
    # premultiplied area average for colour, separate for alpha -> avoids dark fringes
    a = np.array(im).astype(np.float32) / 255
    rgb = a[..., :3] * a[..., 3:4]
    pre = Image.fromarray((np.concatenate([rgb, a[..., 3:4]], -1) * 255).astype(np.uint8), 'RGBA')
    small = np.array(pre.resize((w, h), Image.BOX)).astype(np.float32) / 255
    al = small[..., 3:4]
    col = np.where(al > 1e-3, small[..., :3] / np.maximum(al, 1e-3), 0)
    return np.concatenate([np.clip(col, 0, 1), al], -1)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('inp'); ap.add_argument('out')
    ap.add_argument('--h', type=int); ap.add_argument('--w', type=int)
    ap.add_argument('--colors', type=int, default=32)
    ap.add_argument('--alpha', type=float, default=0.5)
    ap.add_argument('--outline', default=None)
    ap.add_argument('--nocrop', action='store_true')
    ap.add_argument('--palette', default=None)
    ap.add_argument('--opaque', action='store_true', help='ignore alpha (backgrounds)')
    a = ap.parse_args()
    im = load(a.inp)
    if a.opaque:
        im.putalpha(255)
    elif not a.nocrop:
        im = im.crop(bbox(im))
    W, H = im.size
    if a.h and a.w: w, h = a.w, a.h
    elif a.h: h = a.h; w = max(1, round(W * a.h / H))
    elif a.w: w = a.w; h = max(1, round(H * a.w / W))
    else: sys.exit('need --h or --w')
    px = downsample(im, w, h)
    alpha = px[..., 3] >= a.alpha
    rgb = Image.fromarray((px[..., :3] * 255).astype(np.uint8), 'RGB')
    if a.palette:
        pal = Image.open(a.palette).convert('RGB').quantize(colors=256)
        q = rgb.quantize(palette=pal, dither=Image.Dither.NONE).convert('RGB')
    else:
        # quantize only the opaque pixels
        arr = np.array(rgb); sel = arr[alpha]
        if len(sel):
            strip = Image.fromarray(sel.reshape(1, -1, 3))
            qs = strip.quantize(colors=a.colors, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE).convert('RGB')
            arr[alpha] = np.array(qs).reshape(-1, 3)
        q = Image.fromarray(arr)
    out = np.zeros((h, w, 4), np.uint8)
    out[..., :3] = np.array(q); out[..., 3] = np.where(alpha, 255, 0)
    if a.outline:
        c = tuple(int(a.outline[i:i + 2], 16) for i in (0, 2, 4))
        pad = np.zeros((h + 2, w + 2, 4), np.uint8); pad[1:-1, 1:-1] = out
        m = pad[..., 3] > 0
        n = np.zeros_like(m)
        n[1:, :] |= m[:-1, :]; n[:-1, :] |= m[1:, :]; n[:, 1:] |= m[:, :-1]; n[:, :-1] |= m[:, 1:]
        ring = n & ~m
        pad[ring] = (*c, 255)
        out = pad
    Image.fromarray(out, 'RGBA').save(a.out)
    print(a.out, out.shape[1], 'x', out.shape[0])

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--sheet':
        # python tools/pixelize.py --sheet OUT f1.png f2.png ...  -> equal cells, bottom-centre aligned
        out, files = sys.argv[2], sys.argv[3:]
        ims = [load(f) for f in files]
        cw = max(i.width for i in ims); ch = max(i.height for i in ims)
        sheet = Image.new('RGBA', (cw * len(ims), ch))
        for k, i in enumerate(ims):
            sheet.paste(i, (k * cw + (cw - i.width) // 2, ch - i.height))
        sheet.save(out); print(out, 'frame', cw, 'x', ch, 'frames', len(ims))
    else:
        main()
