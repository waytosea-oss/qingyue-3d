import asyncio,sys
from playwright.async_api import async_playwright
OUT='/Users/administrator/Tilo工作台/20261028-青跃三维/project/screenshots/'
URL='http://127.0.0.1:18977/qingyue-3d.html'
CAM="(()=>{const a=window.__api;a.cam.position.set(%s);a.controls.target.set(%s);a.controls.update();})()"
SHOTS=[('01_default_34view',None,None),
 ('02_front',CAM%('0,0.58,3.2','0,0.48,0'),None),
 ('03_closeup_face',CAM%('0.9,0.88,1.75','0,0.67,0'),"window.__api.at('sit_hug',0)"),
 ('04_mid_jump',CAM%('3.4,1.13,3.4','0,0.73,0'),"window.__api.at('jump',0.5)"),
 ('05_talking',CAM%('0.6,0.73,2.1','0,0.55,0'),"window.__api.at('idle',0.5);window.__api.speak('呱呱呱，你好呀我是青跃，欢迎来浅滩蛙鸣湾')"),
 ('06_croak',CAM%('1.2,0.73,2.6','0,0.53,0'),"window.__api.at('croak',0.70)"),
 ('07_wave',CAM%('0.6,0.73,3','0,0.53,0'),"window.__api.at('wave',0.6)"),
 ('08_happy_spin',CAM%('2.2,1.13,4.6','0,0.83,0'),"window.__api.at('happy_spin',0.6)"),
 ('09_back',CAM%('-1.8,1.23,-2.6','0,0.43,0'),"window.__api.at('idle',0)"),
 ('10_sleep',CAM%('1.2,0.83,2.6','0,0.43,0'),"window.__api.at('sleep',1.3)"),
 ('11_look_around',CAM%('1.2,0.83,2.6','0,0.43,0'),"window.__api.at('look_around',1.1)"),
 ('12_hop',CAM%('3.2,0.93,1.2','0,0.63,-0.2'),"window.__api.at('hop_forward',0.38)"),
 ('14b_croak_arms_open',CAM%('0.9,0.75,2.5','0,0.48,0'),"window.__api.at('croak',0.42)"),
 ('14_croak_mouth_closeup',CAM%('0.45,0.83,1.5','0,0.71,0'),"window.__api.at('croak',0.70)"),
 ('15_blink_closeup',CAM%('0.6,0.88,1.5','0,0.75,0'),"window.__api.at('sit_hug',0);window.__api.setMorphVal('blink',1)"),
 ('15b_blink_half',CAM%('0.6,0.88,1.5','0,0.75,0'),"window.__api.at('sit_hug',0);window.__api.setMorphVal('blink',0.5)"),
 ('16_talk_viseme_A',CAM%('0.45,0.78,1.5','0,0.67,0'),"window.__api.setMorphVal('blink',0);window.__api.at('sit_hug',0);window.__api.setMorphVal('viseme_A',1)"),
 ('17_mouth_limit_test',CAM%('0.45,0.78,1.5','0,0.67,0'),"window.__api.setMorphVal('viseme_A',0);window.__api.at('croak',0.70);window.__api.setMorphVal('mouth_open',1);window.__api.setBone(3,18)"),
 ('18_crown_closeup',CAM%('0.9,1.33,1.3','0.1,0.83,0'),"window.__api.setMorphVal('mouth_open',0);window.__api.setBone(3,0);window.__api.at('sit_hug',0)"),
 ('20_sit_front_clean',CAM%('0,0.6,3.0','0,0.42,0'),"window.__api.at('sit_hug',0);document.querySelectorAll('#card,#panel,#hint').forEach(e=>e.style.display='none')"),
 ('21_sit_34_clean',CAM%('1.45,0.75,2.65','0,0.42,0'),"window.__api.at('sit_hug',0);document.querySelectorAll('#card,#panel,#hint').forEach(e=>e.style.display='none')"),
 ('22_jump_air_side',CAM%('3.8,0.95,0.15','0,0.85,0.15'),"window.__api.at('jump',0.50);document.querySelectorAll('#card,#panel,#hint').forEach(e=>e.style.display='none')"),
 ('23_jump_air_side_apex',CAM%('3.8,0.95,0.15','0,0.9,0.15'),"window.__api.at('jump',0.66);document.querySelectorAll('#card,#panel,#hint').forEach(e=>e.style.display='none')"),
 ('24_crown_closeup_clean',CAM%('0.95,1.05,1.05','0.12,0.82,0'),"window.__api.at('sit_hug',0);document.querySelectorAll('#card,#panel,#hint').forEach(e=>e.style.display='none')"),
 ('25_crown_side',CAM%('1.25,0.85,0.25','0.15,0.8,0'),"window.__api.at('sit_hug',0);document.querySelectorAll('#card,#panel,#hint').forEach(e=>e.style.display='none')"),
 ('V1_vest_front',CAM%('0,0.6,3.0','0,0.42,0'),"window.__api.setVest(true);window.__api.at('sit_hug',0);document.querySelectorAll('#card,#panel,#hint').forEach(e=>e.style.display='none')"),
 ('V2_vest_back',CAM%('0.25,0.85,-2.9','0,0.42,0'),"window.__api.at('sit_hug',0);document.querySelectorAll('#card,#panel,#hint').forEach(e=>e.style.display='none')"),
 ('V3_vest_34',CAM%('1.65,0.8,2.3','0,0.42,0'),"window.__api.at('sit_hug',0);document.querySelectorAll('#card,#panel,#hint').forEach(e=>e.style.display='none')"),
 ('V4_vest_34back',CAM%('-2.0,0.95,-1.7','0,0.42,0'),"window.__api.at('sit_hug',0);document.querySelectorAll('#card,#panel,#hint').forEach(e=>e.style.display='none')"),
 ('V5_vest_off',CAM%('1.65,0.8,2.3','0,0.42,0'),"window.__api.setVest(false);window.__api.at('sit_hug',0);document.querySelectorAll('#card,#panel,#hint').forEach(e=>e.style.display='none')"),
 ('C1_crown_front',CAM%('0,0.86,1.55','0,0.78,0'),"window.__api.setVest(true);window.__api.at('sit_hug',0);document.querySelectorAll('#card,#panel,#hint').forEach(e=>e.style.display='none')"),
 ('C2_crown_34',CAM%('1.0,0.98,1.3','0.05,0.78,0'),"window.__api.at('sit_hug',0);document.querySelectorAll('#card,#panel,#hint').forEach(e=>e.style.display='none')"),
 ('VS00_hug',CAM%('2.0,1.0,2.9','0,0.5,0'),"window.__api.at('sit_hug',0);document.querySelectorAll('#card,#panel,#hint').forEach(e=>e.style.display='none')"),
 ('VS01_croak',CAM%('2.0,1.0,2.9','0,0.5,0'),"window.__api.at('croak',0.42);document.querySelectorAll('#card,#panel,#hint').forEach(e=>e.style.display='none')"),
 ('VS02_wave',CAM%('2.0,1.0,2.9','0,0.5,0'),"window.__api.at('wave',0.6);document.querySelectorAll('#card,#panel,#hint').forEach(e=>e.style.display='none')"),
 ('VS03_talk',CAM%('2.0,1.0,2.9','0,0.5,0'),"window.__api.at('talk',0.3);document.querySelectorAll('#card,#panel,#hint').forEach(e=>e.style.display='none')"),
 ('VS04_jump_air',CAM%('2.0,1.0,2.9','0,0.75,0'),"window.__api.at('jump',0.5);document.querySelectorAll('#card,#panel,#hint').forEach(e=>e.style.display='none')"),
 ('VS05_jump_land',CAM%('2.0,1.0,2.9','0,0.5,0'),"window.__api.at('jump',1.03);document.querySelectorAll('#card,#panel,#hint').forEach(e=>e.style.display='none')"),
 ('VS06_hop',CAM%('2.0,1.0,2.9','0,0.5,0'),"window.__api.at('hop_forward',0.4);document.querySelectorAll('#card,#panel,#hint').forEach(e=>e.style.display='none')"),
 ('VS07_spin',CAM%('2.0,1.0,2.9','0,0.75,0'),"window.__api.at('happy_spin',0.6);document.querySelectorAll('#card,#panel,#hint').forEach(e=>e.style.display='none')"),
 ('VS08_sleep',CAM%('2.0,1.0,2.9','0,0.5,0'),"window.__api.at('sleep',1.3);document.querySelectorAll('#card,#panel,#hint').forEach(e=>e.style.display='none')"),
 ('VS09_look',CAM%('2.0,1.0,2.9','0,0.5,0'),"window.__api.at('look_around',1.1);document.querySelectorAll('#card,#panel,#hint').forEach(e=>e.style.display='none')"),
 ('19_clean_34view',CAM%('1.45,0.93,3.1','0,0.48,0'),"window.__api.at('sit_hug',0);document.querySelectorAll('#card,#panel,#hint').forEach(e=>e.style.display='none')"),
 ('J1_jump_seq',CAM%('3.4,0.93,1.6','0,0.68,0'),"window.__api.at('jump',0.27);document.querySelectorAll('#card,#panel,#hint').forEach(e=>e.style.display='none')"),
 ('J2_jump_seq',CAM%('3.4,0.93,1.6','0,0.68,0'),"window.__api.at('jump',0.37);document.querySelectorAll('#card,#panel,#hint').forEach(e=>e.style.display='none')"),
 ('J3_jump_seq',CAM%('3.4,0.93,1.6','0,0.68,0'),"window.__api.at('jump',0.50);document.querySelectorAll('#card,#panel,#hint').forEach(e=>e.style.display='none')"),
 ('J4_jump_seq',CAM%('3.4,0.93,1.6','0,0.68,0'),"window.__api.at('jump',0.66);document.querySelectorAll('#card,#panel,#hint').forEach(e=>e.style.display='none')"),
 ('J5_jump_seq',CAM%('3.4,0.93,1.6','0,0.68,0'),"window.__api.at('jump',0.83);document.querySelectorAll('#card,#panel,#hint').forEach(e=>e.style.display='none')"),
 ('J6_jump_seq',CAM%('3.4,0.93,1.6','0,0.68,0'),"window.__api.at('jump',0.93);document.querySelectorAll('#card,#panel,#hint').forEach(e=>e.style.display='none')"),
 ('J7_jump_seq',CAM%('3.4,0.93,1.6','0,0.68,0'),"window.__api.at('jump',1.03);document.querySelectorAll('#card,#panel,#hint').forEach(e=>e.style.display='none')"),
 ('J8_jump_seq',CAM%('3.4,0.93,1.6','0,0.68,0'),"window.__api.at('jump',1.20);document.querySelectorAll('#card,#panel,#hint').forEach(e=>e.style.display='none')"),
 ('W1_wave_seq',CAM%('0.5,0.78,2.6','0,0.58,0'),"window.__api.at('wave',0.10);document.querySelectorAll('#card,#panel,#hint').forEach(e=>e.style.display='none')"),
 ('W2_wave_seq',CAM%('0.5,0.78,2.6','0,0.58,0'),"window.__api.at('wave',0.30);document.querySelectorAll('#card,#panel,#hint').forEach(e=>e.style.display='none')"),
 ('W3_wave_seq',CAM%('0.5,0.78,2.6','0,0.58,0'),"window.__api.at('wave',0.60);document.querySelectorAll('#card,#panel,#hint').forEach(e=>e.style.display='none')"),
 ('W4_wave_seq',CAM%('0.5,0.78,2.6','0,0.58,0'),"window.__api.at('wave',0.85);document.querySelectorAll('#card,#panel,#hint').forEach(e=>e.style.display='none')"),
]
async def main():
    only=sys.argv[1:]
    async with async_playwright() as p:
        b=await p.chromium.launch(channel='chrome',args=['--ignore-gpu-blocklist','--enable-unsafe-swiftshader'])
        logs=[]
        pg=await b.new_page(viewport={'width':1280,'height':800})
        pg.on('console',lambda m:logs.append(f'[{m.type}] {m.text}'))
        pg.on('pageerror',lambda e:logs.append(f'[pageerror] {e}'))
        await pg.goto(URL,timeout=180000); await pg.wait_for_function('window.__ready===true',timeout=180000); await pg.wait_for_timeout(1500)
        await pg.evaluate('window.__api.autoBlink(false)')   # deterministic captures (blink shots set the lids explicitly)
        for name,cam,act in SHOTS:
            if only and name not in only: continue
            if cam: await pg.evaluate(cam)
            if act: await pg.evaluate(act)
            await pg.wait_for_timeout(2500)
            await pg.screenshot(path=OUT+name+'.png',timeout=180000); print('shot',name,flush=True)
            await pg.evaluate("document.querySelectorAll('#card,#panel,#hint').forEach(e=>e.style.display='')")
        test=await pg.evaluate('''async()=>{const a=window.__api;a.release();const out=[];const w=ms=>new Promise(r=>setTimeout(r,ms));
          const live=()=>a.mixer._actions.filter(x=>x.isRunning()&&x.getEffectiveWeight()>0.001).map(x=>x.getClip().name+':'+x.getEffectiveWeight().toFixed(2));
          a.play('jump');await w(200);a.play('wave');await w(120);a.play('croak');await w(150);out.push('mid-switch '+live().join(','));
          await w(700);out.push('after fade '+live().join(','));await w(2500);out.push('after croak ends '+live().join(','));
          a.play('sleep');await w(800);a.play('idle');await w(800);out.push('idle '+live().join(','));a.at('hop_forward',0.38);await w(300);a.at('croak',0.68);await w(300);a.at('sit_hug',0);await w(400);const d=a.debugAngles();out.push('pose after hop->croak->sit_hug (expect all 0): '+JSON.stringify(Object.fromEntries(Object.entries(d).map(([k,v])=>[k,+v.toFixed(3)]))));return out}''')
        print('SWITCH TEST',test)
        await pg.close()
        if not only or 'mobile' in only:
            m=await b.new_page(viewport={'width':390,'height':844},is_mobile=True,has_touch=True,device_scale_factor=2)
            m.on('pageerror',lambda e:logs.append(f'[m pageerror] {e}'))
            await m.goto(URL,timeout=180000); await m.wait_for_function('window.__ready===true',timeout=180000); await m.wait_for_timeout(2000)
            await m.screenshot(path=OUT+'13_mobile.png',timeout=180000); print('shot mobile')
        print('LOGS:'); print('\n'.join(logs[:40]))
        await b.close()
asyncio.run(main())
