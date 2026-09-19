# Backdrop colour targets (measured)

Measured with art/raw/world/measure.py: frames box-resized to 480x270 game px; HSV value (V) and saturation (S) median [10-90%], hue = saturation-weighted circular mean (deg), lc = median std of V in 8x8 game-px windows. Rects hand-picked per band (see REFS/OURS in measure.py).

## Mockups
```
2b74 far  V 0.91 [0.44-0.97] | S 0.67 [0.29-0.71] | hue 206 | lc 0.064
2b74 mid  V 0.53 [0.31-0.91] | S 0.53 [0.25-0.70] | hue 197 | lc 0.099
2b74 near V 0.24 [0.05-0.64] | S 0.60 [0.14-0.93] | hue 126 | lc 0.175
c0f6 far  V 0.60 [0.15-0.91] | S 0.57 [0.42-0.80] | hue 190 | lc 0.193
c0f6 mid  V 0.48 [0.42-0.72] | S 0.56 [0.32-0.68] | hue 197 | lc 0.033
c0f6 near V 0.23 [0.08-0.59] | S 0.43 [0.13-0.78] | hue 127 | lc 0.136
369c far  V 0.65 [0.39-0.87] | S 0.63 [0.25-0.72] | hue 199 | lc 0.091
369c mid  V 0.53 [0.39-0.83] | S 0.64 [0.39-0.78] | hue 198 | lc 0.067
369c near V 0.23 [0.06-0.60] | S 0.50 [0.11-0.86] | hue 140 | lc 0.169
fd55 far  V 0.71 [0.41-0.92] | S 0.70 [0.32-0.81] | hue 199 | lc 0.067
fd55 mid  V 0.45 [0.16-0.69] | S 0.72 [0.45-0.94] | hue 176 | lc 0.130
fd55 near V 0.27 [0.07-0.65] | S 0.59 [0.17-0.91] | hue 113 | lc 0.179
```

Target ranges drawn from these: far V 0.60-0.91, S 0.57-0.70, hue 190-206, lc 0.06-0.09 (c0f6 0.19 outlier). mid V 0.45-0.53, S 0.53-0.72, hue 176-198, lc 0.03-0.13. near (terrain, not backdrop) V 0.23-0.27, S 0.43-0.60, hue 113-140.

## Ours before (round 9)
```
900 far  V 0.86 [0.38-0.96] | S 0.46 [0.40-0.65] | hue 197 | lc 0.063
900 mid  V 0.48 [0.20-0.72] | S 0.47 [0.29-0.72] | hue 162 | lc 0.131
900 near V 0.20 [0.04-0.51] | S 0.49 [0.17-0.83] | hue 132 | lc 0.139
2300 far  V 0.90 [0.86-0.96] | S 0.46 [0.41-0.65] | hue 202 | lc 0.014
2300 mid  V 0.63 [0.35-0.96] | S 0.45 [0.20-0.65] | hue 192 | lc 0.058
2300 near V 0.25 [0.04-0.55] | S 0.50 [0.19-0.80] | hue 143 | lc 0.143
3900 far  V 0.73 [0.68-0.96] | S 0.51 [0.39-0.60] | hue 200 | lc 0.022
3900 mid  V 0.46 [0.28-0.95] | S 0.40 [0.22-0.64] | hue 182 | lc 0.097
3900 near V 0.23 [0.07-0.44] | S 0.34 [0.06-0.75] | hue 145 | lc 0.099
```

## Ours after (round 10)
```
900 far  V 0.86 [0.38-0.96] | S 0.55 [0.48-0.65] | hue 200 | lc 0.063
900 mid  V 0.42 [0.14-0.71] | S 0.57 [0.37-0.83] | hue 170 | lc 0.139
900 near V 0.20 [0.04-0.51] | S 0.49 [0.17-0.83] | hue 133 | lc 0.140
2300 far  V 0.90 [0.86-0.96] | S 0.55 [0.49-0.65] | hue 203 | lc 0.014
2300 mid  V 0.52 [0.28-0.96] | S 0.60 [0.26-0.71] | hue 192 | lc 0.068
2300 near V 0.25 [0.04-0.53] | S 0.53 [0.18-0.83] | hue 150 | lc 0.139
3900 far  V 0.73 [0.67-0.96] | S 0.60 [0.49-0.63] | hue 201 | lc 0.026
3900 mid  V 0.40 [0.16-0.95] | S 0.53 [0.20-0.82] | hue 192 | lc 0.074
3900 near V 0.21 [0.06-0.43] | S 0.34 [0.06-0.76] | hue 148 | lc 0.095
```

Transforms (build.py): MIDTINT #22688e mixed into mid layers (cliffs 0.30+, midtrees 0.26, canopy 0.20, near 0.24 w/ contrast 0.85, outposts 0.34/0.30/0.24); FARTINT #4c92c6 0.40 into far mountains with contrast 1.25, 0.34 into hills/far cliffs.

## Round 12: depth steps (per-layer opaque-pixel medians, measure_layers.py)
```
A near         V 0.36  S 0.49  lc 0.089
A midset       V 0.47  S 0.57  lc 0.053
A canopy       V 0.38  S 0.69  lc 0.071
A outpost2     V 0.37  S 0.50  lc 0.101
B cliffs       V 0.60  S 0.46  lc 0.027
B midtrees     V 0.54  S 0.39  lc 0.032
B outpost1     V 0.62  S 0.48  lc 0.027
C farcliffs    V 0.82  S 0.37  lc 0.007
C hills        V 0.70  S 0.37  lc 0.008
C outpost0     V 0.73  S 0.34  lc 0.018
far mtns       V 0.60  S 0.62  lc 0.015
```
Round-11 before (same metric): near V 0.36/S .49 not re-run; frame-level x=2300 left jungle band V 0.34 S 0.74 lc .087 -> V 0.54 S 0.43 lc .030.

## Round 12 frame measures (re-picked rects)
```
900 far  V 0.96 [0.86-0.96] | S 0.60 [0.48-0.65] | hue 202 | lc 0.015
900 mid  V 0.51 [0.27-0.96] | S 0.59 [0.40-0.76] | hue 179 | lc 0.109
900 near V 0.13 [0.02-0.43] | S 0.43 [0.13-0.75] | hue 127 | lc 0.107
2300 far  V 0.73 [0.65-0.96] | S 0.63 [0.30-0.65] | hue 202 | lc 0.049
2300 mid  V 0.46 [0.28-0.64] | S 0.48 [0.28-0.62] | hue 188 | lc 0.087
2300 bg1  V 0.54 [0.50-0.67] | S 0.43 [0.34-0.52] | hue 190 | lc 0.030
2300 near V 0.17 [0.03-0.77] | S 0.45 [0.14-0.80] | hue 142 | lc 0.146
3900 far  V 0.71 [0.31-0.96] | S 0.61 [0.49-0.76] | hue 190 | lc 0.108
3900 mid  V 0.55 [0.20-0.63] | S 0.46 [0.18-0.59] | hue 191 | lc 0.110
3900 near V 0.15 [0.02-0.43] | S 0.42 [0.11-0.82] | hue 140 | lc 0.114
```
