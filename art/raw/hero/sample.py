# usage: python sample.py in.png out.png [lo hi]  -> Fourier period estimate + phase search, palette-locked mode sampling
import sys; sys.path.insert(0,'art/raw/hero')
from px import *
def prof(a, axis):
    d=np.abs(np.diff(a,axis=axis)).sum(-1); return d.sum(axis=1-axis)
def fper(p,lo,hi):
    x=np.arange(len(p)); best=(0,0)
    for P in np.arange(lo,hi,0.05):
        ang=2*np.pi*x/P; v=np.hypot((p*np.cos(ang)).sum(),(p*np.sin(ang)).sum())/p.sum()
        if v>best[0]: best=(v,P)
    return best[1]
def run(f,out,lo=8,hi=18,force=None):
    im=Image.open(f).convert('RGBA'); a=np.array(im)
    ys,xs=np.where(a[...,3]>128); im=im.crop((xs.min()-2,ys.min()-2,xs.max()+3,ys.max()+3))
    af=np.array(im).astype(np.float32); af[...,:3]*=af[...,3:4]/255
    if force: sx,sy=force
    else: sx=fper(prof(af,1),lo,hi); sy=fper(prof(af,0),lo,hi)
    idx=to_index(im); b=(0,)
    for dsx in (-0.1,0,0.1):
      for dsy in (-0.1,0,0.1):
        for ox in np.arange(0,sx,1.0):
          for oy in np.arange(0,sy,1.0):
            q=purity(idx,sx+dsx,sy+dsy,ox,oy)
            if q>b[0]: b=(q,sx+dsx,sy+dsy,ox,oy)
    print(f,'grid',[round(float(v),2) for v in b])
    d=crop_idx(downsample(idx,*b[1:])); print(' ->',d.shape)
    np.save(out.replace('.png','.npy'),d); render(d).save(out); show(d,out.replace('.png','_x8.png'))
if __name__=='__main__':
    lo,hi=(float(sys.argv[3]),float(sys.argv[4])) if len(sys.argv)>4 else (8,18)
    force=(float(sys.argv[5]),float(sys.argv[6])) if len(sys.argv)>6 else None
    run(sys.argv[1],sys.argv[2],lo,hi,force)
