// Comic-book story intro: Title START -> this -> Game(stage 1) with the helicopter drop-in.
// Panel art: assets/story/<id>.png (generated + pixel-cleaned by art/raw/story/build_story.py; sizes = panel + pan margin).
import { ComicPlayer } from '../fx/comic.js';
import { Music } from '../audio/Music.js';

export const INTRO_PAGES = [
  [ // page 1: the Oval Office
    { id: 'p1', x: 6, y: 6, w: 300, h: 138, pan: [24, 0], from: 'left', beats: [
      { t: 'cap', s: 'WASHINGTON D.C.  03:00 HOURS', x: 4, y: 4 },
      { t: 'sfx', s: 'KRAK!', x: 222, y: 52, font: 'hud-sfx-gold', snd: 'boom' },
      { t: 'say', s: 'THIS IS THE PRESIDENT.\nWAKE UP THE GENERALS!', x: 150, y: 100, tail: [150, 50] } ] },
    { id: 'p2', x: 312, y: 6, w: 162, h: 138, pan: [0, 16], from: 'right', beats: [
      { t: 'say', s: 'THE RED EAGLE ARMY\nHAS SEIZED\nTHE JUNGLE!', x: 96, y: 4, tail: [70, 70] } ] },
    { id: 'p3', x: 6, y: 150, w: 468, h: 114, pan: [24, 0], from: 'bottom', beats: [
      { t: 'cap', s: 'SATELLITE RECON.  SECTOR 7.', x: 4, y: 4 },
      { t: 'say', s: 'SIR... THEY BUILT\nA SECRET LAB\nDOWN THERE.', x: 64, y: 40, phone: true },
      { t: 'cap', s: 'ONLY ONE SOLDIER CAN STOP THEM...', x: 999, y: 999 } ] },
  ],
  [ // page 2: the call, gearing up
    { id: 'p4', x: 6, y: 6, w: 210, h: 258, pan: [0, -24], from: 'left', beats: [
      { t: 'sfx', s: 'RRRING!', x: 168, y: 206, font: 'hud-big-red', snd: 'phone' },
      { t: 'cap', s: 'JUNGLE OUTPOST,\n0301 HOURS', x: 4, y: 4 },
      { t: 'say', s: '...BAAA?', x: 170, y: 58, tail: [128, 98] },
      { t: 'say', s: 'SOLDIER.\nYOUR COUNTRY\nNEEDS YOU.', x: 56, y: 214, phone: true } ] },
    { id: 'p5', x: 222, y: 6, w: 252, h: 126, pan: [20, 0], from: 'top', beats: [
      { t: 'sfx', s: 'TSHK!', x: 999, y: 22, font: 'hud-sfx-gold' },
      { t: 'cap', s: 'GEAR UP.', x: 4, y: 4 } ] },
    { id: 'p6', x: 222, y: 138, w: 252, h: 126, pan: [0, 0], from: 'right', beats: [
      { t: 'sfx', s: 'KLIK-KLAK!', x: 999, y: 22, font: 'hud-sfx-gold' },
      { t: 'say', s: "I'M ON IT.", x: 46, y: 100, tail: [96, 72] } ] },
  ],
  [ // page 3: the chopper
    { id: 'p7', x: 6, y: 6, w: 468, h: 118, pan: [24, 0], from: 'top', loop: 'rotor', beats: [
      { t: 'cap', s: '0600 HOURS.  DAWN.', x: 4, y: 4 },
      { t: 'sfx', s: 'WHUP WHUP', x: 110, y: 92, font: 'hud-sfx-gold' } ] },
    { id: 'p8', x: 6, y: 130, w: 300, h: 134, pan: [-24, 0], from: 'left', beats: [
      { t: 'cap', s: 'OVER ENEMY JUNGLE...', x: 4, y: 110 },
      { t: 'say', s: 'DROP ZONE IN TEN!', x: 170, y: 52, phone: true } ] },
    { id: 'p9', x: 312, y: 130, w: 162, h: 134, pan: [0, 24], from: 'right', beats: [
      { t: 'say', s: "LET'S ROCK!", x: 999, y: 6, tail: [118, 40] },
      { t: 'sfx', s: 'GO!', x: 36, y: 104, font: 'hud-sfx-red' } ] },
  ],
];

export class Intro extends Phaser.Scene {
  constructor() { super('Intro'); }
  create() {
    this.cameras.main.setBackgroundColor('#07080c'); this.cameras.main.fadeIn(300, 0, 0, 0);
    this.leaving = false;
    Music.play(this, 'intro');
    const go = () => {
      if (this.leaving) return; this.leaving = true;
      Music.stop(300);
      this.cameras.main.fadeOut(300, 0, 0, 0);
      this.time.delayedCall(320, () => this.scene.start('Game', { stage: 1, drop: true }));
    };
    this.comic = new ComicPlayer(this, INTRO_PAGES, go, { fallback: { page: 'select', panel: 'page', balloon: 'select', stamp: 'thump' },
      startPage: Math.max(0, (+window.__sheep.query.get('page') || 1) - 1) });
    window.__sheep.ready = true;
  }
}
