// counts frames where two live ground units on the same floor are closer than 24 px (on screen)
window.__stack = { frames: 0, bad: 0, worst: 1e9 };
const o = window.__stepN; window.__stepN = (n, r) => { for (let i = 0; i < n; i++) { o(1, r && i === n - 1);
  const s = window.__sheep.game.scene.getScene('Game'); if (!s || !s.enemies) continue; const cam = s.cameras.main;
  const g = s.enemies.getChildren().filter(e => e.active && !e.dead && e.body && e.body.allowGravity && !e.isCapsule && e.body.blocked.down && e.x > cam.scrollX && e.x < cam.scrollX + 480);
  window.__stack.frames++; let bad = false;
  for (let a = 0; a < g.length; a++) for (let b = a + 1; b < g.length; b++) if (Math.abs(g[a].y - g[b].y) < 10) { const d = Math.abs(g[a].x - g[b].x); window.__stack.worst = Math.min(window.__stack.worst, d); if (d < 24) bad = true; }
  if (bad) window.__stack.bad++; } };
