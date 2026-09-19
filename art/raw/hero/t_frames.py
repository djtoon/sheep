import sys; sys.path.insert(0,'art/raw/hero')
from frames import *
from zoom import clean
S='C:/Users/Dans/AppData/Local/Temp/claude/C--sheep/26278da5-9ac6-40de-a1a4-a76022593c3d/scratchpad/'
rows=[ball_frames(), fall_frames(), prone_frames(), hurt_frames()]
W=max(len(r) for r in rows)
g=np.full((CH*len(rows), CW*W), -1, np.int16)
for j,r in enumerate(rows):
    for i,f in enumerate(r): g[j*CH:(j+1)*CH, i*CW:(i+1)*CW]=f
clean(g, S+'frames2.png', 3)
