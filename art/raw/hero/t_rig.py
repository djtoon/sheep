import sys; sys.path.insert(0,'art/raw/hero')
from poses import *
from zoom import zoom
S='C:/Users/Dans/AppData/Local/Temp/claude/C--sheep/26278da5-9ac6-40de-a1a4-a76022593c3d/scratchpad/'
fr=[stand(0,a,face='up' if a=='up' else 'angry')[0] for a in ('fwd','dup','ddn','up')]
strip=np.concatenate(fr,1); from zoom import clean; clean(strip[20:],S+"rig.png",5)
