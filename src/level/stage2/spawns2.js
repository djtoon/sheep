// Stage-2 spawn list (game-feel builder). NIGHT RAID: harder than stage 1, same fairness rules
// (telegraphs, one tell on screen at a time, nothing fires from off screen, nothing spawns on the sheep).
// Each new roster enemy is introduced ALONE first (stream paused), then mixed in. The mech is a mid-stage set-piece
// (camera holds until it dies). Capsules: M early, S before the mech, S again before the final push.
// Surfaces: floor 168; tiers 146 (900-1180, 2200-2500, 3700-3950); catwalks ~102-106 (300-560, 1210-1382,
// 1760-2020, 2560-2820, 3260-3520, 4050-4310); bridged pits 1420-1640, 3000-3200, 4600-4780. Boss at 5360.
// Trigger x = the camera's right edge. y omitted = on the floor at that x.
export const spawns2 = [
  // BEAT 1 - perimeter road: a grunt trickle and a rifleman on the scaffold to warm up
  { x: 480, type: 'soldier', count: 2, gap: 900 },
  { x: 480, type: 'stream', every: [800, 1300], left: 0, cap: 3 },
  { x: 620, type: 'rifleman', at: 470, y: 106 },
  // INTRO: trooper, alone (stream paused) - learn the 3-way shotgun fan
  { x: 800, type: 'stream', off: true },
  { x: 860, type: 'trooper' },
  { x: 1060, type: 'stream', every: [1100, 1600], left: 0, cap: 2 },
  { x: 1100, type: 'capsule', y: 60, drop: 'M' },
  { x: 1180, type: 'stream', every: [700, 1100], left: 0.1, cap: 4 },
  { x: 1260, type: 'rifleman', at: 1330, y: 104 },
  { x: 1400, type: 'trooper', side: 'L' },
  { x: 1480, type: 'trooper' },
  { x: 1520, type: 'soldier', count: 2, gap: 500 },
  { x: 1580, type: 'drone' },
  // INTRO: shield, alone - shoot it from the scaffold above, jump-shoot, or get behind it
  { x: 1660, type: 'stream', off: true },
  { x: 1720, type: 'shield' },
  { x: 1900, type: 'stream', every: [1100, 1600], left: 0, cap: 2 },
  { x: 2000, type: 'stream', every: [650, 1000], left: 0.2, cap: 4 },
  { x: 2060, type: 'trooper' },
  // INTRO: sniper, alone, on the bunker roof tier (22 px up: a level shot kills it) - see the red line, get off it
  { x: 2140, type: 'stream', off: true },
  { x: 2160, type: 'sniper', at: 2420, y: 146 },
  { x: 2300, type: 'stream', every: [1100, 1600], left: 0, cap: 2 },   // (paused by the mech set-piece)
  { x: 2340, type: 'drone' },
  // S before the hard part
  { x: 2380, type: 'capsule', y: 58, drop: 'S' },
  { x: 2560, type: 'rifleman', at: 2700, y: 104 },
  { x: 2600, type: 'trooper' },
  { x: 2760, type: 'soldier', count: 2, gap: 600 },
  // SET-PIECE: the gatling mech. Camera holds at 2520 until it dies (high stream: prone, low stream: jump)
  { x: 2960, type: 'mech', at: 2950, lock: true, lockAt: 2480, hp: 44, dpsCap: 7 },
  // after the mech: a short breather, then the stream returns harder
  { x: 3100, type: 'stream', every: [600, 950], left: 0.25, cap: 5 },
  // INTRO: drone2 - its 3-round burst follows one locked line; then a trooper and a sniper join
  { x: 3260, type: 'drone2' },
  { x: 3420, type: 'trooper' },
  { x: 3440, type: 'soldier', count: 4, gap: 400, side: 'LR' },
  { x: 3480, type: 'sniper', at: 3440, y: 102 },
  // INTRO: tank - twin level shells at chest height: prone under them or jump
  { x: 3600, type: 'stream', off: true },
  { x: 3640, type: 'tank' },
  { x: 3760, type: 'drone2' },
  { x: 3820, type: 'stream', every: [600, 950], left: 0.25, cap: 5 },
  { x: 3860, type: 'trooper', side: 'L' },
  { x: 3900, type: 'sniper', at: 3930, y: 146 },
  // MIX: trooper + shield push under a drone2, sniper on the catwalk above, then S for the final push
  { x: 3980, type: 'soldier', count: 4, gap: 400, side: 'LR' },
  { x: 4000, type: 'trooper' },
  { x: 4080, type: 'shield' },
  { x: 4120, type: 'drone2' },
  { x: 4200, type: 'sniper', at: 4260, y: 104 },
  { x: 4300, type: 'capsule', y: 56, drop: 'S' },
  { x: 4460, type: 'tank' },
  { x: 4520, type: 'soldier', count: 3, gap: 450, side: 'LR' },
  { x: 4600, type: 'trooper', side: 'L' },
  { x: 4700, type: 'drone2' },
  { x: 4760, type: 'stream', every: [650, 1000], left: 0.2, cap: 5 },
  { x: 4860, type: 'trooper' },
  { x: 4920, type: 'sniper', at: 4990 },
  { x: 5000, type: 'shield' },
  { x: 5080, type: 'rifleman', at: 5120 },
  { x: 5100, type: 'drone2' },
  { x: 5160, type: 'soldier', count: 3, gap: 400 },
  { x: 5240, type: 'trooper' },
  { x: 5280, type: 'tank' },
  // (the stream stops by itself when the boss appears)
];
spawns2.gunnersFrom = 0;   // stage 2: grunts may stop and shoot from the start
spawns2.shotGap = 350;     // quiet gap after a stage-1-type enemy's tell+shot (stage 1: 350)
spawns2.gunnerBias = 0.1; // extra share of stream grunts that stop and shoot
