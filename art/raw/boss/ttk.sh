#!/bin/sh
# core time-to-kill per weapon/stance at mid-arena (turrets removed by eval so only the core phase is timed).
# deterministic 60fps harness: art/raw/feel/play.mjs
H="window.__B=()=>__sheep.game.scene.getScene('Game').boss; window.__kt=()=>{const b=__B(); b.turrets.forEach(t=>b.kill(t));}; window.__done=()=>{const b=__B(); return !b||b.state!=='p2';}"
P="(()=>{const b=__B(); const p=__sheep.game.scene.getScene('Game').player; return {ttk:+((__vt.now()-window.__t0)/1000).toFixed(1), state:b.state, coreHp:b.core.hp, dist:Math.round(b.core.x-p.x)}})()"
for W in ${WEAPONS:-R M S L}; do for ST in stand prone; do
  K=fire; [ $ST = prone ] && K=down+fire
  R=$(node art/raw/feel/play.mjs --query "god=1&x=5100&weapon=$W" --max 90000 --eval "$H" \
    --script "hold:right:1300 wait:4200 eval:__kt() wait:2300 eval:window.__t0=__vt.now() down:$K" \
    --until "__done()" --print "$P" 2>&1 | grep -E "^print|pageerror|Error")
  echo "$W $ST $R"
done; done
