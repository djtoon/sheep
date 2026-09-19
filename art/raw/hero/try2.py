import sys,time; sys.path.insert(0,'art/raw/hero')
from px import *
f=sys.argv[1]; lo,hi=float(sys.argv[2]),float(sys.argv[3]); out=sys.argv[4]
im=Image.open(f).convert('RGBA'); a=np.array(im)
ys,xs=np.where(a[...,3]>128); im=im.crop((xs.min()-2,ys.min()-2,xs.max()+3,ys.max()+3))
idx=to_index(im)
# coarse then fine
b=best_grid(idx,lo,hi,0.25,True); print('coarse',b)
p,sx,sy,ox,oy=b
b2=(0,)
for dsx in np.arange(-0.2,0.21,0.05):
  for dsy in np.arange(-0.2,0.21,0.05):
    for ox2 in np.arange(0,sx,0.5):
      for oy2 in np.arange(0,sy,0.5):
        q=purity(idx,sx+dsx,sy+dsy,ox2,oy2)
        if q>b2[0]: b2=(q,sx+dsx,sy+dsy,ox2,oy2)
print('fine',b2)
p,sx,sy,ox,oy=b2
d=crop_idx(downsample(idx,sx,sy,ox,oy)); print(d.shape)
render(d).save(out); show(d,out.replace('.png','_x8.png'))
