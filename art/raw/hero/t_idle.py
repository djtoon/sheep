import sys; sys.path.insert(0,'art/raw/hero')
from build import *
from zoom import zoom
b=prep_fwd(); hd=head('angry')
ox=40-26; oy=BASE-49   # body placement
frames=[]
for f in range(8):
    cv=np.full((CH,CW),-1,np.int16)
    hx,hy=ox+15, oy+4
    t=tail_mask((hx+1,hy+7),f,8,'run'); paste(cv,t,0,0)
    paste(cv,b,ox,oy); paste(cv,hd,hx,hy); ensure_outline(cv)
    frames.append(cv)
from PIL import Image
S='C:/Users/Dans/AppData/Local/Temp/claude/C--sheep/26278da5-9ac6-40de-a1a4-a76022593c3d/scratchpad/'
zoom(frames[0],S+'idle0.png',8)
strip=np.concatenate(frames,1); render(strip).resize((strip.shape[1]*4,strip.shape[0]*4),Image.NEAREST).save(S+'strip.png')
