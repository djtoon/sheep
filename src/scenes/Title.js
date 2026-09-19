// Title screen (ref: ARMED AND FLUFFY key art, ref/2f33...png), built from separate pixel layers so it can move:
// plate (sky, jungle, burning base) -> additive fire flicker -> searchlight beams -> helicopters -> rain -> sheep on rock
// -> embers -> logo -> menu. Enter / X / Z starts the game.
import { Sfx } from '../audio/Sfx.js'; import { Music } from '../audio/Music.js';

export class Title extends Phaser.Scene {
  constructor() { super('Title'); }

  create() {
    const W = this.scale.width, H = this.scale.height;
    this.cameras.main.roundPixels = true;
    this.t0 = this.time.now;
    this.leaving = false;   // the scene instance is reused: a stale flag from the last visit would block START

    // ---- plate + fire flicker
    if (this.textures.exists('title-bg')) this.add.image(0, 0, 'title-bg').setOrigin(0, 0);
    else this.add.rectangle(0, 0, W, H, 0x101828).setOrigin(0, 0);
    this.fire = this.textures.exists('title-fire') ? this.add.image(0, 0, 'title-fire').setOrigin(0, 0).setBlendMode(Phaser.BlendModes.ADD).setAlpha(0.3) : null;
    this.glow = this.add.graphics().setBlendMode(Phaser.BlendModes.ADD);

    // ---- searchlights + helicopters
    // searchlights: two flat hard-edged translucent tones (core + outer cone) drawn into a 480x270 canvas texture (no soft gradients)
    if (this.textures.exists('title-beams')) this.textures.remove('title-beams');
    this.beamTex = this.textures.createCanvas('title-beams', W, H);
    this.beamCtx = this.beamTex.getContext();
    this.beamImg = this.beamCtx.createImageData(W, H);
    this.add.image(0, 0, 'title-beams').setOrigin(0, 0).setBlendMode(Phaser.BlendModes.ADD);
    this.beamFrame = 0;
    this.helis = [
      { x: 58, y: 62, flip: true, a0: 1.15, amp: 0.22, spd: 0.00055, ph: 0, beamLen: 125 },   // left heli, beam down-right
      { x: 420, y: 26, flip: false, a0: 2.0, amp: 0.2, spd: 0.00047, ph: 2, beamLen: 135 }, // right heli, beam down-left
    ];
    for (const h of this.helis) {
      h.spr = this.add.sprite(h.x, h.y, 'title-heli', 0).setFlipX(h.flip);
      if (this.anims.exists('title-heli-fly')) h.spr.play({ key: 'title-heli-fly', startFrame: h.flip ? 1 : 0 });
    }

    // ---- rain (behind the hero, over the plate)
    this.rain = this.add.graphics();
    this.drops = [];
    for (let i = 0; i < 150; i++) this.drops.push(this.newDrop(true));

    // ---- hero on the rock
    // hero keep-out mask (alpha of the sheep sprite, dilated 3px) so beams never cross the sheep
    this.heroMask = new Uint8Array(W * H);
    if (this.textures.exists('title-sheep')) {
      const img = this.textures.get('title-sheep').getSourceImage(), cv = document.createElement('canvas');
      cv.width = img.width; cv.height = img.height; const cx = cv.getContext('2d'); cx.drawImage(img, 0, 0);
      const px = cx.getImageData(0, 0, img.width, img.height).data;
      for (let y = 0; y < img.height; y++) for (let x = 0; x < img.width; x++) if (px[(y * img.width + x) * 4 + 3] > 0)
        for (let dy = -3; dy <= 3; dy++) for (let dx = -3; dx <= 3; dx++) {
          const X = 152 + x + dx, Y = 89 + y + dy; if (X >= 0 && X < W && Y >= 0 && Y < H) this.heroMask[Y * W + X] = 1;
        }
    }
    this.beamMask = new Uint8Array(W * H);
    if (this.textures.exists('title-sheep')) this.add.image(152, 89, 'title-sheep').setOrigin(0, 0).setDepth(5);   // hero above rain/haze; head sits clearly below FLUFFY

    // ---- embers + foreground rain
    this.embers = this.add.graphics().setDepth(4);          // embers + haze stay BEHIND hero, rock and logo
    this.sparks = [];
    this.rainFg = this.add.graphics().setDepth(4);
    this.dropsFg = [];
    for (let i = 0; i < 40; i++) this.dropsFg.push(this.newDrop(true, true));
    // a very sparse streak layer in FRONT of everything, masked away from the hero and the logo
    this.rainTop = this.add.graphics().setDepth(5.5);
    this.dropsTop = [];
    for (let i = 0; i < 10; i++) this.dropsTop.push(this.newDrop(true, true));
    this.keepOut = [[W / 2 - 120, 0, 240, 110], [150, 86, 180, 160]];   // logo box, hero box (x, y, w, h)

    // ---- lightning flash (rare, subtle)
    this.flash = this.add.rectangle(0, 0, W, H, 0xc8dcff, 0).setOrigin(0, 0).setBlendMode(Phaser.BlendModes.ADD).setDepth(4);
    this.nextBolt = 2600;

    // ---- logo (drops in, then settles)
    if (this.textures.exists('title-logo')) {
      this.logo = this.add.image(Math.round(W / 2 - 117), 0, 'title-logo').setOrigin(0, 0).setDepth(5);
      this.logo.y = -130;
      this.tweens.add({ targets: this.logo, y: 0, duration: 520, ease: 'Bounce.out' });
    } else this.add.text(W / 2, 60, 'ARMED AND FLUFFY', { fontFamily: 'monospace', fontSize: '28px', color: '#ffe0a0', stroke: '#000', strokeThickness: 4 }).setOrigin(0.5);

    // ---- menu
    const bt = (x, y, s, f) => this.cache.bitmapFont.exists(f) ? this.add.bitmapText(x, y, f, s)
      : this.add.text(x, y, s, { fontFamily: 'monospace', fontSize: '10px', color: '#fff', stroke: '#000', strokeThickness: 2 });
    const plate = this.add.graphics().setDepth(6);
    plate.fillStyle(0x05040a, 0.45).fillRect(W / 2 - 58, 243, 124, 27).fillRect(W / 2 - 56, 242, 120, 28);
    this.items = [bt(0, 246, 'START GAME', 'hud-font-gold'), bt(0, 258, 'OPTIONS', 'hud-font-blue')];
    for (const it of this.items) it.setDepth(6);
    for (const it of this.items) it.x = Math.round(W / 2 - it.width / 2 + 4);
    this.items[1].x = this.items[0].x + 7; // left-aligned under START like the ref
    this.cursor = this.add.image(0, 0, 'hud-cursor').setOrigin(0, 0).setDepth(6);
    this.sel = 0; this.placeCursor();
    const pulse = [0xffffff, 0xfff4d0, 0xffe0a0, 0xffc880, 0xffe0a0, 0xfff4d0];
    this.time.addEvent({ delay: 90, loop: true, callback: () => {
      this.blink = ((this.blink || 0) + 1) % pulse.length;
      this.cursor.setTint(pulse[this.blink]);
      const it = this.items[this.sel]; this.cursor.x = it.x - 11 + (this.blink >= 2 && this.blink <= 4 ? 1 : 0);
    } });

    this.sfx = new Sfx(this); Music.play(this, 'title');
    const kb = this.input.keyboard;
    kb.on('keydown-UP', () => this.move(-1)); kb.on('keydown-DOWN', () => this.move(1));
    const go = () => {
      if (this.leaving) return; this.leaving = true;
      this.sound.context?.resume?.();
      this.sfx.play('start'); Music.stop(400);
      this.time.addEvent({ delay: 60, repeat: 7, callback: () => this.items[0].setVisible(!this.items[0].visible) });
      this.cameras.main.fadeOut(380, 0, 0, 0);
      this.time.delayedCall(420, () => this.scene.start('Game', { stage: 1 }));
    };
    kb.on('keydown-ENTER', go); kb.on('keydown-X', go); kb.on('keydown-Z', go); this.input.on('pointerdown', go);
    window.__sheep.ready = true;
  }

  move(d) { this.sfx.play('select'); this.sel = (this.sel + d + this.items.length) % this.items.length; this.placeCursor(); }
  placeCursor() { const it = this.items[this.sel]; this.cursor.setPosition(it.x - 11, it.y - 1); }

  // narrow searchlight cones: start at the nose lamp, taper, 3 hard tones by distance (bright -> faint), no dither.
  // Each beam is clipped where its axis first meets the hero, and never draws over the hero mask.
  drawBeams() {
    const W = this.scale.width, H = this.scale.height, d = this.beamImg.data, M = this.beamMask, hero = this.heroMask;
    d.fill(0); M.fill(0);
    const half = 0.075;
    for (const h of this.helis) {
      const ca = Math.cos(h.ang), sa = Math.sin(h.ang);
      let L = h.beamLen;
      for (let t = 4; t < L; t++) {                                        // clip before the hero
        const X = Math.round(h.sx + ca * t), Y = Math.round(h.sy + sa * t);
        if (X < 0 || X >= W || Y < 0 || Y >= H) { L = t; break; }
        if (hero[Y * W + X]) { L = t - 6; break; }
      }
      const x0 = Math.max(0, Math.floor(Math.min(h.sx, h.sx + ca * L) - L * half - 2)), x1 = Math.min(W - 1, Math.ceil(Math.max(h.sx, h.sx + ca * L) + L * half + 2));
      const y0 = Math.max(0, h.sy), y1 = Math.min(H - 1, Math.ceil(h.sy + sa * L + L * half + 2));
      for (let y = y0; y <= y1; y++) for (let x = x0; x <= x1; x++) {
        const k = y * W + x; if (hero[k]) continue;
        const dx = x - h.sx, dy = y - h.sy, along = dx * ca + dy * sa;
        if (along < 1 || along > L) continue;
        if (Math.abs(-dx * sa + dy * ca) > along * half + 0.5) continue;
        const f = along / h.beamLen;
        const a = f < 0.3 ? 110 : f < 0.62 ? 62 : 30;                       // 3 hard tones
        const i = k * 4; d[i] = 210; d[i + 1] = 232; d[i + 2] = 255; d[i + 3] = a; M[k] = 1;
      }
      for (const [ox, oy] of [[0, 0], [1, 0], [0, 1], [1, 1], [-1, 0], [0, -1]]) {   // hot lamp
        const X = h.sx + ox, Y = h.sy + oy; if (X < 0 || Y < 0 || X >= W || Y >= H) continue;
        const i = (Y * W + X) * 4; d[i] = d[i + 1] = d[i + 2] = 255; d[i + 3] = 255;
      }
    }
    this.beamCtx.putImageData(this.beamImg, 0, 0);
    this.beamTex.refresh();
  }

  newDrop(anyY, fg) {
    const H = this.scale.height;
    return { x: Math.random() * 520, y: anyY ? Math.random() * H : -8 - Math.random() * 20,
      v: fg ? 7 + Math.random() * 2 : 4.5 + Math.random() * 2, len: fg ? 7 : 4 + (Math.random() * 3 | 0), fg,
      c: Math.random() < 0.3 ? 0xd8e8ff : 0x8fb0e0 };
  }

  drawRain(g, drops, alpha, avoid) {
    const H = this.scale.height;
    g.clear();
    for (const d of drops) {
      d.y += d.v; d.x -= d.v / 3;
      if (d.y > H + 8 || d.x < -10) Object.assign(d, this.newDrop(false, d.fg));
      const x = Math.round(d.x), y = Math.round(d.y);
      const lit = x >= 0 && x < 480 && y >= 0 && y < 270 && this.beamMask && this.beamMask[y * 480 + x];
      g.fillStyle(lit ? 0xffffff : d.c, lit ? 1 : alpha);                 // rain catches the searchlight
      if (avoid && avoid.some(([ax, ay, aw, ah]) => x > ax - 4 && x < ax + aw + 4 && y > ay - 8 && y < ay + ah)) continue;
      for (let i = 0; i < d.len; i++) g.fillRect(x + Math.floor((d.len - i) / 3), y + i, 1, 1);
    }
  }

  update(time) {
    const t = time - this.t0, W = this.scale.width;

    // fire flicker: noisy additive pulse on the burning base + warm glow on the right edge
    const n = 0.5 + 0.25 * Math.sin(t * 0.013) + 0.25 * Math.sin(t * 0.031 + 1.7);
    const flick = n * (0.8 + 0.4 * Math.random());
    if (this.fire) this.fire.setAlpha(0.12 + 0.3 * flick);
    this.glow.clear();
    for (let i = 0; i < 6; i++) this.glow.fillStyle(0xff5010, 0.018 + 0.012 * n).fillRect(W - 170 + i * 28, 70, 170 - i * 28, 150);

    // helicopters bob + beams sweep
    for (const h of this.helis) {
      const bob = Math.round(Math.sin(t * 0.002 + h.ph) * 1.5);
      h.spr.setPosition(h.x + Math.round(Math.sin(t * 0.0004 + h.ph) * 4), h.y + bob);
      h.ang = h.a0 + Math.sin(t * h.spd * Math.PI + h.ph) * h.amp;
      h.sx = Math.round(h.spr.x + (h.flip ? 19 : -19)); h.sy = Math.round(h.spr.y + 4);   // the nose lamp
    }
    if ((this.beamFrame++ & 1) === 0) this.drawBeams();
    // rain
    this.drawRain(this.rain, this.drops, 0.45);
    this.drawRain(this.rainFg, this.dropsFg, 0.6);
    this.drawRain(this.rainTop, this.dropsTop, 0.7, this.keepOut);

    // embers rising off the burning base (and a few from the foreground fires)
    if (Math.random() < 0.55) this.sparks.push({ x: 300 + Math.random() * 180, y: 150 + Math.random() * 110, vx: -0.15 - Math.random() * 0.35,
      vy: -0.35 - Math.random() * 0.5, life: 90 + Math.random() * 120, age: 0, s: Math.random() < 0.25 ? 2 : 1, ph: Math.random() * 6 });
    if (Math.random() < 0.12) this.sparks.push({ x: 20 + Math.random() * 150, y: 200 + Math.random() * 60, vx: 0.1 + Math.random() * 0.2,
      vy: -0.3 - Math.random() * 0.3, life: 60 + Math.random() * 80, age: 0, s: 1, ph: Math.random() * 6 });
    this.embers.clear();
    this.sparks = this.sparks.filter(s => {
      s.age++; s.x += s.vx + Math.sin(s.age * 0.08 + s.ph) * 0.25; s.y += s.vy;
      const k = 1 - s.age / s.life; if (k <= 0) return false;
      const c = k > 0.6 ? 0xfff0a0 : k > 0.3 ? 0xffa030 : 0xd84810;
      this.embers.fillStyle(c, 1).fillRect(Math.round(s.x), Math.round(s.y), s.s, s.s);
      return true;
    });

    // lightning
    if (t > this.nextBolt) {
      this.nextBolt = t + 4000 + Math.random() * 5000;
      this.tweens.add({ targets: this.flash, alpha: { from: 0.28, to: 0 }, duration: 90, yoyo: false,
        onComplete: () => this.tweens.add({ targets: this.flash, alpha: { from: 0.18, to: 0 }, duration: 220, delay: 60 }) });
    }
  }
}
