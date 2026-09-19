// Simple "average player" autopilot for scripted full-stage runs (evaluated in the page by play.mjs --bot 1).
// Runs right, holds fire, aims 8-way at the nearest target, jumps pits / walls / incoming shots. Writes window.__sheep.inject.
(() => {
  const PI = Math.PI;
  let jumpT = 0, f = 0, turnT = 0;
  window.__botLog = [];
  window.__bot = () => {
    f++;
    const g = window.__sheep.game, s = g.scene.getScene('Game');
    const inj = window.__sheep.inject; for (const k in inj) inj[k] = false;
    if (!s || !s.sys.isActive() || !s.player) { inj.start = f % 30 < 3; return; }
    const p = s.player; if (p.dead) return;
    if (s.flow === 'continue') { inj.start = f % 30 < 3; return; }
    const cam = s.cameras.main, W = 480, px = p.x, py = p.y - 26;
    const onGround0 = () => p.body.blocked.down || p.body.touching.down;
    // nearest target on screen
    let best = null, bd = 1e9;
    const consider = (e, ey) => {
      if (!e.active || e.x < cam.scrollX + 2 || e.x > cam.scrollX + W - 2) return;
      const shooter = e.windup !== undefined || e.constructor.name === 'Rifleman' || e.constructor.name === 'Turret' || e.constructor.name === 'Drone';
      const dx = e.x - px, dy = ey - py, d = Math.hypot(dx, dy) * (dx < 0 ? 1.6 : 1) * (shooter ? 0.55 : 1);
      if (d < bd) { bd = d; best = { dx, dy, e }; }
    };
    for (const e of s.enemies.getChildren()) consider(e, e.isCapsule || e.originY !== 1 ? e.y : e.y - 18);
    if (s.bossParts) for (const e of s.bossParts.getChildren()) if (e.hp > 0 && e.body && e.body.enable) consider(e, e.y);
    let right = true, left = false, up = false, down = false, jump = false;
    if (s.boss) right = px < cam.scrollX + 170;
    const bossT = best && s.bossParts && s.bossParts.contains(best.e);
    if (bossT) {   // stand where a 45-degree shot lands on the part
      const wantX = Math.max(cam.scrollX + 20, Math.min(cam.scrollX + 300, best.e.x - Math.max(0, py - best.e.y)));
      right = px < wantX - 4; if (px > wantX + 4) { left = true; right = false; }
    }
    if (best) {
      const a = Math.atan2(best.dy, best.dx);
      let o = Math.round(a / (PI / 4)); // -4..4
      if (best.dx < 0 && Math.abs(best.dx) < 170 && Math.abs(best.dy) < 40 && f > turnT) { right = false; left = true; }
      if (bossT) { if (best.dy < -12) up = true; if (up && Math.abs(px - (best.e.x - (py - best.e.y))) < 8) { right = true; } }
      else if (o === -2) { right = false; left = false; up = true; }             // straight up: stand still
      else if (o === -1 || o === -3) up = true;
      else if (o === 1 || o === 3) down = true;
      else if (o === 2 && !p.body.blocked.down) down = true;
    }
    // big units (tank, mech, mutant, walker): hold a firing distance instead of walking into them
    for (const e of s.enemies.getChildren()) if (e.active && !e.dead && (e.hp >= 8 || e.bigBoom) && !e.isCapsule && e.x - px > -12 && e.x - px < 130 && Math.abs(e.y - p.y) < 50) { right = false; break; }
    // shields: jump over and shoot down into them (front shots ricochet)
    const onG1 = p.body.blocked.down || p.body.touching.down;
    if (best && best.e.blocks && !best.e.dead) {
      const facingUs = best.e.flipX ? px > best.e.x : px < best.e.x;
      if (facingUs) { right = best.dx > -40; left = !right; up = false; if (onG1 && Math.abs(best.dx) < 120) jump = true; if (!onG1) down = true; }
    }
    // mech gatling: read the tell like a player would - high stream (even pattern) = go prone, low stream = jump it
    for (const e of s.enemies.getChildren()) {
      if (!e.active || e.dead || e.pattern === undefined) continue;
      const high = e.state === 'spin' ? e.pattern % 2 === 0 : e.state === 'fire' ? (e.pattern - 1) % 2 === 0 : null;
      if (high !== null) window.__botHigh = high;
      if (high === true && onG1) { inj.down = true; inj.fire = true; return; }
    }
    // stay down until the high stream has fully passed
    if (window.__botHigh && onG1 && s.eBullets.getChildren().some(b => b.active && String(b.src).startsWith('mech') && Math.abs(b.x - px) < 160)) { inj.down = true; inj.fire = true; return; }
    // beams / flames with a visible tell: go prone under a walker beam, back off a toxic
    for (const e of s.enemies.getChildren()) {
      if (!e.active) continue;
      if (((e.state === 'charge' || e.state === 'beam') && e.beamRect !== undefined || e.tell) && Math.abs(e.y - p.y) < 20) { if (onG1) { inj.down = true; inj.fire = true; return; } }
    }
    // hazards
    const onG = p.body.blocked.down || p.body.touching.down;
    const dir = left ? -1 : 1;
    if (onG && s.standY(px + dir * 22) === null && (right || left)) jump = true;
    if (onG && (p.body.blocked.right || p.body.blocked.left)) jump = true;
    let proneDodge = false;
    for (const b of s.eBullets.getChildren()) {
      if (!b.active) continue;
      const vx = b.body.velocity.x, vy = b.body.velocity.y;
      // where is the bullet when it reaches our x?
      if (Math.sign(px - b.x) !== Math.sign(vx) && Math.abs(px - b.x) > 6) continue;
      const tt = Math.abs(vx) > 1 ? (px - b.x) / vx : Math.abs((py - b.y) / (vy || 1));
      if (tt < 0 || tt > 0.45) continue;
      const yAt = b.y + vy * tt;
      if (yAt < p.y - 40 || yAt > p.y + 2) continue;          // passes over / under us
      if (yAt < p.y - 14 && onGround0()) proneDodge = true; else jump = true;
    }
    if (proneDodge && !jump) { inj.down = true; inj.fire = true; inj.right = false; inj.left = false; return; }
    // soldier about to run into us at head height and we can't shoot it (e.g. behind): hop
    for (const e of s.enemies.getChildren()) if (e.active && e.dir !== undefined && Math.abs(e.x - px) < 34 && Math.abs(e.y - p.y) < 20) jump = true;
    if (jump && onG && f - jumpT > 8) { inj.jump = true; jumpT = f; }
    inj.right = right && !left; inj.left = left; inj.up = up; inj.down = down && !onG ? true : down && (right || left);
    inj.fire = f % 2 === 0 || true;
  };
})();
