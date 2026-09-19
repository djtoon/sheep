// Loads everything listed in assets/manifest.json, registers animations from assets/anims.json,
// then generates a procedural placeholder for any texture key the game needs that no art provides yet.
// Art pieces plug in by adding entries to the manifest - no code change required.
import { makePlaceholders } from '../gfx/placeholders.js';

export class Boot extends Phaser.Scene {
  constructor() { super('Boot'); }

  preload() {
    // assets/manifest.json = list of part names; each assets/parts/<name>.json = { assets: [...], anims: [...] }
    // One part file per art piece so parallel work never edits the same file.
    this.load.json('manifest', 'assets/manifest.json');
    this.load.on('loaderror', f => console.warn('asset failed to load:', f.key, f.url));
  }

  create() {
    const parts = this.cache.json.get('manifest') || [];
    for (const p of parts) this.load.json('part-' + p, `assets/parts/${p}.json`);
    this.load.once('complete', () => this.loadAssets(parts));
    this.load.start();
  }

  loadAssets(parts) {
    const m = [], anims = [];
    for (const p of parts) { const j = this.cache.json.get('part-' + p) || {}; m.push(...(j.assets || [])); anims.push(...(j.anims || [])); }
    for (const a of m) {
      if (a.type === 'image') this.load.image(a.key, a.url);
      else if (a.type === 'spritesheet') this.load.spritesheet(a.key, a.url, { frameWidth: a.frameWidth, frameHeight: a.frameHeight, margin: a.margin || 0, spacing: a.spacing || 0 });
      else if (a.type === 'audio') this.load.audio(a.key, a.url);
      else if (a.type === 'bitmapFont') this.load.bitmapFont(a.key, a.url, a.data);
      else if (a.type === 'atlas') this.load.atlas(a.key, a.url, a.data);
    }
    this.load.once('complete', () => {
      makePlaceholders(this);
      for (const a of anims) {
        if (!this.textures.exists(a.texture)) continue;
        const frames = a.frames ? this.anims.generateFrameNumbers(a.texture, { frames: a.frames })
          : this.anims.generateFrameNumbers(a.texture, { start: a.start ?? 0, end: a.end ?? (this.textures.get(a.texture).frameTotal - 2) });
        if (this.anims.exists(a.key)) this.anims.remove(a.key);
        this.anims.create({ key: a.key, frames, frameRate: a.frameRate || 12, repeat: a.repeat ?? -1, yoyo: !!a.yoyo });
      }
      const q = window.__sheep.query;
      const scene = q.get('scene') || (q.get('test') ? 'game' : 'title');
      const map = { title: 'Title', intro: 'Intro', ending: 'Ending' };   // ?scene=title|intro|ending|game
      this.scene.start(map[scene] || 'Game', { stage: +(q.get('stage') || 1), drop: q.get('drop') === '1' });
    });
    this.load.start();
  }
}
