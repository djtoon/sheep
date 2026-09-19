import sys; sys.path.insert(0,'art/raw/hero')
from px import *
CAP = """\
.......###..####........
.....##AAA##AAAA##......
....#AAAAABAAAAABA###...
...#AABBAAAABBAAAABAAA#.
..#AABCBBAABCCBBAABCBBA#
..#BCCBBCCBBCCBBCCBBCCB#
.#RRRRRRRRRRRRRRRRRRRRR#
#TSSSSSSSSSSSSSSSSSSSSS#"""
FACE = {
'angry': """\
.#cc#bbb#WW#####WWW#bb#.
#cpp#bbb#WWW###WWWW#bbb#
#cpc#bbb#W##W#WW##W#bba#
.#pc#bbb#W##W#WW##W#bbd#
..##cbbb#WWWW#WWWWW#bbb#
....#bbb#WWWW#WWWWW#bbb#
....#cbbb##########bbbb#
....#ccbbbbbbbbbbbb##bb#
.....#cccbbbbbbbbbbbbb#.
......##ccccbbbbbbbb##..
........############....""",
'up': """\
.#cc#bbb#W##W#WW##W#bb#.
#cpp#bbb#W##W#WW##W#bbb#
#cpc#bbb#WWWW#WWWWW#bba#
.#pc#bbb#WWWW#WWWWW#bbd#
..##cbbb#WWWW#WWWWW#bbb#
....#bbb#WWWW#WWWWW#bbb#
....#cbbb##########bbbb#
....#ccbbbbbbbbbbbb##bb#
.....#cccbbbbbbbbbbbbb#.
......##ccccbbbbbbbb##..
........############....""",
'hurt': """\
.#cc#bbbbbbbbbbbbbbbbbb#
#cpp#bbb##bbb#bb#bbb#bb#
#cpc#bbbbb##bbbbb##bbba#
.#pc#bbb##bbb#bb#bbb#bd#
..##cbbbbbbbbbbbbbbbbbb#
....#bbbbbbbb###bbbbbbb#
....#cbbbbbb#WWW#bbbbbb#
....#ccbbbbbb###bbbbbbb#
.....#cccbbbbbbbbbbbbb#.
......##ccccbbbbbbbb##..
........############....""",
'x': """\
.#cc#bbb#WWWWW#WWWWW#b#.
#cpp#bbb#W#W#W#W#W#W#bb#
#cpc#bbb#WW#WW#WW#WW#ba#
.#pc#bbb#W#W#W#W#W#W#bd#
..##cbbb#WWWWW#WWWWW#bb#
....#bbb#WWWWW#WWWWW#bb#
....#cbbb###########bbb#
....#ccbbbbbbbbbb#pp#bb#
.....#cccbbbbbbbbb##bb#.
......##ccccbbbbbbbb##..
........############....""",
}
def head(kind='angry'):
    L=(CAP+'\n'+FACE[kind]).split('\n'); assert all(len(l)==24 for l in L),[len(l) for l in L]
    return parse(L)
if __name__=='__main__':
    from zoom import zoom
    from PIL import Image
    S='C:/Users/Dans/AppData/Local/Temp/claude/C--sheep/26278da5-9ac6-40de-a1a4-a76022593c3d/scratchpad/'
    ims=[]
    for k in FACE:
        zoom(head(k),S+f'h_{k}.png',12); ims.append(Image.open(S+f'h_{k}.png'))
    o=Image.new('RGBA',(sum(i.width for i in ims)+30,ims[0].height));x=0
    for i in ims: o.paste(i,(x,0)); x+=i.width+10
    o.save(S+'heads.png')
