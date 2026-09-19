// STAGE 02 renderer: night military base B-02 (backdrop + terrain). Same interface as LevelView: new View2(scene, level), update(cam).
// Art: assets/stage2 (keys 's2-*'), generated from ref/levels/level2.png and pixel-cleaned by art/raw/stage2/build2.py.
// Static terrain is baked once into a world-sized canvas and uploaded as cropped 512px chunks; animated bits are culled off-screen.
const CHUNK = 512;
const OUTLINE = '#0a0e14';

function rng(seed) { let a = seed >>> 0; return () => { a = (a + 0x6D2B79F5) >>> 0; let t = a; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; }

export class View2 {
  constructor(scene, level) {
    this.scene = scene; this.level = level; this.anim = []; this.later = []; this.lights = [];
    this.img = k => scene.textures.exists('s2-' + k) ? scene.textures.get('s2-' + k).getSourceImage() : null;
    const n0 = scene.children.list.length;
    this.backdrop();
    if (!this.img('floor')) { this.fallback(); return; }
    const W = level.width, H = level.height;
    const cv = document.createElement('canvas'); cv.width = W; cv.height = H;
    this.ctx = cv.getContext('2d', { willReadFrequently: true }); this.ctx.imageSmoothingEnabled = false;

    this.floorMix = this.mixStrip(['floor', 'floorB', 'floorC'].filter(k => this.img(k)), W, 23);
    for (const d of level.decor || []) if (d.layer === 'back') this.prop(d);
    for (const p of level.platforms) if (p.style === 'scaffold') this.scaffold(p);
    for (const pit of level.pits || []) this.pit(pit);
    const grounds = [...level.ground].sort((a, b) => b.y - a.y);
    for (const s of grounds) this.ground(s);
    for (const p of level.platforms) if (p.style === 'bridge') this.bridge(p);
    for (const d of level.decor || []) if (!d.layer) this.prop(d);
    this.bakeLights();
    this.upload(cv, 'lv2', 20);
    for (const f of this.later) f();
    this.foreground();
    this.cullList(n0);
  }

  // ---------------------------------------------------------------- backdrop: night sky + far base silhouettes + searchlights
  backdrop() {
    const sc = this.scene, W = sc.scale.width;
    this.par = [];
    if (sc.textures.exists('s2-sky')) {
      sc.add.rectangle(0, 0, W, 270, 0x0a1230).setOrigin(0, 0).setScrollFactor(0).setDepth(-101);
      this.par.push({ ts: sc.add.tileSprite(0, -72, W, 270, 's2-sky').setOrigin(0, 0).setScrollFactor(0).setDepth(-100), sf: 0.04 });
    }
    if (sc.textures.exists('s2-compound')) {   // mid-distance compound with lit windows, one value step lighter/bluer than the near towers
      const ch = this.img('compound').height;
      this.par.push({ ts: sc.add.tileSprite(0, 172 - ch, W, ch, 's2-compound').setOrigin(0, 0).setScrollFactor(0).setDepth(-92).setTint(0x98acd8), sf: 0.12 });
    }
    // far tower line (varied lit towers, 2 value steps back) and mid-ground lit structures (1 step back): baked parallax strips
    this.strip(Array.from({ length: 12 }, (_, i) => 'tower' + i), 0.26, [50, 130], 174, 0.34, -88, 5);
    this.strip(Array.from({ length: 8 }, (_, i) => 'big' + i), 0.5, [150, 260], 156, 0.14, -80, 9);
    // sweeping searchlight beams from the far tower line: flat stepped tones, redrawn ~20 fps
    const g = sc.add.graphics().setScrollFactor(0).setDepth(-95).setBlendMode(Phaser.BlendModes.ADD);
    let t = 0, acc = 99;
    this.bg = { g, draw: (cam) => {
      g.clear();
      for (const [i, bx] of (this.beams || []).entries()) {
        const x = Math.round(bx - cam.scrollX * 0.26); if (x < -200 || x > W + 200) continue;
        const a = -Math.PI / 2 + Math.sin(t / 2200 + i * 2.1) * 0.7, oy = 80;
        for (const [len, al, sp] of [[230, 0.06, 0.16], [160, 0.07, 0.11], [90, 0.09, 0.07]]) {
          g.fillStyle(0xcfe4ff, al);
          g.fillTriangle(x, oy, x + Math.cos(a - sp) * len, oy + Math.sin(a - sp) * len, x + Math.cos(a + sp) * len, oy + Math.sin(a + sp) * len);
        }
      }
    }, tick: (dt, cam) => { t += dt; acc += dt; if (acc >= 50) { acc = 0; this.bg.draw(cam); } } };
  }
  strip(keys, sf, [g0, g1], bottom, mix, depth, seed) {
    const sc = this.scene, keysOk = keys.filter(k => this.img(k)); if (!keysOk.length) return;
    const Wd = Math.ceil(this.level.width * sf + sc.scale.width + 40), cv = document.createElement('canvas'); cv.width = Wd; cv.height = 270;
    const c = cv.getContext('2d', { willReadFrequently: true }); c.imageSmoothingEnabled = false; const r = rng(seed); let last = -1;
    for (let x = 10 + r() * 40; x < Wd - 10;) {
      let k; do { k = Math.floor(r() * keysOk.length); } while (k === last && keysOk.length > 1); last = k;
      const im = this.shade(this.img(keysOk[k]), mix, [22, 34, 64]);
      const flip = r() < 0.4;
      c.save(); if (flip) { c.translate(Math.round(x) + im.width, 0); c.scale(-1, 1); c.drawImage(im, 0, bottom - im.height); } else c.drawImage(im, Math.round(x), bottom - im.height); c.restore();
      if (sf < 0.3 && r() < 0.35) (this.beams = this.beams || []).push(x + im.width / 2);
      x += im.width + g0 + r() * (g1 - g0) - (sf > 0.3 ? 0 : im.width * 0.3);
    }
    this.upload(cv, 'par' + Math.round(sf * 100), depth, sf);
  }
  // ---------------------------------------------------------------- helpers  // ---------------------------------------------------------------- helpers
  groundYAt(x) { let b = 999; for (const s of this.level.ground) if (x >= s.x && x < s.x + s.w) b = Math.min(b, s.y); return b; }
  shade(im, mix, col = [16, 24, 44]) {   // one depth step: mix toward night navy (hard pixels, no alpha overlay)
    const t = document.createElement('canvas'); t.width = im.width; t.height = im.height;
    const g = t.getContext('2d'); g.drawImage(im, 0, 0);
    const id = g.getImageData(0, 0, t.width, t.height), d = id.data;
    for (let i = 0; i < d.length; i += 4) if (d[i + 3]) {
      const hot = d[i] > 200 && d[i + 1] > 140;   // lamps and lit windows keep their glow
      if (!hot) for (let c = 0; c < 3; c++) d[i + c] = Math.round(d[i + c] * (1 - mix) + col[c] * mix);
    }
    g.putImageData(id, 0, 0); return t;
  }
  draw(k, x, y, mix = 0, flip = false) {
    let im = this.img(k); if (!im) return null;
    if (mix) im = this.shade(im, mix);
    const c = this.ctx;
    if (flip) { c.save(); c.translate(Math.round(x) + im.width, Math.round(y)); c.scale(-1, 1); c.drawImage(im, 0, 0); c.restore(); }
    else c.drawImage(im, Math.round(x), Math.round(y));
    return im;
  }
  mixStrip(keys, W, seed) {
    const r = rng(seed), first = this.img(keys[0]), H = first.height, cv = document.createElement('canvas'); cv.width = W; cv.height = H;
    const c = cv.getContext('2d', { willReadFrequently: true }); c.imageSmoothingEnabled = false; let last = -1;
    for (let x = 0; x < W;) {
      let k; do { k = Math.floor(r() * keys.length); } while (k === last && keys.length > 1); last = k;
      const im = this.img(keys[k]), sw = im.width, flip = r() < 0.5 && k === 0;   // only the plain girder tile flips (features keep their lighting)
      c.save(); if (flip) { c.translate(x + sw, 0); c.scale(-1, 1); c.drawImage(im, 0, 0); } else c.drawImage(im, x, 0); c.restore();
      x += sw;
    }
    return cv;
  }
  hazard(x, y, w, h) {
    const c = this.ctx; c.fillStyle = '#16181a'; c.fillRect(x, y, w, h); c.fillStyle = '#e0a526';
    for (let i = 0; i < w; i++) for (let j = 0; j < h; j++) if (((i + j) >> 2) % 2 === 0) c.fillRect(x + i, y + j, 1, 1);
  }

  // ---------------------------------------------------------------- ground: riveted steel floor + girder under-structure
  ground(s) {
    const c = this.ctx, H = this.level.height, im = this.floorMix || this.img('floor');
    const L = this.level.ground.find(n => n.x + n.w === s.x), R = this.level.ground.find(n => n.x === s.x + s.w);
    const exL = !L || L.y > s.y, exR = !R || R.y > s.y;
    c.save(); c.beginPath(); c.rect(s.x, s.y, s.w, H - s.y); c.clip();
    c.translate(0, s.y - 2); c.fillStyle = c.createPattern(im, 'repeat-x'); c.fillRect(s.x, 0, s.w, im.height);
    // below the art: keep tiling its bottom foundation course (never the hazard band again)
    if (!this.foot) { const fi = this.img('floor'), f = document.createElement('canvas'); f.width = fi.width; f.height = 20; f.getContext('2d').drawImage(fi, 0, fi.height - 20, fi.width, 20, 0, 0, fi.width, 20); this.foot = f; }
    c.fillStyle = c.createPattern(this.foot, 'repeat'); c.fillRect(s.x, im.height, s.w, H); c.restore();
    // darker in steps toward the bottom (the under-structure recedes into the night)
    for (let y = s.y + 40, k = 0; y < H; y += 12, k++) { c.fillStyle = `rgba(6,10,20,${Math.min(0.38, 0.06 + k * 0.06).toFixed(2)})`; c.fillRect(s.x, y, s.w, 12); }
    // walk lip: dark line above, white rim, light plate
    c.fillStyle = OUTLINE; c.fillRect(s.x, s.y - 1, s.w, 1);
    c.fillStyle = '#f4f6ee'; c.fillRect(s.x, s.y, s.w, 1);
    c.fillStyle = '#9aa0a0'; c.fillRect(s.x, s.y + 1, s.w, 1);
    // exposed side walls: outlined steel edge with a lit left rim / shaded right rim, hazard corner
    for (const [ex, x, lit, nb] of [[exL, s.x, true, L], [exR, s.x + s.w - 4, false, R]]) {
      if (!ex) continue;
      const bot = nb ? nb.y + 2 : s.y + 26;   // a step: just the riser; a shaft edge: a short lip, then the shaft art
      c.fillStyle = OUTLINE; c.fillRect(lit ? x : x + 3, s.y - 1, 1, bot - s.y + 1);
      c.fillStyle = lit ? '#6a7478' : '#20262c'; c.fillRect(lit ? x + 1 : x, s.y + 2, 3, bot - s.y - 2);
      this.hazard(lit ? x + 1 : x, s.y + 2, 3, 10);
    }
  }
  pit(p) {
    const c = this.ctx, H = this.level.height, im = this.img('floor'), top = this.groundYAt(p.x - 1);
    // shaft: the same girder structure, two depth steps darker, fading to black; red warning lights on the walls
    const dark = this.shade(im, 0.62, [4, 8, 16]);
    c.save(); c.beginPath(); c.rect(p.x, top, p.w, H - top); c.clip();
    c.translate(0, top + 20); c.fillStyle = c.createPattern(dark, 'repeat'); c.fillRect(p.x, -20, p.w, H); c.restore();
    for (let y = top + 50, k = 0; y < H; y += 10, k++) { c.fillStyle = `rgba(2,4,8,${Math.min(0.85, 0.25 + k * 0.12).toFixed(2)})`; c.fillRect(p.x, y, p.w, 10); }
    for (const x of [p.x + 6, p.x + p.w - 9]) { c.fillStyle = OUTLINE; c.fillRect(x - 1, top + 36, 5, 5); this.lights.push({ x: x + 1, y: top + 38, r: 10, col: [255, 60, 40] }); c.fillStyle = '#ff4a2a'; c.fillRect(x, top + 37, 3, 3); }
  }
  // steel catwalk bridge over a shaft: bright lip, plate, hazard band, dark riveted beam + truss (hand pixels)
  bridge(p) {
    const c = this.ctx, x = p.x - 2, w = p.w + 4, y = p.y;
    c.fillStyle = OUTLINE; c.fillRect(x, y - 1, w, 13);
    c.fillStyle = '#f4f6ee'; c.fillRect(x, y, w, 1); c.fillStyle = '#a4aaa8'; c.fillRect(x, y + 1, w, 2);
    this.hazard(x, y + 3, w, 4);
    c.fillStyle = '#2a3238'; c.fillRect(x, y + 7, w, 4); c.fillStyle = '#4a555c'; c.fillRect(x, y + 7, w, 1);
    for (let i = x + 4; i < x + w; i += 10) { c.fillStyle = '#8c9694'; c.fillRect(i, y + 9, 1, 1); }
    const top = y + 12, bot = y + 26;
    for (let bx = x + 2; bx < x + w - 3; bx += 16) {
      const e = Math.min(bx + 16, x + w - 3);
      for (let i = 0; i <= bot - top; i++) { const t = i / (bot - top), xa = Math.round(bx + t * (e - bx)), xb = Math.round(e - t * (e - bx));
        c.fillStyle = OUTLINE; c.fillRect(xa - 1, top + i, 3, 1); c.fillRect(xb - 1, top + i, 3, 1);
        c.fillStyle = t < 0.4 ? '#5a666c' : '#3a444a'; c.fillRect(xa, top + i, 1, 1); c.fillRect(xb, top + i, 1, 1); }
      c.fillStyle = OUTLINE; c.fillRect(bx - 1, top, 3, bot - top); c.fillStyle = '#6e7a80'; c.fillRect(bx, top, 1, bot - top);
    }
    c.fillStyle = OUTLINE; c.fillRect(x + 1, bot, w - 2, 4); c.fillStyle = '#56626a'; c.fillRect(x + 2, bot, w - 4, 1); c.fillStyle = '#262e34'; c.fillRect(x + 2, bot + 1, w - 4, 2);
  }
  // generated scaffold catwalk: left bay + repeated middle bay + right bay (bay = 88px); legs stretched to the ground
  scaffold(p) {
    const c = this.ctx, im = this.img('scaffold'); if (!im) return;
    const DECK = 15, x0 = p.x - 2, y0 = p.y - DECK, gy = this.groundYAt(p.x + p.w / 2);
    const tmp = document.createElement('canvas'); const n = Math.max(0, Math.round((p.w + 4 - 177) / 88));
    tmp.width = 177 + n * 88; tmp.height = Math.max(im.height, gy - y0 + 2); const t = tmp.getContext('2d');
    const draw = (sx, sw, dx) => {
      t.drawImage(im, sx, 0, sw, im.height - 8, dx, 0, sw, im.height - 8);                      // everything but the feet
      for (let yy = im.height - 8; yy < tmp.height - 8; yy++) t.drawImage(im, sx, im.height - 12, sw, 1, dx, yy, sw, 1);   // stretch legs
      t.drawImage(im, sx, im.height - 8, sw, 8, dx, tmp.height - 8, sw, 8);                       // feet on the ground
    };
    draw(0, 88, 0); for (let k = 0; k < n; k++) draw(88, 88, 88 + k * 88); draw(176, im.width - 176, 88 + n * 88);
    c.drawImage(tmp, x0, y0);
    // bright walk lip on the deck + warm pools under the hanging lamps
    c.fillStyle = '#f4f6ee'; c.fillRect(x0 + 2, p.y, tmp.width - 4, 1);
    for (let lx = x0 + 18; lx < x0 + tmp.width - 10; lx += 44) this.lights.push({ x: lx, y: p.y + 12, r: 16, k: 0.6, rim: 0.2, col: [255, 176, 70], floor: gy });
  }
  prop(d) {
    const k = d.k, back = d.layer === 'back', mix = back ? 0.18 : 0;
    if (k === 'fence') { const im = this.img('fence'); if (!im) return; for (let i = 0; i < (d.n || 1); i++) { const fx = d.x + i * (im.width - 3); const gy = d.y ?? this.groundYAt(fx + 4); if (gy > 300) continue; this.draw('fence', fx, gy - im.height + 1, 0.22); } return; }
    const im = this.img(k); if (!im) return;
    const gy = d.y ?? this.groundYAt(d.x + im.width / 2), y = gy - im.height + 1;
    this.draw(k, d.x, y, mix, !!d.flip);
    if (k === 'lamp') this.lights.push({ x: d.x + im.width - 5, y: y + 8, r: 54, col: [255, 170, 60], floor: gy });
    if (k === 'watchtower') this.lights.push({ x: d.x + im.width / 2, y: y + 16, r: 20, col: [255, 170, 60] });
    if (k === 'fortress') for (const [fx, fy] of [[0.36, 0.44], [0.66, 0.44], [0.5, 0.2]]) this.lights.push({ x: d.x + im.width * fx, y: y + im.height * fy, r: 18, k: 0.6, col: [255, 170, 70] });
    if (k === 'radar' || k === 'watchtower' || k === 'fortress') this.beacons(k, d.x, y, im);
  }
  // blinking red beacons: find the red pixels at the top of the art and toggle a bright overlay on them
  beacons(k, x, y, im) {
    const t = document.createElement('canvas'); t.width = im.width; t.height = im.height; const g = t.getContext('2d'); g.drawImage(im, 0, 0);
    const d = g.getImageData(0, 0, im.width, Math.min(im.height, 40)).data, pts = [];
    for (let yy = 0; yy < Math.min(im.height, 40); yy++) for (let xx = 0; xx < im.width; xx++) { const i = (yy * im.width + xx) * 4; if (d[i + 3] && d[i] > 170 && d[i + 1] < 90 && d[i + 2] < 90) pts.push([xx, yy]); }
    if (!pts.length) return;
    this.later.push(() => {
      const gr = this.scene.add.graphics().setDepth(20.5); gr.fillStyle(0xffd0c0, 1); for (const [xx, yy] of pts) gr.fillRect(x + xx, y + yy, 1, 1);
      gr.__x0 = x; gr.__x1 = x + im.width;
      this.scene.tweens.add({ targets: gr, alpha: 0, duration: 500, yoyo: true, repeat: -1, delay: (x * 7) % 900, hold: 300 });
    });
  }
  searchBeam(x, y) {
    this.later.push(() => {
      const sc = this.scene, g = sc.add.graphics().setDepth(19).setBlendMode(Phaser.BlendModes.ADD); g.__x0 = x - 200; g.__x1 = x + 200;
      let t = x, acc = 99;
      const draw = () => { g.clear(); const a = -Math.PI / 2 + 0.2 + Math.sin(t / 1900) * 0.7;
        for (const [len, al, sp] of [[190, 0.07, 0.13], [130, 0.08, 0.09], [70, 0.1, 0.055]]) { g.fillStyle(0xfff2c8, al);
          g.fillTriangle(x, y, x + Math.cos(a - sp) * len, y + Math.sin(a - sp) * len, x + Math.cos(a + sp) * len, y + Math.sin(a + sp) * len); } };
      const tick = dt => { t += dt; acc += dt; if (acc >= 50) { acc = 0; draw(); } }; tick.x0 = g.__x0; tick.x1 = g.__x1; this.anim.push(tick); draw();
    });
  }
  // warm sodium light: hard-stepped additive pools baked into the terrain pixels (only lights opaque pixels) +
  // a flat pool on the floor under lamps
  bakeLights() {
    const c = this.ctx, W = this.level.width, H = this.level.height;
    for (const L of this.lights) {
      const pools = [[L.x, L.y, L.r, 1, L.k ?? 1]];
      if (L.floor) pools.push([L.x, L.floor + 3, Math.max(28, L.r * 1.25), 0.24, 1.6]);   // wide flat pool on the deck under the lamp
      for (const [cx, cy, r, ys, kk] of pools) {
        const x0 = Math.max(0, Math.floor(cx - r)), y0 = Math.max(0, Math.floor(cy - r * ys)), w = Math.min(W - x0, Math.ceil(r * 2)), h = Math.min(H - y0, Math.ceil(r * 2 * ys) + 1);
        if (w <= 0 || h <= 0) continue;
        const id = c.getImageData(x0, y0, w, h), d = id.data, src = new Uint8ClampedArray(d);
        for (let yy = 0; yy < h; yy++) for (let xx = 0; xx < w; xx++) {
          const i = (yy * w + xx) * 4; if (!src[i + 3]) continue;
          const dx = (x0 + xx - cx) / r, dy = (y0 + yy - cy) / (r * ys), q = Math.sqrt(dx * dx + dy * dy); if (q >= 1) continue;
          let k = (q < 0.3 ? 0.5 : q < 0.6 ? 0.3 : 0.14) * kk;                               // three hard steps
          // rim light: pixels whose neighbour toward the lamp is darker/empty (an edge facing the light) get a strong warm kick
          const nx = xx + Math.sign(cx - (x0 + xx)), ny = yy + Math.sign(cy - (y0 + yy));
          if (nx >= 0 && nx < w && ny >= 0 && ny < h) { const j = (ny * w + nx) * 4, lj = src[j] + src[j + 1] + src[j + 2], li = src[i] + src[i + 1] + src[i + 2];
            if (!src[j + 3] || lj < li - 60) k += (L.rim ?? 0.35) * kk * (1 - q); }
          // multiplicative warm light (keeps the steel's own contrast: no washed-out stripes), small additive floor so dark steel still warms
          d[i] = Math.min(255, d[i] * (1 + 1.5 * k) + 40 * k); d[i + 1] = Math.min(255, d[i + 1] * (1 + 1.0 * k) + 22 * k); d[i + 2] = Math.min(255, d[i + 2] * (1 + 0.25 * k));
        }
        c.putImageData(id, x0, y0);
      }
    }
  }
  foreground() {
    const sc = this.scene, W = sc.scale.width, H = this.level.height;
    const L = 'tr-fg-leaves-l', R = 'tr-fg-leaves-r';
    if (sc.textures.exists(L)) sc.add.image(-26, H - 86, L).setOrigin(0, 0).setScrollFactor(0).setDepth(91).setTint(0x6a7a92);
    if (sc.textures.exists(R)) sc.add.image(W - sc.textures.get(R).getSourceImage().width + 26, H - 72, R).setOrigin(0, 0).setScrollFactor(0).setDepth(91).setTint(0x6a7a92);
    // jungle canopy hanging into the top-left corner, like the mockup (behind the HUD, never over the play lane)
    if (sc.textures.exists('tr-fg-leaves-l2')) sc.add.image(-30, -40, 'tr-fg-leaves-l2').setOrigin(0, 0).setScrollFactor(0).setDepth(-60).setFlipY(true).setTint(0x4a5a78);
    if (sc.textures.exists('tr-fg-leaves-r2')) sc.add.image(W - 60, -46, 'tr-fg-leaves-r2').setOrigin(0, 0).setScrollFactor(0).setDepth(-60).setFlipY(true).setTint(0x4a5a78);
  }

  upload(cv, name, depth, sf = 1) {
    const W = cv.width, H = cv.height, sc = this.scene, g = cv.getContext('2d');
    for (let cx = 0, i = 0; cx < W; cx += CHUNK, i++) {
      const w = Math.min(CHUNK, W - cx), key = name + '-' + i;
      if (sc.textures.exists(key)) sc.textures.remove(key);
      const a = g.getImageData(cx, 0, w, H).data; let y0 = H, y1 = -1;
      for (let y = 0; y < H; y++) { const o = y * w * 4; for (let k = 3; k < w * 4; k += 16) if (a[o + k]) { if (y < y0) y0 = y; y1 = y; break; } }
      if (y1 < 0) continue; y0 = Math.max(0, y0 - 1); const h = Math.min(H, y1 + 2) - y0;
      const t = sc.textures.createCanvas(key, w, h); t.context.imageSmoothingEnabled = false;
      t.context.drawImage(cv, cx, y0, w, h, 0, 0, w, h); t.refresh();
      sc.add.image(cx, y0, key).setOrigin(0, 0).setDepth(depth).setScrollFactor(sf, 1);
    }
  }
  cullList(n0) {
    this.cull = [];
    for (const o of this.scene.children.list.slice(n0)) {
      if (o.scrollFactorX !== 1 || o.type === 'Zone' || /^(lv2|par)/.test(o.texture?.key || '')) continue;
      let x0, x1; if (o.type === 'Graphics') { x0 = o.__x0; x1 = o.__x1; if (x0 === undefined) continue; } else { const b = o.getBounds(); x0 = b.x; x1 = b.x + b.width; }
      this.cull.push({ o, x0, x1, on: true });
    }
  }
  fallback() {
    const g = this.scene.add.graphics().setDepth(20);
    for (const s of this.level.ground) g.fillStyle(0x3a4046, 1).fillRect(s.x, s.y, s.w, this.level.height - s.y);
    for (const p of this.level.platforms) g.fillStyle(0x6a7076, 1).fillRect(p.x, p.y, p.w, 5);
  }

  update(cam) {
    for (const l of this.par || []) l.ts.tilePositionX = cam.scrollX * l.sf;
    const dt = this.scene.game.loop.delta;
    if (this.bg) this.bg.tick(dt, cam);
    const L = cam.scrollX - 64, R = cam.scrollX + this.scene.scale.width + 64;
    if (this.cull) for (const e of this.cull) { const on = e.x1 > L && e.x0 < R; if (on !== e.on) { e.on = on; e.o.setVisible(on); } }
    for (const f of this.anim) { if (f.x0 !== undefined && (f.x1 < L || f.x0 > R)) continue; f(dt); }
  }
}
