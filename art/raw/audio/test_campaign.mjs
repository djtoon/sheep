// Campaign audio check: per-stage music + boss themes (lazy-loaded), intro/ending tracks, new SFX + loops. Exit 3 on page errors.
import { chromium } from 'playwright';
import { serve } from '../../../tools/serve.mjs';
const port = 9000 + Math.floor(Math.random() * 900); await serve(port);
const browser = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--autoplay-policy=no-user-gesture-required', '--enable-unsafe-swiftshader'] });
let errors = 0;
async function run(query, fn) {
  const page = await browser.newPage({ viewport: { width: 480, height: 270 } });
  page.on('pageerror', e => { errors++; console.log('[pageerror]', query, e.message); });
  page.on('console', m => { if (m.type() === 'error' || m.type() === 'warning') console.log('[console]', query, m.text()); });
  await page.goto(`http://localhost:${port}/index.html?test=1&god=1&${query}`);
  await page.waitForFunction(() => window.__sheep && window.__sheepAudio && window.__sheep.game.scene.getScenes(true).length, null, { timeout: 30000 });
  const r = await page.evaluate(fn); console.log(query.padEnd(14), JSON.stringify(r)); await page.close();
}
const stageFn = async () => {
  const wait = ms => new Promise(r => setTimeout(r, ms)); const A = window.__sheepAudio;
  for (let i = 0; i < 40 && !(A.Music.cur && A.Music.cur.src); i++) await wait(100);
  const g = window.__sheep.game.scene.getScene('Game'), c = A.Music.cur, out = { stage: g.stageNo, music: c && c.key, started: !!(c && c.src) };
  if (c && c.src) out.loop = [+c.src.loopStart.toFixed(3), +c.src.loopEnd.toFixed(3), +c.src.buffer.duration.toFixed(3)];
  await wait(1500); out.bossPrefetched = ['music-boss2', 'music-boss3'].filter(k => g.cache.audio.exists(k));
  g.events.emit('boss'); await wait(300); out.sting = A.Music.cur && A.Music.cur.key; await wait(2900);
  out.boss = A.Music.cur && A.Music.cur.key; out.bossStarted = !!(A.Music.cur && A.Music.cur.src);
  return out;
};
await run('stage=1', stageFn); await run('stage=2', stageFn); await run('stage=3', stageFn);
const storyFn = name => new Function(`return (async () => { const name = '${name}';` + (async () => {
  const wait = ms => new Promise(r => setTimeout(r, ms)); const A = window.__sheepAudio;
  await wait(2500); const sc = window.__sheep.game.scene.getScenes(true).filter(x => x.scene.key !== 'Boot')[0];
  A.Music.play(sc, name); for (let i = 0; i < 40 && !(A.Music.cur && A.Music.cur.src); i++) await wait(100);
  const c = A.Music.cur; return { scene: sc.scene.key, music: c && c.key, started: !!(c && c.src), loop: c && c.src ? [+c.src.loopStart.toFixed(3), +c.src.loopEnd.toFixed(3)] : null };
}).toString().replace(/^async \(\) => \{/, '') + ')()');
await run('scene=intro', storyFn('intro')); await run('scene=ending', storyFn('ending'));
await run('scene=title', async () => {
  const wait = ms => new Promise(r => setTimeout(r, ms)); const A = window.__sheepAudio;
  await wait(5000); const sc = window.__sheep.game.scene.getScene('Title');
  return { music: A.Music.cur && A.Music.cur.key, introPrefetched: sc.cache.audio.exists('music-intro') };
});
await run('stage=2', async () => {  // every new sfx + loops through a real Sfx
  const wait = ms => new Promise(r => setTimeout(r, ms));
  for (let i = 0; i < 50 && !window.__sheep.game.scene.getScene('Game')?.sfx; i++) await wait(100);
  const g = window.__sheep.game.scene.getScene('Game'), b = window.__sheepAudio.audioBus(g);
  const an = b.ctx.createAnalyser(); an.fftSize = 2048; b.clip.connect(an); const d = new Float32Array(2048); let pk = 0;
  const iv = setInterval(() => { an.getFloatTimeDomainData(d); for (const v of d) pk = Math.max(pk, Math.abs(v)); }, 30);
  const names = ['shotgun', 'ricochet', 'sniper-charge', 'sniper', 'tank', 'gatling-spin', 'gatling', 'laser-bolt', 'flame', 'xeno-screech', 'xeno-pounce', 'mutant-roar', 'goo', 'glass', 'queen-roar', 'rotor', 'thump', 'page', 'phone'];
  const missing = [], played = [];
  for (const n of names) { if (!g.cache.audio.exists('sfx-' + n)) missing.push(n); g.sfx.play(n); if ((g.sfx.active[n] || []).length) played.push(n); await wait(90); }
  const h1 = g.sfx.loop('rotor', 0.8), h2 = g.sfx.loop('flame', 0.7); await wait(1500); const loops = Object.keys(g.sfx.loops);
  h1.stop(200); g.sfx.stopLoop('flame'); await wait(300);
  clearInterval(iv); return { played: played.length + '/' + names.length, missing, loops, loopsAfterStop: Object.keys(g.sfx.loops), peak: +pk.toFixed(3) };
});
console.log(errors ? 'PAGE ERRORS: ' + errors : 'no page errors'); await browser.close(); process.exit(errors ? 3 : 0);
