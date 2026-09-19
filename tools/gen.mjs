// Generate an image with openai/gpt-image-2.5-flare on Replicate (see image.md).
// usage: node tools/gen.mjs --out art/raw/x.png --prompt "..." [--ref ref/a.png --ref art/b.png]
//        [--aspect 1:1|16:9|3:2|...|WxH] [--quality low|medium|high|xhigh] [--bg transparent|opaque|auto] [--n 1]
// With --n > 1 files are written as x_1.png, x_2.png ...
import fs from 'node:fs';
import path from 'node:path';

const args = process.argv.slice(2);
const opt = { ref: [], aspect: '1:1', quality: 'high', bg: 'auto', n: 1 };
for (let i = 0; i < args.length; i++) {
  const k = args[i].replace(/^--/, ''), v = args[++i];
  if (k === 'ref') opt.ref.push(v); else opt[k] = v;
}
if (!opt.out || !opt.prompt) { console.error('need --out and --prompt'); process.exit(1); }
if (opt.promptFile) opt.prompt = fs.readFileSync(opt.promptFile, 'utf8');
const TOKEN = process.env.REPLICATE_API_TOKEN;
const H = { Authorization: `Bearer ${TOKEN}` };

async function upload(file) {
  const fd = new FormData();
  const mime = file.endsWith('.png') ? 'image/png' : file.endsWith('.webp') ? 'image/webp' : 'image/jpeg';
  fd.append('content', new Blob([fs.readFileSync(file)], { type: mime }), path.basename(file));
  const r = await fetch('https://api.replicate.com/v1/files', { method: 'POST', headers: H, body: fd });
  if (!r.ok) throw new Error('upload ' + r.status + ' ' + await r.text());
  return (await r.json()).urls.get;
}

const input = { prompt: opt.prompt, aspect_ratio: opt.aspect, quality: opt.quality, output_format: 'png',
  background: opt.bg, number_of_images: +opt.n, moderation: 'low' };
if (opt.ref.length) input.input_images = await Promise.all(opt.ref.map(upload));

let r = await fetch('https://api.replicate.com/v1/models/openai/gpt-image-2.5-flare/predictions', {
  method: 'POST', headers: { ...H, 'Content-Type': 'application/json', Prefer: 'wait=60' }, body: JSON.stringify({ input }) });
let p = await r.json();
while (p.status && !['succeeded', 'failed', 'canceled'].includes(p.status)) {
  await new Promise(s => setTimeout(s, 2000));
  p = await (await fetch(p.urls.get, { headers: H })).json();
}
if (p.status !== 'succeeded') { console.error('FAILED', JSON.stringify(p.error || p)); process.exit(2); }
const outs = Array.isArray(p.output) ? p.output : [p.output];
fs.mkdirSync(path.dirname(opt.out), { recursive: true });
for (let i = 0; i < outs.length; i++) {
  const buf = Buffer.from(await (await fetch(outs[i], { headers: H })).arrayBuffer());
  const f = outs.length > 1 ? opt.out.replace(/(\.\w+)$/, `_${i + 1}$1`) : opt.out;
  fs.writeFileSync(f, buf); console.log(f);
}
