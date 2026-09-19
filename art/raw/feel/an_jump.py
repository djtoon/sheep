import json,sys
t=json.load(open(sys.argv[1]))
xs=[(f['t'],f['player']['x'],f['player']['y'],f['player']['ground']) for f in t if f['player']]
seg=[];cur=None
prev=xs[0]
for x in xs:
  if not x[3]:
    cur=(cur or [prev])+[x]
  elif cur: seg.append(cur+[x]);cur=None
  prev=x
for s in seg: print('air',round(s[-1][0]-s[0][0]),'ms apex', s[0][2]-min(q[2] for q in s), 'dx', s[-1][1]-s[0][1])
g=[x for x in xs if x[3]]
run=[(a,b) for a,b in zip(xs,xs[1:]) if b[1]!=a[1] and a[3] and b[3]]
if run: print('run px/s', round(sum((b[1]-a[1]) for a,b in run)/sum((b[0]-a[0]) for a,b in run)*1000,1))
