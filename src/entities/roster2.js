// Stage-2 enemy roster (night base B-02): exports ROSTER2 = { typeName: Class }.
// Same contract as Enemies.js: hp, score, update(time), damage(n, from), die(from); fair-fire rules (canFire),
// one tell on screen at a time (claimTell -> telegraph -> shot), all bullets through scene.fireEnemy.
// Art: assets/roster2/<type>.png (see assets/parts/roster2.json), origin bottom-centre, facing LEFT (flipX = facing right).
const rnd = Phaser.Math.Between;
const SHOT_GAP = 350;   // same quiet gap as stage 1 after a tell+shot

class Enemy2 extends Phaser.Physics.Arcade.Sprite {
  constructor(scene, x, y, tex, hp, score) {
    super(scene, x, y, tex);
    scene.add.existing(this); scene.physics.add.existing(this);
    this.setOrigin(0.5, 1).setDepth(40);
    this.hp = hp; this.score = score; this.flash = 0; this.kind = tex;
  }
  // hit box in art pixels (w x h, bottom-centred, optional x shift toward the facing side)
  box(w, h, dx = 0) { this.bw = w; this.bh = h; this.bdx = dx; this.body.setSize(w, h); this.fitBox(); }
  fitBox() { if (this.bw) this.body.setOffset((this.width - this.bw) / 2 + (this.flipX ? -this.bdx : this.bdx), this.height - this.bh - 1); }   // -1: the ink row under the feet sinks into the floor line
  face(right) { if (this.flipX !== right) { this.setFlipX(right); this.fitBox(); } }
  get fdir() { return this.flipX ? 1 : -1; }
  damage(n, from) {
    if (!this.active || this.dead) return;
    if (this.blocks && this.blocks(from)) { this.ricochet(from); return; }
    this.hp -= n;
    const now = this.scene.time.now;
    if (now > (this.nextFlash || 0)) { this.nextFlash = now + 110; this.flash = 34; this.setTint(0x605040).setTintMode(Phaser.TintModes.ADD); }
    if (this.hp <= 0) { this.dead = true; this.scene.enemyKilled?.(this, from); this.die(from); }
    else { this.scene.sfx?.play('hit'); this.onHit?.(from); }
  }
  ricochet(from) {
    const sc = this.scene; sc.sfx?.play('ricochet', 0.7);
    if (from && from.body) sc.fx.impact(from.x, from.y, { ricochet: true });
  }
  preUpdate(t, dt) {
    super.preUpdate(t, dt);
    if (this.flash > 0 && (this.flash -= dt) <= 0) this.clearTint();
    const cam = this.scene.cameras.main;
    if (this.x < cam.scrollX - 90 || this.y > this.scene.level.height + 60) this.destroy();
  }
  canFire(margin = 12) {
    const sc = this.scene, p = sc.player, cam = sc.cameras.main;
    return p && !p.dead && !sc.cleared && !sc.boss && sc.flow === 'play' && this.x > cam.scrollX + margin && this.x < cam.scrollX + sc.scale.width - margin && this.y > 8;
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
  aimAngle(o, dy = 0, quant = 0) {
    const c = this.scene.player.hurtCenter();
    let a = Math.atan2(c.y + dy - o.y, c.x - o.x);
    if (quant) a = Math.round(a / quant) * quant;
    return a;
  }
  fireA(o, a, speed) {
    this.scene.fireEnemy(o.x, o.y, Math.cos(a) * speed, Math.sin(a) * speed, this.kind + '@' + Math.round(this.x) + ',' + Math.round(this.y));
  }
  // walker death: the body plays its hit/collapse frames while flung back, then pops in a small blast
  wreck(from, anim, boom = 0.8, fling = 18) {
    const sc = this.scene, dir = from && from.x < this.x ? 1 : -1;
    sc.addScore(this.score, this.x, this.y - this.height / 2);
    const d = sc.add.sprite(this.x, this.y, this.texture.key).setOrigin(0.5, 1).setDepth(45).setFlipX(this.flipX);
    if (sc.anims.exists(anim)) d.play(anim);
    sc.fx.spark?.(this.x, this.y - this.height * 0.6, 6);
    sc.sfx?.play('enemy-die');
    sc.tweens.add({ targets: d, x: this.x + dir * fling, duration: 260, ease: 'Quad.easeOut' });
    sc.time.delayedCall(330, () => { sc.fx.explode(d.x, d.y - d.height * 0.35, boom); });
    sc.tweens.add({ targets: d, alpha: 0, delay: 700, duration: 260, onComplete: () => d.destroy() });
    this.destroy();
  }
}

// muzzle point from art coords (mx < 0 = in front of the unit, my < 0 = above its feet), mirrored with facing
function M(e, mx, my) { return { x: e.x + (e.flipX ? -mx : mx), y: e.y + my }; }

// ------------------------------------------------------------------ trooper
// Olive armoured robot with a shotgun. Walks in, plants, tells, fires a 3-way spread (middle round on you: jump,
// prone or step into a gap), walks on.
export class Trooper extends Enemy2 {
  constructor(scene, x, y) {
    super(scene, x, y, 'trooper', 3, 300);
    this.box(16, 36); this.play('trooper-walk');
    this.next = scene.time.now + rnd(700, 1100); this.state = 'walk';
  }
  update(time) {
    const p = this.scene.player; if (!p || this.dead) return;
    const b = this.body;
    this.face(p.x > this.x);
    if (this.state === 'walk') {
      b.setVelocityX(Math.abs(p.x - this.x) > 70 ? this.fdir * Trooper.SPEED : 0);
      if (b.blocked.down && !this.scene.groundAhead(this.x + this.fdir * 10, this.y)) b.setVelocityX(0);
      if (this.canFire(20) && Math.abs(p.x - this.x) < 230 && time > this.next) {
        if (this.claimTell(time, Trooper.TELL + 200)) {
          this.state = 'aim'; b.setVelocityX(0); this.play('trooper-aim');
          this.fireAt = time + Trooper.TELL; this.telegraph(M(this, -19, -31), Trooper.TELL);
        } else this.next = time + 300;
      }
    } else if (this.state === 'aim') {
      b.setVelocityX(0);
      if (time > this.fireAt) {
        if (this.canFire(12)) {
          const o = M(this, -19, -31), a = this.aimAngle(o, 0, Math.PI / 16);
          for (const s of [-Trooper.FAN, 0, Trooper.FAN]) this.fireA(o, a + s, Trooper.BULLET);
          this.scene.sfx?.play('shotgun');
          this.scene.fx.muzzle(o.x, o.y, this.fdir, 0, 0.8);
        }
        this.play('trooper-fire').chain('trooper-aim');
        this.state = 'hold'; this.holdUntil = time + 450;
      }
    } else if (this.state === 'hold') {
      b.setVelocityX(0);
      if (time > this.holdUntil) { this.state = 'walk'; this.play('trooper-walk'); this.next = time + rnd(2200, 2900); }
    }
  }
  die(from) { this.wreck(from, 'trooper-die', 0.7); }
}
Trooper.SPEED = 38; Trooper.TELL = 520; Trooper.BULLET = 105; Trooper.FAN = 0.3;

// ------------------------------------------------------------------ shield
// Riot robot. The shield soaks every level shot from the front (ricochet); shoot it from above (jump-shoot / aim down
// from a ledge) or from behind. Advances slowly, turns around a beat after you get behind it, and now and then
// pokes a pistol round the shield: one slow, level shot (jump it).
export class Shield extends Enemy2 {
  constructor(scene, x, y) {
    super(scene, x, y, 'shield', 5, 500);
    this.box(22, 38); this.play('shield-walk');
    this.next = scene.time.now + rnd(1600, 2400); this.state = 'walk'; this.turnAt = 0;
    this.face(false);
  }
  // blocked: a bullet travelling into the shield face, below the shield's top edge
  blocks(from) {
    if (!from || !from.body) return false;
    const vx = from.body.velocity.x, into = this.flipX ? vx < -1 : vx > 1;
    const inFront = this.flipX ? from.x > this.x - 2 : from.x < this.x + 2;
    const shieldTop = this.y - Shield.SHIELD_H;
    return into && inFront && from.y > shieldTop && Math.abs(from.body.velocity.y) < Math.abs(vx) * 1.2;
  }
  update(time) {
    const p = this.scene.player; if (!p || this.dead) return;
    const b = this.body, behind = this.flipX ? p.x < this.x - 6 : p.x > this.x + 6;
    // FX ricochet flag: the player is square in front of the shield
    this.armor = !behind && p.hurtCenter().y > this.y - Shield.SHIELD_H;
    if (behind) { if (!this.turnAt) this.turnAt = time + Shield.TURN; if (time > this.turnAt) { this.face(p.x > this.x); this.turnAt = 0; } }
    else this.turnAt = 0;
    if (this.state === 'walk') {
      b.setVelocityX(this.fdir * Shield.SPEED);
      if (Math.abs(p.x - this.x) < 34 || (b.blocked.down && !this.scene.groundAhead(this.x + this.fdir * 12, this.y))) b.setVelocityX(0);
      if (!behind && this.canFire(24) && Math.abs(p.x - this.x) < 240 && time > this.next) {
        if (this.claimTell(time, Shield.TELL + 200)) {
          this.state = 'brace'; b.setVelocityX(0); this.play('shield-brace');
          this.fireAt = time + Shield.TELL; this.telegraph(M(this, -16, -26), Shield.TELL);
        } else this.next = time + 400;
      }
    } else if (this.state === 'brace') {
      b.setVelocityX(0);
      if (time > this.fireAt) {
        if (this.canFire(12)) { const o = M(this, -16, -26); this.fireA(o, this.flipX ? 0 : Math.PI, Shield.BULLET); this.scene.sfx?.play('enemy-shot'); this.scene.fx.muzzle(o.x, o.y, this.fdir, 0, 0.6); }
        this.play('shield-fire'); this.state = 'hold'; this.holdUntil = time + 500;
      }
    } else if (this.state === 'hold') {
      b.setVelocityX(0);
      if (time > this.holdUntil) { this.state = 'walk'; this.play('shield-walk'); this.next = time + rnd(2600, 3400); }
    }
  }
  die(from) { this.armor = false; this.wreck(from, 'shield-die', 0.8, 10); }
}
Shield.SPEED = 20; Shield.TELL = 550; Shield.BULLET = 90; Shield.SHIELD_H = 34; Shield.TURN = 900;

// ------------------------------------------------------------------ sniper
// Skeletal sniper bot. Holds position (ledges), paints you with a laser sight that LOCKS a line, then one fast
// precise round down that line: see the red line, get off it.
export class Sniper extends Enemy2 {
  constructor(scene, x, y) {
    super(scene, x, y, 'sniper', 2, 500);
    this.box(12, 36); this.play('sniper-aim');
    this.next = scene.time.now + 1200; this.state = 'idle';
    this.laser = scene.add.graphics().setDepth(55);
  }
  update(time) {
    const p = this.scene.player; if (!p || this.dead) return;
    this.body.setVelocityX(0);
    const g = this.laser; g.clear();
    if (this.state === 'idle') {
      this.face(p.x > this.x);
      if (this.canFire(20) && time > this.next) {
        if (this.claimTell(time, Sniper.TELL + 250)) {
          const o = M(this, -18, -32); this.lockA = this.aimAngle(o); this.state = 'paint';
          this.fireAt = time + Sniper.TELL; this.telegraph(o, Sniper.TELL); this.scene.sfx?.play('sniper-charge');
        } else this.next = time + 400;
      }
    } else if (this.state === 'paint') {
      const o = M(this, -18, -32), left = this.fireAt - time;
      // thin red sight line along the locked shot; blinks faster in the last 250 ms
      const on = left > 250 ? true : Math.floor(left / 50) % 2 === 0;
      if (on) {
        const L = 480, ex = o.x + Math.cos(this.lockA) * L, ey = o.y + Math.sin(this.lockA) * L;
        g.lineStyle(1, 0xff2a20, left > 250 ? 0.55 : 0.95).lineBetween(o.x, o.y, ex, ey);
        g.fillStyle(0xffe0a0, 1).fillRect(Math.round(o.x) - 1, Math.round(o.y) - 1, 2, 2);
      }
      if (time > this.fireAt) {
        if (this.canFire(12)) { this.fireA(o, this.lockA, Sniper.BULLET); this.scene.sfx?.play('sniper'); this.scene.fx.muzzle(o.x, o.y, Math.cos(this.lockA), Math.sin(this.lockA), 0.9); }
        this.play('sniper-fire').chain('sniper-aim');
        this.state = 'idle'; this.next = time + rnd(2600, 3200);
      }
    }
  }
  destroy(fromScene) { this.laser?.destroy(); super.destroy(fromScene); }
  die(from) { this.laser.clear(); this.wreck(from, 'sniper-die', 0.6); }
}
Sniper.TELL = 950; Sniper.BULLET = 200;

// ------------------------------------------------------------------ tank
// Mini tank: rolls in, stops, tells, fires a pair of level shells from its twin barrels at chest height: go prone under them (or jump clear).
export class Tank extends Enemy2 {
  constructor(scene, x, y) {
    super(scene, x, y, 'tank', 12, 800);
    this.box(54, 36); this.play('tank-roll'); this.bigBoom = true;
    this.state = 'roll'; this.stopAt = scene.time.now + rnd(1400, 2000);
  }
  update(time) {
    const p = this.scene.player; if (!p || this.dead) return;
    const b = this.body;
    if (this.state === 'roll') {
      this.face(p.x > this.x + 40);
      b.setVelocityX(this.fdir * Tank.SPEED); this.anims.play('tank-roll', true);
      if (b.blocked.down && !this.scene.groundAhead(this.x + this.fdir * 20, this.y)) b.setVelocityX(0);
      if ((time > this.stopAt || Math.abs(p.x - this.x) < 120) && this.canFire(24)) {
        if (this.claimTell(time, Tank.TELL + 300)) {
          this.state = 'aim'; b.setVelocityX(0); this.anims.stop(); this.setFrame(0);
          this.fireAt = time + Tank.TELL; this.telegraph(M(this, -32, -37), Tank.TELL);
        } else this.stopAt = time + 400;
      }
    } else if (this.state === 'aim') {
      b.setVelocityX(0);
      if (time > this.fireAt) {
        if (this.canFire(12)) {
          const a = this.flipX ? 0 : Math.PI;
          this.fireA(M(this, -32, -37), a, Tank.BULLET); this.scene.sfx?.play('tank');
          this.scene.time.delayedCall(90, () => this.active && !this.dead && this.canFire(8) && this.fireA(M(this, -32, -28), a, Tank.BULLET));
          this.scene.fx.muzzle(M(this, -32, -32).x, M(this, -32, -32).y, this.fdir, 0, 1);
          this.scene.fx.shake?.(80, 0.002);
        }
        this.play('tank-fire'); this.state = 'wait'; this.waitUntil = time + 1300;
      }
    } else if (this.state === 'wait') {
      b.setVelocityX(0);
      if (time > this.waitUntil) { this.state = 'roll'; this.stopAt = time + rnd(1600, 2400); }
    }
    if (this.hp <= 4 && this.anims.currentAnim?.key !== 'tank-hurt' && this.state === 'wait') this.setFrame(4);
  }
  die(from) {
    const sc = this.scene; sc.addScore(this.score, this.x, this.y - 14);
    const w = sc.add.image(this.x, this.y, 'tank', 5).setOrigin(0.5, 1).setDepth(35).setFlipX(this.flipX);
    sc.fx.explode(this.x, this.y - 14, 1.3); sc.sfx?.play('boom-big');
    sc.time.delayedCall(180, () => sc.fx.explode(this.x + rnd(-10, 10), this.y - 20, 0.8));
    sc.tweens.add({ targets: w, alpha: 0, delay: 1400, duration: 400, onComplete: () => w.destroy() });
    this.destroy();
  }
}
Tank.SPEED = 30; Tank.TELL = 650; Tank.BULLET = 115;

// ------------------------------------------------------------------ drone2
// Armoured gatling drone: strafes ahead of you, swapping sides of your head, and fires 3-round bursts down one
// locked 16-step line (the whole burst follows the first round's line: step off it).
export class Drone2 extends Enemy2 {
  constructor(scene, x, y) {
    if (y > 150) y = 60 + Math.random() * 40;
    super(scene, x, y, 'drone2', 4, 400);
    this.setOrigin(0.5, 0.5); this.body.setAllowGravity(false);
    this.body.setSize(34, 24).setOffset((this.width - 34) / 2, 12);
    this.baseY = y; this.t0 = scene.time.now; this.side = 1; this.swapAt = scene.time.now + 3000;
    this.next = scene.time.now + 1500; this.play('drone2-fly'); this.state = 'fly';
  }
  update(time) {
    const p = this.scene.player; if (!p || this.dead) return;
    if (time > this.swapAt) { this.side = -this.side; this.swapAt = time + rnd(2600, 3400); }
    const cam = this.scene.cameras.main;
    const tx = Phaser.Math.Clamp(p.x + this.side * 80, cam.scrollX + 30, cam.scrollX + this.scene.scale.width - 30);
    this.body.setVelocityX(this.state === 'fly' ? Phaser.Math.Clamp((tx - this.x) * 1.5, -70, 70) : 0);
    this.y = this.baseY + Math.sin((time - this.t0) / 420) * 10;
    this.face(p.x > this.x);
    const o = { x: this.x + (this.flipX ? 16 : -16), y: this.y + 17 };
    if (this.state === 'fly' && this.canFire(16) && time > this.next) {
      if (this.claimTell(time, Drone2.TELL + 3 * Drone2.GAP + 200)) {
        this.state = 'aim'; this.fireAt = time + Drone2.TELL; this.telegraph(o, Drone2.TELL); this.scene.sfx?.play('gatling-spin', 0.6);
      } else this.next = time + 500;
    }
    if (this.state === 'aim' && time > this.fireAt) {
      this.state = 'burst'; this.play('drone2-fire'); this.scene.sfx?.play('gatling', 0.7);
      const a = this.aimAngle(o, 0, Math.PI / 8);
      for (let i = 0; i < 3; i++) this.scene.time.delayedCall(i * Drone2.GAP, () => {
        if (!this.active || this.dead || !this.canFire(8)) return;
        const q = { x: this.x + (this.flipX ? 16 : -16), y: this.y + 17 };
        this.fireA(q, a, Drone2.BULLET);
      });
      this.scene.time.delayedCall(3 * Drone2.GAP + 100, () => { if (this.active && !this.dead) { this.state = 'fly'; this.play('drone2-fly'); this.next = this.scene.time.now + rnd(2200, 2800); } });
    }
  }
  die(from) {
    const sc = this.scene; sc.addScore(this.score, this.x, this.y);
    const d = sc.add.sprite(this.x, this.y, 'drone2', 5).setDepth(45).setFlipX(this.flipX);
    sc.fx.explode(this.x, this.y, 0.7); sc.sfx?.play('enemy-die');
    sc.tweens.add({ targets: d, y: this.y + 60, angle: this.flipX ? 40 : -40, duration: 520, ease: 'Quad.easeIn', onComplete: () => { sc.fx.explode(d.x, d.y, 0.6); d.destroy(); } });
    this.destroy();
  }
}
Drone2.TELL = 450; Drone2.GAP = 120; Drone2.BULLET = 120;

// ------------------------------------------------------------------ mech
// Mini-boss gatling walker. Stomps in, plants, SPINS UP (barrels blur, glint, shake) and sweeps a burst.
// Two learnable patterns, alternating: HIGH stream at chest height sweeping down onto it (go prone / duck under),
// then LOW stream at ankle height (jump it). The first round of each stream marks its line.
export class Mech extends Enemy2 {
  constructor(scene, x, y) {
    super(scene, x, y, 'mech', 45, 3000);
    this.box(34, 58, 4); this.play('mech-walk'); this.bigBoom = true;
    this.state = 'walk'; this.next = scene.time.now + 1500; this.pattern = 0;
    this.setDepth(38);
  }
  update(time) {
    const p = this.scene.player; if (!p || this.dead) return;
    const b = this.body;
    if (this.state === 'walk') {
      this.face(p.x > this.x);
      const far = Math.abs(p.x - this.x) > 150;
      b.setVelocityX(far ? this.fdir * Mech.SPEED : 0);
      if (b.blocked.down && !this.scene.groundAhead(this.x + this.fdir * 20, this.y)) b.setVelocityX(0);
      this.anims.play(b.velocity.x ? 'mech-walk' : 'mech-idle', true);
      if (time > this.next && this.canFire(30)) {
        const dur = Mech.TELL + Mech.ROUNDS * Mech.GAP + 300;
        if (this.claimTell(time, dur)) {
          this.state = 'spin'; b.setVelocityX(0); this.play('mech-spin');
          this.fireAt = time + Mech.TELL; this.telegraph(M(this, -30, -37), Mech.TELL);
          this.scene.fx.shake?.(Mech.TELL, 0.0015); this.scene.sfx?.play('gatling-spin');
        } else this.next = time + 500;
      }
    } else if (this.state === 'spin') {
      b.setVelocityX(0);
      if (time > this.fireAt) {
        this.state = 'fire'; this.play('mech-fire'); this.scene.sfx?.play('gatling');
        const high = this.pattern++ % 2 === 0;
        const o = M(this, -30, -37), c = p.hurtCenter();
        const y1 = p.y - (high ? 22 : 5);                 // chest line (prone under it) / ankle line (jump it)
        const y0 = y1 - (high ? 34 : 14);                 // each stream starts above its line and sweeps down onto it
        const cx = c.x;
        for (let i = 0; i < Mech.ROUNDS; i++) this.scene.time.delayedCall(i * Mech.GAP, () => {
          if (!this.active || this.dead || !this.canFire(8)) return;
          const q = M(this, -30, -37), k = Math.min(1, i / 3), ty = y0 + (y1 - y0) * k;
          this.fireA(q, Math.atan2(ty - q.y, cx - q.x), Mech.BULLET);
          if (i % 2 === 0) this.scene.fx.muzzle(q.x, q.y, this.fdir, 0, 0.8);
        });
        this.doneAt = time + Mech.ROUNDS * Mech.GAP + 250;
      }
    } else if (this.state === 'fire') {
      b.setVelocityX(0);
      if (time > this.doneAt) { this.state = 'walk'; this.next = time + rnd(1800, 2400); }
    }
  }
  die(from) {
    const sc = this.scene; sc.addScore(this.score, this.x, this.y - 32);
    const w = sc.add.sprite(this.x, this.y, 'mech', 10).setOrigin(0.5, 1).setDepth(37).setFlipX(this.flipX);
    sc.fx.hitstop?.(90);
    [0, 160, 320, 520].forEach((t, i) => sc.time.delayedCall(t, () => sc.fx.explode(this.x + rnd(-16, 16), this.y - rnd(12, 50), i === 3 ? 1.6 : 1)));
    sc.time.delayedCall(300, () => w.setFrame(11));
    sc.tweens.add({ targets: w, alpha: 0, delay: 1800, duration: 500, onComplete: () => w.destroy() });
    this.destroy();
  }
}
Mech.SPEED = 16; Mech.TELL = 950; Mech.ROUNDS = 8; Mech.GAP = 95; Mech.BULLET = 118;

export const ROSTER2 = { trooper: Trooper, shield: Shield, sniper: Sniper, tank: Tank, drone2: Drone2, mech: Mech };
