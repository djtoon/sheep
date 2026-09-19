import sys; sys.path.insert(0,'art/raw/hero')
from frames2 import *
from zoom import clean
S='C:/Users/Dans/AppData/Local/Temp/claude/C--sheep/26278da5-9ac6-40de-a1a4-a76022593c3d/scratchpad/'
rows=[stand_frames('fwd')[0][:4], run_frames('fwd')[0][:4], run_frames('dup')[0][:4], run_frames('ddn')[0][:4], stand_frames('up')[0][:4], prone_frames()]
g=np.full((CH*len(rows), CW*4), -1, np.int16)
for j,r in enumerate(rows):
    for i,f in enumerate(r): g[j*CH:(j+1)*CH, i*CW:(i+1)*CW]=f
clean(g[:, :], S+'f2.png', 3)
clean(rows[0][0][20:], S+'f2big.png', 8)
