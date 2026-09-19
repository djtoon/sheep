// STAGE 03 renderer (underground lab). Same interface as LevelView: new View3(scene, level); update(cam).
// Planes, far -> near: back wall (sf .2), machinery row (sf .5), then the play plane in world space:
// pre-composited chunks (ceiling, floor, sub-floor, catwalks, ladders, props) built by art/raw/stage3/build3.py,
// plus animated sprites (specimen tanks, specimen window, blast-door lamps, toxic pools). Everything is hard-pixel,
// no alpha overlays. Off-screen chunks and sprites are culled every frame.
import { meta3 } from './meta3.js';

const PLAY_DEPTH = 20;

export class View3 {
  constructor(scene, level) {
    this.scene = scene; this.level = level;
    const W = scene.scale.width, H = scene.scale.height;
    const has = k => scene.textures.exists(k);
    this.layers = [];
    // background fill (never visible if the back wall loads, but keeps the frame dark indoors)
    scene.add.rectangle(0, 0, W, H, 0x05090c, 1).setOrigin(0, 0).setScrollFactor(0).setDepth(-101);
    for (const [key, sf, depth] of [['s3-back', 0.2, -100], ['s3-machines', 0.5, -90]]) {
      if (!has(key)) continue;
      const img = scene.textures.get(key).getSourceImage();
      const y = key === 's3-machines' ? 176 - img.height : 0;   // machinery stands on a line just below the floor lip
      const ts = scene.add.tileSprite(0, y, W, img.height, key).setOrigin(0, 0).setScrollFactor(0).setDepth(depth);
      this.layers.push({ ts, sf });
    }
    // play plane chunks
    this.chunks = [];
    for (let i = 0; i < meta3.chunks; i++) {
      const k = 's3-chunk' + i; if (!has(k)) continue;
      this.chunks.push(scene.add.image(i * 480, 0, k).setOrigin(0, 0).setDepth(PLAY_DEPTH));
      if (has('s3-bchunk' + i)) this.chunks.push(scene.add.image(i * 480, 0, 's3-bchunk' + i).setOrigin(0, 0).setDepth(PLAY_DEPTH - 2));
    }
    // animated set pieces (hard frame steps)
    this.anims = [];
    const add = (key, x, y, frames, ms, depth, phase = 0) => {
      if (!has(key)) return null;
      const s = scene.add.sprite(x, y, key, 0).setOrigin(0, 1).setDepth(depth);
      this.anims.push({ s, frames, ms, phase, w: s.width });
      return s;
    };
    let n = 0;
    for (const d of meta3.sprites) {
      if (d.k === 'tank') add('s3-tank', d.x, d.y + 1, 8, 170, PLAY_DEPTH - 1, n++ * 3);
      else if (d.k === 'window') add('s3-window', d.x, 108, 4, 220, PLAY_DEPTH - 1, n++);
      else if (d.k === 'door') add('s3-door-' + (d.label || 'LAB 07').replace(' ', '_'), d.x, d.y + 1, 2, 480, PLAY_DEPTH - 1);
    }
    (level.water || []).forEach((w, i) => {
      if (has('s3-toxic' + i)) add('s3-toxic' + i, w.x, 274, 4, 200, PLAY_DEPTH + 1, i);   // surface at y~214
    });
  }

  update(cam) {
    const t = this.scene.time.now, W = this.scene.scale.width, x0 = cam.scrollX - 8, x1 = cam.scrollX + W + 8;
    for (const l of this.layers) l.ts.tilePositionX = Math.round(cam.scrollX * l.sf);
    for (const c of this.chunks) c.setVisible(c.x + 480 > x0 && c.x < x1);
    for (const a of this.anims) {
      const vis = a.s.x + a.w > x0 && a.s.x < x1;
      a.s.setVisible(vis);
      if (vis) a.s.setFrame((Math.floor(t / a.ms) + a.phase) % a.frames);
    }
  }
}
