// Mobile support: a "tap to play" fullscreen gate, pixel-art on-screen controls (D-pad, JUMP, FIRE, pause,
// fullscreen) and a "rotate to landscape" screen. The buttons synthesize the same keyboard events a desktop
// player sends (arrows, Z, X, Enter), so every scene - menus, comic pages, gameplay, results, continue - works
// on touch without touch-specific code. All UI art is drawn here at low resolution and scaled up with
// nearest-neighbour, in the HUD palette, so it matches the game's pixel art.

const KEYS = {
  left: ['ArrowLeft', 37], right: ['ArrowRight', 39], up: ['ArrowUp', 38], down: ['ArrowDown', 40],
  jump: ['KeyZ', 90, 'z'], fire: ['KeyX', 88, 'x'], start: ['Enter', 13],
};

function sendKey(type, name) {
  const [code, keyCode, key] = KEYS[name];
  const e = new KeyboardEvent(type, { code, key: key || code, bubbles: true, cancelable: true });
  Object.defineProperty(e, 'keyCode', { get: () => keyCode });
  Object.defineProperty(e, 'which', { get: () => keyCode });
  window.dispatchEvent(e);
}

// a quick tap still has to be seen by at least a couple of game frames (Controls polls isDown once per frame)
const held = new Set(), downAt = {}, MIN_HOLD = 90;
function set(name, on) {
  if (on === held.has(name)) return;
  if (on) { held.add(name); downAt[name] = performance.now(); sendKey('keydown', name); return; }
  held.delete(name);
  const wait = MIN_HOLD - (performance.now() - (downAt[name] || 0));
  if (wait > 0) setTimeout(() => { if (!held.has(name)) sendKey('keyup', name); }, wait); else sendKey('keyup', name);
}

export function isTouchDevice() {
  const q = new URLSearchParams(location.search).get('touch');
  if (q === '1') return true; if (q === '0') return false;
  // phones/tablets: a coarse primary pointer, or touch with no hover (touchscreen laptops keep the keyboard UI)
  return matchMedia('(pointer: coarse)').matches || (navigator.maxTouchPoints > 0 && matchMedia('(hover: none)').matches);
}

function el(tag, cls, parent, html) { const e = document.createElement(tag); e.className = cls; if (html) e.innerHTML = html; parent.appendChild(e); return e; }

// ---------- pixel-art renderer ----------
const C = { ink: '#1a1420', cream: '#f0e6c8', gold: '#ffd040', goldD: '#c07818', steel: '#3a4050', steelL: '#5a6474', steelD: '#23262f',
  red: '#b8281e', redL: '#e8503a', redD: '#6e1410', blue: '#2a58a8', blueL: '#5a8ae0', blueD: '#18306a', shadow: '#0c0a10' };

// 5x7 pixel font (only the glyphs the UI needs)
const FONT = {
  A: ['01110', '10001', '10001', '11111', '10001', '10001', '10001'], C: ['01111', '10000', '10000', '10000', '10000', '10000', '01111'],
  D: ['11110', '10001', '10001', '10001', '10001', '10001', '11110'], E: ['11111', '10000', '10000', '11110', '10000', '10000', '11111'],
  F: ['11111', '10000', '10000', '11110', '10000', '10000', '10000'], G: ['01111', '10000', '10000', '10111', '10001', '10001', '01111'],
  H: ['10001', '10001', '10001', '11111', '10001', '10001', '10001'], I: ['11111', '00100', '00100', '00100', '00100', '00100', '11111'],
  J: ['00111', '00010', '00010', '00010', '00010', '10010', '01100'], L: ['10000', '10000', '10000', '10000', '10000', '10000', '11111'],
  M: ['10001', '11011', '10101', '10101', '10001', '10001', '10001'], N: ['10001', '11001', '10101', '10011', '10001', '10001', '10001'],
  O: ['01110', '10001', '10001', '10001', '10001', '10001', '01110'], P: ['11110', '10001', '10001', '11110', '10000', '10000', '10000'],
  R: ['11110', '10001', '10001', '11110', '10100', '10010', '10001'], S: ['01111', '10000', '10000', '01110', '00001', '00001', '11110'],
  T: ['11111', '00100', '00100', '00100', '00100', '00100', '00100'], U: ['10001', '10001', '10001', '10001', '10001', '10001', '01110'],
  V: ['10001', '10001', '10001', '10001', '10001', '01010', '00100'], Y: ['10001', '10001', '01010', '00100', '00100', '00100', '00100'],
  K: ['10001', '10010', '10100', '11000', '10100', '10010', '10001'], B: ['11110', '10001', '10001', '11110', '10001', '10001', '11110'],
  W: ['10001', '10001', '10001', '10101', '10101', '11011', '10001'], '!': ['00100', '00100', '00100', '00100', '00100', '00000', '00100'],
  ' ': ['00000', '00000', '00000', '00000', '00000', '00000', '00000'],
};
const textW = (s) => s.length * 6 - 1;
function text(g, s, x, y, col, shadow = C.ink) {
  for (const pass of shadow ? [0, 1] : [1]) {
    g.fillStyle = pass ? col : shadow;
    [...s].forEach((ch, i) => (FONT[ch] || FONT[' ']).forEach((row, r) => [...row].forEach((b, c) => {
      if (b === '1') g.fillRect(x + i * 6 + c + (pass ? 0 : 1), y + r + (pass ? 0 : 1), 1, 1);
    })));
  }
}
function canvas(w, h, draw) { const c = document.createElement('canvas'); c.width = w; c.height = h; const g = c.getContext('2d'); g.imageSmoothingEnabled = false; draw(g, w, h); return c.toDataURL(); }
// pixel disc: a filled circle on the integer grid
function disc(g, cx, cy, r, col) { g.fillStyle = col; for (let y = -r; y <= r; y++) { const w = Math.floor(Math.sqrt(r * r - y * y + r * 0.8)); g.fillRect(cx - w, cy + y, w * 2 + 1, 1); } }

// round action button: ink ring, bevelled face (light top-left, dark bottom-right), label; pressed = sunk 1px, brighter
function roundBtn(label, base, light, dark, pressed) {
  const S = 34, cx = 17, cy = 17;
  return canvas(S, S + 2, (g) => {
    disc(g, cx, cy + 2, 16, C.shadow);                                       // drop shadow
    const o = pressed ? 1 : 0;
    disc(g, cx, cy + o, 16, C.ink);
    disc(g, cx, cy + o, 14, pressed ? light : dark);                         // bevel ring (dark lower edge)
    disc(g, cx, cy - 1 + o, 13, pressed ? light : base);
    if (!pressed) { g.fillStyle = light; g.fillRect(cx - 8, cy - 11, 7, 1); g.fillRect(cx - 10, cy - 10, 3, 1); g.fillRect(cx - 11, cy - 9, 2, 2); }
    text(g, label, cx - Math.floor(textW(label) / 2), cy - 4 + o, pressed ? C.gold : C.cream);
  });
}
// small square plate button (pause / fullscreen) with a pixel icon
function plateBtn(icon, pressed) {
  return canvas(20, 16, (g) => {
    const o = pressed ? 1 : 0;
    g.fillStyle = C.shadow; g.fillRect(1, 2, 19, 14);
    g.fillStyle = C.ink; g.fillRect(0, o, 19, 14);
    g.fillStyle = C.steelD; g.fillRect(1, 1 + o, 17, 12);
    g.fillStyle = pressed ? C.steelL : C.steel; g.fillRect(1, 1 + o, 17, 11);
    if (!pressed) { g.fillStyle = C.steelL; g.fillRect(1, 1, 17, 1); g.fillRect(1, 1, 1, 10); }
    g.fillStyle = pressed ? C.gold : C.cream;
    if (icon === 'pause') { g.fillRect(6, 4 + o, 2, 6); g.fillRect(11, 4 + o, 2, 6); }
    else { for (const [x, y, sx, sy] of [[4, 3, 1, 1], [14, 3, -1, 1], [4, 10, 1, -1], [14, 10, -1, -1]]) { g.fillRect(x, y + o, 1, 1); g.fillRect(x + sx, y + o, 1, 1); g.fillRect(x + sx * 2, y + o, 1, 1); g.fillRect(x, y + sy + o, 1, 1); g.fillRect(x, y + sy * 2 + o, 1, 1); } }
  });
}
// D-pad: a bevelled steel cross; the pressed directions light their arrow gold and sink their arm
const padCache = {};
function padImg(dirs) {
  const key = [...dirs].sort().join(',');
  if (padCache[key]) return padCache[key];
  const S = 48, a = 16;   // arm width
  return padCache[key] = canvas(S, S + 2, (g) => {
    const arm = (x, y, w, h, col) => { g.fillStyle = col; g.fillRect(x, y, w, h); };
    arm(a, 2, a, S, C.shadow); arm(0, a + 2, S, a, C.shadow);                          // drop shadow
    arm(a, 0, a, S, C.ink); arm(0, a, S, a, C.ink);                                    // outline
    arm(a + 1, 1, a - 2, S - 2, C.steelD); arm(1, a + 1, S - 2, a - 2, C.steelD);      // bevel dark
    arm(a + 1, 1, a - 2, S - 3, C.steel); arm(1, a + 1, S - 2, a - 3, C.steel);       // face
    g.fillStyle = C.steelL; g.fillRect(a + 1, 1, a - 2, 1); g.fillRect(1, a + 1, a, 1); g.fillRect(a + 1, 1, 1, a); g.fillRect(1, a + 1, 1, a - 3);
    disc(g, 24, 24, 4, C.steelD); disc(g, 24, 23, 3, C.steel);                         // hub
    const tri = (d, col) => {
      g.fillStyle = col;
      for (let i = 0; i < 5; i++) {
        const w = i * 2 + 1;
        if (d === 'up') g.fillRect(24 - i, 5 + i, w, 1);
        if (d === 'down') g.fillRect(24 - i, 42 - i, w, 1);
        if (d === 'left') g.fillRect(5 + i, 24 - i, 1, w);
        if (d === 'right') g.fillRect(42 - i, 24 - i, 1, w);
      }
    };
    for (const d of ['up', 'down', 'left', 'right']) {
      if (dirs.has(d)) {                                                                // sunk arm
        g.fillStyle = C.steelD;
        if (d === 'up') g.fillRect(a + 1, 1, a - 2, 13); if (d === 'down') g.fillRect(a + 1, 34, a - 2, 13);
        if (d === 'left') g.fillRect(1, a + 1, 13, a - 2); if (d === 'right') g.fillRect(34, a + 1, 13, a - 2);
      }
      tri(d, dirs.has(d) ? C.gold : C.cream);
    }
  });
}
const bg = (e, url) => { e.style.backgroundImage = `url(${url})`; };

// ---------- controls ----------
function dpad(root) {
  const pad = el('div', 'tc-pad px', root);
  bg(pad, padImg(new Set()));
  let id = null, last = '';
  const apply = (dirs) => {
    for (const d of ['left', 'right', 'up', 'down']) set(d, dirs.has(d));
    const k = [...dirs].sort().join(','); if (k !== last) { last = k; bg(pad, padImg(dirs)); }
  };
  const read = (e) => {
    const r = pad.getBoundingClientRect(), dx = e.clientX - (r.left + r.width / 2), dy = e.clientY - (r.top + r.height / 2);
    const dirs = new Set();
    if (Math.hypot(dx, dy) > r.width * 0.12) {
      const a = Math.atan2(dy, dx) * 180 / Math.PI;   // 8 sectors of 45 deg
      if (a > -67.5 && a < 67.5) dirs.add('right');
      if (a > 112.5 || a < -112.5) dirs.add('left');
      if (a > 22.5 && a < 157.5) dirs.add('down');
      if (a < -22.5 && a > -157.5) dirs.add('up');
    }
    apply(dirs);
  };
  pad.addEventListener('pointerdown', e => { id = e.pointerId; pad.setPointerCapture(id); read(e); e.preventDefault(); });
  pad.addEventListener('pointermove', e => { if (e.pointerId === id) read(e); });
  const end = e => { if (e.pointerId !== id) return; id = null; apply(new Set()); };
  pad.addEventListener('pointerup', end); pad.addEventListener('pointercancel', end); pad.addEventListener('lostpointercapture', end);
}

function button(root, cls, up, down, onDown, onUp) {
  const b = el('div', 'tc-btn px ' + cls, root); bg(b, up);
  let id = null;
  b.addEventListener('pointerdown', e => { id = e.pointerId; b.setPointerCapture(id); bg(b, down); onDown(); e.preventDefault(); e.stopPropagation(); });
  const end = e => { if (e.pointerId !== id) return; id = null; bg(b, up); onUp && onUp(); };
  b.addEventListener('pointerup', end); b.addEventListener('pointercancel', end); b.addEventListener('lostpointercapture', end);
  return b;
}
const keyBtn = (root, cls, up, down, name) => button(root, cls, up, down, () => set(name, true), () => set(name, false));

// ---------- fullscreen ----------
const fsEl = () => document.fullscreenElement || document.webkitFullscreenElement;
const fsSupported = () => !!(document.documentElement.requestFullscreen || document.documentElement.webkitRequestFullscreen);
function goFullscreen() {
  const d = document.documentElement, fs = d.requestFullscreen || d.webkitRequestFullscreen;
  try {
    const r = fs && fs.call(d, { navigationUI: 'hide' });
    const lock = () => { try { screen.orientation?.lock?.('landscape').catch(() => {}); } catch (e) { /* unsupported */ } };
    if (r && r.then) r.then(lock).catch(() => {}); else lock();
  } catch (e) { /* not allowed (iOS Safari on iPhone) */ }
}

export function initTouch(game) {
  const touch = isTouchDevice();
  document.body.classList.toggle('touch', touch);

  // rotate-to-landscape screen (touch devices in portrait); the game sleeps while it shows
  const rot = el('div', 'tc-rotate', document.body);
  const phone = el('div', 'tc-phone px', rot);
  bg(phone, canvas(24, 16, (g) => { g.fillStyle = C.ink; g.fillRect(0, 0, 24, 16); g.fillStyle = C.cream; g.fillRect(1, 1, 22, 14); g.fillStyle = C.ink; g.fillRect(2, 2, 20, 12); g.fillStyle = '#2a6a3a'; g.fillRect(3, 3, 18, 10); g.fillStyle = C.gold; g.fillRect(11, 6, 3, 4); }));
  const rt = el('div', 'tc-rtext px', rot); bg(rt, canvas(textW('ROTATE YOUR DEVICE') + 2, 9, g => text(g, 'ROTATE YOUR DEVICE', 0, 0, C.gold)));
  const rs = el('div', 'tc-rsub px', rot); bg(rs, canvas(textW('PLAYS IN LANDSCAPE') + 2, 9, g => text(g, 'PLAYS IN LANDSCAPE', 0, 0, C.cream)));

  const portrait = () => touch && window.innerHeight > window.innerWidth;
  let slept = false;
  const check = () => {
    // integer UI scale: pixel art stays square; about 120 UI pixels across the short side
    document.documentElement.style.setProperty('--px', Math.max(2, Math.floor(Math.min(innerWidth, innerHeight) / 120)) + 'px');
    const p = portrait();
    rot.classList.toggle('show', p);
    const sleep = p;   // the tap-to-play gate doesn't sleep the game: assets keep loading behind it
    if (sleep && !slept && game.loop) { game.loop.sleep(); slept = true; for (const n of [...held]) set(n, false); }
    else if (!sleep && slept) { game.loop.wake(); slept = false; }
    game.scale && game.scale.refresh();
  };
  window.addEventListener('resize', check); window.addEventListener('orientationchange', () => setTimeout(check, 200));
  game.events.once('ready', check); setTimeout(check, 0);

  if (!touch) return;

  // "tap to play" gate: the one user gesture that can open fullscreen, lock landscape and unlock audio
  if (new URLSearchParams(location.search).get('gate') !== '0') {
    const gate = el('div', 'tc-gate', document.body);
    const up = canvas(78, 22, g => { g.fillStyle = C.shadow; g.fillRect(2, 3, 76, 19); g.fillStyle = C.ink; g.fillRect(0, 0, 76, 19); g.fillStyle = C.redD; g.fillRect(1, 1, 74, 17); g.fillStyle = C.red; g.fillRect(1, 1, 74, 15); g.fillStyle = C.redL; g.fillRect(1, 1, 74, 1); g.fillRect(1, 1, 1, 14); text(g, 'TAP TO PLAY', 6, 5, C.cream); });
    const down = canvas(78, 22, g => { g.fillStyle = C.ink; g.fillRect(0, 2, 76, 19); g.fillStyle = C.redL; g.fillRect(1, 3, 74, 17); text(g, 'TAP TO PLAY', 6, 7, C.gold); });
    const b = el('div', 'tc-gbtn px', gate); bg(b, up);
    const note = el('div', 'tc-gnote px', gate);
    const msg = fsSupported() ? 'FULLSCREEN LANDSCAPE' : 'LANDSCAPE';
    bg(note, canvas(textW(msg) + 2, 9, g => text(g, msg, 0, 0, C.cream)));
    let busy = false;
    gate.addEventListener('pointerdown', e => { e.preventDefault(); bg(b, down); });
    gate.addEventListener('pointerup', e => {
      e.preventDefault(); if (busy) return; busy = true;
      goFullscreen();
      try { game.sound?.context?.resume?.(); } catch (err) { /* no audio */ }
      gate.classList.add('out'); check();
      setTimeout(() => gate.remove(), 250);
    });
  }

  const root = el('div', 'tc-root', document.body);
  dpad(root);
  keyBtn(root, 'tc-jump', roundBtn('JUMP', C.blue, C.blueL, C.blueD), roundBtn('JUMP', C.blue, C.blueL, C.blueD, true), 'jump');
  keyBtn(root, 'tc-fire', roundBtn('FIRE', C.red, C.redL, C.redD), roundBtn('FIRE', C.red, C.redL, C.redD, true), 'fire');
  keyBtn(root, 'tc-start', plateBtn('pause'), plateBtn('pause', true), 'start');
  if (fsSupported()) {   // back to fullscreen after the player swipes out of it
    const f = button(root, 'tc-fs', plateBtn('fs'), plateBtn('fs', true), () => {}, goFullscreen);
    const upd = () => f.classList.toggle('hide', !!fsEl());
    document.addEventListener('fullscreenchange', upd); document.addEventListener('webkitfullscreenchange', upd); upd();
  }

  // no long-press menus, text selection or pinch zoom over the game
  document.addEventListener('contextmenu', e => e.preventDefault());
  document.addEventListener('gesturestart', e => e.preventDefault());
}
