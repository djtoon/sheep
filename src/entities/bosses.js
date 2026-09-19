// Boss registry: level.boss.type -> class with the BossWall interface: new B(scene, x); update(time); calls scene.bossDefeated().
import { BossWall } from './Boss.js';
import { Boss2 } from './Boss2.js';
import { Boss3 } from './Boss3.js';
export const BOSSES = { wall: BossWall, base: Boss2, lab: Boss3 };
