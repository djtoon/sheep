import sys; sys.path.insert(0,'art/raw/hero')
import frames2 as F
from zoom import clean
from PIL import Image
import numpy as np
def sil(f):
    s=np.full(f.shape,-1,np.int16); s[f>=0]=0; return s
fr=[F.stand_frames('fwd')[0][0], F.run_frames('fwd')[0][1], F.run_frames('fwd')[0][5]]
row=np.concatenate([f[10:] for f in fr]+[sil(f)[10:] for f in fr],1)
clean(row,sys.argv[1],int(sys.argv[2]) if len(sys.argv)>2 else 3, bg=(230,230,230,255))
