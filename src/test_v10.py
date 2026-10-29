# v10 headless test: sound (Web Audio nodes, spatial sources, underwater low-pass, thunder delay), mute / volume, camera-relative movement,
# camera modes (follow / free / first person), recenter + collision + long-jump aim, headlamp on the vine crown, minimap creature icons,
# new pond-side plants, fog vs sky, lightning, phone viewport (390x844).
# usage: python src/test_v10.py [url] [screens dir]   -> prints PASS/FAIL per check, writes test_v10_report.txt + screenshots
import asyncio,os,sys,math
from playwright.async_api import async_playwright
URL=sys.argv[1] if len(sys.argv)>1 else 'http://127.0.0.1:18977/qingyue-pond.html'
ROOT=os.path.join(os.path.dirname(os.path.abspath(__file__)),'..')
SHOT=sys.argv[2] if len(sys.argv)>2 else os.path.join(os.path.expanduser('~'),'Tilo工作台','20261028-青跃三维','screens-v10')
os.makedirs(SHOT,exist_ok=True)
R=[];ok_all=True
def check(name,cond,info=''):
    global ok_all
    ok_all&=bool(cond); R.append(('PASS' if cond else 'FAIL')+'  '+name+('  | '+info if info else '')); print(R[-1],flush=True)
async def st(pg): return await pg.evaluate('window.__pond.state()')
async def v10(pg): return await pg.evaluate('window.__pond.v10()')
async def aud(pg): return await pg.evaluate('window.__pond.audio()')
async def hold(pg,key,ms):
    await pg.keyboard.down(key); await pg.wait_for_timeout(ms); await pg.keyboard.up(key)
async def shot(pg,name,hud=False):
    if not hud: await pg.evaluate("document.querySelector('#hud').style.visibility='hidden';document.querySelector('#toast').style.visibility='hidden'")
    await pg.screenshot(path=os.path.join(SHOT,name)); await pg.evaluate("document.querySelector('#hud').style.visibility='';document.querySelector('#toast').style.visibility=''")
def watch(pg,logs):
    pg.on('console',lambda m:logs.append((m.type,m.text))); pg.on('pageerror',lambda e:logs.append(('pageerror',str(e))))
    pg.on('response',lambda r:logs.append(('http',r.status,r.url)) if r.status>=400 else None)
def wrap(a): return math.atan2(math.sin(a),math.cos(a))
def srgb(c): return [1.055*x**(1/2.4)-0.055 if x>0.0031308 else 12.92*x for x in c]
async def drag(pg,x0,y0,dx,dy,steps=12,button='left'):
    await pg.mouse.move(x0,y0); await pg.mouse.down(button=button)
    for i in range(1,steps+1): await pg.mouse.move(x0+dx*i/steps,y0+dy*i/steps); await pg.wait_for_timeout(16)
    await pg.mouse.up(button=button)
async def desktop(b):
    pg=await b.new_page(viewport={'width':1280,'height':800}); logs=[]; watch(pg,logs)
    await pg.goto(URL); await pg.wait_for_function('window.__ready===true',timeout=180000); await pg.wait_for_timeout(1500)
    await pg.evaluate("document.body.classList.add('nopanel');window.__pond.setHint(false)")
    # ================= A. sound
    a=await aud(pg)
    check('audio: no AudioContext before the first user gesture (autoplay rules)',a['ctx'] is None,'ctx %s'%a['ctx'])
    await pg.keyboard.press('1'); await pg.wait_for_timeout(2500); a=await aud(pg)
    need=['master','comp','uw','sfx','amb','voice','music','musicLP','verb','thunderOut']
    check('audio: first key press creates + runs the context with master / sfx / ambience / voice / music buses and the underwater low-pass',
          a['ctx']=='running' and all(n in a['nodes'] for n in need) and a['lowpass']>15000,'ctx %s, nodes %s'%(a['ctx'],','.join(a['nodes'])))
    e0=a['events']; await pg.wait_for_timeout(3000); a=await aud(pg); e1=a['events']
    check('audio: night ambience = crickets + distant frog chorus, spatial (PannerNode %s)'%a['panModel'],e1['cricket']>e0['cricket'] and e1['frogFar']>e0['frogFar'] and a['panners']>5 and a['panModel']=='HRTF',
          'crickets +%d, far frogs +%d, %d panners'%(e1['cricket']-e0['cricket'],e1['frogFar']-e0['frogFar'],a['panners']))
    check('audio: background music plays the night mood at night',a['musicW']['night']>0.5 and a['musicW']['day']<0.1 and a['music']>0.1,'mood weights %s'%({k:round(v,2) for k,v in a['musicW'].items()}))
    # hops: take-off + landing on a pad, then into the water: splash
    await pg.evaluate("window.__pond.reset()"); await pg.wait_for_timeout(600); e0=(await aud(pg))['events']
    await pg.keyboard.down('w')
    for _ in range(40):
        await pg.wait_for_timeout(100)
        if (await st(pg))['where']=='water': break
    await pg.keyboard.up('w'); await pg.wait_for_timeout(800); e1=(await aud(pg))['events']
    check('audio: hop take-off, landing on a lily pad and the splash into water each make a sound',e1['jump']-e0['jump']>=2 and e1['land']-e0['land']>=1 and e1['splash']-e0['splash']>=1,
          'jump +%d, land +%d, splash +%d'%(e1['jump']-e0['jump'],e1['land']-e0['land'],e1['splash']-e0['splash']))
    s0=(await aud(pg))['events']['stroke']; t0=await pg.evaluate("window.__api.actions().includes('swim')?window.__api.mixer._actions.find(a=>a.getClip().name==='swim').getClip().duration:0")
    await hold(pg,'w',3000); s1=(await aud(pg))['events']['stroke']
    check('audio: breaststroke = one stroke sound per swim cycle',2<=s1-s0<=8,'%d strokes in 3 s (cycle %.2f s at speed-dependent tempo)'%(s1-s0,t0))
    await hold(pg,'e',1600); await pg.wait_for_timeout(500); a=await aud(pg); s=await st(pg)
    check('audio: frog under water -> whole mix low-passed (BiquadFilter)',s['y']<-0.8 and a['lowpass']<1000 and a['under']>0.8,'y %.2f, cutoff %.0f Hz'%(s['y'],a['lowpass']))
    await hold(pg,'Space',1500); await pg.wait_for_timeout(2500); a=await aud(pg)
    check('audio: back at the surface the low-pass opens again',a['lowpass']>10000,'cutoff %.0f Hz'%a['lowpass'])
    # creatures: a turtle comes up to breathe, dives with a plop when the frog swims up
    i=await pg.evaluate("window.__pond.turtleSurface(0)")
    for _ in range(40):
        await pg.wait_for_timeout(250)
        t=(await v10(pg))['turtles'][i]
        if t['surf']=='bask': break
    await pg.evaluate("window.__pond.mmLayer('radar')"); await pg.wait_for_timeout(200)   # E'': creatures are only drawn on the 生物雷达 layer
    v=await v10(pg); ic=[x for x in v['minimap']['icons'] if x['kind']=='turtle'][i]
    check('turtles: a swimmer surfaces to breathe (opaque icon on the creature radar while up)',t['surf']=='bask' and t['y']>-0.2 and ic['alpha']==1,'state %s, y %.2f, icon alpha %.2f'%(t['surf'],t['y'],ic['alpha']))
    await pg.evaluate("window.__pond.mmLayer('env')")
    d0=(await aud(pg))['events']['turtleDive']; await pg.evaluate("window.__pond.placeWater(%f,%f,0)"%(t['x']+1.2,t['z'])); await pg.wait_for_timeout(1200)
    t2=(await v10(pg))['turtles'][i]; d1=(await aud(pg))['events']['turtleDive']
    check('audio: the turtle dives when the frog comes close -> plop / splash sound',t2['surf']=='swim' and d1>d0,'state %s, dives +%d'%(t2['surf'],d1-d0))
    await pg.evaluate("window.__pond.setTod('day');window.__pond.setWeather('clear')"); await pg.wait_for_timeout(5000); a=await aud(pg); e=a['events']
    await pg.wait_for_timeout(4000); a2=await aud(pg)
    check('audio: daytime = birdsong (+ cicadas) and the day music mood',a2['events']['bird']>e['bird'] and a2['musicW']['day']>0.5 and a2['musicW']['night']<0.2,
          'birds +%d, cicada ticks %d, mood %s'%(a2['events']['bird']-e['bird'],a2['events']['cicada'],{k:round(v,2) for k,v in a2['musicW'].items()}))
    check('audio: fish make bubble / swish sounds',a2['events']['bubble']+a2['events']['swish']>0,'bubbles %d, swishes %d'%(a2['events']['bubble'],a2['events']['swish']))
    async def settle(cond):   # poll up to 10 s for the weather cross-fade
        for _ in range(40):
            await pg.wait_for_timeout(250); x=await aud(pg)
            if cond(x): return x
        return x
    G=lambda x:x['rainCmd'] if x.get('rainCmd') is not None else x['rain']   # commanded gain (AudioParam.value freezes when the audio device does not render)
    rc=G(a2); wc=a2['levels']['wind']; await pg.evaluate("window.__pond.setWeather('rain')"); ar=await settle(lambda x:abs(x['levels']['rain']-1)<0.02); rr=G(ar)
    await pg.evaluate("window.__pond.setWeather('storm')"); a=await settle(lambda x:abs(x['levels']['rain']-1.6)<0.03); rs=G(a)
    check('audio: rain volume follows the amount of rain (clear < rain < storm), wind rises in the storm',rc<0.01<rr<rs and a['levels']['wind']>wc*5 and (a.get('windCmd') or a['wind'])>0.01,
          'rain gain %.3f / %.3f / %.3f (live param %.3f, ctx time %.1f s), wind level %.2f -> %.2f'%(rc,rr,rs,a['rain'],a['ctxTime'],wc,a['levels']['wind']))
    a=await settle(lambda x:x['musicW']['storm']>0.5)   # the music mood has its own (slower) cross-fade
    check('audio: storm music mood',a['musicW']['storm']>0.5,'mood %s'%{k:round(v,2) for k,v in a['musicW'].items()})
    near=await pg.evaluate("window.__pond.strike({dist:400})"); far=await pg.evaluate("window.__pond.strike({dist:1600})")
    check('audio: thunder follows the flash after distance / 343 m/s; farther = later, quieter, duller (low-pass)',
          near['sound'] and far['sound'] and abs(near['sound']['delay']-400/343)<0.01 and abs(far['sound']['delay']-1600/343)<0.01 and far['sound']['gain']<near['sound']['gain'] and far['sound']['cutoff']<near['sound']['cutoff'] and near['sound']['at']>near['flashAt'],
          'near %.2f s gain %.2f %.0f Hz / far %.2f s gain %.2f %.0f Hz'%(near['sound']['delay'],near['sound']['gain'],near['sound']['cutoff'],far['sound']['delay'],far['sound']['gain'],far['sound']['cutoff']))
    # ================= B. mute / volume
    await pg.keyboard.press('k'); await pg.wait_for_timeout(400); m=await aud(pg); lbl=await pg.evaluate("document.querySelector('#muteBtn').textContent")
    await pg.keyboard.press('k'); await pg.wait_for_timeout(400); u=await aud(pg)
    check('mute: K silences everything (master gain 0, HUD 🔇) and K again restores it',m['muted'] and m['master']<0.01 and lbl=='🔇' and not u['muted'] and u['master']>0.5,'master %.3f -> %.3f'%(m['master'],u['master']))
    await pg.evaluate("document.body.classList.remove('nopanel')"); await pg.wait_for_timeout(200)
    await pg.evaluate("(()=>{const i=document.querySelector('#audVol');i.value=0.3;i.dispatchEvent(new Event('input'))})()"); await pg.wait_for_timeout(500); v1=(await aud(pg))['master']
    await pg.click('#musicOn'); await pg.wait_for_timeout(1500); mu=(await aud(pg))['music']; await pg.click('#musicOn')
    await pg.evaluate("(()=>{const i=document.querySelector('#musicVol');i.value=1;i.dispatchEvent(new Event('input'))})()"); await pg.wait_for_timeout(1500); mv=(await aud(pg))['music']
    await pg.click('#sfxOn'); await pg.wait_for_timeout(400); sf=(await aud(pg))['sfx']; await pg.click('#sfxOn')
    await pg.evaluate("(()=>{const i=document.querySelector('#audVol');i.value=0.8;i.dispatchEvent(new Event('input'))})()")
    check('panel: master volume slider, music on/off + music volume, sound-effects on/off',abs(v1-0.3)<0.02 and mu<0.02 and mv>0.5 and sf<0.01,'master %.2f, music off %.3f, music vol 1 -> %.2f, sfx off %.3f'%(v1,mu,mv,sf))
    await pg.evaluate("document.body.classList.add('nopanel');window.__pond.setTod('night');window.__pond.setWeather('clear')")
    # ================= C. camera
    await pg.evaluate("window.__pond.reset()"); await pg.wait_for_timeout(800); v=await v10(pg)
    check('camera: default = follow camera behind the frog (OrbitControls off)',v['cam']['mode']=='follow' and abs(v['cam']['behindErr'])<0.05 and not v['cam']['orbit'] and 3<v['cam']['camToFrog']<7,'behind error %.3f rad, %.1f m'%(v['cam']['behindErr'],v['cam']['camToFrog']))
    await shot(pg,'follow_camera_v10.png')
    res=[]
    for cy in [-math.pi/2, math.pi]:    # camera on the -x side (looking +x), then on the -z side... (looking +z)
        await pg.evaluate("window.__pond.reset()"); await pg.wait_for_timeout(500); await pg.evaluate("window.__pond.camYaw(%f)"%cy); await pg.wait_for_timeout(300)
        cd=(await v10(pg))['cam']['dir']; p0=await st(pg); yaws=[]
        await pg.keyboard.down('w')
        for _ in range(14):
            await pg.wait_for_timeout(40); yaws.append((await st(pg))['yaw'])
        await pg.wait_for_timeout(500); await pg.keyboard.up('w'); await pg.wait_for_timeout(900); p1=await st(pg)
        mv=[p1['x']-p0['x'],p1['z']-p0['z']]; n=math.hypot(*mv) or 1; f=math.hypot(cd[0],cd[2])
        res.append(((mv[0]*cd[0]+mv[1]*cd[2])/n/f,yaws,p0['yaw'],p1['yaw']))
    check('camera-relative WASD: W hops toward "into the screen" for two different camera headings',all(r[0]>0.95 for r in res),'alignment %s'%', '.join('%.3f'%r[0] for r in res))
    await pg.evaluate("window.__pond.reset()"); await pg.wait_for_timeout(500); y0=(await st(pg))['yaw']; await pg.evaluate("window.__pond.camYaw(%f)"%(y0+1.5*math.pi)); await pg.wait_for_timeout(300)
    # sample every rendered frame inside the page (polling over CDP missed short turns)
    await pg.evaluate("(()=>{window.__yl=[];const f=()=>{const s=window.__pond.state();window.__yl.push([s.yaw,s.jumping]);if(window.__yl.length<90)requestAnimationFrame(f)};requestAnimationFrame(f)})()")
    await pg.keyboard.down('w'); await pg.wait_for_timeout(450); await pg.keyboard.up('w'); await pg.wait_for_timeout(1200)
    ys=[tuple(v) for v in await pg.evaluate('window.__yl')]; y1=(await st(pg))['yaw']
    mid=[y for y,j in ys if 0.1<abs(wrap(y-y0))<abs(wrap(y1-y0))-0.1]; first_jump=next((k for k,(y,j) in enumerate(ys) if j),99)
    check('camera-relative WASD: the frog first turns smoothly toward the move direction (90 deg here), then hops',len(mid)>=2 and abs(wrap(y1-y0-math.pi/2))<0.05 and first_jump>0,
          'turn %.2f -> %.2f rad, %d in-between headings before the hop'%(y0,y1,len(mid)))
    # drag to orbit, auto recenter after release
    await pg.evaluate("window.__pond.reset()"); await pg.wait_for_timeout(600)
    await drag(pg,900,420,260,0); v=await v10(pg); e1=v['cam']['behindErr']
    await pg.wait_for_timeout(4500); e2=(await v10(pg))['cam']['behindErr']
    check('camera: mouse drag orbits round the frog; ~1.6 s after release it swings back behind',abs(e1)>0.8 and abs(e2)<0.08,'behind error %.2f -> %.3f rad'%(e1,e2))
    await drag(pg,900,420,-220,0,button='right'); await pg.wait_for_timeout(200); e1=(await v10(pg))['cam']['behindErr']
    await pg.evaluate("document.querySelector('#autoRecenter').click()"); await drag(pg,900,420,-60,0,button='right'); await pg.wait_for_timeout(4000); v=await v10(pg); e2=v['cam']['behindErr']
    await pg.evaluate("document.querySelector('#autoRecenter').click()")
    check('camera: right-button drag also orbits; with 自动回正 off the camera stays where it was put',abs(e1)>0.6 and abs(e2)>0.6 and not v['cam']['autoRecenter'],'%.2f / %.2f rad'%(e1,e2))
    await pg.wait_for_timeout(4000)
    await drag(pg,900,300,0,-400); await pg.wait_for_timeout(300); v=await v10(pg)
    check('camera collision: dragged as low as it goes, the camera stays above the water / lily pads (no clipping, no surface jitter)',v['cam']['pos'][1]>=0.29,'camera y %.2f'%v['cam']['pos'][1])
    ys=[]
    for _ in range(10):
        await pg.wait_for_timeout(50); ys.append((await v10(pg))['cam']['pos'][1])
    check('camera collision: steady at the clamp (no jitter)',max(ys)-min(ys)<0.01,'y range %.4f m'%(max(ys)-min(ys)))
    await pg.wait_for_timeout(3500)
    await pg.keyboard.press('3'); await pg.wait_for_timeout(2600); await hold(pg,'e',1500); await pg.wait_for_timeout(1200); v=await v10(pg); s=await st(pg)
    check('camera: follows the frog under water (camera below the surface, underwater fog)',v['cam']['under'] and v['cam']['pos'][1]<-0.15 and s['under'] and s['fog']>0.15,'frog y %.2f, camera y %.2f'%(s['y'],v['cam']['pos'][1]))
    await shot(pg,'follow_camera_underwater_v10.png')
    await pg.evaluate("window.__pond.reset()"); await pg.wait_for_timeout(1500); y0=(await v10(pg))['cam']['pos'][1]
    await pg.keyboard.press('2'); await pg.wait_for_timeout(1800); v=await v10(pg)
    check('camera: aiming a long jump raises the camera to show the landing spot',v['cam']['aim']>0.9 and v['cam']['pos'][1]>y0+1.0,'camera y %.2f -> %.2f'%(y0,v['cam']['pos'][1]))
    await shot(pg,'longjump_aim_camera_v10.png')
    await pg.keyboard.press('1'); await pg.wait_for_timeout(500)
    modes=[]
    for _ in range(3):
        await pg.keyboard.press('f'); await pg.wait_for_timeout(700); v=await v10(pg); modes.append((v['cam']['mode'],v['cam']['orbit'],v))
    fp=modes[1][2]['cam']; s=await st(pg)
    check('camera: F cycles follow -> free (orbit) -> first person -> follow',[m[0] for m in modes]==['free','first','follow'] and modes[0][1] and not modes[1][1],str([m[0] for m in modes]))
    await pg.keyboard.press('f'); await pg.keyboard.press('f'); await pg.wait_for_timeout(800); v=await v10(pg); s=await st(pg)
    fwd=[math.sin(s['yaw']),math.cos(s['yaw'])]; d=v['cam']['dir']; hd=math.hypot(d[0],d[2])
    check('camera: first person = at the frog\'s eyes, looking where the frog faces',v['cam']['mode']=='first' and v['cam']['camToFrog']<1.3 and (d[0]*fwd[0]+d[2]*fwd[1])/hd>0.98,'%.2f m from the frog root, facing dot %.3f'%(v['cam']['camToFrog'],(d[0]*fwd[0]+d[2]*fwd[1])/hd))
    await shot(pg,'first_person_v10.png')
    await pg.keyboard.press('f'); await pg.wait_for_timeout(600)
    v=await v10(pg); cd=v['cam']['dir']
    check('minimap: the view fan points where the camera looks',abs(wrap(v['minimap']['fanYaw']-math.atan2(cd[0],cd[2])))<0.02,'fan %.3f vs camera %.3f rad'%(v['minimap']['fanYaw'],math.atan2(cd[0],cd[2])))
    # ================= D. headlamp on the vine crown
    v=await v10(pg); L=v['lamp']
    check('headlamp: mounted on the front of the vine crown (head-bone chain), not on the forehead',L['dCrown']<0.06 and L['chain'][0]=='head','%.1f mm from the crown front point'%(L['dCrown']*1000))
    check('headlamp: beam points forward and a little down',L['beamFwd']>0.9 and L['beamDir'][1]<-0.05,'forward %.3f, down %.3f'%(L['beamFwd'],L['beamDir'][1]))
    ds=[];ps=[]; await pg.keyboard.press('c')
    for _ in range(14):
        await pg.wait_for_timeout(80); L=(await v10(pg))['lamp']; ds.append(L['dCrown']); ps.append(L['pos'])
    check('headlamp: rides with the crown / head while croaking',max(ds)-min(ds)<0.001 and max(math.dist(ps[0],p) for p in ps)>0.003,'crown offset %.4f..%.4f m, lamp moved %.3f m'%(min(ds),max(ds),max(math.dist(ps[0],p) for p in ps)))
    await pg.wait_for_timeout(2500)
    await pg.evaluate("window.__pond.setTod('day');window.__pond.setLamp(true)"); await pg.wait_for_timeout(3000)
    await pg.evaluate("window.__pond.camLook(0.7,1.25,0.95,0.03,0.93,0.2,10)"); await pg.wait_for_timeout(600); await shot(pg,'headlamp_crown_closeup_v10.png')
    await pg.evaluate("window.__pond.camLook(1.6,1.1,1.9,0,0.75,0.3,30)"); await pg.wait_for_timeout(400); await shot(pg,'headlamp_crown_v10.png')
    await pg.evaluate("window.__pond.setTod('night')"); await pg.wait_for_timeout(3000); await pg.evaluate("window.__pond.camLook(-1.6,1.4,-2.2,0.4,0.5,1.5,40)"); await pg.wait_for_timeout(400); await shot(pg,'headlamp_crown_night_v10.png')
    await pg.evaluate("window.__pond.setLamp(false);window.__pond.reset()"); await pg.wait_for_timeout(800)
    # ================= E''. minimap layers: 环境地图 (default, no creatures) -> 生物雷达 (only large animals, never fish) -> 关闭; B / on-map button
    PIX="(()=>{const c=document.querySelector('#mmc'),x=c.getContext('2d'),k=c.width/c.clientWidth;return window.__pond.v10().minimap.icons.map(i=>{const d=x.getImageData(Math.round(i.x*k)-2,Math.round(i.y*k)-2,5,5).data;let r=0,g=0,b=0;for(let j=0;j<d.length;j+=4){r+=d[j];g+=d[j+1];b+=d[j+2]}return[i.kind,r/25,g/25,b/25]})})()"
    await pg.evaluate("window.__pond.reset();window.__pond.mmLayer('env')"); await pg.wait_for_timeout(600); v=await v10(pg); mm=v['minimap']
    check('minimap layers: registry has 环境地图 / 生物雷达 / 关闭, default = 环境地图 and its name is shown on the map',mm['layers']==['env','radar','off'] and mm['layer']=='env' and '环境地图' in mm['label'],'%s, label "%s"'%(mm['layers'],mm['label']))
    check('minimap 环境地图: no creatures at all (no turtles / fish / birds drawn)',mm['on'] and len(mm['icons'])==0,'%d creature icons'%len(mm['icons']))
    await pg.keyboard.press('b'); await pg.wait_for_timeout(500); v=await v10(pg); mm=v['minimap']; icons=mm['icons']
    tu=[x for x in icons if x['kind']=='turtle']; fi=[x for x in icons if x['kind']=='fish']; bi=[x for x in icons if x['kind']=='bird']
    bigVisible=[b for b in v['birds'] if b['big'] and b['visible']]
    check('minimap 生物雷达 (B): only large animals - every turtle + visible egrets/night herons, never the fish schools',mm['layer']=='radar' and '生物雷达' in mm['label'] and len(tu)==len(v['turtles'])>=10 and len(fi)==0 and len(bi)==len(bigVisible),
          '%d turtles, %d big birds, %d fish'%(len(tu),len(bi),len(fi)))
    px=await pg.evaluate(PIX); tc=[p for p in px if p[0]=='turtle']
    check('minimap 生物雷达: turtle blips are really drawn (bright green on the radar), under-water ones translucent',sum(1 for p in tc if p[2]>p[1]+20 and p[2]>60)>=len(tc)-1 and any(x['alpha']<1 for x in tu),
          'blips %s'%(['%d,%d,%d'%tuple(p[1:]) for p in tc[:3]]))
    await pg.keyboard.press('b'); await pg.wait_for_timeout(400); v=await v10(pg)
    vis=await pg.evaluate("getComputedStyle(document.querySelector('#mm')).display")
    check('minimap 关闭 (B again): the map is hidden, a small button brings it back',v['minimap']['layer']=='off' and not v['minimap']['on'] and vis=='none')
    await pg.click('#mmShow'); await pg.wait_for_timeout(300); v=await v10(pg); l1=v['minimap']['layer']
    await pg.click('#mmLayer'); await pg.wait_for_timeout(300); l2=(await v10(pg))['minimap']['layer']
    check('minimap: on-map button cycles the layers too (show -> 环境地图, click -> 生物雷达)',l1=='env' and l2=='radar','%s -> %s'%(l1,l2))
    await pg.evaluate("window.__pond.setZoom(2)"); await pg.wait_for_timeout(900); await shot(pg,'minimap_radar_v10.png',hud=True)
    await pg.evaluate("(()=>{const c=document.querySelector('#mm');c.style.transform='scale(2.2)';c.style.transformOrigin='left bottom'})()"); await pg.wait_for_timeout(300)
    await shot(pg,'minimap_radar_zoom_v10.png',hud=True)
    await pg.evaluate("window.__pond.mmLayer('env')"); await pg.wait_for_timeout(300); await shot(pg,'minimap_env_zoom_v10.png',hud=True)
    await pg.evaluate("document.querySelector('#mm').style.transform='';window.__pond.setZoom(1)")
    v=await v10(pg)
    near=[t for t in v['turtles'] if math.hypot(t['x'],t['z'])<6]
    check('turtles: more of them, around the start pad where the player meets them',len(v['turtles'])>=10 and len(near)>=6,'%d turtles, %d within 6 m of the start'%(len(v['turtles']),len(near)))
    await pg.evaluate("window.__pond.setHint(true)"); tt=[t for t in v['turtles'] if not t['swimmer']][1]
    await pg.evaluate("window.__pond.placeWater(%f,%f,0)"%(tt['x']+0.5,tt['z'])); await hold(pg,'e',2000); await pg.wait_for_timeout(600)
    h=(await v10(pg))['hint']; toast=await pg.evaluate("document.querySelector('#toast').textContent")
    check('minimap / hint: swimming up to a creature shows an on-screen hint',('乌龟' in h['last']) and h['now']-h['lastT']<3,'hint "%s", toast "%s"'%(h['last'],toast))
    # ================= F. plants, fog, lightning
    v=await v10(pg)
    need=['Reeds','ReedPlumes','Cattails','WillowTrunks','WillowCrowns','WillowStrands','MetasequoiaTrunks','MetasequoiaCrowns','BankShrubs']
    check('plants: cone trees replaced by instanced reeds / cattails / willows / dawn redwoods / shrubs',v['coneTrees']==0 and all(v['plants'].get(n,0)>0 for n in need),', '.join('%s %d'%(k,c) for k,c in v['plants'].items()))
    for name,tod,wx in [('day','day','clear'),('rain','day','rain'),('fog','day','fog'),('dusk','dusk','clear'),('night','night','clear')]:
        await pg.evaluate("window.__pond.setTod('%s');window.__pond.setWeather('%s');window.__pond.camLook(4.5,2.4,6.5,-6,3.0,-10,60)"%(tod,wx)); await pg.wait_for_timeout(4000)
        await shot(pg,'trees_%s_v10.png'%name)
        if wx in ('rain','fog'):
            f=(await v10(pg))['fog']; fd=srgb(f['color'])
            check('fog fix (%s): fog colour on screen matches the sky horizon (far trees fade into the sky, not white)'%wx,all(fd[i]<=f['skyHor'][i]+0.04 for i in range(3)) and f['skyFogAmt']>0.3,
                  'fog %s vs horizon %s, sky fog %.2f'%(['%.2f'%x for x in fd],['%.2f'%x for x in f['skyHor']],f['skyFogAmt']))
    await pg.evaluate("window.__pond.setTod('night');window.__pond.setWeather('storm');window.__pond.camLook(4.5,2.4,6.5,-6,4.5,-10,64)"); await pg.wait_for_timeout(3500)
    await pg.evaluate("window.__pond.flashHold(true);window.__pond.strike({dist:450})"); await pg.wait_for_timeout(300); v=await v10(pg)
    check('lightning: clearly visible bolt (bright ribbon + glow) with a scene flash; debug hold freezes the frame',v['bolt']['visible'] and v['bolt']['core']>0.9 and v['bolt']['glow']>0.3 and v['bolt']['flash']>0.8,'core %.2f, glow %.2f, flash %.2f'%(v['bolt']['core'],v['bolt']['glow'],v['bolt']['flash']))
    await shot(pg,'storm_lightning_v10.png')
    img=await pg.screenshot(); await pg.evaluate("window.__pond.flashHold(false)"); await pg.wait_for_timeout(1200)
    await pg.evaluate("window.__pond.setWeather('clear');window.__pond.forceBolt(true)"); s0=(await v10(pg))['bolt']['strikes']; await pg.wait_for_timeout(4000); s1=(await v10(pg))['bolt']['strikes']
    await pg.evaluate("window.__pond.forceBolt(false)")
    check('lightning: debug switch forces strikes in any weather (?bolt=1 / panel ⚡ / __pond.forceBolt)',s1>s0,'%d strikes in 4 s under a clear sky'%(s1-s0))
    errs=[l for l in logs if l[0] in ('error','pageerror','http')]
    check('desktop: no console errors / no HTTP errors',not errs,str(errs[:3]))
    await pg.close()
async def c2(b):
    """C2: one camera-relative control scheme for land, surface and under water"""
    pg=await b.new_page(viewport={'width':1280,'height':800}); logs=[]
    pg.on('pageerror',lambda e:logs.append(('pageerror',str(e))))
    await pg.goto(URL); await pg.wait_for_function('window.__ready===true',timeout=180000); await pg.wait_for_timeout(1000)
    OPEN="""(()=>{const P=window.__pond;const s=P.state();for(let r=4;r<18;r+=0.5)for(let a=0;a<6.28;a+=0.25){const x=Math.cos(a)*r,z=Math.sin(a)*r;
       let ok=true;for(let i=0;i<s.pads;i++){const p=P.padInfo(i);if(Math.hypot(p.x-x,p.z-z)<p.r+3.2){ok=false;break}}if(ok)return[x,z]}})()"""
    ox,oz=await pg.evaluate(OPEN); CY=0.9   # fixed camera heading for every measurement
    async def track(key,ms):   # per-frame positions while the key is held
        await pg.evaluate("(()=>{window.__tr=[];const f=()=>{const s=window.__pond.state();window.__tr.push([s.x,s.y,s.z,s.yaw]);if(window.__tr.length<400)requestAnimationFrame(f)};requestAnimationFrame(f)})()")
        await pg.keyboard.down(key); await pg.wait_for_timeout(ms); await pg.keyboard.up(key); await pg.wait_for_timeout(250)
        return await pg.evaluate('window.__tr')
    def heading(tr,frac=0.5):   # direction of travel over the last part of the motion (after the eased turn)
        a=tr[int(len(tr)*frac)]; z=tr[-1]; return math.atan2(z[0]-a[0],z[2]-a[2]),math.hypot(z[0]-a[0],z[2]-a[2])
    async def camdir():
        d=(await v10(pg))['cam']['dir']; return math.atan2(d[0],d[2])
    res={}
    for key in ('w','d'):
        await pg.evaluate("window.__pond.reset()"); await pg.wait_for_timeout(500); await pg.evaluate("window.__pond.camYaw(%f)"%CY); await pg.wait_for_timeout(400)
        cdl=await camdir(); s0=await st(pg); await pg.keyboard.down(key); await pg.wait_for_timeout(500); await pg.keyboard.up(key); await pg.wait_for_timeout(1500); s1=await st(pg)
        land=math.atan2(s1['x']-s0['x'],s1['z']-s0['z'])
        await pg.evaluate("window.__pond.placeWater(%f,%f,%f)"%(ox,oz,CY+2.0)); await pg.wait_for_timeout(300); await pg.evaluate("window.__pond.camYaw(%f)"%CY); await pg.wait_for_timeout(500)
        cdw=await camdir(); tr=await track(key,2600); water,dist=heading(tr)
        res[key]=(land-cdl,water-cdw,dist)
        check('C2: same camera heading -> %s moves the same screen direction on land and in the water (<5 deg)'%key.upper(),
              abs(wrap((land-cdl)-(water-cdw)))<math.radians(5) and dist>0.3,
              'land %.1f deg, water %.1f deg rel. to the camera (water swim %.2f m)'%(math.degrees(wrap(land-cdl)),math.degrees(wrap(water-cdw)),dist))
    await pg.evaluate("window.__pond.placeWater(%f,%f,%f)"%(ox,oz,CY)); await pg.wait_for_timeout(300); await pg.evaluate("window.__pond.camYaw(%f)"%CY); await pg.wait_for_timeout(500)
    cd=await camdir(); tr=await track('s',3000); h,dist=heading(tr,0.6)
    check('C2: S in the water turns the frog round and swims toward the camera (not tank back-pedal)',abs(wrap(h-(cd+math.pi)))<math.radians(8) and dist>0.3 and abs(wrap(tr[-1][3]-(cd+math.pi)))<0.3,
          'travel %.1f deg from "toward camera", frog faces %.1f deg off'%(math.degrees(wrap(h-(cd+math.pi))),math.degrees(wrap(tr[-1][3]-(cd+math.pi)))))
    await pg.evaluate("window.__pond.placeWater(%f,%f,%f)"%(ox,oz,CY)); await pg.wait_for_timeout(400)   # open water again (the S swim may have reached a pad)
    await pg.keyboard.down('e'); await pg.wait_for_timeout(1200); await pg.keyboard.up('e'); await pg.wait_for_timeout(600); y0=(await st(pg))['y']
    tr=await track('w',1200); ys=[p[1] for p in tr]
    check('C2: under water, W swims level - it never dives on its own (only Shift/E dive, Space/Q rise)',min(ys)>=y0-0.02,'y start %.2f, lowest %.2f'%(y0,min(ys)))
    # land -> water: no direction flip, no camera jump
    await pg.evaluate("window.__pond.reset()"); await pg.wait_for_timeout(500); await pg.evaluate("window.__pond.camYaw(%f)"%CY); await pg.wait_for_timeout(300)
    await pg.evaluate("(()=>{window.__cj=[];let last=null;const f=()=>{const c=window.__pond.v10().cam.pos,s=window.__pond.state();if(last)window.__cj.push([Math.hypot(c[0]-last[0],c[1]-last[1],c[2]-last[2]),s.yaw,s.where]);last=c;if(window.__cj.length<240)requestAnimationFrame(f)};requestAnimationFrame(f)})()")
    await pg.keyboard.press('3'); await pg.wait_for_timeout(3500); cj=await pg.evaluate('window.__cj')
    yaws=[c[1] for c in cj]; flips=max(abs(wrap(yaws[i+1]-yaws[i])) for i in range(len(yaws)-1)); jump=max(c[0] for c in cj)
    check('C2: diving in from a lily pad keeps the heading and the camera moves smoothly (no flip, no jump)',flips<0.35 and jump<0.35 and cj[-1][2]=='water',
          'largest per-frame turn %.2f rad, largest camera step %.2f m'%(flips,jump))
    check('C2: no page errors',not logs,str(logs[:2]))
    await pg.close()
async def birds_trees(b):
    """J: reed-bed birds; F: nicer trees that fade to silhouettes (not white) in rain / fog; lightning frame"""
    pg=await b.new_page(viewport={'width':1280,'height':800}); logs=[]
    pg.on('pageerror',lambda e:logs.append(('pageerror',str(e))))
    pg.on('console',lambda m:logs.append(('error',m.text)) if m.type=='error' else None)
    await pg.goto(URL); await pg.wait_for_function('window.__ready===true',timeout=180000); await pg.wait_for_timeout(800)
    await pg.mouse.click(640,400); await pg.wait_for_timeout(300)   # first gesture unlocks audio
    await pg.evaluate("document.body.classList.add('nopanel')")
    async def birds(): return (await v10(pg))['birds']
    async def wait_birds(cond,secs=25):
        for _ in range(int(secs*4)):
            await pg.wait_for_timeout(250); bs=await birds()
            if cond(bs): return bs
        return bs
    async def look_at(bd,dist=2.6,side=1.2,h=0.9,fov=40):
        s=await st(pg); a=math.atan2(bd['z'],bd['x']); dx,dz=bd['x']-s['x'],bd['z']-s['z']
        await pg.evaluate("window.__pond.camLook(%f,%f,%f,%f,%f,%f,%d)"%(dx-math.cos(a)*dist+math.sin(a)*side,h,dz-math.sin(a)*dist-math.cos(a)*side,dx,bd['y']-s['y']-0.1,dz,fov))
    info=await pg.evaluate("window.__pond.birdModels()")
    check('birds: modelled, not placeholders - lathe bodies, tube S-necks, shaped notched wings, jointed legs (>= 10 parts each)',
          all(m['meshes']>=10 and 'LatheGeometry' in m['types'] and 'TubeGeometry' in m['types'] and 'ShapeGeometry' in m['types'] for m in info if m['kind'] in ('egret','heron')),
          '; '.join('%s %d parts (%s)'%(m['kind'],m['meshes'],'/'.join(sorted(set(m['types'])))) for m in info[:2]))
    # night: night herons roost in the reeds, no egrets
    await pg.evaluate("window.__pond.setTod('night',true);window.__pond.setWeather('clear',true)")
    bs=await wait_birds(lambda bs:any(x['kind']=='heron' and x['state'] in ('stand','forage') for x in bs) and not any(x['kind']=='egret' and x['visible'] for x in bs))
    he=[x for x in bs if x['kind']=='heron' and x['state'] in ('stand','forage')]
    check('birds: at night the night herons (夜鹭) stand in the reeds, egrets are away',len(he)>=1 and not any(x['kind']=='egret' and x['visible'] for x in bs),'%d herons landed'%len(he))
    if he: await look_at(he[0]); await pg.evaluate("window.__pond.setLamp(true)"); await pg.wait_for_timeout(900); await shot(pg,'night_heron_v10.png'); await pg.evaluate("window.__pond.setLamp(false)")
    # day: egrets + kingfisher + grebes; herons leave
    await pg.evaluate("window.__pond.setTod('day',true)")
    bs=await wait_birds(lambda bs:sum(1 for x in bs if x['kind']=='egret' and x['state'] in ('stand','forage'))>=2 and not any(x['kind']=='heron' and x['visible'] for x in bs),35)
    eg=[x for x in bs if x['kind']=='egret' and x['state'] in ('stand','forage')]
    check('birds: by day egrets (白鹭) wade in the shallows, the night herons have left',len(eg)>=2 and not any(x['kind']=='heron' and x['visible'] for x in bs),'%d egrets landed'%len(eg))
    gr=[x for x in bs if x['kind']=='grebe' and x['visible']]
    check('birds: little grebes (小䴙䴘) swim on the water',len(gr)>=1 and all(abs(x['y'])<0.08 or x['state']=='dive' for x in gr),', '.join('%s y %.2f'%(x['state'],x['y']) for x in gr))
    necks=[]
    for _ in range(40):
        await pg.wait_for_timeout(150); necks+= [x['neck'] for x in await birds() if x['kind']=='egret' and x['state']=='forage']
    check('birds: egrets forage - the neck dips down to peck',necks and max(necks)>0.8,'max neck pitch %.2f rad'%(max(necks) if necks else 0))
    if eg: await look_at(eg[0]); await pg.wait_for_timeout(900); await shot(pg,'egret_day_v10.png')
    if gr: await look_at(gr[0],dist=2.0,side=0.8,h=0.5); await pg.wait_for_timeout(700); await shot(pg,'grebe_v10.png')
    # the frog swims up -> alarm call + wing beats, the egret takes off, circles and lands back
    bs=await birds(); i=next(k for k,x in enumerate(bs) if x['kind']=='egret' and x['state'] in ('stand','forage')); e=bs[i]
    a0=(await aud(pg))['events']; a=math.atan2(e['z'],e['x'])
    await pg.evaluate("window.__pond.placeWater(%f,%f,0)"%(e['x']-math.cos(a)*1.8,e['z']-math.sin(a)*1.8)); await pg.wait_for_timeout(500)
    b1=(await birds())[i]; a1=(await aud(pg))['events']
    check('birds: the frog comes close -> the egret flies off with an alarm call and wing beats',b1['state']=='fly' and a1.get('birdFlee',0)>a0.get('birdFlee',0) and a1.get('wings',0)>a0.get('wings',0) and a1.get('birdCall',0)>a0.get('birdCall',0),
          'state %s, flee +%d, wings +%d, calls +%d'%(b1['state'],a1.get('birdFlee',0)-a0.get('birdFlee',0),a1.get('wings',0)-a0.get('wings',0),a1.get('birdCall',0)-a0.get('birdCall',0)))
    ws=[]
    for _ in range(12):
        await pg.wait_for_timeout(60); ws.append((await birds())[i]['wing'])
    check('birds: wings really flap in flight',max(ws)-min(ws)>0.6,'wing angle %.2f .. %.2f rad'%(min(ws),max(ws)))
    await pg.evaluate("(()=>{const s=window.__pond.state();window.__pond.camLook(-2.5,1.6,-3.5,0,1.5,0,55)})()"); await pg.wait_for_timeout(300); await shot(pg,'birds_flee_v10.png')
    await pg.evaluate("window.__pond.reset()")
    bs=await wait_birds(lambda bs:bs[i]['state'] in ('stand','forage'),30)
    check('birds: after flying off, the egret circles back and lands in the reeds again',bs[i]['state'] in ('stand','forage'),'state %s'%bs[i]['state'])
    # rain / storm: birds shelter in the reeds (crouched, pulled back into the reed bed)
    r0={k:math.hypot(x['x'],x['z']) for k,x in enumerate(bs) if x['kind']=='egret' and x['state'] in ('stand','forage')}
    await pg.evaluate("window.__pond.setWeather('rain')")
    bs=await wait_birds(lambda bs:all(bs[k]['crouch']<-0.02 and math.hypot(bs[k]['x'],bs[k]['z'])-r0[k]>0.8 for k in r0),25)
    moved=[math.hypot(bs[k]['x'],bs[k]['z'])-r0[k] for k in r0]
    check('birds: in rain they shelter in the reeds (crouch, move back into the reed bed)',all(bs[k]['crouch']<-0.02 for k in r0) and all(m>0.8 for m in moved),'moved back %s m'%['%.1f'%m for m in moved])
    await pg.evaluate("window.__pond.setWeather('clear')")
    # F: trees fade to darker silhouettes in rain / fog (not white); lightning frame
    tp=await pg.evaluate("window.__pond.treeProbe()")
    check('trees: every pond-side plant material uses the silhouette fog',tp['silhouette'])
    for wx in ('rain','fog'):
        await pg.evaluate("window.__pond.setTod('day',true);window.__pond.setWeather('%s',true);window.__pond.camLook(4.5,2.4,6.5,-6,3.0,-10,60)"%wx); await pg.wait_for_timeout(1500)
        tp=await pg.evaluate("window.__pond.treeProbe()"); png=await pg.screenshot(); open(os.path.join(SHOT,'trees_%s_v10.png'%wx),'wb').write(png)
        from PIL import Image; import io; im=Image.open(io.BytesIO(png)).convert('RGB'); W,H=im.size; k=W/1280
        def lum(x,y):
            px=[im.getpixel((min(W-1,max(0,int(x*k)+dx)),min(H-1,max(0,int(y*k)+dy)))) for dx in (-3,0,3) for dy in (-3,0,3)]
            return sum(0.2126*p[0]+0.7152*p[1]+0.0722*p[2] for p in px)/len(px)/255
        far=[t for t in tp['trees'] if t['dist']>14]; diffs=[lum(t['x'],t['skyY'])-lum(t['x'],t['y']) for t in far]
        check('trees (%s): far trees stay darker silhouettes against the sky, not washed white'%wx,len(far)>=3 and sum(1 for d in diffs if d>0.05)>=len(far)*0.8,
              '%d far trees, sky - tree luminance %s'%(len(far),['%.2f'%d for d in diffs[:6]]))
    await pg.evaluate("window.__pond.setWeather('clear',true)"); await pg.wait_for_timeout(600); await shot(pg,'trees_day_v10.png')
    await pg.evaluate("window.__pond.setTod('night',true);window.__pond.setWeather('storm',true);window.__pond.camLook(4.5,2.4,6.5,-6,4.5,-10,64)"); await pg.wait_for_timeout(1500)
    await pg.evaluate("window.__pond.flashHold(true);window.__pond.strike({dist:450})"); await pg.wait_for_timeout(300)
    png=await pg.screenshot(); open(os.path.join(SHOT,'storm_lightning_v10.png'),'wb').write(png)
    from PIL import Image; import io; im=Image.open(io.BytesIO(png)).convert('L'); hist=im.histogram(); bright=sum(hist[245:])
    check('lightning: the captured storm frame really contains the bolt (many near-white pixels)',bright>1500,'%d near-white pixels'%bright)
    await pg.evaluate("window.__pond.flashHold(false)")
    check('birds / trees page: no console errors',not logs,str(logs[:2]))
    await pg.close()
async def phone(b):
    ctx=await b.new_context(viewport={'width':390,'height':844},device_scale_factor=3,is_mobile=True,has_touch=True)
    pg=await ctx.new_page(); logs=[]; watch(pg,logs)
    await pg.goto(URL); await pg.wait_for_function('window.__ready===true',timeout=180000); await pg.wait_for_timeout(1500)
    await pg.evaluate("window.__pond.setHint(false)")
    await pg.tap('#c',position={'x':200,'y':420}); await pg.wait_for_timeout(800); a=await aud(pg)
    check('phone 390x844: first tap unlocks audio (equal-power panning on phones)',a['ctx']=='running' and a['panModel']=='equalpower','ctx %s'%a['ctx'])
    v=await v10(pg)
    check('phone: follow camera behind the frog',v['cam']['mode']=='follow' and abs(v['cam']['behindErr'])<0.1)
    cdp=await ctx.new_cdp_session(pg)
    await cdp.send('Input.dispatchTouchEvent',{'type':'touchStart','touchPoints':[{'x':300,'y':500}]})
    for i in range(1,11): await cdp.send('Input.dispatchTouchEvent',{'type':'touchMove','touchPoints':[{'x':300-14*i,'y':500}]}); await pg.wait_for_timeout(16)
    await cdp.send('Input.dispatchTouchEvent',{'type':'touchEnd','touchPoints':[]}); await pg.wait_for_timeout(100); e1=(await v10(pg))['cam']['behindErr']
    await pg.wait_for_timeout(4000); e2=(await v10(pg))['cam']['behindErr']
    check('phone: swiping on the scene orbits the camera, then it recenters',abs(e1)>0.5 and abs(e2)<0.1,'%.2f -> %.3f rad'%(e1,e2))
    s0=await st(pg); cd=(await v10(pg))['cam']['dir']; box=await pg.evaluate("(()=>{const r=document.querySelector('#tpad .u').getBoundingClientRect();return[r.left+r.width/2,r.top+r.height/2]})()")
    await cdp.send('Input.dispatchTouchEvent',{'type':'touchStart','touchPoints':[{'x':box[0],'y':box[1]}]}); await pg.wait_for_timeout(1300)
    await cdp.send('Input.dispatchTouchEvent',{'type':'touchEnd','touchPoints':[]}); await pg.wait_for_timeout(1300); s1=await st(pg)
    mv=[s1['x']-s0['x'],s1['z']-s0['z']]; n=math.hypot(*mv) or 1
    check('phone: D-pad ▲ hops toward the camera\'s forward direction',n>0.5 and (mv[0]*cd[0]+mv[1]*cd[2])/n/math.hypot(cd[0],cd[2])>0.9,'moved %.2f m'%n)
    await pg.tap('#muteBtn'); await pg.wait_for_timeout(400); m=(await aud(pg))['muted']; await pg.tap('#muteBtn'); await pg.wait_for_timeout(300)
    check('phone: HUD 🔊 button mutes / unmutes',m and not (await aud(pg))['muted'])
    await pg.tap('#mmShow'); await pg.wait_for_timeout(700); v=await v10(pg)
    await pg.evaluate("window.__pond.mmLayer('radar')"); await pg.wait_for_timeout(300); v=await v10(pg)
    check('phone: creature radar shows the turtles (fewer on phones), never fish',v['minimap']['on'] and 5<=len([x for x in v['minimap']['icons'] if x['kind']=='turtle'])<=8 and not any(x['kind']=='fish' for x in v['minimap']['icons']),'%d icons'%len(v['minimap']['icons']))
    r=await pg.evaluate("(()=>{const b=document.querySelector('#mmLayer').getBoundingClientRect();return[b.width,b.height]})()")
    check('phone: the minimap layer button is big enough to tap',r[0]>=22 and r[1]>=22,'%.0fx%.0f px'%tuple(r))
    await pg.evaluate("window.__pond.mmLayer('env')")
    await pg.evaluate("window.__pond.setTod('night');window.__pond.setWeather('rain')"); await pg.wait_for_timeout(3000)
    await pg.screenshot(path=os.path.join(SHOT,'phone_390x844_v10.png'))
    await pg.evaluate("window.__pond.setTod('day');window.__pond.setWeather('clear')"); await pg.wait_for_timeout(3500); await pg.screenshot(path=os.path.join(SHOT,'phone_390x844_day_v10.png'))
    errs=[l for l in logs if l[0] in ('error','pageerror','http')]
    check('phone: no console errors / no HTTP errors',not errs,str(errs[:3]))
    await ctx.close()
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(channel='chrome')
        await desktop(b); await c2(b); await birds_trees(b); await phone(b); await b.close()
    txt='\n'.join(R)+'\n\nRESULT: '+('ALL PASS' if ok_all else 'FAILURES')+' (%d checks)\n'%len(R)
    open(os.path.join(ROOT,'test_v10_report.txt'),'w',encoding='utf-8').write(txt); print('RESULT',ok_all)
asyncio.run(main())
