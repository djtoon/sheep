// Stage-3 spawn list (game-feel builder). SECRET LAB: the hardest stage, still fair
// (telegraphs, one tell on screen at a time, nothing fires from off screen, nothing spawns on the sheep).
// Each lab creature is introduced ALONE first, then mixed. The walker is the mid-stage set-piece (camera holds).
// Capsules: M early, S before the walker, L mid, S before the final push.
// Surfaces: floor 168; decks 160 (640-1020, 1900-2140, 4080-4220), 158 (3080-3260); grate bridges 163-164 over the
// toxic pools 1020-1200, 2140-2380, 3260-3460, 4220-4440; catwalks 700-930@108, 1320-1570@112, 1660-1780@118,
// 2180-2340@104, 2560-2820@110, 3280-3430@100, 3620-3860@110, 4560-4760@108. Boss at 5360.
// Trigger x = the camera's right edge. y omitted = on the floor at that x.
export const spawns3 = [
  // entry hall: a grunt trickle, then the hazmat alone
  { x: 480, type: 'soldier', count: 2, gap: 900 },
  { x: 480, type: 'stream', every: [900, 1400], left: 0, cap: 3 },
  { x: 560, type: 'hazmat' },
  { x: 760, type: 'hazmat', at: 860, y: 108 },
  // INTRO: xeno, alone - fast, overshoots, 380 ms tell before the pounce
  { x: 960, type: 'stream', off: true },
  { x: 1000, type: 'xeno' },
  { x: 1100, type: 'capsule', y: 60, drop: 'M' },
  { x: 1120, type: 'stream', every: [1100, 1600], left: 0, cap: 2 },
  { x: 1180, type: 'stream', every: [750, 1150], left: 0.15, cap: 4 },
  // INTRO: clawbot, alone - hovers beside you, swoop-grab or slow orb
  { x: 1300, type: 'stream', off: true },
  { x: 1340, type: 'clawbot' },
  { x: 1480, type: 'stream', every: [1100, 1600], left: 0, cap: 2 },
  { x: 1560, type: 'stream', every: [700, 1100], left: 0.2, cap: 4 },
  { x: 1600, type: 'hazmat', at: 1480, y: 112 },
  { x: 1700, type: 'xeno', count: 2, gap: 800, side: 'LR' },
  { x: 1760, type: 'hazmat', at: 1720, y: 118 },
  // INTRO: toxic, alone - a 700 ms pilot flame, then a 78 px cone: keep your distance
  { x: 1880, type: 'stream', off: true },
  { x: 1920, type: 'toxic' },
  { x: 2080, type: 'stream', every: [700, 1100], left: 0.1, cap: 4 },
  { x: 2160, type: 'hazmat' },
  { x: 2200, type: 'clawbot' },
  // S before the hard part
  { x: 2240, type: 'capsule', y: 58, drop: 'S' },
  // INTRO: mutant, alone - slow, 10 HP, close slash
  { x: 2400, type: 'mutant' },
  { x: 2480, type: 'soldier', count: 3, gap: 500, side: 'LR' },
  { x: 2520, type: 'clawbot' },
  { x: 2560, type: 'hazmat', at: 2700, y: 110 },
  { x: 2800, type: 'xeno', count: 2, gap: 600, side: 'LR' },
  // SET-PIECE: the walker. Camera holds at 2560 until it dies (1.3 s red aim line, then a full-width beam)
  { x: 3040, type: 'walker', at: 3020, lock: true, lockAt: 2560, hp: 44, dpsCap: 7 },
  // after the walker: the lab turns on you
  { x: 3120, type: 'stream', every: [500, 850], left: 0.3, cap: 5 },
  { x: 3160, type: 'capsule', y: 60, drop: 'L' },
  { x: 3300, type: 'xeno', count: 2, gap: 700 },
  { x: 3380, type: 'hazmat', at: 3350, y: 100 },
  { x: 3460, type: 'hazmat' },
  { x: 3500, type: 'clawbot' },
  { x: 3560, type: 'hazmat', at: 3740, y: 110 },
  { x: 3640, type: 'xeno', count: 2, gap: 500, side: 'L' },
  { x: 3700, type: 'toxic' },
  { x: 3760, type: 'xeno', count: 2, gap: 500, side: 'LR' },
  { x: 3800, type: 'clawbot' },
  { x: 3880, type: 'hazmat' },
  { x: 3920, type: 'clawbot' },
  { x: 3960, type: 'mutant' },
  // S for the final push
  { x: 4080, type: 'capsule', y: 56, drop: 'S' },
  { x: 4200, type: 'hazmat', at: 4150, y: 160 },
  { x: 4300, type: 'xeno', count: 3, gap: 500, side: 'LR' },
  { x: 4360, type: 'hazmat' },
  { x: 4420, type: 'hazmat', at: 4660, y: 108 },
  { x: 4500, type: 'clawbot' },
  { x: 4580, type: 'xeno', count: 2, gap: 500, side: 'L' },
  { x: 4680, type: 'toxic' },
  { x: 4760, type: 'stream', every: [550, 900], left: 0.3, cap: 5 },
  { x: 4800, type: 'clawbot' },
  { x: 4840, type: 'mutant' },
  { x: 4900, type: 'hazmat' },
  { x: 4960, type: 'xeno', count: 3, gap: 450, side: 'LR' },
  { x: 5060, type: 'hazmat', at: 5100 },
  { x: 5120, type: 'toxic' },
  { x: 5160, type: 'clawbot' },
  { x: 5240, type: 'mutant' },
  // (the stream stops by itself when the boss appears)
];
spawns3.gunnersFrom = 0;
spawns3.shotGap = 150;     // quiet gap after a stage-1-type enemy's tell+shot (stage 1: 350)
spawns3.gunnerBias = 0.55; // extra share of stream grunts that stop and shoot
