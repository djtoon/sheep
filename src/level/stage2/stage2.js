// STAGE 02 - NIGHT BASE (B-02). Pure data; Game.js builds physics from it and View2 dresses it.
// ground: solid blocks from y down (walk plane y=168, ~62% down the screen). platforms: one-way (scaffold catwalks, pit bridges).
// Steps between ground blocks are <=24px (vaultable); every pit is fully spanned by a bridge within 0px of both lips.
import { spawns2 } from './spawns2.js';

export const stage2 = {
  name: 'STAGE 02',
  subtitle: 'NIGHT RAID',
  theme: 'base', gruntSkin: 'grunt2',   // stream grunts reskinned to the night-base roster (Enemies.js gruntTex)
  width: 5600,
  height: 270,
  ground: [
    { x: 0, w: 900, y: 168 },            // perimeter road, fence line + lamp posts
    { x: 900, w: 280, y: 146 },          // loading dock (vault up 22)
    { x: 1180, w: 240, y: 168 },
    // pit 1: 1420-1640 (drainage shaft, bridged)
    { x: 1640, w: 560, y: 168 },
    { x: 2200, w: 300, y: 146 },         // bunker roof tier
    { x: 2500, w: 500, y: 168 },
    // pit 2: 3000-3200
    { x: 3200, w: 500, y: 168 },
    { x: 3700, w: 250, y: 146 },         // gun emplacement tier
    { x: 3950, w: 650, y: 168 },
    // pit 3: 4600-4780
    { x: 4780, w: 820, y: 168 },         // approach + boss arena (flat from 5000)
  ],
  platforms: [
    { x: 300, w: 260, y: 106, style: 'scaffold' },
    { x: 1210, w: 172, y: 104, style: 'scaffold' },
    { x: 1420, w: 220, y: 168, style: 'bridge' },
    { x: 1760, w: 260, y: 102, style: 'scaffold' },
    { x: 2560, w: 260, y: 104, style: 'scaffold' },
    { x: 3000, w: 200, y: 168, style: 'bridge' },
    { x: 3260, w: 260, y: 102, style: 'scaffold' },
    { x: 4050, w: 260, y: 104, style: 'scaffold' },
    { x: 4600, w: 180, y: 168, style: 'bridge' },
  ],
  pits: [{ x: 1420, w: 220 }, { x: 3000, w: 200 }, { x: 4600, w: 180 }],
  water: [],
  // set dressing drawn by View2. k = prop key, x = left edge, y = ground it stands on (default: ground at x),
  // layer: 'back' (behind the floor lip, dimmed a step) or default (in front of the fence line, full value)
  decor: [
    { k: 'fence', x: 0, n: 16, layer: 'back' },
    { k: 'lamp', x: 60, layer: 'back' }, { k: 'lamp', x: 420, layer: 'back' }, { k: 'lamp', x: 760, layer: 'back' },
    { k: 'crates2', x: 20 }, { k: 'crate', x: 70 }, { k: 'drums', x: 190 }, { k: 'crate', x: 600 }, { k: 'drum', x: 640 },
    { k: 'watchtower', x: 820, layer: 'back' },
    { k: 'crates2', x: 930, y: 146 }, { k: 'drums', x: 1080, y: 146 },
    { k: 'lamp', x: 1250, layer: 'back' }, { k: 'crate', x: 1300 },
    { k: 'radar', x: 1700, layer: 'back' }, { k: 'fence', x: 1640, n: 10, layer: 'back' },
    { k: 'crates2', x: 1680 }, { k: 'drum', x: 2090 }, { k: 'lamp', x: 1960, layer: 'back' },
    { k: 'crate', x: 2260, y: 146 }, { k: 'searchlight', x: 2330, y: 146 }, { k: 'drums', x: 2400, y: 146 },
    { k: 'watchtower', x: 2520, layer: 'back' }, { k: 'fence', x: 2500, n: 8, layer: 'back' }, { k: 'lamp', x: 2880, layer: 'back' },
    { k: 'crates2', x: 2860 }, { k: 'drum', x: 2940 },
    { k: 'fence', x: 3200, n: 8, layer: 'back' }, { k: 'lamp', x: 3240, layer: 'back' }, { k: 'radar', x: 3580, layer: 'back' },
    { k: 'crate', x: 3230 }, { k: 'crates2', x: 3600 },
    { k: 'drums', x: 3760, y: 146 }, { k: 'searchlight', x: 3830, y: 146 }, { k: 'crate', x: 3880, y: 146 },
    { k: 'fence', x: 3950, n: 11, layer: 'back' }, { k: 'lamp', x: 4000, layer: 'back' }, { k: 'watchtower', x: 4380, layer: 'back' },
    { k: 'crates2', x: 4420 }, { k: 'drum', x: 4540 }, { k: 'lamp', x: 4500, layer: 'back' },
    { k: 'crate', x: 4800 }, { k: 'drums', x: 4880 }, { k: 'lamp', x: 4960, layer: 'back' },
    { k: 'fortress', x: 5080, layer: 'back' },
  ],
  spawns: spawns2,
  boss: { x: 5360, type: 'base' },
};
