import json, os, sys
from PIL import Image, ImageDraw
m = json.load(open('assets/terrain/pieces.json'))
names = sys.argv[2:] or list(m)
W = 1400; x = y = 0; rowh = 0; pos = []
for n in names:
    im = Image.open(f'assets/terrain/{n}.png'); w, h = im.width * 3, im.height * 3
    if x + w > W: x = 0; y += rowh + 20; rowh = 0
    pos.append((n, im, x, y)); x += w + 12; rowh = max(rowh, h)
sheet = Image.new('RGBA', (W, y + rowh + 20), (60, 90, 120, 255)); d = ImageDraw.Draw(sheet)
for n, im, x, y in pos:
    sheet.alpha_composite(im.resize((im.width * 3, im.height * 3), Image.NEAREST), (x, y + 10)); d.text((x, y), n, fill=(255, 255, 0, 255))
sheet.save(sys.argv[1])
