// Enemy registry: spawn 'type' -> class. Stage 1 types live in Enemies.js; each new roster module is owned by its builder.
import { ENEMY_TYPES } from './Enemies.js';
import { ROSTER2 } from './roster2.js';
import { ROSTER3 } from './roster3.js';
export const TYPES = { ...ENEMY_TYPES, ...ROSTER2, ...ROSTER3 };
