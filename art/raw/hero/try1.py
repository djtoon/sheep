import sys; sys.path.insert(0,'art/raw/hero')
from px import *
from PIL import Image
f=sys.argv[1]; s=float(sys.argv[2]); out=sys.argv[3]
im=Image.open(f).convert('RGBA'); a=np.array(im)
ys,xs=np.where(a[...,3]>128); im=im.crop((xs.min(),ys.min(),xs.max()+1,ys.max()+1))
idx=to_index(im)
best=None
for ox in np.arange(0,s,s/4):
  for oy in np.arange(0,s,s/4):
    d=downsample(idx,s,s,ox,oy)
    # score: prefer fewer isolated pixels
    sc=0
    if best is None or True: pass
    best=d; break
  break
d=crop_idx(best); print(d.shape)
render(d).save(out); show(d,out.replace('.png','_x8.png'))
