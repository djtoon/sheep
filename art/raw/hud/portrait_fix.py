# portrait 28x22: hand-cleaned from the downsampled generation (art/raw/hud/portrait_gen_2.png -> pq_2_1.png),
# redrawn pixel by pixel after the mockup portrait + hero sheet: round eyes with pupils + glint, angry brows,
# rounded muzzle with frown, wool cap framing the face, headband knot trailing left, grey ears.
ROWS = [
 'BBBBBBBBBBBBBBBBBBBBBBBBBBBB',
 'BBBBBBBBKKKBKKKBKKKBBBBBBBBB',
 'BBBBBBKKWWWKWWWKWWWKKBBBBBBB',
 'BBBBBKWWWWWWWWwWWWWWWKBBBBBB',
 'BBBBKWWwWWWWwWWWWwWWWWKBBBBB',
 'BBBKWWwwWWwwwWWwwWWwWWWWKBBB',
 'BBBKhhhhhhhhhhhhhhhhhhhhhKBB',
 'BKKKRRRRRRRRRRRRRRRRRRRRRRKB',
 'KRRKRRRRRRRRRRRRRRRRRRRRRKBB',
 'KRrKrrrrrrrrrrrrrrrrrrrrrKBB',
 'KRRBKfFFKKFFFFFFFFFFKKFFgKBB',
 'BKRrKfFFFFKKKFFKKKFFFFFgKBBB',
 'BKKKKfFKKEEEKKKKEEEKKFFgKKKB',
 'KFppKfFKEEEEEKKEEEEEKFFgppFK',
 'KgggKfFKEEEKEKKEKEEEKFFgggFK',
 'BKKKKFFKEEKKEKKEKKEEKFFgKKKB',
 'WWWWKgFFKEEEKFFKEEEKFFgKWWWW',
 'WwWvvKgFFKKKFFFFKKKFFgKvvWwW',
 'wWWWvKgFFfffgffgfffFFgKvWWWw',
 'WWwwvvKgFffffKKffffFgKvvwWWW',
 'vwwwwvvKgfffKffKfffgKvvwwwwv',
 'wvvvvvwwKKggffffggKKwwwvvvvv',
]
def grid():
    for r in ROWS: assert len(r) == 28, r
    return ROWS
if __name__ == '__main__':
    print('\n'.join(grid()))
