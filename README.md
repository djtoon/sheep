# Armed and Fluffy

A Contra-style run-and-gun starring a commando sheep. Built with Phaser 4 (vendored in `lib/`).

## The campaign

1. **Story intro**: a comic-book briefing (the President, the call, the chopper ride). Enter / X / Z advance a panel; Esc (or holding a key) skips it.
2. **STAGE 01 - JUNGLE ASSAULT**: the sheep fast-ropes in from a helicopter. Boss: the IRON EAGLE GATE.
3. **STAGE 02 - NIGHT RAID**: night military base B-02, again by chopper. Boss: the B-02 WARDEN mech.
4. **STAGE 03 - SECRET LAB**: the underground lab, entered by rope through a blown ceiling hatch. Boss: SPECIMEN X.
5. **Ending**: a comic epilogue, then THE END and a credits roll over your final score, and back to the title.

Each boss opens with a WARNING! alarm and shows a health strip at the bottom of the screen. After each boss, a results card
shows score, kills, accuracy, the lives bonus (2,000 per life left) and time. Press Start to move on.
**Score, lives and your current weapon carry over** from stage to stage. Dying resets the weapon to the rifle, as in Contra.
Extra lives come at 20,000 points and then every 60,000.

## Run

```
npm start
```

Then open **http://localhost:8080/** in a browser. You only need Node 18 or later. The game uses no runtime
dependencies, so `npm install` is only needed for the dev tools (Playwright screenshots).

## Controls

| Action | Keyboard | Gamepad | Touch |
|---|---|---|---|
| Move / aim (8-way) | Arrow keys or WASD | Left stick / D-pad | On-screen D-pad (slide for diagonals) |
| Jump | Z, K or Space | A | JUMP |
| Fire | X or J | X / B / R2 | FIRE |
| Prone | Down (standing still) | Down | D-pad down |
| Drop through a bridge | Down + Jump | Down + A | D-pad down + JUMP |
| Start / pause | Enter or Esc | Start | II button |

**Mobile:** on phones and tablets the game shows on-screen controls, and asks you to rotate to landscape if you hold the device upright (the game pauses until you do).
Tap the screen to start, and tap FIRE or JUMP to turn comic pages. The first touch also tries to go fullscreen.
Add `?touch=1` to force the touch controls on a desktop browser, or `?touch=0` to hide them.

On the title screen, Enter, X or Z starts the game. Press Start during play to pause.
When you run out of lives you get a 9-second **CONTINUE?** countdown. Press Start to continue on the spot with 3 lives, but your score is reset.
If the countdown runs out, the game returns to the title, and a new game starts again from the intro.

Weapon capsules fly across the screen. Shoot one to drop a pickup: **M** machine gun, **S** spread, **L** laser (you start with the **R** rifle).

## Dev / test query flags

These flags only apply when they are in the URL, so normal play (no query string) never uses them.

| Flag | Effect |
|---|---|
| `?test=1` | skip the title and boot straight into a stage (used by the tools) |
| `?stage=1\|2\|3` | which stage to boot into (with `test=1`); `?test=1&stage=3` is a direct entry into the lab |
| `?drop=1` | start the stage with its drop-in (helicopter for stages 1-2, ceiling hatch for stage 3), as in the campaign |
| `?scene=title\|intro\|ending` | force a scene: the title, the story intro (it continues into stage 1) or the ending (overrides `test=1`) |
| `?page=N` | with `scene=intro`: start the comic at page N |
| `?score=N` | with `scene=ending`: the final score shown in the credits |
| `?credits=1` | with `scene=ending`: skip the epilogue page and go straight to THE END and the credits |
| `?god=1` | invulnerable hero |
| `?x=2400` | start at level x-position 2400 (every stage's boss arena starts around 5000); also skips the stage intro card |
| `?weapon=R\|M\|S\|L` | start with a weapon: Rifle, Machine gun, Spread or Laser |
| `?hitboxes=1` | draw arcade physics bodies |
| `?nointro=1` | skip the stage intro card |
| `?nocull=1` | disable off-screen culling of stage-1 level props (perf comparison) |
| `?bgshift=N` | override the stage-1 backdrop's vertical lift (art tuning) |

Examples:
- `http://localhost:8080/?test=1&god=1&x=4900&weapon=S` puts you at the stage-1 boss with the spread gun, invulnerable.
- `http://localhost:8080/?test=1&stage=2&drop=1` starts stage 2 exactly as the campaign does, with the chopper drop.
- `http://localhost:8080/?scene=ending&score=123450` plays the ending.

## Tools

- `node tools/shot.mjs --out shots/x.png [--query "god=1&x=1200"] [--script "hold:ArrowRight+KeyX:1500 shot:name"] [--clip shots/x.mp4]`
  plays the real game in headless Chromium and saves screenshots or clips.
- `node art/raw/feel/play.mjs [--query ...] [--script ...] [--bot 1] [--clip ...] [--trace ...]` is a deterministic
  60 fps harness with scripted input and an autopilot bot.
- `BUILDERS.md` is the art and code handbook (resolution, asset manifest, file ownership).

## Layout

- `index.html` and `src/`: the game (`src/scenes`, `src/entities`, `src/level`, `src/fx`, `src/audio`)
- `assets/`: final art and audio, loaded through `assets/manifest.json` and `assets/parts/*.json`
- `art/raw/`: generation sources and build scripts (not loaded by the game)
