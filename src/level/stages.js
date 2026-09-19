// Stage registry. Each stage module is owned by its builder; Game looks stages up by number.
import { stage1 } from './stage1.js';
import { stage2 } from './stage2/stage2.js';
import { stage3 } from './stage3/stage3.js';
export const STAGES = { 1: stage1, 2: stage2, 3: stage3 };
