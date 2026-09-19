"""Blind A/B pair for critics. Only the LEAD runs this; critics only ever see the output image.
usage: python tools/abpair.py OURS.png REF.png OUT.png [--crop x,y,w,h] [--crop-ours x,y,w,h] [--crop-ref x,y,w,h]
(crops in 0..1 fractions; --crop applies to both)
Randomly assigns left/right, labels them only 'A' and 'B', scales both to the same height.
The answer key is appended to .ab_keys.txt, which critics must never read."""
import sys, random, os
from PIL import Image, ImageDraw, ImageFont

ours, ref, out = sys.argv[1:4]
def arg(n):
    return [float(v) for v in sys.argv[sys.argv.index(n) + 1].split(',')] if n in sys.argv else None
crops = [arg('--crop-ours') or arg('--crop'), arg('--crop-ref') or arg('--crop')]
ims = []
for p, crop in zip((ours, ref), crops):
    im = Image.open(p).convert('RGB')
    if crop:
        x, y, w, h = crop; W, H = im.size
        im = im.crop((int(x * W), int(y * H), int((x + w) * W), int((y + h) * H)))
    ims.append(im)
H = 810  # native height of our 3x captures: ours is never resampled smoothly (pixel art must stay crisp)
ims = [ims[0].resize((round(ims[0].width * H / ims[0].height), H), Image.NEAREST),
       ims[1].resize((round(ims[1].width * H / ims[1].height), H), Image.LANCZOS if ims[1].height > H else Image.NEAREST)]
order = [0, 1]; random.shuffle(order)
L, R = ims[order[0]], ims[order[1]]
canvas = Image.new('RGB', (L.width + R.width + 30, H + 50), (18, 18, 18))
canvas.paste(L, (0, 50)); canvas.paste(R, (L.width + 30, 50))
d = ImageDraw.Draw(canvas)
try:
    f = ImageFont.truetype('arial.ttf', 36)
except Exception:
    f = None
d.text((L.width // 2 - 10, 5), 'A', fill=(255, 255, 255), font=f)
d.text((L.width + 30 + R.width // 2 - 10, 5), 'B', fill=(255, 255, 255), font=f)
os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
canvas.save(out)
key = 'A' if order[0] == 0 else 'B'
with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.ab_keys.txt'), 'a') as fh:
    fh.write(f'{out}\tours={key}\n')
print(out)
