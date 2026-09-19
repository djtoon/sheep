import sys; sys.path.insert(0,'art/raw/hero')
from rast import *
H,W=26,30
def wool_blob(circles, shade_dir=(0.5,0.8)):
    """union of circles, shaded as curls: returns (mask, colour idx array)"""
    m=np.zeros((H,W),bool); col=np.full((H,W),-1,np.int16)
    x,y=grid(H,W)
    for (cx,cy,r) in circles:
        c=((x-cx)**2+(y-cy)**2)<=r*r
        # per-circle shading: offset along light dir
        d=((x-cx)*shade_dir[0]+(y-cy)*shade_dir[1])/r
        cc=np.where(d>0.55,IDX['w2'],np.where(d>0.05,IDX['w1'],IDX['w0']))
        col[c]=cc[c]; m|=c
    return m,col
def make_head(look='fwd', eyes='angry'):
    cv=np.full((H,W),-1,np.int16)
    # ear (behind)
    ear=seg(H,W,(12,13.5),(5.5,16.5),2.1)
    cv[ear]=IDX['f2']; cv[seg(H,W,(11,14),(6.8,16),0.9)]=IDX['p0']
    cv[ring(ear)&(cv<0)]=IDX['ol']
    # face
    face=ellipse(H,W,17.5,15.5,7.2,6.6)|ellipse(H,W,22.5,18.2,4.6,3.6)
    x,y=grid(H,W)
    fc=np.where((x<13.5)|(y>20.5),IDX['f2'],IDX['f1']).astype(np.int16)
    fc[(x-21)**2/9+(y-18)**2/4<1]=IDX['f1']
    fc[ellipse(H,W,24.5,16.8,2.0,1.2)]=IDX['f0']
    cv[face]=fc[face]
    # ring between ear and face
    r=ring(face); cv[r&(cv>=0)&~face]=IDX['ol']
    # wool cap
    cap,capc=wool_blob([(8.5,8.5,3.2),(11.5,5.8,3.8),(16.2,4.6,4.0),(20.8,5.2,3.8),(24.3,7.6,3.2),(26.2,10,2.2)])
    # curls: small crescents inside
    cv[cap]=capc[cap]
    # headband
    band=np.zeros((H,W),bool); band[8:11,:]=True
    sil=(cv>=0)
    b=band&(sil|cap)&(x>5)
    cv[b&(y<9)]=IDX['r0']; cv[b&(y>=9)&(y<10)]=IDX['r1']; cv[b&(y>=10)]=IDX['r2']
    # knot at back
    knot=ellipse(H,W,5.2,9.6,1.8,1.6); cv[knot]=IDX['r1']; cv[ellipse(H,W,4.7,9.0,0.8,0.7)]=IDX['r0']
    # eyes
    if eyes in ('angry','up','x'):
        ex=[16.3,21.6]; ey=14.6 if look!='up' else 13.8
        for i,cx in enumerate(ex):
            e=ellipse(H,W,cx,ey,2.55,3.1)
            cv[ring(e)]=IDX["ol"]
            cv[e]=IDX['ew']
        for i,cx in enumerate(ex):
            if eyes=='x':
                cv[seg(H,W,(cx-1.4,ey-1.4),(cx+1.4,ey+1.4),0.6)]=IDX['ol']; cv[seg(H,W,(cx-1.4,ey+1.4),(cx+1.4,ey-1.4),0.6)]=IDX['ol']
            elif look=='up':
                cv[int(ey-2):int(ey), int(cx):int(cx)+2]=IDX['ol']
            else:
                cv[int(ey)-1:int(ey)+2, int(cx)+1:int(cx)+2+1]=IDX['ol']
        if eyes=='angry':
            cv[seg(H,W,(13.2,11.2),(18.8,13.2),0.75)]=IDX['ol']
            cv[seg(H,W,(19.6,13.0),(24.6,11.4),0.75)]=IDX['ol']
    # mouth + nostril
    cv[seg(H,W,(21.5,21.2),(24.2,20.6),0.5)]=IDX['ol']
    cv[21,21]=IDX['ol']
    cv[17,26]=IDX['f3']
    # silhouette outline
    m=cv>=0; cv[ring(m)]=IDX['ol']
    # dark line under cap edge where cap meets face (above band) not needed; band separates
    # line under band
    under=np.zeros_like(m); under[11,:]=True; cv[under&face&(cv==IDX['f1'])|under&face&(cv==IDX['f2'])]=IDX['ol']
    return cv
if __name__=='__main__':
    from zoom import zoom
    for k,(l,e) in {'fwd':('fwd','angry'),'up':('up','up'),'x':('fwd','x')}.items():
        hd=make_head(l,e); np.save(f'art/raw/hero/head_{k}.npy',hd)
        zoom(hd,f'C:/Users/Dans/AppData/Local/Temp/claude/C--sheep/26278da5-9ac6-40de-a1a4-a76022593c3d/scratchpad/head_{k}.png',16)
