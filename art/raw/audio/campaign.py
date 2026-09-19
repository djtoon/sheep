# Campaign audio (stages 2-3, bosses 2-3, story intro/ending, new-enemy SFX).
# Executed inside synth.py's namespace (shares Track, instruments, parse, etc.) - run synth.py, not this file.
R16 = '. . . . . . . . . . . . . . . .'

def stage2():  # "Night Base" - D minor, 158 BPM: tense, driving, darker; syncopated low hook
    tk = Track(158, 4, 40)
    chords = ['Dm', 'Dm', 'Bb', 'A'] + \
        ['Dm', 'Dm', 'Bb', 'C', 'Dm', 'Dm', 'Gm', 'A', 'Dm', 'Dm', 'Bb', 'C', 'Dm', 'Dm', 'Gm A', 'Dm'] + \
        ['Bb', 'F', 'C', 'Dm', 'Bb', 'F', 'Gm', 'A', 'Bb', 'C', 'Dm', 'Bb', 'Gm', 'A', 'A', 'A'] + \
        ['Dm', 'Dm', 'Eb', 'Dm', 'Dm', 'Dm', 'Eb', 'Dm A']
    hook = 'D5 - - D5 - - F5 - A5 - - - G5 - F5 -'
    A = [hook, 'E5 - - - F5 - - - D5 - - - - - . .', 'D5 - - D5 - - F5 - Bb5 - - - A5 - G5 -', 'A5 - - - G5 - - - E5 - - - C5 - - -',
         hook, 'E5 - - - F5 - - - A5 - - - D6 - - -', 'D6 - - - C6 - - - Bb5 - - - G5 - - -', 'C#6 - - - - - - - A5 - - - E5 - - -']
    A2 = A[:6] + ['Bb5 - - - A5 - - - G5 - - - E5 - - -', 'D5 - - - - - - - - - - - . . . .']
    B = ['F5 - - - - - D5 - F5 - - - Bb5 - - -', 'A5 - - - - - - - C6 - - - A5 - - -', 'G5 - - - - - E5 - G5 - - - C6 - - -',
         'A5 - - - - - - - - - - - . . . .', 'F5 - - - - - D5 - F5 - - - Bb5 - - -', 'C6 - - - - - - - A5 - - - F5 - - -',
         'Bb5 - - - A5 - - - G5 - - - D5 - - -', 'E5 - - - - - - - C#5 - - - A4 - - -', 'D6 - - - - - - - Bb5 - - - F5 - - -',
         'E6 - - - - - - - C6 - - - G5 - - -', 'F6 - - - E6 - - - D6 - - - A5 - - -', 'D6 - - - - - - - F6 - - - - - - -',
         'D6 - - - - - - - Bb5 - - - G5 - - -', 'C#6 - - - - - - - E6 - - - - - - -', 'A5 - - - - - - - - - - - - - - -', R16]
    C = ['D4 . D4 . F4 . D4 . G#4 . A4 . D5 . C5 .', 'D4 . D4 . F4 . D4 . A4 - G4 . F4 . E4 .',
         'Eb4 . Eb4 . G4 . Eb4 . Bb4 . A4 . G4 . F4 .', 'D4 . D4 . F4 . D4 . A4 - - - C#5 - D5 -']
    tk.notes('stab', parse(['D4 . . D4 . . D4 . . D4 . . F4 . E4 .', 'D4 . . D4 . . D4 . . D4 . . A4 . G4 .',
                            'D4 . . D4 . . D4 . . D4 . . F4 . E4 .', R16]), i_stab)
    tk.notes('riff', parse([R16, R16, R16, 'A4 - - A4 - - A4 - C#5 - - - E5 - - -']), i_riff)
    tk.notes('lead', parse(A + A2, 4), i_lead)
    tk.notes('pad', parse([tr(b, -12) for b in A2], 12), i_pad)
    tk.notes('flute', parse(B, 20), i_flute)
    tk.notes('arp', arp(chords, range(28, 36), idx=(0, 2, 1, 3), base=62), i_stab)
    tk.notes('riff', parse(C + [tr(b, 12) for b in C], 36), i_riff)
    tk.notes('riff2', parse([tr(b, -12) for b in C], 40), i_riff)
    tk.notes('stab', stabs(chords, range(4, 20), steps=(3, 6, 11, 14)), i_stab)
    drive = 'R - O - R R O - R - O - R R O -'; gallop = 'R R O R R O R O R R O R R O R O'
    tk.notes('bass', bass_line(chords, [gallop, gallop, gallop, 'R - R - R - R - O - O - O O O O'] + [gallop] * 16 +
                               [drive] * 15 + ['R - - - R - - - O - - - O O O O'] + [gallop] * 8), i_bass)
    Ab = 'Kh . h K Sh . h . Kh . Kh K Sh . h h'
    f1 = 'Kh . h K Sh . h . Kh . S . S S S S'; f2 = 'Kh . h . Sh . h . K . T T t t S S'
    Bb = 'Kh . o . Sh . h K . K h . Sh . o .'; Br = 'Kh h h h KSh h h h Kh h h h KSh h h h'
    roll8 = 'KS . S . KS . S . KS . S . KS . S S'; roll16 = 'KS S S S KS S S S KS S S S KS S S S'
    c = lambda bar: 'C' + bar
    tk.drums(drums_parse(['Kh . h . h . h . Kh . h . h . h .', 'Kh . h . h . h . Kh . h . Sh . S S', Ab, roll16] +
                         [c(Ab), Ab, Ab, f1, Ab, Ab, Ab, f2, c(Ab), Ab, Ab, f1, Ab, Ab, Ab, f2] +
                         [c(Bb), Bb, Bb, Bb, Bb, Bb, Bb, f2, c(Bb), Bb, Bb, Bb, Bb, Bb, roll8, roll16] +
                         [c(Br), Br, Br, f1, c(Br), Br, roll8, roll16]))
    return tk.mix(MIX, lead_delay=('lead', 'flute'))

def stage3():  # "Sub-Level B" - E minor, 146 BPM: eerie arps over a pounding kick, B-section turns heroic
    tk = Track(146, 4, 40)
    chords = ['Em', 'Em', 'C', 'B'] + ['Em', 'C', 'Am', 'B'] * 4 + \
        ['C', 'D', 'G', 'Em', 'C', 'D', 'B', 'B', 'C', 'D', 'G', 'Em', 'Am', 'B', 'E', 'E'] + ['Em', 'Em', 'C', 'C', 'Am', 'Am', 'B', 'B']
    A = ['B5 - - - - - - - - - - - G5 - - -', 'C6 - - - - - - - - - - - E5 - - -', 'A5 - - - - - - - C6 - - - E6 - - -',
         'D#6 - - - - - - - - - - - F#5 - - -', 'B5 - - - - - - - E6 - - - G6 - - -', 'F#6 - - - E6 - - - - - - - C6 - - -',
         'A5 - - - C6 - - - B5 - - - A5 - - -', 'B5 - - - - - - - - - - - . . . .']
    B = ['E5 - - G5 - - C6 - - - - - B5 - C6 -', 'D6 - - - - - A5 - F#5 - - - A5 - - -', 'B5 - - D6 - - G6 - - - - - F#6 - D6 -',
         'E6 - - - - - - - - - - - . . B5 -', 'C6 - - E6 - - G6 - - - - - E6 - C6 -', 'D6 - - - - - F#6 - A6 - - - F#6 - D6 -',
         'D#6 - - - - - - - F#6 - - - - - - -', 'B5 - - - - - - - - - - - . . . .', 'E6 - - - D6 - - - C6 - - - G5 - - -',
         'F#6 - - - E6 - - - D6 - - - A5 - - -', 'G6 - - - F#6 - - - D6 - - - B5 - - -', 'E6 - - - - - - - B5 - - - G5 - - -',
         'A5 - - - C6 - - - E6 - - - A6 - - -', 'F#6 - - - - - - - D#6 - - - B5 - - -', 'G#6 - - - - - - - - - - - E6 - - -',
         'B5 - - - - - - - - - - - . . . .']
    C = [R16] * 6 + ['B4 . B4 . D#5 . B4 . F#5 . B4 . A5 . F#5 .', 'B5 - - - A5 - - - G5 - - - F#5 - - -']
    tk.notes('flute', parse(A + A, 4), i_flute)
    tk.notes('pad', parse([tr(b, -7) for b in A], 12), i_pad)
    tk.notes('lead', parse(B, 20), i_lead)
    tk.notes('riff', parse(C, 36), i_riff)
    tk.notes('arp', arp(chords, list(range(0, 20)) + list(range(36, 44)), idx=(0, 1, 2, 3, 2, 1), base=64), i_stab, 1.15)
    tk.notes('stab', stabs(chords, range(20, 36), steps=(2, 6, 10, 14)), i_stab)
    pound = 'R - R - R - R - R - R - O - O -'
    tk.notes('bass', bass_line(chords, ['R - - - - - - - R - - - - - - -'] * 2 + [pound, 'R R O R R O R O R R O R R O R O'] +
                               [pound] * 16 + ['R - O - R R O - R - O - R R O -'] * 16 + [pound] * 8), i_bass)
    P = 'Kh . h . KSh . h . Kh . h K KSh . h .'
    Ph = 'Kh . o . KSh . h K Kh . o . KSh . h h'
    fl = 'Kh . h . KSh . h . K . T T t t S S'
    K4 = 'K . h . K . h . K . h . K . h .'
    tk.drums(drums_parse(['K . . . K . . . K . . . K . . .', 'K . . . K . . . K . . . K . . .', K4, 'KS . S . KS . S . KS S S S KS S S S'] +
                         ['C' + P, P, P, P, P, P, P, fl, 'C' + P, P, P, P, P, P, P, fl] +
                         ['C' + Ph, Ph, Ph, Ph, Ph, Ph, Ph, fl, 'C' + Ph, Ph, Ph, Ph, Ph, Ph, 'KS . S . KS . S . KS . S . KS . S S', fl] +
                         ['C' + K4, K4, K4, K4, K4, K4, 'KS . S . KS . S . KS . S . KS . S S', 'KS S S S KS S S S KS S S S KS S S S']))
    return tk.mix(MIX, lead_delay=('lead', 'flute'))

def boss2():  # D minor, 178 BPM: harmonic-minor menace, riff middle, rising last line
    tk = Track(178, 0, 16)
    chords = ['Dm', 'Dm', 'Bb', 'A', 'Dm', 'Dm', 'Eb', 'A', 'Gm', 'Gm', 'Dm', 'Dm', 'Bb', 'C', 'A', 'A']
    lead = ['D5 - - - A5 - - - G#5 - - - A5 - - -', 'F5 - - - E5 - - - D5 - - - C#5 - - -', 'D5 - - - F5 - - - Bb5 - - - A5 - - -',
            'A5 - - - - - - - E5 - - - C#5 - - -']
    riff = ['D5 . D5 . F5 . D5 . A5 . D5 . G#5 . A5 .', 'D5 . D5 . F5 . D5 . C6 - A5 . G#5 . A5 .',
            'Eb5 . Eb5 . G5 . Eb5 . Bb5 . Eb5 . A5 . G5 .', 'C#5 . C#5 . E5 . C#5 . A5 - - - G5 - E5 -']
    end = ['G5 - - - - - - - Bb5 - - - D6 - - -', 'C6 - - - Bb5 - - - A5 - - - G5 - - -', 'A5 - - - - - - - F5 - - - D5 - - -',
           'E5 - - - F5 - - - G5 - - - A5 - - -', 'Bb5 - - - - - - - D6 - - - F6 - - -', 'E6 - - - - - - - G6 - - - E6 - - -',
           'C#6 - - - - - - - E6 - - - - - - -', 'A5 - - - G5 - - - E5 - - - C#5 - - -']
    tk.notes('lead', parse(lead, 0), i_lead); tk.notes('riff', parse(riff, 4), i_riff); tk.notes('riff2', parse([tr(b, -12) for b in riff], 4), i_riff)
    tk.notes('lead', parse(end, 8), i_lead)
    tk.notes('arp', arp(chords, list(range(0, 4)) + list(range(8, 16)), idx=(0, 2, 1, 3, 2, 1), base=60), i_stab)
    tk.notes('bass', bass_line(chords, ['R R O R 1 R O R R R O R 1 R O 1'] * 15 + ['R R O R R O R O O O 8 8 O O 8 8']), i_bass)
    Bt = 'Kh h h h Sh h K h Kh h K h Sh h K h'; Bf = 'Kh h h h Sh h K h S S T T t t S S'
    tk.drums(drums_parse(['C' + Bt, Bt, Bt, Bf, 'C' + Bt, Bt, Bt, 'KS . S . KS . S . KS S S S KS S S S',
                          'C' + Bt, Bt, Bt, Bf, 'C' + Bt, Bt, Bt, 'KS S S S KS S S S KS S S S KS S S S']))
    return tk.mix(MIX)

def boss3():  # the finale - E minor, 188 BPM (fastest): epic line, riff section, heroic climax with an octave shimmer
    tk = Track(188, 0, 24)
    chords = ['Em', 'Em', 'C', 'D', 'Em', 'Em', 'C', 'B', 'Am', 'Am', 'Em', 'Em', 'C', 'D', 'B', 'B', 'C', 'D', 'Em', 'Em', 'C', 'D', 'B', 'B']
    A = ['E5 - - - B5 - - - - - - - A5 - B5 -', 'G5 - - - F#5 - - - E5 - - - D5 - E5 -', 'C6 - - - - - - - B5 - - - A5 - - -',
         'D6 - - - - - - - A5 - - - F#5 - - -', 'E6 - - - - - - - D6 - - - B5 - - -', 'G6 - - - F#6 - - - E6 - - - D6 - - -',
         'E6 - - - - - - - C6 - - - G5 - - -', 'F#6 - - - - - - - D#6 - - - B5 - - -']
    R = ['A4 . A4 . C5 . A4 . E5 . A4 . D#5 . E5 .', 'A4 . A4 . C5 . A4 . F5 - E5 . D5 . C5 .',
         'E5 . E5 . G5 . E5 . B5 . E5 . A#5 . B5 .', 'E5 . E5 . G5 . E5 . C6 - B5 . A5 . G5 .']
    M = ['G5 - - - - - - - C6 - - - E6 - - -', 'F#6 - - - - - - - D6 - - - A5 - - -', 'B5 - - - - - - - D#6 - - - F#6 - - -',
         'B6 - - - - - - - - - - - A6 - F#6 -']
    H = ['G6 - - - - - - - E6 - - - C6 - - -', 'A6 - - - - - - - F#6 - - - D6 - - -', 'B6 - - - - - - - G6 - - - E6 - - -',
         'E6 - - - F#6 - - - G6 - - - A6 - - -', 'G6 - - - - - - - E6 - - - C6 - - -', 'F#6 - - - - - - - A6 - - - - - - -',
         'D#6 - - - - - - - F#6 - - - B6 - - -', 'A6 - - - F#6 - - - D#6 - - - B5 - - -']
    tk.notes('lead', parse(A + [R16] * 4 + M[:3] + [tr(M[3], -12)] + [tr(b, -12) for b in H]), i_lead)
    tk.notes('pad', parse(H, 16), i_pad, 0.9)
    tk.notes('riff', parse(R, 8), i_riff); tk.notes('riff2', parse([tr(b, 7) for b in R], 8), i_riff)
    tk.notes('arp', arp(chords, list(range(0, 8)) + list(range(12, 24)), idx=(0, 1, 2, 3, 2, 1), base=60), i_stab)
    tk.notes('stab', stabs(chords, range(16, 24), steps=(0, 3, 6, 10, 12, 14), ivs=(0, 1, 2)), i_stab, 0.8)
    tk.notes('bass', bass_line(chords, ['R R O R 1 R O R R R O R 1 R O 1'] * 7 + ['R R O R R O R O O O 8 8 O O 8 8'] +
                               ['R R O R R O R O R R O R R O R O'] * 8 + ['R R O R 5 R O R R R O R 5 R O O'] * 7 + ['R R O R R O R O O O 8 8 O O 8 8']), i_bass)
    Bt = 'Kh h Kh h Sh h K h Kh h Kh h Sh h K h'; Bf = 'Kh h h h Sh h K h S S T T t t S S'
    tk.drums(drums_parse(['C' + Bt, Bt, Bt, Bf, Bt, Bt, Bt, 'KS . S . KS . S . KS S S S KS S S S',
                          'C' + Bt, Bt, Bt, Bf, Bt, Bt, Bt, 'KS S S S KS S S S KS S S S KS S S S',
                          'C' + Bt, Bt, Bt, Bf, 'C' + Bt, Bt, Bt, 'KS S S S KS S S S KS S S S KS S S S']))
    return tk.mix(MIX)

def intro_theme():  # comic intro: presidential brass fanfare (Bb major march) -> urgent G-minor action, loops
    tk = Track(112, 1, 16)
    chords = ['Bb'] + ['Bb', 'Eb Bb', 'F', 'Bb', 'Gm', 'Eb F', 'Bb Gm', 'C F'] + ['Gm', 'Gm', 'Eb', 'F', 'Gm', 'Gm', 'Eb', 'D']
    P = ['F4 - - F4 Bb4 - - - D5 - - - F5 - - -', 'G5 - - - Eb5 - - - F5 - - - D5 - - -', 'C5 - - C5 F5 - - - A5 - - - C6 - - -',
         'Bb5 - - - - - - - - - - - F5 - - -', 'G5 - - G5 Bb5 - - - D6 - - - Bb5 - - -', 'Eb6 - - - - - - - C6 - - - A5 - - -',
         'Bb5 - - - D6 - - - D6 - - - Bb5 - - -', 'C6 - - - - - - - C6 - - - A5 - - -']
    Hm = ['D4 - - D4 F4 - - - Bb4 - - - D5 - - -', 'Eb5 - - - Bb4 - - - D5 - - - Bb4 - - -', 'A4 - - A4 C5 - - - F5 - - - A5 - - -',
          'F5 - - - - - - - - - - - D5 - - -', 'D5 - - D5 G5 - - - Bb5 - - - G5 - - -', 'G5 - - - - - - - A5 - - - F5 - - -',
          'F5 - - - Bb5 - - - Bb5 - - - G5 - - -', 'G5 - - - - - - - A5 - - - F5 - - -']
    Q = ['G4 . G4 . Bb4 . G4 . D5 . G4 . C5 . Bb4 .', 'G4 . G4 . Bb4 . G4 . F5 - D5 . C5 . Bb4 .',
         'Eb5 . Eb5 . G5 . Eb5 . Bb5 . Eb5 . A5 . G5 .', 'F5 . F5 . A5 . F5 . C6 - - - A5 - F5 -']
    QL = ['D6 - - - - - - - Bb5 - - - G5 - - -', 'A5 - - - Bb5 - - - C6 - - - D6 - - -', 'Eb6 - - - D6 - - - C6 - - - Bb5 - - -',
          'A5 - - - - - - - F#5 - - - D5 - - -']
    tk.notes('lead', parse(P, 1), i_lead); tk.notes('pad', parse(Hm, 1), i_pad, 1.1)
    tk.notes('riff', parse(Q + [tr(b, -12) for b in Q[:3]] + ['D4 . D4 . F#4 . D4 . A4 - - - F#4 - D4 -'], 9), i_riff)
    tk.notes('lead', parse(QL, 13), i_lead)
    tk.notes('stab', stabs(chords, range(1, 9), steps=(3, 6, 11, 14)), i_stab)
    tk.notes('bass', bass_line(chords, ['R - - - - - - - R - - - R - R -'] + ['R - - - 5 - - - R - - - 5 - - -'] * 8 +
                               ['R R O R R O R O R R O R R O R O'] * 8), i_bass)
    M = 'K . s s S . s . K . s s S s S s'; D = 'Kh . h K Sh . h . Kh . Kh K Sh . h h'
    tk.drums(drums_parse(['S s S s S s S s S S S S S S S S'] + ['C' + M, M, M, M, M, M, M, 'KS . s s S . s . KS S S S S S S S'] +
                         ['C' + D, D, D, 'Kh . h K Sh . h . Kh . S . S S S S', D, D, D, 'KS S S S KS S S S KS S S S KS S S S']))
    return tk.mix(MIX)

def ending_theme():  # victorious & warm: 4-bar fanfare, then a gentle credits loop (F major, 100 BPM)
    tk = Track(100, 4, 16)
    chords = ['F', 'Bb', 'C', 'F'] + ['F', 'C', 'Dm', 'Bb', 'F', 'C', 'Bb', 'C', 'Dm', 'Am', 'Bb', 'F', 'Gm', 'C', 'F', 'F']
    fan = ['C5 - - C5 F5 - - - A5 - - - C6 - - -', 'D6 - - - C6 - - - Bb5 - - - A5 - - -', 'G5 - - - A5 - - - Bb5 - - - E5 - - -',
           'F5 - - - - - - - - - - - . . . .']
    fanh = ['A4 - - A4 C5 - - - F5 - - - A5 - - -', 'F5 - - - F5 - - - D5 - - - D5 - - -', 'E5 - - - F5 - - - G5 - - - C5 - - -',
            'A4 - - - - - - - - - - - . . . .']
    E = ['A5 - - - - - G5 - F5 - - - C5 - - -', 'E5 - - - - - D5 - C5 - - - G5 - - -', 'F5 - - - - - E5 - D5 - - - A5 - - -',
         'Bb5 - - - - - - - A5 - - - G5 - - -', 'A5 - - - - - G5 - F5 - - - C6 - - -', 'C6 - - - - - Bb5 - A5 - - - G5 - - -',
         'F5 - - - - - D5 - F5 - - - Bb5 - - -', 'A5 - - - - - - - G5 - - - - - - -', 'A5 - - - - - - - D6 - - - C6 - - -',
         'C6 - - - - - - - E5 - - - A5 - - -', 'Bb5 - - - - - - - F5 - - - D6 - - -', 'C6 - - - - - - - A5 - - - F5 - - -',
         'Bb5 - - - A5 - - - G5 - - - D5 - - -', 'E5 - - - F5 - - - G5 - - - Bb5 - - -', 'A5 - - - - - - - - - - - - - - -',
         '. . . . . . . . . . . . C5 - - -']
    tk.notes('lead', parse(fan), i_lead); tk.notes('pad', parse(fanh), i_pad, 1.1)
    tk.notes('flute', parse(E, 4), i_flute)
    tk.notes('pad', parse([tr(b, -12) for b in E[8:]], 12), i_pad, 0.9)
    tk.notes('arp', arp(chords, range(4, 20), idx=(0, 1, 2, 1), base=60, every=2), i_stab, 1.2)
    tk.notes('bass', bass_line(chords, ['R - - - R - - - R - - - O - R -'] * 4 + ['R - - - - - - - 5 - - - O - - -'] * 16), i_bass_long)
    G = 'K . h . S . h . K . K . S . h .'
    tk.drums(drums_parse(['KC . . . S . . . K . . . S . S S', 'K . . . S . . . K . . . S . S S', 'K . . . S . . . K . S S S S S S',
                          'KC . . . . . . . . . . . . . . .'] + ['C' + G if i in (0, 8) else G for i in range(15)] + ['K . h . S . h . K . S . S S S S']))
    return tk.mix(MIX, lead_delay=('lead', 'flute'))

CAMPAIGN_MUSIC = [('music-stage2', stage2, -15), ('music-stage3', stage3, -15), ('music-boss2', boss2, -14.5),
                  ('music-boss3', boss3, -14.5), ('music-intro', intro_theme, -15), ('music-ending', ending_theme, -15.5)]

# ---------------------------------------------------------------- campaign SFX
def _bp(x, lo, hi, order=2): return sosfilt(butter(order, [lo, hi], 'bandpass', fs=SR, output='sos'), x)
def _loopify(y, xf=0.15):  # equal-power crossfade of the tail into the head -> seamless loop
    n = int(xf * SR); head, tail = y[:n].copy(), y[-n:]
    a = np.linspace(0, 1, n); y = y[:-n].copy(); y[:n] = head * np.sqrt(a) + tail * np.sqrt(1 - a); return y
def _growl(dur, f0, f1, formants, jitter=0.06, seed=1, duty=0.2):
    r = np.random.default_rng(seed); n = S(dur); t = T(n); k = int(dur * 40) + 2
    jit = np.interp(t, np.linspace(0, dur, k), r.normal(0, jitter, k))
    f = (f0 + (f1 - f0) * t / dur) * (1 + jit)
    src = dec(pulse(f, duty) + 0.18 * noise(np.full(n, 12000), n))
    y = sum(g * _bp(src, lo, hi) for (lo, hi, g) in formants) + 0.15 * src
    return np.tanh(y * 2.5)
def sfx_shotgun():
    n = S(0.45); t = T(n)
    x = noise(50000 * (0.3 + 0.7 * ex(t, 0.05)), n) * ex(t, 0.055) + sine(55 + 160 * ex(t, 0.015)) * ex(t, 0.1) * 1.3
    x += pulse(180 + 500 * ex(t, 0.02), 0.25) * ex(t, 0.04) * 0.4
    return np.tanh(filt(filt(dec(x * att(t, 0.0005)), 'highpass', 40), 'lowpass', 7500) * 1.5)
def sfx_ricochet():
    n = S(0.5); t = T(n); x = np.zeros(n)
    for f, a, d in [(1180, 1, 0.12), (1873, .8, 0.09), (2641, .6, 0.07), (3950, .4, 0.05), (5230, .3, 0.04)]:
        x += sine(np.full(n, float(f))) * ex(t, d) * a
    x += pulse(3200 * ex(t, 0.35) + 900, 0.5) * np.clip((t - 0.03) / 0.01, 0, 1) * ex(t, 0.12) * 0.25
    x += noise(np.full(n, 300000), n) * ex(t, 0.004) * 0.8
    return filt(dec(x * att(t, 0.0003)), 'highpass', 300)
def sfx_sniper_charge():
    n = S(0.7); t = T(n)
    f = 300 * 2 ** (t / 0.7 * 3); trem = 0.6 + 0.4 * np.sign(np.sin(2 * np.pi * (8 + 40 * t / 0.7) * t))
    x = (pulse(f, 0.125) * 0.7 + sine(f * 2) * 0.3) * trem * np.clip(t / 0.5, 0, 1) * np.clip((0.7 - t) / 0.02, 0, 1)
    return filt(dec(x), 'highpass', 200)
def sfx_sniper():
    n = S(0.4); t = T(n)
    x = noise(np.full(n, 400000), n) * ex(t, 0.012) * 1.2 + pulse(2400 * ex(t, 0.03) + 300, 0.5) * ex(t, 0.05) * 0.4
    x += sine(90 + 200 * ex(t, 0.01)) * ex(t, 0.05) * 0.8
    y = dec(x * att(t, 0.0002)); d = int(0.11 * SR); y[d:] += filt(y[:-d], 'lowpass', 2500) * 0.25  # slap echo
    return filt(y, 'highpass', 60)
def sfx_tank():
    y = boom_core(1.0, 0.3, 0.22, 16000, 1200)
    n = S(0.08); t = T(n); c = dec(noise(np.full(n, 400000), n) * ex(t, 0.01)); y[:len(c)] += c * 0.8
    return np.tanh(y * 1.2)
def sfx_gatling_spin():
    n = S(0.6); t = T(n)
    rate = 6 + 50 * (t / 0.6) ** 1.5; ph = np.cumsum(rate) / FS; clk = (np.diff(np.floor(ph), prepend=0) > 0).astype(float)
    clicks = np.convolve(clk, np.exp(-np.arange(S(0.004)) / S(0.001)), 'same') * noise(np.full(n, 200000), n)
    whir = pulse(120 + 700 * (t / 0.6) ** 1.3, 0.25) * 0.25 * np.clip(t / 0.3, 0, 1)
    return filt(dec(clicks * 0.8 + whir), 'highpass', 120)
def sfx_gatling():
    one = sfx_shoot_m(); step = int(0.055 * SR); y = np.zeros(step * 8 + len(one)); r = np.random.default_rng(4)
    for i in range(8): y[i * step:i * step + len(one)] += one * (0.85 + 0.15 * r.random())
    return filt(y, 'lowpass', 7000)
def sfx_laser_bolt():
    n = S(0.22); t = T(n); f = 1700 * ex(t, 0.06) + 350
    x = (pulse(f, 0.125) * 0.6 + pulse(f * 0.5, 0.5) * 0.4) * ex(t, 0.07) * att(t, 0.001) * (0.8 + 0.2 * np.sin(2 * np.pi * 45 * t))
    return filt(dec(x), 'highpass', 150)
def sfx_flame():  # loopable
    n = S(1.25); t = T(n); r = np.random.default_rng(3)
    fl = np.interp(t, np.linspace(0, 1.25, 60), r.uniform(0.6, 1.0, 60))
    x = dec(noise(np.full(n, 400000), n) * fl)
    y = _bp(x, 900, 5500) * 1.2 + filt(x, 'lowpass', 400) * 0.6
    y += dec(sine(80 + 25 * np.sin(2 * np.pi * 7 * t)) * 0.25 * fl)
    return _loopify(y)
def sfx_xeno_screech():
    n = S(0.55); t = T(n)
    f = (1500 - 500 * t / 0.55) * (1 + 0.06 * np.sin(2 * np.pi * 32 * t))
    x = pulse(f, 0.3) * (0.6 + 0.4 * np.sin(2 * np.pi * 57 * t)) * np.clip(t / 0.02, 0, 1) * np.clip((0.55 - t) / 0.15, 0, 1)
    y = dec(x + noise(np.full(n, 40000), n) * 0.3 * ex(t, 0.2))
    return np.tanh((_bp(y, 2000, 3400) * 1.5 + _bp(y, 900, 1500) + 0.2 * y) * 2)
def sfx_xeno_pounce():
    n = S(0.35); t = T(n)
    wh = _bp(dec(noise(np.full(n, 400000), n) * np.sin(np.pi * np.clip(t / 0.3, 0, 1)) ** 2), 500, 3000)
    gr = _growl(0.35, 170, 120, [(500, 900, 1.2), (1200, 2000, .6)], seed=4)
    m = min(len(wh), len(gr)); return wh[:m] * 0.9 + gr[:m] * 0.6
def sfx_mutant_roar():
    g = _growl(1.1, 95, 70, [(250, 500, 1.3), (600, 1000, 1.0), (1400, 2200, .4)], jitter=0.08, seed=5, duty=0.15)
    t = np.arange(len(g)) / SR; e = np.clip(t / 0.06, 0, 1) * np.clip((1.1 - t) / 0.35, 0, 1)
    return filt(g * e + np.sin(2 * np.pi * 48 * t) * 0.4 * e, 'highpass', 35)
def sfx_goo():
    n = S(0.32); t = T(n)
    x = noise(8000 + 30000 * ex(t, 0.02), n) * ex(t, 0.05) * 0.7 + sine(320 * ex(t, 0.06) + 70) * ex(t, 0.09)
    y = dec(x * att(t, 0.0008)); r = np.random.default_rng(6)
    for i in range(4):
        s = int(r.uniform(0.04, 0.2) * SR); m = int(0.02 * SR); tt = np.arange(m) / SR
        y[s:s + m] += np.sin(2 * np.pi * r.uniform(600, 1400) * (1 - tt * 8) * tt) * np.exp(-tt / 0.006) * 0.3
    return filt(y, 'lowpass', 6000)
def sfx_glass():
    n = int(0.9 * SR); y = np.zeros(n); r = np.random.default_rng(9)
    for i in range(46):
        s = int(r.exponential(0.1) * SR) % int(0.6 * SR); m = int(r.uniform(0.04, 0.25) * SR); tt = np.arange(min(m, n - s)) / SR
        y[s:s + len(tt)] += np.sin(2 * np.pi * r.uniform(2200, 9000) * tt) * np.exp(-tt / r.uniform(0.02, 0.08)) * r.uniform(0.2, 0.6)
    k = S(0.05); c = dec(noise(np.full(k, 400000), k) * ex(T(k), 0.01)); y[:len(c)] += c * 1.2
    m = int(0.1 * SR); tm = np.arange(m) / SR; y[:m] += np.sin(2 * np.pi * 110 * tm) * np.exp(-tm / 0.025) * 0.5
    return filt(y, 'highpass', 80)
def sfx_queen_roar():
    hi = _growl(1.9, 330, 210, [(700, 1200, 1.2), (1800, 2800, .9), (3200, 4200, .4)], jitter=0.1, seed=11, duty=0.25)
    lo = _growl(1.9, 62, 50, [(150, 400, 1.4), (500, 900, .8)], jitter=0.07, seed=12, duty=0.15)
    t = np.arange(len(hi)) / SR; e = np.clip(t / 0.12, 0, 1) * np.clip((1.9 - t) / 0.6, 0, 1)
    return filt(np.tanh((hi * 0.8 + lo * 1.1) * e * 1.3), 'highpass', 30)
def sfx_rotor():  # loopable: ~11 Hz blade slap + turbine whine
    dur = 1.0; n = S(dur + 0.15); t = T(n); x = np.zeros(n); per = 1 / 11
    for i in range(int((dur + 0.15) / per) + 1):
        s = S(i * per); m = min(S(0.05), n - s)
        if m <= 0: break
        tt = T(m); x[s:s + m] += (noise(np.full(m, 30000), m) * 0.8 + sine(np.full(m, 75.0))) * ex(tt, 0.014)
    x += sine(np.full(n, 1650.0)) * 0.04 + sine(np.full(n, 2475.0)) * 0.02
    return _loopify(filt(dec(x), 'lowpass', 3000), 0.15)
def sfx_thump():
    n = S(0.3); t = T(n)
    x = sine(48 + 110 * ex(t, 0.02)) * ex(t, 0.08) * 1.2 + noise(np.full(n, 15000), n) * ex(t, 0.025) * 0.5
    return filt(dec(x * att(t, 0.0008)), 'lowpass', 3000)
def sfx_page():  # paper swish with a rising band + a soft flap at the end
    n = int(0.4 * SR); t = np.arange(n) / SR; r = np.random.default_rng(2)
    wn = r.uniform(-1, 1, n) * np.sin(np.pi * np.clip(t / 0.3, 0, 1)) ** 1.5
    y = np.zeros(n); blk = 441
    for i in range(0, n, blk):
        fc = 900 + 3500 * min(i / SR / 0.3, 1); lo = max(i - 4096, 0)
        y[i:i + blk] = _bp(wn[lo:i + blk], fc * 0.6, fc * 1.6)[i - lo:]
    k = int(0.3 * SR); m = 400; y[k:k + m] += r.uniform(-1, 1, m) * np.exp(-np.arange(m) / 60) * 0.6
    return y
def sfx_phone():  # retro double ring + gap (loopable)
    n = S(2.0); t = T(n)
    gate = ((t < 0.42) | ((t > 0.62) & (t < 1.04))).astype(float)
    g = np.convolve(gate, np.ones(S(0.004)) / S(0.004), 'same')
    clap = 0.55 + 0.45 * np.sign(np.sin(2 * np.pi * 22 * t))
    x = (pulse(np.full(n, 1318.5), 0.5) * 0.5 + pulse(np.full(n, 1661.2), 0.25) * 0.4) * clap * g
    return filt(dec(x), 'lowpass', 6000)
CAMPAIGN_SFX = {'shotgun': (sfx_shotgun, -11.5), 'ricochet': (sfx_ricochet, -15), 'sniper-charge': (sfx_sniper_charge, -21),
                'sniper': (sfx_sniper, -12), 'tank': (sfx_tank, -9), 'gatling-spin': (sfx_gatling_spin, -19), 'gatling': (sfx_gatling, -15),
                'laser-bolt': (sfx_laser_bolt, -17.5), 'flame': (sfx_flame, -18), 'xeno-screech': (sfx_xeno_screech, -14),
                'xeno-pounce': (sfx_xeno_pounce, -16), 'mutant-roar': (sfx_mutant_roar, -11.5), 'goo': (sfx_goo, -16),
                'glass': (sfx_glass, -13), 'queen-roar': (sfx_queen_roar, -9.5), 'rotor': (sfx_rotor, -19), 'thump': (sfx_thump, -13),
                'page': (sfx_page, -19), 'phone': (sfx_phone, -16)}
LOOPING_SFX = ('flame', 'rotor', 'phone')
