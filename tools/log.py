"""Append an entry to the live progress page and rebuild progress.html.
usage: python tools/log.py --piece hero --kind build|critic|wave|note --title "..." [--text "..."] [--media shots/a.png --media shots/b.mp4]
Media is copied into progress/media so later overwrites of shots/ don't change history.
One JSON file per entry (progress/entries/) so parallel agents never collide."""
import argparse, json, os, shutil, time, glob, html

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
E = os.path.join(ROOT, 'progress', 'entries'); M = os.path.join(ROOT, 'progress', 'media')

def rebuild():
    items = []
    for f in sorted(glob.glob(os.path.join(E, '*.json'))):
        try: items.append(json.load(open(f, encoding='utf-8')))
        except Exception: pass
    items.sort(key=lambda x: x['t'], reverse=True)
    pieces = sorted({i['piece'] for i in items})
    latest = {}
    for i in items:
        if i['piece'] not in latest and any(m.endswith('.png') for m in i.get('media', [])): latest[i['piece']] = i
    def media(ms):
        out = []
        for m in ms:
            if m.endswith('.mp4') or m.endswith('.webm'):
                out.append(f'<video src="{m}" controls loop muted playsinline></video>')
            else:
                out.append(f'<a href="{m}"><img src="{m}" loading="lazy"></a>')
        return ''.join(out)
    cards = ''.join(f'''<article class="k-{html.escape(i['kind'])}"><header><b>{html.escape(i['piece'])}</b> <span class="kind">{html.escape(i['kind'])}</span>
<time>{time.strftime('%H:%M', time.localtime(i['t']))}</time></header><h3>{html.escape(i['title'])}</h3>
<p>{html.escape(i.get('text', '')).replace(chr(10), '<br>')}</p><div class="m">{media(i.get('media', []))}</div></article>''' for i in items)
    now_strip = ''.join(f'<figure><img src="{[m for m in i["media"] if m.endswith(".png")][0]}"><figcaption>{html.escape(p)}</figcaption></figure>' for p, i in latest.items())
    page = f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="refresh" content="60"><title>Armed and Fluffy progress</title><style>
:root{{--bg:#0d0f14;--card:#171a22;--fg:#e9e6dc;--mut:#8a8f9c;--acc:#ffb020;--win:#5fd068;--lose:#ff6a5a}}
body{{margin:0;background:var(--bg);color:var(--fg);font:15px/1.45 system-ui,sans-serif}}
main{{max-width:1100px;margin:auto;padding:16px}} h1{{font-size:22px;margin:4px 0 2px}} .sub{{color:var(--mut);margin:0 0 14px}}
.now{{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:8px;margin-bottom:18px}}
.now figure{{margin:0}} .now img{{width:100%;image-rendering:pixelated;border-radius:6px}} figcaption{{color:var(--mut);font-size:12px}}
article{{background:var(--card);border-radius:10px;padding:12px 14px;margin:0 0 12px;border-left:4px solid #333}}
.k-critic{{border-color:var(--lose)}} .k-win{{border-color:var(--win)}} .k-wave{{border-color:var(--acc)}} .k-build{{border-color:#4a90d9}}
header{{display:flex;gap:8px;align-items:baseline;font-size:13px;color:var(--mut)}} header b{{color:var(--acc)}} time{{margin-left:auto}}
h3{{margin:4px 0;font-size:16px}} p{{margin:4px 0 8px;color:#cfccc2}} .m{{display:flex;flex-wrap:wrap;gap:8px}}
.m img,.m video{{max-width:100%;width:480px;image-rendering:pixelated;border-radius:6px}}
</style></head><body><main><h1>ARMED AND FLUFFY: live build log</h1>
<p class="sub">{len(items)} entries · pieces: {html.escape(', '.join(pieces))} · updated {time.strftime('%Y-%m-%d %H:%M')} · auto-refreshes every minute</p>
<h2>Latest frame per piece</h2><div class="now">{now_strip}</div><h2>Timeline</h2>{cards}</main></body></html>'''
    open(os.path.join(ROOT, 'progress.html'), 'w', encoding='utf-8').write(page)

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--piece', default='lead'); ap.add_argument('--kind', default='note'); ap.add_argument('--title', default='')
    ap.add_argument('--text', default=''); ap.add_argument('--media', action='append', default=[])
    a = ap.parse_args()
    os.makedirs(E, exist_ok=True); os.makedirs(M, exist_ok=True)
    t = time.time(); stamp = time.strftime('%Y%m%d-%H%M%S') + f'-{int(t * 1000) % 1000:03d}'
    media = []
    for m in a.media:
        if not os.path.exists(m): continue
        dst = f'{stamp}_{a.piece}_{os.path.basename(m)}'
        shutil.copy(m, os.path.join(M, dst)); media.append('progress/media/' + dst)
    if a.title or a.text or media:
        json.dump({'t': t, 'piece': a.piece, 'kind': a.kind, 'title': a.title, 'text': a.text, 'media': media},
                  open(os.path.join(E, f'{stamp}_{a.piece}.json'), 'w', encoding='utf-8'))
    rebuild(); print('progress.html updated')
