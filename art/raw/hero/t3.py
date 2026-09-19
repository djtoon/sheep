import sys; sys.path.insert(0,'art/raw/hero')
import frames2 as F
from wool import fleece
from px import IDX
from zoom import clean
from rast import dil
import numpy as np
T=F.TORSO
mask=(T>=0)&(T!=IDX['ol'])
outs=[T]
for sd,o in ((1,'up'),(1,'down'),(2,'up')):
    fl=fleece(mask,seed=sd,order=o)
    gold=np.isin(T,[IDX['g0'],IDX['g1'],IDX['g2']])
    out=fl.copy(); out[gold]=T[gold]; out[dil(dil(gold))&~gold&(T==IDX['ol'])&(out>=0)]=IDX['ol']
    outs.append(out)
clean(np.concatenate([np.pad(o,((0,0),(0,2)),constant_values=-1) for o in outs],1),'C:/Users/Dans/AppData/Local/Temp/claude/C--sheep/26278da5-9ac6-40de-a1a4-a76022593c3d/scratchpad/wool.png',7)
