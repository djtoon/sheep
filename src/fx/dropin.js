// Stage-start drop-in (story builder).
// Game calls dropIn(scene) at create when started with data.drop (stage 1 after the intro, stages 2/3 after results).
//  - outdoors (stages 1, 2): a Huey flies in over the start point, drops a rope, the sheep fast-ropes down, the chopper leaves.
//  - underground (level.theme 'lab', stage 3): a ceiling hatch blasts open (cover + debris + sparks), the rope drops
//    through it, the sheep fast-ropes down, the rope reels back up. No chopper, no rotor.
// Same timing either way: rope at ~0.95 s, slide 1.15-1.93 s, landing + scene.dropDone() at 1.96 s. Hard pixels only.
// While it runs the player is hidden with a do-nothing autopilot and no body (scene.dropping keeps spawns off).
import { Sfx } from '../audio/Sfx.js';

const IDLE = { right: false, left: false, up: false, down: false, jump: false, fire: false };

export function dropIn(scene) {
  const p = scene.player;
  if (!p) { scene.dropDone(); return; }
  const lab = scene.level && scene.level.theme === 'lab';
  if (!lab && !scene.textures.exists('story-chopper')) { scene.dropDone(); return; }
  const cam = scene.cameras.main, W = scene.scale.width;
  const sfx = scene.sfx || new Sfx(scene);   // reuse Game's Sfx: a second Sfx on the Game scene re-wires every music/pause hook (double sounds)
  const gy = p.y;                                   // player's feet (already standing on the ground)
  p.auto = IDLE; p.setVisible(false); p.body.enable = false;

  const rope = scene.add.graphics().setDepth(59);
  const rider = scene.add.sprite(0, 0, 'sheep', 38).setOrigin(0.5, 1).setDepth(59.5).setVisible(false);   // aim-up frame: hoof + rifle raised = gripping the rope
  const st = { rope: 0, rider: -1, t: 0, landed: false };
  const src = lab ? hatchSource(scene, p, gy, sfx) : heliSource(scene, p, gy, sfx);

  const tick = (time, dt) => {
    st.t += dt;
    if (!st.landed) p.setVisible(false);
    const [ax, ay] = src.update(st.t);                // rope anchor this frame
    rope.clear();
    if (st.rope > 0) {
      const len = Math.round(st.rope * (gy - ay));
      rope.fillStyle(0x2a2016, 1).fillRect(ax, ay, 1, len);
      rope.fillStyle(0xb89a64, 1).fillRect(ax + 1, ay, 1, len);
    }
    if (st.rider >= 0) {                              // hooves + rifle grip the rope; the sheep starts clear below the door/hatch
      const y0 = Math.min(gy, ay + 59);
      rider.setPosition(ax + 1 - 20, Math.round(y0 + st.rider * (gy - y0)));
    }
  };
  scene.events.on('update', tick);
  const tw = (o) => scene.tweens.add(o);
  const cleanup = () => { scene.events.off('update', tick); rope.destroy(); src.destroy(); };

  // 2. rope drops
  scene.time.delayedCall(950, () => tw({ targets: st, rope: 1, duration: 260, ease: 'Linear' }));
  // 3. sheep slides down the rope
  scene.time.delayedCall(1150, () => {
    st.rider = 0; rider.setVisible(true);
    tw({ targets: st, rider: 1, duration: 780, ease: 'Quad.in' });
  });
  // 4. landing: hand over to the real player
  scene.time.delayedCall(1960, () => {
    st.landed = true; rider.destroy();
    p.body.enable = true; p.setVisible(true);
    if (p.body.reset) p.body.reset(p.x, gy);
    sfx.play('thump'); sfx.play('land');
    if (scene.fx && scene.fx.dust) scene.fx.dust(p.x, gy, 1.2);
    cam.shake(90, 0.004);
    scene.dropDone();
  });
  // 5. rope reels in, then the source leaves / settles
  scene.time.delayedCall(2150, () => tw({ targets: st, rope: 0, duration: 260 }));
  scene.time.delayedCall(2350, () => src.leave(cleanup));
}

// ---------------------------------------------------------------- outdoors: the Huey
function heliSource(scene, p, gy, sfx) {
  const cam = scene.cameras.main, W = scene.scale.width;
  const hoverY = Math.max(68, gy - 120);             // low enough that the rotor clears the foreground canopy
  const doorDX = 12, doorDY = 17;                   // rope anchor: at the skid, below the cabin door                   // rope anchor relative to the chopper centre (cabin door)
  const heli = scene.add.sprite(cam.scrollX - 70, hoverY - 30, 'story-chopper', 0).setDepth(60);
  if (scene.anims.exists('story-chopper-fly')) heli.play('story-chopper-fly');
  const rotor = scene.add.graphics().setDepth(61);
  if (sfx.loop) sfx.loop('rotor', 0.7);
  // 1. fly in and settle into a hover over the start point
  scene.tweens.add({ targets: heli, x: Math.round(p.x - doorDX), y: hoverY, duration: 1000, ease: 'Cubic.out' });
  return {
    update(t) {
      const bob = Math.round(Math.sin(t * 0.006) * 1.5);
      const hx = Math.round(heli.x), hy = Math.round(heli.y) + bob;
      // main rotor: a blade bar that alternates long / short each frame = spinning
      rotor.clear();
      const len = (Math.floor(t / 45) % 2) === 0 ? 50 : 18;
      rotor.fillStyle(0x16141c, 1).fillRect(hx + 10 - len, hy - 17, len * 2, 1);
      rotor.fillStyle(0x3a3a44, 1).fillRect(hx + 10 - Math.round(len * 0.6), hy - 18, Math.round(len * 1.2), 1);
      return [hx + doorDX, hy + doorDY];
    },
    leave(done) {   // bank away up and off to the right
      scene.tweens.add({ targets: heli, x: cam.scrollX + W + 90, y: hoverY - 60, duration: 1000, ease: 'Cubic.in', onComplete: () => {
        if (sfx.stopLoop) sfx.stopLoop('rotor', 300); done();
      } });
    },
    destroy() { rotor.destroy(); heli.destroy(); },
  };
}

// ---------------------------------------------------------------- underground: a ceiling hatch blown open
function hatchSource(scene, p, gy, sfx) {
  const cam = scene.cameras.main;
  const hx = Math.round(p.x), hy = 44;               // hatch at the bottom of a ceiling duct, clear below the HUD strip
  const HW = 14;                                     // half width of the opening
  const frame = scene.add.graphics().setDepth(57);
  const cover = scene.add.graphics().setDepth(58);
  let open = false;
  const drawFrame = () => {
    frame.clear();
    // ceiling duct coming down to the hatch (riveted steel box)
    frame.fillStyle(0x0c0a12, 1).fillRect(hx - HW - 3, 0, (HW + 3) * 2, hy - 4);
    frame.fillStyle(0x2e333e, 1).fillRect(hx - HW - 2, 0, (HW + 2) * 2, hy - 5);
    frame.fillStyle(0x454b58, 1).fillRect(hx - HW - 2, 0, 2, hy - 5);
    frame.fillStyle(0x1c2028, 1).fillRect(hx + HW - 1, 0, 2, hy - 5);
    for (let y = 4; y < hy - 6; y += 8) frame.fillStyle(0x6a7282, 1).fillRect(hx - HW, y, 1, 1).fillRect(hx + HW - 2, y, 1, 1);
    // housing: dark steel collar with bolts and hazard stripes
    frame.fillStyle(0x0c0a12, 1).fillRect(hx - HW - 5, hy - 5, (HW + 5) * 2, 9);
    frame.fillStyle(0x4a505e, 1).fillRect(hx - HW - 4, hy - 4, (HW + 4) * 2, 7);
    frame.fillStyle(0x7a8294, 1).fillRect(hx - HW - 4, hy - 4, (HW + 4) * 2, 1);
    for (let x = hx - HW - 3; x < hx + HW + 4; x += 4) {
      frame.fillStyle(0xe8b020, 1).fillRect(x, hy - 2, 2, 3);
      frame.fillStyle(0x16141c, 1).fillRect(x + 2, hy - 2, 2, 3);
    }
    frame.fillStyle(0xb8c0d0, 1).fillRect(hx - HW - 3, hy + 1, 1, 1).fillRect(hx + HW + 2, hy + 1, 1, 1);
    // the opening (black shaft once the cover is gone)
    frame.fillStyle(open ? 0x040306 : 0x2a2e38, 1).fillRect(hx - HW, hy - 3, HW * 2, 6);
    if (open) frame.fillStyle(0xff7a20, 1).fillRect(hx - HW, hy + 2, HW * 2, 1);   // hot rim of the blown hinge
  };
  const drawCover = () => {
    cover.clear();
    cover.fillStyle(0x0c0a12, 1).fillRect(-HW - 1, -2, HW * 2 + 2, 5);
    cover.fillStyle(0x6a7282, 1).fillRect(-HW, -1, HW * 2, 3);
    cover.fillStyle(0x9aa2b4, 1).fillRect(-HW, -1, HW * 2, 1);
    cover.fillStyle(0x16141c, 1).fillRect(-3, 0, 6, 1);
  };
  drawFrame(); drawCover(); cover.setPosition(hx, hy + 2);
  // 1. a beat, then the charge blows the cover off
  scene.time.delayedCall(420, () => {
    open = true; drawFrame();
    sfx.play('boom');
    cam.shake(160, 0.007);
    const fx = scene.fx;
    if (fx) {
      fx.spark && fx.spark(hx, hy + 4, 14, 'fire', 150);
      fx.shards && fx.shards(hx, hy + 4, 6, 180);
      fx.smokePuffs && fx.smokePuffs(hx, hy + 6, 4, 10);
    }
    // debris chunks: hard 2x2 / 1x1 pixels falling with gravity
    const deb = scene.add.graphics().setDepth(58);
    const bits = Array.from({ length: 10 }, () => ({ x: hx + Phaser.Math.Between(-HW, HW), y: hy + 3,
      vx: Phaser.Math.FloatBetween(-50, 50), vy: Phaser.Math.FloatBetween(-40, 30), s: Math.random() < 0.4 ? 2 : 1 }));
    let life = 0;
    const ev = scene.time.addEvent({ delay: 16, loop: true, callback: () => {
      life += 16; deb.clear();
      for (const b of bits) {
        b.vy += 9; b.x += b.vx * 0.016; b.y += b.vy * 0.016;
        if (b.y < gy) deb.fillStyle(b.s === 2 ? 0x6a7282 : 0xb8c0d0, 1).fillRect(Math.round(b.x), Math.round(b.y), b.s, b.s);
      }
      if (life > 1400) { ev.remove(); deb.destroy(); }
    } });
    // the cover tumbles down (flips between its two faces = spin) and bounces off the floor
    const c = { vy: -60, vx: Phaser.Math.Between(0, 1) ? 45 : -45, t: 0 };
    const cv = scene.time.addEvent({ delay: 16, loop: true, callback: () => {
      c.t += 16; c.vy += 14; cover.x += c.vx * 0.016; cover.y += c.vy * 0.016;
      cover.scaleY = (Math.floor(c.t / 70) % 2) ? 1 : -1;
      if (cover.y > gy - 2) { cover.y = gy - 2; c.vy = -Math.abs(c.vy) * 0.35; c.vx *= 0.6; if (Math.abs(c.vy) < 20) { cover.scaleY = 1; cv.remove(); sfx.play('land'); } }
    } });
  });
  return {
    update() { return [hx, hy + 3]; },
    leave(done) { scene.time.delayedCall(300, done); },   // hatch stays open; only the rope went back up
    destroy() {},                                        // the open hatch and the cover stay as scenery
  };
}
