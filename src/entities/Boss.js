// Stage 1 boss: THE IRON EAGLE GATE. A fortified bunker-gate that rises out of the boss yard.
//  Phase 1: two "wool-shredder" gatling ball-turrets (aimed 3-round bursts, red-eye telegraph) + a roof mortar
//           launcher (lobs 3 shells, landing spots marked on the ground). Blast door shut, core armoured.
//  Phase 2: (both turrets destroyed) the facade blows apart, the blast door cycles open to expose the reactor eye.
//           While open the core rolls shredder saws along the floor (jump them) or rakes a head-height volley
//           preceded by a laser sight (go prone). Enrages under half HP.
//  Death:   hitstop + flash, chain explosions, debris, the gate sinks back into the ground, white-out, bossDefeated().
// Art: assets/boss/* built by art/raw/boss/build_boss.py. Parts in scene.bossParts expose .damage(n).
import { BossBar } from './bosskit.js';   // shared bottom boss strip (same as stages 2 and 3)
let GY = 168;                                               // arena ground line, read from the level in the constructor
const GUN_A0 = -10, GUN_A1 = 45, GUN_N = 12;                // barrel sheet angles: -10..45 step 5 (+ = down-left)
const RISE = 150;                                           // tower starts fully below the ground line
const rnd = (a, b) => a + Math.random() * (b - a);
const pick = (a) => a[Math.floor(Math.random() * a.length)];

export class BossWall {
  constructor(scene, x) {
    const sc = this.scene = scene; this.active = true;
    const g = sc.groundYAt ? sc.groundYAt(x + 60) : NaN;
    GY = Number.isFinite(g) && g < (sc.level?.height ?? 270) ? g : 168;
    const X = this.X = x + 20, Y = this.Y = GY - 145;      // top-left of the 98x146 tower frame
    this.state = 'rise'; this.t0 = this.spawnAt = sc.time.now; this.rise = RISE; this.enraged = false;
    this.haz = [];                                          // saws / shells / marks we own
    this.smokeSpots = [];

    // foundation plinth sunk into the cliff below the yard; the tower rises out of it
    this.found = sc.add.image(X - 18, GY - 2, 'boss-found').setOrigin(0, 0).setDepth(29);
    this.body = sc.add.image(X, Y, 'boss-body', 0).setOrigin(0, 0).setDepth(30);
    this.core = this.part(sc.physics.add.image(X + 48, Y + 113, 'boss-core', 0).setDepth(30.5), 26, 'core');
    this.core.body.setSize(28, 38).setOffset((19 - 28) / 2, 1); this.core.body.enable = false;
    this.doorL = sc.add.image(X + 30, Y + 91, 'boss-door-l', 0).setOrigin(0, 0).setDepth(31);
    this.doorR = sc.add.image(X + 49, Y + 91, 'boss-door-r', 0).setOrigin(0, 0).setDepth(31);
    this.doorOpen = 0;                                      // 0 shut .. 1 fully retracted
    this.launcher = this.part(sc.physics.add.image(X + 34, Y, 'boss-launcher', 0).setOrigin(0, 0).setDepth(31), 24, 'launcher');
    this.launcher.body.setSize(25, 16).setOffset(3, 3);
    this.turrets = [[16, 50], [16, 77]].map(([dx, dy], i) => {
      const t = this.part(sc.physics.add.sprite(X + dx, Y + dy, 'boss-gun-house', 0).setDepth(32).setVisible(false), 18, 'turret');
      t.body.setSize(34, 20).setOffset(-6, 2); t.spin = 0; t.body.enable = false; t.rk = 0;
      t.barrel = sc.add.sprite(X + dx - 8, Y + dy, 'boss-gun-barrel', 2).setDepth(31.9).setVisible(false);
      t.bx = X + dx; t.by = Y + dy; t.ang = 0; t.idx = i; t.phase = 'idle'; t.next = 0;
      return t;
    });
    // low intake cannon bolted to the tower foot: the phase-1 target you can hit standing or prone (Contra wall rule)
    this.low = this.part(sc.physics.add.sprite(X + 10, GY, 'boss-gun-low', 0).setOrigin(0.5, 1).setDepth(32).setVisible(false), 17, 'low');
    this.low.body.setSize(26, 34).setOffset(1, 1); this.low.body.enable = false; this.low.phase = 'idle'; this.low.next = 0;
    // armour: soaks shots that hit the facade (Contra walls eat bullets)
    this.armor = [
      // upper facade + the pillar BEHIND (right of) the core only. Nothing may sit in front of the doorway at
      // shot height, or horizontal fire from the arena never reaches the core (round-4 blocking bug).
      this.zone(X + 27, Y + 21, 70, 68), this.zone(X + 69, Y + 91, 28, 54),
    ];
    this.doorZone = this.zone(X + 30, Y + 91, 39, 54);
    this.doorZone.damage = (n, bl) => {
      this.tink(bl ? bl.x : this.doorZone.body.x + 2, bl ? bl.y : this.doorZone.body.center.y);
      const c = this.core;
      if (this.state !== 'p2' || c.dead) return;
      c.chip = (c.chip || 0) + n * 0.3;
      if (c.chip >= 1) { const d = Math.floor(c.chip); c.chip -= d; c.hp -= d; this.coreHit(d, true); if (c.hp <= 0) this.kill(c); }
    };
    // boss HP: the shared bottom BossBar (was a small bar over the door frame)
    this.bar = new BossBar(sc, 'IRON EAGLE GATE');
    for (const z of [...this.armor, this.doorZone]) z.body.enable = false;
    // lights (additive glow sprites)
    const G = (lx, ly, fr) => sc.add.image(X + lx, Y + ly, 'boss-lamp', fr).setDepth(33).setVisible(false);   // hard-pixel lit lamp, no additive blur
    this.beacons = [G(22, 17, 1), G(77, 17, 1)];
    this.lamps = [G(33, 89, 3), G(64, 89, 3), G(33, 24, 3), G(64, 24, 3)];
    this.coreGlow = G(48, 113, 1).setDepth(30.6);          // unused (core has baked hot frames)
    this.tubeGlow = [[42, 5], [53, 5], [42, 14], [53, 14]].map(([a, b]) => G(a, b, 1));
    this.sight = sc.add.graphics().setDepth(54);
    this.layout();
  }

  part(s, hp, kind) {
    s.body.setAllowGravity(false).setImmovable(true);
    s.hp = s.maxHp = hp; s.kind = kind; s.dead = false;
    s.damage = (n, bl) => this.hit(s, n, bl);
    this.scene.bossParts.add(s);
    s.body.setAllowGravity(false);
    return s;
  }
  zone(x, y, w, h) {
    const z = this.scene.add.zone(x + w / 2, y + h / 2, w, h);
    this.scene.physics.add.existing(z); this.scene.bossParts.add(z);
    z.body.setAllowGravity(false).setImmovable(true);
    z.armor = true;
    z.damage = (n, bl) => this.tink(bl ? bl.x : z.body.x + 2, bl ? bl.y : z.body.center.y);
    return z;
  }

  // armour hit: small grey ricochet star + two grey chips bouncing back (so the player learns where NOT to shoot)
  tink(x, y) {
    const sc = this.scene, now = sc.time.now;
    if (now < (this.nextTink || 0)) return; this.nextTink = now + 45;
    if (sc.anims.exists('boss-tink')) { const t = sc.add.sprite(Math.round(x), Math.round(y), 'boss-tink', 0).setDepth(70).play('boss-tink'); t.once('animationcomplete', () => t.destroy()); }
    if (sc.fx.part) for (let i = 0; i < 2; i++) sc.fx.part('boss-tink', [2], x, y, -rnd(60, 130), -rnd(20, 90), { g: 500, life: 260, depth: 70, ground: false });
  }

  // ---------------------------------------------------------------- placement / ground clipping during rise & sink
  layout() {
    const r = Math.round(this.rise), clip = (img, top, h) => {
      img.y = top + r;
      const vis = Math.max(0, Math.min(h, GY - img.y));
      if (vis < h) img.setCrop(0, 0, img.frame.realWidth, vis); else img.setCrop();
      img.setVisible(vis > 0 && img.visibleWanted !== false);
    };
    clip(this.body, this.Y, 146);
    this.found.y = GY - 2 + (this.state === 'rise' ? Math.round(r * 0.72) : 0);
    this.doorL.x = this.X + 30 - Math.round(this.doorOpen * 19);
    this.doorR.x = this.X + 49 + Math.round(this.doorOpen * 20);
    for (const [d, w, dir] of [[this.doorL, 19, -1], [this.doorR, 20, 1]]) {
      d.y = this.Y + 91 + r;
      const slid = Math.round(this.doorOpen * w), vis = Math.max(0, Math.min(54, GY - d.y));
      if (slid >= w || vis <= 0) { d.setVisible(false); continue; }
      d.setVisible(true);
      if (dir < 0) d.setCrop(slid, 0, w - slid, vis); else d.setCrop(0, 0, w - slid, vis);
    }
    if (this.launcher.active) clip(this.launcher, this.Y, 22);
    if (this.low.shown) {                                   // sinks with the tower on death, clipped at the ground
      this.low.y = GY + r; const vis = Math.max(0, Math.min(36, 36 - r));
      if (vis < 36) this.low.setCrop(0, 0, 28, vis); else this.low.setCrop();
      this.low.setVisible(vis > 0);
    }
    this.core.y = this.Y + 113 + r; this.core.setVisible(r < 45);
    this.coreGlow.y = this.core.y;
  }

  // ---------------------------------------------------------------- damage
  hit(s, n, bl) {
    if (!s.active || s.dead || !this.fighting()) return;
    if (s.kind === 'low' && !this.lowOpen()) { this.tink(bl ? bl.x : s.x - 12, bl ? bl.y : s.y - 18); return; }   // shutter shut: ricochet
    if (s.kind === 'low') { n = Math.min(n, Math.max(0, 8 - (s.winDmg || 0))); s.winDmg = (s.winDmg || 0) + n; if (!n) return; }   // max 8 per window
    if (s.kind === 'core') { s.winDmg = (s.winDmg || 0) + n; if (s.winDmg >= 15 && this.cyc === 'open' && s.hp - n > 0) this.coreFlinch(); }
    if (s.kind === 'core' && this.doorOpen < 0.6) return;
    s.hp -= n;
    const now = this.scene.time.now;
    if (now > (s.nextFlash || 0)) {
      const tu = s.kind === 'turret', pod = tu || s.kind === 'low';
      s.nextFlash = now + (pod ? 160 : 90);
      for (const o of tu ? [s, s.barrel] : [s]) o.setTint(pod ? 0x3a3024 : 0x605040).setTintMode(Phaser.TintModes.ADD);
      this.scene.time.delayedCall(pod ? 30 : 40, () => { if (s.active) s.clearTint(); if (tu) s.barrel.clearTint(); });
    }
    this.scene.sfx?.play('hit');
    if (s.kind === 'core') this.coreHit(n);
    if (s.hp <= 0) this.kill(s);
  }
  // core hit reaction: glow pops, sparks spray, a floating damage tick, crack stages at 66% / 33%
  coreHit(n, chip) {
    const sc = this.scene, c = this.core, fx = sc.fx;
    if (!chip) this.coreKick = sc.time.now + 70;
    sc.addScore(n * 50);                                   // every hit moves the score
    fx.spark?.(c.x - 6 + rnd(-3, 3), c.y + rnd(-5, 5), 3, 'fire', 120, 20);
    const st = c.hp <= c.maxHp / 3 ? 2 : c.hp <= c.maxHp * 2 / 3 ? 1 : 0;
    if (st > (c.crack || 0)) {
      c.crack = st; fx.explode(c.x, c.y, 0.7); this.chunks(c.x, c.y, 4, 0.8); sc.cameras.main.shake(120, 0.006);
    }
    if (sc.time.now > (this.nextTick || 0)) {
      this.nextTick = sc.time.now + 140;
      const t = sc.add.text(Math.round(c.x - 14 + rnd(-3, 3)), Math.round(c.y - 16), String(Math.max(0, Math.ceil(c.hp))), {
        fontFamily: 'monospace', fontSize: '8px', color: c.hp <= c.maxHp / 3 ? '#ff5a3a' : '#ffe08a', stroke: '#1a1420', strokeThickness: 2 }).setDepth(70).setResolution(1);
      sc.tweens.add({ targets: t, y: t.y - 10, duration: 420, onComplete: () => t.destroy() });
    }
  }
  // 15 damage in one door-open window: the reactor flinches, sparks, and the blast doors slam (evens S/M vs R)
  coreFlinch() {
    const sc = this.scene, c = this.core;
    this.cyc = 'closing'; this.atk = null; this.atkQueue = []; this.coreHot = false;
    sc.fx.spark?.(c.x - 4, c.y, 8, 'fire', 150, 30); sc.cameras.main.shake(120, 0.005); sc.sfx?.play('boom', 0.6);
  }
  fighting() { return this.state === 'p1' || this.state === 'p2' || this.state === 'trans'; }

  kill(s) {
    const sc = this.scene, fx = sc.fx;
    s.dead = true; s.body.enable = false;
    if (s.kind === 'turret') {
      fx.explode(s.x - 16, s.y - 2, 1.1); this.chunks(s.x, s.y, 7, 1);
      s.setFrame(2); s.clearTint(); s.barrel.clearTint();
      const br = s.barrel;
      sc.tweens.add({ targets: br, y: GY + 10, x: br.x - 18, angle: -50, duration: 700, ease: 'Quad.easeIn', onComplete: () => { fx.dust(br.x, GY, 1); br.setVisible(false); } });
      this.smokeSpots.push({ x: s.bx + 2, y: s.by - 4, fire: true });
      sc.addScore(1000);
      // pods are optional (Contra wall rule: the gun you can shoot standing up is the gate's key)
    } else if (s.kind === 'low') {
      fx.explode(s.x - 6, s.y - 18, 1.1); this.chunks(s.x, s.y - 18, 6, 1);
      s.setFrame(2); s.clearTint();
      this.smokeSpots.push({ x: s.x, y: s.y - 30, fire: true });
      sc.addScore(1000);
      if (this.state === 'p1') this.toPhase2();
    } else if (s.kind === 'launcher') {
      fx.explode(s.x + 15, s.y + 9, 1.4); this.chunks(s.x + 15, s.y + 8, 6, 1);
      s.setFrame(2); s.clearTint(); this.tubeGlow.forEach(g => g.setVisible(false));
      this.smokeSpots.push({ x: this.X + 47, y: this.Y + 12, fire: true });
      sc.addScore(1000);
    } else if (s.kind === 'core') {
      sc.addScore(10000);
      this.die();
    }
  }

  chunks(x, y, n, s = 1) {
    const fx = this.scene.fx; if (!fx.part) return;
    for (let i = 0; i < n; i++)
      fx.part('boss-chunks', [Math.floor(Math.random() * 8)], x + rnd(-6, 6), y + rnd(-6, 6), rnd(-160, 90) * s, -rnd(120, 280) * s,
        { g: 700, life: rnd(1100, 1600), bounce: 0.35, spin: rnd(-12, 12), depth: 64, blink: 300 });
  }

  // ---------------------------------------------------------------- main loop
  update(time) {
    const sc = this.scene, p = sc.player; if (!p) return;
    const t = time - this.t0;
    // the gate is solid: the player can't walk into it
    if (this.state !== 'dead' && this.state !== 'sunk' && p.x > this.X - 22) { p.x = this.X - 22; if (p.body.velocity.x > 0) p.body.setVelocityX(0); }

    if (this.state === 'rise') this.updRise(t);
    else if (this.state === 'wake') this.updWake(t);
    else if (this.state === 'p1' || this.state === 'p2') {
      for (const tu of this.turrets) this.updTurret(tu, time);
      this.updLow(time);
      this.updLauncher(time);
      if (this.state === 'p2') this.updCore(time);
    } else if (this.state === 'trans') this.updTrans(t);
    else if (this.state === 'dying') this.updDying(t);

    this.updLights(time);
    this.updHazards(time);
    this.updSmoke(time);
    this.layout();
  }

  // ---------------------------------------------------------------- intro
  updRise(t) {
    const sc = this.scene, D = 2300;
    const k = Math.min(1, t / D);
    this.rise = RISE * (1 - (1 - Math.pow(1 - k, 2)));      // ease-out climb
    if (t > (this.nextRumble || 0)) {
      this.nextRumble = t + 110;
      sc.cameras.main.shake(130, 0.004);
      sc.fx.dust(this.X + rnd(-4, 102), GY, rnd(0.8, 1.3));
      if (Math.random() < 0.5) this.chunks(this.X + rnd(0, 98), GY - 2, 1, 0.6);
    }
    if (t > (this.nextBoom || 300)) { this.nextBoom = t + 480; sc.sfx?.play('boom', 0.5); }
    if (k >= 1) {
      this.rise = 0; this.state = 'wake'; this.t0 = sc.time.now;
      sc.fx.shake(300, 0.012); sc.sfx?.play('boom-big', 0.8);
      for (let i = 0; i < 8; i++) sc.fx.dust(this.X - 10 + i * 16, GY, 1.4);
    }
  }
  updWake(t) {
    const sc = this.scene;
    if (!this.lit && t > 200) { this.lit = true; this.lamps.forEach(l => l.setVisible(true)); sc.sfx?.play('select', 0.6); }
    this.turrets.forEach((tu, i) => {
      if (!tu.out && t > 500 + i * 350) {
        tu.out = true; tu.setVisible(true).setFrame(0); tu.barrel.setVisible(true); tu.x = tu.bx + 10;
        sc.tweens.add({ targets: tu, x: tu.bx, duration: 260, ease: 'Back.easeOut' });
        sc.fx.shake(90, 0.004); sc.sfx?.play('land', 0.8);
        sc.fx.spark?.(tu.bx - 6, tu.by, 5, 'fire', 110);
      }
    });
    if (!this.low.shown && t > 300) { this.low.shown = true; this.low.setVisible(true); sc.fx.shake(90, 0.004); for (let i = 0; i < 3; i++) sc.fx.dust(this.low.x - 10 + i * 10, GY, 1.2); }
    if (t > 1600) {
      this.state = 'p1'; this.t0 = this.p1At = sc.time.now;
      this.low.body.enable = true; this.low.next = sc.time.now + 1400;
      for (const tu of this.turrets) { tu.body.enable = true; tu.next = sc.time.now + 500 + tu.idx * 900; }
      for (const z of [...this.armor, this.doorZone]) z.body.enable = true;
      this.launcher.nextFire = sc.time.now + 2600;
    }
  }

  // ---------------------------------------------------------------- phase 1 weapons
  aimAt(tu) {
    const p = this.scene.player;
    // aim at the top of a STANDING player's head: stepping or going prone makes the locked burst miss
    const dx = p.x - (tu.x - 8), dy = (p.y - 34) - tu.y;
    // shallow max depression: the strip right under the gate is a safe pocket (Contra wall), the mortar covers it
    return Phaser.Math.Clamp(Math.atan2(dy, -dx) * 180 / Math.PI, GUN_A0, tu.idx === 0 ? 30 : 20);
  }
  tip(tu, d = 33) {
    const a = tu.ang * Math.PI / 180, c = Math.cos(a), s = Math.sin(a);
    return { x: tu.x - 8 - d * c, y: tu.y + d * s, dx: -c, dy: s };        // pivot = collar on the house
  }
  updTurret(tu, time) {
    if (tu.dead || !tu.out) return;
    const sc = this.scene, fx = sc.fx;
    // idle: drift toward the player slowly. Tell: the aim is LOCKED at the tell's start (where the player stood)
    // and the barrels swing onto that line, so one step (or going prone under a shallow line) dodges the burst.
    const want = tu.phase === 'idle' ? this.aimAt(tu) : tu.lock, step = (sc.game.loop.delta / 1000) * (tu.phase === 'idle' ? 50 : 140);
    if (tu.phase !== 'fire') tu.ang += Phaser.Math.Clamp(want - tu.ang, -step, step);
    // barrels spin up during the tell and whirl while firing (3 spin phases per aim angle)
    const spinMs = tu.phase === 'fire' ? 40 : tu.phase === 'charge' ? (time < tu.until - 260 ? 110 : 55) : 0;
    if (spinMs && time > (tu.nextSpin || 0)) { tu.nextSpin = time + spinMs; tu.spin = (tu.spin + 1) % 3; }
    const a = tu.ang * Math.PI / 180;
    tu.rk = Math.max(0, tu.rk - sc.game.loop.delta * 0.04);           // barrel recoil decays
    tu.barrel.setFrame(tu.spin * GUN_N + Phaser.Math.Clamp(Math.round((tu.ang - GUN_A0) / 5), 0, GUN_N - 1))
      .setPosition(Math.round(tu.x - 8 + Math.cos(a) * tu.rk), Math.round(tu.y - Math.sin(a) * tu.rk));
    // pods take turns (never two bursts in the air at once), each burst preceded by a 600ms locked tell
    if (tu.phase === 'idle' && time > tu.next && time > (this.podFree || 0) && !this.turrets.some(o => o !== tu && o.phase !== 'idle')) {
      tu.phase = 'charge'; tu.until = time + 600; tu.lock = this.aimAt(tu); this.podFree = time + 2000;
    }
    if (tu.phase === 'charge') {                            // telegraph: eye blinks hot, sparks at the barrels
      tu.setFrame(Math.floor(time / 55) % 2 ? 1 : 0);       // twin red sensor eyes blink hot (hard pixels)
      if (Math.random() < 0.3) { const m = this.tip(tu, 32); fx.spark?.(m.x, m.y, 1, 'fire', 40); }
      if (time > tu.until) { tu.phase = 'fire'; tu.shots = 0; tu.nextShot = time; }
    } else if (tu.phase === 'fire') {
      tu.setFrame(1);
      if (time >= tu.nextShot) {
        const m = this.tip(tu), sp = 130;
        sc.fireEnemy(m.x + m.dx * 3, m.y + m.dy * 3, m.dx * sp, m.dy * sp); fx.muzzle(m.x, m.y, m.dx, m.dy, 1.4);
        tu.rk = 3;                                                             // barrel kicks back
        tu.shots++; tu.nextShot = time + 75;
        if (tu.shots >= 3) { tu.phase = 'idle'; tu.next = time + rnd(2600, 3200) * (this.state === 'p2' ? 1.5 : 1); tu.setFrame(0); }
      }
    } else tu.setFrame(0);
    if (tu.hp < tu.maxHp / 2 && Math.random() < 0.04) fx.smokePuffs?.(tu.x + 4, tu.y - 8, 1, 3);
    if (tu.hp < tu.maxHp / 2 && Math.random() < 0.03) fx.spark?.(tu.x + rnd(-6, 6), tu.y + rnd(-6, 6), 2, 'fire', 80);
  }

  // low intake cannon (the phase-1 key). SHUT = armoured (shots ricochet off the shutter). Every ~3.4s the shutter
  // opens for a 650ms tell (red eye hot), fires a floor-skimming pair (jump it), and stays open until 1.3s after the
  // tell started - the punish window. Taking 9+ damage in one window makes it flinch and slam shut early, so every
  // weapon needs ~3 windows (Contra rhythm: wait, dodge, punish; evens out S/M vs R).
  lowOpen() { const g = this.low; return g.phase === 'tell' || g.phase === 'fire' || g.phase === 'open'; }
  lowSlam(time, flinch) {
    const g = this.low, sc = this.scene;
    g.phase = 'idle'; g.next = g.t0 + 2000 + rnd(1700, 2100); g.setFrame(0); g.winDmg = 0;   // fixed rhythm: a flinch doesn't bring the next window sooner
    sc.sfx?.play('land', 0.7); sc.fx.shake(70, 0.003);
    if (flinch) { sc.fx.spark?.(g.x - 12, GY - 18, 6, 'fire', 140, 30); this.chunks(g.x - 8, GY - 20, 2, 0.6); }
  }
  updLow(time) {
    const g = this.low, sc = this.scene; if (!g.active || g.dead) return;
    if (g.phase === 'idle' && time > g.next) { g.phase = 'tell'; g.t0 = time; g.until = time + 650; g.winDmg = 0; g.setFrame(1); sc.sfx?.play('telegraph', 0.8); }
    if (g.phase === 'tell') {
      if (time > g.until) { g.phase = 'fire'; g.shots = 0; g.nextShot = time; }
    } else if (g.phase === 'fire') {
      if (time >= g.nextShot) {
        const mx = g.x - 15, my = GY - 6;
        sc.fireEnemy(mx, my, -125, 0); sc.fx.muzzle(mx, my, -1, 0, 1.2);
        g.shots++; g.nextShot = time + 90;
        if (g.shots >= 2) g.phase = 'open';
      }
    } else if (g.phase === 'open' && time > g.t0 + 2000) this.lowSlam(time, false);
    if (this.lowOpen() && (g.winDmg || 0) >= 8) this.lowSlam(time, true);
    g.armor = !this.lowOpen();
    if (g.hp < g.maxHp / 2 && Math.random() < 0.03) sc.fx.smokePuffs?.(g.x + 4, g.y - 30, 1, 3);
  }

  updLauncher(time) {
    const L = this.launcher, sc = this.scene; if (!L.active || L.dead) return;
    if (!L.charging && time > L.nextFire) { L.charging = true; L.fireAt = time + 700; sc.sfx?.play('telegraph', 0.8); }
    if (L.charging) {
      const on = Math.floor(time / 70) % 2 === 0;
      this.tubeGlow.forEach(g => g.setVisible(on));
      if (time > L.fireAt) {
        L.charging = false; this.tubeGlow.forEach(g => g.setVisible(false));
        L.nextFire = time + (this.state === 'p2' ? 5200 : 4300);
        const p = sc.player, cam = sc.cameras.main;
        const lo = cam.scrollX + 18, hi = this.X - 14;
        const base = Phaser.Math.Clamp(p.x, lo, hi);
        // brackets the player (boxes you in, punishes a panicked step); tighter in phase 2
        const xs = (this.state === 'p2' ? [base - 34, base + 34, base - 78] : [base - 40, base + 40, base - 84]).map(v => Phaser.Math.Clamp(v, lo, hi));
        xs.forEach((tx, i) => sc.time.delayedCall(i * 170, () => this.launchShell(tx, i)));
      }
    }
  }
  launchShell(tx, i) {
    const sc = this.scene; if (!this.launcher.active || this.launcher.dead || !this.fighting()) return;
    const x0 = this.X + 42 + (i % 2) * 11, y0 = this.Y + 2, T = 1.35, g = 420;
    const s = this.bullet(x0, y0, 'boss-shell', 45, 'boss-shell-blink', true); if (!s) return;
    s.body.setSize(6, 8);
    const mk = sc.add.sprite(tx, GY - 3, 'boss-mark', 0).setDepth(21).play('boss-mark-blink');
    sc.fx.muzzle(x0, y0 - 2, 0, -1, 1); sc.fx.smokePuffs?.(x0, y0, 2, 3); sc.sfx?.play('enemy-shot', 0.8);
    s.body.setVelocity((tx - x0) / T, ((GY - 4 - y0) - 0.5 * g * T * T) / T);
    this.haz.push({ kind: 'shell', s, mk, g, tx });
  }

  // ---------------------------------------------------------------- phase change
  toPhase2() {
    const sc = this.scene;
    this.state = 'trans'; this.t0 = this.transAt = sc.time.now; this.transBooms = 0;
    this.haz.filter(h => h.kind === 'shell').forEach(h => (h.dead = true));
  }
  updTrans(t) {
    const sc = this.scene, fx = sc.fx;
    if (t > this.transBooms * 180 && this.transBooms < 10) {
      this.transBooms++;
      fx.explode(this.X + rnd(8, 90), this.Y + rnd(22, 130), this.transBooms % 3 ? 0.7 : 1.3);
      this.chunks(this.X + rnd(15, 88), this.Y + rnd(30, 117), 3);
    }
    if (!this.cracked && t > 600) {
      this.cracked = true;
      // the facade blast takes any surviving gun pods with it (no score): phase 2 is the core's fight
      for (const tu of this.turrets) if (!tu.dead) { tu.hp = 0; this.kill(tu); sc.addScore(-1000); }
      this.body.setFrame(1); this.doorL.setFrame(1); this.doorR.setFrame(1);
      if (this.launcher.active && !this.launcher.dead) this.launcher.setFrame(1);
      sc.cameras.main.flash(120, 255, 240, 200); fx.shake(400, 0.012); sc.sfx?.play('boom-big');
      this.chunks(this.X + 44, this.Y + 66, 14, 1.2);
      this.smokeSpots.push({ x: this.X + 82, y: this.Y + 44 }, { x: this.X + 22, y: this.Y + 29 }, { x: this.X + 86, y: this.Y + 109, spark: true },
        { x: this.X + 73, y: this.Y + 73, spark: true });
    }
    if (t > 1600) {
      this.state = 'p2'; this.core.body.enable = false;
      this.cyc = 'shut'; this.cycT = sc.time.now + 300; this.attack = 0;
      this.launcher.nextFire = sc.time.now + 3000;
    }
  }

  // ---------------------------------------------------------------- phase 2: the core cycles open
  updCore(time) {
    const sc = this.scene, dt = sc.game.loop.delta / 1000;
    const openMs = this.enraged ? 3000 : 2700, shutMs = this.enraged ? 1000 : 1500;
    if (this.cyc === 'shut' && time > this.cycT) { this.cyc = 'opening'; sc.sfx?.play('land', 0.9); sc.fx.shake(120, 0.003); }
    if (this.cyc === 'opening') {
      this.doorOpen = Math.min(1, this.doorOpen + dt * 3);
      if (this.doorOpen >= 1) { this.cyc = 'open'; this.cycT = time + openMs; this.core.winDmg = 0; this.startAttack(time); }
    } else if (this.cyc === 'open') {
      this.runAttack(time);
      if (time > this.cycT && !this.atk) { this.cyc = 'closing'; }
    } else if (this.cyc === 'closing') {
      this.doorOpen = Math.max(0, this.doorOpen - dt * 3);
      if (this.doorOpen <= 0) { this.cyc = 'shut'; this.cycT = time + shutMs; sc.fx.shake(100, 0.004); sc.sfx?.play('land', 1); }
    }
    const open = this.doorOpen > 0.6;
    this.core.body.enable = open; this.doorZone.body.enable = !open;
    if (!this.enraged && this.core.hp < this.core.maxHp / 2) {
      this.enraged = true; sc.fx.explode(this.X + 48, this.Y + 80, 1.3); this.chunks(this.X + 48, this.Y + 80, 8);
      this.smokeSpots.push({ x: this.X + 37, y: this.Y + 86, fire: true }, { x: this.X + 61, y: this.Y + 86, fire: true });
    }
  }
  startAttack(time) {
    this.attack++;
    const kinds = this.enraged ? (this.attack % 2 ? ['saws', 'sweep'] : ['sweep', 'saws']) : [this.attack % 2 ? 'saws' : 'sweep'];
    this.atkQueue = kinds; this.atk = null; this.atkNext = time + 150;
  }
  runAttack(time) {
    const sc = this.scene, fx = sc.fx;
    if (!this.atk && this.atkQueue.length && time > this.atkNext) {
      const k = this.atkQueue.shift();
      this.atk = { k, t: time, n: 0 };
    }
    const A = this.atk; if (!A) return;
    const cx = this.X + 48, e = time - A.t;
    if (A.k === 'saws') {
      const count = this.enraged ? 3 : 2;
      // each saw: spins up in the doorway (sparks, glow) for 450ms, then rolls out along the floor
      const gap = this.enraged ? 820 : 1000;                 // room to land between two jumps
      if (A.n < count && e > A.n * gap) {
        A.n++;
        const s = this.bullet(cx, GY - 9, 'boss-saw', 44, 'boss-saw-spin');
        if (s) { s.body.setCircle(6, 3, 3); this.haz.push({ kind: 'saw', s, go: time + 450, sp: this.enraged ? 150 : 125 }); }
      }
      if (A.n >= count && e > count * gap + 300) { this.atk = null; this.atkNext = time + 250; }
    } else if (A.k === 'sweep') {
      // laser sight at head height (prone dodges), then a raking stream of shots
      const y = GY - 24, g = this.sight; g.clear();
      if (e < 650) {
        if (Math.floor(e / 60) % 2 === 0) {
          g.fillStyle(0xff2a1a, 1).fillRect(sc.cameras.main.scrollX, y, cx - 10 - sc.cameras.main.scrollX, 1);
          g.fillStyle(0xffd060, 1).fillRect(cx - 14, y - 1, 3, 3);
        }
      } else {
        const shots = this.enraged ? 8 : 6;
        if (A.n < shots && e > 650 + A.n * 95) {
          A.n++; sc.fireEnemy(cx - 14, y, -210, 0); fx.muzzle(cx - 14, y, -1, 0, 1.2);
        }
        if (A.n >= shots) { this.atk = null; this.atkNext = time + 300; }
      }
    }
    this.coreHot = !!this.atk;
  }

  // ---------------------------------------------------------------- hazards we simulate ourselves (FX restyles eBullets)
  // saws and mortar shells are real scene.eBullets members (noStyle: FX leaves their art alone), so Game's
  // player overlap, culling and the bot all see them; we only steer them (gravity, grind-then-roll) and time out.
  bullet(x, y, tex, depth, anim, late) {
    const sc = this.scene, b = sc.physics.add.sprite(x, y, tex, 0).setDepth(depth);
    b.noStyle = true; b.born = sc.time.now;
    if (!late) { sc.eBullets.add(b); if (!sc.eBullets.contains(b)) { b.destroy(); return null; } }   // pool full
    b.body.setAllowGravity(false); if (anim) b.play(anim);
    return b;
  }
  updHazards(time) {
    const sc = this.scene, p = sc.player, dt = Math.min(sc.game.loop.delta, 50) / 1000, fx = sc.fx;
    const pb = p && p.body && !p.dead ? p.body : null;
    for (const h of this.haz) {
      if (h.dead) continue;
      const b = h.s;
      if (!b.scene || !b.active) { h.dead = true; continue; }   // hit the player / culled by Game
      b.born = sc.time.now;                                    // we own the lifetime, not Game's 3s cull
      if (h.kind === 'shell') {
        b.body.velocity.y += h.g * dt;
        if (!h.live && b.body.velocity.y > 0 && b.y > GY - 70) { h.live = true; const vx = b.body.velocity.x, vy = b.body.velocity.y; sc.eBullets.add(b); b.body.setAllowGravity(false).setVelocity(vx, vy); }   // group.add resets velocity   // arms on the way down
        b.setRotation(Math.atan2(b.body.velocity.y, b.body.velocity.x) - Math.PI / 2);
        h.mk.anims.timeScale = b.body.velocity.y > 0 ? 2.2 : 1;
        if (b.y >= GY - 4 && b.body.velocity.y > 0) {
          h.dead = true; fx.explode(h.tx, GY - 8, 0.72); fx.dust(h.tx, GY, 1.2);
          if (pb && Math.abs(p.x - h.tx) < 15 && pb.y + pb.height > GY - 26) p.hurt();
        }
      } else if (h.kind === 'saw') {
        if (time < h.go) {                                  // grinding in the doorway
          b.body.setVelocity(0, 0);
          if (Math.random() < 0.5) fx.spark?.(b.x - 4, GY - 1, 1, 'fire', 80, 60);
        } else {
          if (!h.rolled) { h.rolled = true; sc.sfx?.play('capsule', 0.7); b.body.setVelocity(-h.sp, 0); }
          if (Math.random() < 0.35) fx.spark?.(b.x + 6, GY - 1, 1, 'fire', 90, 70);
          if (b.x < sc.cameras.main.scrollX - 20) h.dead = true;
        }
      }
    }
    for (const h of this.haz) if (h.dead && !h.gone) { h.gone = true; if (h.s.scene) h.s.destroy(); h.mk?.destroy(); }
    this.haz = this.haz.filter(h => !h.gone);
    if (!this.atk || this.atk.k !== 'sweep') this.sight.clear();
  }

  // ---------------------------------------------------------------- lights / damage-state ambience
  drawHp() {
    // campaign-wide bottom BossBar for the whole fight: the low cannon (phase 1), then the reactor core
    const c = this.core, lo = this.low;
    this.bar.set(this.state === 'p1' && !lo.dead ? c.maxHp + Math.max(0, lo.hp) : c.hp, c.maxHp + lo.maxHp, this.fighting() && !c.dead);
  }
  updLights(time) {
    this.drawHp();
    const alive = this.state !== 'dying' && this.state !== 'sunk' && this.state !== 'rise';
    const fast = this.state === 'trans' || this.state === 'p2';
    const on = Math.floor(time / (fast ? 140 : 380)) % 2 === 0;
    this.beacons.forEach((b, i) => b.setVisible(alive && (i ? !on : on)));
    if (!alive) this.lamps.forEach(l => l.setVisible(false));
    // core glow pulses; hot while attacking; hidden behind the door
    const vis = this.doorOpen > 0.15 && this.state !== 'sunk' && this.core.active;
    const pulse = 0.5 + 0.5 * Math.sin(time / (this.coreHot ? 50 : 160));
    this.coreGlow.setVisible(false);
    const kick = time < (this.coreKick || 0);
    if (this.core.active && !this.core.dead) this.core.setFrame((this.core.crack || 0) * 2 + ((this.coreHot && Math.floor(time / 60) % 2) || kick ? 1 : 0));
  }
  updSmoke(time) {
    if (time < (this.nextSmoke || 0) || this.state === 'rise') return;
    this.nextSmoke = time + (this.enraged ? 120 : 200);
    const fx = this.scene.fx, s = pick(this.smokeSpots.length ? this.smokeSpots : [null]); if (!s) return;
    const y = s.y + Math.round(this.rise);
    if (y > GY) return;
    fx.smokePuffs?.(s.x + rnd(-2, 2), y, 1, 3);
    if (s.fire && Math.random() < 0.6) fx.embers?.(s.x, y, 2, 3);
    if (s.spark && Math.random() < 0.5) fx.spark?.(s.x, y, 3, 'fire', 110, 30);
  }

  // ---------------------------------------------------------------- death
  die() {
    const sc = this.scene;
    this.state = 'dying'; this.t0 = this.diedAt = sc.time.now; this.booms = 0; this.coreHot = false; this.atk = null; this.atkQueue = [];
    this.haz.forEach(h => (h.dead = true)); this.sight.clear();
    for (const z of [...this.armor, this.doorZone]) z.body.enable = false;
    for (const tu of this.turrets) { tu.body.enable = false; if (!tu.dead) tu.setFrame(0); }
    if (this.launcher.active) this.launcher.body.enable = false;
    this.low.body.enable = false;
    sc.fx.hitstop(160); sc.cameras.main.flash(160, 255, 255, 255);
    sc.fx.explode(this.core.x, this.core.y, 1.6); this.chunks(this.core.x, this.core.y, 10, 1.3);
    this.core.setVisible(false); this.core.body.enable = false;
    this.tubeGlow.forEach(g => g.setVisible(false));
  }
  updDying(t) {
    const sc = this.scene, fx = sc.fx, X = this.X, Y = this.Y + Math.round(this.rise);
    if (t < 2600 && t > this.booms * 95) {                 // chain explosions over the whole gate
      this.booms++;
      const big = this.booms % 6 === 0;
      fx.explode(X + rnd(5, 93), Math.min(GY - 6, Y + rnd(8, 140)), big ? 1.3 : rnd(0.55, 0.72));
      if (this.booms % 2) this.chunks(X + rnd(8, 90), Math.min(GY - 8, Y + rnd(15, 125)), 2, 1.1);
      sc.cameras.main.shake(100, 0.006);
    }
    if (!this.scorched && t > 900) {
      this.scorched = true; this.body.setFrame(2);
      this.turrets.forEach(tu => { fx.explode(tu.x, tu.y, 1.3); tu.setFrame(2); tu.barrel.setVisible(false); sc.tweens.add({ targets: tu, y: GY + 20, angle: -70, duration: 900, ease: 'Quad.easeIn', onComplete: () => tu.setVisible(false) }); });
      if (!this.low.dead) { this.low.dead = true; fx.explode(this.low.x, this.low.y - 18, 1.1); }
      this.low.setFrame(2);
      if (this.launcher.active) { this.launcher.setFrame(2); fx.explode(this.launcher.x + 15, this.launcher.y + 8, 1.3); }
      this.doorL.setVisible(false).visibleWanted = false; this.doorOpen = 1;
    }
    if (t > 1300) {                                         // collapse: sinks back into the yard, shuddering
      const k = Math.min(1, (t - 1300) / 2000);
      this.rise = 110 * k * k;
      this.body.x = this.X + (Math.floor(t / 40) % 2 ? 1 : -1) * (k < 1 ? 1 : 0);
      if (Math.random() < 0.5) fx.dust(X + rnd(0, 98), GY, rnd(0.9, 1.4));
    }
    if (!this.whiteout && t > 2900) {
      this.whiteout = true; sc.cameras.main.flash(500, 255, 255, 255); fx.explode(X + 48, GY - 30, 1.6);
      sc.sfx?.play('boom-big');
    }
    if (t > 3400) {
      this.state = 'sunk'; this.active = false; this.body.x = this.X;
      const sy = GY - 8 - Math.round(this.rise);
      this.smokeSpots = [{ x: X + 30, y: sy }, { x: X + 70, y: sy, fire: true }, { x: X + 110, y: sy }];
      this.scene.bossDefeated(this);
    }
  }
}
