// STAGE 02 boss: B-02 WARDEN, an olive armoured walker mech (ref/levels/level2 boss.png).
//  Intro: stomps in from the right (WARNING from the HUD), visor flares.
//  Phase 1: walks the arena. Six-barrel gatling arm (aim LOCKED at the tell start, 5-round burst: step or prone),
//           quad missile volley onto blinking ground marks (bracketing you), stomp shockwave if you crowd it (jump).
//           After every volley it crouches to cool and its chest opens: the reactor core is the weak point
//           (armoured/ricochet otherwise, max 10 damage per vent). The gatling arm can be shot off (16 HP).
//  Phase 2: (core at half) the armour blows apart; it stays crouched with the core exposed, fires faster, stomps more.
//           Core damage is capped at 12 per 3 s (overload flashes) so every weapon takes a few windows.
//  Death:   core overload, chain explosions, the mech topples forward and sinks, white-out, bossDefeated().
// Art: assets/boss2/* built by art/raw/boss2/build_boss2.py.
import { rnd, pick, groundLine, part, zone, placeZone, tink, chunks, flash, tick, BossBar, hazard, runHazards, lob } from './bosskit.js';

const FW = 159, FH = 153, BOT = 152;                        // body frame (2px outline); row 152 sits on the ground
const PIV = [[69, 68], [60, 90], [67, 90]];                 // gun shoulder pivot per body frame [stand, crouch, broken]
const WAR = [[99, 6], [94, 19], [94, 19]];                  // warhead overlay top-left per frame
const CORE = [[78, 54], [69, 76], [76, 76]];                // reactor centre per frame
const EYE = [[73, 30], [65, 51], [65, 51]];
const FOOT = [7, 1, 1];
const SINK = 3;                                             // feet sunk 3px into the deck (the pod lid is trimmed in the art for HUD clearance)                                     // leftmost foot pixel per frame (player push-out)
const GUN_A0 = -10, GUN_N = 9, GUN_TIP = 66;

export class Boss2 {
  constructor(scene, x) {
    const sc = this.scene = scene; this.active = true;
    this.GY = groundLine(sc, x + 60);
    this.HX = x - 62;                                        // home: frame left edge; the core's 45-degree spot stays inside the arena
    this.X = this.HX + 170; this.bob = 0;
    this.state = 'enter'; this.t0 = this.spawnAt = sc.time.now; this.fr = 0;
    this.haz = [];
    this.body = sc.add.image(0, 0, 'b2-body', 0).setOrigin(0, 0).setDepth(30);
    this.war = sc.add.image(0, 0, 'b2-warheads').setOrigin(0, 0).setDepth(30.5);
    this.gun = part(this, sc.physics.add.sprite(0, 0, 'b2-gun', 2).setDepth(31), 16, 'gun');
    this.gun.body.setSize(62, 18); this.gun.body.enable = false; this.gun.ang = 0; this.gun.phase = 'idle';
    this.core = part(this, sc.physics.add.sprite(0, 0, 'b2-core', 0).setDepth(30.8).setVisible(false), 44, 'core');   // big orange disc while the chest is open
    this.core.body.setSize(44, 40); this.core.body.setOffset((21 - 44) / 2, (21 - 40) / 2); this.core.body.enable = false;
    this.armor = [zone(this, 0, 0, 10, 10)];
    this.armor.forEach(z => (z.body.enable = false));
    this.eye = sc.add.image(0, 0, 'boss-lamp', 1).setDepth(31).setVisible(false);
    this.podLamps = [0, 1].map(() => sc.add.image(0, 0, 'boss-lamp', 1).setDepth(31).setVisible(false));
    this.bar = new BossBar(sc, 'B-02 WARDEN');
    this.smokeSpots = [];
    this.layout();
  }

  // ------------------------------------------------------------------ placement
  get top() { return this.GY - BOT + SINK + Math.round(this.bob); }
  L(p) { return [Math.round(this.X + p[0]), this.top + p[1]]; }
  G(p) { return [Math.round(this.X + p[0]), this.top - SINK + p[1]]; }   // pre-sink geometry (aim lock reference)
  layout() {
    const f = this.fr, t = this.top, X = Math.round(this.X);
    this.body.setFrame(f).setPosition(X, t);
    this.body.setCrop(0, 0, FW, Math.max(0, Math.min(FH, this.GY - t)));      // clip the sunk feet at the deck line
    const [wx, wy] = this.L(WAR[f]); this.war.setPosition(wx, wy).setCrop(0, Math.max(0, 8 - WAR[f][1]), 27, 22);
    const [px, py] = this.L(PIV[f]);
    const g = this.gun, a = g.ang * Math.PI / 180;
    if (!g.dead) {
      g.setPosition(px + Math.cos(a) * (g.rk || 0), py - Math.sin(a) * (g.rk || 0));
      g.setFrame(Phaser.Math.Clamp(Math.round((g.ang - GUN_A0) / 5), 0, GUN_N - 1));
      g.body.setOffset(75 - 62, 75 - 9 + Math.round(Math.sin(a) * 26));        // barrel box follows the aim
    }
    const [cx, cy] = this.L(CORE[f]); this.core.setPosition(cx, cy);
    this.core.setVisible(this.coreOpen() && !this.core.dead).setFrame(Math.floor(this.scene.time.now / 110) % 2);
    const [ex, ey] = this.L(EYE[f]); this.eye.setPosition(ex, ey);
    this.podLamps.forEach((l, i) => l.setPosition(wx + 7 + i * 12, wy + 3));
    // armour: upper torso above the core only - nothing below it, so diagonal shots from the arena reach the core
    placeZone(this.armor[0], X + 38, t + 12, 80, Math.max(4, CORE[f][1] - 16 - 12));
  }

  // ------------------------------------------------------------------ damage
  fighting() { return this.state === 'p1' || this.state === 'p2' || this.state === 'trans'; }
  coreOpen() { return this.state === 'p2' || (this.state === 'p1' && this.act === 'vent' && this.fr === 1); }
  hit(s, n, bl) {
    if (!s.active || s.dead || !this.fighting()) return;
    const sc = this.scene, now = sc.time.now;
    if (s.kind === 'core') {
      if (!this.coreOpen()) { tink(this, bl ? bl.x : s.x - 10, bl ? bl.y : s.y); return; }
      // per-window cap: vents in phase 1, 3 s windows in phase 2 (overload = ricochet until the window resets)
      if (this.state === 'p2' && now > (this.capT || 0)) { this.capT = now + 3000; this.win = 0; }
      const cap = this.state === 'p2' ? 12 : 10;
      n = Math.min(n, Math.max(0, cap - (this.win || 0)));
      if (!n) { tink(this, bl ? bl.x : s.x - 10, bl ? bl.y : s.y); if (Math.random() < 0.2) sc.fx.spark?.(s.x - 8, s.y, 3, 'fire', 120, 20); return; }
      this.win = (this.win || 0) + n;
      s.hp -= n; sc.addScore(n * 50);
      if (now > (this.nextBodyFlash || 0)) { this.nextBodyFlash = now + 220; flash(sc, [this.body], false); }
      sc.fx.spark?.(s.x - 8 + rnd(-3, 3), s.y + rnd(-4, 4), 3, 'fire', 120, 20);
      tick(this, s.x - 14, s.y - 18, s.hp, s.maxHp);
      sc.sfx?.play('hit');
      if (this.state === 'p1' && s.hp <= s.maxHp / 2) this.toPhase2();
      if (s.hp <= 0) this.die();
      return;
    }
    s.hp -= n;
    if (now > (s.nextFlash || 0)) { s.nextFlash = now + 150; flash(sc, [s], false); }
    sc.sfx?.play('hit');
    if (s.hp <= 0 && s.kind === 'gun') this.killGun();
  }
  killGun() {
    const sc = this.scene, g = this.gun;
    g.dead = true; g.body.enable = false; g.phase = 'idle';
    const [px, py] = this.L(PIV[this.fr]);
    sc.fx.explode(px - 30, py, 1.2); sc.fx.explode(px - 8, py - 4, 0.7); chunks(sc, 'b2-chunks', px - 20, py, 8, 1.1);
    sc.tweens.add({ targets: g, y: this.GY + 30, angle: -60, duration: 800, ease: 'Quad.easeIn', onComplete: () => { sc.fx.dust(g.x, this.GY, 1.3); g.setVisible(false); } });
    this.smokeSpots.push({ dx: PIV[0][0] - 4, dy: PIV[0][1] - 6, fire: true });
    sc.addScore(1000);
  }

  // ------------------------------------------------------------------ main loop
  update(time) {
    const sc = this.scene, p = sc.player; if (!p) return;
    const t = time - this.t0;
    // the mech is solid: no walking through its legs
    // push-out: the sheep's body (half-width ~9, sprite ~20) never overlaps the front claw
    const front = this.X + FOOT[this.fr] - 20;
    if (this.state !== 'sunk' && this.state !== 'dying' && p.x > front) { p.x = front; if (p.body.velocity.x > 0) p.body.setVelocityX(0); }

    if (this.state === 'enter') this.updEnter(t);
    else if (this.state === 'wake') this.updWake(t);
    else if (this.state === 'p1' || this.state === 'p2') { this.updGun(time); this.updBrain(time); }
    else if (this.state === 'trans') this.updTrans(t);
    else if (this.state === 'dying') this.updDying(t);

    this.drawHud(time);
    runHazards(this, this.GY);
    this.updSmoke(time);
    this.layout();
  }

  stomp(big) {
    const sc = this.scene;
    sc.fx.shake(big ? 200 : 110, big ? 0.01 : 0.005); sc.sfx?.play(big ? 'thump' : 'land', big ? 1 : 0.9);
    sc.fx.dust(this.X + 20, this.GY, 1.4); sc.fx.dust(this.X + 110, this.GY, 1.2);
  }
  // step toward a target x with a heavy bob + stomp
  walkTo(x, time, speed) {
    const dt = this.scene.game.loop.delta / 1000;
    const d = x - this.X; if (Math.abs(d) < 1) { this.X = x; this.bob = 0; return true; }
    this.X += Math.sign(d) * Math.min(Math.abs(d), speed * dt);
    const ph = (time / 520) % 1; this.bob = -Math.abs(Math.sin(ph * Math.PI)) * 3;
    if (Math.floor(time / 520) !== this.lastStep) { this.lastStep = Math.floor(time / 520); this.stomp(false); }
    return false;
  }

  updEnter(t) {
    if (this.walkTo(this.HX, this.scene.time.now, 70)) { this.state = 'wake'; this.t0 = this.scene.time.now; this.stomp(true); }
  }
  updWake(t) {
    const sc = this.scene;
    this.eye.setVisible(Math.floor(t / 90) % 2 === 0);
    if (t > 900) {
      this.eye.setVisible(false);
      this.state = 'p1'; this.t0 = this.p1At = sc.time.now;
      this.gun.body.enable = true; this.armor.forEach(z => (z.body.enable = true));
      this.act = null; this.nextAct = sc.time.now + 600; this.seq = 0;
    }
  }

  // ------------------------------------------------------------------ attack brain
  updBrain(time) {
    const sc = this.scene, p = sc.player, p2 = this.state === 'p2';
    if (!this.act) {
      if (time < this.nextAct) { this.bob = 0; return; }
      const close = p.x > this.X - 70;
      const order = p2 ? ['gat', 'stomp', 'volley', 'walk'] : ['volley', 'gat', 'volley', 'walk'];
      let a = order[this.seq++ % order.length];
      if (close && a !== 'volley' && Math.random() < 0.7) a = 'stomp';     // crowding it earns a stomp, never skips a vent
      if (a === 'gat' && this.gun.dead) a = p2 ? 'stomp' : 'walk';
      this.startAct(a, time);
    }
    const A = this.act, e = time - this.actT;
    if (A === 'walk') {
      if (this.walkTo(this.walkX, time, p2 ? 60 : 40)) this.endAct(time, p2 ? 300 : 500);
    } else if (A === 'gat') {
      if (this.gun.dead) return this.endAct(time, 200);
      if (this.gun.phase === 'idle') this.endAct(time, p2 ? 350 : 600);
    } else if (A === 'volley') {
      const on = Math.floor(e / 70) % 2 === 0;
      if (e < 700) { this.podLamps.forEach(l => l.setVisible(on)); this.war.setVisible(true); }
      else if (!this.fired) {
        this.fired = true; this.podLamps.forEach(l => l.setVisible(false)); this.war.setVisible(false);
        const base = Phaser.Math.Clamp(p.x, sc.cameras.main.scrollX + 18, this.X - 14);
        // bracket the player; marks that would fall off the arena are dropped, never piled onto the edge
        const xs = [base - 38, base + 38, base - 86, base + 86].filter(v => v > sc.cameras.main.scrollX + 12 && v < this.X - 14);
        const [wx, wy] = this.L(WAR[this.fr]);
        xs.forEach((tx, i) => sc.time.delayedCall(i * 120, () => {
          if (!this.fighting()) return;
          sc.fx.muzzle(wx + 7 + (i % 2) * 12, wy, 0, -1, 1);
          lob(this, this.GY, wx + 7 + (i % 2) * 12, wy + 2 + Math.floor(i / 2) * 9, tx, 'b2-missile', 'b2-missile-burn', { T: 1.3, g: 440, size: [5, 10], armY: 26 });
          sc.sfx?.play('tank', 0.7);
        }));
        sc.fx.smokePuffs?.(wx + 13, wy, 3, 6);
      } else if (e > 1500) {
        if (!p2) { this.act = 'vent'; this.actT = time; this.win = 0; this.fr = 1; this.core.body.enable = true; if (!this.gun.dead) this.gun.body.enable = false; this.stomp(false); sc.sfx?.play('land', 0.8); }   // gun arm braces while venting
        else this.endAct(time, 300);
        this.war.setVisible(true); this.fired = false;
      }
    } else if (A === 'vent') {                               // crouched, chest open: punish window
      if (Math.random() < 0.08) sc.fx.smokePuffs?.(this.X + 40 + rnd(0, 60), this.top + 30, 1, 4);
      if (e > 2400 || (this.win || 0) >= 10) {
        this.fr = 0; this.core.body.enable = false; this.stomp(false); if (!this.gun.dead) this.gun.body.enable = true;
        if ((this.win || 0) >= 10) sc.fx.spark?.(this.core.x - 8, this.core.y, 8, 'fire', 150, 30);
        this.endAct(time, 500);
      }
    } else if (A === 'stomp') {
      if (e < 450) this.bob = -Math.round(e / 450 * 6);                  // rears up: the tell
      else if (!this.fired) {
        this.fired = true; this.bob = 0; this.stomp(true);
        const n = p2 ? 2 : 1;
        for (let i = 0; i < n; i++) sc.time.delayedCall(i * 700, () => {
          if (!this.fighting()) return;
          const w = hazard(sc, this.X + 6, this.GY - 8, 'b2-wave', 44, 'b2-wave-roll');
          // starts slow off the foot (a beat to jump), then races across the floor
          if (w) { w.body.setSize(18, 10); w.body.setVelocity(-55, 0); this.haz.push({ kind: 'roll', s: w });
            sc.time.delayedCall(320, () => w.active && w.body && w.body.setVelocity(-(p2 ? 160 : 145), 0)); }
        });
      } else if (e > (p2 ? 1300 : 800)) { this.fired = false; this.endAct(time, 300); }
    }
  }
  startAct(a, time) {
    const sc = this.scene, p = sc.player;
    this.act = a; this.actT = time; this.fired = false;
    if (a === 'walk') {
      const lo = this.HX - 40, hi = this.HX;
      this.walkX = this.X > (lo + hi) / 2 ? lo + rnd(0, 15) : hi - rnd(0, 10);
    } else if (a === 'gat') {
      const g = this.gun; g.phase = 'charge'; g.until = time + 700; g.lock = this.aimAt(); sc.sfx?.play('gatling-spin', 0.8);
    }
  }
  endAct(time, gap) { this.act = null; this.nextAct = time + gap; this.bob = 0; }

  aimAt() {
    const p = this.scene.player, [px, py] = this.G(PIV[this.fr]);
    return Phaser.Math.Clamp(Math.atan2((p.y - 34) - py, px - p.x) * 180 / Math.PI, GUN_A0, 25);   // shallow max depression: the strip under the gun is a safe pocket
  }
  updGun(time) {
    const g = this.gun, sc = this.scene; if (g.dead) return;
    const dt = sc.game.loop.delta / 1000;
    g.rk = Math.max(0, (g.rk || 0) - dt * 40);
    const want = g.phase === 'idle' ? this.aimAt() : g.lock;
    if (g.phase !== 'fire') g.ang += Phaser.Math.Clamp(want - g.ang, -dt * (g.phase === 'idle' ? 40 : 120), dt * (g.phase === 'idle' ? 40 : 120));
    if (g.phase === 'charge') {
      // tell: barrel shakes and the muzzle sparks while it spins up
      g.x += (Math.floor(time / 40) % 2 ? 1 : -1);
      if (Math.random() < 0.4) { const m = this.tip(); sc.fx.spark?.(m.x, m.y, 1, 'fire', 50); }
      if (time > g.until) { g.phase = 'fire'; g.shots = 0; g.next = time; }
    } else if (g.phase === 'fire' && time >= g.next) {
      const m = this.tip(), sp = this.state === 'p2' ? 165 : 150;
      sc.fireEnemy(m.x + m.dx * 4, m.y + m.dy * 4, m.dx * sp, m.dy * sp); sc.fx.muzzle(m.x + m.dx * 3, m.y + m.dy * 3, m.dx, m.dy, 0.8);   // small flash past the tip: the barrel stays readable sc.sfx?.play('gatling', 0.7);
      g.rk = 3; g.shots++; g.next = time + 85;
      if (g.shots >= (this.state === 'p2' ? 6 : 5)) g.phase = 'idle';
    }
  }
  tip() {
    const g = this.gun, a = g.ang * Math.PI / 180, [px, py] = this.L(PIV[this.fr]);   // bullets leave the DRAWN muzzle
    return { x: px - Math.cos(a) * GUN_TIP, y: py - 2 + Math.sin(a) * GUN_TIP, dx: -Math.cos(a), dy: Math.sin(a) };
  }

  // ------------------------------------------------------------------ phase change
  toPhase2() {
    const sc = this.scene;
    this.state = 'trans'; this.t0 = this.transAt = sc.time.now; this.booms = 0;
    this.act = null; this.core.body.enable = false; this.podLamps.forEach(l => l.setVisible(false));
    if (this.gun.phase !== 'idle') this.gun.phase = 'idle';
  }
  updTrans(t) {
    const sc = this.scene;
    if (t > this.booms * 170 && this.booms < 9) {
      this.booms++;
      sc.fx.explode(this.X + rnd(20, 130), this.top + rnd(15, 120), this.booms % 3 ? 0.7 : 1.3);
      chunks(sc, 'b2-chunks', this.X + rnd(30, 120), this.top + rnd(20, 100), 3);
    }
    if (!this.broke && t > 500) {
      this.broke = true; this.fr = 2; this.stomp(true); sc.cameras.main.flash(120, 255, 240, 200);
      chunks(sc, 'b2-chunks', this.X + 70, this.top + 70, 14, 1.2);
      this.smokeSpots.push({ dx: 100, dy: 10 }, { dx: 128, dy: 30, fire: true }, { dx: 50, dy: 60, spark: true }, { dx: 110, dy: 90, spark: true });
    }
    if (t > 1600) {
      this.state = 'p2'; this.core.body.enable = true; this.act = null; this.nextAct = sc.time.now + 300; this.seq = 0;
      this.capT = 0; this.win = 0;
    }
  }

  // ------------------------------------------------------------------ hud / ambience
  drawHud(time) {
    const c = this.core, show = this.fighting() && !c.dead;
    this.bar.set(c.hp, c.maxHp, show);
    if (this.state === 'p1' || this.state === 'p2') {
      if (this.coreOpen() && Math.random() < 0.15) this.scene.fx.spark?.(c.x + rnd(-6, 6), c.y + rnd(-6, 6), 1, 'fire', 60, 20);
    }
  }
  updSmoke(time) {
    if (time < (this.nextSmoke || 0) || !this.smokeSpots.length) return;
    this.nextSmoke = time + (this.state === 'p2' ? 140 : 220);
    const s = pick(this.smokeSpots), fx = this.scene.fx, x = this.X + s.dx, y = this.top + s.dy;
    fx.smokePuffs?.(x, y, 1, 3);
    if (s.fire && Math.random() < 0.6) fx.embers?.(x, y, 2, 3);
    if (s.spark && Math.random() < 0.5) fx.spark?.(x, y, 3, 'fire', 110, 30);
  }

  // ------------------------------------------------------------------ death
  die() {
    const sc = this.scene;
    this.state = 'dying'; this.t0 = this.diedAt = sc.time.now; this.booms = 0; this.act = null;
    this.core.dead = true; this.core.body.enable = false; this.gun.body.enable = false; this.gun.phase = 'idle';
    this.armor.forEach(z => (z.body.enable = false)); this.bar.set(0, 1, false);
    this.haz.forEach(h => (h.dead = true));
    sc.fx.hitstop(160); sc.cameras.main.flash(160, 255, 255, 255);
    sc.fx.explode(this.core.x, this.core.y, 1.6); chunks(sc, 'b2-chunks', this.core.x, this.core.y, 12, 1.3);
    sc.addScore(10000);
  }
  updDying(t) {
    const sc = this.scene, fx = sc.fx;
    if (t < 2400 && t > this.booms * 100) {
      this.booms++;
      fx.explode(this.X + rnd(15, 140), Math.min(this.GY - 6, this.top + rnd(10, 140)), this.booms % 6 === 0 ? 1.3 : rnd(0.55, 0.72));
      if (this.booms % 2) chunks(sc, 'b2-chunks', this.X + rnd(20, 130), this.top + rnd(20, 120), 2, 1.1);
      sc.cameras.main.shake(100, 0.006);
    }
    if (t > 900 && !this.toppled) {                          // topples forward onto its face
      this.toppled = true;
      if (!this.gun.dead) this.killGun();
      this.war.setVisible(false);
      this.slump = true;                                     // pitches forward as it sinks
    }
    if (t > 1300) {
      const k = Math.min(1, (t - 1300) / 1800);
      this.bob = 60 * k * k; if (this.slump) this.X -= 6 * this.scene.game.loop.delta / 1000;
      const vis = Math.max(0, Math.min(FH, this.GY - this.top));
      this.body.setCrop(0, 0, FW, vis);
      if (Math.random() < 0.5) fx.dust(this.X + rnd(0, 150), this.GY, rnd(0.9, 1.4));
    }
    if (!this.whiteout && t > 2800) { this.whiteout = true; sc.cameras.main.flash(500, 255, 255, 255); fx.explode(this.X + 70, this.GY - 30, 1.6); sc.sfx?.play('boom-big'); }
    if (t > 3300) {
      this.state = 'sunk'; this.active = false;
      this.smokeSpots = [{ dx: 40, dy: 110 }, { dx: 80, dy: 100, fire: true }, { dx: 120, dy: 110 }];
      sc.bossDefeated(this);
    }
  }
}
