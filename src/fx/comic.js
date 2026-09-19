// Comic-book page player shared by the story Intro and the Ending (story builder).
// A page is a set of panels on cream halftone paper; panels slide in one by one in hard steps, then their art pans
// (integer px steps, no soft fades) while captions, speech balloons and SFX lettering pop in beat by beat.
// Enter / X / Z: finish the current panel's beats, or go to the next panel / page.  Esc (or holding a key): skip all.
import { Sfx } from '../audio/Sfx.js';

const INK = 0x14101c, PAPER = 0xefe5cb, DOT = 0xdccfae, CAPTION = 0xffe070;

export class ComicPlayer {
  // pages: [[panel, ...], ...]; panel = {id, x, y, w, h, pan:[dx,dy], from:'left'|'right'|'top'|'bottom', beats:[...]}
  // beat = {t:'cap'|'say'|'sfx', s:'TEXT', x, y (panel-relative), tail:[x,y] (say only), font, big}
  constructor(scene, pages, onDone, opts = {}) {
    this.s = scene; this.pages = pages; this.onDone = onDone; this.opts = opts;
    this.sfx = new Sfx(scene);
    this.W = scene.scale.width; this.H = scene.scale.height;
    this.paperTex();
    this.page = (opts.startPage || 0) - 1; this.panel = -1; this.busy = false; this.done = false;
    this.pageLayer = null; this.pending = [];
    const kb = scene.input.keyboard;
    const adv = () => this.advance();
    kb.on('keydown-ENTER', adv); kb.on('keydown-X', adv); kb.on('keydown-Z', adv); kb.on('keydown-SPACE', adv);
    kb.on('keydown-ESC', () => this.finish());
    scene.input.on('pointerdown', adv);
    this.holdKeys = ['ENTER', 'X', 'Z'].map(k => kb.addKey(k));
    this.holdT = 0;
    scene.events.on('update', (t, dt) => this.update(dt));
    this.nextPage();
  }

  paperTex() {
    const s = this.s;
    if (s.textures.exists('comic-paper')) return;
    const W = this.W, H = this.H, t = s.textures.createCanvas('comic-paper', W, H), c = t.getContext();
    c.fillStyle = '#' + PAPER.toString(16); c.fillRect(0, 0, W, H);
    c.fillStyle = '#' + DOT.toString(16);
    for (let y = 0; y < H; y += 3) for (let x = (y / 3 % 2) * 2; x < W; x += 4) c.fillRect(x, y, 1, 1);
    t.refresh();
  }

  play(name) { const k = 'sfx-' + name; this.sfx.play(this.s.cache.audio.exists(k) ? name : (this.opts.fallback?.[name] || 'select')); }
  startLoop(name) { if (this.loopName) return; this.loopName = name; this.sfx.loop && this.sfx.loop(name, 0.6); }
  stopLoop() { if (this.loopName && this.sfx.stopLoop) this.sfx.stopLoop(this.loopName, 400); this.loopName = null; }

  update(dt) {
    if (this.done) return;
    // holding Enter / X / Z for 0.9 s skips the whole comic
    if (this.holdKeys.some(k => k.isDown)) { this.holdT += dt; if (this.holdT > 900) this.finish(); } else this.holdT = 0;
    // pan the live panels' art in 1px hard steps
    for (const p of this.live || []) {
      if (!p.pan || (!p.pan[0] && !p.pan[1])) continue;
      p.acc += dt;
      while (p.acc > p.stepMs && p.k < p.steps) { p.acc -= p.stepMs; p.k++; this.cropPanel(p); }
    }
    if (this.idleAt && this.s.time.now > this.idleAt && !this.busy) this.advance();   // auto-advance
  }

  cropPanel(p) {
    const [dx, dy] = p.pan, f = p.k / Math.max(1, p.steps);
    const cx = Math.round((dx >= 0 ? f : 1 - f) * Math.abs(dx)), cy = Math.round((dy >= 0 ? f : 1 - f) * Math.abs(dy));
    p.img.setCrop(cx, cy, p.w, p.h); p.img.setPosition(p.x - cx, p.y - cy);
  }

  nextPage() {
    this.page++;
    if (this.page >= this.pages.length) return this.finish();
    const old = this.pageLayer, W = this.W;
    const L = this.pageLayer = this.s.add.container(0, 0).setDepth(10);
    L.add(this.s.add.image(0, 0, 'comic-paper').setOrigin(0, 0));
    this.live = []; this.panel = -1;
    if (old) {   // page turn: the old page slides off left, the new one slides in from the right, hard steps
      this.play('page'); this.stopLoop();
      L.x = W; this.busy = true;
      this.s.tweens.add({ targets: old, x: -W, duration: 320, ease: 'Stepped', easeParams: [6], onComplete: () => old.destroy() });
      this.s.tweens.add({ targets: L, x: 0, duration: 320, ease: 'Stepped', easeParams: [6], onComplete: () => { this.busy = false; this.nextPanel(); } });
    } else this.nextPanel();
  }

  nextPanel() {
    const panels = this.pages[this.page];
    this.panel++;
    if (this.panel >= panels.length) return this.nextPage();
    const d = panels[this.panel], s = this.s, L = this.pageLayer;
    const p = { ...d, acc: 0, k: 0 };
    p.steps = Math.max(Math.abs(d.pan?.[0] || 0), Math.abs(d.pan?.[1] || 0)); p.stepMs = 5200 / Math.max(1, p.steps);
    const C = p.box = s.add.container(0, 0);
    const fr = s.add.graphics();
    fr.fillStyle(INK, 1).fillRect(d.x - 2, d.y - 2, d.w + 4, d.h + 4);
    fr.fillStyle(0x000000, 0.25).fillRect(d.x + 2, d.y + d.h + 2, d.w + 1, 2).fillRect(d.x + d.w + 2, d.y + 2, 2, d.h + 1);   // drop shadow
    C.add(fr);
    p.img = s.add.image(d.x, d.y, 'story-' + d.id).setOrigin(0, 0);
    C.add(p.img); this.cropPanel(p);
    p.fx = s.add.container(0, 0); C.add(p.fx);   // balloons / lettering live here (above the art, inside the panel's slide)
    L.add(C);
    this.live.push(p);
    // slide in from a side in hard steps
    const off = { left: [-60, 0], right: [60, 0], top: [0, -50], bottom: [0, 50] }[d.from || 'left'];
    C.setPosition(off[0], off[1]);
    this.busy = true; this.idleAt = 0;
    this.play('panel');
    if (d.loop) this.startLoop(d.loop);
    s.tweens.add({ targets: C, x: 0, y: 0, duration: 200, ease: 'Stepped', easeParams: [4], onComplete: () => {
      this.busy = false; this.cur = p; this.runBeats(p);
    } });
  }

  runBeats(p) {
    this.pending = (p.beats || []).map((b, i) => this.s.time.delayedCall(180 + i * 520, () => this.beat(p, b)));
    const total = 180 + (p.beats || []).length * 520;
    this.idleAt = this.s.time.now + total + (this.opts.hold || 3600);
  }

  flushBeats() {
    const left = this.pending.filter(e => e.getProgress() < 1);
    if (!left.length) return false;
    left.forEach(e => { e.remove(false); e.callback && e.callback(); });
    this.pending = [];
    this.idleAt = this.s.time.now + (this.opts.hold || 3600);
    return true;
  }

  advance() {
    if (this.done || this.busy) return;
    if (this.flushBeats()) return;
    this.nextPanel();
  }

  finish() {
    if (this.done) return; this.done = true;
    this.stopLoop();
    this.pending.forEach(e => e.remove(false));
    this.s.input.keyboard.removeAllListeners(); this.s.input.removeAllListeners();
    this.onDone && this.onDone();
  }

  txt(x, y, s, font) {
    const sc = this.s;
    if (sc.cache.bitmapFont.exists(font)) return sc.add.bitmapText(x, y, font, s);
    return sc.add.text(x, y, s, { fontFamily: 'monospace', fontSize: '8px', color: '#000' });
  }

  beat(p, b) {
    const s = this.s, F = p.fx; let X = p.x + b.x, Y = p.y + b.y;
    if (b.t === 'sfx') {                      // stamped lettering, slight tilt-free pop: 2x -> 1x in hard steps + panel jolt
      const t = this.txt(X, Y, b.s, b.font || 'hud-sfx-gold').setOrigin(0.5);
      const hw = Math.ceil(t.width / 2), hh = Math.ceil(t.height / 2);     // keep the lettering inside its panel
      t.x = Phaser.Math.Clamp(X, p.x + hw + 5, p.x + p.w - hw - 5); t.y = Phaser.Math.Clamp(Y, p.y + hh + 5, p.y + p.h - hh - 5);   // >= 4px clear of the border
      if (t.width + 10 > p.w) console.error(`[comic] SFX "${b.s}" is wider than panel ${p.id}`);
      F.add(t); t.setScale(2);
      s.time.delayedCall(60, () => t.setScale(1.5)); s.time.delayedCall(120, () => t.setScale(1));
      const C = p.box; s.tweens.add({ targets: C, x: { from: 3, to: 0 }, duration: 160, ease: 'Stepped', easeParams: [3] });
      this.play(b.snd || 'stamp');
      return;
    }
    const font = b.big ? 'hud-big-ink' : 'hud-font-ink';
    const t = this.txt(0, 0, b.s, font);
    const tw = Math.ceil(t.width), th = Math.ceil(t.height);
    const g = s.add.graphics();
    if (b.t === 'cap') {                      // yellow narration caption box
      const w = tw + 8, h = th + 5;
      X = Phaser.Math.Clamp(X, p.x + 4, p.x + p.w - w - 4); Y = Phaser.Math.Clamp(Y, p.y + 4, p.y + p.h - h - 4);
      if (w + 8 > p.w) console.error(`[comic] caption "${b.s}" is wider than panel ${p.id}`);
      g.fillStyle(INK, 1).fillRect(X - 1, Y - 1, w + 2, h + 2);
      g.fillStyle(CAPTION, 1).fillRect(X, Y, w, h);
      g.fillStyle(0xfff4b8, 1).fillRect(X, Y, w, 1);
      t.setPosition(X + 4, Y + 3);
    } else {                                  // speech balloon: rounded white box, 1px ink outline, short wedge tail
      const w = tw + 10, h = th + 7;
      const bx = Phaser.Math.Clamp(Math.round(X - w / 2), p.x + 4, p.x + p.w - w - 4), by = Phaser.Math.Clamp(Y, p.y + 4, p.y + p.h - h - 4);
      // every balloon must sit >= 4px inside its panel
      if (bx < p.x + 4 || by < p.y + 4 || bx + w > p.x + p.w - 4 || by + h > p.y + p.h - 4)
        console.error(`[comic] balloon "${b.s}" (${w}x${h}) does not fit 4px inside panel ${p.id} (${p.w}x${p.h})`);
      if (b.phone) {                          // voice on the phone / radio: jagged electric outline, no tail
        g.fillStyle(INK, 1).fillRect(bx - 1, by - 1, w + 2, h + 2);
        for (let x = bx + 2; x < bx + w - 2; x += 5) g.fillRect(x, by - 3, 2, 2).fillRect(x + 2, by + h + 1, 2, 2);
        for (let y = by + 2; y < by + h - 2; y += 5) g.fillRect(bx - 3, y, 2, 2).fillRect(bx + w + 1, y + 2, 2, 2);
        g.fillStyle(0xffffff, 1).fillRect(bx, by, w, h);
        g.fillStyle(0xdde4f0, 1).fillRect(bx, by + h - 1, w, 1);
      } else {
        // tail: a short wedge (max 11px) from the nearest balloon edge toward the speaker's mouth / the phone
        const [tx0, ty0] = b.tail ? [p.x + b.tail[0], p.y + b.tail[1]] : [bx + w / 2, by + h + 8];
        const side = ty0 > by + h ? 'down' : ty0 < by ? 'up' : tx0 < bx ? 'left' : 'right';
        let e1, e2, ex, ey;                   // base edge points + base centre
        if (side === 'down' || side === 'up') {
          const b0 = Phaser.Math.Clamp(Math.round(tx0) - 3, bx + 5, bx + w - 11), yy = side === 'down' ? by + h - 1 : by + 1;
          e1 = [b0, yy]; e2 = [b0 + 6, yy]; ex = b0 + 3; ey = side === 'down' ? by + h : by;
        } else {
          const b0 = Phaser.Math.Clamp(Math.round(ty0) - 2, by + 3, by + h - 8), xx = side === 'left' ? bx + 1 : bx + w - 1;
          e1 = [xx, b0]; e2 = [xx, b0 + 5]; ex = side === 'left' ? bx : bx + w; ey = b0 + 2;
        }
        const dx = tx0 - ex, dy = ty0 - ey, d = Math.hypot(dx, dy) || 1, L = Math.min(11, d);
        const tx = Math.round(ex + dx / d * L), ty = Math.round(ey + dy / d * L);
        g.fillStyle(INK, 1).fillTriangle(e1[0] - 1, e1[1] - (side === 'left' || side === 'right' ? 1 : 0), e2[0] + 1, e2[1] + (side === 'left' || side === 'right' ? 1 : 0), tx + Math.sign(dx), ty + Math.sign(dy));
        g.fillStyle(0xffffff, 1).fillTriangle(e1[0] + (side === 'up' || side === 'down' ? 1 : 0), e1[1] + (side === 'left' || side === 'right' ? 1 : 0),
          e2[0] - (side === 'up' || side === 'down' ? 1 : 0), e2[1] - (side === 'left' || side === 'right' ? 1 : 0), tx, ty);
        g.fillStyle(INK, 1).fillRect(bx + 2, by - 1, w - 4, h + 2).fillRect(bx - 1, by + 2, w + 2, h - 4).fillRect(bx, by, w, h);
        g.fillStyle(0xffffff, 1).fillRect(bx + 2, by, w - 4, h).fillRect(bx, by + 2, w, h - 4).fillRect(bx + 1, by + 1, w - 2, h - 2);
        // re-open the balloon outline where the tail joins
        if (side === 'down' || side === 'up') g.fillStyle(0xffffff, 1).fillRect(e1[0] + 1, side === 'down' ? by + h - 2 : by - 1, 5, 3);
        else g.fillStyle(0xffffff, 1).fillRect(side === 'left' ? bx - 1 : bx + w - 2, e1[1] + 1, 3, 4);
      }
      t.setPosition(bx + 5, by + 4);
    }
    F.add([g, t]);
    // pop: 2px up then settle (hard steps)
    [g, t].forEach(o => { o.y -= 2; s.time.delayedCall(70, () => { o.y += 2; }); });
    this.play('balloon');
  }
}
