import sys, math; sys.path.insert(0, 'art/raw/hero')
from rig import *

AIM = {  # angle, gun origin offset from torso centre, head kind
    'fwd': (0, (5, -2)),
    'dup': (-45, (4, -5)),
    'ddn': (45, (5, 0)),
    'up':  (-90, (5, -6)),
}

def stand(t=0.0, aim='fwd', legs=None, bob=0, squash=0.0, tail_mode='run', face='angry', recoil=0, cx=38, seed=0):
    """legs: ((hip_back, foot_back), (hip_front, foot_front)) in absolute cell coords, or None for idle stance"""
    cv = blank()
    cy = 61 + bob
    hx, hy = cx - 7, 32 + bob + (1 if squash > 0 else 0)
    tails(cv, (hx + 1, hy + 7), t, tail_mode)
    if legs is None:
        legs = (((cx - 5, 70), (cx - 8, 78)), ((cx + 5, 70), (cx + 7, 78)))
    (hb, fb), (hf, ff) = legs
    ang, (gdx, gdy) = AIM[aim]
    gx, gy = cx + gdx - recoil, cy + gdy
    a = math.radians(ang)
    hand_f = (gx + 7.5 * math.cos(a) - 1.2 * math.sin(a), gy + 7.5 * math.sin(a) + 1.2 * math.cos(a))
    hand_g = (gx - 3.2 * math.cos(a) - 2.2 * math.sin(a), gy - 3.2 * math.sin(a) + 2.2 * math.cos(a))
    leg(cv, hb, fb, back=True)
    arm(cv, (cx + 3, cy - 4), hand_f, back=True)
    leg(cv, hf, ff)
    torso(cv, cx, cy, squash=squash, seed=seed)
    head_at(cv, face, hx, hy)
    gm, gc = gun_layer(gx, gy, ang)
    over(cv, outlined(gm, gc))
    arm(cv, (cx - 2, cy + 1), hand_g)
    mz = muzzle_point(gx, gy, ang)
    return cv, mz
