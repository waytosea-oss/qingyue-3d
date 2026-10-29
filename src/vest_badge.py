# v6: embroidered round patch for the vest (leaf + 凤凰岛科普, no brand logos)
TEX='/Users/administrator/Tilo工作台/20261028-青跃三维/project/textures/'
from PIL import Image as _I, ImageDraw as _D, ImageFont as _F
BRES=512; img=_I.new('RGB',(BRES,BRES),(236,226,190)); d=_D.Draw(img)
d.ellipse((6,6,BRES-6,BRES-6),fill=(64,96,52)); d.ellipse((26,26,BRES-26,BRES-26),fill=(240,232,198)); d.ellipse((44,44,BRES-44,BRES-44),outline=(64,96,52),width=6)
c=BRES/2   # leaf
d.polygon([(c-90,c+40),(c-40,c-80),(c+30,c-120),(c+95,c-125),(c+80,c-60),(c+30,c+10),(c-40,c+50)],fill=(110,150,60))
d.line([(c-95,c+55),(c+80,c-110)],fill=(64,96,52),width=7)
for k in range(4): d.line([(c-50+k*35,c+20-k*35),(c-20+k*35,c-30-k*35)],fill=(64,96,52),width=4)
try: fnt=_F.truetype('/System/Library/Fonts/Hiragino Sans GB.ttc',62)
except Exception: fnt=_F.load_default()
txt='凤凰岛科普'; w_=d.textlength(txt,font=fnt); d.text((c-w_/2,c+70),txt,fill=(64,96,52),font=fnt)
img.save(TEX+'qingyue_vest_badge.png')
print('badge ok')
