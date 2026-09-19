// Unified input: keyboard (arrows/WASD, Z/K jump, X/J fire) + gamepad. Call poll() once per frame.
export class Controls {
  constructor(scene) {
    this.scene = scene;
    const K = Phaser.Input.Keyboard.KeyCodes;
    this.k = scene.input.keyboard.addKeys({
      left: K.LEFT, right: K.RIGHT, up: K.UP, down: K.DOWN,
      a: K.A, d: K.D, w: K.W, s: K.S,
      jump: K.Z, jump2: K.K, jump3: K.SPACE, fire: K.X, fire2: K.J, start: K.ENTER, esc: K.ESC,
    });
    this.state = { left: false, right: false, up: false, down: false, jump: false, fire: false, start: false };
    this.prev = { ...this.state };
  }
  poll() {
    const k = this.k, s = this.state; this.prev = { ...s };
    const pad = this.scene.input.gamepad && this.scene.input.gamepad.total ? this.scene.input.gamepad.getPad(0) : null;
    const ax = pad ? pad.leftStick.x : 0, ay = pad ? pad.leftStick.y : 0;
    s.left = k.left.isDown || k.a.isDown || ax < -0.4 || !!(pad && pad.left);
    s.right = k.right.isDown || k.d.isDown || ax > 0.4 || !!(pad && pad.right);
    s.up = k.up.isDown || k.w.isDown || ay < -0.4 || !!(pad && pad.up);
    s.down = k.down.isDown || k.s.isDown || ay > 0.4 || !!(pad && pad.down);
    s.jump = k.jump.isDown || k.jump2.isDown || k.jump3.isDown || !!(pad && pad.A);
    s.fire = k.fire.isDown || k.fire2.isDown || !!(pad && (pad.X || pad.B || pad.R2 > 0.3));
    s.start = k.start.isDown || k.esc.isDown || !!(pad && pad.buttons[9] && pad.buttons[9].pressed);
    const inj = window.__sheep && window.__sheep.inject; // test harness input (art/raw/feel/play.mjs)
    if (inj) for (const n in s) s[n] = s[n] || !!inj[n];
  }
  pressed(n) { return this.state[n] && !this.prev[n]; }
}
