// The sheep. Contra rules: 8-way aim, committed spin-jump (fixed-height wool ball, full air steering), prone,
// drop through platforms (down + jump), 1-hit death, drop-in respawn with i-frames.
// Feel numbers and the reasoning behind them: art/raw/feel/targets.md.
import { WEAPONS } from './weapons.js';

export const FEEL = {
  RUN: 100,          // px/s  (~4.8 s to cross the 480 px screen; Contra ~4.3 s)
  JUMP: -415,        // px/s  launch speed ...
  GRAV_EXTRA: 200,   // ... with 900 world + 200 = 1100 px/s^2 -> apex ~75 px (~1.6 sheep), airtime ~0.74 s
  MAX_FALL: 520,
  COYOTE: 80,        // ms after walking off a ledge that jump still works
  BUFFER: 120,       // ms a jump press is remembered before landing
  FIRE_BUFFER: 110,  // ms a fire press is remembered while the gun cools
  DROP_MS: 220,      // ms platforms are ignored after down+jump
};
// hurtboxes (relative to feet, facing right), much smaller than the art like Contra's
const HURT = {
  stand: { x: -6, y: -38, w: 12, h: 36 },
  prone: { x: -14, y: -11, w: 30, h: 11 },
  spin: { x: -13, y: -30, w: 16, h: 16 },
};

export class Player extends Phaser.Physics.Arcade.Sprite {
  constructor(scene, x, y) {
    super(scene, x, y, 'sheep');
    scene.add.existing(this); scene.physics.add.existing(this);
    this.setOrigin(0.5, 1).setDepth(50);
    this.stance = null; this.setStance('stand');
    this.body.setMaxVelocityY(FEEL.MAX_FALL);
    this.body.setGravityY(FEEL.GRAV_EXTRA);
    this.facing = 1; this.aim = { x: 1, y: 0 };
    this.weapon = 'R'; this.cool = 0; this.fireBuf = -1e9;
    this.lastGround = 0; this.jumpBuf = -1e9; this.dropUntil = 0;
    this.invuln = 0; this.dead = false; this.prone = false; this.spinning = false; this.auto = null;
    this.jumpT0 = 0;
  }

  setWeapon(w) { this.weapon = w; this.scene.events.emit('weapon', w); }

  play2(key) {
    if (!this.scene.anims.exists(key)) key = 'sheep-idle';
    if (this.anims.currentAnim?.key !== key) this.play(key, true);
  }

  // collision body is always bottom-aligned with the feet (so landing never shoves the body into the floor)
  setStance(s) {
    if (this.stance === s) return; this.stance = s;
    const w = 16, h = s === 'prone' ? 14 : s === 'spin' ? 24 : 32;
    this.body.setSize(w, h).setOffset((this.width - w) / 2, this.height - h);
  }

  // world-space hurtbox for the current stance
  hurtRect() {
    const k = this.prone ? HURT.prone : this.spinning ? HURT.spin : HURT.stand, f = this.facing;
    const x = f > 0 ? this.x + k.x : this.x - k.x - k.w;
    return { x, y: this.y + k.y, w: k.w, h: k.h };
  }
  hurtCenter() { const r = this.hurtRect(); return { x: r.x + r.w / 2, y: r.y + r.h / 2 }; }
  touches(body, shrink = 0) {
    const r = this.hurtRect();
    return body.x + shrink < r.x + r.w && body.right - shrink > r.x && body.y + shrink < r.y + r.h && body.bottom - shrink > r.y;
  }

  // called every frame, even during hit-stop, so presses are never eaten
  latch(time, c) {
    if (c.pressed('jump')) this.jumpBuf = time;
    if (c.pressed('fire')) this.fireBuf = time;
  }

  update(time, dt, c) {
    if (this.dead) return;
    const b = this.body, onGround = b.blocked.down || b.touching.down;
    if (onGround && b.velocity.y >= 0) this.lastGround = time;
    this.latch(time, c);
    const st = this.auto || c.state;   // autopilot (stage-clear walk-off) overrides the pad

    // horizontal: instant start/stop, full air control (Contra)
    const mx = (st.right ? 1 : 0) - (st.left ? 1 : 0);
    this.prone = onGround && st.down && !mx && !this.spinning;
    if (mx) this.facing = mx;
    b.setVelocityX(this.prone ? 0 : mx * FEEL.RUN);

    // jump / drop-through. Jump height is fixed: once you leave the ground the arc is committed.
    if (time - this.jumpBuf < FEEL.BUFFER && time - this.lastGround < FEEL.COYOTE) {
      this.jumpBuf = -1e9;
      if (st.down && onGround && this.scene.platformUnder(this)) {
        this.dropUntil = time + FEEL.DROP_MS; this.lastGround = -1e9; this.y += 2; b.setVelocityY(60);
        this.prone = false;
      } else {
        b.setVelocityY(FEEL.JUMP); this.lastGround = -1e9; this.spinning = true; this.prone = false; this.jumpT0 = time;
        this.scene.sfx?.play('jump'); this.scene.fx?.dust(this.x, this.y);
        this.scene.events.emit('player-jump', this);
      }
    }
    const grounded = onGround && b.velocity.y >= 0 && time - this.jumpT0 > 60;
    if (grounded && this.spinning) { this.spinning = false; this.scene.fx?.dust(this.x, this.y, 0.6); this.scene.events.emit('player-land', this); }
    this.setStance(this.prone ? 'prone' : this.spinning ? 'spin' : 'stand');

    // aim (8-way, snaps instantly). Ground: down = prone (aim forward low), down+dir = diagonal down. Air: down = straight down.
    let ax = mx, ay = (st.up ? -1 : 0) + (st.down && !onGround ? 1 : 0);
    if (st.down && onGround && mx) ay = 1;
    if (!ax && !ay) ax = this.facing;
    this.aim.x = ax; this.aim.y = ay;

    // fire: holding auto-fires at wpn.hold; mashing can reach wpn.rate; a press during cooldown is buffered
    this.cool -= dt;
    const wpn = WEAPONS[this.weapon];
    const wantPress = time - this.fireBuf < FEEL.FIRE_BUFFER, wantHold = st.fire && wpn.auto;
    if (this.cool <= 0 && (wantPress || wantHold)) {
      if (this.scene.firePlayer(this.muzzle(), this.aim, wpn)) {
        this.cool = wantPress ? wpn.rate : wpn.hold; this.fireBuf = -1e9; this.lastShot = time;
      }
    }

    // animation
    const shooting = st.fire || time - (this.lastShot || -1e9) < 250;
    if (!onGround) this.play2(this.spinning ? 'sheep-jump' : 'sheep-fall');
    else if (this.prone) this.play2('sheep-prone');
    else if (mx) this.play2(ay < 0 ? 'sheep-run-aimup' : ay > 0 ? 'sheep-run-aimdown' : shooting ? 'sheep-run-shoot' : 'sheep-run');
    else this.play2(ay < 0 ? 'sheep-aimup' : shooting ? 'sheep-shoot' : 'sheep-idle');
    this.setFlipX(this.facing < 0);

    if (this.invuln > 0) { this.invuln -= dt; this.setAlpha(Math.floor(time / 60) % 2 ? 0.35 : 1); } else this.setAlpha(1);
  }

  // where bullets leave the gun, relative to stance + aim
  muzzle() {
    const f = this.facing, a = this.aim;
    if (this.prone) return { x: this.x + f * 45, y: this.y - 8 };
    if (this.spinning) return { x: this.x + a.x * 13, y: this.y - 20 + a.y * 13 };
    if (a.y < 0 && !a.x) return { x: this.x + f * 20, y: this.y - 54 };
    if (a.y < 0) return { x: this.x + f * 36, y: this.y - 37 };
    if (a.y > 0) return { x: this.x + f * 38, y: this.y - 3 };
    return { x: this.x + f * 44, y: this.y - 19 };
  }

  get onPlatform() { return !!this.scene.platformUnder(this); }

  hurt(cause = 'hit') {
    if (this.dead || this.invuln > 0 || window.__sheep.debug.god || this.scene.cleared) return false;
    this.dead = true; this.cause = cause;
    this.scene.onPlayerDeath(this);
    return true;
  }
}
