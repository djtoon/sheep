import { STAGES } from '../level/stages.js';
import { makeView } from '../level/views.js';
import { Player } from '../entities/Player.js';
import { ENEMY_TYPES } from '../entities/Enemies.js';
import { TYPES } from '../entities/rosters.js';
import { BOSSES } from '../entities/bosses.js';
import { dropIn } from '../fx/dropin.js';
import { WEAPONS } from '../entities/weapons.js';
import { FX } from '../fx/FX.js';
import { Sfx } from '../audio/Sfx.js';
import { Controls } from '../input.js';

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
    this.stageNo = data.stage || 1; this.dropping = !!data.drop;
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
    this.view = makeView(this, L);
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
    if (this.state.weapon && this.state.weapon !== 'R') this.player.setWeapon(this.state.weapon);   // Contra: the gun you finished a stage with carries into the next
    if (q.get('weapon')) this.player.setWeapon(q.get('weapon'));
    if (this.dropping) { this.flow = 'drop'; this.cameras.main.fadeIn(400, 0, 0, 0); dropIn(this); }   // flow 'drop': no spawns, no enemy fire (canFire needs 'play')   // helicopter drop-in at stage start (story builder); calls dropDone()
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
      b.dmg = w.dmg; b.wpn = w.name; b.pierce = !!w.pierce; b.hitSet = new Set(); b.born = this.time.now;
    }
    this.pointBlank(o, w);
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
    // set-pieces soak at most 2 pellets of one spread volley, so point-blank S doesn't erase a mini-boss in 2 s
    if (e.volleyCap && b.born !== undefined) {
      if (e._vb !== b.born) { e._vb = b.born; e._vn = 0; }
      if (++e._vn > e.volleyCap) { this.fx.impact(b.x, b.y); this.killBullet(b); return; }
    }
    // set-piece damage budget: at most dpsCap damage per rolling second, so S/M/L all land in the same 4-8 s window
    // and the weak rifle (~4.5 dps, under the cap) still finishes it in ~11 s
    let dmg = b.dmg;
    if (e.dpsCap && b.wpn === 'RIFLE') dmg *= 2;   // the starting rifle is under the cap anyway: let it finish a set-piece in ~10 s
    if (e.dpsCap) {
      const now = this.time.now; e._dl = (e._dl || []).filter(h => now - h.t < 1000);
      const used = e._dl.reduce((a, h) => a + h.n, 0), room = e.dpsCap - used;
      if (room <= 0) { this.fx.impact(b.x, b.y); if (!b.pierce) this.killBullet(b); else b.hitSet.add(e); return; }
      dmg = Math.min(dmg, room); e._dl.push({ t: now, n: dmg });
    }
    if (!b.hitSet.size) this.stat.hits = (this.stat.hits || 0) + 1;   // accuracy: bullets that hit something
    b.hitSet.add(e);
    this.fx.impact(b.x, b.y);
    e.damage(dmg, b);
    if (!b.pierce) this.killBullet(b);
  }
  // point-blank: the gun muzzle sits ~30 px ahead of the sheep, so a bullet born past (or inside) an enemy the sheep is
  // pressed against would never touch it. Contra counts those: sweep the gap from the sheep's body to the muzzle.
  pointBlank(o, w) {
    const p = this.player, y = o.y, x0 = p.x, x1 = o.x;
    const fresh = this.pBullets.getChildren().filter(b => b.active && b.born === this.time.now);
    for (const e of this.enemies.getChildren()) {
      if (!e.active || !e.body || !e.damage || e.dead) continue;
      const eb = e.body;
      if (Math.max(x0, x1) < eb.x || Math.min(x0, x1) > eb.right || y < eb.y - 4 || y > eb.bottom + 4) continue;
      for (const b of fresh) if (b.active && !b.hitSet.has(e)) this.bulletHit(b, e);
    }
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
    if (this.stageNo > 1 ? this.groundCrowd(x, y, 32)   // stages 2+: any ground unit (roster walkers too) blocks the entry
        : this.enemies.getChildren().some(o => o.active && o instanceof ENEMY_TYPES.soldier && Math.abs(o.x - x) < 28 && Math.abs(o.y - y) < 20)) return 'busy';
    const e = new ENEMY_TYPES.soldier(this, x, y); e.dir = side < 0 ? 1 : -1; this.enemies.add(e);
    return true;
  }

  spawn(s) {
    if (s.type === 'stream') return this.setStream(s);
    if (s.type === 'capsule') return this.spawnCapsule(this.cameras.main.scrollX + this.scale.width + 10, s.y, s.drop);
    const T = TYPES[s.type];
    const tries = {};
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
      const left = s.side === 'L' || (s.side === 'LR' && i % 2 === 1), L0 = this.cameras.main.scrollX;
      let x = s.at ?? (left ? L0 - 16 : R2 + 16), y;
      if (!s.at && this.player && Math.abs(this.player.x - x) < 60) x += left ? -40 : 40;   // never appear on top of the sheep
      if (s.type === 'drone') { x = left ? L0 - 20 : R2 + 20; y = 60 + Math.random() * 40; }
      else {
        if (s.y === undefined) { let n = 0; while (this.groundYAt(x) > this.level.height && n++ < 40) x += left ? -8 : 8; } // never spawn over a pit
        y = s.y ?? this.groundYAt(x);
      }
      // never stack ground units: if another walker already stands within ~32 px of the entry point, try again shortly
      const flyer = s.type === 'drone' || s.type === 'drone2' || s.type === 'clawbot';
      if (!flyer && (tries[i] = (tries[i] || 0) + 1) < 12 && this.groundCrowd(x, y, 32)) { this.time.delayedCall(260, () => one(i)); return; }
      const e = new T(this, x, y); this.enemies.add(e);
      if (left && e.face) e.face(true);
      // set-piece (mini-boss): the camera holds at s.lockAt until it dies; the ambient stream pauses
      if (s.lock) {
        e.volleyCap = s.volleyCap ?? 2;
        if (s.hp) e.hp = s.hp;                 // spawn-entry HP override (tuned with dpsCap for weapon-independent length)
        if (s.dpsCap) e.dpsCap = s.dpsCap;
        this.setPiece = e; this.setPieceScroll = s.lockAt ?? this.cameras.main.scrollX; this.streamBeforeSet = this.stream; this.stream = null;
        this.events.emit('setpiece', { type: s.type, enemy: e });
      }
    };
    const n = s.count || 1;
    for (let i = 0; i < n; i++) this.time.delayedCall(i * (s.gap || 0), () => one(i));
  }

  groundCrowd(x, y, d) {
    return this.enemies.getChildren().some(o => o.active && !o.dead && o.body && o.body.allowGravity && !o.isCapsule && Math.abs(o.x - x) < d && Math.abs(o.y - y) < 20);
  }
  // soft separation: ground units on the same floor closer than one body width get eased apart (the one farther from
  // the sheep gives way), so troopers / mutants / crawlers never pile into one blob
  separateGround() {
    const g = this.enemies.getChildren().filter(e => e.active && !e.dead && e.body && e.body.allowGravity && !e.isCapsule && (e.body.blocked.down || e.body.touching.down));
    if (g.length < 2) return;
    const px = this.player.x;
    for (let i = 0; i < g.length; i++) for (let j = i + 1; j < g.length; j++) {
      const a = g[i], b = g[j];
      if (Math.abs(a.y - b.y) > 10) continue;
      const min = Math.max(28, Math.min(40, (a.body.width + b.body.width) / 2 + 10)), dx = b.x - a.x;
      if (Math.abs(dx) >= min) continue;
      let rear = Math.abs(a.x - px) > Math.abs(b.x - px) ? a : b, other = rear === a ? b : a;
      if (rear === this.setPiece || rear.bigBoom) [rear, other] = [other, rear];   // mini-bosses / heavies never get shoved
      if (rear === this.setPiece || rear.bigBoom) continue;
      const dir = rear.x === other.x ? (rear.x > px ? 1 : -1) : Math.sign(rear.x - other.x);
      const nx = rear.x + dir * Math.min(2, min - Math.abs(dx));
      if (this.groundAhead(nx + dir * 6, rear.y)) { rear.x = nx; rear.body.updateFromGameObject(); }
    }
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
  // after the results card: next stage keeps score/lives/continues, the last stage goes to the ending
  goNext() {
    if (this.leaving) return; this.leaving = true;
    const next = STAGES[this.stageNo + 1];
    const state = { ...this.state, lives: Math.max(this.state.lives, 1), weapon: this.player && !this.player.dead ? this.player.weapon : 'R' };
    this.cameras.main.fadeOut(400, 0, 0, 0);
    this.time.delayedCall(420, () => {
      this.scene.stop('HUD');
      if (next) this.scene.start('Game', { stage: this.stageNo + 1, state, drop: true });
      else this.scene.start(this.scene.get('Ending') ? 'Ending' : 'Title', { score: this.state.score });
    });
  }
  // stage-start drop-in (helicopter) finished: the player gets control
  dropDone() { this.dropping = false; if (this.flow === 'drop') this.flow = 'play'; if (this.player) this.player.auto = null; }
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
      time: Math.round((this.time.now - st.t0) / 1000), deaths: st.deaths, continues: this.state.continues || 0, hi: this.state.hi, next: STAGES[this.stageNo + 1] ? 'NEXT: ' + STAGES[this.stageNo + 1].name + (STAGES[this.stageNo + 1].subtitle ? ' - ' + STAGES[this.stageNo + 1].subtitle : '') : 'MISSION COMPLETE' };
    this.results = r; window.__sheep.results = r;
    this.events.emit('stage-end', r);
    if (!this.hooked.results) this.drawResults(r);
    this.resultsEv = this.time.delayedCall(6000, () => this.goNext());
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
    if (this.flow === 'results') { if (time > this.resultsFrom && (c.pressed('start') || c.pressed('fire') || c.pressed('jump'))) this.goNext(); return; }
    if (this.flow === 'continue') { if (c.pressed('start') || c.pressed('fire') || c.pressed('jump')) this.doContinue(); return; }
    if (this.flow === 'play' && time > this.startLock && c.pressed('start')) this.setPaused(!this.paused);
    if (this.paused) { if (!this.physics.world.isPaused) this.physics.world.pause(); this.fx.frozen = true; return; }
    if (this.fx.frozen || this.physics.world.isPaused) { p.latch(time, c); return; }   // hit-stop: keep the presses, skip the sim

    if (p.auto && p.x > this.cameras.main.scrollX + W + 12) { p.body.enable = false; p.setVisible(false); return; }   // walked off into the base
    p.update(time, dt, c);
    this.stepUp(p);

    // forward-only camera with a small run-direction lead, eased so it never jerks
    let bossLock = this.boss && !p.auto ? L.boss.x + 140 - W : L.width - W;
    if (this.setPiece) {
      if (this.setPiece.active && !this.setPiece.dead) {
        bossLock = Math.min(bossLock, Math.max(this.setPieceScroll, this.camMinX));
        // the set-piece never leaves the held screen (it must stay shootable)
        const sp = this.setPiece, lo = this.camMinX + 24, hi = this.camMinX + W - 24;
        if (sp.x > hi || sp.x < lo) { sp.x = Phaser.Math.Clamp(sp.x, lo, hi); sp.body.updateFromGameObject(); }
      }
      else { this.setPiece = null; this.stream = this.stream || this.streamBeforeSet || null; this.nextStream = time + 1500; this.events.emit('setpiece-end'); }
    }
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
    if (!this.dropping) while (this.spawnIdx < L.spawns.length && L.spawns[this.spawnIdx].x <= cam.scrollX + W) this.spawn(L.spawns[this.spawnIdx++]);
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
    if (!this.boss && L.boss && cam.scrollX + W >= L.boss.x + 100) { this.boss = new (BOSSES[L.boss.type || 'wall'] || BOSSES.wall)(this, L.boss.x); this.stream = null; this.events.emit('boss'); }
    if (this.boss) this.boss.update(time);

    // cull bullets + pickups
    const kill = (g) => g.getChildren().forEach(b => {
      if (b.active && (b.x < cam.scrollX - 20 || b.x > cam.scrollX + W + 20 || b.y < -20 || b.y > L.height + 20 || time - b.born > 3000)) { b.setActive(false).setVisible(false); b.body.stop(); }
    });
    kill(this.pBullets); kill(this.eBullets);
    this.hitScan();
    if (this.stageNo > 1) this.separateGround();   // stage 1 is frozen (its grunts already keep their own spacing)
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
