// Screenshot / play the REAL running game in headless Chromium.
// usage:
//   node tools/shot.mjs --out shots/x.png [--query "stage=1&x=600"] [--wait 1500]
//        [--script "hold:ArrowRight:1200 tap:KeyZ hold:ArrowRight+KeyX:800 wait:300 shot:name"]
//        [--clip shots/run.mp4]   (records frames during the script, encoded with ffmpeg)
//        [--scale 3]  (viewport = 480x270 * N; default 3)
//        [--eval "js to run once the game is ready"]
// Keys: arrows move/aim, Z = jump, X = fire, Enter = start/pause.
// Script steps: hold:KEYS:ms  down:KEYS  up:KEYS  tap:KEYS  wait:ms  shot:name (-> shots/<name>.png)
//   KEYS may be combined with '+', e.g. hold:ArrowRight+KeyX:1000
// Prints console errors / page errors; exit code 3 if the page threw.
import { chromium } from 'playwright';
import { serve } from './serve.mjs';
import fs from 'node:fs'; import path from 'node:path'; import { execFileSync } from 'node:child_process';

const args = process.argv.slice(2); const o = { wait: 1500, scale: 3, query: '' };
for (let i = 0; i < args.length; i++) o[args[i].replace(/^--/, '')] = args[++i];
const port = 9000 + Math.floor(Math.random() * 900);
const server = await serve(port);
const browser = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--autoplay-policy=no-user-gesture-required', '--enable-unsafe-swiftshader'] });
const page = await browser.newPage({ viewport: { width: 480 * +o.scale, height: 270 * +o.scale } });
const errors = [];
page.on('console', m => { if (m.type() === 'error' || m.type() === 'warning') console.log('[console.' + m.type() + ']', m.text()); });
page.on('pageerror', e => { errors.push(e.message); console.log('[pageerror]', e.message); });
await page.goto(`http://localhost:${port}/index.html?test=1&${o.query}`);
await page.waitForFunction(() => window.__sheep && window.__sheep.ready, null, { timeout: 30000 }).catch(() => console.log('WARN: window.__sheep.ready never became true'));
if (o.eval) await page.evaluate(o.eval);
await page.waitForTimeout(+o.wait);

const canvas = await page.$('canvas');
async function snap(file) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  await canvas.screenshot({ path: file });
  console.log('saved', file);
}
let frameDir = null, frameN = 0, recording = false, recLoop = null;
if (o.clip) {
  frameDir = path.join('shots', '.frames_' + port); fs.mkdirSync(frameDir, { recursive: true });
  recording = true;
  recLoop = (async () => { const t0 = Date.now(); while (recording) { await canvas.screenshot({ path: path.join(frameDir, `f${String(frameN++).padStart(5, '0')}.png`) }); } return Date.now() - t0; })();
}
const keysOf = s => s.split('+');
for (const step of (o.script || '').split(/\s+/).filter(Boolean)) {
  const [cmd, a1, a2] = step.split(':');
  if (cmd === 'hold') { for (const k of keysOf(a1)) await page.keyboard.down(k); await page.waitForTimeout(+a2); for (const k of keysOf(a1)) await page.keyboard.up(k); }
  else if (cmd === 'down') for (const k of keysOf(a1)) await page.keyboard.down(k);
  else if (cmd === 'up') for (const k of keysOf(a1)) await page.keyboard.up(k);
  else if (cmd === 'tap') { for (const k of keysOf(a1)) await page.keyboard.down(k); await page.waitForTimeout(70); for (const k of keysOf(a1)) await page.keyboard.up(k); }
  else if (cmd === 'wait') await page.waitForTimeout(+a1);
  else if (cmd === 'shot') await snap(path.join('shots', a1 + '.png'));
  else if (cmd === 'eval') await page.evaluate(step.slice(5));
}
if (o.clip) {
  recording = false; const ms = await recLoop;
  const fps = Math.max(5, Math.round(frameN / (ms / 1000)));
  fs.mkdirSync(path.dirname(o.clip), { recursive: true });
  execFileSync('ffmpeg', ['-y', '-loglevel', 'error', '-framerate', String(fps), '-i', path.join(frameDir, 'f%05d.png'),
    '-pix_fmt', 'yuv420p', '-vf', 'pad=ceil(iw/2)*2:ceil(ih/2)*2', o.clip]);
  fs.rmSync(frameDir, { recursive: true, force: true });
  console.log('clip', o.clip, frameN, 'frames @', fps, 'fps (real-time capture)');
}
if (o.out) await snap(o.out);
const stats = await page.evaluate(() => window.__sheep && window.__sheep.stats ? window.__sheep.stats() : null).catch(() => null);
if (stats) console.log('stats', JSON.stringify(stats));
await browser.close(); server.close();
process.exit(errors.length ? 3 : 0);
