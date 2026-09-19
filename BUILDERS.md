# Armed and Fluffy: builder handbook

A Contra-style run-and-gun starring a commando sheep, in Phaser 4.2.1 (global `Phaser` from `lib/phaser.min.js`).
The Phaser 4 docs for agents are in `node_modules/phaser/skills/*/SKILL.md`. Read `v3-to-v4-migration` before using any API you know from v3
(for example, tint fill is `setTint(c).setTintMode(Phaser.TintModes.FILL)`, `group.getChildren()` not `group.children.each`, and FX/masks are now filters).

## The bar
The mockups in `ref/`. Every frame of the running game must hold up next to them.
- `ref/2b74…png`, `ref/c0f6…png`, `ref/369c…png`, `ref/fd55…png` are in-game frames (jungle, waterfalls, bridges, enemy base, HUD).
- `ref/3c48…png` is the hero character sheet (idle, run, shoot).
- `ref/2f33…png` is the title screen.
Game feel is judged against the original Contra (NES) and Metal Slug.

## Resolution and scale
The logical canvas is **480x270**, integer-scaled and pixel-perfect (`pixelArt: true`). The mockups are ~1672x941, so **1 game pixel ≈ 3.5 mockup px**.
Measure a thing in the mockup and divide by 3.5 to get its in-game size. The sheep is ~44-48 px tall, soldiers ~36-40, and the ground top is at y≈214.
Art must look pixel-crisp at 1x: no blurry resamples, no half-alpha fringes, and a consistent dark outline and palette with the mockups.

## Tools (all run from the repo root)
- `node tools/gen.mjs --out art/raw/<name>.png --prompt "..." --ref ref/<img>.png [--ref more] --aspect 1:1|16:9|3:2|WxH --quality low|medium|high --bg transparent|opaque [--n 4]`
  generates art with the model from `image.md` (Replicate, token already in env). **Always pass the relevant `ref/` images (or already-approved art) as `--ref`** so the style stays consistent.
  Transparent backgrounds come out with clean alpha. Draft at `low`/`medium` and finalize at `high`.
- `python tools/pixelize.py IN OUT --h <px> [--colors N] [--outline 1a1420] [--opaque]` cleans an image into a true pixel sprite at game size.
  `python tools/pixelize.py --sheet OUT f1.png f2.png ...` packs frames into an equal-cell horizontal strip (bottom-aligned).
  These are a starting point. Write your own scripts when needed (keeping the grid, palette-locking to the mockups, hand-fixing pixels with numpy, and so on).
- `node tools/shot.mjs --out shots/<name>.png [--query "x=1200&god=1&weapon=S"] [--wait ms] [--script "hold:ArrowRight+KeyX:1500 tap:KeyZ wait:200 shot:name"] [--clip shots/x.mp4]`
  plays the **real running game** in headless Chromium and screenshots the canvas (1440x810 = 3x). Query flags: `x` start x-position in the level, `god=1`, `weapon=R|M|S|L`, `scene=title`, `hitboxes=1`.
  Exit code 3 means the page threw, so fix it.
- `python tools/log.py --piece <yours> --kind build --title "..." --text "..." --media shots/x.png` posts to the live progress page. Post after every meaningful iteration, with a real screenshot.

## How art plugs in
`assets/manifest.json` lists part names. Each part owns `assets/parts/<part>.json`:
```json
{ "assets": [ {"type":"spritesheet","key":"sheep","url":"assets/sprites/sheep.png","frameWidth":64,"frameHeight":64} ],
  "anims":  [ {"key":"sheep-run","texture":"sheep","start":0,"end":7,"frameRate":14} ] }
```
(Anims can use `"frames":[0,1,2]` instead of start/end, and `"repeat":0` for one-shots.) Types are image, spritesheet, audio, atlas, and bitmapFont.
Texture and anim keys the code already uses, with their expected sizes, are listed in `src/gfx/placeholders.js`. Anything missing from the manifest gets a placeholder box.
If your art needs a different frame size or origin, adjust the body/offset code in the owning entity file, and keep hitboxes fair (Contra hitboxes are small).

## File ownership (parallel work, so stay in your lane)
Only edit files your piece owns. If you need a change in someone else's file, say so in your report and don't make it yourself.
Put raw generations under `art/raw/<piece>/` and final game art under `assets/<piece>/`.

## Definition of done
There isn't one. You work a round, produce real in-game screenshots, and report. A separate blind critic then compares your frame with the mockup, and the single biggest gap comes back to you.
Never report "looks great". Report what you changed and the exact screenshot paths.
