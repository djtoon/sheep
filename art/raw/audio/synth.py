"""Armed and Fluffy - offline chiptune renderer.
Renders all music + SFX into assets/audio/*.ogg (+ WAV masters in art/raw/audio/wav/),
writes assets/parts/audio.json and src/audio/audioData.js (loop points + keys).
NES-style voices (pulse w/ duty, 4-bit triangle, LFSR noise) rendered at 4x and decimated (no aliasing grit),
then mixed in stereo with a ping-pong echo on the lead, loudness-normalised and peak-limited.
usage: python art/raw/audio/synth.py [--only music|sfx]"""
import numpy as np, json, os, sys, subprocess
from scipy.signal import resample_poly, butter, sosfilt
from scipy.ndimage import maximum_filter1d, minimum_filter1d, uniform_filter1d
import soundfile as sf
import pyloudnorm as pyln

SR = 44100; OS = 4; FS = SR * OS
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
OUT = os.path.join(ROOT, 'assets', 'audio'); WAV = os.path.join(ROOT, 'art', 'raw', 'audio', 'wav')
os.makedirs(OUT, exist_ok=True); os.makedirs(WAV, exist_ok=True)
rng = np.random.default_rng(7)

# ------------------------------------------------------------------ pitch helpers
NOTE = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}
NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
def midi(n):
    i, acc = 1, 0
    while n[i] in '#b': acc += 1 if n[i] == '#' else -1; i += 1
    return 12 * (int(n[i:]) + 1) + NOTE[n[0]] + acc
def name(m): return NAMES[m % 12] + str(m // 12 - 1)
def hz(m): return 440.0 * 2 ** ((m - 69) / 12)
def tr(bar, k):  # transpose a bar string
    return ' '.join(t if t in '.-' else name(midi(t) + k) for t in bar.split())

# ------------------------------------------------------------------ raw NES-ish oscillators (at FS)
def phase(f):
    ph = np.cumsum(np.asarray(f, np.float64)) / FS
    return ph - np.floor(ph)
def pulse(f, duty):
    fr = phase(f); return 2.0 * ((fr < duty).astype(np.float64) - duty)
TRI = np.concatenate([np.arange(15, -1, -1), np.arange(0, 16)]) / 7.5 - 1.0
def tri(f):  # NES 32-step, 4-bit triangle
    return TRI[(phase(f) * 32).astype(int) % 32]
def sine(f): return np.sin(2 * np.pi * phase(f))
def _lfsr(short):
    reg, out, n, tap = 1, [], (93 if short else 32767), (6 if short else 1)
    for _ in range(n):
        b = (reg ^ (reg >> tap)) & 1; reg = (reg >> 1) | (b << 14); out.append(reg & 1)
    return np.array(out, np.float64) * 2 - 1
LFSR_L, LFSR_S = _lfsr(False), _lfsr(True)
def noise(rate, n, short=False):  # NES noise clocked at `rate` Hz (scalar or array)
    seq = LFSR_S if short else LFSR_L
    r = np.broadcast_to(np.asarray(rate, np.float64), (n,))
    idx = (np.cumsum(r) / FS).astype(np.int64)
    return seq[idx % len(seq)]
def T(n): return np.arange(n) / FS
def env(n_gate, a=0.002, d=0.1, s=0.7, r=0.03, curve=1.0):
    nr = int(r * FS); N = n_gate + nr; t = T(N)
    e = np.where(t < a, t / max(a, 1e-9), s + (1 - s) * np.exp(-(t - a) / max(d, 1e-9)))
    if nr > 0:
        g = n_gate / FS; lvl = e[min(n_gate, N - 1)]
        e = np.where(t >= g, lvl * np.clip(1 - (t - g) / r, 0, 1) ** curve, e)
    return e
def dec(x): return resample_poly(x, 1, OS).astype(np.float32)
def sos(kind, fc, order=2, sr=SR):
    return butter(order, fc, btype=kind, fs=sr, output='sos')
def filt(x, kind, fc, order=2, sr=SR): return sosfilt(sos(kind, fc, order, sr), x)

# ------------------------------------------------------------------ instruments  (f0 Hz, dur s, vel) -> FS array
def vib(t, f0, delay=0.16, rate=5.6, depth=0.18, ramp=0.18):
    k = np.clip((t - delay) / ramp, 0, 1)
    return f0 * 2 ** (depth / 12 * np.sin(2 * np.pi * rate * np.maximum(t - delay, 0)) * k)
def i_lead(f0, dur, v):  # brassy 25% pulse, 12.5% bite, delayed vibrato, faint chorus voice
    e = env(int(dur * FS * 0.94), 0.0015, 0.16, 0.72, 0.035); t = T(len(e))
    f = vib(t, f0); d = np.where(t < 0.028, 0.125, 0.25)
    w = pulse(f, d) + 0.28 * pulse(f * 1.0035, 0.5)
    return w * e * v
def i_flute(f0, dur, v):  # B-section: rounder 50% pulse, deeper vibrato
    e = env(int(dur * FS * 0.95), 0.004, 0.25, 0.8, 0.05); t = T(len(e))
    f = vib(t, f0, 0.12, 5.2, 0.28); d = np.where(t < 0.02, 0.25, 0.5)
    return (pulse(f, d) * 0.85 + 0.25 * pulse(f * 2.002, 0.125)) * e * v
def i_riff(f0, dur, v):  # staccato 12.5%/25% chug
    e = env(int(dur * FS * 0.8), 0.001, 0.07, 0.45, 0.012); t = T(len(e))
    return pulse(np.full(len(e), f0), np.where(t < 0.02, 0.125, 0.25)) * e * v
def i_stab(f0, dur, v):  # pulse-2 chord stabs / arps (12.5% duty, plucky)
    e = env(int(dur * FS * 0.75), 0.001, 0.06, 0.25, 0.015)
    return pulse(np.full(len(e), f0), 0.125) * e * v
def i_pad(f0, dur, v):  # harmony line under fanfares
    e = env(int(dur * FS * 0.95), 0.003, 0.3, 0.6, 0.05); t = T(len(e))
    return pulse(vib(t, f0, 0.2, 5.6, 0.12), 0.25) * e * v
def i_bass(f0, dur, v):  # NES triangle + a sine sub for weight
    e = env(int(dur * FS * 0.86), 0.002, 1.0, 1.0, 0.008); f = np.full(len(e), f0)
    return (tri(f) * 0.8 + 0.45 * sine(f)) * e * v
def i_bass_long(f0, dur, v):
    e = env(int(dur * FS * 0.97), 0.003, 0.6, 0.75, 0.05); f = np.full(len(e), f0)
    return (tri(f) * 0.8 + 0.45 * sine(f)) * e * v
# drums
def d_kick(v=1.0):
    n = int(0.26 * FS); t = T(n)
    f = 46 + 170 * np.exp(-t / 0.022)
    body = (0.55 * tri(f) + 0.8 * sine(f)) * np.exp(-t / 0.11)
    click = noise(180000, n) * np.exp(-t / 0.004) * 0.35
    return (body + click) * np.minimum(1, t / 0.0008) * v
def d_snare(v=1.0):
    n = int(0.24 * FS); t = T(n)
    nz = noise(np.full(n, 56000), n) * np.exp(-t / 0.075)
    body = tri(185 * np.exp(-t / 0.08) + 90) * np.exp(-t / 0.045) * 0.9
    return (0.8 * nz + body) * np.minimum(1, t / 0.0006) * v
def d_hat(v=1.0, open_=False):
    n = int((0.16 if open_ else 0.05) * FS); t = T(n)
    return noise(np.full(n, 400000), n) * np.exp(-t / (0.06 if open_ else 0.014)) * v
def d_crash(v=1.0):
    n = int(1.4 * FS); t = T(n)
    return (noise(np.full(n, 400000), n) * 0.8 + 0.25 * noise(np.full(n, 90000), n, True)) * np.exp(-t / 0.45) * np.minimum(1, t / 0.001) * v
def d_tom(v=1.0, f0=190):
    n = int(0.25 * FS); t = T(n)
    f = f0 * (0.6 + 0.4 * np.exp(-t / 0.05))
    return (tri(f) * 0.8 + 0.3 * noise(30000, n) * np.exp(-t / 0.02)) * np.exp(-t / 0.12) * v
DRUMS = {'K': ('kick', lambda: d_kick()), 'S': ('snare', lambda: d_snare()), 's': ('snare', lambda: d_snare(0.45)),
         'h': ('hat', lambda: d_hat(0.5)), 'o': ('hat', lambda: d_hat(0.55, True)), 'C': ('crash', lambda: d_crash()),
         'T': ('tom', lambda: d_tom(1, 220)), 't': ('tom', lambda: d_tom(1, 150))}
_drum_cache = {}
def drum(ch):
    if ch not in _drum_cache: _drum_cache[ch] = dec(DRUMS[ch][1]())
    return _drum_cache[ch]

# ------------------------------------------------------------------ chords & generators
CH = {'Am': (9, [0, 3, 7]), 'A': (9, [0, 4, 7]), 'F': (5, [0, 4, 7]), 'G': (7, [0, 4, 7]), 'E': (4, [0, 4, 7]), 'E7': (4, [0, 4, 7, 10]),
      'C': (0, [0, 4, 7]), 'Dm': (2, [0, 3, 7]), 'D': (2, [0, 4, 7]), 'Em': (4, [0, 3, 7]), 'Bb': (10, [0, 4, 7]), 'B': (11, [0, 4, 7]),
      'Gm': (7, [0, 3, 7]), 'Eb': (3, [0, 4, 7])}
def chord_at(chords, step):
    parts = chords[step // 16].split(); return parts[(step % 16) * len(parts) // 16]
def bass_line(chords, pats):
    """pats: one 16-token pattern per bar (or one for all). tokens: R root, O octave, 5 fifth, 1 root+1 (chromatic), - hold, . rest"""
    ev, cur = [], None
    for b in range(len(chords)):
        p = (pats[b] if isinstance(pats, list) else pats).split(); assert len(p) == 16, p
        for i, tk in enumerate(p):
            s = b * 16 + i; pc = CH[chord_at(chords, s)][0]; R = 33 + (pc - 9) % 12
            if tk == '-':
                if cur: cur[1] += 1
            elif tk == '.': cur = None
            else:
                m = {'R': R, 'O': R + 12, '5': R + 7, '1': R + 1, '8': R + 19}[tk]
                cur = [s, 1, m, 1.0]; ev.append(cur)
    return ev
def arp(chords, bars, idx=(0, 1, 2, 3), base=64, every=1, vel=1.0):
    ev = []
    for b in bars:
        for i in range(0, 16, every):
            s = b * 16 + i; pc, iv = CH[chord_at(chords, s)]
            r = base + (pc - base) % 12
            tones = [r + x for x in iv] + [r + 12]
            ev.append([s, every, tones[idx[(i // every) % len(idx)] % len(tones)], vel])
    return ev
def stabs(chords, bars, steps=(2, 6, 10, 14), ivs=(1, 2), base=62, vel=1.0):
    ev = []
    for b in bars:
        for i in steps:
            s = b * 16 + i; pc, iv = CH[chord_at(chords, s)]
            r = base + (pc - base) % 12
            for k in ivs: ev.append([s, 1, r + iv[k], vel])
    return ev
def parse(bars, offset_bars=0):
    ev, cur = [], None
    toks = []
    for b in bars:
        t = b.split(); assert len(t) == 16, (b, len(t)); toks += t
    for i, tk in enumerate(toks):
        if tk == '-':
            if cur: cur[1] += 1
        elif tk == '.': cur = None
        else: cur = [offset_bars * 16 + i, 1, midi(tk), 1.0]; ev.append(cur)
    return ev
def drums_parse(bars, offset_bars=0):
    ev = []
    for b, bar in enumerate(bars):
        t = bar.split(); assert len(t) == 16, (bar, len(t))
        for i, tk in enumerate(t):
            if tk != '.':
                for ch in tk: ev.append((offset_bars * 16 + b * 16 + i, ch))
    return ev

# ------------------------------------------------------------------ track / mixer
class Track:
    def __init__(self, bpm, intro_bars, loop_bars, tail=3.5):
        self.st = 60 / bpm / 4; self.intro = intro_bars * 16; self.loop = loop_bars * 16
        self.N = int(((self.intro + self.loop) * self.st + tail) * SR)
        self.bus = {}
    def buf(self, b):
        if b not in self.bus: self.bus[b] = np.zeros(self.N, np.float64)
        return self.bus[b]
    def put(self, b, step, sig, g=1.0):
        B = self.buf(b); i = int(round(step * self.st * SR)); n = min(len(sig), self.N - i)
        if n > 0: B[i:i + n] += sig[:n] * g
    def notes(self, b, ev, inst, g=1.0, cache=True):
        memo = {}
        for s, l, m, v in ev:
            key = (l, m, v)
            if key not in memo or not cache: memo[key] = dec(inst(hz(m), l * self.st, v))
            self.put(b, s, memo[key], g)
    def drums(self, ev, g=1.0):
        for s, ch in ev: self.put(DRUMS[ch][0], s, drum(ch), g)
    def mix(self, spec, lead_delay=('lead',), fb=0.33, dly_steps=3, wet=0.22, loop=True):
        L = np.zeros(self.N); R = np.zeros(self.N)
        for b, x in self.bus.items():
            g, pan = spec.get(b, (1.0, 0.0))
            x = filt(x, 'highpass', 28)
            if b in ('hat', 'crash'): x = filt(x, 'highpass', 6000)
            if b == 'snare': x = filt(x, 'lowpass', 9000)
            a = (pan + 1) * np.pi / 4
            L += x * g * np.cos(a) * 1.414; R += x * g * np.sin(a) * 1.414
            if b in lead_delay:  # ping-pong echo, darker each repeat
                d = int(round(dly_steps * self.st * SR)); y = filt(x * g, 'lowpass', 3500)
                for k in range(1, 6):
                    sh = np.zeros(self.N); sh[k * d:] = y[:self.N - k * d] * wet * fb ** (k - 1)
                    if k % 2: R += sh
                    else: L += sh
        st = np.stack([L, R], 1)
        n = (self.intro + self.loop) * self.st
        end = int(round(n * SR))
        if loop:  # fold the release tail back onto the loop start -> seamless loop
            ls = int(round(self.intro * self.st * SR)); tail = st[end:]
            k = min(len(tail), end - ls); st[ls:ls + k] += tail[:k]
            return st[:end], self.intro * self.st
        return st, None

def limiter(x, ceil_db=-1.2, look=0.003, rel=0.06):
    thr = 10 ** (ceil_db / 20); pk = np.abs(x).max(1)
    W = int(look * SR) | 1
    g = np.minimum(1.0, thr / np.maximum(maximum_filter1d(pk, W), 1e-9))
    g = minimum_filter1d(g, W * 2 + 1)
    Wr = int(rel * SR) | 1
    g = np.minimum(g, uniform_filter1d(minimum_filter1d(g, Wr), Wr))
    return x * g[:, None], 20 * np.log10(g.min())
def true_peak_db(x):
    up = resample_poly(x, 4, 1, axis=0); return 20 * np.log10(np.abs(up).max() + 1e-12)
METER = pyln.Meter(SR)
REPORT = []
def master(st, target_lufs):
    lufs0 = METER.integrated_loudness(st)
    st = st * 10 ** ((target_lufs - lufs0) / 20)
    st, gr = limiter(st, -1.5)
    st, _ = limiter(st, -1.5)
    return st, gr
def write(key, x, loop=None, lufs=None, kind='music'):
    p = os.path.join(WAV, key + '.wav'); sf.write(p, x.astype(np.float32), SR, subtype='PCM_16')
    o = os.path.join(OUT, key + '.ogg')
    q = '5' if kind == 'music' else '6'
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', p, '-c:a', 'libvorbis', '-q:a', q, o], check=True)
    mono = x if x.ndim == 1 else x.mean(1)
    w = int(0.05 * SR)
    rms_st = 10 * np.log10(uniform_filter1d(mono ** 2, w).max() + 1e-12)
    xs = x if x.ndim == 2 else x[:, None]
    try: L = METER.integrated_loudness(np.pad(xs, ((0, max(0, int(0.5 * SR) - len(xs))), (0, 0))))
    except Exception: L = float('nan')
    REPORT.append(dict(key=key, kind=kind, dur=round(len(x) / SR, 3), loop=loop, lufs=round(L, 1),
                       peak=round(20 * np.log10(np.abs(x).max()), 2), tp=round(true_peak_db(xs), 2), rms50=round(rms_st, 1),
                       kb=round(os.path.getsize(o) / 1024, 1)))
    print(REPORT[-1])

MIX = {'lead': (0.30, -0.12), 'flute': (0.30, -0.12), 'riff': (0.27, -0.1), 'riff2': (0.17, 0.35), 'stab': (0.16, 0.4), 'arp': (0.13, 0.38),
       'pad': (0.16, 0.3), 'bass': (0.42, 0.0), 'kick': (0.6, 0.0), 'snare': (0.42, 0.06), 'hat': (0.3, 0.25), 'crash': (0.24, -0.2), 'tom': (0.45, -0.1)}

# ================================================================== STAGE 1 "Wool Ops" (A minor, 150 BPM)
def stage1():
    tk = Track(150, 4, 44)
    # ---- chords (intro 4 | A 16 | B 16 | bridge 12)
    chords = ['Am', 'Am', 'F G', 'E'] + \
        ['Am', 'Am', 'F', 'G', 'Am', 'Am', 'F G', 'E', 'Am', 'Am', 'C', 'G', 'F', 'G', 'E', 'Am'] + \
        ['F', 'G', 'Em', 'Am', 'F', 'G', 'C', 'E', 'Dm', 'Em', 'F', 'G', 'Dm', 'E', 'F G', 'E'] + \
        ['Am', 'Am', 'Bb', 'Am', 'Am', 'Am', 'Bb', 'Am', 'F', 'G', 'E', 'E7']
    R_ = '. . . . . . . . . . . . . . . .'
    intro = [R_, R_, 'A4 - - A4 - - A4 - C5 - - C5 - - C5 -', 'B4 - - B4 - - B4 - D5 - - - E5 - D5 -']
    hook = 'E5 - . E5 A5 - . A5 B5 - C6 - - - B5 -'
    hook2 = 'A5 - - - - - E5 - A5 - B5 - C6 - D6 -'
    A = [hook, hook2, 'E6 - - - - - - - D6 - - - C6 - - -', 'D6 - - - - - B5 - G5 - - - - - . .',
         hook, 'A5 - - - E5 - - - A5 - C6 - E6 - - -', 'F6 - - - E6 - - - D6 - - - B5 - - -', 'G#5 - - - - - - - B5 - - - E6 - - -',
         hook, hook2, 'E6 - - - - - - - G6 - - - E6 - - -', 'D6 - - - - - - - B5 - - - G5 - - -',
         'A5 - - - C6 - - - F6 - - - E6 - D6 -', 'D6 - - - - - - - B5 - D6 - G6 - - -', 'E6 - - - D6 - C6 - B5 - - - G#5 - - -',
         'A5 - - - - - - - - - - - . . . .']
    B = ['A5 - - C6 - - F6 - - - - - E6 - C6 -', 'D6 - - B5 - - G5 - - - - - A5 - B5 -', 'G5 - - B5 - - E6 - - - - - D6 - B5 -',
         'C6 - - A5 - - E5 - - - - - A5 - B5 -', 'A5 - - C6 - - F6 - - - - - G6 - A6 -', 'G6 - - - - - - - - - - - D6 - - -',
         'E6 - - G6 - - E6 - - - - - D6 - C6 -', 'B5 - - - - - - - G#5 - - - E5 - - -',
         'F5 - - A5 - - D6 - - - - - C6 - A5 -', 'G5 - - B5 - - E6 - - - - - D6 - B5 -', 'A5 - - C6 - - F6 - - - - - E6 - F6 -',
         'G6 - - - - - - - F6 - - - D6 - - -', 'F6 - - - E6 - - - D6 - - - A5 - - -', 'G#5 - - - B5 - - - E6 - - - D6 - - -',
         'C6 - - - - - - - D6 - - - - - - -', 'E6 - - - - - - - - - - - . . . .']
    riff = ['A4 . A4 . C5 . A4 . D5 . A4 . E5 . D5 .', 'A4 . A4 . C5 . A4 . G5 - E5 . D5 . C5 .',
            'Bb4 . Bb4 . D5 . Bb4 . F5 . Bb4 . E5 . D5 .', 'A4 . A4 . C5 . A4 . E5 - - - D#5 - D5 -']
    br_end = ['A5 - - - - - C6 - - - F6 - - - E6 -', 'D6 - - - - - B5 - - - G5 - - - B5 -',
              'B5 - - - - - - - - - - - - - - -', 'E6 - D6 - B5 - G#5 - B5 - G#5 - E5 - D5 -']
    tk.notes('riff', parse(intro[:4]), i_riff)
    tk.notes('lead', parse(A, 4), i_lead)
    tk.notes('flute', parse(B, 20), i_flute)
    tk.notes('riff', parse(riff + [tr(b, 12) for b in riff], 36), i_riff)
    tk.notes('riff2', parse([tr(b, -5) for b in riff] + riff, 36), i_riff)   # parallel 4ths, then octave doubling
    tk.notes('lead', parse(br_end, 44), i_lead)
    # pulse-2: intro stabs, offbeat chord stabs in A, sparkle arps in B, stabs under the bridge climax
    tk.notes('stab', parse(['A4 . . A4 . . A4 . . A4 . . C5 . D5 .', 'A4 . . A4 . . A4 . . A4 . . E5 . D5 .'] + [R_] * 2), i_stab)
    tk.notes('stab', stabs(chords, range(4, 20)), i_stab)
    tk.notes('arp', arp(chords, range(20, 36), base=64), i_stab)
    tk.notes('stab', stabs(chords, range(44, 48), steps=(0, 3, 6, 8, 11, 14)), i_stab)
    # bass
    drive = 'R - O - R R O - R - O - R R O -'
    gallop = 'R R O R R O R O R R O R R O R O'
    walkB = 'R - O - 5 - O - R - O - 5 - O R'
    bp = [gallop, gallop, drive, 'R - R - R - R - O - O - O O O O'] + [drive] * 16 + [walkB] * 16 + [gallop] * 8 + \
         [drive, drive, 'R - - - R - - - O - - - R - - -', 'R R O R R O R O R R O R 5 5 O O']
    tk.notes('bass', bass_line(chords, bp), i_bass)
    # drums
    Ab = 'Kh . h . Sh . h . Kh . Kh . Sh . h h'
    f1 = 'Kh . h . Sh . h . Kh . S . S S S S'
    f2 = 'Kh . h . Sh . h . K . T T t t S S'
    Bb = 'Kh . o . Sh . h K . K h . Sh . o .'
    Br = 'Kh h h h KSh h h h Kh h h h KSh h h h'
    roll8 = 'KS . S . KS . S . KS . S . KS . S S'
    roll16 = 'KS S S S KS S S S KS S S S KS S S S'
    first = lambda s: 'C' + s if not s.startswith('C') else s
    ctok = lambda bar: ' '.join([('C' + bar.split()[0])] + bar.split()[1:])
    dr = ['Kh . h . h . h . Kh . h . h . h .', 'Kh . h . h . h . Kh . h . Sh . S S', Ab, 'KS . S . KS . S . KS S S S KS S S S'] + \
         [ctok(Ab), Ab, Ab, f1, Ab, Ab, Ab, f2, ctok(Ab), Ab, Ab, f1, Ab, Ab, Ab, f2] + \
         [ctok(Bb), Bb, Bb, Bb, Bb, Bb, Bb, f2, ctok(Bb), Bb, Bb, Bb, Bb, Bb, roll8, roll16] + \
         [ctok(Br), Br, Br, Br, Br, Br, Br, f1, ctok(Ab), Ab, roll8, roll16]
    tk.drums(drums_parse(dr))
    st, ls = tk.mix(MIX, lead_delay=('lead', 'flute'))
    return st, ls

# ================================================================== TITLE fanfare (A minor, 116 BPM)
def title():
    tk = Track(116, 2, 8)
    chords = ['Am', 'E', 'Am', 'F', 'G', 'Am', 'F', 'G', 'E', 'E']
    lead = ['A4 - - A4 - - A4 - A4 - - A4 - - A4 -', 'G#4 - - G#4 - - G#4 - B4 - - B4 D5 - E5 -',
            'A4 - - - E5 - - - A5 - - - - - - -', 'C6 - - - - - B5 - A5 - - - F5 - - -', 'D6 - - - - - C6 - B5 - - - G5 - - -',
            'E6 - - - - - - - - - - - E5 - A5 -', 'F6 - - - E6 - - - D6 - - - C6 - - -', 'D6 - - - C6 - - - B5 - - - G5 - - -',
            'G#5 - - - B5 - - - E6 - - - D6 - - -', 'B5 - - - - - - - G#5 - - - E5 - B4 -']
    harm = ['E4 - - E4 - - E4 - E4 - - E4 - - E4 -', 'E4 - - E4 - - E4 - G#4 - - G#4 B4 - B4 -',
            'C5 - - - - - - - E5 - - - - - - -', 'A4 - - - - - - - C5 - - - - - - -', 'B4 - - - - - - - D5 - - - - - - -',
            'C5 - - - - - - - - - - - . . . .', 'A5 - - - G5 - - - F5 - - - E5 - - -', 'B5 - - - A5 - - - G5 - - - D5 - - -',
            'E5 - - - G#5 - - - B5 - - - B5 - - -', 'G#5 - - - - - - - E5 - - - B4 - G#4 -']
    tk.notes('riff', parse(lead[:2]), i_riff); tk.notes('lead', parse(lead[2:], 2), i_lead)
    tk.notes('pad', parse(harm), i_pad)
    tk.notes('stab', stabs(chords, range(2, 10), steps=(3, 6, 11, 14)), i_stab)
    tk.notes('bass', bass_line(chords, ['R - - R - - R - R - - R - - R -', 'R - - R - - R - O - - O - O - O -'] +
                               ['R - - - - - O - R - - - O - R -'] * 8), i_bass_long)
    march = 'K . s s S . s . K . s s S s S s'
    tk.drums(drums_parse(['K . . K . . K . K . . K . . K .', 'K . . K . . K . S S S S S S S S', 'C' + march, march, march, march,
                          march, march, march, 'KS . s s S . s . KS S S S T T t t']))
    return tk.mix(MIX)

# ================================================================== BOSS (E phrygian-ish, 172 BPM)
def boss():
    tk = Track(172, 0, 16)
    chords = ['Em', 'Em', 'F', 'Em', 'Em', 'Em', 'C', 'B', 'Em', 'Em', 'F', 'Em', 'C', 'D', 'B', 'B']
    lead = ['E5 - - - - - - - F5 - - - E5 - - -', 'G5 - - - - - F5 - E5 - - - D#5 - - -', 'F5 - - - A5 - - - C6 - - - B5 - - -',
            'B5 - - - - - - - - - - - A#5 - B5 -', 'E6 - - - D#6 - - - E6 - - - G6 - - -', 'F#6 - - - E6 - - - D#6 - - - B5 - - -',
            'C6 - - - B5 - - - A5 - - - G5 - - -', 'F#5 - - - A5 - - - B5 - - - D#6 - - -']
    riff = ['E5 . E5 . G5 . E5 . A#5 . E5 . B5 . A5 .', 'E5 . E5 . G5 . E5 . F5 - E5 . D#5 . E5 .',
            'F5 . F5 . A5 . F5 . B5 . F5 . C6 . B5 .', 'E5 . E5 . G5 . E5 . B5 - - - A#5 - B5 -']
    end = ['C6 - - - - - - - G5 - - - E5 - - -', 'D6 - - - - - - - A5 - - - F#5 - - -',
           'D#6 - - - - - - - F#6 - - - - - - -', 'B5 - - - A5 - - - F#5 - - - D#5 - - -']
    tk.notes('lead', parse(lead), i_lead); tk.notes('riff', parse(riff, 8), i_riff)
    tk.notes('riff2', parse([tr(b, -12) for b in riff], 8), i_riff); tk.notes('lead', parse(end, 12), i_lead)
    tk.notes('arp', arp(chords, range(0, 8), idx=(0, 2, 1, 3, 2, 1), base=60), i_stab)
    tk.notes('stab', stabs(chords, range(12, 16), steps=(0, 3, 6, 10, 12, 14), ivs=(0, 1, 2)), i_stab)
    tk.notes('bass', bass_line(chords, ['R R O R 1 R O R R R O R 1 R O 1'] * 15 + ['R R O R R O R O O O 8 8 O O 8 8']), i_bass)
    Bt = 'Kh h h h Sh h K h Kh h h h Sh h K h'
    Bf = 'Kh h h h Sh h K h S S T T t t S S'
    tk.drums(drums_parse(['C' + Bt, Bt, Bt, Bf, Bt, Bt, Bt, 'KS . S . KS . S . KS S S S KS S S S',
                          'C' + Bt, Bt, Bt, Bf, 'C' + Bt, Bt, Bt, 'KS S S S KS S S S KS S S S KS S S S']))
    return tk.mix(MIX)

# ================================================================== STINGS
def sting_clear():
    tk = Track(150, 0, 4, tail=0.2)
    chords = ['A', 'F G', 'A', 'A']
    tk.notes('lead', parse(['A4 . C#5 . E5 . A5 - - - G5 - A5 - B5 -', 'C6 - - - - - - - D6 - - - - - - -',
                            'C#6 - - - - - - - - - - - - - - -', '. . . . . . . . . . . . . . . .']), i_lead)
    tk.notes('pad', parse(['E4 . A4 . C#5 . E5 - - - E5 - E5 - G5 -', 'A5 - - - - - - - B5 - - - - - - -',
                           'A5 - - - - - - - - - - - - - - -', '. . . . . . . . . . . . . . . .']), i_pad)
    tk.notes('stab', parse(['. . . . . . . . . . . . . . . .', 'F5 . . F5 . . F5 . G5 . . G5 . . G5 .',
                            'E5 - - - - - - - - - - - - - - -', '. . . . . . . . . . . . . . . .']), i_pad, 0.8)
    tk.notes('bass', parse(['A2 - - - - - - - E2 - - - A2 - E2 -', 'F2 - - F2 - - F2 - G2 - - G2 - - G2 -',
                            'A2 - - - - - - - - - - - - - - -', '. . . . . . . . . . . . . . . .']), i_bass_long)
    tk.drums(drums_parse(['KC . . . S . . . K . S . S S S S', 'K . . K . . S . K . . K . . S S',
                          'KC . . . . . . . . . . . . . . .', '. . . . . . . . . . . . . . . .']))
    st, _ = tk.mix(MIX, loop=False)
    return fade_end(st, 1.4)
def sting_gameover():
    tk = Track(96, 0, 3, tail=0.2)
    tk.notes('lead', parse(['E5 - - - - - D5 - C5 - - - - - B4 -', 'A4 - - - - - - - G#4 - - - - - - -', 'A4 - - - - - - - - - - - - - - -']), i_flute)
    tk.notes('pad', parse(['C5 - - - - - B4 - A4 - - - - - G#4 -', 'F4 - - - - - - - E4 - - - - - - -', 'E4 - - - - - - - - - - - - - - -']), i_pad)
    tk.notes('bass', parse(['A2 - - - - - - - A2 - - - - - - -', 'F2 - - - - - - - E2 - - - - - - -', 'A1 - - - - - - - - - - - - - - -']), i_bass_long)
    tk.drums(drums_parse(['t . . . . . . . t . . . . . . .', 't . . . . . . . T . . t . . . .', 'KC . . . . . . . . . . . . . . .']))
    st, _ = tk.mix(MIX, loop=False)
    return fade_end(st, 1.6)
def sting_warning():  # klaxon: 4 rising whoops + fifth, pulsing low drone, hits on each whoop
    dur = 2.6; n = int(dur * FS); t = T(n)
    per = 0.62; ph = (t % per) / per; on = ph < 0.8
    f = 420 * 2 ** (ph * 0.95)
    a = np.where(on, np.minimum(1, ph * per / 0.006) * np.clip((0.8 - ph) * per / 0.05, 0, 1), 0)
    k = np.where(t > per * 4 - 0.05, np.clip(1 - (t - per * 4 + 0.05) / 0.1, 0, 1), 1)
    wail = (pulse(f, 0.25) * 0.8 + 0.4 * pulse(f * 1.4983, 0.5)) * a * k
    drone = (tri(np.full(n, hz(28))) * 0.9 + 0.5 * sine(np.full(n, hz(28)))) * (0.6 + 0.4 * np.cos(2 * np.pi * t / per)) * np.clip((dur - t) / 0.3, 0, 1)
    x = dec(wail * 0.5 + drone * 0.5)
    k_, s_ = d_kick(), d_snare(); k_[:len(s_)] += 0.6 * s_; hit = dec(k_)
    for i in range(4):
        s = int(i * per * SR); x[s:s + len(hit)] += hit[:len(x) - s] * 0.8
    x = filt(x, 'highpass', 30)
    return np.stack([x, x], 1)
def sting_continue():  # re-arm: snare roll + rising riff, lands on the dominant so the stage theme drops straight in
    tk = Track(150, 0, 2, tail=0.6)
    tk.notes('riff', parse(['A4 . A4 . C5 . D5 . E5 . G5 . A5 - - -', 'B5 - - - - - - - . . . . . . . .']), i_lead)
    tk.notes('pad', parse(['E4 . E4 . A4 . A4 . C5 . D5 . E5 - - -', 'G#5 - - - - - - - . . . . . . . .']), i_pad)
    tk.notes('bass', parse(['A2 . A2 . A2 . A2 . A2 . A2 . A3 . A3 .', 'E2 - - - - - - - . . . . . . . .']), i_bass)
    tk.drums(drums_parse(['KS s S s KS s S s KS S S S KS S S S', 'KC . . . . . . . . . . . . . . .']))
    st, _ = tk.mix(MIX, loop=False)
    return fade_end(st, 0.9)
def fade_end(st, sec):
    n = int(sec * SR); st = st.copy(); st[-n:] *= np.linspace(1, 0, n)[:, None] ** 2; return st

# ================================================================== SFX (mono, 44.1k)
def S(sec): return int(sec * FS)
def ex(t, tau): return np.exp(-t / tau)
def att(t, a=0.0015): return np.minimum(1, t / a)
def crush(x, bits=6, hold=4):  # light bit/sample crush for chip grit (on SR signal)
    y = np.repeat(x[::hold], hold)[:len(x)]; q = 2 ** (bits - 1); return np.round(y * q) / q
def sfx_shoot():  # rifle: bright snap + body thump
    n = S(0.16); t = T(n)
    f = 380 + 1500 * ex(t, 0.018)
    tone = pulse(f, np.where(t < 0.02, 0.5, 0.25)) * ex(t, 0.045) * 0.7
    nz = noise(np.full(n, 220000), n) * ex(t, 0.02) * 0.8
    thump = sine(95 + 120 * ex(t, 0.01)) * ex(t, 0.04) * 0.9
    x = dec((tone + nz + thump) * att(t, 0.0006))
    return filt(x, 'highpass', 60)
def sfx_shoot_m():  # machine gun: shorter, tighter, a touch lower so rapid fire doesn't fatigue
    n = S(0.1); t = T(n)
    f = 300 + 1100 * ex(t, 0.014)
    tone = pulse(f, 0.25) * ex(t, 0.03) * 0.6
    nz = noise(np.full(n, 150000), n) * ex(t, 0.014) * 0.85
    thump = sine(110 + 100 * ex(t, 0.008)) * ex(t, 0.025) * 0.9
    return filt(dec((tone + nz + thump) * att(t, 0.0005)), 'highpass', 70)
def sfx_spread():  # shotgun-ish: 3 detuned falling pulses + fat noise
    n = S(0.24); t = T(n); x = 0
    for k, dt in enumerate((1.0, 1.26, 1.5)):
        x = x + pulse((260 + 900 * ex(t, 0.03)) * dt, 0.25) * ex(t, 0.07) * 0.32
    nz = noise(60000 * (0.4 + 0.6 * ex(t, 0.05)), n) * ex(t, 0.06) * 0.8
    thump = sine(80 + 140 * ex(t, 0.012)) * ex(t, 0.06)
    return filt(dec((x + nz + thump) * att(t, 0.0008)), 'highpass', 50)
def sfx_laser():  # classic falling zap with ring
    n = S(0.3); t = T(n)
    f = 280 + 2400 * ex(t, 0.05)
    x = pulse(f, 0.5) * 0.55 + pulse(f * 1.51, 0.125) * 0.3 + sine(f * 0.5) * 0.3
    x = x * (0.75 + 0.25 * np.sin(2 * np.pi * 60 * t)) * ex(t, 0.1) * att(t, 0.001)
    x += noise(np.full(n, 300000), n) * ex(t, 0.01) * 0.3
    return filt(dec(x), 'highpass', 90)
def sfx_enemy_shot():  # dull, lower "pff-tok" so it reads as not-yours
    n = S(0.12); t = T(n)
    x = pulse(520 * ex(t, 0.12) + 180, 0.125) * ex(t, 0.04) * 0.6 + noise(np.full(n, 40000), n) * ex(t, 0.015) * 0.6
    return filt(dec(x * att(t, 0.001)), 'lowpass', 5000)
def sfx_hit():  # metallic tick
    n = S(0.07); t = T(n)
    x = pulse(1500 * ex(t, 0.05) + 500, 0.5) * ex(t, 0.02) * 0.5 + noise(np.full(n, 300000), n) * ex(t, 0.008) * 0.6
    return filt(dec(x * att(t, 0.0004)), 'highpass', 300)
def sfx_enemy_die():  # crunch + short falling yelp (a startled "meh!")
    n = S(0.36); t = T(n)
    crunch = noise(30000 * ex(t, 0.08) + 3000, n) * ex(t, 0.09) * 0.9
    fy = (820 * ex(t, 0.2) + 180) * (1 + 0.04 * np.sin(2 * np.pi * 28 * t))
    yelp = pulse(fy, 0.25) * np.clip((t - 0.015) / 0.01, 0, 1) * ex(t, 0.1) * 0.55
    thump = sine(70 + 120 * ex(t, 0.02)) * ex(t, 0.07) * 0.9
    x = dec((crunch + yelp + thump) * att(t, 0.0006))
    return filt(x, 'highpass', 40)
def boom_core(dur, sub_tau, body_tau, rate0, rate1, crack=0):
    n = S(dur); t = T(n)
    chip = noise(rate1 + (rate0 - rate1) * ex(t, dur * 0.25), n) * ex(t, body_tau) * 0.8
    white = noise(np.full(n, 400000), n) * ex(t, body_tau * 0.35)
    sub = sine(32 + 90 * ex(t, 0.06)) * ex(t, sub_tau) * 1.1
    x = chip + sub
    x = dec(x * att(t, 0.001))
    w = dec(white * att(t, 0.0005))
    # darkening sweep on the white layer
    cut = sos('lowpass', 6000); w = sosfilt(cut, w) * 0.6
    y = x + w
    if crack:
        for i in range(crack):
            s = int(rng.uniform(0.12, dur * 0.6) * SR); m = int(0.03 * SR)
            y[s:s + m] += noise(np.full(m * OS, 90000), m * OS)[::OS][:len(y) - s] * np.exp(-np.arange(m) / (0.008 * SR)) * rng.uniform(0.2, 0.45)
    y = np.tanh(y * 1.6) / np.tanh(1.6)
    return filt(y, 'highpass', 25)
def sfx_boom(): return boom_core(0.7, 0.16, 0.18, 26000, 2500)
def sfx_boom_big(): return boom_core(1.5, 0.35, 0.38, 20000, 1400, crack=7)
def sfx_jump():
    n = S(0.14); t = T(n)
    f = 260 * 2 ** (t / 0.14 * 1.4)
    return dec(pulse(f, 0.25) * ex(t, 0.07) * att(t, 0.002) * 0.6)
def sfx_land():
    n = S(0.1); t = T(n)
    x = sine(60 + 90 * ex(t, 0.015)) * ex(t, 0.035) + noise(np.full(n, 20000), n) * ex(t, 0.012) * 0.35
    return filt(dec(x * att(t, 0.001)), 'lowpass', 2500)
def sfx_pickup():  # power-up: fast rising major arpeggio with a shimmer echo
    notes = [69, 73, 76, 81, 85, 88, 93]; step = 0.045; n = S(0.62); t = T(n); x = np.zeros(n)
    for i, m in enumerate(notes):
        s = S(i * step); m_ = S(0.16); tt = T(m_)
        seg = pulse(np.full(m_, hz(m)), 0.25 if i % 2 else 0.125) * ex(tt, 0.06) * att(tt, 0.001)
        x[s:s + m_] += seg[:n - s] * 0.5
    y = dec(x); d = int(0.09 * SR)
    y[d:] += y[:-d] * 0.35; y[2 * d:] += y[:-2 * d] * 0.12
    return y
def sfx_die():  # the sheep gets it: crunch + chip drop + bit-crushed "BAAA-a-a"
    n = S(1.05); t = T(n)
    crunch = noise(40000 * ex(t, 0.1) + 4000, n) * ex(t, 0.08) * 0.9 + sine(60 + 150 * ex(t, 0.02)) * ex(t, 0.08)
    drop = pulse(900 * ex(t, 0.25) + 80, 0.5) * ex(t, 0.35) * 0.18 * np.clip((t - 0.05) / 0.02, 0, 1)
    # bleat: bright pulse source, pitch 560 -> 430 Hz, 17 Hz warble (the "a-a-a"), formants /a/
    tb = np.maximum(t - 0.07, 0)
    fb = (560 - 130 * np.minimum(tb / 0.6, 1)) * (1 + 0.035 * np.sin(2 * np.pi * 17 * tb))
    ab = np.clip(tb / 0.02, 0, 1) * np.clip((0.78 - tb) / 0.2, 0, 1) * (0.72 + 0.28 * np.sin(2 * np.pi * 17 * tb)) * (t > 0.07)
    src = pulse(fb, 0.3) * ab
    src = dec(src)
    b1 = sosfilt(butter(2, [700, 1100], 'bandpass', fs=SR, output='sos'), src)
    b2 = sosfilt(butter(2, [1300, 1900], 'bandpass', fs=SR, output='sos'), src)
    b3 = sosfilt(butter(2, [2500, 3300], 'bandpass', fs=SR, output='sos'), src)
    op = np.clip((np.arange(len(src)) / SR - 0.07) / 0.05, 0.25, 1)  # "b": formants open up
    bleat = (1.6 * b1 + 1.1 * b2 + 0.5 * b3 + 0.25 * src) * op
    bleat = crush(bleat * 1.3, 7, 3)
    y = dec(crunch + drop) + bleat * 0.9
    return filt(np.tanh(y * 1.3), 'highpass', 50)
def sfx_capsule():  # pod pops open: bright rising "pok" + small bang
    n = S(0.3); t = T(n)
    pok = pulse(600 * 2 ** np.minimum(t / 0.06, 1.3), 0.5) * ex(t, 0.05) * 0.6
    nz = noise(90000 * ex(t, 0.05) + 8000, n) * ex(t, 0.06) * 0.7
    sub = sine(90 + 90 * ex(t, 0.02)) * ex(t, 0.05) * 0.7
    return filt(dec((pok + nz + sub) * att(t, 0.0006)), 'highpass', 50)
def sfx_select():  # menu cursor blip
    n = S(0.1); t = T(n)
    f = np.where(t < 0.035, hz(88), hz(93))
    return dec(pulse(f, 0.25) * ex(t, 0.05) * att(t, 0.001) * 0.6)
def sfx_start():  # confirm: big power chord blast + rising blip
    n = S(0.8); t = T(n); x = np.zeros(n)
    for m in (57, 64, 69, 73, 76):
        x += pulse(np.full(n, hz(m)) * (1 + 0.002 * (m % 3)), 0.25) * 0.18
    x = x * ex(t, 0.3) * att(t, 0.002)
    x += pulse(hz(81) * 2 ** np.minimum(t / 0.08, 1), 0.125) * ex(t, 0.12) * 0.25
    x += d_crash(0.35)[:n]
    return dec(x)

# target = loudest-50ms RMS in dBFS (a short-term loudness proxy); tiers: ambient -21, feedback -18, weapons -14, events -12, explosions -9
def _seq(notes, step, dur_each, duty=0.25, tau=0.08, total=None, vib_=False):
    n = S(total or (len(notes) * step + dur_each + 0.05)); x = np.zeros(n)
    for i, m in enumerate(notes):
        if m is None: continue
        s = S(i * step); m_ = min(S(dur_each), n - s); tt = T(m_)
        f = vib(tt, hz(m), 0.08, 6.5, 0.25) if vib_ else np.full(m_, hz(m))
        x[s:s + m_] += pulse(f, np.where(tt < 0.015, 0.125, duty)) * ex(tt, tau) * att(tt, 0.001)
    return x
def sfx_pause():  # NES-style pause chime: quick up-down triad with an echo
    y = dec(_seq([88, 83, 88, 95], 0.055, 0.12, 0.25, 0.05)); d = int(0.08 * SR)
    y = np.concatenate([y, np.zeros(d * 2)]); y[d:] += y[:-d] * 0.3
    return y
def sfx_telegraph():  # enemy wind-up: tiny rising charge tick
    n = S(0.08); t = T(n)
    x = pulse(900 * 2 ** (t / 0.06), 0.125) * ex(t, 0.025) * att(t, 0.002) * 0.6 + noise(np.full(n, 300000), n) * ex(t, 0.004) * 0.3
    return filt(dec(x), 'highpass', 400)
def sfx_count():  # continue countdown tick
    n = S(0.12); t = T(n)
    return dec(pulse(np.full(n, hz(81)), 0.5) * ex(t, 0.035) * att(t, 0.001) * 0.5 + tri(np.full(n, hz(69))) * ex(t, 0.05) * 0.4)
def sfx_extralife():  # 1-UP: bright rising run, then a trilled top note with harmony
    lead = _seq([69, 73, 76, 81, 80, 81, 85, 88], 0.055, 0.1, 0.25, 0.06, total=1.0)
    s = S(8 * 0.055); m_ = S(0.5); tt = T(m_)
    top = pulse(vib(tt, hz(93), 0.05, 12, 0.35), 0.25) * np.minimum(1, tt / 0.003) * np.clip((0.5 - tt) / 0.25, 0, 1)
    har = pulse(vib(tt, hz(88), 0.05, 12, 0.35), 0.125) * np.minimum(1, tt / 0.003) * np.clip((0.5 - tt) / 0.25, 0, 1) * 0.5
    lead[s:s + m_] += (top + har) * 0.9
    y = dec(lead); d = int(0.07 * SR); y = np.concatenate([y, np.zeros(d)]); y[d:] += y[:-d] * 0.25
    return y
def sfx_powerup():  # weapon get: "ka-CHUNK" reload + brassy rising fanfare
    n = S(0.95); t = T(n); x = np.zeros(n)
    ka = noise(np.full(S(0.03), 300000), S(0.03)) * ex(T(S(0.03)), 0.006) * 0.6
    x[:len(ka)] += ka
    c0 = S(0.075); m_ = S(0.12); tt = T(m_)
    x[c0:c0 + m_] += (noise(40000, m_) * ex(tt, 0.02) * 0.7 + sine(70 + 120 * ex(tt, 0.015)) * ex(tt, 0.05))
    f0 = S(0.16)
    for i, (m, l) in enumerate([(64, 0.07), (69, 0.07), (76, 0.55)]):
        s = f0 + S(i * 0.07); mm = min(S(l + 0.1), n - s); tt = T(mm)
        e = att(tt, 0.002) * (ex(tt, 0.3) if l > 0.2 else ex(tt, 0.05)) * np.clip((l + 0.1 - tt) / 0.1, 0, 1)
        x[s:s + mm] += (pulse(vib(tt, hz(m), 0.12, 6, 0.2), np.where(tt < 0.02, 0.125, 0.25)) + 0.5 * pulse(vib(tt, hz(m - 5 + (0 if i < 2 else 1)), 0.12, 6, 0.2), 0.5)) * e * 0.55
    y = dec(x); d = int(0.09 * SR); y[d:] += y[:-d] * 0.22
    return y

SFX = {'shoot': (sfx_shoot, -14), 'shoot-m': (sfx_shoot_m, -15.5), 'spread': (sfx_spread, -13.5), 'laser': (sfx_laser, -14),
       'enemy-shot': (sfx_enemy_shot, -18.5), 'hit': (sfx_hit, -20), 'enemy-die': (sfx_enemy_die, -12.5), 'boom': (sfx_boom, -9.5),
       'boom-big': (sfx_boom_big, -8), 'jump': (sfx_jump, -19), 'land': (sfx_land, -22), 'pickup': (sfx_pickup, -13.5),
       'die': (sfx_die, -9), 'capsule': (sfx_capsule, -13), 'select': (sfx_select, -18), 'start': (sfx_start, -13),
       'pause': (sfx_pause, -17), 'telegraph': (sfx_telegraph, -24), 'count': (sfx_count, -19), 'extralife': (sfx_extralife, -13),
       'powerup': (sfx_powerup, -13)}

exec(compile(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'campaign.py')).read(), 'campaign.py', 'exec'))
LAZY = [k for k, _, _ in CAMPAIGN_MUSIC]  # loaded on demand by Music.js (keeps boot fast and decoded-audio memory low)

def render_sfx(which=None):
    table = {**SFX, **CAMPAIGN_SFX} if which is None else which
    for k, (fn, pk) in table.items():
        x = np.asarray(fn(), np.float64)
        # trim trailing silence, 3 ms fade out
        if k not in LOOPING_SFX:
            nz = np.nonzero(np.abs(x) > 1e-3)[0]; x = x[:nz[-1] + int(0.01 * SR)] if len(nz) else x
            x[-int(0.003 * SR):] *= np.linspace(1, 0, int(0.003 * SR))
        r = 10 * np.log10(uniform_filter1d(x ** 2, int(0.05 * SR)).max())
        x = x * 10 ** ((pk - r) / 20)
        if np.abs(x).max() > 10 ** (-1.5 / 20):  # too peaky for its loudness: soft-limit instead of clipping
            x, _ = limiter(x[:, None], -1.5); x = x[:, 0]
        write('sfx-' + k, x, kind='sfx')

def render_music(campaign_only=False):
    loops = {}
    base = [('music-stage1', stage1, -15), ('music-title', title, -15), ('music-boss', boss, -14.5)]
    for key, fn, lufs in ([] if campaign_only else base) + CAMPAIGN_MUSIC:
        st, ls = fn(); st, gr = master(st, lufs)
        print(key, 'limiter GR dB', round(gr, 2)); write(key, st, loop=ls); loops[key] = dict(loopStart=round(ls, 6), loopEnd=round(len(st) / SR, 6))
    for key, fn, lufs in [] if campaign_only else [('sting-clear', sting_clear, -14), ('sting-gameover', sting_gameover, -16), ('sting-warning', sting_warning, -13), ('sting-continue', sting_continue, -14)]:
        st = fn(); st, gr = master(st, lufs)
        nz = np.nonzero(np.abs(st).max(1) > 10 ** (-60 / 20))[0]; st = st[:nz[-1] + int(0.02 * SR)]
        write(key, st)
    return loops

if __name__ == '__main__':
    only = sys.argv[sys.argv.index('--only') + 1] if '--only' in sys.argv else None
    loops = {}
    if only in (None, 'music'): loops = render_music()
    if only in (None, 'sfx'): render_sfx()
    if only == 'csfx': render_sfx(CAMPAIGN_SFX)
    if only == 'campaign': loops = render_music(True); render_sfx(CAMPAIGN_SFX)
    rp = os.path.join(os.path.dirname(__file__), 'report.json')
    old = json.load(open(rp)) if os.path.exists(rp) else {'items': [], 'loops': {}}
    items = {i['key']: i for i in old['items']}; items.update({i['key']: i for i in REPORT})
    old['loops'].update(loops)
    json.dump({'items': list(items.values()), 'loops': old['loops']}, open(rp, 'w'), indent=1)
    # asset registration
    keys = sorted(k for k in items if k not in LAZY)
    json.dump({'assets': [{'type': 'audio', 'key': k, 'url': f'assets/audio/{k}.ogg'} for k in keys], 'anims': []},
              open(os.path.join(ROOT, 'assets', 'parts', 'audio.json'), 'w'), indent=1)
    with open(os.path.join(ROOT, 'src', 'audio', 'audioData.js'), 'w') as f:
        f.write('// GENERATED by art/raw/audio/synth.py - loop points (seconds) for the rendered music.\n')
        f.write('export const LOOPS = ' + json.dumps(old['loops'], indent=1) + ';\n')
        f.write('// not in the boot manifest: fetched + decoded on first Music.play / Music.prefetch' + chr(10))
        f.write('export const LAZY = ' + json.dumps({k: f'assets/audio/{k}.ogg' for k in LAZY}, indent=1) + ';' + chr(10))
