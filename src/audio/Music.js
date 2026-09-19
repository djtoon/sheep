// Music + mix bus. Tracks are pre-rendered OGGs (art/raw/audio/synth.py) with sample-accurate loop points
// (audioData.js): an intro plays once, then [loopStart, loopEnd] loops gaplessly via a raw WebAudio BufferSource.
//
//   Music.play(scene, 'title' | 'stage1' | 'boss')   start a track (no-op if it is already playing)
//   Music.stop(fadeMs = 300)                         fade out and stop the current track
//   Music.sting('clear' | 'gameover' | 'warning', { then: 'boss' })
//                                                    stop the music, play a one-shot jingle, optionally start a track after it
//   Music.duck(on, level = 0.22)                     pause-style duck of the music bus
//   Music.setVolume(v)                               music bus level (default 0.6); Sfx has its own bus
//
// Browsers keep the AudioContext suspended until a user gesture; anything requested before that is held and
// starts the moment the context resumes (Phaser unlocks on the first key/pointer press).
import { LOOPS } from './audioData.js';

export const MUSIC_VOL = 0.6, SFX_VOL = 1.0;
const BUSES = new WeakMap();

// One shared chain per AudioContext: music + sfx gains -> gentle safety compressor -> Phaser's master (volume/mute).
export function audioBus(scene) {
  const snd = scene && scene.sound, ctx = snd && snd.context;
  if (!ctx || !ctx.createGain) return null;
  let b = BUSES.get(ctx);
  if (!b) {
    const comp = ctx.createDynamicsCompressor(); // only engages when many sfx stack (explosion chains)
    comp.threshold.value = -6; comp.knee.value = 4; comp.ratio.value = 16; comp.attack.value = 0.001; comp.release.value = 0.12;
    const clip = ctx.createWaveShaper(); // transparent below -2 dBFS, then a soft knee that never exceeds 0.98
    const N = 2048, curve = new Float32Array(N);
    for (let i = 0; i < N; i++) { const x = i / (N - 1) * 2 - 1, a = Math.abs(x); curve[i] = a < 0.8 ? x : Math.sign(x) * (0.8 + 0.18 * Math.tanh((a - 0.8) / 0.18)); }
    clip.curve = curve; clip.oversample = '2x';
    comp.connect(clip); clip.connect(snd.destination || ctx.destination);
    const music = ctx.createGain(); music.gain.value = MUSIC_VOL; music.connect(comp);
    const sfx = ctx.createGain(); sfx.gain.value = SFX_VOL; sfx.connect(comp);
    b = { ctx, comp, clip, music, sfx, waiters: [] };
    const flush = () => { if (ctx.state === 'running') { const w = b.waiters.splice(0); w.forEach(f => f()); } };
    ctx.addEventListener ? ctx.addEventListener('statechange', flush) : (ctx.onstatechange = flush);
    snd.on && snd.on('unlocked', flush);
    BUSES.set(ctx, b);
  }
  return b;
}
// run fn now if audio is live, else as soon as the context is unlocked (only the latest request per slot survives)
function whenRunning(b, slot, fn) {
  if (b.ctx.state === 'running') return fn();
  b.pending = b.pending || {};
  b.pending[slot] = fn;
  b.waiters.push(() => { if (b.pending[slot] === fn) { b.pending[slot] = null; fn(); } });
}

export const Music = {
  scene: null, cur: null, token: 0, lastSting: { name: '', t: 0 },

  play(scene, name, opts = {}) {
    if (typeof scene === 'string') { opts = name || {}; name = scene; scene = this.scene; }
    if (!scene) return;
    this.scene = scene;
    const key = 'music-' + name;
    if (!opts.restart && this.cur && this.cur.key === key) return;
    this.stop(opts.fadeOut ?? 250);
    const tok = ++this.token;
    this.cur = { key, name, src: null, gain: null };
    const b = audioBus(scene);
    if (!b) { // HTML5-audio fallback: plain loop, no intro handling
      if (scene.cache.audio.exists(key)) this.cur.sound = scene.sound.add(key, { loop: true, volume: MUSIC_VOL }), this.cur.sound.play();
      return;
    }
    whenRunning(b, 'music', () => { if (tok === this.token) this._start(b, scene, key, true, opts.fadeIn || 0); });
  },

  _start(b, scene, key, loop, fadeIn, onEnd) {
    const buf = scene.cache.audio.get(key);
    if (!buf || !buf.getChannelData) return null;
    const ctx = b.ctx, src = ctx.createBufferSource(), g = ctx.createGain(), t = ctx.currentTime + 0.01;
    src.buffer = buf;
    if (loop) {
      const L = LOOPS[key] || { loopStart: 0, loopEnd: buf.duration };
      src.loop = true; src.loopStart = Math.min(L.loopStart, buf.duration - 0.05); src.loopEnd = Math.min(L.loopEnd, buf.duration);
    }
    g.gain.setValueAtTime(fadeIn ? 0.0001 : 1, t);
    if (fadeIn) g.gain.exponentialRampToValueAtTime(1, t + fadeIn / 1000);
    src.connect(g).connect(b.music);
    if (onEnd) src.onended = onEnd;
    src.start(t);
    if (this.cur && this.cur.key === key) { this.cur.src = src; this.cur.gain = g; }
    return { src, g };
  },

  stop(fadeMs = 300) {
    const c = this.cur; this.cur = null; this.token++;
    if (!c) return;
    if (c.sound) { c.sound.stop(); c.sound.destroy(); return; }
    if (c.src) fadeKill(c.src, c.gain, fadeMs);
  },

  // one-shot jingle on the music bus; kills the current track. opts.then = track name to start when it ends.
  sting(scene, name, opts = {}) {
    if (typeof scene === 'string') { opts = name || {}; name = scene; scene = this.scene; }
    if (!scene) return;
    this.scene = scene;
    const now = performance.now();
    if (this.lastSting.name === name && now - this.lastSting.t < 800) return; // same sting requested twice (auto-wire + manual hook)
    this.lastSting = { name, t: now };
    this.stop(name === 'warning' ? 120 : 200);
    const key = 'sting-' + name, b = audioBus(scene), tok = this.token;
    if (!b) { if (scene.cache.audio.exists(key)) scene.sound.play(key, { volume: MUSIC_VOL }); if (opts.then) this.play(scene, opts.then); return; }
    whenRunning(b, 'music', () => {
      if (tok !== this.token) return;
      const s = this._start(b, scene, key, false, 0, () => { if (tok === this.token && opts.then) this.play(scene, opts.then, { fadeIn: 0 }); });
      if (s) this.cur = { key, name, src: s.src, gain: s.g, sting: true };
      else if (opts.then) this.play(scene, opts.then);
    });
  },

  // pause / 1-UP ducking of the music bus (smooth, no zipper noise)
  duck(on, level = 0.22, ms = 120, scene = this.scene) {
    const b = audioBus(scene); if (!b) return;
    const g = b.music.gain, t = b.ctx.currentTime, v = on ? MUSIC_VOL * level : (this.vol ?? MUSIC_VOL);
    g.cancelScheduledValues(t); g.setValueAtTime(g.value, t); g.setTargetAtTime(v, t, ms / 3000);
    this.ducked = !!on;
  },

  setVolume(v, scene = this.scene) { this.vol = v; const b = audioBus(scene); if (b) b.music.gain.value = v; },
};

export function fadeKill(src, gain, ms) {
  try {
    const t = src.context.currentTime, g = gain.gain;
    g.cancelScheduledValues(t); g.setValueAtTime(Math.max(g.value, 0.0001), t);
    g.exponentialRampToValueAtTime(0.0001, t + Math.max(ms, 5) / 1000);
    src.onended = null; src.stop(t + Math.max(ms, 5) / 1000 + 0.02);
  } catch (e) { /* already stopped */ }
}

if (typeof window !== 'undefined') { window.__sheepAudio = { Music, audioBus }; }
