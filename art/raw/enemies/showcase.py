from PIL import Image, ImageDraw
import os
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
S = 4
rows = [('soldier run 0-7', 'soldier', 56, 44, range(0, 8)), ('aim / fire / kneel-aim / kneel-fire', 'soldier', 56, 44, range(8, 12)),
        ('death (knock-back)', 'soldier', 56, 44, range(12, 16)), ('turret idle, blink, recoil, return', 'turret', 66, 58, range(4)),
        ('drone rotor spin', 'drone', 44, 33, range(4))]
singles = ['capsule', 'pickup-M', 'pickup-S', 'pickup-L']
W = 8 * 56 * S + 9 * 8; y = 0; blocks = []
for label, key, fw, fh, fr in rows:
    im = Image.open(f'assets/enemies/{key}.png'); blocks.append((label, [im.crop((k * fw, 0, (k + 1) * fw, fh)) for k in fr]))
blocks.append(('capsule + pickups M S L', [Image.open(f'assets/enemies/{k}.png') for k in singles]))
H = sum(max(f.height for f in fs) * S + 34 for _, fs in blocks) + 10
c = Image.new('RGB', (W, H), (46, 58, 44)); d = ImageDraw.Draw(c)
for label, fs in blocks:
    d.text((8, y + 6), label, fill=(240, 230, 200)); y += 22; x = 8
    hh = max(f.height for f in fs) * S
    for f in fs:
        big = f.resize((f.width * S, f.height * S), Image.NEAREST)
        d.rectangle((x - 1, y - 1, x + big.width, y + hh), outline=(70, 86, 66))
        c.paste(big, (x, y + hh - big.height), big); x += big.width + 8
    y += hh + 12
c.save('shots/enemies_showcase.png'); print(c.size)
