// View registry: level.theme -> renderer class (backdrop + terrain). Each stage builder owns its own view module.
import { LevelView } from './LevelView.js';
import { View2 } from './stage2/View2.js';
import { View3 } from './stage3/View3.js';
const VIEWS = { jungle: LevelView, base: View2, lab: View3 };
export function makeView(scene, level) { const V = VIEWS[level.theme || 'jungle'] || LevelView; return new V(scene, level); }
