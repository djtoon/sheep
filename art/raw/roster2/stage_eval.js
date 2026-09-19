window.G = () => __sheep.game.scene.getScene('Game');
window.S = (l) => { const g = G(); g.spawnIdx = g.level.spawns.length; g.stream = null; l.forEach(s => g.spawn(s)); };
window.CLR = () => { const g = G(); g.spawnIdx = g.level.spawns.length; g.stream = null; g.enemies.getChildren().slice().forEach(e => e.destroy()); };
window.KILL = () => { const g = G(); g.enemies.getChildren().slice().forEach(e => { if (e.damage) { e.blocks = null; e.damage(999, g.player); } }); };
