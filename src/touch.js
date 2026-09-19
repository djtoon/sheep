// Mobile support: on-screen D-pad + JUMP/FIRE/PAUSE buttons and a "rotate to landscape" screen.
// The buttons synthesize the same keyboard events a desktop player sends (arrows, Z, X, Enter), so every
// scene - menus, comic pages, gameplay, results, continue - works on touch without touch-specific code.

const KEYS = {
  left: ['ArrowLeft', 37], right: ['ArrowRight', 39], up: ['ArrowUp', 38], down: ['ArrowDown', 40],
  jump: ['KeyZ', 90, 'z'], fire: ['KeyX', 88, 'x'], start: ['Enter', 13],
};

function sendKey(type, name) {
  const [code, keyCode, key] = KEYS[name];
  const e = new KeyboardEvent(type, { code, key: key || code.replace('Arrow', 'Arrow'), bubbles: true, cancelable: true });
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

// D-pad: one zone, 8 directions from the finger's angle to the pad centre (dead zone in the middle)
function dpad(root) {
  const pad = el('div', 'tc-pad', root);
  el('div', 'tc-pad-h', pad); el('div', 'tc-pad-v', pad); el('div', 'tc-pad-hub', pad);
  const arrows = {};
  for (const d of ['up', 'down', 'left', 'right']) arrows[d] = el('div', 'tc-arrow tc-' + d, pad);
  let id = null;
  const apply = (dirs) => {
    for (const d of ['left', 'right', 'up', 'down']) { set(d, dirs.has(d)); arrows[d].classList.toggle('on', dirs.has(d)); }
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

function button(root, cls, label, name) {
  const b = el('div', 'tc-btn ' + cls, root, '<span>' + label + '</span>');
  let id = null;
  b.addEventListener('pointerdown', e => { id = e.pointerId; b.setPointerCapture(id); set(name, true); b.classList.add('on'); e.preventDefault(); });
  const end = e => { if (e.pointerId !== id) return; id = null; set(name, false); b.classList.remove('on'); };
  b.addEventListener('pointerup', end); b.addEventListener('pointercancel', end); b.addEventListener('lostpointercapture', end);
  return b;
}

export function initTouch(game) {
  const touch = isTouchDevice();
  document.body.classList.toggle('touch', touch);

  // rotate-to-landscape screen (touch devices in portrait); the game sleeps while it shows
  const rot = el('div', 'tc-rotate', document.body,
    '<div class="tc-phone"><div class="tc-screen"></div></div><p>ROTATE YOUR DEVICE</p><p class="tc-sub">ARMED AND FLUFFY PLAYS IN LANDSCAPE</p>');
  const portrait = () => touch && window.innerHeight > window.innerWidth;
  let slept = false;
  const check = () => {
    const p = portrait();
    rot.classList.toggle('show', p);
    if (p && !slept && game.loop) { game.loop.sleep(); slept = true; for (const n of [...held]) set(n, false); }
    else if (!p && slept) { game.loop.wake(); slept = false; }
    game.scale && game.scale.refresh();
  };
  window.addEventListener('resize', check); window.addEventListener('orientationchange', () => setTimeout(check, 200));
  game.events.once('ready', check); setTimeout(check, 0);

  if (!touch) return;
  const root = el('div', 'tc-root', document.body);
  dpad(root);
  button(root, 'tc-jump', 'JUMP', 'jump');
  button(root, 'tc-fire', 'FIRE', 'fire');
  button(root, 'tc-start', 'II', 'start');

  // first touch: go fullscreen and try to lock landscape (both are best-effort; iOS Safari ignores them)
  const first = () => {
    document.removeEventListener('pointerdown', first, true);
    const d = document.documentElement, fs = d.requestFullscreen || d.webkitRequestFullscreen;
    try { const r = fs && fs.call(d, { navigationUI: 'hide' }); r && r.then && r.then(() => screen.orientation?.lock?.('landscape').catch(() => {})).catch(() => {}); } catch (e) { /* not allowed */ }
    try { game.sound?.context?.resume?.(); } catch (e) { /* no audio */ }
  };
  document.addEventListener('pointerdown', first, true);
  // no long-press menus, text selection or pinch zoom over the game
  document.addEventListener('contextmenu', e => e.preventDefault());
  document.addEventListener('gesturestart', e => e.preventDefault());
}
