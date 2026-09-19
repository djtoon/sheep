// STAGE 03 boss (the finale): SPECIMEN X, a xeno-cyborg queen (ref/levels/level3 boss.png).
//  Intro:   the specimen window flickers, the thing inside wakes (green eyes), slams the glass - WARNING.
//  Phase 1: it fights from behind the cracked specimen glass. The glass is the target (standing / prone line,
//           4 crack stages, max 10 damage per 3 s). Attacks: charged plasma beam (long cyan charge, aim LOCKED at
//           the tell start at head-top: prone or step), acid spit arcs onto blinking marks, tail whip needles.
//  Phase 2: the glass explodes; the queen steps out. Weak point: the glowing honeycomb heart (max 12 per 3 s).
//           Adds: screeching lunge (claws sweep the ground in front - back off), summons xeno crawlers,
//           beam / acid / needles faster. Its two specimen canisters can be shot off (no crawlers / less acid).
//  Death:   heart ruptures, it thrashes, chain explosions, collapses and dissolves into the floor, long white-out.
// Art: assets/boss3/* built by art/raw/boss3/build_boss3.py.
import { rnd, pick, groundLine, part, zone, tink, chunks, flash, tick, BossBar, hazard, runHazards, lob } from './bosskit.js';
import { ROSTER3 } from './roster3.js';

const FW = 140, FH = 131, BOT = 129;                         // body frame (2px outline); row 129 sits on the ground
const CANNON = [2, 50], MUZ = [3, 65];                       // cannon sprite top-left / muzzle (frames 0, 1)
const ROOT = [[121, 75], [121, 75], [124, 89]];              // tail root per frame
const ORG = [[63, 57], [61, 55], [65, 72]];                  // heart centre per frame [stand, hurt, lunge]
const CANS = [[81, 13], [96, 27]];                           // canister top-left (16x22), frames 0/1
const MOUTH = [27, 40];
const TAIL_A = [-25, -12, 0, 12, 25], TAIL_TIP = [-8, -72];
const HUD_Y = 34;
// debris stays low: nothing gets flung up onto the ceiling beam
const chunks3 = (sc, x, y, n, s = 1) => chunks(sc, 'b3-chunks', x, y, n, Math.min(0.75, s));                                            // nothing of hers may enter the HUD band

export class Boss3 {
  constructor(scene, x) {
    const sc = this.scene = scene; this.active = true;
    this.GY = groundLine(sc, x + 60);
    this.X1 = x - 22; this.X2 = x - 62; this.X = this.X1; this.dy = 0;
    this.state = 'intro'; this.t0 = this.spawnAt = sc.time.now; this.fr = 0;
    this.haz = []; this.smokeSpots = []; this.crawlers = [];
    const WX = this.X1 - 22, WY = Math.max(HUD_Y, this.GY - 134);
    // dim the far wall behind her so the purple crest reads (a flat dark wash, not a glow)
    this.dim = sc.add.rectangle(WX - 30, 0, 600, this.GY, 0x02060a, 1).setOrigin(0, 0).setDepth(21).setAlpha(0);
    sc.tweens.add({ targets: this.dim, alpha: 0.6, duration: 900 });
    this.win = sc.add.image(WX, WY, 'b3-window').setOrigin(0, 0).setDepth(32);
    this.glass = part(this, sc.physics.add.sprite(WX + 6 + 86, WY + 11 + 59, 'b3-glass', 0).setDepth(31.5), 30, 'glass');
    this.glass.body.setSize(172, 118); this.glass.body.enable = false;
    this.body = sc.add.image(0, 0, 'b3-body', 0).setOrigin(0, 0).setDepth(30);
    this.cannon = sc.add.image(0, 0, 'b3-cannon').setOrigin(0, 0).setDepth(30.6);
    this.tail = sc.add.sprite(0, 0, 'b3-tail', 2).setDepth(29.5); this.tail.ai = 2;
    this.organ = part(this, sc.physics.add.sprite(0, 0, 'b3-organ', 0).setDepth(30.5), 40, 'organ');
    this.organ.body.setSize(28, 30); this.organ.body.enable = false;
    this.cans = CANS.map((c, i) => { const k = part(this, sc.physics.add.sprite(0, 0, 'b3-cans', i * 2).setOrigin(0, 0).setDepth(30.4), 8, 'can'); k.idx = i; k.body.enable = false; return k; });
    this.charge = sc.add.sprite(0, 0, 'b3-charge', 0).setDepth(33).setVisible(false);
    this.eyes = sc.add.image(0, 0, 'boss-lamp', 1).setDepth(31).setVisible(false);
    this.bar = new BossBar(sc, 'SPECIMEN X');
    this.sight = sc.add.graphics().setDepth(54);
    this.layout();
  }

  // ------------------------------------------------------------------ placement
  get top() { return this.GY - BOT + Math.round(this.dy); }
  L(p) { return [Math.round(this.X + p[0]), this.top + p[1]]; }
  layout() {
    const f = this.fr, t = this.top, X = Math.round(this.X + (this.jit || 0));
    this.body.setFrame(f).setPosition(X, t);
    const lunging = f === 2;
    this.cannon.setVisible(!lunging && this.state !== 'sunk' && !this.cannonGone).setPosition(X + CANNON[0], t + CANNON[1]);
    const [rx, ry] = this.L(ROOT[f]); this.tail.setPosition(rx, ry).setFrame(this.tail.ai);
    this.tail.setVisible(this.state !== 'sunk' && !this.tailGone);
    const [ox, oy] = this.L(ORG[f]); this.organ.setPosition(ox, oy);
    this.cans.forEach((c, i) => { const [cx, cy] = this.L(CANS[i]); c.setPosition(cx, cy).setVisible(!lunging && this.state !== 'sunk'); if (!lunging && !c.dead) c.body.enable = this.state === 'p2'; if (lunging) c.body.enable = false; });
    const [mx, my] = this.L(MUZ); this.charge.setPosition(mx - 3, my);
    this.eyes.setPosition(X + 20, t + 34);
  }
  tailTip() {
    const a = TAIL_A[this.tail.ai] * Math.PI / 180, [rx, ry] = this.L(ROOT[this.fr]);
    const x = TAIL_TIP[0], y = TAIL_TIP[1];
    return { x: rx + x * Math.cos(a) + y * Math.sin(a), y: ry - x * Math.sin(a) + y * Math.cos(a) };
  }

  // ------------------------------------------------------------------ damage
  fighting() { return this.state === 'p1' || this.state === 'p2' || this.state === 'trans'; }
  hit(s, n, bl) {
    if (!s.active || s.dead || !this.fighting()) return;
    const sc = this.scene, now = sc.time.now;
    if (s.kind === 'glass' || s.kind === 'organ') {
      if (s.kind === 'organ' && this.state !== 'p2') return;
      if (now > (this.capT || 0)) { this.capT = now + 3000; this.capW = 0; }
      const cap = s.kind === 'glass' ? 10 : 12;
      n = Math.min(n, Math.max(0, cap - (this.capW || 0)));
      if (!n) {                                              // over the window's cap: the hit glances off
        if (s.kind === 'glass') { if (Math.random() < 0.5) sc.fx.part?.('b3-shards', [Math.floor(rnd(0, 8))], bl ? bl.x : s.x, bl ? bl.y : s.y, -rnd(40, 110), -rnd(40, 120), { g: 500, life: 400, depth: 64 }); }
        else tink(this, bl ? bl.x : s.x - 8, bl ? bl.y : s.y);
        return;
      }
      this.capW = (this.capW || 0) + n; s.hp -= n; sc.addScore(n * 50);
      sc.sfx?.play('hit');
      if (s.kind === 'glass') {
        for (let i = 0; i < 2; i++) sc.fx.part?.('b3-shards', [Math.floor(rnd(0, 8))], bl ? bl.x : s.x, bl ? bl.y : s.y, -rnd(40, 140), -rnd(40, 160), { g: 600, life: 600, depth: 64, bounce: 0.3 });
        const st = Math.min(3, Math.floor((1 - s.hp / s.maxHp) * 4));
        if (st > (s.stage || 0)) { s.stage = st; s.setFrame(st); sc.sfx?.play('glass', 0.7); sc.fx.shake(120, 0.005); }
        tick(this, bl ? bl.x - 6 : s.x, (bl ? bl.y : s.y) - 16, s.hp, s.maxHp);
        if (s.hp <= 0) this.shatter();
      } else {
        if (now > (this.nextFlash || 0)) { this.nextFlash = now + 200; flash(sc, [this.body, s], false); }
        this.kick = now + 70;
        sc.fx.spark?.(s.x - 6 + rnd(-3, 3), s.y + rnd(-4, 4), 3, 'fire', 120, 20);
        tick(this, s.x - 14, s.y - 20, s.hp, s.maxHp);
        const cr = s.hp <= s.maxHp / 3 ? 2 : s.hp <= s.maxHp * 2 / 3 ? 1 : 0;
        if (cr > (s.crack || 0)) { s.crack = cr; sc.fx.explode(s.x, s.y, 0.7); chunks3(sc, s.x, s.y, 4, 0.8); sc.sfx?.play('goo', 0.9); if (cr === 1) this.fr = this.fr === 2 ? 2 : 1; }
        if (s.hp <= 0) this.die();
      }
      return;
    }
    // canisters
    s.hp -= n; sc.sfx?.play('hit');
    if (now > (s.nextFlash || 0)) { s.nextFlash = now + 150; flash(sc, [s], true); }
    if (s.hp <= 0) {
      s.dead = true; s.body.enable = false; s.setFrame(s.idx * 2 + 1);
      sc.fx.explode(s.x + 8, s.y + 10, 1.1); sc.sfx?.play('glass', 0.9);
      for (let i = 0; i < 6; i++) sc.fx.part?.('b3-shards', [Math.floor(rnd(0, 8))], s.x + 8, s.y + 10, rnd(-120, 120), -rnd(60, 200), { g: 600, life: 700, depth: 64, bounce: 0.3 });
      this.smokeSpots.push({ dx: CANS[s.idx][0] + 8, dy: CANS[s.idx][1] + 4, goo: true });
      sc.addScore(1000);
    }
  }

  // ------------------------------------------------------------------ main loop
  update(time) {
    const sc = this.scene, p = sc.player; if (!p) return;
    const t = time - this.t0;
    const front = this.state === 'p1' || this.state === 'intro' || this.state === 'trans' ? this.X1 - 24 : this.X - 26;
    if (this.state !== 'sunk' && p.x > front) { p.x = front; if (p.body.velocity.x > 0) p.body.setVelocityX(0); }
    if (this.state === 'intro') this.updIntro(t);
    else if (this.state === 'p1' || this.state === 'p2') this.updBrain(time);
    else if (this.state === 'trans') this.updTrans(t);
    else if (this.state === 'dying') this.updDying(t);
    this.updOrgan(time);
    runHazards(this, this.GY);
    this.crawlers = this.crawlers.filter(c => c.active);
    this.updSmoke(time);
    this.drawHud();
    this.layout();
  }

  updIntro(t) {
    const sc = this.scene;
    this.eyes.setVisible(t > 400 && Math.floor(t / 110) % 2 === 0);
    if (t > 900 && !this.slam1) { this.slam1 = true; this.tail.ai = 0; sc.fx.shake(160, 0.008); sc.sfx?.play('thump', 1); this.glass.setFrame(1); this.glass.stage = 1; }
    if (t > 1200 && !this.roar) { this.roar = true; this.tail.ai = 2; sc.sfx?.play('queen-roar', 1); sc.fx.shake(500, 0.004); }
    if (t > 2100) {
      this.eyes.setVisible(false);
      this.state = 'p1'; this.t0 = this.p1At = sc.time.now; this.glass.body.enable = true;
      this.act = null; this.nextAct = sc.time.now + 700; this.seq = 0;
    }
  }

  // ------------------------------------------------------------------ attacks
  updBrain(time) {
    const sc = this.scene, p = sc.player, p2 = this.state === 'p2';
    if (!this.act) {
      if (time < this.nextAct) return;
      const order = p2 ? ['beam', 'lunge', 'summon', 'needles', 'lunge', 'acid'] : ['beam', 'acid', 'needles'];
      let a = order[this.seq++ % order.length];
      if (a === 'summon' && (this.cans[0].dead || this.crawlers.length >= 2)) a = 'acid';
      if (a === 'lunge' && p.x < this.X - 110) a = 'needles';
      this.act = a; this.actT = time; this.fired = 0;
      if (a === 'beam') { this.lock = this.beamAim(); sc.sfx?.play('sniper-charge', 0.9); }
      if (a === 'lunge') { this.fr = 2; sc.sfx?.play('xeno-screech', 1); this.homeX = this.X; }
      if (a === 'needles') { this.tail.ai = 0; this.nlock = null; }
    }
    const A = this.act, e = time - this.actT, g = this.sight;
    if (A === 'beam') {
      const TELL = p2 ? 700 : 1000;
      if (e < TELL) {                                         // charge: growing cyan orb + a dotted aim line
        this.charge.setVisible(true).setFrame(Math.min(2, Math.floor(e / (TELL / 3))));
        g.clear();
        if (Math.floor(e / 80) % 2 === 0) {
          const [mx, my] = this.L(MUZ);
          g.fillStyle(0x46dcd8, 1);
          for (let d = 12; d < 460; d += 8) g.fillRect(Math.round(mx - Math.cos(this.lock) * d), Math.round(my + Math.sin(this.lock) * d), 2, 1);
        }
      } else {
        g.clear(); this.charge.setFrame(2).setVisible(Math.floor(e / 50) % 2 === 0);
        const shots = p2 ? 9 : 8;
        if (this.fired < shots && e > TELL + this.fired * 55) {
          const [mx, my] = this.L(MUZ), a = this.lock, sp = 260;
          const b = hazard(sc, mx - 4, my, 'b3-bolt', 55, 'b3-bolt-fizz');
          if (b) { b.setRotation(-a); b.body.setSize(6, 4); b.body.setVelocity(-Math.cos(a) * sp, Math.sin(a) * sp); this.haz.push({ kind: 'bolt', s: b }); }
          if (this.fired === 0) sc.sfx?.play('laser-bolt', 1);
          this.fired++;
        }
        if (this.fired >= shots) { this.charge.setVisible(false); this.end(time, p2 ? 500 : 900); }
      }
    } else if (A === 'acid') {
      const n = p2 ? (this.cans[1].dead ? 2 : 4) : 3;
      if (e > 250 && this.fired < n && e > 250 + this.fired * 160) {
        const base = Phaser.Math.Clamp(p.x, sc.cameras.main.scrollX + 18, this.X - 20);
        const off = [-40, 40, -90, 90][this.fired], tx = base + off;
        if (tx > sc.cameras.main.scrollX + 12 && tx < this.X - 16) {
          const [hx, hy] = this.L(MOUTH);
          lob(this, this.GY, hx, hy, tx, 'b3-acid', 'b3-acid-wobble', { T: 1.1, g: 480, size: [6, 6], armY: 30, spin: 8,
            onLand: (x) => { sc.fx.dust(x, this.GY, 1); sc.fx.explode(x, this.GY - 6, 0.6); sc.sfx?.play('goo', 0.6); } });
        }
        if (this.fired === 0) sc.sfx?.play('goo', 0.8);
        this.fired++;
      }
      if (this.fired >= n && e > 900) this.end(time, p2 ? 250 : 700);
    } else if (A === 'needles') {
      if (e < 550) { this.tail.ai = Math.floor(e / 140) % 2 ? 0 : 1; if (!this.nlock && e > 100) this.nlock = this.needleAim(); }
      else if (this.fired < 3 && e > 550 + this.fired * 110) {
        this.tail.ai = 4; const tp = this.tailTip(), a = this.nlock ?? this.needleAim(), sp = 200;
        const b = hazard(sc, tp.x, tp.y, 'b3-needle', 55);
        if (b) { b.setRotation(Math.atan2(Math.sin(a), -Math.cos(a))); b.body.setSize(5, 4); b.body.setVelocity(-Math.cos(a) * sp, Math.sin(a) * sp); this.haz.push({ kind: 'bolt', s: b }); }
        sc.sfx?.play('enemy-shot', 0.8); this.fired++;
      } else if (this.fired >= 3 && e > 1100) { this.tail.ai = 2; this.end(time, 500); }
    } else if (A === 'summon') {
      if (e < 400) this.eyes.setVisible(Math.floor(e / 80) % 2 === 0);
      else if (!this.fired) {
        this.fired = 1; this.eyes.setVisible(false); sc.sfx?.play('xeno-screech', 1);
        { const aim = !this.aimedOnce && Math.random() < 0.4; this.aimedOnce = true; this.spitVolley(3, aim); }   // the first summon may send a glob straight at you                                   // acid rains while the crawlers come
        for (let i = 0; i < 2; i++) sc.time.delayedCall(i * 450, () => {
          if (!this.fighting() || !ROSTER3.xeno) return;
          const c = new ROSTER3.xeno(sc, this.X + 60 + i * 20, this.GY - 2);
          sc.enemies.add(c); this.crawlers.push(c); sc.fx.dust(c.x, this.GY, 1.2);
        });
      } else if (e > 1300) this.end(time, 400);
    } else if (A === 'lunge') {
      // tell: crouch + screech (450 ms), dash 60 px, claws rake the ground in front, recover, walk back
      const TW = 280;                                          // windup (rear back + screech)
      if (e < TW) { this.dy = Math.round(e / TW * 3); this.X = this.homeX + Math.round(e / TW * 8); }
      else if (e < TW + 300) {
        this.X = this.homeX + 8 - 68 * ((e - TW) / 300);
        if (!this.fired) {
          this.fired = 1; sc.sfx?.play('xeno-pounce', 1); sc.fx.shake(120, 0.006);
          // the claw rake is a real low hazard (eBullets, invisible): it skims the floor ahead of her - jump it or back off
          const c = hazard(sc, this.X + 4, this.GY - 10, 'b3-shards', 44);
          if (c) { c.setVisible(false); c.body.setSize(26, 18); c.body.setVelocity(-70, 0); this.claw = c; sc.time.delayedCall(160, () => c.active && c.body && c.body.setVelocity(-280, 0)); this.haz.push({ kind: 'bolt', s: c }); }
        }
        if (Math.random() < 0.5) sc.fx.dust(this.X + 10, this.GY, 1);
      } else if (e < TW + 700) { this.dy = 0; if (this.claw && this.claw.active) { this.claw.destroy(); } this.claw = null; }
      else {
        this.fr = this.organ.crack ? 1 : 0;
        this.X = Math.min(this.homeX, this.X + 90 * sc.game.loop.delta / 1000);
        if (this.X >= this.homeX) { this.end(time, 250); if (Math.random() < 0.5) this.spitVolley(2); }   // parting spit
      }
    }
  }
  spitVolley(n, aimed) {
    const sc = this.scene, p = sc.player;
    for (let i = 0; i < n; i++) sc.time.delayedCall(i * 170, () => {
      if (this.state !== 'p2') return;
      const base = Phaser.Math.Clamp(p.x, sc.cameras.main.scrollX + 18, this.X - 20), tx = base + (aimed ? [0, -52, 52] : [-44, 44, -96])[i];   // aimed: the first glob lands ON you (1.1 s mark: step off)
      if (tx < sc.cameras.main.scrollX + 12 || tx > this.X - 16) return;
      const [hx, hy] = this.L(MOUTH);
      lob(this, this.GY, hx, hy, tx, 'b3-acid', 'b3-acid-wobble', { T: 1.1, g: 480, size: [6, 6], armY: 30, spin: 8,
        onLand: (x) => { sc.fx.dust(x, this.GY, 1); sc.fx.explode(x, this.GY - 6, 0.6); sc.sfx?.play('goo', 0.6); } });
    });
  }
  end(time, gap) { this.act = null; this.nextAct = time + gap; this.sight.clear(); this.charge.setVisible(false); this.dy = 0; }
  beamAim() {   // locked at the tell start, at the top of a standing player's head (prone ducks under it)
    const p = this.scene.player, [mx, my] = this.L(MUZ);
    return Phaser.Math.Clamp(Math.atan2((p.y - 34) - my, mx - p.x), -0.2, 0.55);
  }
  needleAim() {
    const p = this.scene.player, tp = this.tailTip();
    return Phaser.Math.Clamp(Math.atan2((p.y - 34) - tp.y, tp.x - p.x), -0.3, 1.0);
  }

  // ------------------------------------------------------------------ phase change: the glass explodes
  shatter() {
    const sc = this.scene, g = this.glass;
    g.dead = true; g.body.enable = false; g.setVisible(false);
    this.state = 'trans'; this.t0 = this.transAt = sc.time.now; this.act = null; this.end(sc.time.now, 0);
    sc.sfx?.play('glass', 1); sc.sfx?.play('boom-big', 0.8); sc.cameras.main.flash(140, 200, 255, 250); sc.fx.hitstop(90);
    for (let i = 0; i < 40; i++) sc.fx.part?.('b3-shards', [Math.floor(rnd(0, 8))], g.x + rnd(-80, 80), g.y + rnd(-70, 70), rnd(-240, 60), -rnd(40, 260), { g: 700, life: rnd(700, 1200), depth: 64, bounce: 0.3, spin: rnd(-10, 10) });
    for (let i = 0; i < 6; i++) sc.time.delayedCall(i * 60, () => sc.fx.dust(g.x - 80 + i * 30, this.GY, 1.4));
    this.win.setDepth(28.5);                                   // the empty frame is now behind her
  }
  updTrans(t) {
    const sc = this.scene;
    if (t < 400) return;
    if (!this.roar2) { this.roar2 = true; sc.sfx?.play('queen-roar', 1); sc.fx.shake(600, 0.006); }
    this.X = Math.max(this.X2, this.X1 - (this.X1 - this.X2) * Math.min(1, (t - 400) / 700));
    if (Math.floor(t / 230) !== this.lastStep) { this.lastStep = Math.floor(t / 230); sc.fx.dust(this.X + 30, this.GY, 1.1); sc.fx.dust(this.X + 120, this.GY, 1.1); }
    if (t > 1500) {
      this.state = 'p2'; this.organ.body.enable = true; this.capT = 0;
      this.act = null; this.nextAct = sc.time.now + 300; this.seq = 0;
    }
  }

  updOrgan(time) {
    const o = this.organ; if (o.dead) return;
    const hot = time < (this.kick || 0) || (this.act === 'beam' && Math.floor(time / 90) % 2);
    o.setFrame((o.crack || 0) * 2 + (hot ? 1 : 0)).setVisible(this.state !== 'sunk');
  }
  drawHud() {
    const show = this.fighting() && !this.organ.dead;
    // one bar for the whole fight: glass (first half) then heart (second half)
    const hp = this.state === 'p1' ? this.organ.maxHp + this.glass.hp : this.organ.hp;
    this.bar.set(hp, this.organ.maxHp + this.glass.maxHp, show);
  }
  updSmoke(time) {
    if (time < (this.nextSmoke || 0) || !this.smokeSpots.length) return;
    this.nextSmoke = time + 200;
    const s = pick(this.smokeSpots), x = this.X + s.dx, y = this.top + s.dy;
    if (s.goo) this.scene.fx.part?.('b3-shards', [3], x, y, rnd(-20, 20), rnd(10, 40), { g: 300, life: 500, depth: 64 });
    else this.scene.fx.smokePuffs?.(x, y, 1, 3);
  }

  // ------------------------------------------------------------------ death (the finale)
  die() {
    const sc = this.scene, o = this.organ;
    this.state = 'dying'; this.t0 = this.diedAt = sc.time.now; this.booms = 0; this.act = null; this.end(sc.time.now, 0);
    o.dead = true; o.body.enable = false; o.setVisible(false); this.cans.forEach(c => (c.body.enable = false));
    this.haz.forEach(h => (h.dead = true)); this.bar.set(0, 1, false); this.fr = 1; sc.tweens.add({ targets: this.dim, alpha: 0, duration: 2500 });
    this.crawlers.forEach(c => c.active && (c.die ? c.die() : c.destroy()));
    sc.fx.hitstop(200); sc.cameras.main.flash(200, 200, 255, 250);
    sc.fx.explode(o.x, o.y, 1.6); chunks3(sc, o.x, o.y, 14, 1.3);
    for (let i = 0; i < 24; i++) sc.fx.part?.('b3-shards', [Math.floor(rnd(0, 8))], o.x, o.y, rnd(-200, 200), -rnd(60, 280), { g: 600, life: 900, depth: 64, bounce: 0.3 });
    sc.sfx?.play('queen-roar', 1); sc.addScore(20000);
  }
  updDying(t) {
    const sc = this.scene, fx = sc.fx;
    if (t < 3200) {                                          // thrashing
      this.jit = Math.floor(t / 45) % 2 ? 2 : -2;
      this.tail.ai = Math.floor(t / 120) % 5;
      if (t > this.booms * 110) {
        this.booms++;
        fx.explode(this.X + rnd(10, 150), Math.min(this.GY - 6, this.top + rnd(10, 140)), this.booms % 5 === 0 ? 1.3 : rnd(0.55, 0.75));
        if (this.booms % 2) chunks3(sc, this.X + rnd(20, 140), this.top + rnd(20, 120), 2, 1.1);
        if (this.booms % 4 === 0) sc.sfx?.play('goo', 0.8);
        sc.cameras.main.shake(100, 0.007);
      }
    }
    if (t > 1600) {                                          // collapses and dissolves into the floor
      const k = Math.min(1, (t - 1600) / 2000);
      this.dy = 110 * k * k;
      const vis = Math.max(0, Math.min(FH, this.GY - this.top));
      this.body.setCrop(0, 0, FW, vis); this.cannonGone = vis < 90; this.tailGone = vis < 110;
      this.cans.forEach(c => c.setVisible(vis > 120));
      if (Math.random() < 0.6) fx.dust(this.X + rnd(0, 150), this.GY, rnd(1, 1.5));
      if (Math.random() < 0.4) fx.part?.('b3-shards', [3], this.X + rnd(20, 140), this.GY - 4, rnd(-40, 40), -rnd(40, 120), { g: 400, life: 600, depth: 64 });
    }
    if (!this.whiteout && t > 3500) {
      this.whiteout = true; sc.cameras.main.flash(900, 255, 255, 255); fx.explode(this.X + 70, this.GY - 30, 1.6); fx.explode(this.X + 30, this.GY - 60, 1.3);
      sc.sfx?.play('boom-big');
    }
    if (t > 4200) {
      this.state = 'sunk'; this.active = false; this.body.setVisible(false);
      this.smokeSpots = [{ dx: 40, dy: 140 }, { dx: 90, dy: 140 }];
      sc.bossDefeated(this);
    }
  }
}
