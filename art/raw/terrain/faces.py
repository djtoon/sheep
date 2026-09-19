"""Generated cliff-face / base-foundation strips and rock spire -> palette-locked, horizontally tileable game art.
python art/raw/terrain/faces.py -> assets/terrain/face.png, found.png, spire.png"""
import os, sys
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(__file__))
import px
from build_terrain import seamless_x

def strip(src, h, name, blend=24):
    a = px.load(src); H0, W0 = a.shape[:2]
    w = round(W0 * h / H0)
    s = px.down(a, w + blend, h); s[..., 3] = 255
    s = seamless_x(s, blend)
    s = px.quant(s)
    Image.fromarray(s).save(os.path.join(px.OUT, name + '.png')); print(name, s.shape[1], s.shape[0])

strip('face_1.png', 130, 'face')
strip('face2_1.png', 130, 'face2')
strip('face2_2.png', 130, 'face3')
# value break on the original face: keep the lit band under the lip, darken the lower half in steps
a = np.array(Image.open(os.path.join(px.OUT, 'face.png')))
for y in range(a.shape[0]):
    k = 1.0 if y < 40 else max(0.5, 1 - (y - 40) / 110)
    a[y, :, :3] = (a[y, :, :3] * k).astype(np.uint8)
a = px.quant(a); Image.fromarray(a).save(os.path.join(px.OUT, 'face.png'))
strip('found_1.png', 130, 'found')
a = px.load('spire_1.png'); a = px.crop_alpha(a, 100)
h = 196; w = round(a.shape[1] * h / a.shape[0])
sp = px.crop_alpha(px.quant(px.down(a, w, h)))
Image.fromarray(sp).save(os.path.join(px.OUT, 'spire.png')); print('spire', sp.shape[1], sp.shape[0])
