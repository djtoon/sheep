#!/bin/bash
# re-generations: a clearly fictional President (no real-person likeness), and a sheep-free enemy map panel
T=ref/2f3330c3-2919-4954-83e8-50b26fc47907.png; H=ref/3c485156-1ab2-4472-a273-76e378d5eb05.png
STY="16-bit pixel art ACTION COMIC BOOK PANEL in exactly the style of the reference title screen: chunky crisp pixels, bold black comic ink outlines, halftone dot shading in the shadows, saturated colours, dramatic cinematic lighting. Full-bleed illustration, NO text, NO letters, NO speech balloons, NO captions, NO panel border, NO frame."
SHEEP="the commando sheep hero from the character sheet (fluffy cream wool body, grey face and ears, big round white eyes with black pupils, angry eyebrows, red headband with long trailing tails, golden bullet bandolier across the wool, black assault rifle)"
PRES="an invented cartoon President character: a stocky BALD man with a huge bushy grey walrus moustache, thick black eyebrows and round wire glasses, dark navy suit with a red tie (NOT resembling any real person)"
g(){ node tools/gen.mjs --out art/raw/story/$1.png $REFS --aspect $2 --quality high --bg opaque --n 2 --prompt "$STY $3" > art/raw/story/log_$1.txt 2>&1 & }
REFS="--ref $T"
g p1 3:2  "Night. Inside the Oval Office: $PRES stands at a big wooden desk gripping a glowing RED telephone to his ear, alarmed. Tall windows behind him with rain and lightning, flags, an eagle seal on the carpet, warm lamp light versus blue storm light."
g p2 1:1  "Extreme close-up of $PRES shouting urgently into a red telephone handset, sweat on his bald head, face lit red from below, speed lines behind him, dramatic comic close-up."
g p3 16:9 "A glowing military situation-room wall screen showing a satellite map of a dense jungle with a hidden enemy fortress and a secret laboratory dome, red target markers, and on the side screens red banners with a black eagle emblem. Empty dark room, silhouettes of human generals in the foreground. NO sheep, NO animals."
REFS="--ref $T --ref $H"
g e3 3:2  "On the White House lawn with flags: $PRES pins a shining gold medal on the chest of $SHEEP, who stands at attention saluting proudly, confetti, warm golden light."
wait
