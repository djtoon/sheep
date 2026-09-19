// cohesion pass: real-time probe. Loads the game, runs a keyboard script (same syntax as tools/shot.mjs) and every
// --every ms prints the value of --poll (a JS expression). Also counts console warnings/errors and page errors.
//   node art/raw/cohesion/probe.mjs --query "god=1&x=5000" --script "hold:ArrowRight:1500 wait:9000" --poll "expr" --every 1000
import { chromium } from 'playwright';
import { serve } from '../../../tools/serve.mjs';

const args = process.argv.slice(2); const o = { query: 'test=1', every: 1000, poll: 'JSON.stringify(window.__sheep.stats())', scale: 2 };
for (let i = 0; i < args.length; i++) o[args[i].replace(/^--/, '')] = args[++i];
const port = 9000 + Math.floor(Math.random() * 900);
const server = await serve(port);
const browser = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--autoplay-policy=no-user-gesture-required', '--enable-unsafe-swiftshader'] });
const page = await browser.newPage({ viewport: { width: 480 * +o.scale, height: 270 * +o.scale } });
let warns = 0, errs = 0;
page.on('console', m => { if (m.type() === 'error' || m.type() === 'warning') { (m.type() === 'error' ? errs++ : warns++); console.log('[console.' + m.type() + ']', m.text()); } });
page.on('pageerror', e => { errs++; console.log('[pageerror]', e.message); });
await page.goto(`http://localhost:${port}/index.html?${o.query}`);
await page.waitForFunction(() => window.__sheep && window.__sheep.ready, null, { timeout: 30000 });
if (o.eval) await page.evaluate(o.eval);
let polling = true;
const t0 = Date.now();
const poller = (async () => { while (polling) { try { console.log(((Date.now() - t0) / 1000).toFixed(1) + 's', await page.evaluate(o.poll)); } catch (e) { console.log('poll error', e.message); } await page.waitForTimeout(+o.every); } })();
const keysOf = s => s.split('+');
for (const step of (o.script || '').split(/\s+/).filter(Boolean)) {
  const [cmd, a1, a2] = step.split(':');
  if (cmd === 'hold') { for (const k of keysOf(a1)) await page.keyboard.down(k); await page.waitForTimeout(+a2); for (const k of keysOf(a1)) await page.keyboard.up(k); }
  else if (cmd === 'down') for (const k of keysOf(a1)) await page.keyboard.down(k);
  else if (cmd === 'up') for (const k of keysOf(a1)) await page.keyboard.up(k);
  else if (cmd === 'tap') { for (const k of keysOf(a1)) await page.keyboard.down(k); await page.waitForTimeout(70); for (const k of keysOf(a1)) await page.keyboard.up(k); }
  else if (cmd === 'wait') await page.waitForTimeout(+a1);
  else if (cmd === 'eval') await page.evaluate(step.slice(5));
}
polling = false; await poller;
console.log('warnings', warns, 'errors', errs);
await browser.close(); server.close();
