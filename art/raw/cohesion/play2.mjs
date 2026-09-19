// cohesion pass: copy of art/raw/feel/play.mjs with --script2 (runs after --until, with the bot switched off)
// Deterministic game-feel harness (feel builder). Drives the REAL game with a virtual clock at exactly 60 fps,
// so timings/positions are measured in game time regardless of how slow headless Chromium renders.
//
//   node art/raw/feel/play.mjs [--query "god=1&x=600"] [--script "hold:right+fire:1500 tap:jump wait:400 shot:name"]
//        [--bot 1] [--until "js expr"] [--max ms] [--clip shots/feel/x.mp4] [--scale 2] [--every 2]
//        [--trace art/raw/feel/x.json] [--sample 6] [--eval "js"] [--print "js expr"]
// Script input names: left right up down jump fire start (combine with +). key:Enter sends a real keyboard event.
// Steps: hold:KEYS:ms  down:KEYS  up:KEYS  tap:KEYS  wait:ms  shot:name  eval:js  mark:label  step:frames
import { chromium } from 'playwright';
import { serve } from '../../../tools/serve.mjs';
import fs from 'node:fs'; import path from 'node:path'; import { execFileSync } from 'node:child_process';

const args = process.argv.slice(2); const o = { scale: 2, every: 2, sample: 6, query: '', max: 240000 };
for (let i = 0; i < args.length; i++) o[args[i].replace(/^--/, '')] = args[++i];
const port = 9000 + Math.floor(Math.random() * 900);
const server = await serve(port);
const browser = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--autoplay-policy=no-user-gesture-required', '--enable-unsafe-swiftshader'] });
const page = await browser.newPage({ viewport: { width: 480 * +o.scale, height: 270 * +o.scale } });
const errors = [];
page.on('console', m => { if (m.type() === 'error') console.log('[console.error]', m.text()); if (m.text().startsWith('[feel]')) console.log(m.text()); });
page.on('pageerror', e => { errors.push(e.message); console.log('[pageerror]', e.stack || e.message); });
await page.addInitScript(() => {
  // virtual clock: performance.now + setTimeout follow game time once enabled
  const realNow = performance.now.bind(performance), realST = window.setTimeout.bind(window);
  let on = false, now = 0, q = [], id = 1e6;
  performance.now = () => on ? now : realNow();
  const realDate = Date.now.bind(Date); let d0 = 0;
  Date.now = () => on ? d0 + now : realDate();   // TweenManager keeps its own Date.now clock
  window.setTimeout = (fn, ms = 0, ...a) => { if (!on) return realST(fn, ms, ...a); q.push({ t: now + (+ms || 0), fn, a, id: ++id }); return id; };
  const realCT = window.clearTimeout.bind(window);
  window.clearTimeout = (h) => { const i = q.findIndex(x => x.id === h); if (i >= 0) q.splice(i, 1); else realCT(h); };
  window.__vt = {
    enable() { now = realNow(); d0 = realDate() - now; on = true; },
    now: () => now,
    advance(ms) { now += ms; for (;;) { q.sort((a, b) => a.t - b.t); if (!q.length || q[0].t > now) break; const x = q.shift(); try { x.fn(...x.a); } catch (e) { console.error(e); } } },
  };
});
await page.goto(`http://localhost:${port}/index.html?test=1&${o.query}`);
await page.waitForFunction(() => window.__sheep && window.__sheep.ready, null, { timeout: 30000 });
await page.evaluate(() => {
  const g = window.__sheep.game; g.loop.sleep(); window.__vt.enable();
  window.__sheep.inject = { left: false, right: false, up: false, down: false, jump: false, fire: false, start: false };
  window.__frame = 0;
  window.__stepN = (n, render) => {
    const DT = 1000 / 60;
    for (let i = 0; i < n; i++) {
      window.__vt.advance(DT);
      if (render && i === n - 1) g.step(window.__vt.now(), DT); else g.headlessStep(window.__vt.now(), DT);
      window.__frame++;
      if (window.__bot) window.__bot();
      if (window.__traceOn && window.__frame % window.__traceEvery === 0) window.__trace.push(window.__sheep.stats());
    }
  };
});
if (o.eval) await page.evaluate(o.eval);
if (o.trace) await page.evaluate((n) => { window.__trace = []; window.__traceOn = true; window.__traceEvery = n; }, +o.sample);
if (o.bot) await page.evaluate(fs.readFileSync(new URL('../feel/bot.js', import.meta.url), 'utf8'));

const canvas = await page.$('canvas');
let frameDir = null, fno = 0;
if (o.clip) { frameDir = path.join('shots', '.feel_' + port); fs.mkdirSync(frameDir, { recursive: true }); }
const snap = async (file) => { fs.mkdirSync(path.dirname(file), { recursive: true }); await canvas.screenshot({ path: file }); console.log('saved', file); };
// advance `frames` game frames, recording a clip frame every o.every
async function run(frames) {
  if (!o.clip) { while (frames > 0) { const n = Math.min(frames, 60); await page.evaluate(n => window.__stepN(n, false), n); frames -= n; } return; }
  while (frames > 0) {
    const n = Math.min(frames, +o.every); await page.evaluate(n => window.__stepN(n, true), n); frames -= n;
    await canvas.screenshot({ path: path.join(frameDir, `f${String(fno++).padStart(5, '0')}.png`) });
  }
}
const setKeys = (ks, v) => page.evaluate(([ks, v]) => { for (const k of ks) window.__sheep.inject[k] = v; }, [ks, v]);
const ms2f = ms => Math.max(1, Math.round(+ms / (1000 / 60)));
async function runScript(scr){
for (const step of (scr || '').split(/\s+/).filter(Boolean)) {
  const [cmd, a1, a2] = step.split(':');
  const ks = a1 ? a1.split('+') : [];
  if (cmd === 'hold') { await setKeys(ks, true); await run(ms2f(a2)); await setKeys(ks, false); }
  else if (cmd === 'down') await setKeys(ks, true);
  else if (cmd === 'up') await setKeys(ks, false);
  else if (cmd === 'tap') { await setKeys(ks, true); await run(4); await setKeys(ks, false); }
  else if (cmd === 'wait') await run(ms2f(a1));
  else if (cmd === 'step') await run(+a1);
  else if (cmd === 'shot') { await page.evaluate(() => window.__stepN(1, true)); await snap(path.join('shots', a1 + '.png')); }
  else if (cmd === 'eval') await page.evaluate(step.slice(5));
  else if (cmd === 'key') { await page.keyboard.down(a1); await run(3); await page.keyboard.up(a1); }
  else if (cmd === 'mark') console.log('mark', a1, JSON.stringify(await page.evaluate(() => window.__sheep.stats())));
}
}
await runScript(o.script);
if (o.until) {
  let t = 0; const lim = ms2f(o.max);
  while (t < lim) { await run(30); t += 30; if (await page.evaluate(o.until)) break; }
  console.log('until done after', Math.round(t / 60 * 10) / 10, 's game time');
}
if (o.script2) { await page.evaluate(() => { window.__bot = null; }); await runScript(o.script2); }
if (o.clip) {
  fs.mkdirSync(path.dirname(o.clip), { recursive: true });
  execFileSync('ffmpeg', ['-y', '-loglevel', 'error', '-framerate', String(Math.round(60 / +o.every)), '-i', path.join(frameDir, 'f%05d.png'),
    '-pix_fmt', 'yuv420p', '-vf', 'pad=ceil(iw/2)*2:ceil(ih/2)*2', o.clip]);
  fs.rmSync(frameDir, { recursive: true, force: true });
  console.log('clip', o.clip, fno, 'frames');
}
if (o.trace) { const tr = await page.evaluate(() => window.__trace); fs.mkdirSync(path.dirname(o.trace), { recursive: true }); fs.writeFileSync(o.trace, JSON.stringify(tr)); console.log('trace', o.trace, tr.length); }
if (o.print) console.log('print', JSON.stringify(await page.evaluate(o.print)));
const stats = await page.evaluate(() => window.__sheep.stats()).catch(() => null);
console.log('stats', JSON.stringify(stats));
await browser.close(); server.close();
process.exit(errors.length ? 3 : 0);
