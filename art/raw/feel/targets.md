# Game-feel targets vs measured (feel builder)

Bar: NES Contra (256x224 @ 60 fps, Bill about 32 px tall) and Metal Slug (304x224, Marco about 40 px).
Ours is 480x270 with a 49 px sheep (ears included; the body is about 44 px), so every target is converted to **screens/s** (divide by the screen width) or **body heights** (divide by the character height).
The reference numbers are recalled from frame-stepping knowledge of the originals, so treat them as approximate: ±10-20%.

All measurements come from `art/raw/feel/play.mjs`. It drives the real game on a virtual 60 fps clock, so results don't depend on headless speed, and it reads `window.__sheep.stats()`.
The analysis scripts are `an_jump.py` and `an_pace.py`. `runs.sh` runs N non-god bot runs, and `bot.js` is a simple "average player" autopilot.

## Controls
| metric | Contra / Metal Slug | target (ours) | measured |
|---|---|---|---|
| run speed | Contra 1 px/f = 60 px/s = 0.23 scr/s, 1.9 bodies/s (MS about 0.3 scr/s) | 0.2-0.25 scr/s, about 2 bodies/s | **100 px/s = 0.21 scr/s = 2.0 bodies/s** (4.8 s per screen) |
| accel / decel | instant (0 frames) | instant | **instant**, full speed on the first frame |
| input latency | 1-2 frames | ≤ 2 frames | **1 frame** (velocity set in the input frame, moves on the next physics step) |
| jump height | fixed, about 1.3-1.5 bodies | fixed, about 1.5 bodies, clears the 70 px tier ledges | **75 px = 1.53 sheep, fixed (committed arc)** |
| jump airtime | about 0.7 s | 0.7-0.8 s | **750 ms** |
| air control | full (Contra) | full | full, instant |
| coyote / jump buffer | none (NES) | invisible forgiveness | 80 ms / 120 ms; fire presses are buffered 110 ms and latched during hit-stop |
| 8-way aim | snaps instantly | snaps | snaps on the same frame. Up = straight up, up+dir = diagonal, down+dir = diagonal down, down in air = straight down, down on ground = prone |
| drop-through | down + jump on a bridge | same | works (ledge y160 to ground y214), platforms ignored for 220 ms |
| player hurtbox | much smaller than the sprite | small | stand 12x36, prone 30x11, spin ball 16x16 (the collision body is separate and always feet-aligned) |
| death → control | about 2 s | about 2 s | death anim 1.5 s, then drop-in from the top of the screen 0.6 s |
| respawn i-frames | about 2 s after landing (128 f) | about 2 s | **2.6 s total = 2.0 s after landing**, flashing; the weapon resets to R (Contra) |

## Weapons (player bullets)
| gun | Contra | target | measured (3 s hold, bullets from screen-left) |
|---|---|---|---|
| R rifle | about 0.8-0.9 scr/s, 4 on screen, no autofire | 0.8 scr/s, cap 4, hold autofires slowly, mashing is faster | 380 px/s (0.79 scr/s), cap 4. Hold: **4.3 shots/s** (cap-limited at long range), mash cap 130 ms |
| M machine gun | autofire, 6 on screen | stream with no stutter | 420 px/s, cap 10, **9.7 shots/s** |
| S spread | 5-way fan, 10 on screen | wide fan, fills the screen, 5 dmg point-blank | 360 px/s, ±10°/±20° fan, cap 20 (4 volleys), **4.7 volleys/s = 23 bullets/s** |
| L laser | piercing beam | piercing, heavy | 560 px/s, 3 dmg, pierce, cap 2, 3 shots/s |
| enemy : player bullet speed | about 1 : 3 | about 1 : 3 | 105-125 : 380 = **1 : 3.1-3.6** |

## Enemies
| metric | Contra / MS | target | ours |
|---|---|---|---|
| enemy bullet speed | 1.5-2 px/f, about 0.4 scr/s | about 0.23-0.26 scr/s (2.2-2.5 bodies/s) so they can be dodged | rifleman 115, gunner-soldier 105, turret 115, drone 110 px/s |
| telegraph before a shot | aim pose / barrel turn | ≥ 400 ms readable tell | rifleman 450 ms, soldier gunner 450 ms, turret 600 ms, drone 400 ms (2 muzzle glints + `telegraph` event) |
| fire only when visible | yes | yes | enemies fire only from inside the screen, never at a dead player, never after the boss dies |
| aim quantisation | turrets 12 directions | 16 | turrets and drones snap to 16 directions; riflemen aim directly |
| foot soldier HP | 1 | 1 | soldier 1, rifleman 1 (was 2) |
| wall turret HP | about 8 | 8 | 8 (was 10); drone 2 (was 3) |
| grunt spawn cadence | about 1-2 s from the edges, both sides | 0.8-1.8 s, 15-35% from behind | stream every 0.8-1.7 s depending on the beat, 15-35% from the left, cap 3-5 alive, plus scripted waves |
| grunt spacing | individuals | ≥ 24 px, varied behaviour | spawns keep ≥ 28 px from the last grunt. Followers tail their leader and slow down under 24 px. Mix per wave: runner, gunner (stops, tells, fires once), hopper. Turrets are not obstacles (drawn behind) |

## Pacing (stage 1, god-mode bot that never stops running)
| metric | target | measured |
|---|---|---|
| time to the boss for a fast run | Contra stage 1 is about 55-60 s for a runner | **53-63 s** |
| kills per 10 s | always something to shoot | 12-20 |
| mean enemies on screen | 1.5-2.5 | **1.5 (god bot) / 2.0 (live bot)** |
| samples with an empty screen (0.5 s sampling, instant kills) | < 25% | 20-26% |
| longest breather mid-stage | 1.5-3 s at the planned spots | 1.5 s (cliff, before the base) + the 3-5 s boss-yard approach |
| capsules | at calm moments before a spike | M at 860 (over the falls), S at 2320 (stream paused, then a 7-grunt wave), L at 3660 (base), S again at 4300 (re-arm before the gauntlet and the boss) |

## Difficulty (non-god bot, 4 runs, 4 lives)
The bot has perfect reflexes but dumb positioning. It jumps or goes prone at incoming shots, doesn't grab pickups and never waits to shoot shooters first.
Result: **game over in all 4 runs at x ≈ 2850-3850** (about 60% of the stage), with 4 deaths each, all from telegraphed shots or grunt contact.
Recurring spots: the cliff turret at 1880 (the bot walks up into it) and the rifleman on the y196 rise at 2250.
This is harder than I would like for a human first-timer. See the report.

## Camera
| metric | target | measured |
|---|---|---|
| scroll | forward-only (Contra) | forward-only, never scrolls back |
| lead | player a little left of centre while running | anchor 42%, minus up to 26 px lead while running → player at **x ≈ 177 px (37%)**, eased (max 170 px/s camera catch-up) |
| shake | sparingly | Game shakes only on player death. FX owns the rest |

---
# Round 2 (critic: "worse than Contra", 75%)

## 1. Enemies one step up could not be hit
- Player shots now use a custom scan (`Game.hitScan`). A bullet counts as at least 6 px tall. Walkers (soldiers and riflemen) can be hit down to **14 px below their feet**; flyers and turrets get a 3 px apron, capsules 4 px.
- Level shots may skim **10 px into a step's lip** before the terrain eats them. Downward shots still hit the dirt. (NES Contra bullets ignore terrain completely.)
- No enemy stands on a 46 px ledge any more (the old 2760 and 4000 riflemen are gone). Every remaining spot is either ≤ 32 px up (level shot) or ≥ 58 px up (walking diagonal, Contra's answer).
- Scripted test: `art/raw/feel/hittest.sh [level|diag]` spawns a rifleman and holds a standing R shot from 100 and 170 px to the left (diag: walks up+right from 200 and 280 px).

| spot (rifleman x, y) | height above the player's floor | level R shot | walking diagonal |
|---|---|---|---|
| 610, 144 | 24 | HIT / HIT | - |
| 1700, 136 (the critic's 1552 → 1700 step) | 32 | HIT / HIT (also from x=1552 exactly) | - |
| 2250, 150 | 18 | HIT / HIT | - |
| 3330, 144 | 24 | HIT / HIT | - |
| 3930, 150 | 0 | HIT / HIT | - |
| 4610, 168 (moved from 4560) | 0 | HIT / HIT | - |
| 4860, 144 | 0-24 | HIT / HIT | - |
| 1200, 82 | 62 | miss (too high) | HIT / HIT |
| 1440, 78 | 66-90 | miss | HIT / HIT |
| 3060, 86 | 64-82 | miss | HIT / HIT |
| 4720, 110 | 58 | miss | HIT / HIT |
| ~~2760, 104~~ and ~~4000, 104~~ | 46 (only hittable by jumping) | removed | |

## 2. Density (average-player bot, no god, 4 lives)
| | before (R1, 4 runs) | after (R2, final build, 5 runs) |
|---|---|---|
| reached the boss | **0 / 4** | **5 / 5** (earlier R2 batches during tuning: 2/5, 4/5, 2/5, 2/5, 3/5, 2/5) |
| deaths per run | 4, 4, 4, 4 (game over) | 2, 2, 2, 1, 3 |
| where | 1300-1850 (falls, cliff turret), 2085 (rifleman), 2700-2850 (pinch), 3300-3850 | 2105 (rifleman at 2250, every run), 4267-4546 (gunner grunts in the base gauntlet) |
| deaths before the base (x < 3700) | 16 of 16 | 5 of 10 (all the same telegraphed level shot at 2105) |

Changes:
- No grunts from behind before x 2000. Running grunts don't stop to shoot until camera x 1800 (the riflemen do the shooting).
- One shooter at a time in the first half. The 2800 pinch is gone: I removed the rear wave, the 2760 and 3010 riflemen and the 3180 drone, and the stream now starts at 2900.
- Waves thinned (4 → 3, 5 → 4). The drone pair at 1820 is now a single drone at 1900. The rifleman grace period before the first shot is 0.9 s on screen + a 0.45 s tell.
- The early stream is still frequent (runners only) so there's always something to shoot.

God-bot pacing after the change: **53-55 s to the boss**, 0.85 enemies on screen on average (was 1.5), 5-18 kills per 10 s, max 3 enemy shots on screen.
The trade-off is emptier stretches: the longest mid-stage gaps are now 3-6 s (around 2000-2200 and 3230-3500).

## 3. Soldiers landing on you
- No contact damage from a grunt that is airborne and above you (`e.y < p.y - 8`). You only die to a grunt on your level.
- Grunts won't walk off a ledge onto the sheep when it's within ±44 px below; they turn back.
- Hoppers don't hop within 70 px of the sheep. Grunts don't leap a planted gunner within 80 px of the sheep; they wait.
- Edge spawns come in off-screen and running, never while the sheep is within 80 px of that edge. Left-side (behind) spawns are 0% before x 2000 and 15-25% after.
- Contact deaths: R1 had some in most runs. In the final R2 batch: 0 in 5 runs (2 earlier in tuning).

---
# Round 3 (critic: "slightly worse than Contra", 65%)

## 1. Crossfire on landing at x≈4200-4270 → one warning on screen at a time
Before an enemy starts its warning it must claim a scene-wide shot lock (`Enemy.claimTell`). It holds the lock through its warning, its burst and 350 ms of quiet (`Enemy.SHOT_GAP`); a blocked shooter retries about 250 ms later. This covers riflemen, turrets, drones and gunner soldiers, so two dodges can no longer conflict (jumping one shot while going prone for another). The boss is not included.
Deaths in the 4200-4270 zone: 3 of 12 in the critic's runs → **0 of 7** in my 7 final bot runs.

## 2. Soldiers one tier down → 14 px head margin (hittest spots added)
Walkers are now hittable from **14 px above the head** as well as 14 px below the feet.

| target (rifleman x, y) | player position | standing level shot | prone shot | walking diagonal-down |
|---|---|---|---|---|
| 4370 / 4420, 168 (14 px below the shelf at 4200-4330) | shelf, feet y154 | HIT (all 3 distances) | HIT | - |
| 1960 / 2000, 168 (32 px below the cliff) | cliff top, feet y136 | miss (would need a 30 px margin) | **HIT** (all 3 distances) | HIT |

A 32 px drop is now a prone shot or a walking diagonal-down shot, as in Contra. A 14 px drop is a plain level shot. The round-2 spots still pass.

## 3. Dead air → the ambient stream never fully stops mid-stage
- The breathers at 2300 (S capsule) and 3460 (bridge into the base) are now light streams (cap 2).
- Lone drones added at 2280, 2460, 3440 and 4540.
- Pre-boss: the stream runs right up to the arena lock (it stops by itself when the boss appears).
- All stream intervals were cut by about 30%. There's a 35% chance a stream grunt brings a partner 0.45 s behind.
- The first half stays easy: before camera x 1800 the grunts only charge, and there are no rear spawns before x 2000. Streams with `left: 0` never fall back to a rear spawn, and grunts now also enter along bridges over chasms.

| (god-mode bot, 0.1 s sampling) | R2 final | R3 |
|---|---|---|
| frames with no enemy and no enemy bullet | 47-48% | **37-39%** |
| longest empty stretch | 5-6 s (2000, 3230, pre-boss) | 3.3-3.7 s |
| mean enemies on screen | 0.63-0.85 | 0.91-1.03 |
| kills on the way to the boss | ~60 | ~110-117 (no-god bot) |
| time to boss | 53-55 s | 54-55 s |

## Difficulty (average-player bot, no god, 4 lives)
| | R1 | R2 final | R3 |
|---|---|---|---|
| reached the boss | 0/4 | 5/5 | **5/5** (+1 recorded run: reached, 2 deaths) |
| deaths per run | 4 (game over) | 1-3 | **1** each |
| where | everywhere x ≤ 3850 | 2105 rifleman (every run), 4267-4546 gauntlet | turret at 3440 (×3), drones at 2150/2310 (×2). 0 deaths at 2105 and 0 in the 4200-4270 crossfire zone |

---
# Round 4 (critic: "on par with Contra stage 1", 70%)

## 1. Final stretch fizzled → a final push into the WARNING
- From 4720 the stream thickens (every 550-900 ms, cap 4, 20% from behind).
- Riflemen on both catwalks (4720 and 4790, y110) and on the rise (4860).
- A drone pair at 4800, a 4-grunt wave at 5000, a rifleman at 5140, a drone at 5200 and a 3-grunt wave at 5260, right up to the arena lock.
- Non-boss enemies hold fire once the boss is up (the boss owns the danger), and the stream stops by itself.

| god bot, player x 4600-5200 | before (R3 runs) | after (R4 runs) |
|---|---|---|
| longest stretch with no enemy and no enemy bullet | 3.4 s / 5.4 s | **1.3 s / 1.9 s** |
| kills in that stretch | 8 / 8 | **20 / 20** |

## 2. The 24 px step at x≈560 → auto-vault
- Steps of 11-26 px that you run into on the ground are vaulted with a small hop that just clears the lip (`Game.stepUp`, player only, not while prone).
- Test: holding right from x=470, the sheep reaches x=552, hops for about 0.25 s at full run speed, and lands on y144 at x≈575. It never stops.
- This also fixes the 24 px rises at 3260 and 4730 and the 18 px one at 2180. Steps under 10 px were already walked up.
- Terrain builder: an intermediate 12 px step at 552 would still look nicer, but it's no longer needed for feel.

## 2b. No kill farming
- The ambient stream dries up after **6 s without camera progress**. Test at x=500 holding fire: 7 kills in the first 6 s, then **0 in the next 14 s** (before: an endless stream; the critic farmed 190 kills).
- Scripted waves still arrive, and the stream resumes as soon as the camera moves.

## 3. Stage clear → results screen
Boss death → STAGE CLEAR card → 3.2 s → the sheep runs off into the base → 3.6 s → `showResults()`.
- The lives bonus (lives × 2000) is added to the score.
- `stage-end` is emitted with `{score, kills, shots, hits, accuracy, lives, livesBonus, time, deaths, continues, hi, next:'STAGE 2 COMING SOON'}` (also in `window.__sheep.results`).
- The HUD's existing tally card counts up the score. Game draws fallback lines under it: kills + accuracy, lives bonus, time, STAGE 2 COMING SOON. A HUD owner can take these over with `hooked.results = true`.
- Holds for Enter / fire / jump (accepted after 1.2 s) or 6 s, then fades to the Title screen.
- Accuracy = player bullets that hit something ÷ bullets fired (spread pellets count individually).
- Test run: score 6900 (bonus 6000), 8 kills, 23 bullets, 9 hits = 39%, time 0:17, and Enter → Title works.

## Difficulty (average-player bot, no god)
| | R3 | R4 |
|---|---|---|
| reached the boss | 5/5 | **5/5** |
| deaths per run | 1 | 1-2 (cliff turret at 1880 ×2, drones around 2150-2370 ×4, drone at 3417, turret at 3440). **0 in the final push** |
| kills per run | ~110-117 | ~121-129 |
| whole stage: frames with no enemy and no enemy bullet | 37-39% | 38-39% |
