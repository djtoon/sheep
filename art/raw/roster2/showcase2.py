import json, os
from PIL import Image, ImageDraw
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
meta = json.load(open('art/raw/roster2/out/meta.json'))
labels = {'trooper': 'trooper: walk x8, aim, fire, hit, down', 'shield': 'shield: walk x8, brace, fire, hit, down',
          'sniper': 'sniper: walk x4, aim, fire, hit, down', 'tank': 'tank: roll x3, fire, damaged, wreck',
          'drone2': 'drone2: rotor x4, fire, wreck', 'mech': 'mech: walk x8, spin-up, fire, hit, wreck'}
S = 4; rows = []
for k, m in meta.items():
    im = Image.open(f'assets/roster2/{k}.png'); cw, ch = m['cell']
    rows.append((labels[k], [im.crop((i * cw, 0, (i + 1) * cw, ch)) for i in range(im.width // cw)]))
W = max(sum(f.width * S + 6 for f in fs) for _, fs in rows) + 16
H = sum(fs[0].height * S + 30 for _, fs in rows) + 10
c = Image.new('RGB', (W, H), (30, 34, 48)); d = ImageDraw.Draw(c); y = 4
for lab, fs in rows:
    d.text((8, y + 4), lab, fill=(236, 228, 200)); y += 20; x = 8
    for f in fs:
        big = f.resize((f.width * S, f.height * S), Image.NEAREST)
        d.rectangle((x - 1, y - 1, x + big.width, y + big.height), outline=(56, 62, 80))
        c.paste(big, (x, y), big); x += big.width + 6
    y += fs[0].height * S + 10
c.save('shots/roster2_showcase.png'); print(c.size)
