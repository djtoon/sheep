import sys; sys.path.insert(0,'art/raw/hero')
from px import *
from PIL import ImageDraw
def zoom(idx, path, s=16, x0=0,y0=0,x1=None,y1=None):
    sub=idx[y0:y1, x0:x1]; im=render(sub); b=Image.new('RGBA',im.size,(70,110,70,255)); b.alpha_composite(im)
    b=b.resize((im.width*s,im.height*s),Image.NEAREST); d=ImageDraw.Draw(b)
    for i in range(sub.shape[1]+1): d.line([(i*s,0),(i*s,b.height)],fill=(0,0,0,60))
    for j in range(sub.shape[0]+1): d.line([(0,j*s),(b.width,j*s)],fill=(0,0,0,60))
    for i in range(sub.shape[1]):
        if (i+x0)%5==0: d.text((i*s+2,0),str(i+x0),fill=(255,255,0,255))
    for j in range(sub.shape[0]):
        if (j+y0)%5==0: d.text((0,j*s+2),str(j+y0),fill=(255,255,0,255))
    b.save(path)
if __name__=='__main__':
    idx=np.load(sys.argv[1]); a=[int(v) for v in sys.argv[3:]]
    zoom(idx, sys.argv[2], 16, *a)

def clean(idx, path, s=6, bg=(86,140,90,255)):
    im=render(idx); b=Image.new('RGBA',im.size,bg); b.alpha_composite(im)
    b.resize((im.width*s,im.height*s),Image.NEAREST).save(path)
