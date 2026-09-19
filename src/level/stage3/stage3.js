// STAGE 03 - UNDERGROUND SECRET LAB (SUB-LEVEL B, SECTOR 3). Geometry + set dressing; rendered by View3.
// ground: solid blocks from y down. platforms: one-way. Steps between neighbours are <=10px (walk) or <=26px (vault).
// Toxic pools (water) sit in the gaps under steel grate bridges that hang <=6px below both lips.
import { spawns3 } from './spawns3.js';

export const stage3 = {
  name: 'STAGE 03',
  subtitle: 'SECRET LAB',
  theme: 'lab', gruntSkin: 'grunt3',   // stream grunts reskinned to the lab roster (Enemies.js gruntTex)
  width: 5600,
  height: 270,
  ground: [
    { x: 0, w: 640, y: 168, style: 'lab' },          // entry hall: rock wall, SUB-LEVEL B sign, specimen tanks
    { x: 640, w: 380, y: 160, style: 'lab' },        // raised deck (8px step) under the first mezzanine
    // toxic pool 1: 1020-1200, grate bridge
    { x: 1200, w: 700, y: 168, style: 'lab' },       // terminal room
    { x: 1900, w: 240, y: 160, style: 'lab' },
    // toxic pool 2: 2140-2380, grate bridge + upper catwalk
    { x: 2380, w: 700, y: 168, style: 'lab' },       // specimen window hall
    { x: 3080, w: 180, y: 158, style: 'lab' },
    // toxic pool 3: 3260-3460
    { x: 3460, w: 620, y: 168, style: 'lab' },       // tank gallery 2
    { x: 4080, w: 140, y: 160, style: 'lab' },
    // toxic pool 4: 4220-4440
    { x: 4440, w: 1160, y: 168, style: 'lab' },      // LAB 07 blast door + boss arena (flat 5020-5600)
  ],
  platforms: [
    { x: 700, w: 230, y: 108, style: 'catwalk' },   // mezzanine 1 (ladder at 900)
    { x: 1020, w: 180, y: 164, style: 'grate' },     // bridge over pool 1 (lips 160 / 168)
    { x: 1320, w: 250, y: 112, style: 'catwalk' },   // terminal-room mezzanine
    { x: 1660, w: 120, y: 118, style: 'catwalk' },
    { x: 2140, w: 240, y: 164, style: 'grate' },     // bridge over pool 2 (lips 160 / 168)
    { x: 2180, w: 160, y: 104, style: 'catwalk' },   // upper crossing over pool 2
    { x: 2560, w: 260, y: 110, style: 'catwalk' },   // window hall mezzanine
    { x: 3260, w: 200, y: 163, style: 'grate' },     // bridge over pool 3 (lips 158 / 168)
    { x: 3280, w: 150, y: 100, style: 'catwalk' },
    { x: 3620, w: 240, y: 110, style: 'catwalk' },
    { x: 4220, w: 220, y: 164, style: 'grate' },     // bridge over pool 4 (lips 160 / 168)
    { x: 4560, w: 200, y: 108, style: 'catwalk' },   // mezzanine before the blast door
  ],
  // set dressing drawn by View3 (visual only). x = left edge in world px; y = floor line (defaults to ground at x).
  // Landmarks (one large lit set piece per screen width, alternating): tankpair / door / dnabank / window.
  decor: [
    { k: 'rock', x: 0 }, { k: 'sign', x: 30 },
    { k: 'tankpair', x: 150 }, { k: 'crates', x: 330 }, { k: 'dnabank', x: 470 },
    { k: 'ladder', x: 900, top: 108 }, { k: 'crate', x: 760, y: 108 }, { k: 'door', x: 872, label: 'LAB 03' },
    { k: 'crates', x: 1210 }, { k: 'tankpair', x: 1380 }, { k: 'ladder', x: 1540, top: 112 }, { k: 'crate', x: 1690, y: 118 },
    { k: 'dnabank', x: 1760 }, { k: 'crates', x: 2020 },
    { k: 'crates', x: 2390 }, { k: 'window', x: 2440 }, { k: 'ladder', x: 2790, top: 110 }, { k: 'crate', x: 2600, y: 110 }, { k: 'crates', x: 2860 },
    { k: 'door', x: 2930, label: 'LAB 05' }, { k: 'sign', x: 3090 },
    { k: 'tankpair', x: 3490 }, { k: 'crates', x: 3660 }, { k: 'ladder', x: 3830, top: 110 },
    { k: 'dnabank', x: 3900 }, { k: 'crates', x: 4480 },
    { k: 'ladder', x: 4730, top: 108 }, { k: 'door', x: 4790, label: 'LAB 07' }, { k: 'crates', x: 4930 },
    { k: 'tankpair', x: 5040 }, { k: 'window', x: 5260 }, { k: 'rock', x: 5540 },
  ],
  water: [{ x: 1020, w: 180 }, { x: 2140, w: 240 }, { x: 3260, w: 200 }, { x: 4220, w: 220 }],
  spawns: spawns3,
  boss: { x: 5360, type: 'lab' },
};
