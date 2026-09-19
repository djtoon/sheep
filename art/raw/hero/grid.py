import sys, numpy as np
from PIL import Image
def prof(a, axis):
    d = np.abs(np.diff(a, axis=axis)).sum(-1)
    return d.sum(axis=1-axis)
def period(p, lo=8, hi=20):
    x=np.arange(len(p)); res=[]
    for P in np.arange(lo,hi,0.05):
        ang=2*np.pi*x/P
        c=(p*np.cos(ang)).sum(); s=(p*np.sin(ang)).sum()
        res.append((np.hypot(c,s)/p.sum(),P,(np.arctan2(s,c)/(2*np.pi)*P)%P))
    res.sort(reverse=True); return res[:3]
if __name__=='__main__':
    im=np.array(Image.open(sys.argv[1]).convert('RGBA')).astype(np.float32)
    im[...,:3]*=im[...,3:4]/255
    print('x',[tuple(round(float(v),2) for v in r) for r in period(prof(im,1))])
    print('y',[tuple(round(float(v),2) for v in r) for r in period(prof(im,0))])
