#!/bin/bash
# For every rifleman spot: stand on the ground 100 px and 170 px to the left, hold a LEVEL rifle shot for 1.5 s, did it die?
cd /c/sheep
MODE=${1:-level}; KEYS=fire; [ "$MODE" = diag ] && KEYS=right+up+fire; [ "$MODE" = prone ] && KEYS=down+fire; [ "$MODE" = ddiag ] && KEYS=right+down+fire
SPOTS=${SPOTS:-"610:144 740:144 1200:82 1440:78 1700:136 2250:150 2760:104 3010:168 3060:86 3330:144 3930:150 4000:104 4560:168 4720:110 4860:144"}
EV="window.__ht=(ex,ey,dx)=>{const s=window.__sheep.game.scene.getScene('Game');s.enemies.clear(true,true);s.eBullets.getChildren().forEach(b=>s.killEnemyBullet(b));s.stream=null;s.spawnIdx=999;const px=ex-dx;s.camMinX=Math.max(0,px-150);const p=s.player;p.facing=1;const gy=s.groundYAt(px)<300?s.groundYAt(px):s.standY(px);p.body.reset(px,gy-1);s.spawn({type:'rifleman',at:ex,y:ey});window.__k0=s.stat.kills;}"
SCRIPT=""
for sp in $SPOTS; do ex=${sp%%:*}; ey=${sp##*:}; for dx in ${DXS:-100 170}; do SCRIPT="$SCRIPT eval:window.__ht($ex,$ey,$dx) wait:100 hold:$KEYS:1500 eval:console.log('[feel]',$ex,$ey,$dx,window.__sheep.game.scene.getScene('Game').stat.kills-window.__k0,Math.round(window.__sheep.game.scene.getScene('Game').player.y))"; done; done
node art/raw/feel/play.mjs --query "god=1&x=100&nointro=1" --eval "$EV" --script "wait:200 $SCRIPT" 2>&1 | grep "\[feel\]" | awk '{printf "rifleman x=%s y=%s  player %s px left (feet y=%s): %s\n",$2,$3,$4,$6,($5>0?"HIT":"miss")}'
