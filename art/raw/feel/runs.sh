#!/bin/bash
# N parallel non-god bot runs to the boss; prints deaths
cd /c/sheep
N=${1:-3}; Q=${2:-nointro=1}
for i in $(seq 1 $N); do
  node art/raw/feel/play.mjs --query "$Q" --bot 1 --trace art/raw/feel/run_live$i.json --sample 30 --until "(s=>s.boss||s.flow==='continue'||s.scene.includes('Title'))(window.__sheep.stats())" --max 200000 --print "(()=>{const s=window.__sheep.game.scene.getScene('Game');return {deaths:s.stat.deathLog.map(d=>d.x+':'+d.cause),kills:s.stat.kills,flow:s.flow,t:Math.round(s.time.now/1000)}})()" > art/raw/feel/run_out$i.txt 2>&1 &
done
wait
for i in $(seq 1 $N); do grep -E "pageerror|print" art/raw/feel/run_out$i.txt | sed "s/^/run$i /"; done
