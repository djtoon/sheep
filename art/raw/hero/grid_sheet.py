import sys,glob; from PIL import Image
files=sys.argv[2:]; S=4; cw=max(Image.open(f).width for f in files)+4; ch=max(Image.open(f).height for f in files)+4
cols=5; rows=(len(files)+cols-1)//cols
sh=Image.new('RGBA',(cols*cw,rows*ch),(70,110,70,255))
for i,f in enumerate(files):
    im=Image.open(f).convert('RGBA'); sh.alpha_composite(im,((i%cols)*cw+2,(i//cols)*ch+ch-2-im.height))
sh.resize((sh.width*S,sh.height*S),Image.NEAREST).save(sys.argv[1])
