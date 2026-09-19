#!/bin/sh
# per-vent trace for Boss2 (bot, no god): time into p1, player x, mech X, damage dealt in the vent
node art/raw/feel/play.mjs --query "stage=2&x=${X:-5077}&weapon=${W:-R}" --bot 1 --max 120000 \
 --eval "(()=>{window.__v=[]; const sc=__sheep.game.scene.getScene('Game'); let last=null; const f=window.__stepN; window.__stepN=(n,r)=>{for(let i=0;i<n;i++){f(1,r&&i===n-1); const b=sc.boss; if(!b) continue; if(b.act==='vent'&&last!=='vent') window.__v.push({t:Math.round((sc.time.now-b.p1At)/100)/10,px:Math.round(sc.player.x),X:Math.round(b.X),prone:sc.player.prone}); if(b.act!=='vent'&&last==='vent') window.__v[window.__v.length-1].win=b.win; last=b.act;}};})()" \
 --until "(()=>{const b=__sheep.game.scene.getScene('Game').boss; return b&&b.transAt})()" --print "window.__v" 2>&1 | grep -E "^print|rror"
