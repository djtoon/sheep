// Procedural stand-ins so the game always runs. Real art (assets/manifest.json) with the same key wins.
// This file doubles as the ASSET CONTRACT: every texture/anim key the code uses is listed here with its size.

export const TEXTURES = [
  // key, w, h, colour, frames (horizontal strip)
  ['sheep', 48, 48, 0xf2e3b8, 1],          // hero sheet; origin bottom-centre, feet on frame bottom
  ['soldier', 40, 40, 0x4d6b35, 1],
  ['turret', 32, 32, 0x6d7278, 1],
  ['drone', 32, 24, 0x3a3f46, 1],
  ['bullet-player', 10, 4, 0xfff0a0, 1],
  ['bullet-spread', 6, 6, 0xff7040, 1],
  ['bullet-laser', 18, 3, 0x80e0ff, 1],
  ['bullet-enemy', 6, 6, 0xff5050, 1],
  ['muzzle', 16, 16, 0xffd060, 1],
  ['explosion', 48, 48, 0xff9030, 1],
  ['spark', 3, 3, 0xffffa0, 1],
  ['smoke', 12, 12, 0x6a6a6a, 1],
  ['debris', 4, 4, 0x55504a, 1],
  ['capsule', 24, 14, 0xb8c0c8, 1],
  ['pickup-M', 18, 14, 0xd04040, 1],
  ['pickup-S', 18, 14, 0xd04040, 1],
  ['pickup-L', 18, 14, 0xd04040, 1],
  ['hud-portrait', 34, 28, 0xf2e3b8, 1],   // framed portrait (frame baked in)
  ['hud-life', 17, 15, 0xf2e3b8, 1],
  ['hud-wbox', 64, 22, 0x101014, 1],       // weapon box frame
  ['hud-guns', 40, 14, 0xb8c0d0, 4],       // weapon icons: 0 R, 1 M, 2 S, 3 L
  ['hud-pip', 4, 8, 0xffc030, 2],          // ammo pip: 0 lit, 1 empty
  ['hud-cursor', 7, 11, 0xffd040, 1],       // title menu cursor
];

// anim key -> texture it lives on (placeholders get a 1-frame anim so code can always play() it)
export const ANIMS = {
  'sheep-idle': 'sheep', 'sheep-run': 'sheep', 'sheep-run-shoot': 'sheep', 'sheep-run-aimup': 'sheep', 'sheep-run-aimdown': 'sheep',
  'sheep-aimup': 'sheep', 'sheep-prone': 'sheep', 'sheep-jump': 'sheep', 'sheep-fall': 'sheep', 'sheep-hurt': 'sheep', 'sheep-die': 'sheep',
  'soldier-run': 'soldier', 'soldier-shoot': 'soldier', 'soldier-die': 'soldier',
  'drone-fly': 'drone', 'muzzle-flash': 'muzzle', 'explode': 'explosion',
};

export function makePlaceholders(scene) {
  const g = scene.make.graphics({ x: 0, y: 0 }, false);
  for (const [key, w, h, color, frames] of TEXTURES) {
    if (scene.textures.exists(key)) continue;
    g.clear();
    for (let f = 0; f < frames; f++) {
      g.fillStyle(0x000000, 1).fillRect(f * w, 0, w, h);
      g.fillStyle(color, 1).fillRect(f * w + 1, 1, w - 2, h - 2);
    }
    g.generateTexture(key, w * frames, h);
    if (frames > 1) {
      const t = scene.textures.get(key);
      for (let f = 0; f < frames; f++) t.add(f, 0, f * w, 0, w, h);
    }
  }
  g.destroy();
  for (const [key, tex] of Object.entries(ANIMS)) {
    if (scene.anims.exists(key) || !scene.textures.exists(tex)) continue;
    const t = scene.textures.get(tex);
    const names = t.getFrameNames().filter(n => n !== '__BASE');
    scene.anims.create({ key, frames: names.length ? [{ key: tex, frame: names[0] }] : [{ key: tex }], frameRate: 1, repeat: -1 });
  }
}
