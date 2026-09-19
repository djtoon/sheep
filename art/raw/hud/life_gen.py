# procedural 17x15 life icon: a cream wool ball (dominant), grey face front-right, big eyes, thin red band -> row strings
import numpy as np

def life_rows():
    W, H = 17, 15
    yy, xx = np.mgrid[0:H, 0:W]
    P = np.full((H, W), '.', dtype='<U1')
    def ell(cx, cy, rx, ry): return ((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2 <= 1
    def ring(m):
        r = np.zeros_like(m)
        for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            r |= np.roll(np.roll(m, dy, 0), dx, 1)
        return r & ~m
    wool = (ell(4.6, 5.4, 3.5, 3.4) | ell(8.6, 3.6, 3.6, 2.9) | ell(12.4, 4.8, 3.3, 3.2) | ell(4.6, 9.6, 3.7, 3.5)
            | ell(8.0, 11.0, 3.8, 2.8) | ell(13.4, 8.6, 2.6, 3.0))
    wool &= (xx >= 1) & (xx <= 15) & (yy >= 1) & (yy <= 13)
    face = ell(10.6, 9.4, 3.9, 3.7) & (yy <= 13) & (xx <= 15)
    sil = wool | face
    P[ring(sil)] = 'K'
    # wool: light top-left, mid lower, shade on bottom edges, a few curl marks
    P[wool] = 'W'
    P[wool & (yy >= 8)] = 'w'
    P[wool & ~np.roll(wool, -1, 0)] = 'v'
    P[wool & ~np.roll(wool, -1, 1) & (yy >= 6)] = 'v'
    for x, y in [(3, 3), (6, 2), (10, 2), (13, 3), (2, 7), (5, 7), (3, 10), (6, 12), (14, 6)]:
        if wool[y, x]: P[y, x] = 'w'
    # face
    P[face] = 'F'
    P[ring(face) & wool] = 'K'
    P[face & ~np.roll(face, -1, 0)] = 'g'
    P[face & ~np.roll(face, -1, 1)] = 'g'
    P[face & (yy >= 11) & (yy <= 12) & (xx >= 9) & (xx <= 13)] = 'f'
    # thin headband across the wool top + short tail on the left
    for x in range(1, 16):
        if sil[5, x] and not face[5, x]: P[5, x] = 'R'
    P[5, 0] = 'R'; P[6, 0] = 'r'; P[4, 0] = 'K'; P[7, 0] = 'K'
    # eyes: 3x3 whites, pupils toward the centre-bottom
    for ex in (7, 11):
        for dx in range(3):
            for dy in range(3): P[7 + dy, ex + dx] = 'E'
    P[8, 9] = 'K'; P[9, 9] = 'K'; P[8, 11] = 'K'; P[9, 11] = 'K'
    P[6, 7:14] = np.where(face[6, 7:14], 'K', P[6, 7:14])     # brow line over the eyes
    P[7, 10] = 'F'; P[8, 10] = 'F'; P[9, 10] = 'F'
    P[11, 10] = 'g'; P[11, 12] = 'g'
    return [''.join(r) for r in P]

if __name__ == '__main__':
    print('\n'.join(life_rows()))
