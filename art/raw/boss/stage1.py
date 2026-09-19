# step 1: hard-alpha + downscale body variants to game scale for inspection
import numpy as np
from PIL import Image
S=7.5; BOX=(16,28,1006,1513)
def load(f,thr=200):
    a=np.array(Image.open(f).convert('RGBA')).astype(np.float32)/255
    a[...,3]=(a[...,3]>=thr/255).astype(np.float32)
    return a
def down(a,w,h):
    rgb=a[...,:3]*a[...,3:4]
    pre=np.concatenate([rgb,a[...,3:4]],-1)
    im=Image.fromarray((pre*255).astype(np.uint8),'RGBA').resize((w,h),Image.BOX)
    s=np.array(im).astype(np.float32)/255; al=s[...,3:4]
    col=np.where(al>1e-3,s[...,:3]/np.maximum(al,1e-3),0)
    return np.concatenate([np.clip(col,0,1),al],-1)
W=round((BOX[2]-BOX[0])/S); H=round((BOX[3]-BOX[1])/S)
for k in ['body_a_1','body_dmg','body_open']:
    a=load(f'art/raw/boss/{k}.png')[BOX[1]:BOX[3],BOX[0]:BOX[2]]
    d=down(a,W,H); d[...,3]=(d[...,3]>=0.5)
    Image.fromarray((d*255).astype(np.uint8)).resize((W*4,H*4),Image.NEAREST).save(f'art/raw/boss/_x4_{k}.png')
print(W,H)
