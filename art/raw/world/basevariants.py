"""Bake cooler/lighter 'base area' variants of the layers visible behind the enemy base (hard per-pixel palette
shift, no alpha): assets/world/<name>-base.png. Run after build.py."""
import numpy as np, json
from PIL import Image
COL = np.array([166, 208, 230], float)
LAYERS = {'near': 0.22, 'near-1': 0.22, 'near-2': 0.22, 'near-3': 0.22, 'cliffs': 0.22, 'cliffs-1': 0.22, 'cliffs-2': 0.22,
          'cliffs-3': 0.22, 'midtrees': 0.22, 'canopy': 0.22, 'hills': 0.15, 'farcliffs': 0.12}
out = []
for n, amt in LAYERS.items():
    a = np.array(Image.open(f'assets/world/{n}.png').convert('RGBA'))
    rgb = a[..., :3].astype(float)
    lum = rgb @ [.3, .59, .11]
    # contrast-preserving shift: move the whole palette toward the cool haze colour by an OFFSET (not a mix),
    # plus a light 10% mix, so pixel-to-pixel steps and outlines keep their crispness
    m = a[..., 3] > 0; mean = rgb[m].mean(0)
    k = np.where(lum < 60, amt * 0.5, amt)[..., None]
    new = rgb + k * (COL - mean) * 0.9
    new = new * 0.92 + COL * 0.08
    a[..., :3] = np.clip(new + 0.5, 0, 255).astype(np.uint8)
    Image.fromarray(a).save(f'assets/world/{n}-base.png'); out.append(n)
p = 'assets/parts/world.json'; j = json.load(open(p))
have = {x['key'] for x in j['assets']}
for n in out:
    k = f'bg-{n}-base'
    if k not in have: j['assets'].insert(-1, {"type": "image", "key": k, "url": f"assets/world/{n}-base.png"})
json.dump(j, open(p, 'w'), indent=1); print('baked', out)
