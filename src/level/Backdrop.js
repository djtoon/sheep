// Parallax backdrop behind the playfield. Art lives in assets/world/ (built by art/raw/world/build.py).
// Layers (far -> near): sky, drifting clouds, far mountains, jungle hills, waterfall cliffs (animated),
// jungle canopy + palms, then late-stage enemy-base silhouettes placed in world space. Birds fly across the sky.
// Every layer is a horizontally seamless tile; tile offsets are rounded so pixels stay crisp at 1x.
// Behind the enemy base the layers swap to baked cooler/lighter '-base' textures (hard palette, no alpha),
// staggered far -> near. Each swap cross-fades in hard alpha steps over SWAP_SPAN px of camera travel
// (an overlay tile sprite carries the '-base' texture), so it reads as the air getting hazier, never as a pop.
const SWAP_SPAN = 72, SWAP_STEPS = 4;
// Gorge vistas: full sink within (half gap + VISTA_PAD) of the gorge centre, eased in/out over VISTA_RAMP px of camera
// travel so the near layers settle slowly (a long ramp keeps their vertical speed well under their parallax speed).
const VISTA_PAD = 55, VISTA_RAMP = 400;
const BASE_SWAP ={ 'bg-farcliffs': 3200, 'bg-hills': 3240, 'bg-cliffs': 3300, 'bg-midtrees': 3360, 'bg-canopy': 3420, 'bg-near': 3480 };
const LAYERS = [
  // key, scroll factor, auto drift (px/s), depth, animation frame keys (optional), ms per frame
  { key: 'bg-sky', sf: 0, depth: -100 },
  { key: 'bg-clouds', sf: 0.03, drift: 2.5, depth: -98, lift: 0.2 },
  { key: 'bg-far', sf: 0.07, depth: -96, pad: true, lift: 0.3 },
  { key: 'bg-hills', sf: 0.12, depth: -94, pad: true, lift: 0.4 },
  { key: 'bg-farcliffs', sf: 0.17, depth: -93, y: 104, lift: 0.5 },
  { key: 'bg-cliffs', sf: 0.24, depth: -92, frames: ['bg-cliffs', 'bg-cliffs-1', 'bg-cliffs-2', 'bg-cliffs-3'], frameMs: 130, pad: true, lift: 0.6, sink: 22 },
  { key: 'bg-midtrees', sf: 0.32, depth: -90, pad: true, lift: 0.7, sink: 60 },
  { key: 'bg-canopy', sf: 0.42, depth: -88, pad: true, lift: 0.7, sink: 70 },
  // close set pieces right behind the play plane: big cliffs, falls, towers, bunker, rope bridges
  { key: 'bg-near', sf: 0.6, depth: -84, frames: ['bg-near', 'bg-near-1', 'bg-near-2', 'bg-near-3'], frameMs: 110, offset: 90, pad: true, lift: 0.65, sink: 46 },
  // overhanging jungle canopy + vines framing the top of the screen, in front of the action (terrain fg is 90)
  { key: 'bg-overhang', sf: 1.1, depth: 88, y: 0, lift: 0, fadeOut: [4700, 4960] },
  // boss arena (camera locks at 5020): only a thin leafy fringe so the boss roof silhouette stays clear
  { key: 'bg-overhang-thin', sf: 1.1, depth: 88, y: 0, lift: 0, fadeIn: [4700, 4960] },
];
// Enemy-base props (non-tiling), placed so they appear once the camera reaches the base area (x ~ 3500+).
// sx = where the prop sits on screen when the camera scrollX equals camX.
const BASE_PROPS = [
  // layered jungle outposts around level x ~2300: watchtowers on waterfall cliffs, each farther one smaller/bluer/hazier
  // gorge 1 vista (x~900): a far and a mid outpost behind the rope bridge
  { key: 'bg-outpost0', sf: 0.2, camX: 760, sx: 395, bottom: 84, depth: -87.9, lift: 0.15 },
  { key: 'bg-outpost1', sf: 0.26, camX: 760, sx: 130, bottom: 44, depth: -87.8, lift: 0.15 },
  { key: 'bg-outbridge', sf: 0.2, camX: 2160, sx: 246, bottom: 150, depth: -87.95, lift: 0.15 },
  { key: 'bg-outpost1', sf: 0.26, camX: 2160, sx: 290, bottom: 50, depth: -87.8, lift: 0.15 },
  // crisp mid-distance cliff pair with a rope bridge and tower, framed behind the play plane's rope bridge
  { key: 'bg-midset', sf: 0.4, camX: 2160, sx: 20, bottom: 72, depth: -86.5, lift: 0 },
  { key: 'bg-base', sf: 0.65, camX: 3450, sx: 480, bottom: 48, depth: -83, repeat: 3, lift: 0.9 },
];

export class Backdrop {
  constructor(scene, level) {
    this.scene = scene; this.level = level; this.layers = []; this.birds = [];
    const has = k => scene.textures.exists(k);
    const W = scene.scale.width, H = scene.scale.height;
    // The art was laid out for a ground line at y=214. If the level's main ground sits higher, lift every layer
    // (scaled per layer: far layers move less) so their bottoms stay hidden behind the ground / cliff mass.
    const wsum = {};
    for (const g of level.ground) wsum[g.y] = (wsum[g.y] || 0) + g.w;
    const mainY = +Object.keys(wsum).sort((a, b) => wsum[b] - wsum[a])[0];
    const q = window.__sheep && window.__sheep.query;
    this.shift = q && q.get('bgshift') !== null ? +q.get('bgshift') : Math.min(0, mainY - 214);
    // Vistas: over jungle gorges (gaps in the ground wider than 150px, before the base) the near/mid jungle layers
    // sink so the far cliffs, waterfalls, towers, hills and mountains open up behind the bridge.
    this.gorges = [];
    const gs = [...level.ground].sort((a, b) => a.x - b.x);
    for (let i = 1; i < gs.length; i++) {
      const x0 = gs[i - 1].x + gs[i - 1].w, x1 = gs[i].x;
      if (x1 - x0 >= 150 && x0 < 3400) this.gorges.push({ c: (x0 + x1) / 2, p: (x1 - x0) / 2 + VISTA_PAD });
    }
    let any = false;
    for (const L of LAYERS) {
      if (!has(L.key)) continue; any = true;
      const img = scene.textures.get(L.key).getSourceImage();
      const lift = Math.round(this.shift * (L.lift ?? (L.key === 'bg-sky' ? 0 : 1)));
      const y = (L.y ?? H - img.height) + lift;
      const ts = scene.add.tileSprite(0, y, W, img.height, L.key).setOrigin(0, 0).setScrollFactor(0).setDepth(L.depth);
      // when lifted, continue the layer's bottom downward with a mirrored strip of its last rows
      let padTs = null;
      if (L.pad && y + img.height < H) {
        const need = H - (y + img.height), tex = scene.textures.get(L.key), fname = '__padbot';
        if (!tex.has(fname)) tex.add(fname, 0, 0, img.height - 48, img.width, 48);
        padTs = scene.add.tileSprite(0, y + img.height, W, Math.min(48, need), L.key, fname)
          .setOrigin(0, 0).setScrollFactor(0).setDepth(L.depth).setFlipY(true);
      }
      const frames = (L.frames || []).filter(has);
      const l = { key: L.key, base: false, ts, padTs, y0: y, sink: L.sink || 0, sf: L.sf, fadeIn: L.fadeIn, fadeOut: L.fadeOut, offset: L.offset || 0, drift: L.drift || 0, frames, frameMs: L.frameMs || 150, cur: 0 };
      this.layers.push(l);
      // base-area cross-fade: an overlay copy of the layer (and its pad strip) carrying the '-base' texture, drawn just above it
      if (BASE_SWAP[L.key] !== undefined && has(L.key + '-base')) {
        l.over = scene.add.tileSprite(0, y, W, img.height, L.key + '-base').setOrigin(0, 0).setScrollFactor(0).setDepth(L.depth).setVisible(false);
        l.overKey = L.key + '-base';
        if (padTs) {
          this.padFrame(L.key + '-base');
          l.overPad = scene.add.tileSprite(0, padTs.y, W, padTs.height, L.key + '-base', '__padbot').setOrigin(0, 0).setScrollFactor(0).setDepth(L.depth).setFlipY(true).setVisible(false);
        }
      }
    }
    if (!any) {
      const g = scene.add.graphics().setScrollFactor(0).setDepth(-100);
      g.fillGradientStyle(0x2d6fa8, 0x2d6fa8, 0x9fd0e0, 0x9fd0e0, 1).fillRect(0, 0, W, H);
      return;
    }
    // base props in world space: screenX = x - scrollX * sf  =>  x = sx + camX * sf
    for (const p of BASE_PROPS) {
      if (!has(p.key)) continue;
      const src = scene.textures.get(p.key).getSourceImage();
      const n = p.repeat || 1;
      for (let i = 0; i < n; i++) {
        const x = Math.round(p.sx + p.camX * p.sf) + i * src.width;
        scene.add.image(x, H - (p.bottom ?? 0) + Math.round(this.shift * (p.lift ?? 1)), p.key).setOrigin(0, 1).setScrollFactor(p.sf, 0).setDepth(p.depth);
      }
    }
    // birds: small flocks gliding across the sky now and then
    if (has('bg-bird')) {
      for (let i = 0; i < 5; i++) {
        const b = scene.add.sprite(-50, 0, 'bg-bird', 0).setScrollFactor(0).setDepth(-95);
        b.setVisible(false); this.birds.push(b);
      }
      this.nextFlock = 1500;
    }
  }

  spawnFlock(t) {
    const W = this.scene.scale.width;
    const y0 = 30 + Math.random() * 60, dir = Math.random() < 0.7 ? -1 : 1, n = 2 + Math.floor(Math.random() * 3);
    for (let i = 0; i < n && i < this.birds.length; i++) {
      const b = this.birds[i];
      b.setVisible(true).setFlipX(dir > 0);
      b.bx = dir < 0 ? W + 10 + i * 9 : -10 - i * 9; b.by = y0 + (i % 2) * 5 + i * 2;
      b.vx = dir * (14 + Math.random() * 4); b.ph = Math.random() * 1000;
    }
    this.nextFlock = t + 9000 + Math.random() * 8000;
  }

  // switch a layer (and its mirrored bottom pad strip) to another texture of the same size
  setTex(l, key) {
    l.ts.setTexture(key, '__BASE');
    if (l.padTs) { this.padFrame(key); l.padTs.setTexture(key, '__padbot'); }
  }
  padFrame(key) {
    const tex = this.scene.textures.get(key), img = tex.getSourceImage();
    if (!tex.has('__padbot')) tex.add('__padbot', 0, 0, img.height - 48, img.width, 48);
  }

  update(cam) {
    const t = this.scene.time.now;
    const cx = cam.scrollX + this.scene.scale.width / 2;
    let v = 0;
    for (const g of this.gorges) v = Math.max(v, Math.min(1, Math.max(0, 1 - (Math.abs(cx - g.c) - g.p) / VISTA_RAMP)));
    this.vista = v * v * (3 - 2 * v);
    for (const l of this.layers) {
      l.ts.tilePositionX = Math.round(cam.scrollX * l.sf + l.offset + (l.drift * t) / 1000);
      if (l.sink) {
        const dy = Math.round(l.sink * this.vista);
        l.ts.y = l.y0 + dy; if (l.padTs) { l.padTs.y = l.y0 + l.ts.height + dy; l.padTs.height = Math.max(1, Math.min(48, this.scene.scale.height - l.padTs.y)); }
      }
      if (l.padTs) l.padTs.tilePositionX = l.ts.tilePositionX;
      const fr = l.fadeIn || l.fadeOut;
      if (fr) {
        const k = Math.min(1, Math.max(0, (cam.scrollX - fr[0]) / (fr[1] - fr[0])));
        const a = l.fadeIn ? k : 1 - k;
        l.ts.setAlpha(a).setVisible(a > 0.01);
      }
      const sw = BASE_SWAP[l.key];
      // base swap: 0 -> 1 in SWAP_STEPS hard steps over SWAP_SPAN px; the layer itself switches once the overlay is opaque
      const mix = l.over ? Math.floor(Math.min(1, Math.max(0, (cam.scrollX - sw) / SWAP_SPAN)) * SWAP_STEPS) / SWAP_STEPS : 0;
      const wantBase = mix >= 1;
      const sfx = wantBase ? '-base' : '';
      if (l.frames.length > 1) {
        const f = Math.floor(t / l.frameMs) % l.frames.length;
        if (f !== l.cur || wantBase !== l.base) { l.cur = f; l.base = wantBase; this.setTex(l, l.frames[f] + sfx); }
      } else if (wantBase !== l.base) {
        l.base = wantBase; this.setTex(l, l.key + sfx);
      }
      if (l.over) {
        const on = mix > 0 && mix < 1;
        l.over.setVisible(on); if (l.overPad) l.overPad.setVisible(on);
        if (on) {
          const key = (l.frames.length > 1 ? l.frames[l.cur] : l.key) + '-base';
          if (key !== l.overKey && this.scene.textures.exists(key)) {
            l.overKey = key; l.over.setTexture(key, '__BASE');
            if (l.overPad) { this.padFrame(key); l.overPad.setTexture(key, '__padbot'); }
          }
          l.over.setAlpha(mix).setPosition(l.ts.x, l.ts.y); l.over.tilePositionX = l.ts.tilePositionX;
          if (l.overPad) { l.overPad.setAlpha(mix).setPosition(l.padTs.x, l.padTs.y); l.overPad.height = l.padTs.height; l.overPad.tilePositionX = l.padTs.tilePositionX; }
        }
      }
    }
    if (this.birds.length) {
      if (t > this.nextFlock) this.spawnFlock(t);
      const dt = this.scene.game.loop.delta / 1000;
      for (const b of this.birds) {
        if (!b.visible) continue;
        b.bx += b.vx * dt;
        b.setPosition(Math.round(b.bx), Math.round(b.by + Math.sin((t + b.ph) / 700) * 2));
        b.setFrame(Math.floor((t + b.ph) / 160) % 2);
        if (b.bx < -30 || b.bx > this.scene.scale.width + 30) b.setVisible(false);
      }
    }
  }
}
