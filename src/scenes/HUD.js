// HUD overlay, matches the reference layout at 480x270:
//   left:  framed sheep portrait, orange "1UP", 6-digit score, sheep-head life icons
//   right: framed weapon box (icon per weapon + ammo pips), "STAGE 01"
// plus banner cards: stage intro, WARNING!, STAGE CLEAR, GAME OVER. All text is pixel bitmap fonts (assets/hud/*.xml).
import { WEAPONS } from '../entities/weapons.js';

const GUN_FRAME = { R: 0, M: 1, S: 2, L: 3 };
const PIPS = 6;
const CARD_TOP = 44;   // y of the transient cards that play over live action (below the HUD clusters, above the play plane)

export class HUD extends Phaser.Scene {
  constructor() { super('HUD'); }
  init(d) {
    this.g = d.game;
    // the scene instance is reused per run: drop references to the previous run's (already destroyed) banner / continue objects
    this.bannerEvents = []; this.contEvents = []; this.contLayer = null; this.contNum = null;
  }

  // bitmap text with a system-font fallback so the HUD never breaks if a font fails to load
  txt(x, y, s, font = 'hud-font') {
    if (this.cache.bitmapFont.exists(font)) return this.add.bitmapText(x, y, font, s);
    const col = { 'hud-font-orange': '#ffa020', 'hud-big-red': '#ff5020', 'hud-big-gold': '#ffd060' }[font] || '#ffffff';
    return this.add.text(x, y, s, { fontFamily: 'monospace', fontSize: font.includes('big') ? '16px' : '8px', color: col, stroke: '#000', strokeThickness: 2 });
  }

  create() {
    const g = this.g, W = this.scale.width;
    this.cameras.main.roundPixels = true;

    // ---- left cluster
    this.add.image(4, 3, 'hud-portrait').setOrigin(0, 0);
    this.txt(42, 4, '1UP', 'hud-font-orange');
    this.score = this.txt(72, 4, "000000");
    this.lives = [];
    this.drawLives(g.state.lives);

    // ---- right cluster
    const stage = this.txt(0, 7, g.level.name);
    stage.x = W - 12 - stage.width;
    this.boxX = stage.x - 7 - 64; this.boxY = 3;
    this.box = this.add.image(this.boxX, this.boxY, 'hud-wbox').setOrigin(0, 0);
    this.gun = this.add.image(this.boxX + 3, this.boxY + 3, 'hud-guns', 0).setOrigin(0, 0);
    this.pips = [];
    for (let i = 0; i < PIPS; i++) this.pips.push(this.add.image(this.boxX + 42 + i * 3, this.boxY + 12, 'hud-pip', 0).setOrigin(0, 0));
    this.boxFlash = this.add.rectangle(this.boxX + 2, this.boxY + 2, 60, 18, 0xffffff, 0).setOrigin(0, 0);
    this.lit = PIPS;

    // ---- banners
    this.bannerLayer = this.add.container(0, 0).setDepth(10);

    g.events.on('score', s => { this.score.setText(String(Math.max(0, s)).padStart(6, '0')); });
    g.events.on('lives', n => this.drawLives(n));
    g.events.on('weapon', w => this.setWeapon(w, true));
    g.events.on('boss', () => this.warning());
    g.events.on('cleared', () => this.card('STAGE CLEAR', 'hud-big-gold', null, 0, false, CARD_TOP));
    g.events.on('gameover', () => this.card('GAME OVER', 'hud-big-steel', null, 0, true));
    g.events.on('pause', on => on ? this.card('PAUSE', 'hud-big-gold', 'PRESS START', 0, true) : this.clearBanner());
    g.events.on('continue', d => this.showContinue(d && d.seconds != null ? d.seconds : 9));
    g.events.on('continue-tick', n => this.tickContinue(n));
    g.events.on('continued', () => { this.hideContinue(); this.clearBanner(); });
    g.events.on('extralife', () => this.extraLife());
    g.events.on('stage-end', d => this.results(d || {}));
    if (g.hooked) { g.hooked.pause = true; g.hooked.continue = true; g.hooked.results = true; }
    this.hi0 = g.state.hi || 0;   // hi-score at stage start, to know if the results beat it
    this.events.once('shutdown', () => ['score', 'lives', 'weapon', 'boss', 'cleared', 'gameover', 'pause', 'continue', 'continue-tick',
      'continued', 'extralife', 'stage-end'].forEach(e => g.events.off(e)));
    this.setWeapon(g.player.weapon, false);
    this.score.setText(String(g.state.score || 0).padStart(6, '0'));

    // stage intro card (skipped when the test harness jumps into the middle of the level)
    const q = window.__sheep.query;
    if (!q.get('x') && !q.get('nointro')) this.card(g.level.name, 'hud-big-steel', 'JUNGLE ASSAULT', 2200, false, CARD_TOP);
  }

  update() {
    // ammo pips show how many shots of the current weapon are still "in the magazine" (Contra's on-screen bullet cap)
    const g = this.g; if (!g || !g.pBullets || !g.player) return;
    const wp = WEAPONS[g.player.weapon]; if (!wp) return;
    const per = wp.spread.length, cap = Math.max(1, Math.floor(wp.max / per) || 1);
    const used = Math.ceil(g.pBullets.countActive(true) / per);
    const lit = Phaser.Math.Clamp(Math.round(PIPS * (1 - used / cap)), 0, PIPS);
    if (lit !== this.lit) { this.lit = lit; this.pips.forEach((p, i) => p.setFrame(i < lit ? 0 : 1)); }
  }

  setWeapon(w, flash) {
    this.gun.setFrame(GUN_FRAME[w] ?? 0);
    this.lit = -1;
    if (flash) {
      this.tweens.killTweensOf(this.boxFlash);
      this.boxFlash.setAlpha(0.9);
      this.tweens.add({ targets: this.boxFlash, alpha: 0, duration: 260, ease: 'Stepped', easeParams: [4] });
    }
  }

  drawLives(n) {
    this.lives.forEach(l => l.destroy()); this.lives = [];
    const shown = Math.min(Math.max(0, n), 6);
    for (let i = 0; i < shown; i++) this.lives.push(this.add.image(41 + i * 18, 14, 'hud-life').setOrigin(0, 0));
  }

  clearBanner() {
    this.tweens.killTweensOf(this.bannerLayer.list); this.bannerLayer.removeAll(true);
    (this.bannerEvents || []).forEach(e => e.remove()); this.bannerEvents = [];
  }

  // centred card: dark band + big title (+ optional subtitle). ms=0 keeps it up. top = band y (default: screen centre);
  // the non-dimming cards (stage intro, stage clear) sit high in the sky band so they never cover the hero on the play plane.
  card(title, font, sub, ms, dim, top) {
    this.clearBanner();
    const W = this.scale.width, H = this.scale.height, L = this.bannerLayer;
    if (dim) L.add(this.add.rectangle(0, 0, W, H, 0x05040a, 0.45).setOrigin(0, 0));
    const bandH = sub ? 44 : 34, y0 = top ?? Math.round(H / 2 - bandH / 2) - 8;
    const band = this.add.graphics();
    band.fillStyle(0x05040a, 0.78).fillRect(0, y0, W, bandH);
    band.fillStyle(0xffa020, 1).fillRect(0, y0, W, 1).fillRect(0, y0 + bandH - 1, W, 1);
    band.fillStyle(0x7a3a08, 1).fillRect(0, y0 + 1, W, 1).fillRect(0, y0 + bandH - 2, W, 1);
    L.add(band);
    const t = this.txt(0, y0 + 7, title, font); t.x = Math.round(W / 2 - t.width / 2); L.add(t);
    if (sub) { const s = this.txt(0, y0 + 29, sub, 'hud-font-orange'); s.x = Math.round(W / 2 - s.width / 2); L.add(s); }
    // wipe in from the centre
    const mask = { v: 0 };
    this.tweens.add({ targets: mask, v: 1, duration: 160, onUpdate: () => {
      const h = Math.round(bandH * mask.v); band.clear();
      band.fillStyle(0x05040a, 0.78).fillRect(0, y0 + (bandH - h) / 2 | 0, W, h);
      band.fillStyle(0xffa020, 1).fillRect(0, y0 + (bandH - h) / 2 | 0, W, 1).fillRect(0, (y0 + (bandH + h) / 2 | 0) - 1, W, 1);
    } });
    t.x -= W; this.tweens.add({ targets: t, x: t.x + W, duration: 260, delay: 80, ease: 'Cubic.out' });
    if (ms > 0) this.bannerEvents.push(this.time.delayedCall(ms, () => {
      this.tweens.add({ targets: L.list, alpha: 0, duration: 250, ease: 'Stepped', easeParams: [5], onComplete: () => this.clearBanner() });
    }));
  }

  // boss alarm: blinking red WARNING! between scrolling hazard stripes
  warning() {
    this.clearBanner();
    const W = this.scale.width, L = this.bannerLayer, y0 = 96;
    const stripes = this.add.graphics(); L.add(stripes);
    const t = this.txt(0, y0 + 12, 'WARNING!', 'hud-big-red'); t.x = Math.round(W / 2 - t.width / 2); L.add(t);
    let off = 0;
    const draw = () => {
      stripes.clear();
      stripes.fillStyle(0x200404, 0.7).fillRect(0, y0 + 6, W, 30);
      for (const yy of [y0, y0 + 36]) {
        stripes.fillStyle(0x0c0a12, 1).fillRect(0, yy, W, 6);
        stripes.fillStyle(0xe82818, 1);
        for (let x = -12 + (off % 12); x < W + 12; x += 12)
          for (let r = 0; r < 4; r++) stripes.fillRect(x + r, yy + 1 + r, 6, 1);
      }
    };
    draw();
    const ev = this.time.addEvent({ delay: 50, loop: true, callback: () => { off += 1; draw(); } });
    const blink = this.time.addEvent({ delay: 220, loop: true, callback: () => t.setVisible(!t.visible) });
    this.bannerEvents.push(ev, blink, this.time.delayedCall(2600, () => this.clearBanner()));
  }

  // bevelled panel in the weapon-box style: dark outline, light top/left, shaded bottom/right, near-black glass
  panel(x, y, w, h, alpha = 0.92) {
    const gr = this.add.graphics();
    gr.fillStyle(0x0c0a12, 1).fillRect(x + 1, y, w - 2, h).fillRect(x, y + 1, w, h - 2);
    gr.fillStyle(0xd8dee8, 1).fillRect(x + 1, y + 1, w - 2, h - 2);
    gr.fillStyle(0xffffff, 1).fillRect(x + 2, y + 1, w - 4, 1).fillRect(x + 1, y + 2, 1, h - 4);
    gr.fillStyle(0x8e98ae, 1).fillRect(x + 2, y + h - 2, w - 4, 1).fillRect(x + w - 2, y + 2, 1, h - 4);
    gr.fillStyle(0x0c0a12, 1).fillRect(x + 1, y + 1, 1, 1).fillRect(x + w - 2, y + 1, 1, 1).fillRect(x + 1, y + h - 2, 1, 1).fillRect(x + w - 2, y + h - 2, 1, 1);
    gr.fillStyle(0x05060a, alpha).fillRect(x + 2, y + 2, w - 4, h - 4);
    return gr;
  }

  centerX(t) { t.x = Math.round(this.scale.width / 2 - t.width / 2); return t; }

  // arcade CONTINUE? countdown under the GAME OVER card
  showContinue(sec) {
    this.hideContinue();
    const W = this.scale.width, pw = 150, ph = 40, x = Math.round(W / 2 - pw / 2), y = 150;
    const L = this.contLayer = this.add.container(0, 0).setDepth(11);
    L.add(this.panel(x, y, pw, ph));
    const q = this.txt(x + 12, y + 8, 'CONTINUE?', 'hud-font-gold');
    this.contNum = this.txt(0, y + 5, String(sec), 'hud-big-orange'); this.contNum.x = x + pw - 14 - this.contNum.width;
    const ps = this.txt(0, y + 25, 'PRESS START', 'hud-font'); this.centerX(ps);
    L.add([q, this.contNum, ps]);
    this.contEvents = [this.time.addEvent({ delay: 260, loop: true, callback: () => ps.setVisible(!ps.visible) })];
    L.y = 8; this.tweens.add({ targets: L, y: 0, duration: 160, ease: 'Stepped', easeParams: [4] });
  }
  tickContinue(n) {
    if (!this.contNum) return;
    const x = this.contNum.x + this.contNum.width;
    this.contNum.setText(String(Math.max(0, n)));
    this.contNum.x = x - this.contNum.width;
    // hard flash: swap to the bright steel font for a beat, then back
    if (this.cache.bitmapFont.exists('hud-big-steel')) {
      this.contNum.setFont('hud-big-steel');
      this.time.delayedCall(120, () => this.contNum && this.contNum.setFont(n <= 3 ? 'hud-big-red' : 'hud-big-orange'));
    }
  }
  hideContinue() {
    (this.contEvents || []).forEach(e => e.remove()); this.contEvents = [];
    if (this.contLayer) { this.contLayer.destroy(true); this.contLayer = null; this.contNum = null; }
  }

  // 1-UP: the newest life icon blinks and a "1UP!" tag pops next to the row
  extraLife() {
    const last = this.lives[this.lives.length - 1];
    const tx = last ? last.x + 19 : 42;
    const tag = this.txt(tx, 18, '1UP!', 'hud-font-orange');
    let n = 0;
    const ev = this.time.addEvent({ delay: 110, repeat: 15, callback: () => {
      n++; if (last && last.active) last.setVisible(n % 2 === 0 || n > 14);
      if (n > 15) tag.destroy();
    } });
    this.tweens.add({ targets: tag, y: 14, duration: 300, ease: 'Stepped', easeParams: [4] });
    return ev;
  }

  // stage-clear score tally under the STAGE CLEAR card: counts up, then holds
  tally(score) {
    const W = this.scale.width, pw = 170, ph = 30, x = Math.round(W / 2 - pw / 2), y = 150;
    const L = this.add.container(0, 0).setDepth(11);
    this.bannerLayer.add(L);
    L.add(this.panel(x, y, pw, ph));
    L.add(this.txt(x + 10, y + 11, 'SCORE', 'hud-font-orange'));
    const v = this.txt(0, y + 7, '000000', 'hud-big-gold'); v.x = x + pw - 10 - v.width; L.add(v);
    const c = { n: 0 };
    this.tweens.add({ targets: c, n: score, duration: 800, ease: 'Linear',
      onUpdate: () => v.setText(String(Math.round(c.n / 10) * 10).padStart(6, '0')),
      onComplete: () => v.setText(String(score).padStart(6, '0')) });
  }

  // arcade stage RESULTS card: header, lines counting up one by one with a tick, hi-score flash, next stage, PRESS START
  results(r) {
    this.clearBanner();
    const g = this.g, W = this.scale.width, H = this.scale.height, L = this.bannerLayer;
    const pw = 264, ph = 176, x0 = Math.round(W / 2 - pw / 2), y0 = Math.round(H / 2 - ph / 2) - 4;
    L.add(this.add.rectangle(0, 0, W, H, 0x05040a, 0.5).setOrigin(0, 0));
    L.add(this.panel(x0, y0, pw, ph, 0.94));
    const head = this.centerX(this.txt(0, y0 + 8, (g.level.name || 'STAGE 01') + ' CLEAR', 'hud-big-gold')); L.add(head);
    const rule = this.add.graphics(); rule.fillStyle(0xffa020, 1).fillRect(x0 + 12, y0 + 29, pw - 24, 1); rule.fillStyle(0x7a3a08, 1).fillRect(x0 + 12, y0 + 30, pw - 24, 1); L.add(rule);
    const tm = r.time || 0, mmss = n => Math.floor(n / 60) + ':' + String(n % 60).padStart(2, '0');
    const rows = [
      ['SCORE', r.score || 0, n => String(n).padStart(6, '0')],
      ['KILLS', r.kills || 0, n => String(n)],
      ['ACCURACY', r.accuracy || 0, n => n + '%'],
      ['LIVES BONUS', r.livesBonus || 0, n => (r.lives || 0) + 'x2000=' + n],
      ['TIME', tm, n => mmss(n)],
    ];
    const snd = () => g.sfx && g.sfx.play && g.sfx.play('count');
    let t = 250;
    rows.forEach(([label, val, fmt], i) => {
      const y = y0 + 38 + i * 15;
      const lab = this.txt(x0 + 16, y, label, 'hud-font').setVisible(false);
      const v = this.txt(0, y, fmt(0), 'hud-font-gold').setVisible(false);
      const right = x0 + pw - 16; v.x = right - v.width;
      L.add([lab, v]);
      this.bannerEvents.push(this.time.delayedCall(t, () => {
        lab.setVisible(true); v.setVisible(true);
        const steps = 8; let k = 0;
        this.bannerEvents.push(this.time.addEvent({ delay: 40, repeat: steps - 1, callback: () => {
          k++; const n = k >= steps ? val : Math.round(val * k / steps);
          v.setText(fmt(n)); v.x = right - v.width; if (k % 2 === 0 || k === steps) snd();
        } }));
      }));
      t += 480;
    });
    // hi-score flash
    if ((r.score || 0) > this.hi0) {
      const hi = this.centerX(this.txt(0, y0 + 116, 'NEW HI-SCORE!', 'hud-big-red')).setVisible(false); L.add(hi);
      this.bannerEvents.push(this.time.delayedCall(t, () => {
        snd(); let n = 0;
        this.bannerEvents.push(this.time.addEvent({ delay: 90, loop: true, callback: () => {
          n++; hi.setVisible(n % 2 === 0 || n > 12); if (n > 12) hi.setFont(n % 8 < 4 ? 'hud-big-red' : 'hud-big-gold');
        } }));
      }));
      t += 400;
    }
    const next = this.centerX(this.txt(0, y0 + 142, r.next || 'STAGE 2 COMING SOON', 'hud-font-orange')).setVisible(false);
    const ps = this.centerX(this.txt(0, y0 + 158, 'PRESS START', 'hud-font')).setVisible(false);
    L.add([next, ps]);
    this.bannerEvents.push(this.time.delayedCall(t, () => {
      next.setVisible(true);
      this.bannerEvents.push(this.time.addEvent({ delay: 260, loop: true, callback: () => ps.setVisible(!ps.visible) }));
    }));
    L.y = 10; this.tweens.add({ targets: L, y: 0, duration: 200, ease: 'Stepped', easeParams: [5] });
  }
}
