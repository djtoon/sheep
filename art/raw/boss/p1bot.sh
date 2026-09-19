#!/bin/sh
# Boss measurement with the average-player bot (art/raw/feel/bot.js), varied per run:
# Math.random is replaced by a seeded PRNG (seed = run index) and the start x shifts by run.
# usage: p1bot.sh WEAPON GOD(0|1) RUNS [full]   (full = play to clear/game over, else stop at phase 2)
W=${1:-R}; G=${2:-1}; N=${3:-1}; FULL=${4:-}
for i in $(seq 1 $N); do
  X=$((5040 + (i * 37) % 120)); Q="x=$X&weapon=$W"; [ "$G" = 1 ] && Q="god=1&$Q"
  SEED="(()=>{let s=$i*2654435761>>>0; Math.random=()=>{s=(s+0x6D2B79F5)>>>0; let t=s; t=Math.imul(t^t>>>15,t|1); t^=t+Math.imul(t^t>>>7,t|61); return ((t^t>>>14)>>>0)/4294967296;};})()"
  if [ -n "$FULL" ]; then U="(()=>{const s=__sheep.game.scene.getScene('Game'); return !s||!s.player||(s.cleared&&s.boss&&s.boss.state==='sunk')||s.flow==='continue'||s.state.lives<0||(s.stat&&s.stat.deathLog.length>=4)})()"
  else U="(()=>{const s=__sheep.game.scene.getScene('Game'); const b=s&&s.boss; return !s||!s.player||(b&&b.transAt)||s.flow==='continue'||(s.stat&&s.stat.deathLog.length>=4)})()"; fi
  node art/raw/feel/play.mjs --query "$Q" --bot 1 --max 180000 --eval "$SEED" --until "$U" \
    --print "(()=>{const s=__sheep.game.scene.getScene('Game'); const b=s.boss; const dl=s.stat?s.stat.deathLog:[]; const f=v=>v==null?null:+(v/1000).toFixed(1); return {w:'$W',god:$G,run:$i,x:$X,p1:b&&b.transAt?f(b.transAt-b.p1At):null,p2:b&&b.diedAt&&b.transAt?f(b.diedAt-b.transAt):null,cleared:!!s.cleared,d1:dl.filter(d=>b&&b.p1At&&d.t>=b.p1At&&(!b.transAt||d.t<b.transAt)).length,d2:dl.filter(d=>b&&b.transAt&&d.t>=b.transAt).length,dAll:dl.length,coreHp:b?b.core.hp:null}})()" 2>&1 | grep -E "^print|pageerror" &
done; wait
