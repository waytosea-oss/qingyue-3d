# v8 headless test of the night-pond page: every movement mode driven by real key presses (Chrome via Playwright).
# usage: python src/test_pond.py [url]      -> prints PASS/FAIL per check, writes screenshots + test_pond_report.txt
import asyncio,json,sys,math,os
from playwright.async_api import async_playwright
URL=sys.argv[1] if len(sys.argv)>1 else 'http://127.0.0.1:18977/qingyue-pond.html'
ROOT=os.path.join(os.path.dirname(os.path.abspath(__file__)),'..'); SHOT=os.path.join(ROOT,'screenshots')
R=[];ok_all=True
def check(name,cond,info=''):
    global ok_all
    ok_all&=bool(cond); R.append(('PASS' if cond else 'FAIL')+'  '+name+('  | '+info if info else '')); print(R[-1],flush=True)
async def st(pg): return await pg.evaluate('window.__pond.state()')
async def hold(pg,key,ms):
    await pg.keyboard.down(key); await pg.wait_for_timeout(ms); await pg.keyboard.up(key)
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(channel='chrome',args=['--autoplay-policy=no-user-gesture-required'])
        pg=await b.new_page(viewport={'width':1280,'height':800}); logs=[]
        pg.on('console',lambda m:logs.append((m.type,m.text))); pg.on('pageerror',lambda e:logs.append(('pageerror',str(e))))
        pg.on('response',lambda r:logs.append(('http',r.status,r.url)) if r.status>=400 else None)
        await pg.goto(URL); await pg.wait_for_function('window.__ready===true',timeout=180000); await pg.wait_for_timeout(1200)
        s=await st(pg); check('page loads: frog on the start lily pad, %d pads'%s['pads'],s['where']=='pad' and s['pads']>=50)
        await pg.evaluate("document.body.classList.add('nopanel')")
        # ---- panorama
        await pg.evaluate("window.__pond.camLook(4.5,2.4,6.5,-6,3.6,-10,64)"); await pg.wait_for_timeout(1000)   # wide view toward the moon
        await pg.evaluate("document.querySelector('#hud').style.visibility='hidden'")
        await pg.screenshot(path=os.path.join(SHOT,'P1_night_panorama.png')); await pg.evaluate("document.querySelector('#hud').style.visibility=''"); await pg.evaluate("window.__pond.camFov(42);window.__pond.reset()"); await pg.wait_for_timeout(600)
        # ---- mode 1: hold W -> discrete hops (real jump clip), pads react
        await pg.keyboard.press('1'); x0=(await st(pg))
        anims=set();offs=[];kinds=set()
        await pg.keyboard.down('w')
        for _ in range(28):
            await pg.wait_for_timeout(100); s=await st(pg); anims.add(s['anim']); offs.append(s['padOff']); kinds|=set(s['log'])
            if s['where']=='water': break
        await pg.keyboard.up('w'); await pg.wait_for_timeout(1500); s=await st(pg)
        d=math.hypot(s['x']-x0['x'],s['z']-x0['z'])
        check('mode 1: holding W makes repeated discrete hops',s['log'].count('hop')>=2,'%d hops, moved %.2f m'%(s['log'].count('hop'),d))
        check('mode 1: hops use the skeletal jump clip (not sliding)','jump' in anims,'clips seen %s'%sorted(a for a in anims if a))
        check('mode 1: lily pad sinks on landing',min(offs)<-0.005,'min pad offset %.3f m'%min(offs))
        # mid-air screenshot: start a hop and freeze it in flight
        await pg.evaluate("window.__pond.reset()"); await pg.wait_for_timeout(800); await pg.keyboard.press('1')
        await pg.evaluate("window.__pond.pauseAt(0.62)"); await pg.keyboard.down('d'); await pg.wait_for_timeout(250); await pg.keyboard.up('d')
        await pg.wait_for_function("window.__pond.state().animTime>=0.6",timeout=5000); await pg.wait_for_timeout(200)
        s=await st(pg); check('mode 1: frozen mid-hop (airborne, root above the pad)',s['jumping'] and s['anim']=='jump','clip t=%.2f'%s['animTime'])
        await pg.evaluate("window.__pond.camTo(2.6,1.1,1.9)"); await pg.wait_for_timeout(300); await pg.screenshot(path=os.path.join(SHOT,'P2_hop_midair.png'))
        await pg.evaluate("window.__pond.resume()"); await pg.wait_for_timeout(1500)
        # hop into water -> auto swim
        await pg.evaluate("window.__pond.reset()"); await pg.wait_for_timeout(600); await pg.keyboard.press('1')
        wet=False
        for k in range(10):
            await hold(pg,'s',180); await pg.wait_for_timeout(1100); s=await st(pg)
            if s['where']=='water': wet=True;break
        await pg.wait_for_timeout(800); s=await st(pg)
        check('mode 1: hopping off the pads into water switches to swimming',wet and s['mode']==3 and s['anim']=='swim','mode %s, clip %s'%(s['mode'],s['anim']))
        # ---- mode 2: target, range, trajectory preview, valid/invalid, long jump
        await pg.evaluate("window.__pond.reset()"); await pg.wait_for_timeout(700); await pg.keyboard.press('2'); await pg.wait_for_timeout(300)
        s=await st(pg); check('mode 2: range circle + target + trajectory preview shown',s['preview'] and s['mode']==2)
        t0=s['target'];await hold(pg,'d',500); s=await st(pg)
        check('mode 2: WASD moves the target marker',math.hypot(s['target'][0]-t0[0],s['target'][1]-t0[1])>0.6,'moved %.2f m'%math.hypot(s['target'][0]-t0[0],s['target'][1]-t0[1]))
        far=await pg.evaluate("(()=>{const p=window.__pond.padInfo(7);return p})()")
        await pg.evaluate("window.__pond.setTarget(%f,%f)"%(far['x'],far['z'])); await pg.wait_for_timeout(200); s=await st(pg)
        check('mode 2: target beyond 3.6 m is rejected (red)',not s['valid'] and '超出' in s['reason'],s['reason'])
        await pg.keyboard.press('Space'); await pg.wait_for_timeout(400); s=await st(pg)
        check('mode 2: Space does nothing on an invalid target',not s['jumping'] and s['where']=='pad')
        tgt=await pg.evaluate("window.__pond.padInfo(3)")    # pad at about 2.2 m
        await pg.evaluate("window.__pond.setTarget(%f,%f)"%(tgt['x'],tgt['z'])); await pg.wait_for_timeout(250); s=await st(pg)
        dist=math.hypot(tgt['x'],tgt['z'])
        check('mode 2: target %.1f m away on a lily pad is valid (green)'%dist,s['valid'])
        await pg.evaluate("window.__pond.camLook(2.5,6.2,6.4,0.2,0,-1.0,48)"); await pg.wait_for_timeout(2600)   # whole range circle; let the earlier toast fade
        await pg.screenshot(path=os.path.join(SHOT,'P3_longjump_preview.png')); await pg.evaluate("window.__pond.camFov(42)")
        await pg.keyboard.press('Space'); await pg.wait_for_timeout(250); s=await st(pg)
        check('mode 2: Space starts a long jump with the jump clip',s['jumping'] and s['jumpKind']=='long' and s['anim']=='jump')
        await pg.wait_for_timeout(2600); s=await st(pg)
        check('mode 2: lands on the target pad',s['where']=='pad' and math.hypot(s['x']-tgt['x'],s['z']-tgt['z'])<0.05,'landed %.2f m from target, pad #%d'%(math.hypot(s['x']-tgt['x'],s['z']-tgt['z']),s['pad']))
        # ---- mode 3: dive in, 6 channels
        await pg.evaluate("window.__pond.reset()"); await pg.wait_for_timeout(700); await pg.keyboard.press('3'); await pg.wait_for_timeout(2600)
        s=await st(pg); check('mode 3: from a pad it dives into the water and swims',s['where']=='water' and s['anim']=='swim','y %.2f'%s['y'])
        a=await st(pg); await hold(pg,'w',1500); b2=await st(pg)
        check('mode 3: W swims forward',math.hypot(b2['x']-a['x'],b2['z']-a['z'])>0.6,'%.2f m'%math.hypot(b2['x']-a['x'],b2['z']-a['z']))
        await hold(pg,'s',900); c=await st(pg); check('mode 3: S swims backward / brakes',math.hypot(c['x']-b2['x'],c['z']-b2['z'])>0.05)
        y0=(await st(pg))['yaw']; await hold(pg,'a',700); s=await st(pg); check('mode 3: A/D turn',abs(s['yaw']-y0)>0.5,'yaw change %.2f rad'%(s['yaw']-y0))
        y1=(await st(pg))['y']; await hold(pg,'e',1300); s=await st(pg); check('mode 3: E (down) dives',s['y']<y1-0.4,'y %.2f -> %.2f'%(y1,s['y']))
        y2=s['y']; await pg.keyboard.down('Shift'); await pg.wait_for_timeout(500); await pg.keyboard.up('Shift'); s=await st(pg); check('mode 3: Shift (down) also dives',s['y']<y2-0.05)
        await pg.evaluate("window.__pond.camTo(2.1,0.15,1.5)"); await pg.wait_for_timeout(600); s=await st(pg)
        check('underwater camera: dense blue-green underwater fog',s['under'] and s['fog']>0.2,'fog %.2f'%s['fog'])
        await pg.screenshot(path=os.path.join(SHOT,'P4_underwater_swim.png'))
        y3=(await st(pg))['y']; await hold(pg,'Space',700); s=await st(pg); check('mode 3: Space (up) rises',s['y']>y3+0.2,'y %.2f -> %.2f'%(y3,s['y']))
        y4=s['y']; await hold(pg,'q',300); await pg.wait_for_timeout(2500); s=await st(pg); check('mode 3: buoyancy floats it back to the surface',s['y']>-0.42,'y %.2f'%s['y'])
        await pg.evaluate("window.__pond.camTo(2.2,1.3,2.4)"); await pg.wait_for_timeout(700)
        await pg.keyboard.down('w'); await pg.wait_for_timeout(500); await pg.screenshot(path=os.path.join(SHOT,'P5_surface_swim.png')); await pg.keyboard.up('w')
        # climb onto a lily pad from the water
        p1=await pg.evaluate("window.__pond.padInfo(1)")
        await pg.evaluate("window.__pond.placeWater(%f,%f,%f)"%(p1['x']+p1['r']+0.55,p1['z'],-math.pi/2)); await pg.wait_for_timeout(500)   # open water east of pad #1, facing it
        await pg.keyboard.down('w')
        for _ in range(30):
            await pg.wait_for_timeout(60)
            if 'climb' in (await st(pg))['log']: break
        await pg.keyboard.up('w'); await pg.wait_for_timeout(1800); s=await st(pg)   # release W once the climb starts (holding it keeps hopping)
        check('mode 3: swimming into a pad edge climbs onto it (jump)',s['where']=='pad' and 'climb' in s['log'] and s['mode']==1,'pad #%d, mode %d'%(s['pad'],s['mode']))
        # ---- v7 features still there: T talk (Edge TTS MP3), C croak, V vest
        await pg.keyboard.press('t'); await pg.wait_for_timeout(500); t=await pg.evaluate('window.__api.ttsState()')
        check('T: speaks a line with the Edge TTS MP3',t['playing'] is not None and t['ctx']=='running','clip %s, jaw %.1f deg'%(t['playing'],t['jaw']))
        jaws=[]
        for _ in range(30):
            await pg.wait_for_timeout(80); jaws.append((await pg.evaluate('window.__api.ttsState()'))['jaw'])
        check('talking opens the jaw clearly (target ~20-22 deg, cap 22)',15<=max(jaws)<=22.5,'max %.1f deg, mean %.1f deg'%(max(jaws),sum(jaws)/len(jaws)))
        await pg.wait_for_timeout(2500); await pg.keyboard.press('c'); await pg.wait_for_timeout(300); s=await st(pg); check('C: croak on a lily pad',s['anim']=='croak')
        sacs=[]
        for _ in range(20):
            await pg.wait_for_timeout(80); sacs.append((await pg.evaluate('window.__api.debugAngles()'))['sac'])
        check('croak inflates the vocal sac (bone scale ~16.7 = head-wide balloon)',max(sacs)>12 and min(sacs)<8,'sac scale %.1f -> %.1f'%(min(sacs),max(sacs)))
        vc=await pg.evaluate("document.querySelector('#vestOn').checked"); await pg.keyboard.press('v'); await pg.wait_for_timeout(200)
        check('V: toggles the vest',await pg.evaluate("document.querySelector('#vestOn').checked")!=vc); await pg.keyboard.press('v')
        errs=[l for l in logs if l[0] in ('error','pageerror','http')]
        check('no console errors / no HTTP errors',not errs,str(errs[:3]))
        await b.close()
    txt='\n'.join(R)+'\n\nRESULT: '+('ALL PASS' if ok_all else 'FAILURES')+' (%d checks)\n'%len(R)
    open(os.path.join(ROOT,'test_pond_report.txt'),'w',encoding='utf-8').write(txt); print('RESULT',ok_all)
asyncio.run(main())
