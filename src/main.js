import { Boot } from './scenes/Boot.js';
import { Title } from './scenes/Title.js';
import { Game } from './scenes/Game.js';
import { HUD } from './scenes/HUD.js';

export const W = 480, H = 270;
const q = new URLSearchParams(location.search);

// Test / debug hooks used by tools/shot.mjs. Never gate gameplay on these except via query flags.
window.__sheep = {
  ready: false,
  query: q,
  debug: { god: q.get('god') === '1', hitboxes: q.get('hitboxes') === '1' },
  stats: () => {
    const g = window.__sheep.game; const s = g && g.scene.getScene('Game');
    const live = s && s.sys && s.sys.isActive() && s.player;
    const p = live ? s.player : null, b = p && p.body, cam = live ? s.cameras.main : null;
    return { fps: g ? Math.round(g.loop.actualFps) : 0, scene: g ? g.scene.getScenes(true).map(x => x.scene.key) : [],
      t: live ? Math.round(s.time.now) : 0,
      player: p ? { x: Math.round(p.x), y: Math.round(p.y), vx: Math.round(b.velocity.x), vy: Math.round(b.velocity.y), lives: s.state.lives,
        ground: !!(b.blocked.down || b.touching.down), spin: !!p.spinning, prone: !!p.prone, dead: !!p.dead, invuln: Math.max(0, Math.round(p.invuln)),
        aim: [p.aim.x, p.aim.y], facing: p.facing, weapon: p.weapon } : null,
      cam: cam ? Math.round(cam.scrollX) : 0,
      enemies: live && s.enemies ? s.enemies.countActive() : 0,
      onscreen: live && s.enemies ? s.enemies.getChildren().filter(e => e.active && e.x > cam.scrollX - 8 && e.x < cam.scrollX + 488).length : 0,
      pShots: live && s.pBullets ? s.pBullets.countActive() : 0, eShots: live && s.eBullets ? s.eBullets.countActive() : 0,
      score: s && s.state ? s.state.score : 0, kills: s && s.stat ? s.stat.kills : 0, shots: s && s.stat ? s.stat.shots || 0 : 0, deaths: s && s.stat ? s.stat.deaths : 0,
      paused: !!(s && s.paused), boss: !!(s && s.boss), cleared: !!(s && s.cleared), flow: s && s.flow || null };
  },
};

const game = new Phaser.Game({
  type: Phaser.WEBGL,
  parent: 'game',
  width: W, height: H,
  backgroundColor: '#07080c',
  pixelArt: true,
  roundPixels: true,
  scale: { mode: Phaser.Scale.FIT, autoCenter: Phaser.Scale.CENTER_BOTH },
  physics: { default: 'arcade', arcade: { gravity: { y: 900 }, debug: window.__sheep.debug.hitboxes } },
  input: { gamepad: true },
  scene: [Boot, Title, Game, HUD],
});
window.__sheep.game = game;
