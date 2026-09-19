# Builds all hero frames, packs assets/hero/sheep.png, writes assets/parts/hero.json and shots/hero_showcase.png
import sys, json; sys.path.insert(0,'art/raw/hero')
from frames import *
import frames2 as F2
from PIL import Image, ImageDraw
ANIMS = [  # key, frames, fps, repeat
 ('sheep-idle',        F2.stand_frames('fwd')[0], 7, -1),
 ('sheep-run',         F2.run_frames('fwd')[0], 14, -1),
 ('sheep-run-shoot',   F2.run_frames('fwd', recoil=True)[0], 14, -1),
 ('sheep-run-aimup',   F2.run_frames('dup')[0], 14, -1),
 ('sheep-run-aimdown', F2.run_frames('ddn')[0], 14, -1),
 ('sheep-aimup',       F2.stand_frames('up')[0], 7, -1),
 ('sheep-shoot',       F2.shoot_frames()[0], 16, -1),
 ('sheep-prone',       F2.prone_frames(), 6, -1),
 ('sheep-jump',        F2.ball_frames(), 20, -1),
 ('sheep-fall',        F2.fall_frames(), 10, -1),
 ('sheep-hurt',        hurt_frames(), 12, -1),
 ('sheep-die',         hurt_frames(), 12, 0),
]
COLS=12
allf=[f for _,fr,_,_ in ANIMS for f in fr]
rows=(len(allf)+COLS-1)//COLS
sheet=np.full((rows*CH, COLS*CW), -1, np.int16)
for i,f in enumerate(allf): sheet[(i//COLS)*CH:(i//COLS+1)*CH, (i%COLS)*CW:(i%COLS+1)*CW]=f
import os; os.makedirs('assets/hero',exist_ok=True)
render(sheet).save('assets/hero/sheep.png')
anims=[]; k=0
for key,fr,fps,rep in ANIMS:
    anims.append({'key':key,'texture':'sheep','frames':list(range(k,k+len(fr))),'frameRate':fps,'repeat':rep}); k+=len(fr)
json.dump({'assets':[{'type':'spritesheet','key':'sheep','url':'assets/hero/sheep.png','frameWidth':CW,'frameHeight':CH}],'anims':anims},
          open('assets/parts/hero.json','w'),indent=1)
# showcase: every anim as a row at 4x on a neutral backdrop, labelled
S=4; maxn=max(len(fr) for _,fr,_,_ in ANIMS); LW=150
img=Image.new('RGBA',(LW+maxn*CW*S//1, len(ANIMS)*CH*S),(40,44,56,255)); d=ImageDraw.Draw(img)
for j,(key,fr,fps,rep) in enumerate(ANIMS):
    d.text((8,j*CH*S+CH*S//2),f'{key}\n{len(fr)}f @{fps}fps',fill=(230,230,230,255))
    for i,f in enumerate(fr):
        t=render(f).resize((CW*S,CH*S),Image.NEAREST)
        bg=Image.new('RGBA',t.size,(78,120,84,255) if (i+j)%2==0 else (70,110,78,255)); bg.alpha_composite(t)
        img.paste(bg,(LW+i*CW*S, j*CH*S))
img.save('shots/hero_showcase.png')
print('frames',len(allf),'sheet',sheet.shape, [(a['key'],len(a['frames'])) for a in anims])

for name,fn in [('idle',lambda:F2.stand_frames('fwd')),('run',lambda:F2.run_frames('fwd')),('dup',lambda:F2.run_frames('dup')),('ddn',lambda:F2.run_frames('ddn')),('up',lambda:F2.stand_frames('up'))]:
    fr,m=fn(); print('muzzle',name, round(m[0]-CW//2,1), round(m[1]-(CH-1),1))
