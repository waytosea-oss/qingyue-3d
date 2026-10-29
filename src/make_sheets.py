# 生成对比图与验收拼图（screenshots/ 内）
from PIL import Image,ImageDraw,ImageFont
import os
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)),'..'))
F=lambda n:ImageFont.truetype('/System/Library/Fonts/Hiragino Sans GB.ttc',n)
H=760
ref=Image.open('../ref-portrait-qingyue.jpg').convert('RGB'); ref=ref.resize((int(ref.width*H/ref.height),H))
bl=Image.open('build/cmp_az-28.png').convert('RGB').resize((H,H))
web=Image.open('screenshots/19_clean_34view.png').convert('RGB').crop((260,40,1020,800)).resize((H,H))
M=Image.new('RGB',(ref.width+2*H,H+50),(250,248,236)); M.paste(ref,(0,50)); M.paste(bl,(ref.width,50)); M.paste(web,(ref.width+H,50))
d=ImageDraw.Draw(M)
for x,t in ((10,'原画参考'),(ref.width+10,'v6 · Blender 渲染'),(ref.width+H+10,'v6 · 网页实时 (three.js)')): d.text((x,10),t,fill=(40,60,30),font=F(26))
M.save('screenshots/compare_ref_vs_3d.png')
fs=[('03_closeup_face','静止'),('15_blink_closeup','闭眼（完全覆盖）'),('15b_blink_half','半眨眼'),('16_talk_viseme_A','说话口型 A（限位）'),('14_croak_mouth_closeup','鸣叫大张嘴（手臂张开）'),('17_mouth_limit_test','极限测试：鸣叫+张嘴1.0+滑块（钳制）')]
M=Image.new('RGB',(1380,1000),(250,248,236)); d=ImageDraw.Draw(M)
for i,(fn,t) in enumerate(fs):
    im=Image.open('screenshots/'+fn+'.png').convert('RGB').crop((200,40,900,740)).resize((460,460)); x,y=(i%3)*460,(i//3)*500
    M.paste(im,(x,y+40)); d.text((x+8,y+6),t,fill=(40,60,30),font=F(26))
M.save('screenshots/check_closeups_mouth_eyes.png')
ims=[Image.open('screenshots/W%d_wave_seq.png'%i).convert('RGB').crop((180,0,1000,820)).resize((400,400)) for i in range(1,5)]
M=Image.new('RGB',(1600,400))
for i,im in enumerate(ims): M.paste(im,(i*400,0))
M.save('screenshots/wave_sequence_strip.png')
labs=['预蹲','蹬地','空中伸展','最高点收腿','前伸掌下落','掌先着地','落地压扁','回弹']
ims=[Image.open('screenshots/J%d_jump_seq.png'%i).convert('RGB').crop((100,0,1180,800)).resize((432,320)) for i in range(1,9)]
M=Image.new('RGB',(1728,680),(250,248,236)); d=ImageDraw.Draw(M)
for i,im in enumerate(ims): M.paste(im,((i%4)*432,(i//4)*340+20)); d.text(((i%4)*432+8,(i//4)*340),labs[i],fill=(40,60,30),font=F(18))
M.save('screenshots/jump_sequence_strip.png')
print('sheets ok')

# ---- croak / crown / skin stills
def strip(fns,labels,out,crop=(160,20,1000,800),h=440):
    ims=[Image.open('screenshots/'+f+'.png').convert('RGB').crop(crop) for f in fns]
    w=int(h*ims[0].width/ims[0].height); M=Image.new('RGB',(w*len(ims),h+44),(250,248,236)); d=ImageDraw.Draw(M)
    for i,(im,t) in enumerate(zip(ims,labels)): M.paste(im.resize((w,h)),(i*w,44)); d.text((i*w+8,8),t,fill=(40,60,30),font=F(24))
    M.save('screenshots/'+out)
strip(['14b_croak_arms_open','06_croak','14_croak_mouth_closeup'],['鸣叫：手臂张开让出下巴','鸣叫 3/4','鸣叫大张嘴近景'],'croak_sheet.png')
strip(['J3_jump_seq','04_mid_jump'],['空中伸展（侧）','空中伸展（3/4）'],'jump_air_stretch.png',crop=(100,0,1180,800))
strip(['18_crown_closeup','19_clean_34view'],['藤冠近景','肤色网页静帧（暖雾逆光）'],'crown_and_skin_stills.png')
print('v4 sheets ok')

# ---- v5 deliverables
H=560
def row(cells,out,h=H):
    M=Image.new('RGB',(h*len(cells),h+50),(250,248,236)); d=ImageDraw.Draw(M)
    for i,(t,im) in enumerate(cells):
        im=im.copy(); im.thumbnail((h,h)); M.paste(im,(i*h+(h-im.width)//2,50+(h-im.height)//2)); d.text((i*h+10,10),t,fill=(40,60,30),font=F(26))
    M.save('screenshots/'+out)
ref=Image.open('../ref-qingyue-static.png').convert('RGB').crop((20,130,200,330))
refp=Image.open('../ref-portrait-qingyue.jpg').convert('RGB').crop((380,220,860,780))
row([('原画（黑底立绘）',ref),('v4 · 正面',Image.open('build/v4cmp_az0.png')),('v5 · 正面',Image.open('build/cmp_az0.png')),
     ('原画（主立绘局部）',refp),('v4 · 3/4',Image.open('build/v4cmp_az-28.png')),('v5 · 3/4',Image.open('build/cmp_az-28.png'))],'sit_front_34_v4_vs_v5.png')
row([('v5 网页 · 正面',Image.open('screenshots/20_sit_front_clean.png').crop((240,0,1040,800))),('v5 网页 · 3/4',Image.open('screenshots/21_sit_34_clean.png').crop((240,0,1040,800))),
     ('原画',refp)],'sit_web_v5.png')
row([('空中前扑 · 侧视（伸展）',Image.open('screenshots/22_jump_air_side.png').crop((140,0,1140,800))),('空中前扑 · 侧视（最高点前肢前伸）',Image.open('screenshots/23_jump_air_side_apex.png').crop((140,0,1140,800)))],'jump_air_side.png',h=700)
row([('藤冠特写 · 3/4 俯视',Image.open('screenshots/24_crown_closeup_clean.png').crop((240,0,1040,800))),('藤冠特写 · 侧面（垂下的卷须）',Image.open('screenshots/25_crown_side.png').crop((240,0,1040,800))),
     ('原画藤冠',Image.open('../ref-portrait-qingyue.jpg').convert('RGB').crop((540,210,800,400)))],'crown_closeup.png')
print('v5 sheets ok')

# ---- v6 deliverables
row([('v5 · 藤冠正面',Image.open('build/v5crown_front.png')),('v6 · 藤冠正面',Image.open('build/v6crown_front.png')),
     ('v5 · 藤冠 3/4',Image.open('build/v5crown_q34.png')),('v6 · 藤冠 3/4',Image.open('build/v6crown_q34.png')),
     ('原画藤冠',Image.open('../ref-portrait-qingyue.jpg').convert('RGB').crop((430,210,800,460)))],'crown_v5_vs_v6.png',h=520)
row([('v6 网页 · 藤冠正面',Image.open('screenshots/C1_crown_front.png').crop((240,0,1040,800))),('v6 网页 · 藤冠 3/4',Image.open('screenshots/C2_crown_34.png').crop((240,0,1040,800)))],'crown_web_v6.png',h=600)
row([('背心 · 正面',Image.open('screenshots/V1_vest_front.png').crop((240,0,1040,800))),('背心 · 背面',Image.open('screenshots/V2_vest_back.png').crop((240,0,1040,800))),
     ('背心 · 3/4',Image.open('screenshots/V3_vest_34.png').crop((240,0,1040,800))),('背心 · 3/4 背侧',Image.open('screenshots/V4_vest_34back.png').crop((240,0,1040,800))),
     ('关闭背心（网页开关）',Image.open('screenshots/V5_vest_off.png').crop((240,0,1040,800)))],'vest_stills.png',h=460)
labs=['抱膝坐','鸣叫张臂','挥手','说话','跳跃·空中','跳跃·落地压扁','向前蹦','开心转圈','打瞌睡','东张西望']
import glob
fs=sorted(glob.glob('screenshots/VS*.png'))
ims=[Image.open(f).convert('RGB').crop((140,0,1140,800)) for f in fs]
w,h=340,272; M=Image.new('RGB',(w*5,(h+30)*2),(250,248,236)); d=ImageDraw.Draw(M)
for i,im in enumerate(ims): M.paste(im.resize((w,h)),((i%5)*w,(i//5)*(h+30)+30)); d.text(((i%5)*w+8,(i//5)*(h+30)+4),labs[i],fill=(40,60,30),font=F(20))
M.save('screenshots/vest_actions_strip.png')
print('v6 sheets ok')
