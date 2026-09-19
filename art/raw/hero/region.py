import sys; sys.path.insert(0,'art/raw/hero')
from px import *
a=np.load(sys.argv[1]); y0,y1,x0,x1=map(int,sys.argv[2:6])
print('    '+''.join(str((x//10)%10) for x in range(x0,x1)))
print('    '+''.join(str(x%10) for x in range(x0,x1)))
for y in range(y0,y1): print('%3d '%y+''.join('.' if v<0 else CH[v] for v in a[y,x0:x1]))
