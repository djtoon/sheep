// cohesion pass: drive the real-time game with the feel builder's bot (art/raw/feel/bot.js) once per game step
window.__sheep.inject = { left: false, right: false, up: false, down: false, jump: false, fire: false, start: false };
window.__frame = 0;
window.__sheep.game.events.on('prestep', () => { window.__frame++; if (window.__bot) window.__bot(); });
window.__objs = () => {
  const g = window.__sheep.game, s = g.scene.getScene('Game'), h = g.scene.getScene('HUD');
  if (!s || !s.sys.isActive()) return 'scenes=' + g.scene.getScenes(true).map(x => x.scene.key).join('+');
  const st = window.__sheep.stats();
  return ['fps=' + st.fps, 'cam=' + st.cam, 'flow=' + st.flow, 'lives=' + st.player.lives, 'boss=' + st.boss,
    'objs=' + s.children.list.length, 'hudObjs=' + h.children.list.length, 'tweens=' + s.tweens.getTweens().length,
    'timers=' + s.time._active.length, 'bodies=' + s.physics.world.bodies.size, 'static=' + s.physics.world.staticBodies.size,
    'enemies=' + s.enemies.getLength(), 'tex=' + Object.keys(g.textures.list).length, 'anims=' + g.anims.anims.size,
    'heapMB=' + (performance.memory ? Math.round(performance.memory.usedJSHeapSize / 1048576) : -1)].join(' ');
};
