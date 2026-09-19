// Records the real in-game audio output (music + sfx through the bus) while playing, -> art/raw/audio/wav/ingame.webm
import { chromium } from 'playwright';
import { serve } from '../../../tools/serve.mjs';
import fs from 'node:fs';
const port = 9000 + Math.floor(Math.random() * 900); await serve(port);
const browser = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--autoplay-policy=no-user-gesture-required', '--enable-unsafe-swiftshader'] });
const page = await browser.newPage({ viewport: { width: 480, height: 270 } });
page.on('pageerror', e => console.log('[pageerror]', e.message));
await page.goto(`http://localhost:${port}/index.html?test=1&god=1&x=${process.argv[2] || 60}`);
await page.waitForFunction(() => window.__sheep.game.scene.getScene('Game')?.sfx, null, { timeout: 30000 });
await page.evaluate(() => {
  const g = window.__sheep.game.scene.getScene('Game'), b = window.__sheepAudio.audioBus(g);
  const dst = b.ctx.createMediaStreamDestination(); b.clip.connect(dst);
  const rec = new MediaRecorder(dst.stream, { mimeType: 'audio/webm;codecs=opus', audioBitsPerSecond: 256000 }); const chunks = [];
  rec.ondataavailable = e => chunks.push(e.data); rec.start();
  window.__rec = { rec, chunks };
});
const k = page.keyboard;
await k.down('ArrowRight'); await k.down('KeyX');
for (let i = 0; i < 8; i++) { await page.waitForTimeout(700); await k.press('KeyZ'); }
await k.up('KeyX'); await page.evaluate(() => window.__sheep.game.scene.getScene('Game').player.setWeapon('S')); await k.down('KeyX');
await page.waitForTimeout(2500); await k.up('KeyX'); await k.up('ArrowRight');
const b64 = await page.evaluate(() => new Promise(res => { const r = window.__rec; r.rec.onstop = async () => {
  const buf = await new Blob(r.chunks).arrayBuffer(); let s = ''; const u = new Uint8Array(buf); for (let i = 0; i < u.length; i++) s += String.fromCharCode(u[i]); res(btoa(s)); }; r.rec.stop(); }));
fs.writeFileSync('art/raw/audio/wav/ingame.webm', Buffer.from(b64, 'base64')); console.log('saved');
await browser.close(); process.exit(0);
