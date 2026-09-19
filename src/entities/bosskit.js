// Shared plumbing for the stage-2 / stage-3 bosses (the stage-1 Boss.js is frozen and keeps its own copy).
// A "boss" object using this kit must have: scene, state, and fighting().
export const rnd = (a, b) => a + Math.random() * (b - a);
export const pick = (a) => a[Math.floor(Math.random() * a.length)];
export const groundLine = (sc, x) => {
  const g = sc.groundYAt ? sc.groundYAt(x) : NaN;
  return Number.isFinite(g) && g < (sc.level?.height ?? 270) ? g : 168;
};

// damageable part in scene.bossParts (bullets call part.damage(n, bullet))
export function part(boss, s, hp, kind) {
  s.body.setAllowGravity(false).setImmovable(true);
  s.hp = s.maxHp = hp; s.kind = kind; s.dead = false;
  s.damage = (n, bl) => boss.hit(s, n, bl);
  boss.scene.bossParts.add(s); s.body.setAllowGravity(false);
  return s;
}

// invisible armour zone: eats bullets with a grey ricochet (FX draws its small ricochet for armor=true)
export function zone(boss, x, y, w, h) {
  const sc = boss.scene, z = sc.add.zone(x + w / 2, y + h / 2, w, h);
  sc.physics.add.existing(z); sc.bossParts.add(z);
  z.body.setAllowGravity(false).setImmovable(true); z.armor = true;
  z.damage = (n, bl) => tink(boss, bl ? bl.x : z.body.x + 2, bl ? bl.y : z.body.center.y);
  return z;
}
export function placeZone(z, x, y, w, h) { z.setPosition(x + w / 2, y + h / 2); z.body.setSize(w, h); z.body.updateFromGameObject?.(); }

export function tink(boss, x, y) {
  const sc = boss.scene, now = sc.time.now;
  if (now < (boss._nextTink || 0)) return; boss._nextTink = now + 45;
  if (now > (boss._nextRic || 0)) { boss._nextRic = now + 160; sc.sfx?.play('ricochet', 0.35); }
  if (sc.anims.exists('boss-tink')) { const t = sc.add.sprite(Math.round(x), Math.round(y), 'boss-tink', 0).setDepth(70).play('boss-tink'); t.once('animationcomplete', () => t.destroy()); }
  if (sc.fx.part) for (let i = 0; i < 2; i++) sc.fx.part('boss-tink', [2], x, y, -rnd(60, 130), -rnd(20, 90), { g: 500, life: 260, depth: 70, ground: false });
}

export function chunks(sc, tex, x, y, n, s = 1) {
  if (!sc.fx.part || !sc.textures.exists(tex)) return;
  for (let i = 0; i < n; i++)
    sc.fx.part(tex, [Math.floor(Math.random() * 8)], x + rnd(-6, 6), y + rnd(-6, 6), rnd(-160, 90) * s, -rnd(120, 280) * s,
      { g: 700, life: rnd(1100, 1600), bounce: 0.35, spin: rnd(-12, 12), depth: 64, blink: 300 });
}

// hit flash (additive, weak for big parts so they never read as a white blob)
export function flash(sc, targets, strong) {
  const c = strong ? 0x605040 : 0x3a3024;
  for (const o of targets) if (o && o.active) o.setTint(c).setTintMode(Phaser.TintModes.ADD);
  sc.time.delayedCall(35, () => { for (const o of targets) if (o && o.active) o.clearTint(); });
}

// floating damage tick
export function tick(boss, x, y, hp, maxHp) {
  const sc = boss.scene;
  if (sc.time.now < (boss._nextTick || 0)) return; boss._nextTick = sc.time.now + 140;
  const t = sc.add.text(Math.round(x + rnd(-3, 3)), Math.round(y), String(Math.max(0, Math.ceil(hp))), {
    fontFamily: 'monospace', fontSize: '8px', color: hp <= maxHp / 3 ? '#ff5a3a' : '#ffe08a', stroke: '#1a1420', strokeThickness: 2 }).setDepth(70).setResolution(1);
  sc.tweens.add({ targets: t, y: t.y - 10, duration: 420, onComplete: () => t.destroy() });
}

// hard-pixel HP bar
export function hpBar(g, x, y, w, hp, maxHp, show) {
  g.setVisible(show); if (!show) return;
  const f = Math.max(0, Math.ceil(w * hp / maxHp));
  g.clear();
  g.fillStyle(0x1a1420, 1).fillRect(x - 1, y - 1, w + 2, 5);
  g.fillStyle(0x4a1010, 1).fillRect(x, y, w, 3);
  g.fillStyle(hp <= maxHp / 3 ? 0xff5a3a : 0xffc040, 1).fillRect(x, y, f, 3);
  g.fillStyle(0xfff0c0, 1).fillRect(x, y, f, 1);
}

// enemy hazard as a real scene.eBullets member with FX styling opted out (collision, culling, bots all see it)
export function hazard(sc, x, y, tex, depth, anim, late) {
  const b = sc.physics.add.sprite(x, y, tex, 0).setDepth(depth);
  b.noStyle = true; b.born = sc.time.now;
  if (!late) { sc.eBullets.add(b); if (!sc.eBullets.contains(b)) { b.destroy(); return null; } }
  b.body.setAllowGravity(false); if (anim && sc.anims.exists(anim)) b.play(anim);
  return b;
}
export function arm(sc, b) {  // join eBullets later (keeps velocity: group.add resets it)
  const vx = b.body.velocity.x, vy = b.body.velocity.y;
  sc.eBullets.add(b); b.body.setAllowGravity(false).setVelocity(vx, vy);
}

// generic hazard runner: kinds 'arc' (gravity lob onto a ground mark, blast on landing) and 'roll' (ground roller)
export function runHazards(boss, GY) {
  const sc = boss.scene, p = sc.player, dt = Math.min(sc.game.loop.delta, 50) / 1000, fx = sc.fx;
  const pb = p && p.body && !p.dead ? p.body : null;
  for (const h of boss.haz) {
    if (h.dead) continue;
    const b = h.s;
    if (!b.scene || !b.active) { h.dead = true; continue; }
    b.born = sc.time.now;
    if (h.kind === 'arc') {
      b.body.velocity.y += h.g * dt;
      if (h.spin) b.rotation += h.spin * dt; else b.setRotation(Math.atan2(b.body.velocity.y, b.body.velocity.x) - Math.PI / 2);
      if (h.mk) h.mk.anims.timeScale = b.body.velocity.y > 0 ? 2.2 : 1;
      if (!h.live && b.body.velocity.y > 0 && b.y > GY - (h.armY || 70)) { h.live = true; arm(sc, b); }
      if (b.y >= GY - 4 && b.body.velocity.y > 0) {
        h.dead = true;
        if (h.onLand) h.onLand(h.tx); else { fx.explode(h.tx, GY - 8, 0.72); fx.dust(h.tx, GY, 1.2); }
        if (pb && Math.abs(p.x - h.tx) < (h.r || 15) && pb.y + pb.height > GY - 26) p.hurt();
      }
    } else if (h.kind === 'roll') {
      if (Math.random() < 0.35) fx.spark?.(b.x + 6, GY - 1, 1, 'fire', 90, 70);
      if (b.x < sc.cameras.main.scrollX - 30 || b.x > sc.cameras.main.scrollX + 520) h.dead = true;
    } else if (h.kind === 'bolt') {
      if (b.x < sc.cameras.main.scrollX - 30) h.dead = true;
    }
  }
  for (const h of boss.haz) if (h.dead && !h.gone) { h.gone = true; if (h.s.scene) h.s.destroy(); h.mk?.destroy(); }
  boss.haz = boss.haz.filter(h => !h.gone);
}

// lob an arcing projectile from (x0,y0) onto ground x=tx with a blinking target mark
export function lob(boss, GY, x0, y0, tx, tex, anim, opt = {}) {
  const sc = boss.scene, T = opt.T || 1.35, g = opt.g || 420;
  const s = hazard(sc, x0, y0, tex, 45, anim, true); if (!s) return;
  if (opt.size) s.body.setSize(opt.size[0], opt.size[1]);
  const mk = sc.add.sprite(tx, GY - 3, 'boss-mark', 0).setDepth(21);
  if (sc.anims.exists('boss-mark-blink')) mk.play('boss-mark-blink');
  s.body.setVelocity((tx - x0) / T, ((GY - 4 - y0) - 0.5 * g * T * T) / T);
  boss.haz.push({ kind: 'arc', s, mk, g, tx, spin: opt.spin, r: opt.r, onLand: opt.onLand, armY: opt.armY });
}

// Contra / Metal Slug style boss strip fixed at the bottom of the screen: hard-pixel frame, name, HP bar.
export class BossBar {
  constructor(sc, name) {
    const W = sc.scale.width, y = sc.scale.height - 17;
    this.x = Math.round(W / 2 - 110); this.y = y; this.w = 220;
    this.g = sc.add.graphics().setScrollFactor(0).setDepth(96).setVisible(false);
    this.t = sc.cache.bitmapFont.exists('hud-font') ? sc.add.bitmapText(this.x + 5, y + 3, 'hud-font', name)
      : sc.add.text(this.x + 5, y + 2, name, { fontFamily: 'monospace', fontSize: '8px', color: '#ffe0a0', stroke: '#000', strokeThickness: 2 });
    this.t.setScrollFactor(0).setDepth(97).setVisible(false);
    this.bx = this.x + Math.max(62, Math.ceil(this.t.width) + 12); this.bw = this.x + this.w - 5 - this.bx;
  }
  set(hp, maxHp, show) {
    const g = this.g; g.setVisible(show); this.t.setVisible(show); if (!show) return;
    const { x, y, w, bx, bw } = this, f = Math.max(0, Math.ceil(bw * hp / maxHp));
    g.clear();
    g.fillStyle(0x0a080e, 1).fillRect(x, y, w, 14);
    g.fillStyle(0x7a7f8c, 1).fillRect(x + 1, y + 1, w - 2, 1); g.fillStyle(0x3a3b46, 1).fillRect(x + 1, y + 12, w - 2, 1);
    g.fillStyle(0x555864, 1).fillRect(x + 1, y + 2, 1, 10).fillRect(x + w - 2, y + 2, 1, 10);
    for (let i = 0; i < 4; i++) { g.fillStyle(i % 2 ? 0x16151c : 0xe8b632, 1).fillRect(x + 2 + i * 2, y + 2, 2, 10); }
    g.fillStyle(0x16151c, 1).fillRect(bx - 1, y + 3, bw + 2, 8);
    g.fillStyle(0x4a1010, 1).fillRect(bx, y + 4, bw, 6);
    g.fillStyle(hp <= maxHp / 3 ? 0xff5a3a : 0xffc040, 1).fillRect(bx, y + 4, f, 6);
    g.fillStyle(0xfff0c0, 1).fillRect(bx, y + 4, f, 1);
    g.fillStyle(0x16151c, 1); for (let s = bx + 8; s < bx + bw; s += 8) g.fillRect(s, y + 4, 1, 6);   // segment ticks
  }
  destroy() { this.g.destroy(); this.t.destroy(); }
}
