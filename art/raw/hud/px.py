# pixel-art downscaler used for the title layers: per-cell median of the cell core (keeps edges crisp), then palette quantize.
import numpy as np, sys
from PIL import Image
def cellmed(src, w, h, core=0.6):
    a = np.array(src).astype(np.float32); H, W = a.shape[:2]; out = np.zeros((h, w, a.shape[2]), np.float32)
    for j in range(h):
        y0 = H*j/h; y1 = H*(j+1)/h; cy=(y0+y1)/2; ry=max(0.5,(y1-y0)*core/2)
        ys = slice(int(cy-ry), int(np.ceil(cy+ry)))
        for i in range(w):
            x0 = W*i/w; x1 = W*(i+1)/w; cx=(x0+x1)/2; rx=max(0.5,(x1-x0)*core/2)
            p = a[ys, int(cx-rx):int(np.ceil(cx+rx))].reshape(-1, a.shape[2])
            out[j, i] = np.median(p, 0)
    return out
def quant(rgb, n, mask=None):
    arr = rgb.copy()
    sel = arr[mask] if mask is not None else arr.reshape(-1,3)
    q = Image.fromarray(sel.reshape(1,-1,3).astype(np.uint8)).quantize(colors=n, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE).convert('RGB')
    q = np.array(q).reshape(-1,3)
    if mask is not None: arr[mask] = q
    else: arr = q.reshape(arr.shape)
    return arr
def bbox(a, thr=100):
    ys, xs = np.where(a[..., 3] > thr); return xs.min(), ys.min(), xs.max()+1, ys.max()+1
def sprite(inp, out, w=None, h=None, colors=32, thr=0.5, outline=None, crop=None):
    im = Image.open(inp).convert('RGBA'); a = np.array(im)
    if crop: im = im.crop(crop); a = np.array(im)
    x0,y0,x1,y1 = bbox(a); im = im.crop((x0,y0,x1,y1)); W,H = im.size
    if w and not h: h = round(H*w/W)
    if h and not w: w = round(W*h/H)
    # premultiply for colour so transparent fringe doesn't bleed
    c = cellmed(im, w, h)
    al = c[...,3]/255; m = al >= thr
    rgb = quant(np.clip(c[...,:3],0,255), colors, m)
    o = np.zeros((h,w,4),np.uint8); o[...,:3]=rgb; o[...,3]=np.where(m,255,0)
    if outline:
        col = [int(outline[i:i+2],16) for i in (0,2,4)]
        pad = np.zeros((h+2,w+2,4),np.uint8); pad[1:-1,1:-1]=o; mm = pad[...,3]>0
        n = np.zeros_like(mm); n[1:]|=mm[:-1]; n[:-1]|=mm[1:]; n[:,1:]|=mm[:,:-1]; n[:,:-1]|=mm[:,1:]
        pad[n&~mm] = (*col,255); o = pad
    Image.fromarray(o,'RGBA').save(out); print(out, o.shape[1], o.shape[0])
def plate(inp, out, w, h, colors=64):
    im = Image.open(inp).convert('RGB')
    c = cellmed(im, w, h); rgb = quant(np.clip(c,0,255), colors)
    Image.fromarray(rgb.astype(np.uint8)).save(out); print(out)
