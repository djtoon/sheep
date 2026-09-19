import numpy as np
import sys; sys.path.insert(0,'art/raw/hero')
from px import *
def grid(h,w):
    y,x=np.mgrid[0:h,0:w]; return x+0.5,y+0.5
def ellipse(h,w,cx,cy,rx,ry):
    x,y=grid(h,w); return ((x-cx)/rx)**2+((y-cy)/ry)**2<=1
def seg(h,w,p0,p1,r):
    x,y=grid(h,w); (x0,y0),(x1,y1)=p0,p1; dx,dy=x1-x0,y1-y0; L=dx*dx+dy*dy or 1e-9
    t=np.clip(((x-x0)*dx+(y-y0)*dy)/L,0,1); return (x-x0-t*dx)**2+(y-y0-t*dy)**2<=r*r
def poly(h,w,pts,r):
    m=np.zeros((h,w),bool)
    for a,b in zip(pts[:-1],pts[1:]): m|=seg(h,w,a,b,r)
    return m
def dil(m, diag=False):
    n=m.copy(); n[1:]|=m[:-1]; n[:-1]|=m[1:]; n[:,1:]|=m[:,:-1]; n[:,:-1]|=m[:,1:]
    if diag: n[1:,1:]|=m[:-1,:-1]; n[1:,:-1]|=m[:-1,1:]; n[:-1,1:]|=m[1:,:-1]; n[:-1,:-1]|=m[1:,1:]
    return n
def ero(m): return ~dil(~m)
def ring(m): return dil(m)&~m
def put(canvas, mask, name):
    canvas[mask]=IDX[name]
def paste(dst, src, x, y):
    """paste idx src onto dst at x,y (transparent -1 skipped), clipped"""
    h,w=src.shape; H,W=dst.shape
    sx0=max(0,-x); sy0=max(0,-y); dx0=max(0,x); dy0=max(0,y)
    ww=min(w-sx0, W-dx0); hh=min(h-sy0, H-dy0)
    if ww<=0 or hh<=0: return dst
    s=src[sy0:sy0+hh, sx0:sx0+ww]; d=dst[dy0:dy0+hh, dx0:dx0+ww]
    m=s>=0; d[m]=s[m]; return dst
def outline_part(idx):
    """add a 1px ol ring around opaque pixels (4-neighbour)"""
    m=idx>=0; pad=np.full((idx.shape[0]+2,idx.shape[1]+2),-1,np.int16); pad[1:-1,1:-1]=idx
    mm=pad>=0; r=ring(mm); pad[r]=IDX['ol']; return pad
