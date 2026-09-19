# Palette-locked mode downsampler for AI pixel-art poses.
import numpy as np
from PIL import Image
PAL = {
 'ol':'0c0a12',
 'w0':'fffae6','w1':'f5e3b4','w2':'dcb87e','w3':'a87a48',
 'f0':'9d9aab','f1':'767386','f2':'585566','f3':'3e3b4c',
 'ew':'ffffff','p0':'f4a0a0','p1':'c86a78',
 'r0':'ff4a3a','r1':'e01414','r2':'9c0a1c',
 'g0':'ffe27a','g1':'e0a632','g2':'8e5e2c',
 'k0':'d4e4ff','k1':'343a4c','k2':'14161c',
 'o0':'c07a3c','o1':'7c4422',
 'l0':'dcdae4',
}
NAMES=list(PAL); RGB=np.array([[int(PAL[k][i:i+2],16) for i in (0,2,4)] for k in NAMES],np.float32)
IDX={k:i for i,k in enumerate(NAMES)}
def nearest(rgb):
    # weighted distance
    d=((rgb[:,None,:]-RGB[None])**2*np.array([0.35,0.45,0.2])).sum(-1)
    return d.argmin(1)
def to_index(im):
    a=np.array(im.convert('RGBA'))
    h,w=a.shape[:2]
    idx=nearest(a[...,:3].reshape(-1,3).astype(np.float32)).reshape(h,w)
    idx[a[...,3]<128]=-1
    return idx
def downsample(idx, sx, sy, ox=0, oy=0, W=None, H=None, dark_bias=0.34):
    h,w=idx.shape
    W=W or int((w-ox)/sx); H=H or int((h-oy)/sy)
    out=np.full((H,W),-1,np.int16)
    ol=IDX['ol']
    for j in range(H):
        y0=int(round(oy+j*sy)); y1=max(y0+1,int(round(oy+(j+1)*sy)))
        for i in range(W):
            x0=int(round(ox+i*sx)); x1=max(x0+1,int(round(ox+(i+1)*sx)))
            c=idx[y0:y1,x0:x1].ravel()
            if c.size==0: continue
            opq=c[c>=0]
            if opq.size < c.size*0.5: continue
            cnt=np.bincount(opq,minlength=len(NAMES))
            if cnt[ol] >= opq.size*dark_bias: out[j,i]=ol
            else:
                cnt[ol]=0; out[j,i]=cnt.argmax() if cnt.max()>0 else ol
    return out
def render(idx):
    h,w=idx.shape; o=np.zeros((h,w,4),np.uint8)
    m=idx>=0; o[m,:3]=RGB[idx[m]].astype(np.uint8); o[m,3]=255
    return Image.fromarray(o,'RGBA')
def crop_idx(idx):
    ys,xs=np.where(idx>=0); return idx[ys.min():ys.max()+1, xs.min():xs.max()+1]
def show(img_or_idx, path, s=8, bg=(70,110,70,255)):
    im=render(img_or_idx) if isinstance(img_or_idx,np.ndarray) else img_or_idx
    b=Image.new('RGBA',im.size,bg); b.alpha_composite(im); b.resize((im.width*s,im.height*s),Image.NEAREST).save(path)

def purity(idx, sx, sy, ox, oy):
    h,w=idx.shape
    yy=np.floor((np.arange(h)-oy)/sy).astype(int); xx=np.floor((np.arange(w)-ox)/sx).astype(int)
    vy=yy>=0; vx=xx>=0
    sub=idx[np.ix_(vy,vx)]; cy=yy[vy]; cx=xx[vx]
    W=cx.max()+1
    cell=(cy[:,None]*W+cx[None,:]).ravel(); col=sub.ravel()+1
    K=len(NAMES)+1
    key=cell*K+col
    cnt=np.bincount(key)
    cnt=cnt.reshape(-1,K) if cnt.size%K==0 else np.pad(cnt,(0,K-cnt.size%K)).reshape(-1,K)
    tot=cnt.sum(1); m=cnt.max(1); sel=tot>0
    # ignore fully transparent cells
    sel&= cnt[:,0]<tot
    return (m[sel].sum()/tot[sel].sum())
def best_grid(idx, s_lo, s_hi, step=0.1, aniso=True):
    best=(0,)
    for sx in np.arange(s_lo,s_hi,step):
        for sy in (np.arange(s_lo,s_hi,step) if aniso else [sx]):
            for ox in np.arange(0,sx,1.0):
                for oy in np.arange(0,sy,1.0):
                    p=purity(idx,sx,sy,ox,oy)
                    if p>best[0]: best=(p,sx,sy,ox,oy)
    return best

CH='#ABCDabcdWpqRSTGHIxyzuvL'  # ol w0-3 f0-3 ew p0 p1 r0-2 g0-2 k0-2
def dump(idx):
    for j,row in enumerate(idx):
        print('%2d '%j+''.join('.' if v<0 else CH[v] for v in row))
def parse(lines):
    return np.array([[-1 if c=='.' else CH.index(c) for c in l] for l in lines],np.int16)
