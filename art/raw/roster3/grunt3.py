# Lab security guard 'grunt3': palette/region swap of assets/enemies/soldier.png (exact same frames, feet line, muzzles)
from PIL import Image
import numpy as np, json, os
a=np.array(Image.open('assets/enemies/soldier.png').convert('RGBA')); H,W=a.shape[:2]; o=a.copy()
hx=lambda s: tuple(int(s[i:i+2],16) for i in (0,2,4))
olive={'1c1b0e':0,'403e20':1,'575731':2,'8c8954':3,'8c8c54':3,'bdb980':4,'bdbd7d':4,'ebebb2':5}
BLUE=[(16,20,40),(30,40,78),(44,58,104),(66,86,140),(98,120,176),(140,160,210)]
GREY=[(40,44,58),(82,90,112),(110,118,140),(140,148,168),(200,204,212),(232,236,242)]
other={'341e14':(26,28,36),'623c22':(52,56,70),'965c3c':(84,90,108),'dea270':(64,70,86)}
for f in range(W//56):
    cell=a[:,f*56:(f+1)*56]; oc=o[:,f*56:(f+1)*56]; rgb=cell[...,:3]; op=cell[...,3]>0
    red=op&(((rgb[...,0]>200)&(rgb[...,1]<60))|(rgb==hx('961218')).all(-1))
    ys,xs=np.where(red); cy,cx=(ys.mean(),xs.mean()) if len(ys) else (-99,-99)
    Y,X=np.mgrid[0:H,0:56]
    # helmet: goggles sit at its lower front; for the dying (rotated) frames fall back to a round area
    helm=(((Y-(cy-4))/8.5)**2+((X-(cx+3))/9.0)**2<=1)&(Y<=cy+2) if f<12 else ((Y-cy)**2+(X-cx)**2<=7.5**2)
    for k,t in olive.items():
        m=op&(rgb==hx(k)).all(-1); oc[m&helm,:3]=GREY[t]; oc[m&~helm,:3]=BLUE[t]
    for k,v in other.items():
        m=op&(rgb==hx(k)).all(-1); oc[m,:3]=v
    oc[red&(rgb==hx('961218')).all(-1),:3]=(200,20,40); oc[red&~(rgb==hx('961218')).all(-1),:3]=(255,60,60)
    m=oc[...,3]>0; n=np.zeros_like(m); n[1:]|=m[:-1]; n[:-1]|=m[1:]; n[:,1:]|=m[:,:-1]; n[:,:-1]|=m[:,1:]
    oc[n&~m]=(12,10,18,255)
os.makedirs('assets/roster3',exist_ok=True); Image.fromarray(o,'RGBA').save('assets/roster3/grunt3.png')
j=json.load(open('assets/parts/roster3.json')); e=json.load(open('assets/parts/enemies.json'))
j['assets']=[x for x in j['assets'] if x.get('key')!='grunt3']+[{'type':'spritesheet','key':'grunt3','url':'assets/roster3/grunt3.png','frameWidth':56,'frameHeight':44}]
j['anims']=[x for x in j['anims'] if not x['key'].startswith('grunt3-')]
for an in e['anims']:
    if an['key'].startswith('soldier-'): n=dict(an); n['key']='grunt3-'+an['key'][8:]; n['texture']='grunt3'; j['anims'].append(n)
json.dump(j,open('assets/parts/roster3.json','w'),indent=1)
