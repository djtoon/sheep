// Arcade SFX player. Sounds are pre-rendered OGGs ('sfx-<name>' in assets/parts/audio.json, made by art/raw/audio/synth.py),
// played through a shared WebAudio bus with a per-sound voice cap, small pitch variation on rapid-fire sounds,
// and a safety compressor so stacked explosions never clip.
//
//   const sfx = new Sfx(scene);  sfx.play(name, vol = 1)
//   names: shoot (auto-switches to shoot-m while the player holds the M gun), shoot-m, spread, laser, enemy-shot, hit,
//          enemy-die, boom, boom-big, jump, land, pickup, die, capsule, select, start, pause, telegraph, count, extralife, powerup
//
// In the Game scene the constructor also wires the soundtrack to events Game already emits
// (stage music on create, 'boss' -> WARNING then boss theme, 'cleared' -> stage-clear jingle, 'gameover' -> game-over jingle)
// plus pause (duck + chime), telegraph ticks, countdown ticks, 1-UP, weapon-get, continue re-arm sting and 'player-land'.
// Where Game also plays a generic sound for the same moment (select on pause, pickup on 1-UP/powerup, start on continue)
// the richer sound replaces it. Set Sfx.AUTO_WIRE = false to hook these up by hand.
import { Music, audioBus, fadeKill } from './Music.js';

const VOICES = { shoot: 3, 'shoot-m': 3, spread: 3, laser: 2, 'enemy-shot': 4, hit: 3, 'enemy-die': 4, boom: 4, 'boom-big': 3,
  jump: 1, land: 1, pickup: 1, die: 1, capsule: 2, select: 1, start: 1,
  pause: 1, telegraph: 2, count: 1, extralife: 1, powerup: 1 };
const JITTER = { shoot: 0.03, 'shoot-m': 0.05, spread: 0.02, 'enemy-shot': 0.04, hit: 0.06, 'enemy-die': 0.06, boom: 0.05, capsule: 0.03, land: 0.05, telegraph: 0.04 };
const MIN_GAP = { hit: 40, 'enemy-shot': 45, boom: 50, telegraph: 110, land: 80 }; // ms; everything else 30

export class Sfx {
  constructor(scene) {
    this.scene = scene;
    this.bus = audioBus(scene);
    this.last = {};
    this.active = {};
    if (Sfx.AUTO_WIRE && scene.sys.settings.key === 'Game') this.wireGame(scene);
  }

  play(name, vol = 1) {
    if (name === 'shoot' && this.scene.player && this.scene.player.weapon === 'M') name = 'shoot-m';
    const now = performance.now();
    if (this.last[name] && now - this.last[name] < (MIN_GAP[name] || 30)) return; // de-dupe same-frame spam (and shadow())
    this.last[name] = now;
    const key = 'sfx-' + name, sc = this.scene;
    if (!sc.cache.audio.exists(key)) return;
    const b = this.bus;
    if (!b) { sc.sound.play(key, { volume: vol }); return; } // HTML5 audio fallback
    if (b.ctx.state !== 'running') return; // locked: drop, never queue stale sfx
    const buf = sc.cache.audio.get(key); if (!buf || !buf.getChannelData) return;
    const list = this.active[name] || (this.active[name] = []);
    while (list.length >= (VOICES[name] || 4)) { const o = list.shift(); fadeKill(o.src, o.g, 12); }
    const ctx = b.ctx, src = ctx.createBufferSource(), g = ctx.createGain();
    src.buffer = buf;
    const j = JITTER[name]; if (j) src.playbackRate.value = 1 + (Math.random() * 2 - 1) * j;
    g.gain.value = vol;
    src.connect(g).connect(b.sfx);
    const v = { src, g }; list.push(v);
    src.onended = () => { const i = list.indexOf(v); if (i >= 0) list.splice(i, 1); g.disconnect(); };
    src.start();
  }

  wireGame(scene) {
    const ev = scene.events, on = [];
    const hook = (name, fn) => { ev.on(name, fn); on.push([name, fn]); };
    const stageTrack = () => (scene.boss && !scene.cleared ? 'boss' : 'stage' + (scene.stageNo || 1));
    Music.play(scene, stageTrack());
    hook('boss', () => Music.sting(scene, 'warning', { then: 'boss' }));
    hook('cleared', () => Music.sting(scene, 'clear'));            // also covers 'stage-end' (it fires ~7 s later, after the jingle)
    hook('gameover', () => Music.sting(scene, 'gameover'));
    hook('continue-tick', n => this.play('count', n <= 3 ? 1 : 0.75));
    hook('continued', () => { this.shadow('start'); Music.duck(false); Music.sting(scene, 'continue', { then: stageTrack() }); });
    hook('pause', paused => { this.shadow('select'); Music.duck(!!paused); this.play('pause'); });
    hook('telegraph', () => this.play('telegraph', 0.8));        // MIN_GAP rate-limits bursts of wind-ups
    hook('extralife', () => { this.shadow('pickup'); Music.duck(true, 0.35, 60); scene.time.delayedCall(1000, () => !scene.paused && Music.duck(false)); this.play('extralife'); });
    hook('powerup', () => { this.cut('pickup'); this.play('powerup'); });
    hook('player-land', () => this.play('land', 0.8));
    ev.once('shutdown', () => {
      on.forEach(([n, f]) => ev.off(n, f));
      Music.duck(false);
      if (Music.cur && !Music.cur.sting) Music.stop(400);
    });
  }

  // drop the next generic `name` requested in the next ~2 frames (the event handler already played a richer sound)
  shadow(name, ms = 40) { this.last[name] = performance.now() + ms; }
  // stop voices of `name` that started within the last ~2 frames (generic sound played just before the event)
  cut(name) { const l = this.active[name] || []; while (l.length) { const o = l.pop(); fadeKill(o.src, o.g, 6); } }
}
Sfx.AUTO_WIRE = true;
