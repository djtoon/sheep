import json,sys
t=json.load(open(sys.argv[1]))
t=[f for f in t if f['player'] and not f['boss']] or t
dt=(t[1]['t']-t[0]['t'])/1000
empty=[f['onscreen']==0 for f in t]
runs=[];c=0
for i,e in enumerate(empty):
  if e: c+=1
  elif c: runs.append((c*dt, t[i-c]['cam'])); c=0
print('samples',len(t),'duration to boss %.1fs'%(len(t)*dt))
print('time with no enemy on screen: %.0f%%'%(100*sum(empty)/len(t)))
print('time with no enemy AND no enemy bullet: %.0f%%'%(100*sum(1 for f in t if f['onscreen']==0 and f['eShots']==0)/len(t)))
print('longest empty stretches (s, cam x):',sorted(runs,reverse=True)[:6])
print('mean on-screen enemies %.2f, max %d'%(sum(f['onscreen'] for f in t)/len(t), max(f['onscreen'] for f in t)))
print('max enemy shots on screen', max(f['eShots'] for f in t))
# per 10s window: kills + mean onscreen + camera
for w in range(0,int(len(t)*dt),10):
  seg=[f for f in t if w*1000<=f['t']-t[0]['t']<(w+10)*1000]
  if not seg: continue
  print('%3d-%3ds cam %4d-%4d  kills %2d  onscreen avg %.1f  eShots max %d'%(w,w+10,seg[0]['cam'],seg[-1]['cam'],seg[-1]['kills']-seg[0]['kills'],sum(f['onscreen'] for f in seg)/len(seg),max(f['eShots'] for f in seg)))
