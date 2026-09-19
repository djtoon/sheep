# Armed and Fluffy

A Contra-style run-and-gun starring a commando sheep. Built with Phaser 4 (vendored in `lib/`).

## Run

```
npm start
```

Then open **http://localhost:8080/** in a browser. You only need Node 18 or later. The game uses no runtime
dependencies, so `npm install` is only needed for the dev tools (Playwright screenshots).

## Controls

| Action | Keyboard | Gamepad |
|---|---|---|
| Move / aim (8-way) | Arrow keys or WASD | Left stick / D-pad |
| Jump | Z, K or Space | A |
| Fire | X or J | X / B / R2 |
| Prone | Down (standing still) | Down |
| Drop through a bridge | Down + Jump | Down + A |
| Start / pause | Enter or Esc | Start |

On the title screen, Enter, X or Z starts the game. When a game ends you have a 9-second **CONTINUE?** countdown: press Start to continue.

## Dev / test query flags

These flags only apply when they are in the URL, so normal play (no query string) never uses them.

| Flag | Effect |
|---|---|
| `?test=1` | skip the title and boot straight into the stage (used by the tools) |
| `?scene=title` | force the title screen (overrides `test=1`) |
| `?god=1` | invulnerable hero |
| `?x=2400` | start at level x-position 2400 (the boss arena starts around 5000); also skips the stage intro card |
| `?weapon=R\|M\|S\|L` | start with a weapon: Rifle, Machine gun, Spread or Laser |
| `?hitboxes=1` | draw arcade physics bodies |
| `?nointro=1` | skip the STAGE 01 intro card |
| `?nocull=1` | disable off-screen culling of level props (perf comparison) |
| `?bgshift=N` | override the backdrop's vertical lift (art tuning) |

Example: `http://localhost:8080/?test=1&god=1&x=4900&weapon=S` puts you at the boss with the spread gun, invulnerable.

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
