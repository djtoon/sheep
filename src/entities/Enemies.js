// Enemy roster. Every enemy: hp, score, update(time, dt, scene), onDeath(). Collide with scene.solids unless flying.
const rnd = Phaser.Math.Between;

class Enemy extends Phaser.Physics.Arcade.Sprite {
  constructor(scene, x, y, tex, hp, score) {
    super(scene, x, y, tex);
    scene.add.existing(this); scene.physics.add.existing(this);
    this.setOrigin(0.5, 1).setDepth(40);
    this.hp = hp; this.score = score; this.flash = 0;
  }
  damage(n, from) {
    if (!this.active) return;
    this.hp -= n;
    const now = this.scene.time.now; // throttled flash: sustained fire flickers instead of a solid white silhouette
    if (now > (this.nextFlash || 0)) { this.nextFlash = now + 110; this.flash = 34; this.setTint(0x605040).setTintMode(Phaser.TintModes.ADD); }
    if (this.hp <= 0) { this.scene.enemyKilled?.(this, from); this.die(from); }
    else {
      this.scene.sfx?.play('hit');
      // tiny knock-back on non-lethal hits (movers only)
      if (this.body && !this.body.immovable && this.body.allowGravity && from && from.body) this.x += Math.sign(from.body.velocity.x || 1) * 2;
    }
  }
  preUpdate(t, dt) {
    super.preUpdate(t, dt);
    if (this.flash > 0 && (this.flash -= dt) <= 0) this.clearTint();
    const cam = this.scene.cameras.main, W = this.scene.scale.width;
    if (this.x < cam.scrollX - 80 || this.y > this.scene.level.height + 60 || (this.dir > 0 && this.x > cam.scrollX + W + 60)) this.destroy();
  }
  die() {
    this.scene.addScore(this.score, this.x, this.y - this.height / 2);
    this.scene.fx.explode(this.x, this.y - this.height / 2, this.bigBoom ? 1.4 : 0.8);
    this.destroy();
  }
  // fair-fire rules: only from inside the visible screen, never at a dead / respawning player, never once the boss is up
  // (the boss owns the danger then) or after the stage is won
  canFire(margin = 12) {
    const sc = this.scene, p = sc.player, cam = sc.cameras.main;
    return p && !p.dead && !sc.cleared && !sc.boss && sc.flow === 'play' && this.x > cam.scrollX + margin && this.x < cam.scrollX + sc.scale.width - margin && this.y > 8;
  }
  // One warning on screen at a time: a shooter must claim the scene's shot lock before its tell, and holds it through
  // the tell + burst + a short gap. Stops crossfire where two dodges conflict (jump one, prone the other).
  claimTell(time, ms) {
    const sc = this.scene;
    if ((sc.shotLock || 0) > time && sc.shotLockBy !== this && sc.shotLockBy && sc.shotLockBy.active) return false;
    sc.shotLock = time + ms + (sc.level?.spawns?.shotGap ?? Enemy.SHOT_GAP); sc.shotLockBy = this; return true;
  }
  // wind-up tell before a shot: scene event for FX/audio + a glint at the muzzle (fallback visual)
  telegraph(m, ms) {
    const sc = this.scene;
    sc.events.emit('telegraph', { enemy: this, x: m.x, y: m.y, ms });
    if (!(sc.hooked && sc.hooked.telegraph) && sc.fx && sc.fx.oneShot) for (let i = 0; i < 2; i++) sc.time.delayedCall(i * (ms / 2), () => this.active && sc.fx.oneShot(m.x, m.y, 'hit', 'eflash', 57));
  }
  shootAt(target, speed = 110, from, quant = 0) {
    const o = from || { x: this.x, y: this.y - this.height * 0.6 };
    const aimP = target.hurtCenter ? target.hurtCenter() : { x: target.x, y: target.y - 18 };
    let a = Phaser.Math.Angle.Between(o.x, o.y, aimP.x, aimP.y);
    if (quant) a = Math.round(a / quant) * quant;   // Contra guns aim in fixed steps: readable, dodgeable
    if (this.burstA !== undefined) a = this.burstA;  // follow-up rounds of a burst keep the first round's line (dodging it is rewarded)
    this.scene.fireEnemy(o.x, o.y, Math.cos(a) * speed, Math.sin(a) * speed, this.constructor.name + (this.kind ? '/' + this.kind : '') + '@' + Math.round(this.x) + ',' + Math.round(this.y));
  }
}

// Contra's grunt. Each one gets a personality so a wave reads as individuals, not a conga line:
//   runner: charges straight   hopper: bounds along in little hops   gunner: stops once on screen, tells, fires one shot, runs on
// stages 2-3 reskin the jungle grunts: level.gruntSkin names a texture with the soldier sheet's frame layout,
// and anims '<skin>-run', '<skin>-aim', ... mirror the 'soldier-*' ones
const gruntTex = (scene) => { const k = scene.level?.gruntSkin; return k && scene.textures.exists(k) ? k : 'soldier'; };
const skinKey = (e, key) => e.texture.key !== 'soldier' && typeof key === 'string' ? key.replace(/^soldier-/, e.texture.key + '-') : key;

export class Soldier extends Enemy {
  play(key, ...a) { return super.play(skinKey(this, key), ...a); }
  constructor(scene, x, y) {
    super(scene, x, y, gruntTex(scene), 1, 100);
    this.body.setSize(14, 30).setOffset((this.width - 14) / 2, this.height - 30);
    this.dir = -1; this.play('soldier-run'); this.decided = 0;
    const seq = scene.soldierSeq = (scene.soldierSeq || 0) + 1;
    this.kind = ['runner', 'gunner', 'runner', 'hopper', 'gunner', 'runner', 'hopper'][seq % 7];
    const gFrom = scene.level?.spawns?.gunnersFrom ?? Soldier.GUNNERS_FROM;   // a stage's spawn list may set its own
    if (this.kind === 'gunner' && scene.cameras.main.scrollX < gFrom) this.kind = 'runner';
    else if (this.kind === 'runner' && Math.random() < (scene.level?.spawns?.gunnerBias ?? 0)) this.kind = 'gunner';   // later stages: more grunts stop to shoot   // first stretch: grunts only charge, riflemen do the shooting
    this.speed = Soldier.SPEED * (0.9 + ((seq * 37) % 21) / 100);   // 0.90-1.10x, fixed per soldier
    this.born = scene.time.now; this.nextHop = this.born + rnd(500, 1100); this.stopUntil = 0; this.fired = 0;
  }
  // the nearest soldier just ahead of us on the same floor (same heading, or planted to shoot), within 30 px
  ahead() {
    let best = null, bd = 30;
    for (const o of this.scene.enemies.getChildren()) {
      if (o === this || !o.active || !(o instanceof Soldier)) continue;
      const d = (o.x - this.x) * this.dir;
      if (d > -2 && d < bd && Math.abs(o.y - this.y) < 8 && (o.dir === this.dir || o.stopUntil > this.scene.time.now)) { bd = d; best = o; }
    }
    return best;
  }
  update(time) {
    const b = this.body, sc = this.scene, p = sc.player;
    // gunner: plant, tell, shoot, then carry on toward the sheep
    if (this.stopUntil > time) { b.setVelocityX(0); if (p) this.setFlipX(p.x > this.x); return; }
    if (this.stopUntil && this.anims.currentAnim?.key !== skinKey(this, 'soldier-run')) { this.stopUntil = 0; this.play('soldier-run'); if (p) this.dir = p.x > this.x ? 1 : -1; }
    if (this.kind === 'gunner' && !this.fired && p && b.blocked.down && time - this.born > 700 && this.canFire(30) && Math.abs(p.x - this.x) > 70 && Math.abs(p.x - this.x) < 300 && this.claimTell(time, Soldier.TELL)) {
      this.fired = 1; this.stopUntil = time + Soldier.TELL + 420;
      const kneel = this.y - p.y > -4 && Math.random() < 0.5;
      this.setFlipX(p.x > this.x); this.play(kneel ? 'soldier-kneel-aim' : 'soldier-aim'); b.setVelocityX(0);
      const m = () => ({ x: this.x + (p.x > this.x ? 27 : -27), y: this.y - (kneel ? 24 : 26) });
      this.telegraph(m(), Soldier.TELL);
      sc.time.delayedCall(Soldier.TELL, () => {
        if (!this.active || !this.canFire(8)) return;
        const mm = m(); this.shootAt(sc.player, Soldier.BULLET, mm);
        sc.fx.muzzle(mm.x, mm.y, p.x > this.x ? 1 : -1, 0, 0.7);
        this.play(kneel ? 'soldier-kneel-shoot' : 'soldier-shoot');
      });
      return;
    }
    // keep >= 24 px apart: tail a slower leader at its pace, leap over one that has stopped to shoot
    const lead = b.blocked.down ? this.ahead() : null;
    let v = this.speed;
    if (lead) {
      const d = (lead.x - this.x) * this.dir;
      if (lead.stopUntil > time) { if (d < 26) { if (p && Math.abs(p.x - this.x) > 80) b.setVelocityY(-300); else v = 0; } }
      else v = d < 24 ? Math.min(v, lead.speed) * 0.35 : Math.min(v, lead.speed);
    }
    b.setVelocityX(this.dir * v);
    this.setFlipX(this.dir > 0);
    if (this.kind === 'hopper' && b.blocked.down && time > this.nextHop && !lead && !(p && Math.abs(p.x - this.x) < 70)) { this.nextHop = time + rnd(900, 1500); b.setVelocityY(-230); }
    // turrets are not obstacles: runners pass in front of them (turret depth 36 < soldier 40); only terrain walls make them jump
    // ledge logic: walk off onto lower ground, hop small gaps, otherwise usually turn back (sometimes leap to their doom, Contra-style)
    if (b.blocked.down && time > this.decided && !sc.groundAhead(this.x + this.dir * 12, this.y)) {
      this.decided = time + 400;
      const lower = sc.groundYAt(this.x + this.dir * 20);
      const far = sc.groundYAt(this.x + this.dir * 56);
      if (lower < sc.level.height && lower - this.y < 90) {
        // never drop onto the sheep: if it is standing below the edge, turn back instead
        if (p && !p.dead && Math.abs(p.x - (this.x + this.dir * 24)) < 44 && p.y > this.y) this.dir *= -1;
      }
      else if (far <= this.y + 4) b.setVelocityY(-280);
      else if (Math.random() < 0.2) b.setVelocityY(-280);
      else this.dir *= -1;
    }
    // walls: hop; if we are still stuck on the next try, turn round (never pile up against it)
    if (b.blocked.down && (b.blocked.left || b.blocked.right)) {
      if (this.wallT && time - this.wallT < 900) { this.dir *= -1; this.wallT = 0; } else { this.wallT = time; b.setVelocityY(-280); }
    }
  }
  die(from) {
    this.scene.addScore(this.score, this.x, this.y - 30);
    this.scene.fx.soldierDeath(this, from);
    this.destroy();
  }
}
Soldier.SPEED = 84;   // px/s, a touch slower than the sheep (100) so you can always outrun a chaser
Soldier.TELL = 450; Soldier.BULLET = 105;
Enemy.SHOT_GAP = 350;   // ms of quiet after one enemy's tell+shot before the next enemy may start its tell
Soldier.GUNNERS_FROM = 1800;   // camera x where running grunts start stopping to shoot

// Stands (on ground or a ledge) and fires aimed shots. Crouches between volleys.
export class Rifleman extends Enemy {
  play(key, ...a) { return super.play(skinKey(this, key), ...a); }
  constructor(scene, x, y) {
    super(scene, x, y, gruntTex(scene), 1, 200);   // Contra: every foot soldier dies in one hit
    this.body.setSize(14, 30).setOffset((this.width - 14) / 2, this.height - 30);
    this.next = scene.time.now + 900;
    // art: alternate standing / kneeling riflemen (visual only; hitbox unchanged)
    this.kneel = (Math.floor(x / 40) % 3) === 2;
    this.setDepth(39);   // runners always draw in front of riflemen, so overlaps stay two distinct outlined figures
    this.play(this.kneel ? 'soldier-kneel-aim' : 'soldier-aim');
  }
  update(time) {
    const p = this.scene.player; if (!p) return;
    this.body.setVelocityX(0);
    this.setFlipX(p.x > this.x);
    const mx = 27, my = this.kneel ? 24 : 26;   // rifle tip in the sprite
    const muzzle = () => ({ x: this.x + (p.x > this.x ? mx : -mx), y: this.y - my });
    if (!this.canFire()) { this.next = Math.max(this.next, time + 900); this.windup = 0; return; }   // ~0.9 s on screen + 0.45 s tell before the first shot
    // tell (0.45 s glint) -> shot -> 1.4-2.0 s rest. Occasionally a 2-round burst.
    if (!this.windup && time > this.next - Rifleman.TELL) {
      if (this.claimTell(time, Rifleman.TELL + 260)) { this.windup = 1; this.telegraph(muzzle(), Rifleman.TELL); } else this.next = time + Rifleman.TELL + 250;
    }
    if (time > this.next && this.windup) {
      this.next = time + rnd(1700, 2500); this.windup = 0;
      const shot = () => {
        if (!this.active || !this.canFire()) return;
        const m = muzzle();
        this.shootAt(this.scene.player, Rifleman.BULLET, m);
        this.scene.fx.muzzle(m.x, m.y, p.x > this.x ? 1 : -1, 0, 0.7);
        this.play(this.kneel ? 'soldier-kneel-shoot' : 'soldier-shoot');
      };
      this.burstA = undefined; shot();
      if (Math.random() < 0.2) {
        const m0 = muzzle(), c = p.hurtCenter(); this.burstA = Math.atan2(c.y - m0.y, c.x - m0.x);
        this.scene.time.delayedCall(260, () => { shot(); this.burstA = undefined; });
      }
    }
  }
  die(from) { this.scene.addScore(this.score, this.x, this.y - 30); this.scene.fx.soldierDeath(this, from); this.destroy(); }
}

Rifleman.TELL = 450; Rifleman.BULLET = 115;

// Wall/ground turret, rotates barrel toward player in 16 steps.
export class Turret extends Enemy {
  constructor(scene, x, y) {
    super(scene, x, y, 'turret', 8, 500);
    this.body.setAllowGravity(false).setImmovable(true);
    this.body.setSize(44, 52).setOffset((this.width - 44) / 2, this.height - 52);
    this.next = scene.time.now + 1200; this.bigBoom = true; this.play('turret-idle');
    this.setDepth(36);   // behind riflemen (39) and runners (40)
  }
  update(time) {
    const p = this.scene.player; if (!p) return;
    this.setFlipX(p.x > this.x);
    const m = { x: this.x + (p.x > this.x ? 32 : -32), y: this.y - 44 };   // barrel tip
    if (!this.canFire(20)) { this.next = Math.max(this.next, time + 600); this.windup = 0; return; }
    if (!this.windup && time > this.next - Turret.TELL) {
      if (this.claimTell(time, Turret.TELL + 180)) { this.windup = 1; this.telegraph(m, Turret.TELL); } else this.next = time + Turret.TELL + 250;
    }
    if (time > this.next && this.windup) {
      this.next = time + 1900; this.windup = 0;
      this.play('turret-fire').chain('turret-idle');
      const q = Math.PI / 8;   // 16 aim steps
      const c = p.hurtCenter(); this.burstA = Math.round(Math.atan2(c.y - m.y, c.x - m.x) / q) * q;   // both rounds on one line
      this.shootAt(p, Turret.BULLET, m, q);
      this.scene.time.delayedCall(180, () => { if (this.active && this.canFire(20)) this.shootAt(this.scene.player, Turret.BULLET, m, q); this.burstA = undefined; });
      this.scene.fx.muzzle(m.x, m.y, p.x > this.x ? 1 : -1, 0, 1);
    }
  }
}

Turret.TELL = 600; Turret.BULLET = 115;

// Flying drone: swoops in a sine path, drops shots.
export class Drone extends Enemy {
  constructor(scene, x, y) {
    super(scene, x, y, 'drone', 2, 300);
    this.setOrigin(0.5, 0.5); this.body.setAllowGravity(false);
    this.body.setSize(28, 18).setOffset((this.width - 28) / 2, 11);
    this.baseY = y; this.t0 = scene.time.now; this.next = scene.time.now + 1500; this.play('drone-fly');
  }
  update(time) {
    const p = this.scene.player; if (!p) return;
    const dx = p.x + 60 - this.x;
    this.body.setVelocityX(Phaser.Math.Clamp(dx, -80, 80));
    this.y = this.baseY + Math.sin((time - this.t0) / 380) * 22;
    const m = { x: this.x - 2, y: this.y + 14 };
    if (!this.canFire(16)) { this.next = Math.max(this.next, time + 700); this.windup = 0; return; }
    if (!this.windup && time > this.next - 400) {
      if (this.claimTell(time, 400)) { this.windup = 1; this.telegraph(m, 400); } else this.next = time + 650;
    }
    if (time > this.next && this.windup) { this.next = time + 2000; this.windup = 0; this.shootAt(p, 110, m, Math.PI / 8); }
  }
}

export const ENEMY_TYPES = { soldier: Soldier, rifleman: Rifleman, turret: Turret, drone: Drone };
