"""grunt2: stage-2 stream grunt. Pixel-exact re-skin of assets/enemies/soldier.png (same 56x44 cells, poses, feet, muzzles)
into the enemy1 olive robot trooper in the round-3 night palette: olive armour ramp, dark-metal boots/hands/rifle,
one continuous red visor bar across the mask."""
import os, numpy as np
from PIL import Image
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
a = np.array(Image.open('assets/enemies/soldier.png').convert('RGBA'))
MAP = {
    # fatigues / helmet (khaki) -> night olive ramp
    (28, 27, 14): (20, 24, 12), (64, 62, 32): (46, 52, 26), (87, 87, 49): (74, 82, 40),
    (140, 137, 84): (100, 108, 54), (140, 140, 84): (112, 120, 60),
    (189, 185, 128): (156, 162, 90), (189, 189, 125): (170, 176, 100), (235, 235, 178): (216, 212, 146),
    # boots and hands -> black metal with one grey highlight
    (52, 30, 20): (26, 26, 32), (98, 60, 34): (74, 78, 92), (150, 92, 60): (32, 33, 40), (222, 162, 112): (112, 116, 130),
    # rifle glint
    (128, 134, 148): (112, 116, 130),
}
out = a.copy()
for src, dst in MAP.items():
    m = (a[..., 0] == src[0]) & (a[..., 1] == src[1]) & (a[..., 2] == src[2]) & (a[..., 3] > 0)
    out[m, :3] = dst
# visor: join the two eye blocks on each row into one bar
RED = (255, 40, 30)
red = (a[..., 3] > 0) & (a[..., 0] >= 250) & (a[..., 1] < 60)
for k in range(a.shape[1] // 56):
    x0 = k * 56
    for y in range(a.shape[0]):
        xs = np.where(red[y, x0:x0 + 56])[0]
        if len(xs) >= 2 and xs.max() - xs.min() <= 9:
            for x in range(xs.min(), xs.max() + 1):
                if tuple(out[y, x0 + x, :3]) in ((18, 16, 22), (14, 10, 18), (40, 40, 48), (150, 18, 24)):
                    out[y, x0 + x, :3] = RED
Image.fromarray(out, 'RGBA').save('assets/roster2/grunt2.png')
big = Image.fromarray(out, 'RGBA'); bg = Image.new('RGBA', big.size, (30, 34, 48, 255)); bg.alpha_composite(big)
bg.resize((big.width * 3, big.height * 3), Image.NEAREST).save('shots/grunt2_sheet_3x.png')
print('ok', out.shape)
