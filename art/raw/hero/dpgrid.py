# Adaptive grid sampler: finds the AI image's own (non-uniform) pixel grid with DP, then takes each cell's mode colour.
import sys; sys.path.insert(0,'art/raw/hero')
from px import *
def profile(a, axis):
    d=np.abs(np.diff(a,axis=axis)).sum(-1); return d.sum(axis=1-axis)
def cuts(p, P, lo=0.75, hi=1.3):
    n=len(p); mn=max(2,int(P*lo)); mx=int(np.ceil(P*hi))
    score=np.full(n,-1e18); prev=np.full(n,-1)
    # start: any position within first mx
    for i in range(min(mx,n)): score[i]=p[i]
    for i in range(n):
        if score[i]<-1e17: continue
        for d in range(mn,mx+1):
            j=i+d
            if j>=n: break
            s=score[i]+p[j]
            if s>score[j]: score[j]=s; prev[j]=i
    # end: best in last mx
    end=max(range(max(0,n-mx),n), key=lambda i:score[i])
    out=[]; i=end
    while i>=0: out.append(i); i=prev[i]
    return sorted(out)
def sample(f, P, out=None, shrink=0.2, dark_bias=0.45):
    im=Image.open(f).convert('RGBA'); a=np.array(im)
    ys,xs=np.where(a[...,3]>128); im=im.crop((xs.min()-3,ys.min()-3,xs.max()+4,ys.max()+4))
    af=np.array(im).astype(np.float32); af[...,:3]*=af[...,3:4]/255
    px=profile(af,1); py=profile(af,0)
    cx=cuts(px,P[0]); cy=cuts(py,P[1])
    idx=to_index(im)
    H=len(cy)-1; W=len(cx)-1; o=np.full((H,W),-1,np.int16)
    for j in range(H):
        y0,y1=cy[j]+1,cy[j+1]+1
        sy=int((y1-y0)*shrink/2)
        for i in range(W):
            x0,x1=cx[i]+1,cx[i+1]+1; sx=int((x1-x0)*shrink/2)
            c=idx[y0+sy:y1-sy, x0+sx:x1-sx].ravel()
            if c.size==0: continue
            opq=c[c>=0]
            if opq.size<c.size*0.5: continue
            cnt=np.bincount(opq,minlength=len(NAMES))
            ol=IDX['ol']
            if cnt[ol]>=opq.size*dark_bias and cnt[ol]>=cnt.max()*0.6: o[j,i]=ol
            else: o[j,i]=cnt.argmax()
    o=crop_idx(o)
    if out:
        np.save(out.replace('.png','.npy'),o); render(o).save(out)
    return o
if __name__=='__main__':
    f,out=sys.argv[1],sys.argv[2]; P=(float(sys.argv[3]),float(sys.argv[4]))
    o=sample(f,P,out); print(f,o.shape)
