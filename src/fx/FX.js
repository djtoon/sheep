// Juice: muzzle flashes, bullet looks, impacts, explosions, debris, casings, dust, screen shake, hit-stop.
// Art: assets/fx/* (built by art/raw/fx/build_fx.py). Every public method degrades to placeholders if art is missing.
//
// Public API (called by Game / Player / Enemies / Boss):
//   muzzle(x, y, dx, dy, s)   impact(x, y)   terrainHit(x, y)   dust(x, y, s)   explode(x, y, s)
//   soldierDeath(e, from)     pickupGet(x, y)   shake(ms, amt)   hitstop(ms)   flash(x, y, s)
//
// Purely visual per-frame pass (postupdate): gives player/enemy bullets their per-weapon, per-direction
// animated look (hitboxes untouched), hides player bullets that enter solid ground with a dirt spark,
// follows the player's gun with its muzzle flash, and twinkles pickups.
const PI = Math.PI, OCT = PI / 4;
const MZ = { // base point of the flash inside each cell (w, h, ox, oy)
  muzzle: [44, 32, 3, 16], 'muzzle-d': [38, 38, 4, 34], 'muzzle-u': [32, 44, 16, 41], 'muzzle-sm': [20, 14, 2, 7],
};
const WROW = { R: 0, M: 1, S: 2, L: 3, E: 4 };     // rows in fxb (6 cols: h, d, v, h', d', v')
const PX = { spark: 0, y2: 1, o2: 2, o1: 3, r1: 4, d1: 5, cplus: 6, c2: 7, b1: 8, g2: 9, g1: 10, dust2: 11, pplus: 12, p1: 13, w2: 14, w1: 15 };
const rnd = (a, b) => a + Math.random() * (b - a);

export class FX {
  constructor(scene) {
    this.scene = scene;
    this.parts = []; this.free = []; this.followers = []; this.eGlow = new Map(); this.eMuzzles = []; this.lastHit = []; this.wrecks = []; this.marks = new Map(); this.killZones = []; this.booms = []; this.nextDmg = 0;
    this.frozenUntil = 0; this.mgAlt = 0; this.nextTwinkle = 0;
    const T = scene.textures;
    this.art = T.exists('fxb') && T.get('fxb').frameTotal > 2;
    this.pxTex = T.exists('px') && T.get('px').frameTotal > 2 ? 'px' : null;
    if (this.art) this.makeAnims();
    scene.events.on('postupdate', this.post, this);
    // game-feel event hooks (all guarded)
    const on = (ev, fn) => { const h = (...a) => { try { fn.apply(this, a); } catch (e) { console.warn('fx hook ' + ev, e && e.message); } }; scene.events.on(ev, h); scene.events.once('shutdown', () => scene.events.off(ev, h)); };
    if (T.exists('digits') && T.get('digits').frameTotal > 10) { on('scorepop', this.scorePop); if (scene.hooked) scene.hooked.scorepop = true; }
    on('powerup', this.powerupBurst);
    if (scene.anims.exists('eflash') || T.exists('glint')) { on('telegraph', this.telegraphTell); if (scene.hooked) scene.hooked.telegraph = true; }
    on('player-respawn', this.respawnFlash);
    scene.events.once('shutdown', () => scene.events.off('postupdate', this.post, this));
  }

  makeAnims() {
    const A = this.scene.anims;
    const mk = (key, tex, frames, fps, repeat = 0) => {
      if (!this.scene.textures.exists(tex)) return;
      const total = this.scene.textures.get(tex).frameTotal - 1;           // minus __BASE
      const fr = A.generateFrameNumbers(tex, { frames: frames.filter(f => f < total) });
      if (!fr.length) return;
      const old = A.get(key);
      if (old && old.frames && old.frames.length) return;
      if (old) A.remove(key);                                               // drop a broken zero-frame anim
      A.create({ key, frames: fr, frameRate: fps, repeat });
    };
    for (const t of ['muzzle', 'muzzle-d', 'muzzle-u']) for (let r = 0; r < 4; r++) mk(`${t}-${r}`, t, [r * 4, r * 4, r * 4 + 1, r * 4 + 1, r * 4 + 2, r * 4 + 3], r === 3 ? 44 : 50);
    mk('muzzle-sm-0', 'muzzle-sm', [0, 1, 2, 3], 40);
    mk('eflash', 'glint', [0, 1, 0], 30);   // enemy wind-up tell: small glint, never reads as an impact
    mk('dflash', 'glint', [1, 0], 30);
    mk('tell2', 'glint', [1, 1, 0], 24);
    for (let r = 0; r < 3; r++) mk('hit-' + r, 'hit', [r * 4, r * 4, r * 4, r * 4 + 1, r * 4 + 1, r * 4 + 3], 30);   // big star held ~100ms, ~200ms total
    mk('hit-dirt', 'hit-dirt', [0, 1, 2, 3, 4, 5], 28);
    mk('hb-md', 'explosion', [2, 3, 3, 4, 5], 26);            // heavy hit: ~36px spiky starburst -> fireball            // heavy-target hit burst (~24px)
    mk('hb-lg', 'explosion-big', [3, 4, 4, 5, 6], 26);       // heavy target nearly dead: ~44px               // heavy target nearly dead (~32px)
    mk('bloom', 'ring', [0], 60);
    mk('kill-flash', 'killflash', [0, 0, 1], 30);                                 // 1-frame hard bloom ring per shot
    mk('xp-kill', 'explosion', [2, 3, 3, 4, 4, 5], 24);           // soldier kill burst ~30px, hot frames only
    mk('xp-pop', 'explosion-sm', [1, 2, 3, 4], 22);            // small bright fireball pop for kills
    mk('xp-sm', 'explosion-sm', [0, 1, 2, 3, 4], 22);        // fire frames only; smoke is separate puffs drawn below bullets
    mk('xp-md', 'explosion', [0, 1, 2, 3, 4, 5, 6], 18);
    mk('xp-lg', 'explosion-big', [0, 1, 2, 3, 4, 5, 6], 16);
    for (let r = 0; r < 3; r++) mk('puff-' + r, 'puff', [r * 6, r * 6 + 1, r * 6 + 2, r * 6 + 3, r * 6 + 4, r * 6 + 5], 14);
    mk('puff-solid', 'puff', [0, 1, 2, 3, 4], 14);           // round grey puff without the dithered break-up
    mk('dust', 'dust', [0, 1, 2, 3, 4, 5], 20);
    mk('twinkle', 'twinkle', [0, 1, 2, 3, 4], 22);
    mk('ring', 'ring', [0, 1, 2, 3, 4], 30);
  }

  // ---------------------------------------------------------------- tiny helpers
  oneShot(x, y, tex, anim, depth, ox = 0.5, oy = 0.5) {
    // never throws: missing / zero-frame anims just skip the effect
    try {
      const a = this.scene.anims.get(anim);
      if (!a || !a.frames || !a.frames.length) return null;
      const f0 = a.frames[0];
      const s = this.scene.add.sprite(Math.round(x), Math.round(y), f0.textureKey, f0.textureFrame).setDepth(depth).setOrigin(ox, oy);
      s.play(anim); s.once('animationcomplete', () => s.destroy());
      return s;
    } catch (e) { console.warn('fx oneShot skipped', anim, e && e.message); return null; }
  }

  // simple pooled pixel particles: frames step through life (clean pixel fades instead of alpha/scale mush)
  part(tex, frames, x, y, vx, vy, o = {}) {
    if (tex === 'debris') {                       // cap flying chunks: cull the oldest
      const deb = this.parts.filter(q => q.tex === 'debris');
      if (deb.length >= 12) { const q = deb[0]; q.t = q.life; }
    }
    let img = this.free.pop();
    if (img && img.scene) img.setTexture(tex, frames[0]).setVisible(true).setActive(true).setRotation(0).setAlpha(1);
    else img = this.scene.add.image(x, y, tex, frames[0]);
    img.setPosition(x, y).setDepth(o.depth ?? 66).setBlendMode(o.add ? Phaser.BlendModes.ADD : Phaser.BlendModes.NORMAL);
    this.parts.push({ img, tex, frames, x, y, vx, vy, g: o.g ?? 500, drag: o.drag ?? 0, life: o.life ?? 400, t: 0,
      bounce: o.bounce ?? -1, spin: o.spin || 0, orient: !!o.orient, loop: o.loop || 0, blink: o.blink || 0, ground: o.ground ?? true, rest: 0 });
  }
  spark(x, y, n, pal = 'fire', spd = 160, up = 0) {
    if (!this.pxTex) return;
    const seq = pal === 'cyan' ? [PX.cplus, PX.c2, PX.c2, PX.b1] : pal === 'pink' ? [PX.pplus, PX.p1, PX.p1] :
      [PX.spark, PX.y2, PX.o2, PX.o1, PX.r1];
    for (let i = 0; i < n; i++) {
      const a = rnd(0, PI * 2), v = rnd(spd * 0.4, spd);
      this.part('px', seq, x, y, Math.cos(a) * v, Math.sin(a) * v - up, { g: 420, drag: 1.5, life: rnd(180, 380), depth: 67 });
    }
  }
  // hard white-yellow streaks that fly out of blasts and kills
  shards(x, y, n, spd = 220) {
    if (!this.scene.textures.exists('shard')) return;
    for (let i = 0; i < n; i++) {
      const a = rnd(0, PI * 2), v = rnd(spd * 0.55, spd);
      this.part('shard', [0, 0, 1, 2], x + Math.cos(a) * 4, y + Math.sin(a) * 4, Math.cos(a) * v, Math.sin(a) * v - 30,
        { g: 260, drag: 2.2, life: rnd(220, 380), depth: 67, orient: true, ground: false });
    }
  }
  // round grey smoke puffs (4 tones, broken edge) that drift up
  smokePuffs(x, y, n, spread = 6) {
    if (!this.art) return;
    for (let i = 0; i < n; i++) this.scene.time.delayedCall(i * 40, () => {
      const pf = this.oneShot(x + rnd(-spread, spread), y - rnd(0, 4), 'puff', 'puff-solid', 48);
      if (pf) this.scene.tweens.add({ targets: pf, y: pf.y - rnd(6, 12), x: pf.x + rnd(-3, 3), duration: 420 });
    });
  }
  embers(x, y, n, r) {
    if (!this.pxTex) return;
    for (let i = 0; i < n; i++)
      this.part('px', [PX.y2, PX.o1, PX.o1, PX.r1, PX.d1], x + rnd(-r, r), y + rnd(-r, r), rnd(-30, 30), rnd(-70, -20), { g: -20, drag: 1, life: rnd(500, 900), depth: 67, ground: false });
  }
  groundAt(x) { return this.scene.groundYAt ? this.scene.groundYAt(x) : 1e9; }

  // ---------------------------------------------------------------- muzzle flash
  muzzle(x, y, dx, dy, s = 1) {
    const sc = this.scene;
    if (!this.art) { // placeholder path
      const m = sc.add.sprite(x, y, 'muzzle').setDepth(60).setRotation(Math.atan2(dy, dx));
      sc.time.delayedCall(45, () => m.destroy()); return;
    }
    const p = sc.player; let owner = null;
    if (p && p.muzzle && !p.dead) { const m = p.muzzle(); if (Math.abs(m.x - x) < 0.6 && Math.abs(m.y - y) < 0.6) owner = p; }
    const o = ((Math.round(Math.atan2(dy, dx) / OCT) % 8) + 8) % 8;   // 0=R 1=DR 2=D 3=DL 4=L 5=UL 6=U 7=UR
    let tex, fx = false, fy = false;
    if (o === 0 || o === 4) { tex = 'muzzle'; fx = o === 4; }
    else if (o === 2 || o === 6) { tex = 'muzzle-u'; fy = o === 2; }
    else { tex = 'muzzle-d'; fx = o === 3 || o === 5; fy = o === 1 || o === 3; }
    let row = 0;
    if (owner) { const w = p.weapon; row = w === 'S' ? 2 : w === 'L' ? 3 : (this.mgAlt ^= 1); }
    else if (s < 0.9 && tex === 'muzzle') tex = 'muzzle-sm';
    const nearBoom = owner && (this.booms = this.booms.filter(bm => sc.time.now - bm.t < 350)).some(bm => Math.abs(bm.x - x) < 220 && Math.abs(bm.y - y) < 70);   // a blast owns the frame: flash steps down
    if (nearBoom && tex === 'muzzle') tex = 'muzzle-sm';
    const [w, h, ox, oy] = MZ[tex];
    const anim = tex === 'muzzle-sm' ? 'muzzle-sm-0' : `${tex}-${row}`;
    const spr = this.oneShot(x, y, tex, anim, 60, fx ? 1 - ox / w : ox / w, fy ? 1 - oy / h : oy / h);
    if (!spr) return;
    spr.setFlip(fx, fy);
    if (owner) {
      this.followers.push({ spr, owner });
      if (p.weapon !== 'L' && !nearBoom) { this.oneShot(x + dx * 7, y + dy * 7, 'ring', 'bloom', 61); }
      const w = p.weapon;
      // brass: rifle / MG eject a casing up and back
      if ((w === 'R' || w === 'M') && !p.spinning) {
        const f = p.facing || 1;
        this.part('casing', [0, 1, 2, 3], p.x - f * 2, p.y - 24, -f * rnd(40, 80), -rnd(100, 150),
          { g: 700, life: 1100, bounce: 0.35, loop: 40, depth: 49, blink: 250 });
      }
    } else {
      const now = sc.time.now; this.eMuzzles = this.eMuzzles.filter(m => now - m.t < 80); this.eMuzzles.push({ x, y, t: now });
    }
  }

  // Soft additive glows were cut (round 4): every effect is a hard-edged pixel shape. Kept as a no-op for callers.
  glow() {}
  flash(x, y, s = 1) { this.glow(x, y, s, 140, 1); }

  // ---------------------------------------------------------------- hits
  // impact(x, y, opts): opts.ricochet === true, or the struck target having .armor === true,
  // draws only a few small grey spark pixels (the caller draws its own ricochet sprite).
  impact(x, y, opts) {
    const sc = this.scene;
    // Game.collect() reports a pickup grab through impact(): detect it and sparkle instead
    const pk = sc.pickups && sc.pickups.getChildren().find(k => k.active && Math.abs(k.x - x) < 0.5 && Math.abs(k.y - y) < 0.5);
    if (pk) return this.pickupGet(x, y);
    if (!this.art) { this.spark(x, y, 4); return; }
    // exactly one clean white-cored star per hit, pinned to the surface of what was hit
    let hx = x, hy = y;
    const b = sc.pBullets && sc.pBullets.getChildren().find(q => q.body && Math.abs(q.x - x) < 0.5 && Math.abs(q.y - y) < 0.5);
    const pl = sc.player;
    {
      const vx = b ? b.body.velocity.x : (pl && x < pl.x ? -1 : 1), vy = b ? b.body.velocity.y : 0;
      const pools = [sc.enemies, sc.bossParts].filter(Boolean);
      let tgt = null, tobj = null; this._tobjFound = null;
      for (const g of pools) for (const e of g.getChildren()) {
        const eb = e.body; if (!e.active || !eb) continue;
        if (!tgt && x > eb.left - 20 && x < eb.right + 20 && y > eb.top - 20 && y < eb.bottom + 20) { tgt = eb; tobj = e; this._tobjFound = e; }
      }
      if (tgt) {
        if (Math.abs(vx) >= Math.abs(vy)) { hx = vx > 0 ? tgt.left + 2 : tgt.right - 2; hy = Phaser.Math.Clamp(y, tgt.top + 3, tgt.bottom - 3); }
        else { hy = vy > 0 ? tgt.top + 2 : tgt.bottom - 2; hx = Phaser.Math.Clamp(x, tgt.left + 3, tgt.right - 3); }
      }
    }
    this._lastTarget = this._tobjFound;
    const now = sc.time.now;
    const laser = sc.player && sc.player.weapon === 'L';
    const T = this._lastTarget;
    if ((opts && opts.ricochet) || (T && T.armor === true)) {
      if (this.pxTex) for (let i = 0; i < 3; i++) { const a = rnd(0, PI * 2), v = rnd(60, 130); this.part('px', [PX.w1, PX.g2, PX.g1], hx, hy, Math.cos(a) * v, Math.sin(a) * v - 40, { g: 500, life: rnd(150, 240), depth: 69 }); }
      return;
    }
    const back = b && b.body ? Math.atan2(-b.body.velocity.y, -b.body.velocity.x) : (pl && x < pl.x ? 0 : PI);
    let heavy = false, big = false;
    if (T && T.hp !== undefined) {
      if (T._fxMaxHp === undefined) T._fxMaxHp = T.hp;
      if (T._fxMaxHp >= 8) { heavy = true; big = Math.max(0, T.hp) / T._fxMaxHp < 0.4; }
    }
    const tex = heavy ? (big ? 'explosion-big' : 'explosion') : 'hit';
    if (heavy) { hx += Math.round(Math.cos(back) * 10); hy += Math.round(Math.sin(back) * 10); }   // sit out in front of the target
    const anim = heavy ? (big ? 'hb-lg' : 'hb-md') : (laser ? 'hit-1' : 'hit-0');
    // sustained fire: one persistent contact mark per target, moved + restarted on every hit (never stacked)
    const key = T || null;
    // a kill explosion owns this spot: no new contact stars on top of it
    this.killZones = this.killZones.filter(z => now - z.t < 320);
    if (this.killZones.some(z => Math.abs(z.x - hx) < 30 && Math.abs(z.y - hy) < 30)) return;
    let mark = key && this.marks.get(key), fresh = true;
    if (mark && mark.scene && mark.anims && mark.anims.isPlaying && mark.texture.key === tex && (!heavy || now - (mark._t0 || 0) < 250)) {
      fresh = false;
      if (!heavy) { mark.setPosition(Math.round(hx), Math.round(hy)); mark.play(anim, false); }
    } else {
      // untargeted hits: still suppress exact stacking at one spot
      this.lastHit = this.lastHit.filter(h => now - h.t < 120);
      if (!key && this.lastHit.some(h => Math.abs(h.x - hx) < 12 && Math.abs(h.y - hy) < 12)) return;
      this.lastHit.push({ x: hx, y: hy, t: now });
      mark = this.oneShot(hx, hy, tex, anim, 68);
      if (mark) mark._t0 = now;
      if (key && mark) { this.marks.set(key, mark); mark.once('destroy', () => { if (this.marks.get(key) === mark) this.marks.delete(key); }); }
    }
    if (!this.pxTex || (heavy && !fresh)) return;
    if (heavy) {
      const n = big ? 6 : 4, dark = [6, 7, 3, 4, 2, 5];
      for (let i = 0; i < n; i++) { const a = back + rnd(-1.4, 1.4), v = rnd(140, 240); this.part('debris', [dark[i]], hx, hy, Math.cos(a) * v, Math.sin(a) * v - 60, { g: 700, life: 600, bounce: 0.3, spin: rnd(-12, 12), depth: 69, blink: 150 }); }
      this.shards(hx, hy, 2, 200);
    } else {
      const seq = laser ? [PX.cplus, PX.c2, PX.b1] : [PX.y2, PX.y2, PX.o2, PX.r1];
      for (let i = 0; i < 3; i++) { const a = back + rnd(-1.1, 1.1), v = rnd(90, 170); this.part('px', seq, hx, hy, Math.cos(a) * v, Math.sin(a) * v - 40, { g: 520, drag: 1.2, life: rnd(220, 320), depth: 69 }); }
    }
  }

  terrainHit(x, y) {
    if (this.art) this.oneShot(x, y + 1, 'hit-dirt', 'hit-dirt', 62, 0.5, 1);
    if (!this.art) this.spark(x, y - 1, 2, 'fire', 110, 60);
  }

  pickupGet(x, y) {
    if (this.art) {
      this.oneShot(x, y, 'ring', 'ring', 68);
      for (let i = 0; i < 4; i++) this.scene.time.delayedCall(i * 50, () => this.oneShot(x + rnd(-10, 10), y + rnd(-10, 6), 'twinkle', 'twinkle', 69));
    }
  }

  dust(x, y, s = 1) {
    if (!this.art) return;
    const d = this.oneShot(x, y + 1, 'dust', 'dust', 49, 0.5, 1);
    if (d && s < 1) d.anims.timeScale = 1.3;
    if (this.pxTex && s >= 1) for (let i = 0; i < 2; i++) this.part('px', [PX.dust2, PX.g1], x + rnd(-6, 6), y - 1, rnd(-40, 40), -rnd(40, 80), { g: 500, life: 300 });
  }

  // ---------------------------------------------------------------- explosions
  explode(x, y, s = 1) {
    const sc = this.scene;
    // aerial kill: centre the blast on the drone itself and throw its wreck (rotor, hull chunks, falling smoke)
    const dr = sc.enemies && sc.enemies.getChildren().find(e => e.active && e.texture && e.texture.key === 'drone' && Math.abs(e.x - x) < 3 && Math.abs(e.y - e.height / 2 - y) < 3);
    if (dr) { y = dr.y; this.droneWreck(dr); }
    const size = s < 0.75 ? 'sm' : s < 1.25 ? 'md' : 'lg';
    const tex = { sm: 'explosion-sm', md: 'explosion', lg: 'explosion-big' }[size];
    if (this.art) {
      this.booms.push({ x, y, t: sc.time.now });
      if (size !== 'sm') this.killZones.push({ x, y, t: sc.time.now });
      const xs = this.oneShot(x, y, tex, 'xp-' + size, 70);
      if (size === 'lg') {                                    // kill flash: hard white-yellow star + ring, biggest thing on screen
        // Contra clear-space: enemy bolts right around the blast vanish
        if (sc.eBullets) for (const q of sc.eBullets.getChildren()) if (q.active && !q.noStyle && Math.abs(q.x - x) < 40 && Math.abs(q.y - y) < 40) { q.setActive(false).setVisible(false); if (q.body) q.body.stop(); }
        this.oneShot(x, y, 'killflash', 'kill-flash', 71);
        this.oneShot(x, y, 'ring', 'ring', 69);
      }
      if (size === 'sm') this.oneShot(x, y, 'ring', 'ring', 64);              // capsule pop
      // lingering smoke puffs rise out of the fireball
      const np = size === 'sm' ? 1 : size === 'md' ? 2 : 3;
      for (let i = 0; i < np; i++) sc.time.delayedCall(180 + i * 70, () => {
        const pf = this.oneShot(x + rnd(-8, 8) * s, y - rnd(2, 10) * s, 'puff', 'puff-solid', 50);
        if (pf) sc.tweens.add({ targets: pf, y: pf.y - rnd(10, 18), x: pf.x + rnd(-4, 4), duration: 430 });
      });
      if (size === 'lg') for (let i = 0; i < 2; i++) sc.time.delayedCall(90 + i * 110, () =>
        this.oneShot(x + rnd(-18, 18), y + rnd(-16, 10), 'explosion-sm', 'xp-sm', 66));
      // debris chunks + sparks + embers
      const nd = Math.round(5 * s);
      for (let i = 0; i < nd; i++) {
        const f = Math.floor(rnd(0, 8));
        this.part('debris', [f], x + rnd(-4, 4), y + rnd(-4, 4), rnd(-120, 120) * s, -rnd(120, 260) * Math.sqrt(s),
          { g: 750, life: rnd(900, 1300), bounce: 0.3, spin: rnd(-14, 14), depth: 64, blink: 300 });
      }
      this.spark(x, y, Math.round(6 * s), 'fire', 170 * Math.sqrt(s), 40);
      this.shards(x, y, Math.round(size === 'sm' ? 4 : size === 'md' ? 7 : 10), 240 * Math.sqrt(s));
      this.embers(x, y - 4, Math.round(3 * s), 10 * s);
    } else {
      const e = sc.add.sprite(x, y, 'explosion').setDepth(65).setScale(s);
      sc.tweens.add({ targets: e, scale: s * 1.5, alpha: 0, duration: 300, onComplete: () => e.destroy() });
    }
    this.shake(size === 'lg' ? 260 : size === 'md' ? 130 : 70, size === 'lg' ? 0.011 : size === 'md' ? 0.006 : 0.003);
    if (s >= 0.75) this.hitstop(size === 'lg' ? 80 : 45);
    sc.sfx?.play(s > 1.2 ? 'boom-big' : 'boom');
  }

  droneWreck(dr) {
    const sc = this.scene, fr = dr.frame, W = fr.width, H = fr.height, now = sc.time.now;
    const flip = dr.flipX;
    // hull split into 4 cropped chunks of the drone's own art
    const cuts = [[0, 0, W / 2, H / 2], [W / 2, 0, W / 2, H / 2], [0, H / 2, W / 2, H / 2], [W / 2, H / 2, W / 2, H / 2]];
    for (const [cx, cy, cw, ch] of cuts) {
      const img = sc.add.image(0, 0, dr.texture.key, fr.name).setCrop(cx, cy, cw, ch).setFlipX(flip).setDepth(43)
        .setOrigin((cx + cw / 2) / W, (cy + ch / 2) / H);
      const ox = (flip ? W - (cx + cw / 2) : cx + cw / 2) - W / 2, oy = cy + ch / 2 - H / 2;
      this.wrecks.push({ img, x: dr.x + ox, y: dr.y + oy, vx: ox * 4 + rnd(-30, 30), vy: -rnd(60, 140) + oy * 3, spin: rnd(-9, 9), smoke: 0, t: 0, life: 1400, hot: cy === 0 });
    }
    if (sc.textures.exists('rotor')) {
      const img = sc.add.image(0, 0, 'rotor').setDepth(44);
      this.wrecks.push({ img, x: dr.x, y: dr.y - H / 2 + 4, vx: rnd(-50, 50), vy: -rnd(160, 220), spin: rnd(24, 34) * (Math.random() < 0.5 ? -1 : 1), smoke: 0, t: 0, life: 1500, hot: false });
    }
  }

  // crisp pixel-digit score: pops up, holds, blinks out (sits 14px above the kill, never over the impact)
  scorePop(ev) { this.scene.time.delayedCall(260, () => { try { this._scorePop(ev); } catch (e) {} }); }
  _scorePop({ x, y, n }) {
    const sc = this.scene, str = String(n), w = str.length * 6 + 1; y -= 8;
    const c = sc.add.container(Math.round(x - w / 2), Math.round(y - 8)).setDepth(90);
    [...str].forEach((d, i) => c.add(sc.add.image(i * 6, 0, 'digits', +d).setOrigin(0, 0)));
    sc.tweens.add({ targets: c, y: c.y - 10, duration: 260, ease: 'Quad.easeOut' });
    sc.time.delayedCall(560, () => { if (!c.scene) return; let k = 0; sc.time.addEvent({ delay: 60, repeat: 7, callback: () => { if (!c.scene) return; c.setVisible(++k % 2 === 0); if (k >= 8) c.destroy(); } }); });
  }

  // enemy wind-up tell: one crisp glint that pops at the muzzle, a second brighter one just before the shot
  telegraphTell({ enemy, x, y, ms }) {
    const sc = this.scene;
    this.oneShot(x, y, 'glint', 'eflash', 57);
    sc.time.delayedCall(Math.max(60, (ms || 300) - 110), () => { if (enemy && enemy.active) this.oneShot(x, y, 'glint', 'tell2', 57); });
  }

  powerupBurst({ weapon, x, y }) {
    const sc = this.scene;
    const tint = { M: 0xffd060, S: 0xff7040, L: 0x80e8ff, R: 0xffffff }[weapon] ?? 0xffffff;
    for (let i = 0; i < 2; i++) sc.time.delayedCall(i * 90, () => { const r = this.oneShot(x, y, 'ring', 'ring', 70); if (r && tint !== 0xffffff) r.setTint(tint); });
    for (let i = 0; i < 6; i++) sc.time.delayedCall(i * 45, () => this.oneShot(x + rnd(-5, 5), y - i * 7, 'twinkle', 'twinkle', 71));
    this.shake(60, 0.002);
  }

  respawnFlash(p) {
    const sc = this.scene;
    for (let i = 0; i < 4; i++) sc.time.delayedCall(i * 70, () => this.oneShot(p.x + rnd(-8, 8), (sc.cameras.main.scrollY || 0) + 20 + i * 18, 'twinkle', 'twinkle', 71));
  }

  // ---------------------------------------------------------------- deaths
  soldierDeath(e, from) {
    const sc = this.scene;
    const vx = from && from.body ? from.body.velocity.x : 0;
    const dir = vx ? Math.sign(vx) : (from && from.x < e.x ? 1 : -1);
    const cy = e.y - 18;
    const d = sc.add.sprite(e.x, e.y, e.texture.key, e.frame.name).setOrigin(0.5, 1).setDepth(45).setFlipX(e.flipX);
    d.setTint(0x605040).setTintMode(Phaser.TintModes.ADD);                     // 1-2 frame white hit-flash
    setTimeout(() => d.active && d.clearTint(), 34);
    const da = sc.anims.get('soldier-die');
    if (da && da.frames && da.frames.length && da.frames[0].textureKey === e.texture.key) d.play('soldier-die');
    // bright fireball pop (white -> yellow -> orange -> red) in front of the body, then grey smoke
    // kill payoff: one layered ~30px burst ABOVE the body, nudged toward the shooter; replaces the contact star
    const mk_ = this.marks.get(e); if (mk_ && mk_.scene) mk_.destroy(); this.marks.delete(e);
    const bx = e.x - dir * 5, by = cy - 2;
    this.oneShot(bx, by, 'explosion', 'xp-kill', 68);
    this.killZones.push({ x: bx, y: by, t: sc.time.now });
    if (this.pxTex) for (let i = 0; i < 7; i++) { const a = rnd(0, PI * 2), v = rnd(80, 190); this.part('px', [PX.y2, PX.o2, PX.o1, PX.r1], bx, by, Math.cos(a) * v, Math.sin(a) * v - 50, { g: 480, drag: 1, life: rnd(260, 420), depth: 69 }); }
    sc.time.delayedCall(150, () => this.smokePuffs(e.x + dir * 2, cy - 2, 2, 3));
    this.shards(bx, by, 3, 180);
    if (this.pxTex) for (let i = 0; i < 2; i++) this.part('debris', [i], e.x, cy, dir * rnd(50, 110), -rnd(130, 200), { g: 700, life: 650, bounce: 0.3, spin: rnd(-10, 10), depth: 46 });
    // Contra fling: up and back, drop, a dust puff, blink out
    const gy = this.groundAt(e.x + dir * 26);
    const landY = gy < e.y + 40 ? gy : e.y;
    sc.tweens.add({ targets: d, x: e.x + dir * 26, y: e.y - 18, angle: dir * 25, duration: 220, ease: 'Quad.easeOut',
      onComplete: () => sc.tweens.add({ targets: d, y: landY, angle: dir * 80, duration: 240, ease: 'Quad.easeIn',
        onComplete: () => {
          this.smokePuffs(d.x, landY - 4, 1, 3);
          let n = 0; const ev = sc.time.addEvent({ delay: 50, repeat: 3, callback: () => { d.setVisible(++n % 2 === 0); if (n >= 4) d.destroy(); } });
          d.once('destroy', () => ev.remove());
        } }) });
    this.shake(70, 0.0025);
    this.hitstop(30);
    sc.sfx?.play('enemy-die');
  }

  // ---------------------------------------------------------------- juice
  shake(ms, amt) { this.scene.cameras.main.shake(ms, amt); }

  hitstop(ms) {
    const sc = this.scene, w = sc.physics.world, now = performance.now();
    this.frozenUntil = Math.max(this.frozenUntil, now + ms);
    if (this.frozen) return;
    this.frozen = true; w.pause(); sc.anims.pauseAll(); sc.tweens.pauseAll();
    const check = () => {
      if (performance.now() < this.frozenUntil - 1) { setTimeout(check, this.frozenUntil - performance.now()); return; }
      this.frozen = false; if (!sc.sys.isActive()) return;
      w.resume(); sc.anims.resumeAll(); sc.tweens.resumeAll();
    };
    setTimeout(check, ms);
  }

  // ---------------------------------------------------------------- per-frame visual pass
  post(time, delta) {
    try { this._post(time, delta); } catch (e) { if (!this._warned) { this._warned = 1; console.warn('fx post error', e && e.message); } }
  }
  _post(time, delta) {
    if (this.frozen) return;
    const sc = this.scene; delta *= sc.time.timeScale ?? 1;   // honours debug slow-mo
    const dt = Math.min(delta, 50) / 1000;
    // particles
    for (let i = this.parts.length - 1; i >= 0; i--) {
      const q = this.parts[i]; q.t += delta;
      if (q.t >= q.life || !q.img.scene) { if (q.img.scene) { q.img.setVisible(false).setActive(false); this.free.push(q.img); } this.parts.splice(i, 1); continue; }
      if (!q.rest) {
        q.vy += q.g * dt; if (q.drag) { q.vx -= q.vx * q.drag * dt; q.vy -= q.vy * q.drag * dt; }
        q.x += q.vx * dt; q.y += q.vy * dt;
        if (q.bounce >= 0 && q.ground && q.vy > 0) {
          const gy = this.groundAt(q.x);
          if (q.y >= gy - 1 && q.y < gy + 8) {
            q.y = gy - 1;
            if (q.vy > 60) { q.vy = -q.vy * q.bounce; q.vx *= 0.55; q.spin *= 0.5; } else { q.rest = 1; q.spin = 0; }
          }
        }
      }
      const fr = q.loop && !q.rest ? q.frames[Math.floor(q.t / q.loop) % q.frames.length]
        : q.loop ? q.frames[0] : q.frames[Math.min(q.frames.length - 1, Math.floor(q.t / q.life * q.frames.length))];
      q.img.setFrame(fr).setPosition(Math.round(q.x), Math.round(q.y));
      if (q.spin) q.img.rotation += q.spin * dt;
      if (q.orient) q.img.rotation = Math.atan2(q.vy, q.vx);
      if (q.blink && q.life - q.t < q.blink) q.img.setVisible(Math.floor(q.t / 50) % 2 === 0);
    }
    // drone wreckage: falls, spins, trails smoke, bumps the ground and blinks out
    for (let i = this.wrecks.length - 1; i >= 0; i--) {
      const w = this.wrecks[i]; w.t += delta;
      if (w.t > w.life || !w.img.scene) { w.img.destroy(); this.wrecks.splice(i, 1); continue; }
      if (!w.rest) {
        w.vy += 600 * dt; w.x += w.vx * dt; w.y += w.vy * dt; w.img.rotation += w.spin * dt;
        const gy = this.groundAt(w.x);
        if (w.vy > 0 && w.y >= gy - 3 && w.y < gy + 10) {
          w.y = gy - 3;
          if (w.vy > 120) { w.vy *= -0.3; w.vx *= 0.5; w.spin *= 0.4; if (this.art) this.oneShot(w.x, gy + 1, 'hit-dirt', 'hit-dirt', 62, 0.5, 1); }
          else { w.rest = 1; w.life = Math.min(w.life, w.t + 500); }
        }
        if (w.hot && (w.smoke -= delta) <= 0 && w.t < 1000) { w.smoke = 100; this.part('puff', [1, 2, 2, 3], w.x, w.y - 2, rnd(-6, 6), -rnd(10, 25), { g: -10, life: 420, depth: 42, ground: false }); if (w.hot) this.part('px', [PX.y2, PX.o1, PX.r1], w.x, w.y, rnd(-20, 20), -rnd(10, 30), { g: 0, life: 200, depth: 44, ground: false }); }
      }
      w.img.setPosition(Math.round(w.x), Math.round(w.y));
      if (w.life - w.t < 400) w.img.setVisible(Math.floor(w.t / 50) % 2 === 0);
    }
    // heavy targets below 60% hp: persistent smoke + sparks rising off them
    if (time > this.nextDmg && this.art) {
      this.nextDmg = time + 110;
      for (const g of [sc.enemies, sc.bossParts]) if (g) for (const e of g.getChildren()) {
        if (!e.active || !e._fxMaxHp || e._fxMaxHp < 8 || e.hp === undefined) continue;
        const left = e.hp / e._fxMaxHp; if (left >= 0.6) continue;
        const eb = e.body; if (!eb) continue;
        const px = rnd(eb.left + 3, eb.right - 3), py = eb.top + rnd(1, 6);
        if (Math.random() < 0.7) this.part('puff', [1, 2, 2, 3], px, py, rnd(-6, 6), -rnd(18, 32), { g: -10, life: 500, depth: 46, ground: false });
        if (Math.random() < (left < 0.3 ? 0.8 : 0.4)) this.part('px', [PX.y2, PX.o1, PX.r1], px, py + 4, rnd(-50, 50), -rnd(60, 120), { g: 400, life: 260, depth: 47 });
      }
    }
    // muzzle flash sticks to the gun
    for (let i = this.followers.length - 1; i >= 0; i--) {
      const f = this.followers[i];
      if (!f.spr.scene || !f.owner.active || f.owner.dead) { this.followers.splice(i, 1); continue; }
      const m = f.owner.muzzle(); f.spr.setPosition(Math.round(m.x), Math.round(m.y));
    }
    if (!this.art) return;
    // bullets: per-weapon / per-direction animated frames, hitbox untouched and kept centred
    const altT = Math.floor(time / 70) % 2 ? 3 : 0;
    const style = (b, wpn) => {
      if (b.texture.key !== 'fxb') b.setTexture('fxb', 0);
      if (b._fxBorn !== b.born || b._fxOff !== b.body.offset.x) {
        b._fxBorn = b.born; b._fxW = wpn(); b._fxVar = (this.slugN = (this.slugN || 0) + 1) % 2 ? 3 : 0;
        b.body.setOffset((24 - b.body.width) / 2, (24 - b.body.height) / 2); b._fxOff = b.body.offset.x;
        b._fxHidden = false;
      }
      const row = WROW[b._fxW] ?? 0, v = b.body.velocity, a = Math.atan2(v.y, v.x);
      const alt = row === 1 ? b._fxVar : altT;
      const o = ((Math.round(a / OCT) % 8) + 8) % 8, snapped = Math.abs(a - Math.round(a / OCT) * OCT) < 0.06;
      if (row === 2 || row === 4) { b.setFrame(row * 6 + alt).setFlip(false, false).setRotation(0); return; }
      if (!snapped) { b.setFrame(row * 6 + alt).setFlip(v.x < 0, false).setRotation(v.x < 0 ? a - PI : a); return; }
      let col, fx = false, fy = false;
      if (o === 0 || o === 4) { col = 0; fx = o === 4; } else if (o === 2 || o === 6) { col = 2; fy = o === 2; }
      else { col = 1; fx = o === 3 || o === 5; fy = o === 1 || o === 3; }
      b.setFrame(row * 6 + col + alt).setFlip(fx, fy).setRotation(0);
    };
    if (sc.pBullets) for (const b of sc.pBullets.getChildren()) {
      if (!b.active || !b.body) continue;
      style(b, () => (sc.player && sc.player.weapon) || 'R');
      if (b._fxW === 'L' && b.visible && this.pxTex) {           // laser leaves a short cyan wake
        const v = b.body.velocity, sp = Math.hypot(v.x, v.y) || 1;
        this.part('px', [PX.c2, PX.b1], b.x - v.x / sp * 12, b.y - v.y / sp * 12, 0, 0, { g: 0, life: 70, depth: 54, ground: false });
      }
    }
    // enemy bolts: 16-angle pre-drawn magenta capsules w/ hard-pixel trail; pink star flash only where no muzzle flash fired
    const eAlt = Math.floor(time / 60) % 2 ? 16 : 0;
    if (sc.eBullets && sc.textures.exists('ebolt')) for (const b of sc.eBullets.getChildren()) {
      if (!b.active || !b.body || b.noStyle) continue;          // opt-out: boss saws / shells keep their own look
      if (b.texture.key !== 'ebolt') b.setTexture('ebolt', 0);
      if (b._fxBorn !== b.born || b._fxOff !== b.body.offset.x) {
        const fresh = b._fxBorn !== b.born; b._fxBorn = b.born;
        b.body.setOffset((40 - b.body.width) / 2, (40 - b.body.height) / 2); b._fxOff = b.body.offset.x;
        if (fresh) {
          const now = sc.time.now; this.eMuzzles = this.eMuzzles.filter(m => now - m.t < 80);
          // spawn star only for shooters without their own muzzle flash (drones), so hits never stack pink + orange
          const drone = sc.enemies && sc.enemies.getChildren().some(e => e.active && e.texture && e.texture.key === 'drone' && Math.abs(e.x - b.x) < 24 && Math.abs(e.y - b.y) < 24);
          if (drone && !this.eMuzzles.some(m => Math.abs(m.x - b.x) < 20 && Math.abs(m.y - b.y) < 20)) this.oneShot(b.x, b.y, 'hit', 'dflash', 57);
        }
      }
      const v = b.body.velocity, i = ((Math.round(Math.atan2(v.y, v.x) / (PI / 8)) % 16) + 16) % 16;
      b.setFrame(i + eAlt).setFlip(false, false).setRotation(0);
    }
    if (sc.eBullets && !sc.textures.exists('ebolt')) for (const b of sc.eBullets.getChildren()) if (b.active && b.body && !b.noStyle) style(b, () => 'E');
    // pickups twinkle
    if (sc.pickups && time > this.nextTwinkle) {
      this.nextTwinkle = time + 160;
      for (const k of sc.pickups.getChildren()) if (k.active && Math.random() < 0.6)
        this.oneShot(k.x + rnd(-10, 10), k.y + rnd(-8, 6), 'twinkle', 'twinkle', 44);
    }
  }
}

// No effect may ever throw during gameplay: guard every public entry point.
for (const name of ['muzzle', 'impact', 'terrainHit', 'pickupGet', 'dust', 'explode', 'soldierDeath', 'droneWreck', 'shake', 'hitstop', 'spark', 'shards', 'smokePuffs', 'embers', 'flash']) {
  const fn = FX.prototype[name];
  if (typeof fn !== 'function') continue;
  FX.prototype[name] = function (...args) {
    try { return fn.apply(this, args); } catch (e) { console.warn('fx.' + name + ' skipped:', e && e.message); return null; }
  };
}
