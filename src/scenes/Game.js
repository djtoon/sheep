import { stage1 } from '../level/stage1.js';
import { LevelView } from '../level/LevelView.js';
import { Player } from '../entities/Player.js';
import { ENEMY_TYPES } from '../entities/Enemies.js';
import { BossWall } from '../entities/Boss.js';
import { WEAPONS } from '../entities/weapons.js';
import { FX } from '../fx/FX.js';
import { Sfx } from '../audio/Sfx.js';
import { Controls } from '../input.js';

const STAGES = { 1: stage1 };
const rnd = Phaser.Math.Between;

// Scene events Game emits (for FX / HUD / audio). Payloads in brackets.
//   score [total]  lives [n]  weapon [key]  boss  cleared  gameover          (existing)
//   scorepop [{x, y, n}]            floating score number where an enemy died
//   powerup [{weapon, x, y}]        weapon capsule collected
//   telegraph [{enemy, x, y, ms}]   an enemy is about to fire from (x, y) in ms   (emitted by Enemies.js)
//   player-jump / player-land [player]   player-death [player]   player-respawn [player]
//   pause [bool]                    Enter toggled pause
//   continue [{seconds}]  continue-tick [secondsLeft]  continued   game-over countdown / player took the continue
//   stage-end [{score, kills, shots, hits, accuracy, lives, livesBonus, time, deaths, continues, hi, next}]  results screen (holds for Enter or 6 s)
//   extralife [lives]               1-UP at 20,000 / 80,000 / ...
// Until a HUD/FX owner draws scorepop / pause / continue itself (set scene.hooked.<name> = true), Game draws a plain fallback.
export class Game extends Phaser.Scene {
  constructor() { super('Game'); }

  init(data) {
    this.stageNo = data.stage || 1;
    this.level = STAGES[this.stageNo];
    this.state = data.state || { score: 0, lives: 3, hi: +(localStorage.getItem('af-hi') || 0), continues: 0 };
    this.stat = { kills: 0, deaths: 0, killLog: [], deathLog: [], t0: 0 };
    this.hooked = { scorepop: false, pause: false, continue: false, telegraph: false, results: false };
    // Phaser reuses this scene instance on every start: clear per-run state left over from the previous run
    // (a stale `leaving` blocked the return to the title; a stale lastCamX/camMoveT read as "camping" and muted the soldier stream)
    this.leaving = false; this.lastCamX = undefined; this.camMoveT = undefined;
    this.contUI = null; this.pauseUI = null; this.resUI = null; this.contEv = null; this.resultsEv = null;
  }

  create() {
    const L = this.level, q = window.__sheep.query;
    this.physics.world.setBounds(0, -200, L.width, L.height + 400);
    this.physics.world.checkCollision.down = false;
    this.fx = new FX(this); this.sfx = new Sfx(this); this.controls = new Controls(this);
    this.view = new LevelView(this, L);
    this.flow = 'play'; this.paused = false; this.startLock = this.time.now + 500; this.stat.t0 = this.time.now;

    // terrain physics
    this.solids = this.physics.add.staticGroup();
    for (const s of L.ground) this.addBlock(this.solids, s.x, s.y, s.w, L.height - s.y + 100);
    this.platforms = this.physics.add.staticGroup();
    for (const p of L.platforms) {
      const b = this.addBlock(this.platforms, p.x, p.y, p.w, 6);
      b.body.checkCollision.down = false; b.body.checkCollision.left = false; b.body.checkCollision.right = false;
    }

    // actors
    const startX = +(q.get('x') || 60);
    const gy = this.groundYAt(startX);
    this.player = new Player(this, startX, (gy < L.height ? gy : (this.standY(startX) ?? gy)) - 1);
    this.enemies = this.add.group({ runChildUpdate: true });
    this.bossParts = this.physics.add.group({ allowGravity: false, immovable: true });
    this.pickups = this.physics.add.group();
    this.pBullets = this.physics.add.group({ allowGravity: false, maxSize: 40 });
    this.eBullets = this.physics.add.group({ allowGravity: false, maxSize: 80 });

    const oneWay = (a, plat) => this.time.now > (a.dropUntil || 0) && a.body.velocity.y >= 0 && a.body.prev.y + a.body.height <= plat.body.top + 4;
    this.physics.add.collider(this.player, this.solids);
    this.physics.add.collider(this.player, this.platforms, null, oneWay);
    this.physics.add.collider(this.enemies, this.solids);
    this.physics.add.collider(this.enemies, this.platforms, null, (e, plat) => !e.isCapsule && e.body.velocity.y >= 0);
    this.physics.add.collider(this.pickups, this.solids);
    this.physics.add.collider(this.pickups, this.platforms);
    // player bullets vs enemies: custom scan in hitScan() (generous Contra-style enemy shot boxes, see there)
    this.physics.add.overlap(this.pBullets, this.bossParts, (b, e) => this.bulletHit(b, e));
    // player damage uses the small per-stance hurtbox (Player.hurtRect), not the collision body
    this.physics.add.overlap(this.player, this.eBullets, (p, b) => { if (p.hurt('bullet:' + (b.src || '?'))) this.killEnemyBullet(b); }, (p, b) => b.active && p.touches(b.body));
    this.physics.add.overlap(this.player, this.enemies, (p, e) => p.hurt('contact:' + (e.constructor && e.constructor.name)),
      (p, e) => e.active && !e.isCapsule && !(e instanceof ENEMY_TYPES.turret) && p.touches(e.body, 3)
        && !(e.body.allowGravity && !e.body.blocked.down && e.y < p.y - 8));   // a grunt coming down on top of you doesn't kill: only one on your level
    this.physics.add.overlap(this.player, this.pickups, (p, k) => this.collect(k), (p, k) => !p.dead);

    // camera: Contra-style - follows forward, never scrolls back, leads a little when running
    const cam = this.cameras.main;
    cam.setBounds(0, 0, L.width, L.height);
    cam.scrollX = Phaser.Math.Clamp(startX - 140, 0, L.width - this.scale.width);
    this.camMinX = cam.scrollX; this.lead = 0;
    this.spawnIdx = 0; while (this.spawnIdx < L.spawns.length && L.spawns[this.spawnIdx].x < cam.scrollX + this.scale.width) this.spawnIdx++;
    this.stream = null; this.nextStream = 0;
    // test jumps into the middle of the level: resume whatever soldier stream was active there
    for (let i = 0; i < this.spawnIdx; i++) if (L.spawns[i].type === 'stream') this.setStream(L.spawns[i]);
    this.boss = null; this.cleared = false;

    this.scene.launch('HUD', { game: this });
    this.events.emit('weapon', this.player.weapon);
    if (q.get('weapon')) this.player.setWeapon(q.get('weapon'));
    window.__sheep.ready = true;
  }

  addBlock(group, x, y, w, h) {
    const z = this.add.zone(x + w / 2, y + h / 2, w, h);
    group.add(z); z.body.updateFromGameObject(); return z;
  }

  // walk up small ledges and onto bridges/platforms (<= 10px above the feet) instead of stopping or dropping
  stepUp(a) {
    const b = a.body; if (!b || !b.enable || !b.blocked.down && !b.touching.down) return;
    const vx = b.velocity.x; if (!vx) return;
    const ax = a.x + Math.sign(vx) * (b.halfWidth + 2);
    let best = null;
    for (const s of this.level.ground) if (ax >= s.x && ax < s.x + s.w && s.y < a.y - 0.5 && a.y - s.y <= 10) best = Math.min(best ?? 1e9, s.y);
    if (this.time.now > (a.dropUntil || 0))
      for (const p of this.level.platforms) if (ax >= p.x && ax < p.x + p.w && p.y < a.y - 0.5 && a.y - p.y <= 10) best = Math.min(best ?? 1e9, p.y);
    if (best !== null) { a.y = best - 0.5; b.updateFromGameObject(); b.setVelocityY(0); return; }
    // a knee-high step (11-26 px) while running into it: the sheep vaults it with a small hop instead of sticking to the wall
    if (a === this.player && !a.prone && (b.blocked.right || b.blocked.left)) {
      for (const s of this.level.ground) if (ax >= s.x && ax < s.x + s.w && s.y < a.y - 0.5 && a.y - s.y <= 26) {
        const h = a.y - s.y + 5; b.setVelocityY(-Math.sqrt(2 * (900 + (b.gravity.y || 0)) * h)); a.vaulting = this.time.now; break;
      }
    }
  }

  groundYAt(x) {
    let best = this.level.height + 100;
    for (const s of this.level.ground) if (x >= s.x && x < s.x + s.w) best = Math.min(best, s.y);
    return best;
  }
  groundAhead(x, y) {
    for (const s of this.level.ground) if (x >= s.x && x < s.x + s.w && s.y >= y - 4) return true;
    for (const p of this.level.platforms) if (x >= p.x && x < p.x + p.w && Math.abs(p.y - y) < 6) return true;
    return false;
  }
  // one-way platform directly under an actor's feet (not solid ground at the same height) -> can drop through
  platformUnder(a) {
    const x = a.x, y = a.y;
    if (Math.abs(this.groundYAt(x) - y) < 3) return null;
    return this.level.platforms.find(p => x >= p.x - 4 && x < p.x + p.w + 4 && Math.abs(p.y - y) < 3) || null;
  }
  // something to stand on at x (ground or platform), for pickups / respawns
  standY(x) {
    let best = this.groundYAt(x);
    for (const p of this.level.platforms) if (x >= p.x && x < p.x + p.w) best = Math.min(best, p.y);
    return best < this.level.height ? best : null;
  }

  // ------------------------------------------------------------------ shooting
  firePlayer(o, aim, w) {
    if (this.pBullets.countActive() + w.spread.length > w.max) return false;   // Contra on-screen bullet cap
    const base = Math.atan2(aim.y, aim.x);
    for (const d of w.spread) {
      const a = base + d;
      const b = this.pBullets.get(o.x, o.y, w.tex); if (!b) return false;
      b.setActive(true).setVisible(true).setDepth(55).setRotation(a);
      b.setTexture(w.tex); b.body.setSize(b.frame.realWidth, b.frame.realHeight);
      b.body.reset(o.x, o.y); b.body.setAllowGravity(false);
      b.body.setVelocity(Math.cos(a) * w.speed, Math.sin(a) * w.speed);
      b.dmg = w.dmg; b.pierce = !!w.pierce; b.hitSet = new Set(); b.born = this.time.now;
    }
    this.stat.shots = (this.stat.shots || 0) + 1; this.stat.bullets = (this.stat.bullets || 0) + w.spread.length;
    this.fx.muzzle(o.x, o.y, Math.cos(base), Math.sin(base), 1);
    this.sfx.play(w === WEAPONS.S ? 'spread' : w === WEAPONS.L ? 'laser' : 'shoot', 0.8);
    return true;
  }

  fireEnemy(x, y, vx, vy, src) {
    const b = this.eBullets.get(x, y, 'bullet-enemy'); if (!b) return;
    b.src = src || 'boss';
    b.setActive(true).setVisible(true).setDepth(56);
    b.body.enable = true; b.body.reset(x, y); b.body.setAllowGravity(false); b.body.setVelocity(vx, vy); b.born = this.time.now;
    b.body.setCircle(2, 1, 1);
    this.sfx.play('enemy-shot', 0.6);
  }
  killEnemyBullet(b) { b.setActive(false).setVisible(false); b.body.stop(); }

  bulletHit(b, e) {
    if (b.dmg === undefined) [b, e] = [e, b]; // arcade may hand the pair over in either order
    if (!b.active || !e.active || b.hitSet.has(e)) return;
    if (!b.hitSet.size) this.stat.hits = (this.stat.hits || 0) + 1;   // accuracy: bullets that hit something
    b.hitSet.add(e);
    this.fx.impact(b.x, b.y);
    e.damage(b.dmg, b);
    if (!b.pierce) this.killBullet(b);
  }
  // Player shots vs enemies with Contra-generous boxes: a bullet counts as >= 6 px tall, and anything that walks
  // (soldiers, riflemen) is hittable from 14 px above its head to 14 px below its feet: a level shot kills a grunt on a
  // step up to ~40 px above you or 14 px below you, and a prone shot one a full 32 px tier below.
  // Flyers/turrets get a 3 px apron, capsules 4 px all round.
  hitScan() {
    const es = this.enemies.getChildren();
    for (const b of this.pBullets.getChildren()) {
      if (!b.active || !b.body) continue;
      const bb = b.body, cy = bb.center.y, h = Math.max(6, bb.height) / 2;
      const x0 = bb.x, x1 = bb.right, y0 = cy - h, y1 = cy + h;
      for (const e of es) {
        if (!e.active || !e.body || !e.damage) continue;
        const eb = e.body, walker = e.body.allowGravity && !e.isCapsule, pad = e.isCapsule ? 4 : 1;
        const ext = e.shotExt ?? (walker ? 14 : 3), head = e.shotHead ?? (walker ? 14 : pad);
        if (x1 > eb.x - pad && x0 < eb.right + pad && y1 > eb.y - head && y0 < eb.bottom + Math.max(pad, ext)) {
          this.bulletHit(b, e); if (!b.active) break;
        }
      }
    }
  }
  killBullet(b) { b.setActive(false).setVisible(false); b.body.stop(); b.body.enable = true; this.pBullets.killAndHide(b); }

  // ------------------------------------------------------------------ score
  addScore(n, x, y) {
    const before = this.state.score; this.state.score += n;
    // Contra-style extra lives at 20,000 and every 60,000 after
    for (const m of [20000, 80000, 140000, 200000]) if (before < m && this.state.score >= m) {
      this.state.lives++; this.events.emit('lives', this.state.lives); this.events.emit('extralife', this.state.lives); this.sfx.play('pickup');
    }
    if (this.state.score > this.state.hi) { this.state.hi = this.state.score; try { localStorage.setItem('af-hi', this.state.hi); } catch (e) {} }
    this.events.emit('score', this.state.score);
    if (x !== undefined) { this.events.emit('scorepop', { x, y, n }); if (!this.hooked.scorepop) this.scorePop(x, y, n); }
  }
  enemyKilled(e) { this.stat.kills++; this.stat.killLog.push(Math.round(this.time.now - this.stat.t0)); }

  // fallback floating score (plain bitmap text); replaced once an FX/HUD owner sets hooked.scorepop
  scorePop(x, y, n) {
    // sits ~14 px above the kill and waits 120 ms, so the hit/explosion reads first; small, rises, fades out in steps
    this.time.delayedCall(120, () => {
      const font = this.cache.bitmapFont.exists('hud-font') ? 'hud-font' : null;
      const px = Math.round(x), py = Math.round(y - 14);
      const t = font ? this.add.bitmapText(px, py, font, String(n)).setOrigin(0.5, 1)
        : this.add.text(px, py, String(n), { fontFamily: 'monospace', fontSize: '8px', color: '#fff', stroke: '#000', strokeThickness: 2 }).setOrigin(0.5, 1);
      t.setDepth(70);
      this.tweens.add({ targets: t, y: py - 12, duration: 520, ease: 'Cubic.out' });
      this.tweens.add({ targets: t, alpha: 0, delay: 380, duration: 300, ease: 'Stepped', easeParams: [3], onComplete: () => t.destroy() });
    });
  }

  // ------------------------------------------------------------------ spawning
  setStream(s) {
    this.stream = s.off ? null : { min: s.every?.[0] ?? 1400, max: s.every?.[1] ?? 2600, left: s.left ?? 0.25, cap: s.cap ?? 3, pair: s.pair ?? 0.35 };
    this.nextStream = this.time.now + (s.off ? 0 : 600);
  }

  // one grunt at a screen edge; returns false if that edge is a pit or the player is standing right there
  edgeSoldier(side) {
    const cam = this.cameras.main, W = this.scale.width, p = this.player;
    const x = side < 0 ? cam.scrollX - 14 : cam.scrollX + W + 14;
    if (p && Math.abs(p.x - (side < 0 ? cam.scrollX : cam.scrollX + W)) < 80) return false;
    let y = this.groundYAt(x);
    if (y > this.level.height) {   // over a chasm: run in along the bridge (the lowest platform there), if any
      const br = this.level.platforms.filter(pl => x >= pl.x && x < pl.x + pl.w).sort((a, b) => b.y - a.y)[0];
      if (!br) return false; y = br.y;
    }
    // never stack: the previous grunt from this edge must have cleared ~28 px first
    if (this.enemies.getChildren().some(o => o.active && o instanceof ENEMY_TYPES.soldier && Math.abs(o.x - x) < 28 && Math.abs(o.y - y) < 20)) return 'busy';
    const e = new ENEMY_TYPES.soldier(this, x, y); e.dir = side < 0 ? 1 : -1; this.enemies.add(e);
    return true;
  }

  spawn(s) {
    if (s.type === 'stream') return this.setStream(s);
    if (s.type === 'capsule') return this.spawnCapsule(this.cameras.main.scrollX + this.scale.width + 10, s.y, s.drop);
    const T = ENEMY_TYPES[s.type];
    const one = (i) => {
      if (!this.player || this.cleared) return;
      const R2 = this.cameras.main.scrollX + this.scale.width;
      if (s.type === 'soldier' && !s.at) {
        const side = s.side === 'L' ? -1 : s.side === 'LR' ? (i % 2 ? -1 : 1) : 1;
        const r = this.edgeSoldier(side);
        if (r === 'busy') this.time.delayedCall(200, () => one(i));   // spacing: try again a moment later
        else if (!r) this.edgeSoldier(-side);
        return;
      }
      let x = s.at ?? R2 + 16, y;
      if (s.type === 'drone') { x = R2 + 20; y = 60 + Math.random() * 40; }
      else {
        if (s.y === undefined) { let n = 0; while (this.groundYAt(x) > this.level.height && n++ < 40) x += 8; } // never spawn over a pit
        y = s.y ?? this.groundYAt(x);
      }
      const e = new T(this, x, y); this.enemies.add(e);
    };
    const n = s.count || 1;
    for (let i = 0; i < n; i++) this.time.delayedCall(i * (s.gap || 0), () => one(i));
  }

  spawnCapsule(x, y, drop) {
    // flying weapon capsule (Contra falcon pod): sine-flies left, shoot it to drop a pickup
    const c = this.physics.add.image(x, y, 'capsule').setDepth(42);
    c.isCapsule = true;
    c.body.setAllowGravity(false); c.hp = 1; c.t0 = this.time.now; c.baseY = y;
    c.damage = () => {
      if (!c.active) return;
      this.sfx.play('capsule');
      this.fx.explode(c.x, c.y, 0.6);
      const p = this.pickups.create(c.x, c.y, 'pickup-' + drop).setDepth(43);
      // hop toward something solid (never into a pit)
      let vx = 40; if (this.standY(c.x + 34) === null) vx = this.standY(c.x - 34) !== null ? -40 : 0;
      p.kind = drop; p.body.setVelocity(vx, -180); p.body.setBounce(0.3); p.body.setDragX(40);
      c.destroy();
    };
    c.update = (t) => { c.body.setVelocityX(-55); c.y = c.baseY + Math.sin((t - c.t0) / 260) * 16; if (c.x < this.cameras.main.scrollX - 40) c.destroy(); };
    this.enemies.add(c);
  }

  collect(k) {
    if (!k.active) return;
    const p = this.player;
    p.setWeapon(k.kind); this.addScore(500); this.sfx.play('pickup');
    this.fx.pickupGet(k.x, k.y);
    this.events.emit('powerup', { weapon: k.kind, x: k.x, y: k.y });
    // the sheep flashes white twice: you feel the upgrade land
    for (let i = 0; i < 4; i++) this.time.delayedCall(i * 60, () => { if (i % 2 === 0) p.setTint(0xffffff).setTintMode(Phaser.TintModes.FILL); else p.clearTint(); });
    k.destroy();
  }

  // ------------------------------------------------------------------ death / respawn / continue
  onPlayerDeath(p) {
    this.sfx.play('die');
    this.stat.deaths++; this.stat.deathLog.push({ t: Math.round(this.time.now - this.stat.t0), x: Math.round(p.x), y: Math.round(p.y), cause: p.cause });
    this.state.lives--; this.events.emit('lives', this.state.lives);
    this.events.emit('player-death', p);
    this.fx.shake(200, 0.006);
    p.body.enable = false; p.play2('sheep-die'); p.clearTint();
    const inPit = p.y > this.level.height;
    if (inPit) { this.time.delayedCall(900, () => this.respawn()); return; }
    this.tweens.add({ targets: p, y: p.y - 30, x: p.x - p.facing * 30, angle: -p.facing * 360, duration: 500, ease: 'Quad.easeOut',
      onComplete: () => this.tweens.add({ targets: p, y: Math.min(this.groundYAt(p.x) + 2, this.level.height + 40), duration: 300, ease: 'Quad.easeIn',
        onComplete: () => this.time.delayedCall(700, () => this.respawn()) }) });
  }

  // drop in from the top of the screen over solid footing, flashing with i-frames (Contra: ~2 s)
  respawn() {
    if (this.state.lives < 0) return this.gameOver();
    const p = this.player, cam = this.cameras.main, W = this.scale.width;
    let x = cam.scrollX + 60;
    for (let tx = cam.scrollX + 56; tx < cam.scrollX + W - 60; tx += 8) if (this.standY(tx) !== null) { x = tx; break; }
    p.setAngle(0).clearTint(); p.body.enable = true; p.dead = false; p.invuln = 2600; p.setWeapon('R');
    p.spinning = false; p.prone = false; p.setStance('stand');
    p.body.reset(x, -6); p.body.setVelocity(0, 60);
    this.events.emit('player-respawn', p);
  }

  gameOver() {
    this.flow = 'gameover';
    this.events.emit('gameover');
    this.time.delayedCall(2200, () => {
      this.flow = 'continue'; this.contLeft = 9;
      this.events.emit('continue', { seconds: this.contLeft });
      this.drawContinue();
      this.contEv = this.time.addEvent({ delay: 1000, repeat: 8, callback: () => {
        this.contLeft--; this.events.emit('continue-tick', this.contLeft); this.drawContinue();
        if (this.contLeft <= 0) this.time.delayedCall(700, () => this.flow === 'continue' && this.toTitle());
      } });
    });
  }
  drawContinue() {
    if (this.hooked.continue) return;
    if (!this.contUI) {
      const W = this.scale.width, H = this.scale.height;
      const mk = (y, s, font) => (this.cache.bitmapFont.exists(font) ? this.add.bitmapText(W / 2, y, font, s)
        : this.add.text(W / 2, y, s, { fontFamily: 'monospace', fontSize: '10px', color: '#fff', stroke: '#000', strokeThickness: 2 })).setOrigin(0.5, 0).setScrollFactor(0).setDepth(1000);
      this.contUI = [mk(H / 2 + 26, 'CONTINUE?  9', 'hud-font-gold'), mk(H / 2 + 40, 'PRESS START', 'hud-font')];
    }
    this.contUI[0].setText('CONTINUE?  ' + Math.max(0, this.contLeft));
  }
  doContinue() {
    this.contEv?.remove(); this.contUI?.forEach(t => t.destroy()); this.contUI = null;
    this.state.lives = 3; this.state.score = 0; this.state.continues = (this.state.continues || 0) + 1;
    this.events.emit('score', 0); this.events.emit('lives', 3); this.events.emit('continued');
    const hud = this.scene.get('HUD'); if (hud && hud.clearBanner) hud.clearBanner();   // drop the GAME OVER card
    this.sfx.play('start');
    this.flow = 'play'; this.respawn();
  }
  toTitle() {
    if (this.leaving) return; this.leaving = true;
    this.cameras.main.fadeOut(400, 0, 0, 0);
    this.time.delayedCall(420, () => { this.scene.stop('HUD'); this.scene.start('Title'); });
  }

  // ------------------------------------------------------------------ boss / stage clear
  bossDefeated() {
    this.cleared = true; this.flow = 'clear'; this.stream = null;
    // (the boss runs its own death spectacle before calling this)
    // the base falls: every enemy on screen goes up with it, all enemy fire vanishes
    this.eBullets.getChildren().forEach(b => b.active && this.killEnemyBullet(b));
    this.enemies.getChildren().slice().forEach((e, i) => this.time.delayedCall(80 + i * 90, () => {
      if (!e.active) return;
      if (e.die && !e.isCapsule) e.die({ x: e.x - 1, body: null }); else e.destroy();
    }));
    this.events.emit('cleared');
    // Contra: a beat of silence on the rubble, then the hero runs off into the base
    this.time.delayedCall(3200, () => {
      const p = this.player; if (!p) return;
      p.auto = { right: true, left: false, up: false, down: false, jump: false, fire: false };
      this.time.delayedCall(3600, () => this.showResults());
    });
  }

  // stage-clear results: lives bonus is banked, then the HUD tally card holds until Enter / fire / jump or 6 s
  showResults() {
    const st = this.stat, lives = Math.max(0, this.state.lives);
    const bonus = lives * 2000;                       // Metal Slug-style survivor bonus
    const accuracy = st.bullets ? Math.round(100 * (st.hits || 0) / st.bullets) : 0;
    if (bonus) this.addScore(bonus);
    this.flow = 'results'; this.resultsFrom = this.time.now + 1200;
    const r = { score: this.state.score, kills: st.kills, shots: st.bullets || 0, hits: st.hits || 0, accuracy, lives, livesBonus: bonus,
      time: Math.round((this.time.now - st.t0) / 1000), deaths: st.deaths, continues: this.state.continues || 0, hi: this.state.hi, next: 'STAGE 2 COMING SOON' };
    this.results = r; window.__sheep.results = r;
    this.events.emit('stage-end', r);
    if (!this.hooked.results) this.drawResults(r);
    this.resultsEv = this.time.delayedCall(6000, () => this.toTitle());
  }
  // fallback results lines (under the HUD's STAGE CLEAR card + score tally); a HUD owner sets hooked.results to draw its own
  drawResults(r) {
    const W = this.scale.width;
    const mk = (y, s, font) => (this.cache.bitmapFont.exists(font) ? this.add.bitmapText(W / 2, y, font, s)
      : this.add.text(W / 2, y, s, { fontFamily: 'monospace', fontSize: '8px', color: '#fff', stroke: '#000', strokeThickness: 2 })).setOrigin(0.5, 0).setScrollFactor(0).setDepth(1000);
    const lines = [`KILLS ${r.kills}    ACCURACY ${r.accuracy} PCT`, `LIVES BONUS ${r.lives} X 2000  ${r.livesBonus}`, `TIME ${Math.floor(r.time / 60)}:${String(r.time % 60).padStart(2, '0')}`];
    this.resUI = lines.map((l, i) => mk(188 + i * 11, l, 'hud-font'));
    this.resUI.push(mk(226, r.next, 'hud-font-orange'));
    this.resUI.forEach((t, i) => { t.setVisible(false); this.time.delayedCall(300 + i * 250, () => t.setVisible(true)); });
  }

  // ------------------------------------------------------------------ pause
  setPaused(on) {
    this.paused = on;
    const w = this.physics.world;
    if (on) { w.pause(); this.anims.pauseAll(); this.tweens.pauseAll(); this.time.paused = true; this.enemies.runChildUpdate = false; this.fx.frozen = true; }
    else { w.resume(); this.anims.resumeAll(); this.tweens.resumeAll(); this.time.paused = false; this.enemies.runChildUpdate = true; this.fx.frozen = false; this.fx.frozenUntil = 0; }
    this.events.emit('pause', on);
    this.sfx.play('select');
    if (!this.hooked.pause) {
      if (on) {
        const W = this.scale.width, H = this.scale.height;
        const dim = this.add.rectangle(0, 0, W, H, 0x05040a, 0.5).setOrigin(0, 0).setScrollFactor(0).setDepth(999);
        const t = (this.cache.bitmapFont.exists('hud-big-gold') ? this.add.bitmapText(W / 2, H / 2 - 10, 'hud-big-gold', 'PAUSE')
          : this.add.text(W / 2, H / 2 - 10, 'PAUSE', { fontFamily: 'monospace', fontSize: '16px', color: '#ffd060', stroke: '#000', strokeThickness: 3 })).setOrigin(0.5, 0).setScrollFactor(0).setDepth(1000);
        this.pauseUI = [dim, t];
      } else { this.pauseUI?.forEach(o => o.destroy()); this.pauseUI = null; }
    }
  }

  // ------------------------------------------------------------------ frame
  update(time, dt) {
    const c = this.controls, p = this.player, cam = this.cameras.main, W = this.scale.width, L = this.level;
    c.poll();
    if (this.flow === 'results') { if (time > this.resultsFrom && (c.pressed('start') || c.pressed('fire') || c.pressed('jump'))) this.toTitle(); return; }
    if (this.flow === 'continue') { if (c.pressed('start') || c.pressed('fire') || c.pressed('jump')) this.doContinue(); return; }
    if (this.flow === 'play' && time > this.startLock && c.pressed('start')) this.setPaused(!this.paused);
    if (this.paused) { if (!this.physics.world.isPaused) this.physics.world.pause(); this.fx.frozen = true; return; }
    if (this.fx.frozen || this.physics.world.isPaused) { p.latch(time, c); return; }   // hit-stop: keep the presses, skip the sim

    if (p.auto && p.x > this.cameras.main.scrollX + W + 12) { p.body.enable = false; p.setVisible(false); return; }   // walked off into the base
    p.update(time, dt, c);
    this.stepUp(p);

    // forward-only camera with a small run-direction lead, eased so it never jerks
    const bossLock = this.boss && !p.auto ? L.boss.x + 140 - W : L.width - W;
    const leadWant = p.body.velocity.x > 0 ? 26 : 0;
    this.lead += Phaser.Math.Clamp(leadWant - this.lead, -dt * 0.03, dt * 0.05);
    const want = Phaser.Math.Clamp(p.x - (W * 0.42 - this.lead), this.camMinX, Math.min(L.width - W, bossLock));
    if (want > this.camMinX) this.camMinX = Math.min(want, this.camMinX + dt * 0.17);
    cam.scrollX = Math.round(this.camMinX);
    if (!p.dead) {
      if (p.x < cam.scrollX + 10) { p.x = cam.scrollX + 10; p.body.setVelocityX(Math.max(0, p.body.velocity.x)); }
      if (!p.auto && p.x > cam.scrollX + W - 10) p.x = cam.scrollX + W - 10;
      if (p.y > L.height + 30) { if (!p.hurt('pit')) { p.body.reset(cam.scrollX + 60, -20); this.respawnSafe(p); } }
    }
    this.view.update(cam);

    // scripted spawns (keyed on the camera's right edge) + the ambient soldier stream
    while (this.spawnIdx < L.spawns.length && L.spawns[this.spawnIdx].x <= cam.scrollX + W) this.spawn(L.spawns[this.spawnIdx++]);
    if (this.camMinX > (this.lastCamX ?? -1) + 1) { this.lastCamX = this.camMinX; this.camMoveT = time; }
    const camping = time - (this.camMoveT ?? time) > 6000;   // standing still >6 s: the ambient stream dries up (no kill farming)
    if (this.stream && this.flow === 'play' && !this.boss && !p.dead && !camping && time > this.nextStream) {
      const s = this.stream; this.nextStream = time + rnd(s.min, s.max);
      const grunts = this.enemies.getChildren().filter(e => e.active && e instanceof ENEMY_TYPES.soldier).length;
      if (grunts < s.cap) {
        const side = Math.random() < s.left ? -1 : 1, r = this.edgeSoldier(side);
        // Contra grunts often come in twos: a partner follows ~0.45 s behind (spacing rule still applies)
        if (r === true && grunts + 1 < s.cap && Math.random() < s.pair) this.time.delayedCall(450, () => this.stream && this.edgeSoldier(side));
        if (r === 'busy') this.nextStream = time + 250;
        else if (!r && (s.left <= 0 || this.edgeSoldier(-side) !== true)) this.nextStream = time + 400;   // no rear spawns where the beat says none
      }
    }
    if (!this.boss && L.boss && cam.scrollX + W >= L.boss.x + 100) { this.boss = new BossWall(this, L.boss.x); this.stream = null; this.events.emit('boss'); }
    if (this.boss) this.boss.update(time);

    // cull bullets + pickups
    const kill = (g) => g.getChildren().forEach(b => {
      if (b.active && (b.x < cam.scrollX - 20 || b.x > cam.scrollX + W + 20 || b.y < -20 || b.y > L.height + 20 || time - b.born > 3000)) { b.setActive(false).setVisible(false); b.body.stop(); }
    });
    kill(this.pBullets); kill(this.eBullets);
    this.hitScan();
    this.pBullets.getChildren().forEach(b => {
      // level shots may skim 10 px into a step's lip (Contra bullets ignore terrain entirely); downward shots hit the dirt
      const gy = this.groundYAt(b.x);
      if (b.active && b.y > gy + (b.body.velocity.y > 30 ? 0 : 10)) { this.fx.terrainHit(b.x, gy); this.killBullet(b); }
    });
    this.pickups.getChildren().forEach(k => { if (k.active && (k.x < cam.scrollX - 30 || k.y > L.height + 20)) k.destroy(); });
  }

  // god-mode pit fall: put the sheep back on solid ground
  respawnSafe(p) {
    const cam = this.cameras.main;
    for (let tx = cam.scrollX + 56; tx < cam.scrollX + this.scale.width - 60; tx += 8) if (this.standY(tx) !== null) { p.body.reset(tx, -6); return; }
  }
}
