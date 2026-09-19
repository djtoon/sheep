import sys,glob,os; sys.path.insert(0,'art/raw/hero')
from sample import prof,fper
from dpgrid import sample
from px import *
from PIL import Image
for f in sys.argv[1:]:
    im=Image.open(f).convert('RGBA'); a=np.array(im).astype(np.float32); a[...,:3]*=a[...,3:4]/255
    px=fper(prof(a,1),9,18); py=fper(prof(a,0),9,18)
    # guard against half-period picks: use the larger if they disagree a lot
    P=(px,py)
    if abs(px-py)>2: m=max(px,py); P=(m,m)
    out='art/raw/hero/s/'+os.path.basename(f)
    o=sample(f,P,out); print(f,[round(p,2) for p in P],o.shape)
