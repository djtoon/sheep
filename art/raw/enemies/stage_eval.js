window.S = (list) => { const g = window.__sheep.game.scene.getScene('Game'); for (const s of list) g.spawn(s); };
window.K = () => { const g = window.__sheep.game.scene.getScene('Game'); g.enemies.getChildren().slice().forEach(e => { if (e.damage && !(e.texture.key === 'turret')) e.damage(99, g.player); }); };
