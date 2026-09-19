import { Backdrop } from './Backdrop.js';
// Draws the playfield: cliffs, grass, bridges, catwalks, props, water/falls and foreground leaves.
// Physics lives in Game.js; this is visuals only. Static terrain is composited once into an offscreen
// canvas the size of the level (pixel-exact, world-aligned tiling) and uploaded as 512px-wide chunk textures.
// Art comes from assets/terrain (keys 'tr-*', built by art/raw/terrain/build_terrain.py).

const CHUNK = 512;
const OUTLINE = '#10161a';

function rng(seed) { // mulberry32
  let a = seed >>> 0;
  return () => { a = (a + 0x6D2B79F5) >>> 0; let t = a; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
}

export class LevelView {
  constructor(scene, level) {
    this.scene = scene; this.level = level; this.anim = [];
    this.backdrop = new Backdrop(scene, level);
    this.img = k => scene.textures.exists('tr-' + k) ? scene.textures.get('tr-' + k).getSourceImage() : null;
    if (!this.img('cliff')) { this.fallback(); return; }
    this.rand = rng(1337); this.later = [];

    const W = level.width, H = level.height;
    this.n0 = scene.children.list.length;
    const back = document.createElement('canvas'); back.width = W; back.height = H;
    const ctx = back.getContext('2d', { willReadFrequently: true }); ctx.imageSmoothingEnabled = false;
    this.ctx = ctx;
    this.pat = {};

    this.canv = {};
    if (this.img('face2') && this.img('face3')) this.canv.faceMix = this.mixStrip(['face', 'face2', 'face3'], W, 77);
    const grounds = [...level.ground].sort((a, b) => b.y - a.y); // lower first, raised cliffs overlap them
    // scenery that stands behind the ground line (bunkers, towers, fences) goes first
    for (const d of (level.decor || [])) if (d.layer === 'back') this.prop(d);
    for (const p of level.platforms) if (p.style === 'catwalk') this.catwalkSupports(p);
    for (const s of grounds) this.groundBlock(s);
    for (const s of grounds) this.groundTop(s);
    for (const p of level.platforms) {
      if (p.style === 'ledge') this.ledge(p);
      else if (p.style === 'rope') this.ropeBridge(p);
      else if (p.style === 'steel') this.steelBridge(p);
      else if (p.style === 'catwalk') this.catwalk(p);
    }
    this.scatter(level);
    for (const d of (level.decor || [])) if (!d.layer) this.prop(d);

    this.upload(back, 'lv-back', 20);
    // chasm walls: stepped rock tiers inside every water gap, behind the cascades (depth 17)
    const mid = document.createElement('canvas'); mid.width = W; mid.height = H;
    this.midCtx = mid.getContext('2d', { willReadFrequently: true }); this.midCtx.imageSmoothingEnabled = false;
    this.waterLine = 238;
    { const save = this.ctx; this.ctx = this.midCtx;
      for (const d of (level.decor || [])) if (d.layer === 'far') this.prop(d);
      this.ctx = save; }
    // generated gorge set piece (tiered falls, boulders, plunge pool) where available; procedural chasm otherwise
    const gw = [260, 280, 300, 320];
    for (const wa of level.water) { const W = gw.find(v => v >= wa.w + 20) || 320; wa._gorge = scene.textures.exists('tr-gorge-' + W) ? 'tr-gorge-' + W : null; }
    for (const wa of level.water) if (!wa._gorge) this.chasm(wa);
    // rock columns holding up every raised ledge, drawn over the chasm walls, behind water and ground
    for (const p of level.platforms) if (p.style === 'ledge') this.pillar(p);
    this.upload(mid, 'lv-mid', 17);

    for (const wa of level.water) this.water(wa);
    for (const f of this.later) f();
    this.foreground(level);
    this.baseForeground(level);
    this.lowerForeground(level);
    if (!window.__sheep?.query?.get('nocull')) this.buildCull();
  }
  // Perf: every world-space object LevelView made (animated sprites, graphics, tile sprites, images) is hidden and its
  // animation paused while it is more than 64px outside the camera; per-frame anim callbacks only run when on screen.
  buildCull() {
    this.cull = [];
    for (const o of this.scene.children.list.slice(this.n0)) {
      if (o.scrollFactorX !== 1 || o.type === 'Zone') continue;
      if (/^lv-(back|mid)-/.test(o.texture?.key || '')) continue;     // static 512px chunks: GPU cost only, keep
      let x0, x1;
      if (o.type === 'Graphics') { x0 = o.__x0; x1 = o.__x1; if (x0 === undefined) continue; }
      else { const b = o.getBounds(); x0 = b.x; x1 = b.x + b.width; }
      this.cull.push({ o, x0, x1, on: true });
    }
  }

  mixStrip(keys, W, seed) {
    const r = rng(seed), H = this.img(keys[0]).height, cv = document.createElement('canvas'); cv.width = W; cv.height = H;
    const c = cv.getContext('2d'); c.imageSmoothingEnabled = false;
    const tmp = document.createElement('canvas'); tmp.width = 260; tmp.height = H; const t = tmp.getContext('2d', { willReadFrequently: true });
    let last = -1;
    for (let x = 0; x < W;) {
      let k; do { k = Math.floor(r() * keys.length); } while (k === last && keys.length > 1); last = k;
      const im = this.img(keys[k]), sw = Math.min(im.width, 110 + Math.floor(r() * 110)), sx = Math.floor(r() * (im.width - sw)), flip = r() < 0.5;
      t.clearRect(0, 0, 260, H); t.save(); if (flip) { t.translate(sw, 0); t.scale(-1, 1); } t.drawImage(im, sx, 0, sw, H, 0, 0, sw, H); t.restore();
      if (x > 0) { // dithered seam: left 14px fade in by an ordered pattern
        const id = t.getImageData(0, 0, 14, H), d = id.data, B = [0, 8, 2, 10, 12, 4, 14, 6, 3, 11, 1, 9, 15, 7, 13, 5];
        for (let yy = 0; yy < H; yy++) for (let i = 0; i < 14; i++) if (B[(yy % 4) * 4 + (i % 4)] >= i * 16 / 14) d[(yy * 14 + i) * 4 + 3] = 0;
        t.putImageData(id, 0, 0);
      }
      c.drawImage(tmp, 0, 0, sw, H, x, 0, sw, H);
      x += sw - 14;
    }
    return cv;
  }
  upload(cv, name, depth) {
    const W = cv.width, H = cv.height, scene = this.scene;
    for (let cx = 0, i = 0; cx < W; cx += CHUNK, i++) {
      const w = Math.min(CHUNK, W - cx), key = name + '-' + i;
      if (scene.textures.exists(key)) scene.textures.remove(key);
      // perf: crop each chunk to its opaque rows (skies/empty gorges cost fill-rate for nothing); skip empty chunks
      const a = cv.getContext('2d').getImageData(cx, 0, w, H).data;
      let y0 = H, y1 = -1;
      for (let y = 0; y < H; y++) { const o = y * w * 4; for (let k = 3; k < w * 4; k += 16) if (a[o + k]) { if (y < y0) y0 = y; y1 = y; break; } }
      if (y1 < 0) continue;
      y0 = Math.max(0, y0 - 1); const h = Math.min(H, y1 + 2) - y0;
      const t = scene.textures.createCanvas(key, w, h);
      t.context.imageSmoothingEnabled = false;
      t.context.drawImage(cv, cx, y0, w, h, 0, 0, w, h); t.refresh();
      scene.add.image(cx, y0, key).setOrigin(0, 0).setDepth(depth);
    }
  }
  // inner walls of a chasm: rock shelves stepping down from both lips to the basin, darker the deeper they go
  chasm(wa) {
    const H = this.level.height, x = wa.x, w = wa.w, r = rng(x + 3), WL = this.waterLine;
    const gl = Math.min(this.groundYAt(x - 2), H), gr = Math.min(this.groundYAt(x + w + 1), H);
    wa._shelves = [];
    const side = (fromLeft, gy) => {
      const ww = Math.round(w * 0.3), x0 = fromLeft ? x - 4 : x + w - ww + 4, spans = [];
      const tiers = [[0, gy + 8], [0.34, gy + Math.round((WL - gy) * 0.45)], [0.68, WL - 10]];
      let v = 0;
      for (let i = 0; i < ww; i++) {
        const t = fromLeft ? i / ww : 1 - i / ww;
        let top = tiers[0][1]; for (const [tt, ty] of tiers) if (t >= tt) top = ty;
        v += (r() - 0.5) * 2; v *= 0.6;
        spans.push([Math.round(top + v), H + 2]);
      }
      const cv = this.massCanvas(x0, gy, ww, H - gy + 2, spans, 'cliff', 0.6);
      const g = cv.getContext('2d'); g.globalCompositeOperation = 'source-atop';
      g.fillStyle = 'rgba(6,14,22,0.22)'; g.fillRect(0, 0, ww, H);
      this.midCtx.drawImage(cv, x0, gy);
      const save = this.ctx; this.ctx = this.midCtx;
      for (const [tt, ty] of tiers.slice(1)) {
        const tw = Math.round(ww * 0.34);
        const a = fromLeft ? x0 + Math.round(tt * ww) : x0 + Math.round((1 - tt) * ww) - tw;
        this.grassStrip(a, a + tw, ty - 3, Array(tw).fill(ty + 5 + Math.floor(r() * 6)));
        // shelf lip where water spills to the next tier
        wa._shelves.push({ x: fromLeft ? a + tw - 6 : a - 30, y: ty, flip: !fromLeft });
      }
      this.ctx = save;
    };
    if (gl < H) side(true, gl);
    if (gr < H) side(false, gr);
  }
  // ---------- procedural waterfalls: every fall is unique (own width profile, wobbling edges, foam lip that
  // curls over the rock, streaks drifting down), baked into an 8-frame canvas spritesheet at runtime
  fall(x, y, w, h, depth, seed, opts = {}) {
    const sc = this.scene, N = 8, P = 40, r = rng(seed * 31 + 7), key = 'fall-' + seed + '-' + w + 'x' + h;
    const pad = Math.max(8, Math.round(w * 0.35)), FW = w + pad * 2;
    if (!sc.textures.exists(key)) {
      const B = ['#12375c', '#1f5a8e', '#3a86c0', '#74b8e2', '#c2e6f6', '#f8fdff'];
      const bow = (r() < 0.5 ? -1 : 1) * (1 + r() * 2.5), spread = opts.spread ?? (0.25 + r() * 0.35);
      const nl = [], nr = []; let vl = 0, vr = 0;
      for (let yy = 0; yy < h; yy++) { vl = vl * 0.85 + (r() - 0.5) * 2.2; vr = vr * 0.85 + (r() - 0.5) * 2.2; nl.push(vl); nr.push(vr); }
      const L = [], R = [];
      for (let yy = 0; yy < h; yy++) {
        const t = yy / Math.max(1, h - 1);
        // rounded lip: the sheet bulges out over the edge (narrow crown, fast widening in the first rows)
        const lip = yy < 5 ? [0.55, 0.78, 0.9, 0.96, 1][yy] : 1;
        const half = w / 2 * lip * (1 + spread * Math.sqrt(t));
        const cxx = pad + w / 2 + bow * Math.sin(t * Math.PI);          // bowed centre line
        L.push(Math.round(cxx - half + nl[yy] * (0.3 + t))); R.push(Math.round(cxx + half + nr[yy] * (0.3 + t)));
      }
      // fraying: columns drop out progressively below ~35% height, splitting the sheet into tapering strands
      const colGate = Array.from({ length: FW }, (_, i) => (Math.sin(i * 1.7 + seed) * 0.5 + 0.5) * 0.6 + r() * 0.4);
      const colBase = Array.from({ length: FW }, (_, i) => 1 + Math.floor((Math.sin(i * 0.9 + seed) + Math.sin(i * 0.37 + seed * 2) + 2) / 4 * 2.4));
      const dashes = Array.from({ length: FW }, () => Array.from({ length: 2 + Math.floor(r() * 2) }, () => [Math.floor(r() * P), 5 + Math.floor(r() * 12), 1 + Math.floor(r() * 2)]));
      const foamH = opts.noMist ? 0 : Math.min(10, Math.round(h * 0.18));
      const tex = sc.textures.createCanvas(key, FW * N, h), c = tex.context;
      for (let f = 0; f < N; f++) {
        const ox = f * FW, fr = rng(seed * 97 + f);
        for (let yy = 0; yy < h - foamH; yy++) {
          const t = yy / h, a = Math.max(0, L[yy]), b = Math.min(FW, R[yy]);
          const fray = Math.max(0, (t - 0.35) / 0.65);                  // 0 at 35% height -> 1 at the bottom
          for (let i = a; i < b; i++) {
            const edgeD = Math.min(i - a, b - 1 - i) / Math.max(1, (b - a) / 2);   // 0 at edge, 1 in centre
            if (fray > 0 && colGate[i] < fray * 0.75 * (1.2 - edgeD * 0.6)) {      // gaps open, edges fray first
              if (fr() < 0.04 * fray) { c.fillStyle = B[5]; c.fillRect(ox + i, yy, 1, 1); }   // droplets in the gaps
              continue;
            }
            let lv = colBase[i];
            for (const [y0, ln, add] of dashes[i]) { const d = ((yy - y0 - f * (P / N)) % P + P) % P; if (d < ln) lv = Math.max(lv, colBase[i] + add + (d < ln - 2 ? 0 : -1)); }
            const prevIn = i > a && !(fray > 0 && colGate[i - 1] < fray * 0.75 * (1.2 - Math.min(i - 1 - a, b - i) / Math.max(1, (b - a) / 2) * 0.6));
            if (i === a || i === b - 1 || !prevIn) lv = Math.max(lv, 4);   // bright rim on every strand edge
            if (yy < 4) lv = yy < 2 ? 5 : Math.max(lv, 4);                 // white crown on the rounded lip
            c.fillStyle = B[Math.min(5, lv)]; c.fillRect(ox + i, yy, 1, 1);
          }
          // droplets thrown off the outer edges, more as it falls
          if (fr() < 0.1 * (0.3 + t)) { c.fillStyle = B[fr() < 0.5 ? 5 : 4]; c.fillRect(ox + Math.max(0, a - 1 - Math.floor(fr() * 3)), yy, 1, 1); }
          if (fr() < 0.1 * (0.3 + t)) { c.fillStyle = B[fr() < 0.5 ? 5 : 4]; c.fillRect(ox + Math.min(FW - 1, b + Math.floor(fr() * 3)), yy, 1, 1); }
        }
        // 4-tone hard-pixel foam cluster where it lands: dark rim, mid, light cyan, white core bubbles
        if (foamH) {
          const fy = h - foamH, a = Math.max(0, L[fy] - 4), b = Math.min(FW, R[fy] + 4);
          const blobs = [];
          for (let k = 0; k < Math.max(3, (b - a) / 5); k++) blobs.push([a + 2 + fr() * (b - a - 4), fy + 2 + fr() * (foamH - 3), 2 + Math.floor(fr() * 3.5)]);
          const tone = ['#2c6a9a', '#74b8e2', '#c2e6f6', '#f8fdff'];
          for (let ring = 0; ring < 4; ring++) for (const [bx, by, br] of blobs) {
            const rr = br + 1 - ring * 0.9; if (rr <= 0) continue;
            for (let yy = -Math.ceil(rr); yy <= Math.ceil(rr); yy++) {
              const hw = Math.floor(Math.sqrt(Math.max(0, rr * rr - yy * yy)));
              const Y = Math.round(by + yy); if (Y < fy - 2 || Y >= h) continue;
              c.fillStyle = tone[ring]; c.fillRect(ox + Math.round(bx - hw), Y, hw * 2 + 1, 1);
            }
          }
        }
      }
      tex.refresh();
      for (let f = 0; f < N; f++) tex.add(f, 0, f * FW, 0, FW, h);
      sc.anims.create({ key, frames: Array.from({ length: N }, (_, f) => ({ key, frame: f })), frameRate: 12 + (seed % 5), repeat: -1 });
    }
    const sp = sc.add.sprite(Math.round(x - pad), Math.round(y), key, 0).setOrigin(0, 0).setDepth(depth);
    sp.play({ key, startFrame: seed % N });
    if (!opts.noMist) this.mistBand(x + w / 2, Math.min(this.waterLine, y + h) - 4, w + 8, seed);
    return sp;
  }
  // mist over a landing: rounded puffs in 4 hard opaque tones rising and shrinking away (no alpha smear)
  mistBand(cx, y, w, seed) {
    const sc = this.scene, g = sc.add.graphics().setDepth(19.85), r = rng(seed * 5 + 1);
    g.__x0 = cx - w / 2 - 12; g.__x1 = cx + w / 2 + 12;
    const puffs = Array.from({ length: Math.max(3, Math.round(w / 10)) }, () => ({ x: (r() - 0.5) * w, p: r(), s: 0.6 + r() * 0.7 }));
    const tones = [0x5a9ec8, 0x9ed2ec, 0xd4eef8, 0xffffff];
    let t = 0;
    const draw = () => {
      g.clear();
      for (const q of puffs) {
        const ph = (q.p + t / 1700) % 1; if (ph > 0.75) continue;
        const R0 = Math.max(1, Math.round((2 + ph * 5) * q.s * (ph > 0.55 ? 0.6 : 1))), py = Math.round(y - ph * 12), px = Math.round(cx + q.x + Math.sin(ph * 6 + q.p * 9) * 2);
        for (let ring = 0; ring < 4; ring++) {
          const rr = R0 + 1 - ring; if (rr <= 0) continue;
          for (let yy = -rr; yy <= rr; yy++) { const hw = Math.floor(Math.sqrt(rr * rr - yy * yy) * 1.2); g.fillStyle(tones[ring], 1).fillRect(px - hw, py + yy, hw * 2 + 1, 1); }
        }
      }
    };
    let acc = 0; const tick = dt => { t += dt; acc += dt; if (acc >= 66) { acc = 0; draw(); } };
    tick.x0 = g.__x0; tick.x1 = g.__x1; this.anim.push(tick); draw();
  }

  // ---------- helpers
  pattern(k) {
    if (!this.pat[k]) this.pat[k] = this.ctx.createPattern(this.canv?.[k] || this.img(k), 'repeat');
    return this.pat[k];
  }
  // fill a pixel mask (per-column [top,bottom) spans in world coords) with a world-aligned texture, then outline + shade
  massCanvas(x0, y0, w, h, spans, tex, shade = 0.5, oy = 0) {
    const c = document.createElement('canvas'); c.width = w; c.height = h;
    const g = c.getContext('2d'); g.imageSmoothingEnabled = false;
    g.save(); g.translate(-x0, oy - y0); g.fillStyle = this.pattern(tex); g.fillRect(x0, y0 - oy, w, h); g.restore();
    const id = g.getImageData(0, 0, w, h), d = id.data;
    const inside = new Uint8Array(w * h);
    for (let i = 0; i < w; i++) { const [t, b] = spans[i]; for (let y = Math.max(0, t - y0); y < Math.min(h, b - y0); y++) inside[y * w + i] = 1; }
    const oc = [16, 22, 26];
    for (let y = 0; y < h; y++) for (let i = 0; i < w; i++) {
      const p = (y * w + i) * 4;
      if (!inside[y * w + i]) { d[p + 3] = 0; continue; }
      const edge = i === 0 || i === w - 1 || !inside[y * w + i - 1] || !inside[y * w + i + 1] || (y > 0 && !inside[(y - 1) * w + i]) || (y < h - 1 && !inside[(y + 1) * w + i]);
      if (edge) { d[p] = oc[0]; d[p + 1] = oc[1]; d[p + 2] = oc[2]; continue; }
      // near-edge shadow + depth darkening (quantized in 4px bands to stay pixel-y)
      const near = !inside[y * w + Math.max(0, i - 2)] || !inside[y * w + Math.min(w - 1, i + 2)] || (y < h - 2 && !inside[(y + 2) * w + i]);
      const depth = Math.floor((y + y0 - spans[i][0]) / 6) * 6;
      let k = 1 - Math.min(shade, depth / 90);
      if (depth < 12) k *= 1.14;                 // sunlit upper face
      if (near) k *= 0.62;
      d[p] *= k; d[p + 1] *= k; d[p + 2] *= k * 1.02;
    }
    g.putImageData(id, 0, 0);
    return c;
  }
  wobble(n, amp, seed) { const r = rng(seed); const a = []; let v = 0; for (let i = 0; i < n; i++) { v += (r() - 0.5) * 1.6; v *= 0.85; a.push(Math.round(amp * (0.5 + 0.5 * Math.sin(i * 0.23 + seed)) + v)); } return a; }
  neighbour(s, side) {
    for (const n of this.level.ground) {
      if (n === s) continue;
      if (side < 0 && n.x + n.w === s.x) return n;
      if (side > 0 && n.x === s.x + s.w) return n;
    }
    return null;
  }
  drawImg(k, x, y, flip = false) {
    let im = this.img(k); if (!im) return;
    const c = this.ctx;
    if (this.dim) { // push non-walkable scenery back: darker, cooler
      const t = document.createElement('canvas'); t.width = im.width; t.height = im.height;
      const g = t.getContext('2d'); g.drawImage(im, 0, 0); g.globalCompositeOperation = 'source-atop';
      g.fillStyle = `rgba(14,28,48,${this.dim})`; g.fillRect(0, 0, t.width, t.height); im = t;
    }
    if (flip) { c.save(); c.translate(Math.round(x) + im.width, Math.round(y)); c.scale(-1, 1); c.drawImage(im, 0, 0); c.restore(); }
    else c.drawImage(im, Math.round(x), Math.round(y));
  }
  // crisp a structure: deepen dark recesses (windows, doors, vents), brighten top/left rim pixels of every shape edge
  crisp(im) {
    const t = document.createElement('canvas'); t.width = im.width; t.height = im.height;
    const g = t.getContext('2d'); g.drawImage(im, 0, 0);
    const id = g.getImageData(0, 0, t.width, t.height), d = id.data, W = t.width, H = t.height, L = new Float32Array(W * H);
    for (let i = 0; i < W * H; i++) L[i] = (d[i * 4] * 0.3 + d[i * 4 + 1] * 0.59 + d[i * 4 + 2] * 0.11) / 255;
    for (let y = 1; y < H; y++) for (let x = 1; x < W; x++) {
      const i = y * W + x, p = i * 4; if (!d[p + 3]) continue;
      const l = L[i];
      if (l < 0.22) { d[p] *= 0.45; d[p + 1] *= 0.5; d[p + 2] *= 0.6; continue; }                 // recess
      const up = d[((y - 1) * W + x) * 4 + 3] ? L[i - W] : 0, left = d[(i - 1) * 4 + 3] ? L[i - 1] : 0;
      if (up < l - 0.12 || left < l - 0.12) { d[p] = Math.min(255, d[p] * 1.45 + 30); d[p + 1] = Math.min(255, d[p + 1] * 1.45 + 30); d[p + 2] = Math.min(255, d[p + 2] * 1.4 + 26); }
    }
    g.putImageData(id, 0, 0); return t;
  }
  // one background step of atmospheric perspective: mix toward a light haze blue, lower contrast, keep hard pixels
  aerial(im, k) {
    const t = document.createElement('canvas'); t.width = im.width; t.height = im.height;
    const g = t.getContext('2d'); g.drawImage(im, 0, 0);
    const id = g.getImageData(0, 0, t.width, t.height), d = id.data, hz = [150, 190, 214];
    for (let i = 0; i < d.length; i += 4) if (d[i + 3]) for (let c = 0; c < 3; c++) d[i + c] = Math.round(d[i + c] * (1 - k) + hz[c] * k);
    g.putImageData(id, 0, 0); return t;
  }
  groundYAt(x) {
    let best = 999;
    for (const s of this.level.ground) if (x >= s.x && x < s.x + s.w) best = Math.min(best, s.y);
    return best;
  }

  // ---------- cliff-face dressing: the ~100px below the walk line carries content, not plain boulder fill
  dressFace(s, x0, spans) {
    const H = this.level.height, r = rng(s.x * 7 + 3), c = this.ctx, top = s.y + 18;
    if (H - top < 40) return;
    const inFace = (x, y) => { const i = Math.round(x - x0); return i >= 2 && i < spans.length - 2 && spans[i][0] + 3 <= y; };
    const kinds = s.style === 'base' ? ['pipe', 'cave', 'shelf', 'scaffold', 'pipe', 'roots'] : ['cave', 'shelf', 'scaffold', 'shelf', 'roots', 'cave'];
    let k = Math.floor(r() * kinds.length);
    const rows = [[top + 4, top + 26], [top + 40, H - 34]];
    for (const [ya, yb] of rows) {
      if (yb <= ya) continue;
      for (let x = s.x + 10 + r() * 24; x < s.x + s.w - 34; x += 44 + r() * 46, k++) {
        const kind = kinds[k % kinds.length], y = ya + Math.floor(r() * (yb - ya));
        if (!inFace(x, y) || !inFace(x + 34, y)) continue;
        if (kind === 'cave') this.cave(Math.round(x), y, 22 + Math.floor(r() * 14), 24 + Math.floor(r() * 12), r);
        else if (kind === 'shelf') this.faceShelf(Math.round(x), y, 30 + Math.floor(r() * 26), r);
        else if (kind === 'scaffold') { if (ya > top + 20) this.scaffold(Math.round(x), y, 30 + Math.floor(r() * 14), H - y, r); else this.faceShelf(Math.round(x), y, 34, r); }
        else if (kind === 'pipe') this.pipe(Math.round(x), y, r);
        else this.roots(Math.round(x), ya - 8, 24 + Math.floor(r() * 16), r);
      }
    }
    // tower footings: timber pilings + concrete pier down the face below any watchtower standing on this block
    for (const d of (this.level.decor || [])) {
      if (!/^tower/.test(d.k)) continue;
      const im = this.img(d.k); if (!im || d.x < s.x || d.x > s.x + s.w - 10) continue;
      if ((d.y ?? s.y) !== s.y) continue;
      this.footing(d.x + Math.floor(im.width / 2), s.y, H);
    }
  }
  cave(x, y, w, h, r) {
    const c = this.ctx;
    // irregular mouth: rows narrow toward the top (arch), jagged rim
    for (let row = 0; row < h; row++) {
      const t = row / h, half = Math.round(w / 2 * Math.pow(t, 0.55) + (r() < 0.3 ? 1 : 0));
      const cx = x + w / 2;
      c.fillStyle = '#10161a'; c.fillRect(Math.round(cx - half - 1), y + row, half * 2 + 2, 1);
      c.fillStyle = t < 0.3 ? '#161e22' : '#0a0f12'; c.fillRect(Math.round(cx - half), y + row, half * 2, 1);
      if (t > 0.25 && t < 0.9) { c.fillStyle = '#1e282c'; c.fillRect(Math.round(cx - half), y + row, 2, 1); }   // faint inner wall
    }
    // stalactite teeth + mossy lip over the mouth
    for (let i = 4; i < w - 4; i += 3 + Math.floor(r() * 4)) { const ln = 2 + Math.floor(r() * 4); c.fillStyle = '#3a2e22'; c.fillRect(x + i, y + 1, 1, ln); c.fillStyle = '#10161a'; c.fillRect(x + i, y + 1 + ln, 1, 1); }
    this.grassStrip(x + 2, x + w - 2, y - 7, Array(w).fill(0).map(() => y - 2 + Math.floor(r() * 6)), 5);
    // pebble floor catching light at the mouth
    for (let i = 3; i < w - 3; i++) if (r() < 0.5) { c.fillStyle = r() < 0.5 ? '#4a3e2e' : '#2e2820'; c.fillRect(x + i, y + h - 1 - Math.floor(r() * 2), 1, 1); }
    // a crate or a lantern tucked inside some mouths
    if (r() < 0.35) this.drawImg('crate', x + w / 2 - 15, y + h - 26);
    else if (r() < 0.5) { c.fillStyle = '#10161a'; c.fillRect(x + w / 2 - 2, y + 2, 1, 6); c.fillStyle = '#ffc860'; c.fillRect(x + w / 2 - 3, y + 8, 3, 3); c.fillStyle = '#ffe8a8'; c.fillRect(x + w / 2 - 2, y + 9, 1, 1); }
  }
  faceShelf(x, y, w, r) {
    const c = this.ctx;
    // protruding lit rock lip with a dark undercut shadow, moss on top, sometimes a small spill or a crate
    c.fillStyle = '#10161a'; c.fillRect(x - 1, y - 1, w + 2, 6);
    c.fillStyle = '#9c8a64'; c.fillRect(x, y, w, 1);
    c.fillStyle = '#76664a'; c.fillRect(x, y + 1, w, 2);
    c.fillStyle = '#4c4232'; c.fillRect(x, y + 3, w, 1);
    c.fillStyle = 'rgba(6,10,12,0.55)'; c.fillRect(x + 1, y + 5, w - 2, 5); c.fillStyle = 'rgba(6,10,12,0.3)'; c.fillRect(x + 2, y + 10, w - 4, 3);
    this.grassStrip(x - 2, x + w + 2, y - 5, Array(w + 4).fill(0).map(() => y + 3 + Math.floor(r() * 10)), 3);
    const roll = r();
    if (roll < 0.4) { const sw = 5 + Math.floor(r() * 7), sh = 14 + Math.floor(r() * 16), sx = x + 4 + Math.floor(r() * (w - sw - 8)); this.later.push(() => this.fall(sx, y + 1, sw, sh, 20.5, sx * 3 + y, { noMist: true, spread: 0.5 })); }
    else if (roll < 0.7) this.drawImg(r() < 0.5 ? 'crate' : 'ammo', x + 4, y - (r() < 0.5 ? 26 : 24) + 1);
  }
  scaffold(x, y, w, h, r) {
    const c = this.ctx, wood = '#6a4a2a', lite = '#9a7040', dark = '#2a1c10';
    const legH = Math.min(h, 60 + Math.floor(r() * 30));
    for (const px of [x, x + w - 4]) { c.fillStyle = OUTLINE; c.fillRect(px - 1, y - 1, 6, legH + 1); c.fillStyle = wood; c.fillRect(px, y, 4, legH); c.fillStyle = lite; c.fillRect(px, y, 1, legH); c.fillStyle = dark; c.fillRect(px + 3, y, 1, legH); }
    // cross brace
    for (let i = 0; i < w - 4; i++) { const t = i / (w - 4), yy = Math.round(y + 6 + t * Math.min(legH - 10, 28)); c.fillStyle = dark; c.fillRect(x + 2 + i, yy, 1, 3); c.fillStyle = wood; c.fillRect(x + 2 + i, yy, 1, 2); }
    // plank deck with bolts into the rock
    c.fillStyle = OUTLINE; c.fillRect(x - 3, y - 4, w + 6, 6);
    for (let i = -2; i < w + 2; i += 4) { c.fillStyle = r() < 0.5 ? '#8a6038' : '#7a5230'; c.fillRect(x + i, y - 3, 3, 3); c.fillStyle = '#b08850'; c.fillRect(x + i, y - 3, 3, 1); }
    c.fillStyle = '#c8c8b8'; c.fillRect(x + 1, y + 3, 1, 1); c.fillRect(x + w - 3, y + 3, 1, 1);
    // ladder dropping off one side, crate/drum on the deck, rope coil
    this.ladder(x + w + 3, y - 3, Math.min(h - 2, legH + 8));
    if (r() < 0.6) this.drawImg(r() < 0.5 ? 'crate' : 'drum', x + 3, y - (this.img('crate')?.height || 27) - 2);
  }
  // storm drain: iron grate in a concrete surround, dark mouth, moss and a rust stain, a thin trickle that runs
  // into a stone channel cut below it (deliberate, not an orphan pipe)
  pipe(x, y, r) {
    const c = this.ctx, w = 20 + Math.floor(r() * 8), h = 14;
    c.fillStyle = OUTLINE; c.fillRect(x - 3, y - 3, w + 6, h + 6);
    c.fillStyle = '#8a8c84'; c.fillRect(x - 2, y - 2, w + 4, 2); c.fillStyle = '#5e605a'; c.fillRect(x - 2, y, w + 4, h + 2);
    c.fillStyle = '#06090b'; c.fillRect(x, y + 1, w, h - 1);
    for (let i = 2; i < w; i += 4) { c.fillStyle = '#10161a'; c.fillRect(x + i - 1, y + 1, 3, h - 1); c.fillStyle = '#5c6a72'; c.fillRect(x + i, y + 1, 1, h - 1); }
    c.fillStyle = '#10161a'; c.fillRect(x, y + 6, w, 2); c.fillStyle = '#5c6a72'; c.fillRect(x, y + 6, w, 1);
    c.fillStyle = 'rgba(120,64,24,0.55)'; c.fillRect(x + w / 2 - 2, y + h + 2, 4, 10);
    this.grassStrip(x - 4, x + w + 4, y - 7, Array(w + 8).fill(0).map(() => y - 2 + Math.floor(r() * 7)), 4);
    // channel below
    const cy = y + h + 14, cw = w + 16;
    c.fillStyle = OUTLINE; c.fillRect(x - 9, cy - 1, cw + 2, 7); c.fillStyle = '#707268'; c.fillRect(x - 8, cy, cw, 1); c.fillStyle = '#1a3a58'; c.fillRect(x - 7, cy + 2, cw - 2, 3);
    c.fillStyle = '#6ab0d8'; for (let i = 0; i < cw - 2; i += 3) c.fillRect(x - 7 + i, cy + 2, 2, 1);
    const fx = x + Math.floor(w / 2) - 3;
    this.later.push(() => this.fall(fx, y + h, 6, cy - y - h + 3, 20.5, fx * 11, { noMist: true, spread: 0.4 }));
  }
  roots(x, y, n, r) {
    const c = this.ctx;
    for (let k = 0; k < 4; k++) {
      let rx = x + Math.floor(r() * n), ry = y, len = 14 + Math.floor(r() * 26);
      for (let i = 0; i < len; i++) { c.fillStyle = '#10161a'; c.fillRect(rx - 1, ry, 3, 1); c.fillStyle = i % 5 ? '#5a4028' : '#7a5838'; c.fillRect(rx, ry, 1, 1); ry++; if (r() < 0.3) rx += r() < 0.5 ? -1 : 1; }
    }
    this.drawCropH('vine' + (5 + Math.floor(r() * 5)), x + n / 2, y, 30 + r() * 30);
  }
  footing(cx, gy, H) {
    const c = this.ctx;
    // concrete pier at the base + two tarred timber pilings up to the ground line, with iron straps
    for (const px of [cx - 12, cx + 6]) {
      c.fillStyle = OUTLINE; c.fillRect(px - 1, gy, 8, H - gy); c.fillStyle = '#3e2c1a'; c.fillRect(px, gy, 6, H - gy);
      c.fillStyle = '#6a4a2a'; c.fillRect(px + 1, gy, 1, H - gy);
      for (let yy = gy + 10; yy < H; yy += 18) { c.fillStyle = '#10161a'; c.fillRect(px - 1, yy, 8, 2); c.fillStyle = '#6e7c86'; c.fillRect(px, yy, 6, 1); }
    }
    for (let yy = gy + 16; yy < H - 20; yy += 26) for (let i = 0; i < 12; i++) { c.fillStyle = '#2a1c10'; c.fillRect(cx - 6 + i, yy + i, 1, 2); c.fillRect(cx + 5 - i, yy + i, 1, 2); }
    const py = H - 26; c.fillStyle = OUTLINE; c.fillRect(cx - 18, py, 36, 26); c.fillStyle = '#6c706c'; c.fillRect(cx - 17, py + 1, 34, 25); c.fillStyle = '#8c908a'; c.fillRect(cx - 17, py + 1, 34, 2);
    c.fillStyle = '#4a4e4c'; c.fillRect(cx - 17, py + 14, 34, 1);
  }

  // ---------- ground
  groundBlock(s) {
    const H = this.level.height, L = this.neighbour(s, -1), R = this.neighbour(s, 1);
    const exL = !L || L.y > s.y, exR = !R || R.y > s.y;
    const pad = 6, x0 = s.x - (exL ? 0 : pad), x1 = s.x + s.w + (exR ? 0 : pad);
    const w = x1 - x0, h = H - s.y + 2;
    const wl = this.wobble(h, 3, s.x), wr = this.wobble(h, 3, s.x + 77);
    const spans = [];
    for (let i = 0; i < w; i++) spans.push([s.y, H + 2]);
    // carve exposed edges row by row (rounded top corner + rocky bulges)
    const carve = (fromLeft, bottom, wob) => {
      for (let r = 0; r < h; r++) {
        const y = s.y + r; if (y > bottom) break;
        let off = 1 + wob[r] + (r < 5 ? [4, 3, 2, 1, 1][r] : 0);
        for (let k = 0; k < off; k++) {
          const i = fromLeft ? k : w - 1 - k; if (i < 0 || i >= w) continue;
          if (spans[i][0] <= y) spans[i][0] = y + 1;
        }
      }
    };
    if (exL) carve(true, L ? L.y + 8 : H, wl);
    if (exR) carve(false, R ? R.y + 8 : H, wr);
    // generated cliff-face / base-foundation art, anchored to this block's top so its moss overhang sits under the lip
    const art = s.style === 'base' ? 'found' : (this.canv.faceMix ? 'faceMix' : 'face'), useArt = !!(this.canv[art] || this.img(art));
    const c = this.massCanvas(x0, s.y, w, h, spans, useArt ? art : 'cliff', useArt ? 0.2 : 0.62, useArt ? s.y + 3 : 0);
    this.ctx.drawImage(c, x0, s.y);
    if (!useArt) this.dressFace(s, x0, spans);
    if (s.style === 'base' && !useArt) { // poured concrete slab sitting on the rock
      const slab = spans.map(([t, b]) => [t, Math.min(b, s.y + 28)]);
      this.ctx.drawImage(this.massCanvas(x0, s.y, w, 30, slab, 'concrete', 0.3), x0, s.y);
    }
    s._ex = { exL, exR };
  }
  groundTop(s) {
    const c = this.ctx, { exL, exR } = s._ex;
    if (s.style === 'base') {
      // riveted steel deck edge on concrete
      // strong floor lip: dark line above, near-white rim, light plate, then a 6px shadow band over the foundation art
      c.fillStyle = OUTLINE; c.fillRect(s.x, s.y - 1, s.w, 1);
      c.fillStyle = '#ffffff'; c.fillRect(s.x, s.y, s.w, 1);
      c.fillStyle = '#b8bcb4'; c.fillRect(s.x, s.y + 1, s.w, 1);
      c.fillStyle = '#80847e'; c.fillRect(s.x, s.y + 2, s.w, 2);
      c.fillStyle = 'rgba(2,6,10,0.6)'; c.fillRect(s.x, s.y + 9, s.w, 3); c.fillStyle = 'rgba(2,6,10,0.35)'; c.fillRect(s.x, s.y + 12, s.w, 3);
      c.fillStyle = '#2a2f33'; c.fillRect(s.x, s.y + 4, s.w, 1);
      c.fillStyle = OUTLINE; c.fillRect(s.x, s.y + 5, s.w, 2); c.fillStyle = 'rgba(4,8,12,0.55)'; c.fillRect(s.x, s.y + 7, s.w, 2);
      c.fillStyle = '#c9cac2';
      for (let x = s.x + 4; x < s.x + s.w - 2; x += 12) c.fillRect(x, s.y + 2, 1, 1);
      // hazard stripes at exposed ends
      for (const [ex, xx] of [[exL, s.x], [exR, s.x + s.w - 24]]) if (ex) this.hazard(xx, s.y + 1, 24, 3);
      const r = rng(s.x);
      // grime: water streaks and rust runs down the slab face
      for (let x = s.x + 3; x < s.x + s.w - 3; x += 5 + Math.floor(r() * 16)) {
        const len = 5 + Math.floor(r() * 18), rust = r() < 0.3;
        c.fillStyle = rust ? 'rgba(120,70,30,0.35)' : 'rgba(14,22,18,0.35)';
        c.fillRect(x, s.y + 6, 1 + (r() < 0.3 ? 1 : 0), len);
      }
      // moss band where the slab meets the rock, dripping over the boulders
      for (let x = s.x + Math.floor(r() * 30); x < s.x + s.w - 20; x += 40 + Math.floor(r() * 70)) {
        const len = Math.min(s.x + s.w - x, 30 + Math.floor(r() * 60));
        this.grassStrip(x, x + len, s.y + 14, Array(len).fill(0).map(() => s.y + 30 + Math.floor(r() * 22)), 12);
      }
      // jungle reclaiming the concrete: grassy patches over the deck edge with vines spilling down the face
      for (let x = s.x + 10 + Math.floor(r() * 40); x < s.x + s.w - 30; x += 70 + Math.floor(r() * 110)) {
        const len = Math.min(s.x + s.w - x, 24 + Math.floor(r() * 50));
        this.grassStrip(x, x + len, s.y - 4, Array(len).fill(0).map((_, i) => s.y + 8 + Math.floor(r() * (i > 3 && i < len - 4 ? 22 : 8))));
        this.drawCropH('vine' + Math.floor(r() * 10), x + len / 2 - 6, s.y + 4, 24 + r() * 30);
      }
      if (exL) this.drawImg('cap-l', s.x - 5, s.y - 3);
      if (exR) this.drawImg('cap-r', s.x + s.w - 25, s.y - 3);
      // re-assert the walk lip on top of the reclaiming grass so the floor line never disappears
      c.fillStyle = '#ffffff'; c.fillRect(s.x, s.y, s.w, 1);
      c.fillStyle = '#b8bcb4'; c.fillRect(s.x, s.y + 1, s.w, 1);
      c.fillStyle = OUTLINE; c.fillRect(s.x, s.y + 2, s.w, 1);
      return;
    }
    this.grassStrip(s.x - (exL ? 2 : 0), s.x + s.w + (exR ? 2 : 0), s.y - 4);
    if (!this.img('face')) this.bulges(s.x + 2, s.x + s.w - 2, s.y + 4, s.x * 13 + 1);
    this.lip(s.x + (exL ? 2 : 0), s.x + s.w - (exR ? 2 : 0), s.y);
    // long vines trailing over open gap edges (they hang in front of the cascades)
    const r = rng(s.x + 5);
    if (exL && !this.neighbour(s, -1)) for (const dx of [-3, 5]) { const k = 'vine' + (5 + Math.floor(r() * 5)); this.drawCropH(k, s.x + dx, s.y + 2, 30 + r() * 30); }
    if (exR && !this.neighbour(s, 1)) for (const dx of [-12, -4]) { const k = 'vine' + (5 + Math.floor(r() * 5)); this.drawCropH(k, s.x + s.w + dx, s.y + 2, 30 + r() * 30); }
    if (exL) this.drawImg('cap-l', s.x - 5, s.y - 3);
    if (exR) this.drawImg('cap-r', s.x + s.w - 25, s.y - 3);
  }
  drawCropH(k, x, y, hmax) { const im = this.img(k); if (!im) return; const h = Math.min(im.height, Math.round(hmax)); this.ctx.drawImage(im, 0, im.height - h, im.width, h, Math.round(x), Math.round(y), im.width, h); }
  drawCrop(k, sx, sy, sw, sh, dx, dy) { const im = this.img(k); if (im) this.ctx.drawImage(im, sx, sy, sw, sh, Math.round(dx), Math.round(dy), sw, sh); }
  // grass/moss strip along a top edge; optional per-column max y (world) clips the moss drips
  grassStrip(x0, x1, y, maxY, skipTop = 0) {
    const im = this.img('grass'); if (!im) return;
    const w = x1 - x0, h = im.height, t = document.createElement('canvas'); t.width = w; t.height = h;
    const g = t.getContext('2d'); g.imageSmoothingEnabled = false;
    g.translate(-x0, 0); g.fillStyle = this.pattern('grass'); g.fillRect(x0, 0, w, h);
    if (maxY) {
      const id = g.getImageData(0, 0, w, h), d = id.data;
      for (let i = 0; i < w; i++) for (let r = Math.max(0, maxY[i] - y); r < h; r++) d[(r * w + i) * 4 + 3] = 0;
      for (let r = 0; r < Math.min(h, skipTop); r++) for (let i = 0; i < w; i++) d[(r * w + i) * 4 + 3] = 0;
      g.putImageData(id, 0, 0);
    }
    this.ctx.drawImage(t, x0, y);
  }
  // rounded mossy overhang lumps hanging from a top edge, varying 6-18px, lit top rim + shadowed underside
  bulges(x0, x1, y, seed) {
    const c = this.ctx, r = rng(seed);
    for (let x = x0 + 4 + Math.floor(r() * 16); x < x1 - 14; x += 10 + Math.floor(r() * 34)) {
      const w = 10 + Math.floor(r() * 26), d = 4 + Math.floor(r() * 15);
      for (let i = 0; i < w && x + i < x1 - 2; i++) {
        const t = (i + 0.5) / w, hh = Math.round(d * Math.sqrt(Math.max(0, 1 - Math.pow(2 * t - 1, 2))));
        if (hh <= 0) continue;
        c.fillStyle = '#10161a'; c.fillRect(x + i, y + 2, 1, hh + 2);
        for (let j = 0; j < hh; j++) {   // mottled leafy moss: lit near the top, shadowed toward the underside
          const q = j / hh, n = r();
          c.fillStyle = q < 0.3 ? (n < 0.5 ? '#5ea22e' : '#4c8a26') : q < 0.7 ? (n < 0.35 ? '#4c8a26' : n < 0.8 ? '#3a6e20' : '#2c5a1a') : (n < 0.6 ? '#2c5a1a' : '#1e4014');
          c.fillRect(x + i, y + 2 + j, 1, 1);
        }
        if (r() < 0.25) { c.fillStyle = '#8fd84a'; c.fillRect(x + i, y + 3 + Math.floor(r() * 3), 1, 1); }
        if (r() < 0.1 && hh > 6) { c.fillStyle = '#2e5a1c'; c.fillRect(x + i, y + 2 + hh, 1, 2 + Math.floor(r() * 4)); }
      }
    }
  }
  // the standing line: sunlit grass rim right where feet land, with a dark underline, so tops read instantly
  lip(x0, x1, y) {
    const c = this.ctx, r = rng(x0 + y);
    c.fillStyle = '#1d3a12'; c.fillRect(x0, y + 1, x1 - x0, 1);
    c.fillStyle = '#7fd23a'; c.fillRect(x0, y - 1, x1 - x0, 2);
    c.fillStyle = '#d6f76c';
    for (let x = x0; x < x1; x++) if (r() < 0.8) c.fillRect(x, y - 1, 1, 1);
    for (let x = x0 + 2; x < x1 - 2; x += 3 + Math.floor(r() * 5)) { const hgt = r() < 0.2 ? 3 + Math.floor(r() * 2) : 1 + Math.floor(r() * 2); c.fillStyle = '#2e5a1c'; c.fillRect(x + 1, y - 1 - hgt, 1, hgt); c.fillStyle = r() < 0.5 ? '#b4ee52' : '#7fd23a'; c.fillRect(x, y - 1 - hgt, 1, hgt + 1); }
  }
  hazard(x, y, w, h) {
    const c = this.ctx;
    c.fillStyle = '#1b1d1f'; c.fillRect(x, y, w, h);
    c.fillStyle = '#e0a526';
    for (let i = 0; i < w; i++) for (let j = 0; j < h; j++) if (((i + j) >> 2) % 2 === 0) c.fillRect(x + i, y + j, 1, 1);
  }

  // ---------- floating grassy ledge (one-way platform)
  ledge(p) {
    const w = p.w + 8, x0 = p.x - 4, D = 36 + Math.min(18, p.w / 6);
    const r = rng(p.x), spans = [];
    let v = 0;
    for (let i = 0; i < w; i++) {
      const t = (i + 0.5) / w; v += (r() - 0.5) * 3; v *= 0.7;
      const top = p.y + (i < 3 ? 3 - i : i >= w - 3 ? i - (w - 4) : 0);
      spans.push([top, p.y + Math.round(6 + (D - 6) * Math.pow(Math.sin(Math.PI * t), 0.55) + v)]);
    }
    const c = this.massCanvas(x0, p.y, w, D + 6, spans, this.canv.faceMix ? 'faceMix' : this.img('face') ? 'face' : 'cliff', this.img('face') ? 0.2 : 0.45, p.y + 3);
    this.ctx.drawImage(c, x0, p.y);
    this.grassStrip(x0, x0 + w, p.y - 4, spans.map(([, b]) => b + 3));
    this.bulges(x0 + 2, x0 + w - 2, p.y + 4, p.x * 17 + 5);
    this.lip(x0 + 3, x0 + w - 3, p.y);
    for (const [k, cx] of [['cap-l', x0 - 4], ['cap-r', x0 + w - 26]]) { const im = this.img(k); if (im) this.ctx.drawImage(im, 0, 0, im.width, 34, cx, p.y - 3, im.width, 34); }
    for (let k = 0; k < Math.floor(w / 36); k++) {
      const vi = 'vine' + Math.floor(r() * 10), im = this.img(vi); if (!im) continue;
      const i = 8 + Math.floor(r() * (w - 20));
      this.drawCropH(vi, x0 + i - im.width / 2, spans[Math.min(w - 1, i)][1] - 6, 22 + r() * 22);
    }
  }

  // the rock column a ledge is the top of: tapers and bulges down to the water/ground, darker than the lip,
  // moss and vines down its face, a fall pouring out of a crack when it stands in a basin
  pillar(p) {
    const H = this.level.height, r = rng(p.x * 3 + 1), ctx = this.midCtx;
    const overGorge = this.level.water.find(q => q._gorge && p.x + p.w / 2 > q.x && p.x + p.w / 2 < q.x + q.w);
    if (overGorge && this.img('spire')) {   // generated rock spire rising out of the pool under the ledge
      const im = this.img('spire'), cxs = p.x + Math.round(p.w * 0.28);   // off-centre: under the ledge's left end
      this.midCtx.drawImage(this.aerial(im, 0.34), Math.round(cxs - im.width / 2), Math.max(p.y + 2, H - im.height + 8));
      return;
    }
    const w = Math.round(p.w * (overGorge ? 0.42 : 0.78)), cx = p.x + p.w / 2, y0 = p.y + 8, h = H + 2 - y0;
    const x0 = Math.round(cx - w / 2 - 10), W = w + 20, spans = [];
    const wl = this.wobble(h, 4, p.x + 5), wr = this.wobble(h, 4, p.x + 91);
    for (let i = 0; i < W; i++) spans.push([H + 2, H + 2]);
    for (let row = 0; row < h; row++) {
      const t = row / h, half = w / 2 * (0.92 - 0.12 * Math.sin(t * Math.PI * 1.3)) ;
      const a = Math.round(cx - half - wl[row] - x0), b = Math.round(cx + half + wr[row] - x0);
      for (let i = Math.max(0, a); i < Math.min(W, b); i++) if (spans[i][0] > y0 + row) spans[i][0] = y0 + row;
    }
    const cv = this.massCanvas(x0, y0, W, h, spans, this.img('face') ? 'face' : 'cliff', 0.3, y0);
    const g = cv.getContext('2d'); g.globalCompositeOperation = 'source-atop';
    g.fillStyle = 'rgba(8,16,24,0.34)'; g.fillRect(0, 0, W, h);
    for (let yy = 0; yy < h; yy += 4) { g.fillStyle = `rgba(8,16,24,${(0.25 * yy / h).toFixed(2)})`; g.fillRect(0, yy, W, 4); }
    ctx.drawImage(cv, x0, y0);
    const save = this.ctx; this.ctx = ctx;
    // moss shelves and vines down the face
    for (let yy = y0 + 22 + Math.floor(r() * 10); yy < H - 30; yy += 26 + Math.floor(r() * 16)) {
      const i = Math.floor(r() * (W - 26)), sw = 14 + Math.floor(r() * 12);
      if (spans[i][0] <= yy && spans[Math.min(W - 1, i + sw)][0] <= yy) this.grassStrip(x0 + i, x0 + i + sw, yy - 3, Array(sw).fill(yy + 5 + Math.floor(r() * 5)));
    }
    for (let k = 0; k < Math.max(2, W / 26); k++) this.drawCropH('vine' + Math.floor(r() * 10), x0 + 4 + r() * (W - 16), y0 - 2, 20 + r() * 40);
    this.ctx = save;
    // a fall pouring out of a crack if the column stands in a basin
    const wa = this.level.water.find(q => cx > q.x && cx < q.x + q.w);
    if (wa && !wa._gorge) this.later.push(() => {
      const sc = this.scene, fx = Math.round(cx - 18 + (r() - 0.5) * w * 0.4), fy = y0 + 14;
      this.fall(fx + 6, fy, 10 + Math.floor(r() * 12), this.waterLine - fy + 4, 17.6, fx * 7 + 2);
    });
  }

  // ---------- bridges
  // hand-built rope bridge: uneven gappy planks on a shallow curve (<=2px, the sheep walks the flat physics line),
  // hand ropes and an under-rope hanging in deep catenaries with vertical ties, chunky lashed posts sunk into the rock
  ropeBridge(p) {
    const c = this.ctx, r = rng(p.x + 17), x0 = p.x - 2, x1 = p.x + p.w + 2, W = x1 - x0, y = p.y;
    const cat = (t, d) => Math.round(d * Math.sin(Math.PI * t));
    const deckY = x => y + cat((x - x0) / W, Math.min(2, W / 90));
    const handY = x => y - 21 + cat((x - x0) / W, Math.min(12, W / 18));
    const backY = x => y - 17 + cat((x - x0) / W, Math.min(11, W / 20));
    const underY = x => y + 5 + cat((x - x0) / W, Math.min(14, W / 16));
    const rope = (f, light, dark) => { for (let x = x0 + 3; x < x1 - 3; x++) { const yy = f(x); c.fillStyle = dark; c.fillRect(x, yy, 1, 2); c.fillStyle = light; if ((x & 3) !== 0) c.fillRect(x, yy, 1, 1); } };
    // back hand rope (behind the deck), under-rope + hangers
    rope(backY, '#5a4128', '#20160e');
    for (let x = x0 + 8; x < x1 - 8; x += 9) { const a = deckY(x) + 3, b = underY(x); if (b > a) { c.fillStyle = '#2c1f13'; c.fillRect(x, a, 1, b - a); } }
    rope(underY, '#6e5030', '#20160e');
    // planks: uneven widths, 1px gaps, jittered
    for (let x = x0 + 4; x < x1 - 4;) {
      const pw = 3 + Math.floor(r() * 3), yy = deckY(x) + (r() < 0.25 ? 1 : 0), shade = r();
      c.fillStyle = '#1a120c'; c.fillRect(x - 1, yy - 1, pw + 1, 6);
      c.fillStyle = shade < 0.3 ? '#6a4527' : shade < 0.7 ? '#7e5431' : '#8c6038'; c.fillRect(x, yy, pw - 1, 4);
      c.fillStyle = '#c0925a'; c.fillRect(x, yy, pw - 1, 1);
      c.fillStyle = '#4a3019'; c.fillRect(x, yy + 3, pw - 1, 1);
      if (r() < 0.12) this.drawCropH('vine' + Math.floor(r() * 4), x - 5, yy + 3, 8 + r() * 12);
      x += pw + (r() < 0.2 ? 2 : 1);
    }
    // deck stringer rope along the plank ends
    rope(x => deckY(x) + 4, '#7a5a36', '#20160e');
    // front hand rope + vertical ties down to the deck
    for (let x = x0 + 7; x < x1 - 7; x += 10) { const a = handY(x) + 1, b = deckY(x); c.fillStyle = '#1a120c'; c.fillRect(x - 1, a, 3, b - a); c.fillStyle = '#8a6a40'; c.fillRect(x, a, 1, b - a); }
    rope(handY, '#a07a48', '#20160e');
    // chunky posts sunk into the rock at both ends (rope lashing bands)
    for (const px of [p.x - 10, p.x + p.w + 2]) {
      const top = y - 28, bot = y + 14, PW = 8;
      c.fillStyle = '#1a120c'; c.fillRect(px - 1, top - 1, PW + 2, bot - top + 1);
      c.fillStyle = '#5a3a20'; c.fillRect(px, top, PW, bot - top);
      c.fillStyle = '#8a6038'; c.fillRect(px + 1, top, 3, bot - top);
      c.fillStyle = '#3a2614'; c.fillRect(px + PW - 2, top, 2, bot - top);
      for (let gy = top + 4; gy < bot; gy += 7) { c.fillStyle = '#4a2f18'; c.fillRect(px + 2 + (gy % 3), gy, 1, 3); }
      c.fillStyle = '#b08850'; c.fillRect(px, top, PW, 1);
      for (const ly of [y - 23, y - 20, y - 1, y + 2]) { c.fillStyle = '#d0a868'; c.fillRect(px - 1, ly, PW + 2, 1); c.fillStyle = '#6e5030'; c.fillRect(px - 1, ly + 1, PW + 2, 1); }
      // moss tuft on the post top and rock/grass burying its foot
      c.fillStyle = '#4c8a26'; c.fillRect(px, top - 1, 4, 2); c.fillStyle = '#86c83c'; c.fillRect(px + 1, top - 2, 2, 1);
      this.drawCrop('grass', (px * 7) % 200, 0, 12, 10, px - 3, y - 4);
    }
  }
  // draw an image stretched to `total` width by keeping its ends and repeating a middle slice [m0,m1)
  stretch(k, x0, y0, total, m0, m1) {
    const im = this.img(k); if (!im) return;
    const c = this.ctx, W = im.width;
    const left = Math.min(m0, Math.floor(total / 2)), right = Math.min(W - m1, total - left);
    c.drawImage(im, 0, 0, left, im.height, x0, y0, left, im.height);
    c.drawImage(im, W - right, 0, right, im.height, x0 + total - right, y0, right, im.height);
    for (let x = x0 + left; x < x0 + total - right; x += (m1 - m0)) {
      const sw = Math.min(m1 - m0, x0 + total - right - x);
      c.drawImage(im, m0, 0, sw, im.height, x, y0, sw, im.height);
    }
  }
  steelBridge(p) {
    const c = this.ctx, x0 = p.x - 6, w = p.w + 12, y = p.y;
    // piers down into the water at both ends
    for (const px of [p.x + 40, p.x + p.w - 62]) this.drawImg('tower2', px, y + 18);
    // deck: top chord from the generated girder art (rows 0..8), repeated
    this.stretch2('steelbridge-raw', 0, 9, x0, y - 1, w, 30, 66);
    c.fillStyle = '#10161a'; c.fillRect(x0 + 1, y - 2, w - 2, 1);
    c.fillStyle = '#f8faf2'; c.fillRect(x0 + 2, y - 1, w - 4, 1);
    c.fillStyle = '#06090c'; c.fillRect(x0 + 2, y + 7, w - 4, 2);
    c.fillStyle = '#9aa2a0'; c.fillRect(x0 + 2, y, w - 4, 1);
    // truss, lit from above: bright top edges on every member, mid face, dark underside + shadowed web
    const top = y + 8, bot = y + 24;
    c.fillStyle = 'rgba(4,10,16,0.45)'; c.fillRect(x0 + 3, top, w - 6, bot - top);           // shadowed interior under the deck
    c.fillStyle = OUTLINE; c.fillRect(x0 + 2, bot - 1, w - 4, 6);
    c.fillStyle = '#7c8a90'; c.fillRect(x0 + 3, bot, w - 6, 1);                               // lit top of bottom chord
    c.fillStyle = '#4a565c'; c.fillRect(x0 + 3, bot + 1, w - 6, 2);
    c.fillStyle = '#1c2428'; c.fillRect(x0 + 3, bot + 3, w - 6, 1);                           // dark underside
    const bay = 18;
    for (let bx = x0 + 3; bx < x0 + w - 4; bx += bay) {
      const e = Math.min(bx + bay, x0 + w - 4);
      for (let i = 0; i <= bot - top; i++) {
        const t = i / (bot - top), xa = Math.round(bx + 2 + t * (e - bx - 2)), xb = Math.round(e - t * (e - bx - 2)), lit = 1 - t * 0.6;
        c.fillStyle = OUTLINE; c.fillRect(xa - 1, top + i, 3, 1); c.fillRect(xb - 1, top + i, 3, 1);
        c.fillStyle = lit > 0.7 ? '#6c7a80' : lit > 0.5 ? '#526066' : '#3c484e'; c.fillRect(xa, top + i, 1, 1);
        c.fillStyle = lit > 0.7 ? '#58666c' : '#34404a'; c.fillRect(xb, top + i, 1, 1);
      }
      c.fillStyle = OUTLINE; c.fillRect(bx - 1, top, 4, bot - top);
      c.fillStyle = '#8c9a9e'; c.fillRect(bx, top, 1, bot - top);                                // lit edge of the post
      c.fillStyle = '#4a5357'; c.fillRect(bx + 1, top, 1, bot - top);
      c.fillStyle = '#c8d0cc'; c.fillRect(bx, top + 1, 1, 1); c.fillRect(bx, bot - 2, 1, 1);      // rivet glints
      // gusset plates at the joints
      c.fillStyle = OUTLINE; c.fillRect(bx - 2, bot - 4, 6, 4); c.fillStyle = '#6c7a80'; c.fillRect(bx - 1, bot - 4, 4, 1); c.fillStyle = '#3c484e'; c.fillRect(bx - 1, bot - 3, 4, 2);
    }
    // moss and grass where the bridge meets each cliff
    for (const ex of [x0 - 2, x0 + w - 26]) this.grassStrip(ex, ex + 28, y - 4, Array(28).fill(0).map((_, i) => y + 10 + Math.floor(Math.sin(i * 0.5) * 3 + 6)));
    // a few moss strands hanging off the truss
    const r = rng(p.x);
    for (let k = 0; k < w / 55; k++) { const v = 'vine' + Math.floor(r() * 4), im = this.img(v); if (im) this.ctx.drawImage(im, 0, 0, im.width, Math.min(im.height, 26), x0 + 10 + r() * (w - 30), bot - 2, im.width, Math.min(im.height, 26)); }
  }
  // stretch a horizontal band (rows sy..sy+sh) of an image
  stretch2(k, sy, sh, x0, y0, total, m0, m1) {
    const im = this.img(k); if (!im) return;
    const c = this.ctx, W = im.width, left = m0, right = 15;
    c.drawImage(im, 0, sy, left, sh, x0, y0, left, sh);
    c.drawImage(im, W - right, sy, right, sh, x0 + total - right, y0, right, sh);
    for (let x = x0 + left; x < x0 + total - right; x += (m1 - m0)) {
      const sw = Math.min(m1 - m0, x0 + total - right - x);
      c.drawImage(im, m0, sy, sw, sh, x, y0, sw, sh);
    }
  }
  catwalkSupports(p) {
    const c = this.ctx;
    // foot plates where legs meet ground, and a knee brace from each leg up under the deck
    for (const lx of [p.x + 6, p.x + p.w - 22]) {
      const gy = Math.min(this.groundYAt(lx + 7), this.groundYAt(lx), this.level.height + 2);
      if (gy < this.level.height) { c.fillStyle = OUTLINE; c.fillRect(lx - 3, gy - 4, 20, 4); c.fillStyle = '#6e7c86'; c.fillRect(lx - 2, gy - 4, 18, 1); }
      const dir = lx < p.x + p.w / 2 ? 1 : -1;
      for (let i = 0; i < 18; i++) { const bx = lx + 7 + dir * (6 + i), by = p.y + 30 - i; c.fillStyle = OUTLINE; c.fillRect(bx, by - 1, 1, 4); c.fillStyle = '#4c5a66'; c.fillRect(bx, by, 1, 2); }
    }
    for (const lx of [p.x + 6, p.x + p.w - 22]) {
      const gy = Math.min(this.groundYAt(lx + 7), this.groundYAt(lx), this.level.height + 2);
      this.lattice(lx, p.y + 8, 14, gy - p.y - 8);
    }
  }
  lattice(x, y, w, h) {
    const c = this.ctx;
    c.fillStyle = OUTLINE; c.fillRect(x - 1, y, 5, h); c.fillRect(x + w - 4, y, 5, h);
    c.fillStyle = '#4c5a66'; c.fillRect(x, y, 2, h); c.fillRect(x + w - 3, y, 2, h);
    c.fillStyle = '#6e7c86'; c.fillRect(x, y, 1, h); c.fillRect(x + w - 3, y, 1, h);
    for (let yy = y; yy < y + h - 2; yy += w) {
      for (let i = 0; i < w; i++) {
        const a = Math.min(y + h - 1, yy + i), b = Math.min(y + h - 1, yy + w - 1 - i);
        c.fillStyle = OUTLINE; c.fillRect(x + i, a, 1, 2); c.fillRect(x + i, b, 1, 2);
        c.fillStyle = '#3a4854'; c.fillRect(x + i, a, 1, 1); c.fillRect(x + i, b, 1, 1);
      }
      c.fillStyle = OUTLINE; c.fillRect(x, yy, w, 2); c.fillStyle = '#34414c'; c.fillRect(x + 1, yy, w - 2, 1);
    }
  }
  // solid walkway: bright highlight lip, light plate, hazard band, thick dark body, outlined - no thin railings
  catwalk(p) {
    const c = this.ctx, x = p.x, w = p.w, y = p.y;
    c.fillStyle = OUTLINE; c.fillRect(x - 2, y - 2, w + 4, 16);
    c.fillStyle = '#fbfdf6'; c.fillRect(x - 1, y - 1, w + 2, 1);
    c.fillStyle = '#b4bab6'; c.fillRect(x - 1, y, w + 2, 2);
    c.fillStyle = '#7c8482'; c.fillRect(x - 1, y + 2, w + 2, 1);
    this.hazard(x - 1, y + 3, w + 2, 5);
    c.fillStyle = '#262e34'; c.fillRect(x - 1, y + 8, w + 2, 5);
    c.fillStyle = '#06090c'; c.fillRect(x - 2, y + 14, w + 4, 2);
    c.fillStyle = '#3c464c'; c.fillRect(x - 1, y + 8, w + 2, 1);
    for (let px = x + 4; px < x + w - 2; px += 12) { c.fillStyle = '#8a9290'; c.fillRect(px, y + 10, 1, 1); c.fillStyle = '#10161a'; c.fillRect(px, y + 11, 1, 1); }
    // end caps
    for (const ex of [x - 2, x + w - 2]) { c.fillStyle = OUTLINE; c.fillRect(ex, y - 2, 4, 16); c.fillStyle = '#4a5358'; c.fillRect(ex + 1, y + 3, 2, 9); }
  }

  // ---------- props & scatter
  // weather a concrete structure: stains/rust runs, cracks, moss creeping over its top edge, hanging vines,
  // and a cast shadow on the ground/under its overhang
  weather(x, y, w, h, seed) {
    const c = this.ctx, r = rng(seed);
    for (let i = 2; i < w - 2; i += 2 + Math.floor(r() * 6)) {
      const len = 6 + Math.floor(r() * h * 0.5), rust = r() < 0.3;
      c.fillStyle = rust ? 'rgba(110,58,22,0.45)' : 'rgba(8,16,12,0.4)'; c.fillRect(x + i, y + 4 + Math.floor(r() * 10), 1 + (r() < 0.3 ? 1 : 0), len);
    }
    for (let k = 0; k < Math.max(2, w / 40); k++) {   // cracks: short jagged dark lines with a light edge
      let cx = x + 6 + Math.floor(r() * (w - 12)), cy = y + 8 + Math.floor(r() * (h - 16));
      for (let i = 0; i < 8 + Math.floor(r() * 10); i++) { c.fillStyle = '#0c1014'; c.fillRect(cx, cy, 1, 1); c.fillStyle = 'rgba(200,200,190,0.3)'; c.fillRect(cx + 1, cy, 1, 1); cy++; cx += Math.floor(r() * 3) - 1; }
    }
    // moss creeping down from the top edge, thicker in clumps
    this.grassStrip(x - 2, x + w + 2, y - 5, Array(w + 4).fill(0).map((_, i) => y + 2 + Math.floor((Math.sin(i * 0.13 + seed) + 1) * 5 + r() * 6)));
    for (let k = 0; k < Math.max(2, w / 34); k++) this.drawCropH('vine' + Math.floor(r() * 10), x + 4 + r() * (w - 16), y - 2, 16 + r() * (h * 0.6));
    // cast shadow onto the ground in front (stepped), and under the roof overhang
    c.fillStyle = 'rgba(4,10,16,0.35)'; c.fillRect(x + 3, y + h, w, 3); c.fillStyle = 'rgba(4,10,16,0.2)'; c.fillRect(x + 6, y + h + 3, w - 3, 2);
    c.fillStyle = 'rgba(4,10,16,0.35)'; c.fillRect(x + 2, y + 10, w - 4, 3);
  }
  prop(d) {
    this.dim = d.layer === 'far' ? 0.56 : d.layer === 'back' && d.x >= 3600 ? (/^(bunker|bigdoor)/.test(d.k) ? 0.12 : 0.46) : 0;
    try { this.prop2(d); } finally { this.dim = 0; }
    if (/^(bunker|bunker2|bigdoor|door-eagle)$/.test(d.k)) {
      const im = this.img(d.k), gy = d.y ?? this.groundYAt(d.x + im.width / 2), top = d.top !== undefined ? d.top : gy - im.height + (d.sink ?? 1);
      this.weather(d.x + 2, top + 2, im.width - 4, Math.min(im.height, gy - top) - 4, d.x);
    }
  }
  prop2(d) {
    const k = d.k, im = this.img(k);
    if (k === 'ladder') return this.ladder(d.x, d.y, d.h ?? (this.groundYAt(d.x + 7) - d.y));
    if (k === 'dam') return this.dam(d);
    if (k === 'searchlight') {
      const c = this.ctx, gy = d.y ?? this.groundYAt(d.x + 2), top = gy - (d.h || 70), x = d.x;
      c.fillStyle = OUTLINE; c.fillRect(x - 1, top, 6, gy - top); c.fillStyle = '#3e4a54'; c.fillRect(x, top, 4, gy - top); c.fillStyle = '#6a7882'; c.fillRect(x, top, 1, gy - top);
      for (let yy = top + 8; yy < gy; yy += 10) { c.fillStyle = '#10161a'; c.fillRect(x - 3, yy, 10, 1); }
      c.fillStyle = OUTLINE; c.fillRect(x - 6, gy - 3, 16, 3);
      // lamp housing
      c.fillStyle = OUTLINE; c.fillRect(x - 6, top - 9, 16, 11); c.fillStyle = '#4c5a64'; c.fillRect(x - 5, top - 8, 14, 9); c.fillStyle = '#fff4c8'; c.fillRect(x + 7, top - 7, 2, 7);
      // hard-stepped light cone sweeping up-right (3 bands of decreasing alpha, no blur)
      this.later.push(() => {
        const sc = this.scene, g = sc.add.graphics().setDepth(17.2).setBlendMode(Phaser.BlendModes.ADD);
        const drawCone = (a) => { g.clear(); for (const [len, al] of [[90, 0.10], [60, 0.10], [30, 0.12]]) { g.fillStyle(0xfff0b0, al);
          g.fillTriangle(x + 9, top - 4, x + 9 + Math.cos(a - 0.14) * len, top - 4 + Math.sin(a - 0.14) * len, x + 9 + Math.cos(a + 0.14) * len, top - 4 + Math.sin(a + 0.14) * len); } };
        g.__x0 = x - 10; g.__x1 = x + 110; let t = (x % 1000), acc = 99;
        const tick = dt => { t += dt; acc += dt; if (acc >= 50) { acc = 0; drawCone(-0.9 + Math.sin(t / 1800) * 0.5); } }; tick.x0 = g.__x0; tick.x1 = g.__x1; this.anim.push(tick); tick(0);
      });
      return;
    }
    if (k === 'lamppool') { // warm light pool on wall + ground under a lamp: stepped ellipses, additive
      this.later.push(() => {
        const sc = this.scene, g = sc.add.graphics().setDepth(20.2).setBlendMode(Phaser.BlendModes.ADD);
        for (const [rx, ry, al] of [[d.r || 34, (d.r || 34) * 0.55, 0.07], [(d.r || 34) * 0.66, (d.r || 34) * 0.36, 0.08], [(d.r || 34) * 0.33, (d.r || 34) * 0.18, 0.1]]) { g.fillStyle(0xffb050, al); g.fillEllipse(d.x, d.y, rx * 2, ry * 2); }
        g.__x0 = d.x - (d.r || 34) - 4; g.__x1 = d.x + (d.r || 34) + 4;
        let t = d.x; const tick = dt => { t += dt; g.alpha = 0.85 + Math.sin(t / 300) * 0.08 + (Math.random() < 0.02 ? -0.3 : 0); }; tick.x0 = g.__x0; tick.x1 = g.__x1; this.anim.push(tick);
      });
      return;
    }
    if (k === 'gantry') {
      const gy = d.y, top = d.top, c = this.ctx;
      this.lattice(d.x, top, 14, gy - top); this.lattice(d.x + d.w - 14, top, 14, gy - top);
      // solid I-beam posts carrying the beam down to the deck, with base plates
      for (const px of [d.x - 4, d.x + d.w - 2]) {
        c.fillStyle = OUTLINE; c.fillRect(px - 1, top, 8, gy - top); c.fillStyle = '#3e4a54'; c.fillRect(px, top, 6, gy - top);
        c.fillStyle = '#5e6c76'; c.fillRect(px, top, 1, gy - top); c.fillStyle = '#26303a'; c.fillRect(px + 2, top, 2, gy - top);
        c.fillStyle = OUTLINE; c.fillRect(px - 3, gy - 3, 12, 3); c.fillStyle = '#5e6c76'; c.fillRect(px - 2, gy - 3, 10, 1);
      }
      c.fillStyle = OUTLINE; c.fillRect(d.x - 3, top - 2, d.w + 6, 12);
      c.fillStyle = '#56626c'; c.fillRect(d.x - 2, top - 1, d.w + 4, 2);
      this.hazard(d.x - 2, top + 2, d.w + 4, 4);
      c.fillStyle = '#26303a'; c.fillRect(d.x - 2, top + 6, d.w + 4, 3);
      // hanging hook + chain in the middle, lamps under the beam
      const hx = d.x + Math.round(d.w / 2); c.fillStyle = '#10161a'; c.fillRect(hx, top + 9, 1, 20); c.fillRect(hx - 2, top + 28, 5, 3);
      for (const lx of [d.x + 20, d.x + d.w - 24]) { c.fillStyle = '#10161a'; c.fillRect(lx - 1, top + 9, 5, 4); this.later.push(() => {
        const L = this.scene.add.rectangle(lx, top + 10, 3, 2, 0xffd070).setOrigin(0, 0).setDepth(17.3); this.scene.tweens.add({ targets: L, alpha: 0.45, duration: 700, yoyo: true, repeat: -1, delay: lx % 500 }); }); }
      if (this.dim) { c.fillStyle = `rgba(12,22,34,${this.dim})`; c.fillRect(d.x - 3, top - 2, d.w + 6, gy - top + 2); }
      return;
    }
    if (k === 'wall') return this.wall(d.x, d.w, d.h, d.y ?? this.groundYAt(d.x + 2));
    if (k === 'lattice') return this.lattice(d.x, d.y, d.w || 14, d.h);
    if (k === 'fence') { // run of chain-link panels
      const n = d.n || 1, fw = 56;
      for (let i = 0; i < n; i++) { const fk = ((d.sign ?? 0) === i ? 'fence' : 'fence-plain') + (this.img('fence-solid') ? '-solid' : ''); this.drawImg(this.img(fk) ? fk : 'fence', d.x + i * fw, (d.y ?? this.groundYAt(d.x + 2)) - (this.img('fence')?.height || 57) + 2 + (d.dy || 0)); }
      return;
    }
    if (!im) return;
    const gy = d.y ?? this.groundYAt(d.x + im.width / 2);
    const y = d.top !== undefined ? d.top : gy - im.height + (d.sink ?? 1);
    this.drawImg(k, d.x, y, !!d.flip);
  }
  // compound wall: poured concrete panels with a capping beam, grime toward the base, moss over the top
  // far-bank dam: detailed concrete face (seams, rivets, pipes, grime, moss), sluice outlets pouring water,
  // a parapet with a rim-lit coping (reads as a wall top, not a floor) and blinking warning lights
  dam(d) {
    const c = this.ctx, x = d.x, w = d.w, top = d.top, gy = d.y, h = gy - top, r = rng(x + 9);
    const spans = []; for (let i = 0; i < w; i++) spans.push([top, gy + 2]);
    const cv = this.massCanvas(x, top, w, h + 2, spans, 'concrete', 0.25);
    const g = cv.getContext('2d'); g.globalCompositeOperation = 'source-atop';
    // cool shadow, darker toward the water
    for (let y = 0; y < h; y += 4) { g.fillStyle = `rgba(14,24,36,${(0.2 + 0.28 * y / h).toFixed(2)})`; g.fillRect(0, y, w, 4); }
    // panel seams + rivets
    for (let px = 22; px < w; px += 36) { g.fillStyle = 'rgba(8,12,16,0.7)'; g.fillRect(px, 6, 1, h); g.fillStyle = 'rgba(200,200,190,0.25)'; g.fillRect(px + 1, 6, 1, h); }
    for (const sy of [30, 58]) if (sy < h) { g.fillStyle = 'rgba(8,12,16,0.7)'; g.fillRect(0, sy, w, 1); g.fillStyle = 'rgba(200,200,190,0.22)'; g.fillRect(0, sy + 1, w, 1); }
    g.fillStyle = 'rgba(210,210,200,0.55)';
    for (let px = 26; px < w; px += 36) for (const sy of [10, 34, 62]) if (sy < h) { g.fillRect(px, sy, 1, 1); g.fillRect(px + 8, sy, 1, 1); }
    // grime and rust streaks
    for (let px = 2; px < w; px += 3 + Math.floor(r() * 9)) { g.fillStyle = r() < 0.3 ? 'rgba(110,60,24,0.35)' : 'rgba(10,18,14,0.35)'; g.fillRect(px, 7 + Math.floor(r() * 20), 1, 6 + Math.floor(r() * 26)); }
    this.ctx.drawImage(cv, x, top);
    // horizontal pipe with brackets, and a downpipe
    const py = top + 22;
    c.fillStyle = '#10161a'; c.fillRect(x, py - 1, w, 5);
    c.fillStyle = '#3c464b'; c.fillRect(x, py, w, 3); c.fillStyle = '#6d797c'; c.fillRect(x, py, w, 1);
    for (let bx = x + 10; bx < x + w; bx += 30) { c.fillStyle = '#10161a'; c.fillRect(bx, py - 2, 3, 7); c.fillStyle = '#56615f'; c.fillRect(bx + 1, py - 1, 1, 5); }
    const dx = x + w - 30; c.fillStyle = '#10161a'; c.fillRect(dx - 1, py, 5, h - 22); c.fillStyle = '#3c464b'; c.fillRect(dx, py, 3, h - 22); c.fillStyle = '#6d797c'; c.fillRect(dx, py, 1, h - 22);
    // sluice outlets (water pours from them)
    const outs = [x + Math.round(w * 0.22), x + Math.round(w * 0.58)];
    for (const ox of outs) {
      const oy = top + 36;
      c.fillStyle = '#10161a'; c.fillRect(ox - 1, oy - 1, 22, 12); c.fillStyle = '#05080a'; c.fillRect(ox, oy, 20, 10);
      c.fillStyle = '#7d8583'; c.fillRect(ox - 1, oy - 2, 22, 1);
      for (let k = 0; k < 5; k++) { c.fillStyle = '#2e3538'; c.fillRect(ox + 2 + k * 4, oy, 1, 10); }
      this.later.push(() => { const sc = this.scene; if (!sc.textures.exists('tr-fall-curtain')) return;
        const sp = sc.add.sprite(ox - 8, oy + 8, 'tr-fall-curtain', 0).setOrigin(0, 0).setDepth(17.4); sp.play({ key: 'tr-fall-curtain', startFrame: ox % 12 }); });
    }
    // moss drips over the coping
    const save = c;
    this.grassStrip(x - 2, x + w + 2, top - 1, Array(w + 4).fill(0).map(() => top + 4 + Math.floor(r() * 14)), 6);
    // rim-lit coping and parapet railing
    c.fillStyle = '#10161a'; c.fillRect(x - 3, top - 4, w + 6, 5);
    c.fillStyle = '#56606c'; c.fillRect(x - 2, top - 4, w + 4, 1);
    c.fillStyle = '#3a4450'; c.fillRect(x - 2, top - 3, w + 4, 2);

    // warning lights along the coping + two wall lamps
    for (const lx of [x + 4, x + w - 7, x + Math.round(w / 2)]) {
      c.fillStyle = '#10161a'; c.fillRect(lx - 1, top - 21, 5, 5);
      this.later.push(() => { const sc = this.scene; const L = sc.add.rectangle(lx, top - 20, 3, 3, 0xff4a2a).setOrigin(0, 0).setDepth(17.3);
        sc.tweens.add({ targets: L, alpha: 0.15, duration: 420, yoyo: true, repeat: -1, delay: (lx * 37) % 700 }); });
    }
    this.drawImg('lamp2', x + 60, top + 4); this.drawImg('lamp2', x + w - 70, top + 4);
    for (const lx of [x + 66, x + w - 64]) this.later.push(() => { const sc = this.scene; const glow = sc.add.rectangle(lx - 1, top + 12, 3, 2, 0xffd070).setOrigin(0, 0).setDepth(17.3);
      sc.tweens.add({ targets: glow, alpha: 0.5, duration: 900, yoyo: true, repeat: -1 }); });
  }
  wall(x, w, h, gy) {
    const y = gy - h, spans = [];
    for (let i = 0; i < w; i++) spans.push([y, gy + 2]);
    const cv = this.massCanvas(x, y, w, h + 2, spans, 'concrete', 0.1);
    const g = cv.getContext('2d');
    g.globalCompositeOperation = 'source-atop';
    for (let r = 0; r < h; r += 3) { g.fillStyle = `rgba(10,16,20,${(0.18 + 0.3 * r / h).toFixed(2)})`; g.fillRect(0, r, w, 3); }
    this.ctx.drawImage(cv, x, y);
    const c = this.ctx;
    c.fillStyle = OUTLINE; c.fillRect(x - 2, y - 5, w + 4, 6);
    c.fillStyle = '#8f908a'; c.fillRect(x - 1, y - 4, w + 2, 2);
    c.fillStyle = '#62645f'; c.fillRect(x - 1, y - 2, w + 2, 2);
    this.hazard(x + 1, gy - 9, w - 2, 5);
    if (this.dim) { c.fillStyle = `rgba(12,22,34,${this.dim})`; c.fillRect(x - 2, y - 5, w + 4, h + 6); }
    // sparse vines only (no grass on top, so the wall never reads as a walkable surface)
    const r = rng(x);
    for (let vx = x + 6 + r() * 20; vx < x + w - 12; vx += 22 + r() * 40) this.drawCropH('vine' + Math.floor(r() * 10), vx, y - 3, 10 + r() * 26);
  }
  ladder(x, y, h) {
    const c = this.ctx;
    c.fillStyle = OUTLINE; c.fillRect(x, y, 3, h); c.fillRect(x + 11, y, 3, h);
    c.fillStyle = '#6a7272'; c.fillRect(x + 1, y, 1, h); c.fillRect(x + 12, y, 1, h);
    for (let yy = y + 3; yy < y + h; yy += 6) { c.fillStyle = OUTLINE; c.fillRect(x + 2, yy - 1, 10, 3); c.fillStyle = '#7d8686'; c.fillRect(x + 3, yy, 8, 1); }
  }
  scatter(level) {
    const r = rng(99), occupied = [];
    for (const d of (level.decor || [])) if (!d.layer) occupied.push([d.x - 6, d.x + (this.img(d.k)?.width || 20) + 6]);
    for (const s of level.ground) {
      if (s.style === 'base') continue;
      for (let x = s.x + 10 + r() * 30; x < s.x + s.w - 34; x += 26 + r() * 60) {
        const k = 'bush' + Math.floor(r() * 12), im = this.img(k); if (!im) continue;
        if (occupied.some(([a, b]) => x + im.width > a && x < b)) continue;
        // walk-line tufts stay low (<=9px) so they never read as covering actors' legs; flip via canvas
        { const hh = Math.min(im.height, 9), c = this.ctx, fl = r() < 0.5; c.save(); if (fl) { c.translate(Math.round(x) * 2 + im.width, 0); c.scale(-1, 1); }
          c.drawImage(im, 0, im.height - hh, im.width, hh, Math.round(x), s.y - hh + 2, im.width, hh); c.restore(); }
      }
    }
  }

  // ---------- water basin set piece: falls off both lips and every shelf, curtains from behind the bridge,
  // a churning basin reaching the bottom of the screen, big wet boulders and spray
  water(wa) {
    const sc = this.scene, x = wa.x, w = wa.w, H = this.level.height, WL = this.waterLine, r = rng(x + 11);
    if (wa._gorge) {
      const fw = sc.textures.get(wa._gorge).get(0).width, fh = sc.textures.get(wa._gorge).get(0).height;
      const sp = sc.add.sprite(Math.round(x + w / 2 - fw / 2), H - fh, wa._gorge, 0).setOrigin(0, 0).setDepth(16.8);
      if (sc.anims.exists(wa._gorge)) sp.play({ key: wa._gorge, startFrame: x % 4 });
      return;
    }
    const sprite = (key, sx, sy, depth, flip = false) => {
      if (!sc.textures.exists(key)) return null;
      const sp = sc.add.sprite(Math.round(sx), Math.round(sy), key, 0).setOrigin(0, 0).setDepth(depth).setFlipX(flip);
      if (sc.anims.exists(key)) sp.play({ key, startFrame: Math.floor(r() * 8) });
      return sp;
    };
    const gl = this.groundYAt(x - 2), gr = this.groundYAt(x + w + 1);
    const deck = Math.min(gl, gr) + 2;
    const falls = [];
    // tall falls off both cliff lips
    if (gl < 300) { const fw = 18 + Math.floor(r() * 16); this.fall(x - 4, gl + 1, fw, WL - gl + 2, 18, x + 1); }
    if (gr < 300) { const fw = 14 + Math.floor(r() * 18); this.fall(x + w - fw - 2, gr + 1, fw, WL - gr + 2, 18, x + w + 3); }
    // one wide two-tier cascade pouring from behind the bridge deck into the basin, foam where it lands
    if (!wa.noCascade) {
      const tiered = sc.textures.exists('tr-tiers'), cw = tiered ? 150 : 128, cx = x + Math.round(w / 2 - cw / 2 + (r() - 0.5) * 20);
      if (tiered) sprite('tr-tiers', cx, Math.max(deck - 4, WL + 8 - 98), 17.5); else sprite('tr-cascade', cx, deck, 17.5);
      this.mistBand(cx + 75, WL - 2, 140, cx);
      falls.push(cx + 34, cx + 112);
    }
    // small spills off each shelf
    (wa._shelves || []).forEach((sh, i) => { if (i % 2 === 1 || r() < 0.25) this.fall(sh.x + 6 + Math.floor(r() * 10), sh.y - 2, 7 + Math.floor(r() * 10), WL - sh.y + 4, 17.6, sh.x * 3 + i); });
    // big wet boulders sunk into the basin: drawn BEHIND the water so only their tops break the surface
    const big = ['rock0', 'rock1', 'rock2', 'rock3', 'rock8', 'rock9'];
    const n = 2 + Math.floor(r() * 3), rocks = [];
    let cursor = x + 4 + r() * 30;
    for (let i = 0; i < n && cursor < x + w - 30; i++) {
      const k = big[Math.floor(r() * big.length)], im = this.img(k); if (!im) continue;
      let bx = cursor; cursor += im.width * (r() < 0.4 ? 0.6 : 1.4 + r() * 1.8);   // sometimes a tight cluster, sometimes a wide gap
      if (falls.some(f => Math.abs(bx + im.width / 2 - f) < 14)) bx += 22;
      const stick = 28 + Math.floor(r() * 12);                 // px above the water line
      sc.add.image(Math.round(bx), WL - stick, 'tr-' + k).setOrigin(0, 0).setDepth(18.9);
      rocks.push([Math.round(bx + im.width / 2), im.width]);
    }
    // churning basin: broken foam edge, light ripple bands, stepping to dark teal at the bottom (animated tile)
    if (sc.textures.exists('tr-basin')) {
      const top = WL - 6;
      const p = sc.add.tileSprite(x - 8, top, w + 16, H - top, 'tr-basin', 0).setOrigin(0, 0).setDepth(19);
      p.tilePositionX = x % 128; let t = 0, fr = 0;
      const tick = dt => { t += dt; const f = Math.floor(t / 125) % 8; if (f !== fr) { fr = f; p.setFrame(f); } p.tilePositionX = (x % 128) + Math.round(t / 110); p.tilePositionY = Math.round(Math.sin(t / 600)); };
      tick.x0 = x - 8; tick.x1 = x + w + 8; this.anim.push(tick);
    }
    // foam rings where the water wraps each rock
    for (const [cx, rw] of rocks) {
      sprite('tr-foamring', cx - 24, WL - 8, 19.3);
    }
    // spray + stepped mist puffs where the falls land
    for (const fx of falls) {
      const dy = Math.floor(r() * 5) - 2;

      if (r() < 0.5) sprite('tr-mist', fx - 22 + Math.floor((r() - 0.5) * 12), WL - 24 - Math.floor(r() * 8), 19.8);
    }
    // churn patches boiling across the basin surface and just under it, plus small rocks breaking the surface
    const nch = Math.round(w / 34);
    for (let i = 0; i < nch; i++) {
      const cx = x + 6 + r() * (w - 36), cy = WL - 4 + Math.floor(Math.pow(r(), 1.6) * 22);
      sprite('tr-churn', cx, cy, 19.25);
    }
    const small = ['rock10', 'rock7', 'rock11', 'rock5', 'rock4'];
    for (let i = 0; i < Math.round(w / 90); i++) {
      const k = small[Math.floor(r() * small.length)], im = this.img(k); if (!im) continue;
      const rx = Math.round(x + 10 + r() * (w - 20 - im.width)), ry = WL + 6 + Math.floor(r() * 12);
      sc.add.image(rx, ry - im.height + 6, 'tr-' + k).setOrigin(0, 0).setDepth(19.35);
      sprite('tr-churn', rx + im.width / 2 - 12, ry - 5, 19.4);
    }
  }

  // ---------- foreground jungle leaves framing the bottom of the screen
  foreground(level) {
    const sc = this.scene, SF = 1.35, W = sc.scale.width, H = level.height;
    const span = (level.width - W) * SF + W;
    const r = rng(7), keys = ['fg-leaves-l', 'fg-leaves-r', 'fg-leaves-l2', 'fg-leaves-r2'];
    let i = 0;
    // dark fronds anchored in both bottom corners of the screen, swaying a pixel or two
    if (this.img('fg-leaves-l') && this.img('fg-leaves-r')) {
      const L = sc.add.image(-22, H - 92, 'tr-fg-leaves-l').setOrigin(0, 0).setScrollFactor(0).setDepth(91).setTint(0x8a9a94);
      const R = sc.add.image(W - this.img('fg-leaves-r').width + 24, H - 84, 'tr-fg-leaves-r').setOrigin(0, 0).setScrollFactor(0).setDepth(91).setTint(0x8a9a94);
      let t = 0; const lx = L.x, rx = R.x;
      this.anim.push(dt => { t += dt; L.x = lx + Math.round(Math.sin(t / 900)); R.x = rx + Math.round(Math.sin(t / 1100 + 1)); });
    }
    for (let x = 200; x < span + 100; x += 330 + r() * 260, i++) {
      const k = keys[i % 4]; if (!this.img(k)) continue;
      const im = this.img(k), show = 30 + Math.floor(r() * 22);
      // with scrollFactor SF, screen x = worldX - scrollX*SF; place in that space
      sc.add.image(Math.round(x), H - show, 'tr-' + k).setOrigin(0, 0).setScrollFactor(SF, 1).setDepth(90).setFlipX(r() < 0.3);
    }
  }

  // dark rock masses anchored in the two bottom screen corners, behind the corner fronds (never near the walk line)
  lowerForeground(level) {
    const sc = this.scene, W = sc.scale.width, H = level.height;
    const put = (k, x, y, flip) => { const im = this.img(k); if (!im) return; sc.add.image(x, y, 'tr-' + k).setOrigin(0, 0).setScrollFactor(0).setDepth(90.5).setTint(0x4a5a58).setFlipX(flip); };
    put('rock0', -14, H - 34, false); put('rock8', 22, H - 22, true);
    put('rock1', W - 44, H - 30, true); put('rock9', W - 80, H - 20, false);
  }
  baseForeground(level) {
    const sc = this.scene, SF = 1.35, H = level.height, r = rng(71);
    const rocks = ['rock0', 'rock1', 'rock2', 'rock3', 'rock8', 'rock9'];
    for (let x = 3640 * SF - 200; x < level.width * SF; x += 70 + r() * 90) {
      const k = rocks[Math.floor(r() * rocks.length)], im = this.img(k); if (!im) continue;
      sc.add.image(Math.round(x), H - Math.floor(im.height * (0.45 + r() * 0.25)), 'tr-' + k).setOrigin(0, 0).setScrollFactor(SF, 1).setDepth(90).setTint(0x1a2630);
      if (r() < 0.45) { // a snapped girder end poking up out of the rubble
        const g = sc.add.rectangle(Math.round(x + im.width * 0.5), H - 30 - Math.floor(r() * 10), 6, 40, 0x141c24).setOrigin(0, 0).setScrollFactor(SF, 1).setDepth(89.9).setAngle(-12 + r() * 24);
        g.setStrokeStyle(1, 0x2c3a46);
      }
    }
  }
  fallback() {
    const g = this.scene.add.graphics().setDepth(20), level = this.level;
    for (const s of level.ground) g.fillStyle(s.style === 'base' ? 0x5b5d5f : 0x4a3a28, 1).fillRect(s.x, s.y, s.w, level.height - s.y);
    for (const p of level.platforms) g.fillStyle(0x7a5a36, 1).fillRect(p.x, p.y, p.w, 5);
  }

  update(cam) {
    this.backdrop.update(cam);
    const dt = this.scene.game.loop.delta, L = cam.scrollX - 64, R = cam.scrollX + this.scene.scale.width + 64;
    if (this.cull) for (const e of this.cull) {
      const on = e.x1 > L && e.x0 < R;
      if (on === e.on) continue;
      e.on = on; e.o.setVisible(on);
      if (e.o.anims) { if (on) e.o.anims.resume(); else e.o.anims.pause(); }
    }
    for (const f of this.anim) {
      if (f.x0 !== undefined && (f.x1 < L || f.x0 > R)) continue;
      f(dt);
    }
  }
}
