"""Spectrogram + waveform sheets for the rendered audio -> shots/audio-music.png, shots/audio-sfx.png"""
import numpy as np, soundfile as sf, json, os, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
R = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(R, '..', '..', '..'))
rep = {i['key']: i for i in json.load(open(os.path.join(R, 'report.json')))['items']}
loops = json.load(open(os.path.join(R, 'report.json')))['loops']
plt.style.use('dark_background')
def spec(ax, x, sr, fmax=9000):
    ax.specgram(x, NFFT=1024, Fs=sr, noverlap=768, cmap='magma', vmin=-110, vmax=-20); ax.set_ylim(0, fmax)
mk = ['music-stage1', 'music-title', 'music-boss', 'sting-clear', 'sting-gameover', 'sting-warning', 'sting-continue']
fig, axs = plt.subplots(len(mk), 2, figsize=(18, 3.1 * len(mk)), gridspec_kw={'width_ratios': [3, 2]})
for (a1, a2), k in zip(axs, mk):
    x, sr = sf.read(os.path.join(R, 'wav', k + '.wav')); m = x.mean(1)
    spec(a1, m, sr); r = rep[k]
    a1.set_title(f"{k}  {r['dur']}s  {r['lufs']} LUFS  peak {r['peak']} dBFS  TP {r['tp']} dBTP", fontsize=10, loc='left')
    t = np.arange(len(m)) / sr; a2.plot(t, x[:, 0], lw=0.3, color='#ffb020'); a2.plot(t, -x[:, 1], lw=0.3, color='#4a90d9', alpha=0.6)
    a2.set_ylim(-1, 1); a2.axhline(10 ** (-1 / 20), color='r', lw=0.5); a2.axhline(-10 ** (-1 / 20), color='r', lw=0.5)
    if k in loops:
        for v in (loops[k]['loopStart'],): a1.axvline(v, color='cyan', lw=1); a2.axvline(v, color='cyan', lw=1)
    a2.set_title('waveform L / -R (red = -1 dBFS; cyan = loop start)', fontsize=9, loc='left')
fig.tight_layout(); fig.savefig(os.path.join(ROOT, 'shots', 'audio-music.png'), dpi=70)
sk = [k for k in rep if k.startswith('sfx-')]
fig, axs = plt.subplots(6, 4, figsize=(18, 16)); axs = axs.ravel()
for ax, k in zip(axs, sk):
    x, sr = sf.read(os.path.join(R, 'wav', k + '.wav')); t = np.arange(len(x)) / sr
    ax.plot(t * 1000, x, lw=0.4, color='#5fd068'); ax.set_ylim(-1, 1); ax.axhline(10 ** (-1 / 20), color='r', lw=0.5); ax.axhline(-10 ** (-1 / 20), color='r', lw=0.5)
    r = rep[k]; ax.set_title(f"{k[4:]}  {int(r['dur']*1000)}ms  rms50 {r['rms50']}  pk {r['peak']}", fontsize=10); ax.set_xlabel('ms', fontsize=8)
for ax in axs[len(sk):]: ax.axis("off")
fig.tight_layout(); fig.savefig(os.path.join(ROOT, 'shots', 'audio-sfx.png'), dpi=70)
# loop seam check: last 50 ms + first 50 ms after loop start, spliced
fig, axs = plt.subplots(1, 3, figsize=(18, 3))
for ax, k in zip(axs, ['music-stage1', 'music-title', 'music-boss']):
    x, sr = sf.read(os.path.join(R, 'wav', k + '.wav')); ls = int(round(loops[k]['loopStart'] * sr)); w = int(0.05 * sr)
    y = np.concatenate([x[-w:, 0], x[ls:ls + w, 0]]); ax.plot(np.arange(-w, w) / sr * 1000, y, lw=0.6); ax.axvline(0, color='cyan')
    ax.set_title(f'{k} loop seam (end -> loopStart)', fontsize=10)
fig.tight_layout(); fig.savefig(os.path.join(ROOT, 'shots', 'audio-seams.png'), dpi=70)
print('ok')
# campaign sheet
ck = ['music-stage2', 'music-stage3', 'music-boss2', 'music-boss3', 'music-intro', 'music-ending']
fig, axs = plt.subplots(len(ck), 2, figsize=(18, 3.1 * len(ck)), gridspec_kw={'width_ratios': [3, 2]})
for (a1, a2), k in zip(axs, ck):
    x, sr = sf.read(os.path.join(R, 'wav', k + '.wav')); m = x.mean(1); r = rep[k]
    spec(a1, m, sr); a1.axvline(loops[k]['loopStart'], color='cyan', lw=1)
    a1.set_title(f"{k}  {r['dur']}s (loop from {loops[k]['loopStart']:.2f}s)  {r['lufs']} LUFS  TP {r['tp']} dBTP", fontsize=10, loc='left')
    t = np.arange(len(m)) / sr; a2.plot(t, x[:, 0], lw=0.3, color='#ffb020'); a2.set_ylim(-1, 1)
    a2.axhline(10 ** (-1 / 20), color='r', lw=0.5); a2.axhline(-10 ** (-1 / 20), color='r', lw=0.5); a2.axvline(loops[k]['loopStart'], color='cyan', lw=1)
fig.tight_layout(); fig.savefig(os.path.join(ROOT, 'shots', 'audio-campaign.png'), dpi=70)
cs = ['shotgun', 'ricochet', 'sniper-charge', 'sniper', 'tank', 'gatling-spin', 'gatling', 'laser-bolt', 'flame', 'xeno-screech', 'xeno-pounce',
      'mutant-roar', 'goo', 'glass', 'queen-roar', 'rotor', 'thump', 'page', 'phone']
fig, axs = plt.subplots(5, 4, figsize=(18, 13)); axs = axs.ravel()
for ax, n in zip(axs, cs):
    x, sr = sf.read(os.path.join(R, 'wav', 'sfx-' + n + '.wav'))
    ax.specgram(x, NFFT=512, Fs=sr, noverlap=448, cmap='magma', vmin=-110, vmax=-20); ax.set_ylim(0, 10000)
    r = rep['sfx-' + n]; ax.set_title(f"{n}  {int(r['dur']*1000)}ms  rms50 {r['rms50']}  pk {r['peak']}", fontsize=10)
for ax in axs[len(cs):]: ax.axis('off')
fig.tight_layout(); fig.savefig(os.path.join(ROOT, 'shots', 'audio-campaign-sfx.png'), dpi=70)
print('campaign ok')
