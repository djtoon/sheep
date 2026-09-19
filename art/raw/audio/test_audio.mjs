// Headless check of the audio runtime: buffers decoded, music playing with loop points, sfx fire, event wiring, output level.
// usage: node art/raw/audio/test_audio.mjs
import { chromium } from 'playwright';
import { serve } from '../../../tools/serve.mjs';
const port = 9000 + Math.floor(Math.random() * 900); await serve(port);
const browser = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--autoplay-policy=no-user-gesture-required', '--enable-unsafe-swiftshader'] });
const page = await browser.newPage({ viewport: { width: 480, height: 270 } });
const errs = []; page.on('pageerror', e => { errs.push(e.message); console.log('[pageerror]', e.message); });
page.on('console', m => { if (m.type() === 'error' || m.type() === 'warning') console.log('[console]', m.text()); });
await page.goto(`http://localhost:${port}/index.html?test=1&god=1`);
await page.waitForFunction(() => window.__sheep && window.__sheep.ready !== undefined && window.__sheep.game.scene.getScene('Game')?.sfx, null, { timeout: 30000 });
await page.waitForTimeout(800);
const r = await page.evaluate(async () => {
  const g = window.__sheep.game.scene.getScene('Game'), A = window.__sheepAudio, b = A.audioBus(g), ctx = b.ctx;
  const an = ctx.createAnalyser(); an.fftSize = 2048; b.clip.connect(an);
  const d = new Float32Array(an.fftSize); let peak = 0, sumsq = 0, n = 0;
  const sample = () => { an.getFloatTimeDomainData(d); for (const v of d) { peak = Math.max(peak, Math.abs(v)); sumsq += v * v; n++; } };
  const iv = setInterval(sample, 40);
  const wait = ms => new Promise(r => setTimeout(r, ms));
  const out = { state: ctx.state, rate: ctx.sampleRate, cur: A.Music.cur && A.Music.cur.key };
  const s = A.Music.cur && A.Music.cur.src; out.loop = s ? [s.loop, +s.loopStart.toFixed(3), +s.loopEnd.toFixed(3), +s.buffer.duration.toFixed(3)] : null;
  const keys = window.__sheep.game.cache.audio.getKeys(); out.decoded = keys.length; out.keys = keys.join(',');
  await wait(1500); out.musicOnly = { peak: +peak.toFixed(3), rms: +(10 * Math.log10(sumsq / n)).toFixed(1) }; peak = 0; sumsq = 0; n = 0;
  for (const nm of ['shoot', 'spread', 'laser', 'enemy-shot', 'hit', 'enemy-die', 'boom', 'boom-big', 'jump', 'land', 'pickup', 'die', 'capsule', 'select', 'start']) { g.sfx.play(nm); await wait(120); }
  g.player.weapon = 'M'; g.sfx.play('shoot'); out.mActive = (g.sfx.active['shoot-m'] || []).length;
  for (let i = 0; i < 8; i++) { g.sfx.play('boom-big'); g.sfx.play('boom'); await wait(60); } // stress: stacked explosions
  await wait(600); out.withSfx = { peak: +peak.toFixed(3) };
  g.events.emit('boss'); await wait(300); out.afterBoss = A.Music.cur && A.Music.cur.key;
  await wait(2800); out.afterWarning = A.Music.cur && A.Music.cur.key;
  g.events.emit('cleared'); await wait(200); out.afterClear = A.Music.cur && A.Music.cur.key; await wait(300);
  // round 2 events
  const played = []; const orig = g.sfx.play.bind(g.sfx);
  g.sfx.play = (n, v) => { const before = (g.sfx.active[n === 'shoot' && g.player.weapon === 'M' ? 'shoot-m' : n] || []).length; orig(n, v); played.push(n + ((g.sfx.active[n] || []).length > before ? '' : '(x)')); };
  g.setPaused(true); await wait(400); out.pausedMusicGain = +b.music.gain.value.toFixed(3); g.setPaused(false); await wait(500); out.unpausedMusicGain = +b.music.gain.value.toFixed(3);
  for (let i = 0; i < 6; i++) g.events.emit('telegraph', { enemy: null, x: 0, y: 0, ms: 400 }); await wait(50);
  g.addScore(20000); await wait(100);
  g.collect({ active: true, kind: 'S', x: g.player.x, y: g.player.y, destroy() {} }); await wait(100);
  g.events.emit('player-land', g.player); await wait(50);
  out.played = played.join(' ');
  out.activePickup = (g.sfx.active.pickup || []).length;
  g.state.lives = -1; g.gameOver(); await wait(300); out.gameover = A.Music.cur && A.Music.cur.key;
  await wait(3300); out.continueFlow = g.flow; g.doContinue(); await wait(300); out.afterContinue = A.Music.cur && A.Music.cur.key;
  await wait(3200); out.afterContinueSting = A.Music.cur && A.Music.cur.key;
  g.toTitle(); await wait(1500); out.titleMusic = A.Music.cur && A.Music.cur.key;
  clearInterval(iv); return out;
});
console.log(JSON.stringify(r, null, 1));
console.log(errs.length ? 'PAGE ERRORS: ' + errs.length : 'no page errors');
await browser.close(); process.exit(errs.length ? 3 : 0);
