import sys, json, math; sys.path.insert(0,'art/raw/hero')
from rast import *
from heads import head
CW,CH=80,80; BASE=79   # cell size; ground (outline row under hooves) is the last row
OL=IDX['ol']; WOOL=[IDX[k] for k in ('w0','w1','w2','w3')]
def load(n): return np.load(f'art/raw/hero/s/{n}.npy').astype(np.int16)
def ensure_outline(cv):
    m=cv>=0; body=m&(cv!=OL)
    r=dil(body)&~m; cv[r]=OL
    # drop orphan outline pixels (no non-outline neighbour)
    o=(cv==OL); keep=dil(body,True); cv[o&~keep]=-1
    return cv
def clear(cv, y0,y1,x0,x1, keep=None):
    reg=cv[y0:y1,x0:x1]
    if keep is None: reg[:]=-1
    else: reg[~np.isin(reg,keep)]=-1
    return cv
# ---------------- tails ----------------
def tail_mask(knot, frame, nfr, mode='run', h=CH, w=CW):
    """two ribbon tails from the knot, streaming left. returns idx canvas"""
    cv=np.full((h,w),-1,np.int16)
    kx,ky=knot
    specs=[(13,0.0,-0.25),(10,2.1,0.35)] if mode=='run' else [(11,0.0,0.55),(9,2.1,0.95)]
    if mode=='jump': specs=[(12,0.0,-0.9),(9,2.1,-0.5)]
    for L,ph0,droop in specs:
        pts=[]; t=2*math.pi*frame/nfr
        for k in range(L+1):
            amp=(1.3 if mode=='run' else 0.9)*(k/L)**0.8*2
            pts.append((kx-k*0.95, ky+droop*k+amp*math.sin(t+ph0-k*0.55)))
        m=np.zeros((h,w),bool)
        for k,(a,b) in enumerate(zip(pts[:-1],pts[1:])):
            r=1.25 if k<L*0.55 else (0.95 if k<L*0.85 else 0.6)
            m|=seg(h,w,a,b,r)
        up=m&~np.roll(m,1,0); dn=m&~np.roll(m,-1,0)
        c=np.where(up,IDX['r0'],np.where(dn,IDX['r2'],IDX['r1']))
        # draw with its own outline so overlapping ribbons separate
        r_=ring(m); cv[r_&(cv<0)]=OL
        cv[m]=c[m]; cv[r_ & ~m & (cv!=IDX['r1'])]=OL
    return cv
# ---------------- legs ----------------
def leg(cv, hip, foot, back=False):
    h,w=cv.shape
    m=seg(h,w,hip,foot,1.9)
    # hoof: disc near foot, flattened bottom
    fx,fy=foot
    hoof=ellipse(h,w,fx+0.6,fy-0.3,2.3,1.9)&(grid(h,w)[1]<fy+0.9)
    m|=hoof
    body=np.full((h,w),-1,np.int16)
    x,y=grid(h,w)
    main=IDX['f2'] if back else IDX['f1']; edge=IDX['f3'] if back else IDX['f0']
    body[m]=main
    # light edge on the front (right) side
    fr=m&~np.roll(m,-1,1); body[fr&~hoof]=edge if not back else main
    body[hoof]=IDX['k1']; body[hoof&(y>fy-0.5)]=IDX['k2']
    r_=ring(m); cv[r_]=OL; cv[m]=body[m]
    return cv
# run cycle foot targets relative to hip: (dx, height above ground)
RUN=[(7,0),(3.5,0),(0,0),(-4,0.5),(-7.5,2),(-5,5),(0,5.5),(5,3)]
BOB=[1,2,1,0,1,2,1,0]
def prep_fwd():
    b=load('fwd_1')
    H,W=b.shape
    # remove AI head + tails (keep shoulder wool)
    for y in range(0,22):
        for x in range(0,41):
            v=b[y,x]
            if y<17 or not (v in WOOL): b[y,x]=-1
    b[b==IDX['r1']]=-1; b[b==IDX['r2']]=-1; b[b==IDX['r0']]=-1
    return b
def upper_from(b, cut):
    u=b.copy(); u[cut:]=np.where(np.isin(u[cut:],WOOL+[IDX['k0'],IDX['k1'],IDX['k2']]),u[cut:],-1)
    return u
def compose(parts):
    cv=np.full((CH,CW),-1,np.int16)
    for p,x,y in parts: paste(cv,p,x,y)
    return cv
