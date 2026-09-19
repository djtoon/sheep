// Contra weapon set (targets + reasoning: art/raw/feel/targets.md).
//   rate  = min ms between shots (mash cap)      hold = ms between shots while the button is held (auto fire)
//   speed = px/s     max = player bullets alive on screen for this gun (Contra's on-screen cap; HUD pips read it)
//   spread = fan angles in radians (one bullet each)
export const WEAPONS = {
  R: { name: 'RIFLE', tex: 'bullet-player', rate: 130, hold: 190, auto: true, speed: 380, dmg: 1, spread: [0], max: 4 },
  M: { name: 'MACHINE GUN', tex: 'bullet-player', rate: 85, hold: 85, auto: true, speed: 420, dmg: 1, spread: [0], max: 10 },
  S: { name: 'SPREAD', tex: 'bullet-spread', rate: 170, hold: 170, auto: true, speed: 360, dmg: 1, spread: [-0.36, -0.18, 0, 0.18, 0.36], max: 20 },
  L: { name: 'LASER', tex: 'bullet-laser', rate: 280, hold: 280, auto: true, speed: 560, dmg: 3, spread: [0], max: 2, pierce: true },
};
