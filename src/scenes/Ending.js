// Mission-complete ending after stage 3's results: a comic epilogue page, then THE END and a credits roll
// over the final score (data.score), then back to the Title.  Enter/X/Z advance; Esc skips.
import { ComicPlayer } from '../fx/comic.js';
import { Music } from '../audio/Music.js';
import { Sfx } from '../audio/Sfx.js';

export const ENDING_PAGES = [
  [
    { id: 'e1', x: 6, y: 6, w: 468, h: 128, pan: [24, 0], from: 'top', beats: [
      { t: 'sfx', s: 'KA-BOOOOM!!', x: 300, y: 30, font: 'hud-sfx-red', snd: 'boom-big' },
      { t: 'cap', s: 'THE SECRET LAB IS NO MORE.', x: 4, y: 110 } ] },
    { id: 'e2', x: 6, y: 140, w: 230, h: 124, pan: [-16, 0], from: 'left', loop: 'rotor', beats: [
      { t: 'cap', s: 'EXTRACTION.  0700 HOURS.', x: 4, y: 4 },
      { t: 'say', s: 'MISSION\nCOMPLETE.', x: 54, y: 60, tail: [96, 50] } ] },
    { id: 'e3', x: 242, y: 140, w: 232, h: 124, pan: [0, 0], from: 'right', beats: [
      { t: 'say', s: 'THE NATION\nTHANKS YOU,\nSOLDIER!', x: 196, y: 6, tail: [170, 40] },
      { t: 'say', s: 'BAAA!', x: 40, y: 8, tail: [60, 34] } ] },
  ],
];

export class Ending extends Phaser.Scene {
  constructor() { super('Ending'); }
  init(data) {
    this.score = (data && data.score) || +(window.__sheep.query.get('score') || 0) || (window.__sheep.results && window.__sheep.results.score) || 0;
    this.embers = null; this.roll = null; this.acc = 0;
  }
  create() {
    this.cameras.main.setBackgroundColor('#07080c'); this.cameras.main.fadeIn(400, 0, 0, 0);
    this.leaving = false; this.rolling = false;
    this.sfx = new Sfx(this);
    Music.play(this, 'ending');
    const q = window.__sheep.query;
    if (q.get('credits') === '1') this.theEnd();                     // test hook: jump straight to THE END
    else this.comic = new ComicPlayer(this, ENDING_PAGES, () => this.theEnd(),
      { fallback: { page: 'select', panel: 'page', balloon: 'select', stamp: 'thump' }, hold: 4200 });
    window.__sheep.ready = true;
  }

  txt(x, y, s, font) {
    return this.cache.bitmapFont.exists(font) ? this.add.bitmapText(x, y, font, s)
      : this.add.text(x, y, s, { fontFamily: 'monospace', fontSize: '10px', color: '#fff' });
  }

  // black stage, THE END stamped in, then the credits scroll up over the final score
  theEnd() {
    const W = this.scale.width, H = this.scale.height;
    this.children.removeAll(true);
    this.input.keyboard.removeAllListeners(); this.input.removeAllListeners();
    this.add.rectangle(0, 0, W, H, 0x07080c).setOrigin(0, 0);
    this.embers = this.add.graphics(); this.sparks = [];
    const end = this.txt(0, 0, 'THE END', 'hud-sfx-gold').setOrigin(0.5).setPosition(W / 2, H / 2 - 6);
    end.setScale(2); this.time.delayedCall(70, () => end.setScale(1.5)); this.time.delayedCall(140, () => end.setScale(1));
    this.sfx.play('boom');
    this.cameras.main.shake(160, 0.006);
    const lines = [
      ['ARMED AND FLUFFY', 'hud-big-gold'], null,
      ['FINAL SCORE', 'hud-font-orange'], [String(this.score).padStart(6, '0'), 'hud-big-steel'], null, null,
      ['STARRING', 'hud-font-orange'], ['THE COMMANDO SHEEP', 'hud-font'], null,
      ['VILLAINS', 'hud-font-orange'], ['THE RED EAGLE ARMY', 'hud-font'], null,
      ['COMMANDER IN CHIEF', 'hud-font-orange'], ['THE PRESIDENT', 'hud-font'], null,
      ['PILOT', 'hud-font-orange'], ['CHOPPER ONE', 'hud-font'], null, null,
      ['NO SHEEP WERE SHEARED', 'hud-font-blue'], ['IN THE MAKING OF THIS MISSION', 'hud-font-blue'], null, null,
      ['THANK YOU FOR PLAYING!', 'hud-big-gold'],
    ];
    const roll = this.roll = this.add.container(0, H + 4);
    let y = 0;
    for (const l of lines) {
      if (!l) { y += 10; continue; }
      const t = this.txt(0, y, l[0], l[1]); t.x = Math.round(W / 2 - t.width / 2); roll.add(t);
      y += l[1].includes('big') ? 22 : 13;
    }
    this.rollH = y; this.rollEnd = Math.round(H / 2 - (y - 22));   // roll stops with THANK YOU centred
    // after 1.8 s THE END steps up to the top and the roll starts from below the screen
    this.time.delayedCall(1800, () => {
      this.tweens.add({ targets: end, y: 30, duration: 400, ease: 'Stepped', easeParams: [5] });
      roll.y = H + 4; this.rolling = true;
    });
    const out = () => {
      if (this.leaving) return;
      if (this.rolling) { roll.y = this.rollEnd; return; }   // first press: jump to the end of the roll
      this.leaving = true; Music.stop(400);
      this.cameras.main.fadeOut(400, 0, 0, 0);
      this.time.delayedCall(420, () => this.scene.start('Title'));
    };
    const kb = this.input.keyboard;
    this.time.delayedCall(600, () => { kb.on('keydown-ENTER', out); kb.on('keydown-X', out); kb.on('keydown-Z', out); kb.on('keydown-ESC', out); });
    this.out = out;
  }

  update(t, dt) {
    if (!this.embers) return;
    // embers drifting up behind the credits
    if (Math.random() < 0.3) this.sparks.push({ x: Math.random() * 480, y: 272, vy: -0.3 - Math.random() * 0.5, life: 300 + Math.random() * 200, age: 0 });
    this.embers.clear();
    this.sparks = this.sparks.filter(s => {
      s.age++; s.y += s.vy; s.x += Math.sin(s.age * 0.05) * 0.2;
      const k = 1 - s.age / s.life; if (k <= 0) return false;
      this.embers.fillStyle(k > 0.5 ? 0xffa030 : 0xa03810, 1).fillRect(Math.round(s.x), Math.round(s.y), 1, 1);
      return true;
    });
    if (this.rolling) {
      this.acc = (this.acc || 0) + dt;
      while (this.acc > 45) { this.acc -= 45; this.roll.y -= 1; }            // 1px hard steps, ~22 px/s
      if (this.roll.y <= this.rollEnd && !this.leaving) { this.roll.y = this.rollEnd; this.rolling = false; this.time.delayedCall(3500, () => this.out()); }
    }
    if (this.roll) for (const c of this.roll.list) c.setVisible(this.roll.y + c.y > 46);   // lines vanish under THE END
  }
}
