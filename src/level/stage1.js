// STAGE 01 - JUNGLE. Pure data; Game.js builds physics from it and the level renderer dresses it.
// ground: solid blocks from y down to the bottom of the world. platforms: one-way (jump up through, drop with down+jump).
// spawns trigger when the camera's right edge passes x. y omitted = on the ground at that x.
export const stage1 = {
  name: 'STAGE 01',
  width: 5600,
  height: 270,
  ground: [
    { x: 0, w: 560, y: 168, style: 'jungle' },
    { x: 560, w: 220, y: 144, style: 'jungle' },      // rise to the falls
    // chasm 1: 780-1060, rope bridge over the basin
    { x: 1060, w: 240, y: 144, style: 'jungle' },
    { x: 1300, w: 260, y: 168, style: 'jungle' },
    { x: 1560, w: 360, y: 136, style: 'jungle' },     // raised cliff
    { x: 1920, w: 260, y: 168, style: 'jungle' },
    { x: 2180, w: 120, y: 150, style: 'jungle' },
    // chasm 2: 2300-2600, steel girder bridge
    { x: 2600, w: 300, y: 150, style: 'jungle' },
    { x: 2900, w: 360, y: 168, style: 'jungle' },
    { x: 3260, w: 220, y: 144, style: 'jungle' },
    // chasm 3: 3480-3700, steel bridge into the base
    { x: 3700, w: 260, y: 150, style: 'base' },        // enemy base: concrete slab on rock
    // chasm 4: 3960-4200, girder span
    { x: 4200, w: 130, y: 154, style: 'jungle' },      // jungle reclaiming a shelf past the chasm
    { x: 4330, w: 400, y: 168, style: 'base' },
    { x: 4730, w: 170, y: 144, style: 'jungle' },      // overgrown rise
    { x: 4900, w: 700, y: 168, style: 'base' },        // boss yard
  ],
  platforms: [
    { x: 250, w: 110, y: 114, style: 'ledge' },
    { x: 780, w: 280, y: 153, style: 'rope' },        // rope bridge hangs 9px below both lips (step-up <=10px)
    // stacked tiers over the falls: outcrop + upper rope bridge + raised cliff shelf (ladder, bunker door)
    { x: 700, w: 76, y: 104, style: 'ledge' },
    { x: 836, w: 160, y: 74, style: 'ledge' },       // upper rock ledge over the falls (one bridge per screen)
    { x: 1046, w: 214, y: 82, style: 'ledge' },      // raised cliff shelf (bunker door, ladder)
    { x: 1400, w: 100, y: 78, style: 'ledge' },
    { x: 2300, w: 300, y: 150, style: 'steel' },      // steel bridge
    { x: 2236, w: 100, y: 78, style: 'ledge' },      // upper crossing over chasm 2: posts sunk into both ledges
    { x: 2336, w: 186, y: 78, style: 'rope' },
    { x: 2522, w: 104, y: 78, style: 'ledge' },
    { x: 2700, w: 140, y: 104, style: 'ledge' },
    { x: 2980, w: 160, y: 86, style: 'ledge' },
    { x: 3480, w: 220, y: 147, style: 'steel' },
    { x: 3530, w: 110, y: 92, style: 'catwalk' },    // upper deck over chasm 3
    { x: 3960, w: 240, y: 152, style: 'steel' },      // girder span over the base chasm
    { x: 3900, w: 180, y: 104, style: 'catwalk' },
    { x: 4300, w: 200, y: 94, style: 'catwalk' },
    { x: 4650, w: 160, y: 110, style: 'catwalk' },
  ],
  // set dressing drawn by LevelView (visual only). k = art piece in assets/terrain; x = left edge;
  // y = ground line it stands on (defaults to ground at x); layer 'back' = drawn behind the ground/grass.
  decor: [
    // jungle start: supply dump
    { k: 'crates2', x: 6 }, { k: 'crate-eagle', x: 40 }, { k: 'crate', x: 66 }, { k: 'sandbags', x: 150 },
    { k: 'ammo', x: 330 }, { k: 'drum', x: 400 }, { k: 'drum', x: 414 }, { k: 'crate', x: 600 }, { k: 'sandbags', x: 470 },
    { k: 'tower', x: 700, layer: 'back' }, { k: 'banner', x: 698, top: 80 },
    // across the rope bridge
    { k: 'tower', x: 960, y: 74 }, { k: 'banner', x: 842, top: 80 }, { k: 'door-eagle', x: 1150, y: 82, layer: 'back' }, { k: 'banner', x: 1216, top: 28, layer: 'back' }, { k: 'ladder', x: 1244, y: 82 },
    { k: 'crates2', x: 1120, y: 82 }, { k: 'ladder', x: 2250, y: 78 },
    { k: 'crate', x: 1100 }, { k: 'ammo', x: 1250 }, { k: 'crate-eagle', x: 1500 },
    { k: 'sandbags', x: 1600, y: 136 }, { k: 'tower2', x: 1720, y: 136, layer: 'back' }, { k: 'banner', x: 1716, top: 24 }, { k: 'crates2', x: 1770, y: 136 },
    { k: 'drum', x: 1950 }, { k: 'crate', x: 1968 }, { k: 'sandbags', x: 2080 }, { k: 'ammo', x: 2220 },
    // after the first steel bridge: military presence grows
    { k: 'crate-eagle', x: 2640 }, { k: 'crate', x: 2670 }, { k: 'fence', x: 2880, n: 3, layer: 'back' }, { k: 'sandbags', x: 2900 },
    { k: 'drum', x: 3080 }, { k: 'ammo', x: 3160 }, { k: 'crates2', x: 3290, y: 144 }, { k: 'tower', x: 3400, y: 144, layer: 'back' }, { k: 'banner', x: 3398, top: 72 },
    // enemy base
    // far bank of the base chasm: a concrete dam with a fenced, sandbagged deck and the A-01 door
    { k: 'fence', x: 3720, n: 1, y: 150, sign: -1, layer: 'back' }, { k: 'sandbags', x: 3790, y: 150, layer: 'back' },
    // midground combat dressing behind/under the catwalk: chain fence with the A-01 sign, sandbag emplacement,
    // stacked crates, a searchlight post, a watchtower on the dam, warm lamp pools
    { k: 'fence', x: 3845, n: 2, y: 150, sign: 1, layer: 'back' },
    { k: 'crates2', x: 3905, y: 150, layer: 'back' }, { k: 'crate', x: 3935, y: 150, layer: 'back' },
    { k: 'searchlight', x: 3952, y: 150, h: 64, layer: 'back' },
    { k: 'lamppool', x: 3941, y: 128, r: 30 }, { k: 'lamppool', x: 3775, y: 118, r: 36 }, { k: 'lamppool', x: 4072, y: 150, r: 30 },
    { k: 'bunker', x: 3724, sink: 34, layer: 'back' }, { k: 'banner', x: 3872, top: 86 }, { k: 'lamp2', x: 3800, top: 112 }, { k: 'lamppool', x: 3806, y: 132, r: 40 }, { k: 'lamp', x: 3940, top: 104, layer: 'back' },
    { k: 'ladder', x: 3886, y: 104 }, { k: 'sandbags', x: 3860 }, { k: 'drum', x: 3700 },
    { k: 'crate-eagle', x: 4250 }, { k: 'drum', x: 4214 }, { k: 'drum', x: 4228 }, { k: 'ladder', x: 4290, y: 94 },
    { k: 'wall', x: 4340, w: 170, h: 44, layer: 'back' }, { k: 'crates2', x: 4362 }, { k: 'sandbags', x: 4430 },
    { k: 'bunker2', x: 4520, sink: 30, layer: 'back' }, { k: 'banner', x: 4540, top: 90, layer: 'back' }, { k: 'banner', x: 4668, top: 90, layer: 'back' },
    { k: 'ammo', x: 4560 }, { k: 'crate', x: 4690 },
    { k: 'fence', x: 4750, n: 2, y: 144, layer: 'back' }, { k: 'drum', x: 4870, y: 144 },
    { k: 'wall', x: 4930, w: 420, h: 62, layer: 'back' }, { k: 'bigdoor', x: 4960, layer: 'back' }, { k: 'banner', x: 5160, top: 110, layer: 'back' }, { k: 'banner', x: 5000, top: 50, layer: 'back' }, { k: 'crates2', x: 5100 }, { k: 'ammo', x: 5140 },
    { k: 'tower2', x: 5210, layer: 'back' }, { k: 'lamp2', x: 5236, top: 104, layer: 'back' },
  ],
  water: [{ x: 780, w: 280 }, { x: 2300, w: 300 }, { x: 3480, w: 220 }, { x: 3960, w: 240 }],
  // spawns trigger when the camera's right edge passes x (feel builder owns this list; pacing notes in art/raw/feel/targets.md).
  //   soldier: count/gap waves from the right edge, side 'L' | 'R' | 'LR' (alternating); at = fixed x (ledge riflemen etc.)
  //   stream: ambient grunts trickling in from both edges every [min,max] ms (cap = max grunts alive); {off:true} = breather
  spawns: [
    // Round 2 density pass: stage 1 must let a first-timer reach the base with lives to spare.
    // No grunts from behind until x 2000; one shooter at a time in the first half; every shooter is killable by a
    // level shot (<= 32 px step) or a walking diagonal (ledges >= 60 px up). Nothing stands on a 46 px ledge.
    // BEAT 1 - landing zone: a gentle trickle from the right, first rifleman on the rise, M capsule over the falls
    { x: 480, type: 'soldier', count: 2, gap: 1000 },
    { x: 480, type: 'stream', every: [650, 1050], left: 0, cap: 3 },
    { x: 560, type: 'soldier', count: 2, gap: 800 },
    { x: 640, type: 'rifleman', at: 610, y: 144 },
    { x: 860, type: 'capsule', y: 64, drop: 'M' },
    // BEAT 2 - the falls: one rifleman up on the shelf, a wave from ahead
    { x: 1000, type: 'rifleman', at: 1200, y: 82 },
    { x: 1080, type: 'soldier', count: 3, gap: 560 },
    { x: 1150, type: 'stream', every: [550, 900], left: 0, cap: 3 },
    { x: 1360, type: 'rifleman', at: 1440, y: 78 },
    // breather before the cliff
    { x: 1500, type: 'stream', off: true },
    // BEAT 3 - cliff turret (level shot from the cliff top), a lone drone, then a spike
    { x: 1640, type: 'turret', at: 1880, y: 136 },
    { x: 1760, type: 'rifleman', at: 1700, y: 136 },
    { x: 1800, type: 'stream', every: [700, 1100], left: 0, cap: 3 },
    { x: 1900, type: 'drone', count: 1 },
    { x: 2040, type: 'stream', every: [650, 1050], left: 0.15, cap: 3 },
    { x: 2100, type: 'soldier', count: 3, gap: 480 },
    { x: 2220, type: 'rifleman', at: 2250, y: 150 },
    { x: 2280, type: 'drone', count: 1 },
    // S capsule, with the stream off so you can grab it and then enjoy it on the next wave
    { x: 2300, type: 'stream', every: [900, 1350], left: 0, cap: 2 },   // S capsule: calm, not empty
    { x: 2320, type: 'capsule', y: 60, drop: 'S' },
    { x: 2460, type: 'drone', count: 1 },
    { x: 2580, type: 'soldier', count: 4, gap: 420, side: 'R' },
    { x: 2640, type: 'stream', every: [700, 1100], left: 0, cap: 3 },
    // BEAT 4 - open ground: stream + one sniper up on the rock shelf + turret on the rise
    { x: 2900, type: 'stream', every: [650, 1050], left: 0.2, cap: 4 },
    { x: 3050, type: 'rifleman', at: 3060, y: 86 },
    { x: 3300, type: 'turret', at: 3440, y: 144 },
    { x: 3380, type: 'rifleman', at: 3330, y: 144 },
    { x: 3440, type: 'drone', count: 1 },
    { x: 3460, type: 'stream', every: [750, 1200], left: 0, cap: 2 },   // bridge into the base: a lone grunt at a time
    // BEAT 5 - into the base: drone pair, L capsule, a pincer on the slab
    { x: 3560, type: 'drone', count: 2, gap: 800 },
    { x: 3660, type: 'capsule', y: 64, drop: 'L' },
    { x: 3760, type: 'stream', every: [550, 900], left: 0.25, cap: 4 },
    { x: 3800, type: 'soldier', count: 3, gap: 420, side: 'LR' },
    { x: 3900, type: 'rifleman', at: 3930, y: 150 },
    { x: 4250, type: 'turret', at: 4400, y: 94 },
    // last capsule (S again) right before the final gauntlet, so a dead player re-arms for the boss
    { x: 4300, type: 'capsule', y: 58, drop: 'S' },
    { x: 4420, type: 'soldier', count: 4, gap: 380, side: 'R' },
    { x: 4540, type: 'drone', count: 1 },
    { x: 4580, type: 'soldier', count: 1, side: 'L' },
    { x: 4640, type: 'rifleman', at: 4610 },
    { x: 4700, type: 'rifleman', at: 4720, y: 110 },
    // FINAL PUSH - the build-up peaks straight into the WARNING: stream thickens, both catwalk riflemen, drones, a last wave
    { x: 4720, type: 'stream', every: [550, 900], left: 0.2, cap: 4 },
    { x: 4800, type: 'drone', count: 2, gap: 900 },
    { x: 4840, type: 'rifleman', at: 4790, y: 110 },
    { x: 4900, type: 'rifleman', at: 4860, y: 144 },
    { x: 5000, type: 'soldier', count: 4, gap: 420, side: 'R' },
    { x: 5100, type: 'rifleman', at: 5140 },
    { x: 5200, type: 'drone', count: 1 },
    { x: 5260, type: 'soldier', count: 3, gap: 400, side: 'R' },
    // (the stream stops by itself when the boss appears at camera right >= 5460)
  ],
  boss: { x: 5360, type: 'wall' },
};
