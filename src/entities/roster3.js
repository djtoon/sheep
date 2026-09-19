// Stage-3 enemy roster (secret lab): exports ROSTER3 = { typeName: Class }. Classes follow the Enemy pattern in Enemies.js
// (hp, score, update(time), damage/die, canFire + claimTell shot lock + telegraph). Art faces LEFT; flipX = facing right.
// Every threat has a readable tell and a clear answer:
//   hazmat  laser bolt, 16-step aim, 500 ms visor-glint tell            -> jump / prone / move off the line
//   clawbot hovers; 600 ms claw-open tell then a swoop at where you WERE -> step aside; or a slow orb (450 ms tell)
//   toxic   stops at close range, 700 ms pilot-flame tell, 0.9 s cone    -> stay out of ~50 px, or shoot it first
//   xeno    fast crawler, 380 ms crouch tell then a pounce               -> jump over / shoot early (2 HP)
//   mutant  slow, 10 HP, 450 ms arm-raise tell then a short slash        -> keep distance
//   walker  mini-boss: walks, stops, 1.3 s charge with a dotted aim line, then a horizontal beam -> go prone / jump
const rnd = Phaser.Math.Between;
const SHOT_GAP = 350;

class R3Enemy extends Phaser.Physics.Arcade.Sprite {
  constructor(scene, x, y, name, hp, score) {
    super(scene, x, y, 'r3-' + name);
    scene.add.existing(this); scene.physics.add.existing(this);
    this.setOrigin(0.5, 1).setDepth(40);
    this.unit = name; this.hp = hp; this.maxHp = hp; this.score = score; this.flash = 0; this.dir = -1;
    this.born = scene.time.now;
  }
  anim(k, ignore = true) { const key = this.unit + '-' + k; if (this.scene.anims.exists(key) && this.anims.currentAnim?.key !== key) this.play(key, ignore); }
  face(p) { if (p) this.setFlipX(p.x > this.x); }
  facing() { return this.flipX ? 1 : -1; }
  damage(n, from) {
    if (!this.active) return;
    this.hp -= n;
    const now = this.scene.time.now;
    if (now > (this.nextFlash || 0)) { this.nextFlash = now + 110; this.flash = 34; this.setTint(0x605040).setTintMode(Phaser.TintModes.ADD); }
    if (this.hp <= 0) { this.scene.enemyKilled?.(this, from); this.die(from); }
    else {
      this.scene.sfx?.play('hit');
      if (this.body && !this.body.immovable && this.body.allowGravity && from && from.body && this.knock !== false) this.x += Math.sign(from.body.velocity.x || 1) * 2;
    }
  }
  preUpdate(t, dt) {
    super.preUpdate(t, dt);
    if (this.flash > 0 && (this.flash -= dt) <= 0) this.clearTint();
    const cam = this.scene.cameras.main, W = this.scene.scale.width;
    if (this.x < cam.scrollX - 90 || this.y > this.scene.level.height + 60 || (this.dir > 0 && this.x > cam.scrollX + W + 90)) this.destroy();
  }
  canFire(margin = 12) {
    const sc = this.scene, p = sc.player, cam = sc.cameras.main;
    return p && !p.dead && !sc.cleared && !(sc.boss && !this.miniBoss) && sc.flow === 'play' && this.x > cam.scrollX + margin && this.x < cam.scrollX + sc.scale.width - margin && this.y > 8;
  }
  claimTell(time, ms) {
    const sc = this.scene;
    if ((sc.shotLock || 0) > time && sc.shotLockBy !== this && sc.shotLockBy && sc.shotLockBy.active) return false;
    sc.shotLock = time + ms + SHOT_GAP; sc.shotLockBy = this; return true;
  }
  telegraph(m, ms) {
    const sc = this.scene;
    sc.events.emit('telegraph', { enemy: this, x: m.x, y: m.y, ms });
    if (!(sc.hooked && sc.hooked.telegraph) && sc.fx && sc.fx.oneShot) for (let i = 0; i < 2; i++) sc.time.delayedCall(i * (ms / 2), () => this.active && sc.fx.oneShot(m.x, m.y, 'hit', 'eflash', 57));
  }
  aimAt(o, quant = Math.PI / 8) {
    const p = this.scene.player; const c = p.hurtCenter ? p.hurtCenter() : { x: p.x, y: p.y - 18 };
    let a = Math.atan2(c.y - o.y, c.x - o.x);
    return quant ? Math.round(a / quant) * quant : a;
  }
  // grounded and roughly on the player's floor
  sameFloor(p, tol = 24) { return p && Math.abs(p.y - this.y) < tol; }
  // walk logic shared by the ground units: never walk off a ledge into a pit, turn at walls
  walk(v) {
    const b = this.body, sc = this.scene;
    if (b.blocked.down && !sc.groundAhead(this.x + this.dir * 12, this.y)) { const lower = sc.groundYAt(this.x + this.dir * 20); if (!(lower < sc.level.height && lower - this.y < 60)) { this.dir *= -1; } }
    if (b.blocked.down && (b.blocked.left || b.blocked.right)) this.dir *= -1;
    b.setVelocityX(this.dir * v); this.setFlipX(this.dir > 0);
  }
  scorePop(dy = 24) { this.scene.addScore(this.score, this.x, this.y - dy); }
}

// ---------------------------------------------------------------- projectiles (own pool: custom textures, same player hurt rules)
function shots(sc) {
  if (sc.r3Shots && sc.r3Shots.scene) return sc.r3Shots;
  const g = sc.r3Shots = sc.physics.add.group({ allowGravity: false, maxSize: 40 });
  sc.physics.add.overlap(sc.player, g, (p, b) => { if (p.hurt('bullet:' + (b.src || 'r3'))) kill(b); }, (p, b) => b.active && p.touches(b.body));
  const upd = () => {
    const cam = sc.cameras.main, W = sc.scale.width, now = sc.time.now;
    for (const b of g.getChildren()) if (b.active && (b.x < cam.scrollX - 30 || b.x > cam.scrollX + W + 30 || b.y < -30 || b.y > sc.level.height + 30 || now - b.born > 7000)) kill(b);
  };
  sc.events.on('update', upd);
  sc.events.once('shutdown', () => { sc.events.off('update', upd); sc.r3Shots = null; });
  return g;
}
function kill(b) { b.setActive(false).setVisible(false); b.body.stop(); b.body.enable = false; }
function fire(sc, tex, x, y, a, speed, src, r = 2, snd = 'enemy-shot') {
  const g = shots(sc); const b = g.get(x, y, tex); if (!b) return null;
  b.setTexture(tex).setActive(true).setVisible(true).setDepth(56).setRotation(tex === 'r3-orb' ? 0 : a);
  if (sc.anims.exists(tex + '-a')) b.play(tex + '-a');
  b.body.enable = true; b.body.reset(x, y); b.body.setAllowGravity(false);
  b.body.setCircle(r, b.width / 2 - r, b.height / 2 - r);
  b.body.setVelocity(Math.cos(a) * speed, Math.sin(a) * speed); b.born = sc.time.now; b.src = src;
  sc.sfx?.play(snd, 0.7);
  return b;
}
function rectHit(p, r) {
  if (!p || p.dead) return false;
  const h = p.hurtRect();
  return h.x < r.x + r.w && h.x + h.w > r.x && h.y < r.y + r.h && h.y + h.h > r.y;
}

// ---------------------------------------------------------------- deaths
function gooDeath(e, colour, big = 1) {
  const sc = e.scene, fx = sc.fx;
  e.scorePop(20);
  const s = sc.add.sprite(Math.round(e.x), Math.round(e.y) + 1, 'r3-goo-' + colour, 0).setOrigin(0.5, 1).setDepth(44).setScale(big);
  if (sc.anims.exists('r3-goo-' + colour + '-a')) {
    s.play('r3-goo-' + colour + '-a');
    s.once('animationcomplete', () => sc.tweens.add({ targets: s, alpha: 0, duration: 400, delay: 500, ease: 'Stepped', easeParams: [3], onComplete: () => s.destroy() }));
  } else s.destroy();
  if (fx) { fx.spark?.(e.x, e.y - 10, 5, colour === 'acid' ? 'cyan' : 'pink', 120, 40); fx.shake?.(60, 0.002); fx.hitstop?.(25); }
  sc.sfx?.play('goo');
  e.destroy();
}
function trooperDeath(e, from) {
  const sc = e.scene;
  e.scorePop(30);
  if (sc.fx && sc.fx.soldierDeath) sc.fx.soldierDeath(e, from); else sc.fx?.explode(e.x, e.y - 20, 0.8);
  e.destroy();
}

// ---------------------------------------------------------------- 1. hazmat: white lab trooper with a laser rifle
export class Hazmat extends R3Enemy {
  constructor(scene, x, y) {
    super(scene, x, y, 'hazmat', 3, 300);
    this.body.setSize(16, 34).setOffset((this.width - 16) / 2, this.height - 34);
    this.anim('move'); this.next = scene.time.now + 900; this.stopUntil = 0;
  }
  muzzle() { const f = this.facing(); return { x: this.x + f * 30, y: this.y - 27 }; }
  update(time) {
    const sc = this.scene, p = sc.player, b = this.body; if (!p) return;
    if (this.stopUntil > time) { b.setVelocityX(0); this.face(p); return; }
    const dx = p.x - this.x;
    if (b.blocked.down && time > this.next && this.canFire(24) && Math.abs(dx) > 60 && Math.abs(dx) < 300 && this.claimTell(time, Hazmat.TELL + 200)) {
      this.face(p); b.setVelocityX(0); this.anim('aim');
      this.stopUntil = time + Hazmat.TELL + 520; this.next = time + rnd(1800, 2600);
      this.telegraph(this.muzzle(), Hazmat.TELL);
      const a = this.aimAt(this.muzzle());
      sc.time.delayedCall(Hazmat.TELL, () => {
        if (!this.active || !this.canFire(8)) return;
        const m = this.muzzle(); fire(sc, 'r3-laser', m.x, m.y, a, Hazmat.BOLT, 'Hazmat', 2, 'laser-bolt');
        sc.fx?.muzzle(m.x, m.y, Math.cos(a), Math.sin(a), 0.7); this.anim('attack');
        if (Math.random() < 0.35) sc.time.delayedCall(220, () => { if (this.active && this.canFire(8)) { const m2 = this.muzzle(); fire(sc, 'r3-laser', m2.x, m2.y, a, Hazmat.BOLT, 'Hazmat', 2, 'laser-bolt'); } });
      });
      return;
    }
    if (this.stopUntil && time > this.stopUntil) { this.stopUntil = 0; this.dir = dx > 0 ? 1 : -1; }
    this.anim('move');
    // advance to a firing distance, then hold ground
    if (Math.abs(dx) < 90) { b.setVelocityX(0); this.face(p); this.anim('aim'); } else { this.dir = dx > 0 ? 1 : -1; this.walk(Hazmat.SPEED); }
  }
  die(from) { trooperDeath(this, from); }
}
Hazmat.SPEED = 46; Hazmat.TELL = 500; Hazmat.BOLT = 150;

// ---------------------------------------------------------------- 2. clawbot: floating orb robot, swoop-grab + slow orb
export class Clawbot extends R3Enemy {
  constructor(scene, x, y) {
    super(scene, x, y, 'clawbot', 4, 400);
    this.setOrigin(0.5, 0.5); this.body.setAllowGravity(false);
    this.body.setSize(28, 25).setOffset((this.width - 28) / 2, (this.height - 25) / 2);
    this.hoverY = Phaser.Math.Clamp(y, 50, 110); this.y = this.hoverY; this.t0 = scene.time.now;
    this.state = 'hover'; this.next = scene.time.now + 1600; this.anim('move'); this.knock = false;
  }
  update(time, dt) {
    const sc = this.scene, p = sc.player, b = this.body; if (!p) return;
    this.face(p);
    if (this.state === 'hover') {
      const tx = p.x + (this.x > p.x ? 70 : -70);
      b.setVelocityX(Phaser.Math.Clamp((tx - this.x) * 1.2, -70, 70));
      b.setVelocityY((this.hoverY + Math.sin((time - this.t0) / 420) * 10 - this.y) * 4);
      if (time > this.next && this.canFire(20)) {
        const swoop = Math.abs(p.x - this.x) < 150 && Math.random() < 0.6;
        const tell = swoop ? Clawbot.SWOOP_TELL : Clawbot.ORB_TELL;
        if (!this.claimTell(time, tell + (swoop ? 700 : 150))) { this.next = time + 500; return; }
        this.state = swoop ? 'tellSwoop' : 'tellOrb'; this.until = time + tell; b.setVelocity(0, 0);
        this.anim('open'); this.telegraph({ x: this.x, y: this.y + (swoop ? 12 : 8) }, tell);
        if (swoop) { const c = p.hurtCenter(); this.target = { x: c.x, y: Math.min(c.y, sc.groundYAt(c.x) - 14) }; }   // swoops at where the sheep WAS
      }
    } else if (this.state === 'tellOrb' && time > this.until) {
      const m = { x: this.x, y: this.y + 10 };
      if (this.canFire(8)) fire(sc, 'r3-orb', m.x, m.y, this.aimAt(m, 0), Clawbot.ORB, 'Clawbot', 3);
      this.state = 'hover'; this.next = time + rnd(2200, 3000); this.anim('move');
    } else if (this.state === 'tellSwoop' && time > this.until) {
      this.state = 'swoop'; this.anim('attack');
      const a = Math.atan2(this.target.y - this.y, this.target.x - this.x);
      b.setVelocity(Math.cos(a) * Clawbot.DIVE, Math.sin(a) * Clawbot.DIVE); this.until = time + 900;
    } else if (this.state === 'swoop') {
      const reached = Phaser.Math.Distance.Between(this.x, this.y, this.target.x, this.target.y) < 8 || time > this.until || this.y > sc.groundYAt(this.x) - 12;
      if (reached) { this.state = 'rise'; b.setVelocity(b.velocity.x * 0.3, -Clawbot.DIVE * 0.6); this.anim('move'); }
    } else if (this.state === 'rise') {
      if (this.y <= this.hoverY) { this.state = 'hover'; this.next = time + rnd(2000, 2800); }
    }
  }
  die() {
    this.scorePop(0);
    this.scene.fx?.explode(this.x, this.y, 0.9);
    this.destroy();
  }
}
Clawbot.SWOOP_TELL = 600; Clawbot.ORB_TELL = 450; Clawbot.DIVE = 170; Clawbot.ORB = 70;

// ---------------------------------------------------------------- 3. toxic: hazmat flamethrower, short-range telegraphed cone
export class Toxic extends R3Enemy {
  constructor(scene, x, y) {
    super(scene, x, y, 'toxic', 5, 500);
    this.body.setSize(18, 36).setOffset((this.width - 18) / 2, this.height - 36);
    this.anim('move'); this.next = scene.time.now + 800; this.state = 'walk';
  }
  nozzle() { const f = this.facing(); return { x: this.x + f * 28, y: this.y - 25 }; }
  update(time) {
    const sc = this.scene, p = sc.player, b = this.body; if (!p) return;
    const dx = p.x - this.x;
    if (this.state === 'walk') {
      this.anim('move'); this.dir = dx > 0 ? 1 : -1;
      if (Math.abs(dx) < Toxic.TRIGGER && this.sameFloor(p, 30) && b.blocked.down && time > this.next && this.canFire(16) && this.claimTell(time, Toxic.TELL + Toxic.BURN)) {
        this.state = 'tell'; this.until = time + Toxic.TELL; b.setVelocityX(0); this.face(p); this.anim('aim');
        const n = this.nozzle(); this.telegraph(n, Toxic.TELL);
        // pilot flame: a small flickering tongue of the cone at the nozzle
        this.pilot = sc.add.sprite(n.x, n.y, 'r3-flame', 0).setOrigin(1, 0.5).setScale(0.25).setDepth(41).setFlipX(this.flipX);
        if (this.flipX) this.pilot.setOrigin(0, 0.5);
        if (sc.anims.exists('r3-flame-a')) this.pilot.play('r3-flame-a');
        return;
      }
      if (Math.abs(dx) > Toxic.TRIGGER - 20) this.walk(Toxic.SPEED); else { b.setVelocityX(0); this.face(p); this.anim('aim'); }
    } else if (this.state === 'tell') {
      if (time > this.until) {
        this.pilot?.destroy(); this.pilot = null;
        this.state = 'burn'; this.until = time + Toxic.BURN; this.anim('attack');
        const n = this.nozzle();
        this.cone = sc.add.sprite(n.x, n.y, 'r3-flame', 0).setDepth(57).setFlipX(this.flipX).setOrigin(this.flipX ? 0 : 1, 0.5);
        if (sc.anims.exists('r3-flame-a')) this.cone.play('r3-flame-a');
        sc.sfx?.loop?.('flame');
      }
    } else if (this.state === 'burn') {
      const n = this.nozzle(), f = this.facing();
      if (this.cone) this.cone.setPosition(n.x, n.y);
      // hurt zone: the cone's inner 44 x 12 (fair: the outer flicker never kills)
      const r = { x: f < 0 ? n.x - 44 : n.x, y: n.y - 6, w: 44, h: 12 };
      if (rectHit(p, r)) p.hurt('flame:Toxic');
      if (time > this.until) { this.cone?.destroy(); this.cone = null; this.scene.sfx?.stopLoop?.('flame'); this.state = 'walk'; this.next = time + Toxic.COOL; }
    }
  }
  destroy(fromScene) { if (this.cone) this.scene?.sfx?.stopLoop?.('flame'); this.pilot?.destroy(); this.cone?.destroy(); super.destroy(fromScene); }
  die(from) { trooperDeath(this, from); }
}
Toxic.SPEED = 38; Toxic.TRIGGER = 78; Toxic.TELL = 700; Toxic.BURN = 900; Toxic.COOL = 1500;

// ---------------------------------------------------------------- 4. xeno: fast crawler, crouch tell then pounce
export class Xeno extends R3Enemy {
  constructor(scene, x, y) {
    super(scene, x, y, 'xeno', 2, 300);
    this.body.setSize(32, 16).setOffset((this.width - 32) / 2, this.height - 16);
    this.anim('move'); this.state = 'run'; this.next = scene.time.now + 500;
    this.shotHead = 10;   // low crawler: level shots still connect
  }
  update(time) {
    const sc = this.scene, p = sc.player, b = this.body; if (!p) return;
    const dx = p.x - this.x;
    if (this.state === 'run') {
      this.anim('move');
      if (time > this.turnAt) { this.dir = dx > 0 ? 1 : -1; this.turnAt = 0; }
      if (!this.turnAt && Math.sign(dx) !== this.dir && Math.abs(dx) > 30) this.turnAt = time + 700;   // overshoots, then doubles back
      this.walk(Xeno.SPEED);
      if (b.blocked.down && time > this.next && Math.abs(dx) < Xeno.RANGE && Math.abs(dx) > 30 && Math.sign(dx) === this.dir && this.sameFloor(p, 40) && this.canFire(10)) {
        this.state = 'crouch'; this.until = time + Xeno.TELL; b.setVelocityX(0); this.anim('crouch');
        this.telegraph({ x: this.x + this.facing() * 16, y: this.y - 12 }, Xeno.TELL); sc.sfx?.play('xeno-screech', 0.8);
      }
    } else if (this.state === 'crouch') {
      b.setVelocityX(0);
      if (time > this.until) {
        this.state = 'leap'; this.anim('attack');
        b.setVelocity(this.facing() * Xeno.LEAP_VX, Xeno.LEAP_VY); this.leapT = time; sc.sfx?.play('xeno-pounce', 0.8);
      }
    } else if (this.state === 'leap') {
      if (b.blocked.down && time - this.leapT > 150) { this.state = 'run'; this.next = time + rnd(1100, 1600); }
    }
  }
  die() { gooDeath(this, 'acid'); }
}
Xeno.SPEED = 120; Xeno.RANGE = 120; Xeno.TELL = 380; Xeno.LEAP_VX = 170; Xeno.LEAP_VY = -230;

// ---------------------------------------------------------------- 5. mutant: slow tank, close-range slash
export class Mutant extends R3Enemy {
  constructor(scene, x, y) {
    super(scene, x, y, 'mutant', 10, 800);
    this.body.setSize(22, 42).setOffset((this.width - 22) / 2, this.height - 42);
    this.anim('move'); this.state = 'walk'; this.next = scene.time.now; this.knock = false;
  }
  update(time) {
    const sc = this.scene, p = sc.player, b = this.body; if (!p) return;
    const dx = p.x - this.x;
    if (this.state === 'walk') {
      this.dir = dx > 0 ? 1 : -1; this.anim('move'); this.walk(Mutant.SPEED);
      if (Math.abs(dx) < Mutant.REACH + 10 && this.sameFloor(p, 30) && time > this.next && this.canFire(8)) {
        this.state = 'tell'; this.until = time + Mutant.TELL; b.setVelocityX(0); this.face(p); this.anim('attack');
        this.telegraph({ x: this.x + this.facing() * 14, y: this.y - 40 }, Mutant.TELL); sc.sfx?.play('mutant-roar', 0.8);
      }
    } else if (this.state === 'tell') {
      b.setVelocityX(0);
      if (time > this.until) { this.state = 'slash'; this.until = time + 180; this.x += this.facing() * 3; }
    } else if (this.state === 'slash') {
      const f = this.facing(), r = { x: f < 0 ? this.x - Mutant.REACH : this.x, y: this.y - 34, w: Mutant.REACH, h: 30 };
      if (rectHit(p, r)) p.hurt('slash:Mutant');
      if (time > this.until) { this.state = 'walk'; this.next = time + Mutant.COOL; this.anim('move'); }
    }
  }
  die() { gooDeath(this, 'purple', 1.25); }
}
Mutant.SPEED = 26; Mutant.REACH = 26; Mutant.TELL = 450; Mutant.COOL = 1200;

// ---------------------------------------------------------------- 6. walker: spider-leg turret, mini-boss with a charged beam
export class Walker extends R3Enemy {
  constructor(scene, x, y) {
    super(scene, x, y, 'walker', 40, 3000);
    this.body.setSize(44, 48).setOffset((this.width - 44) / 2, this.height - 48);
    this.anim('move'); this.state = 'walk'; this.until = scene.time.now + 1600; this.miniBoss = true; this.knock = false;
    this.bigBoom = true; this.setDepth(38);
  }
  muzzle() { const f = this.facing(); return { x: this.x + f * 40, y: this.y - 36 }; }
  update(time) {
    const sc = this.scene, p = sc.player, b = this.body; if (!p) return;
    const dx = p.x - this.x, cam = sc.cameras.main;
    if (this.state === 'walk') {
      this.anim('move'); this.dir = dx > 0 ? 1 : -1;
      // keeps its distance: never closer than 110 px, and stays inside the screen once it has arrived
      const inside = this.x < cam.scrollX + sc.scale.width - 40;
      if (Math.abs(dx) > 110 || !inside) this.walk(Walker.SPEED); else { b.setVelocityX(0); this.face(p); }
      if (time > this.until && inside && this.canFire(30) && this.claimTell(time, Walker.TELL + Walker.BEAM)) {
        this.state = 'charge'; this.until = time + Walker.TELL; b.setVelocityX(0); this.face(p); this.anim('charge');
        const m = this.muzzle(), f = this.facing();
        this.telegraph(m, Walker.TELL);
        // long, obvious tell: a dotted aim line across the screen at the beam's height, blinking faster as it charges
        const len = f < 0 ? m.x - cam.scrollX : cam.scrollX + sc.scale.width - m.x;
        this.tell = beamGfx(sc, m.x, m.y, f, len, 'tell');
        sc.tweens.add({ targets: this.tell, alpha: { from: 0.35, to: 1 }, duration: 160, yoyo: true, repeat: -1, ease: 'Stepped', easeParams: [2] });
        sc.sfx?.play('telegraph');
      }
    } else if (this.state === 'charge') {
      if (time > this.until) {
        this.tell?.destroy(); this.tell = null;
        this.state = 'beam'; this.until = time + Walker.BEAM; this.anim('fire');
        const m = this.muzzle(), f = this.facing();
        const len = f < 0 ? m.x - cam.scrollX + 20 : cam.scrollX + sc.scale.width - m.x + 20;
        this.beam = beamGfx(sc, m.x, m.y, f, len, 'beam');
        this.beamRect = { x: f < 0 ? m.x - len : m.x, y: m.y - 3, w: len, h: 6 };
        sc.fx?.muzzle(m.x, m.y, f, 0, 1.3); sc.fx?.shake?.(120, 0.003); sc.sfx?.play('laser-bolt', 1);
      }
    } else if (this.state === 'beam') {
      if (this.beam) this.beam.setAlpha(((time / 60) | 0) % 2 ? 1 : 0.85);
      if (rectHit(p, this.beamRect)) p.hurt('beam:Walker');
      if (time > this.until) { this.beam?.destroy(); this.beam = null; this.state = 'walk'; this.until = time + rnd(1700, 2300); }
    }
  }
  destroy(fromScene) { this.tell?.destroy(); this.beam?.destroy(); super.destroy(fromScene); }
  die() {
    const sc = this.scene, x = this.x, y = this.y;
    this.scorePop(56);
    for (let i = 0; i < 5; i++) sc.time.delayedCall(i * 110, () => sc.fx?.explode(x + rnd(-22, 22), y - rnd(10, 50), 1.1));
    sc.fx?.shake?.(400, 0.008); sc.sfx?.play('boom', 1);
    gooSplash(sc, x, y);
    this.destroy();
  }
}
Walker.SPEED = 24; Walker.TELL = 1300; Walker.BEAM = 520;
// beam and its aim line as crisp pixel bands (Graphics: exact 1px rows, no texture tiling)
function beamGfx(sc, x, y, f, len, kind) {
  const g = sc.add.graphics().setDepth(57);
  const x0 = Math.round(f < 0 ? x - len : x), y0 = Math.round(y), L = Math.round(len);
  if (kind === 'tell') {
    g.fillStyle(0xff3c3c, 1);
    for (let i = 0; i < L; i += 4) g.fillRect(f < 0 ? x0 + L - i - 3 : x0 + i, y0, 3, 1);
  } else {
    const rows = [[-4, 0x0c0a12], [-3, 0x146eaa], [-2, 0x28c8f0], [-1, 0xa0faff], [0, 0xffffff], [1, 0xa0faff], [2, 0x28c8f0], [3, 0x146eaa], [4, 0x0c0a12]];
    for (const [dy, c] of rows) { g.fillStyle(c, 1); g.fillRect(x0, y0 + dy, L, 1); }
    g.fillStyle(0xffffff, 1); g.fillRect(f < 0 ? x0 + L - 6 : x0, y0 - 3, 6, 7);   // muzzle bloom
  }
  return g;
}
// the specimen jar shatters: a small acid splash at the walker's feet
function gooSplash(sc, x, y) {
  const s = sc.add.sprite(Math.round(x), Math.round(y) + 1, 'r3-goo-acid', 0).setOrigin(0.5, 1).setDepth(44).setScale(1.4);
  if (sc.anims.exists('r3-goo-acid-a')) { s.play('r3-goo-acid-a'); s.once('animationcomplete', () => sc.time.delayedCall(700, () => s.destroy())); } else s.destroy();
}

export const ROSTER3 = { hazmat: Hazmat, clawbot: Clawbot, toxic: Toxic, xeno: Xeno, mutant: Mutant, walker: Walker };
