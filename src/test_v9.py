# v9 headless test: minimap, headlamp, underwater life (fish / turtles), time of day + weather, phone viewport (390x844).
# usage: python src/test_v9.py [url]      -> prints PASS/FAIL per check, writes screenshots/*_v9.png + test_v9_report.txt
import asyncio,sys,math,os,json
from playwright.async_api import async_playwright
URL=sys.argv[1] if len(sys.argv)>1 else 'http://127.0.0.1:18977/qingyue-pond.html'
ROOT=os.path.join(os.path.dirname(os.path.abspath(__file__)),'..'); SHOT=os.path.join(ROOT,'screenshots'); os.makedirs(SHOT,exist_ok=True)
R=[];ok_all=True
def check(name,cond,info=''):
    global ok_all
    ok_all&=bool(cond); R.append(('PASS' if cond else 'FAIL')+'  '+name+('  | '+info if info else '')); print(R[-1],flush=True)
async def st(pg): return await pg.evaluate('window.__pond.state()')
async def v9(pg): return await pg.evaluate('window.__pond.v9()')
async def at(pg): return await pg.evaluate('window.__pond.atmo()')
async def hold(pg,key,ms):
    await pg.keyboard.down(key); await pg.wait_for_timeout(ms); await pg.keyboard.up(key)
def overlap(a,b): return not (a[2]<=b[0] or b[2]<=a[0] or a[3]<=b[1] or b[3]<=a[1])
def rect(r): return [r['left'],r['top'],r['right'],r['bottom']]
async def shot(pg,name,hud=False):
    if not hud: await pg.evaluate("document.querySelector('#hud').style.visibility='hidden'")
    await pg.screenshot(path=os.path.join(SHOT,name)); await pg.evaluate("document.querySelector('#hud').style.visibility=''")
def watch(pg,logs):
    pg.on('console',lambda m:logs.append((m.type,m.text))); pg.on('pageerror',lambda e:logs.append(('pageerror',str(e))))
    pg.on('response',lambda r:logs.append(('http',r.status,r.url)) if r.status>=400 else None)
async def desktop(b):
    pg=await b.new_page(viewport={'width':1280,'height':800}); logs=[]; watch(pg,logs)
    await pg.goto(URL); await pg.wait_for_function('window.__ready===true',timeout=180000); await pg.wait_for_timeout(1500)
    await pg.evaluate("document.body.classList.add('nopanel')")
    # ---------------- minimap
    m=(await v9(pg))['minimap']
    check('minimap: shown by default on desktop, round, inside the viewport',m['on'] and m['rect'] and m['rect'][0]>=0 and m['rect'][3]<=800 and abs((m['rect'][2]-m['rect'][0])-(m['rect'][3]-m['rect'][1]))<1,str(m['rect']))
    info=await pg.evaluate("(()=>{const c=document.querySelector('#mmc'),x=c.getContext('2d');const d=x.getImageData(0,0,c.width,c.height).data;let n=0;for(let i=0;i<d.length;i+=4)if(d[i+1]>100&&d[i]<110&&d[i+2]<90)n++;return{w:c.width,green:n,pads:window.__pond.state().pads}})()")
    check('minimap: pond boundary + all lily pads drawn (green pad pixels)',info['green']>200,'%d green px on a %d px canvas'%(info['green'],info['w']))
    p0=(await v9(pg))['minimap']['frogPx']; await pg.keyboard.press('1'); await hold(pg,'d',250); await pg.wait_for_timeout(1500)
    p1=(await v9(pg))['minimap']['frogPx']
    check('minimap: frog marker follows the frog in real time',math.hypot(p1[0]-p0[0],p1[1]-p0[1])>0.8,'%.1f px'%math.hypot(p1[0]-p0[0],p1[1]-p0[1]))
    FAN="(()=>{const c=document.querySelector('#mmc'),x=c.getContext('2d');const d=x.getImageData(0,0,c.width,c.height).data;let n=0;for(let i=0;i<d.length;i+=4)if(d[i]>d[i+2]+12&&d[i+1]>d[i+2]+8)n++;return n})()"
    fan=await pg.evaluate(FAN); fanR=(await v9(pg))['minimap']['fanR']
    check('minimap: view fan (camera direction + FOV, radius = visibility) drawn',fan>150 and fanR>5,'%d fan px, radius %.1f m'%(fan,fanR))
    await pg.click('#mmIn'); z=(await v9(pg))['minimap']['zoom']; await pg.click('#mmOut')
    check('minimap: zoom in / out buttons',z==2 and (await v9(pg))['minimap']['zoom']==1)
    await pg.keyboard.press('m'); off=(await v9(pg))['minimap']['on']; vis=await pg.evaluate("getComputedStyle(document.querySelector('#mmShow')).display")
    await pg.keyboard.press('m'); on=(await v9(pg))['minimap']['on']
    check('minimap: M collapses (leaves a small 地图 button) and restores',(not off) and vis!='none' and on)
    await pg.evaluate("window.__pond.reset()"); await pg.wait_for_timeout(800)
    await pg.evaluate("window.__pond.camTo(-2.2,1.6,-2.6)"); await pg.wait_for_timeout(500); await shot(pg,'minimap_v9.png',hud=True)
    # ---------------- headlamp
    L=(await v9(pg))['lamp']
    check('headlamp: modelled lamp body parented to the head bone',L['parent'] and 'head' in L['parent'].lower() and L['meshes']>=8,'parent %s, %d meshes'%(L['parent'],L['meshes']))
    await pg.keyboard.press('l'); await pg.wait_for_timeout(700); L=(await v9(pg))['lamp']
    check('headlamp: L switches the SpotLight + visible beam on',L['on'] and L['intensity']>4 and L['beam'] and await pg.evaluate("document.querySelector('#lampOn').checked"),'intensity %.1f'%L['intensity'])
    ds=[];ps=[]; await pg.keyboard.press('c')
    for _ in range(12):
        await pg.wait_for_timeout(90); L=(await v9(pg))['lamp']; ds.append(L['headD']); ps.append(L['pos'])
    mv=max(math.dist(ps[0],p) for p in ps)
    check('headlamp: follows the head bone while animating (rigid offset, lamp moves)',max(ds)-min(ds)<0.002 and mv>0.003,'head offset %.4f..%.4f m, lamp moved %.3f m'%(min(ds),max(ds),mv))
    await pg.wait_for_timeout(2500)
    await pg.evaluate("window.__pond.camTo(2.9,1.2,-0.8)"); await pg.wait_for_timeout(600); await shot(pg,'headlamp_surface_v9.png')
    # underwater: dive and keep the lamp on
    await pg.keyboard.press('3'); await pg.wait_for_timeout(2600); await hold(pg,'e',1400); await pg.wait_for_timeout(300)
    s=await st(pg); L=(await v9(pg))['lamp']
    check('headlamp: works under water (stronger beam)',s['y']<-0.6 and L['on'] and L['intensity']>7,'y %.2f, intensity %.1f'%(s['y'],L['intensity']))
    await pg.evaluate("window.__pond.camTo(1.6,0.15,1.9)"); await pg.wait_for_timeout(800); await shot(pg,'headlamp_underwater_v9.png')
    await pg.keyboard.press('l'); await pg.wait_for_timeout(300)
    check('headlamp: L switches it off again',not (await v9(pg))['lamp']['on'])
    # ---------------- fish
    a=await v9(pg); await pg.wait_for_timeout(1500); b2=await v9(pg)
    check('fish: 3 species, schools, detailed bodies (not placeholder boxes)',len(a['fish'])==3 and all(f['n']>=6 and f['verts']>500 for f in a['fish']),', '.join('%s x%d (%d verts)'%(f['name'],f['n'],f['verts']) for f in a['fish']))
    moved=[math.dist(f['c'],g['c']) for f,g in zip(a['fish'],b2['fish'])]
    check('fish: schools swim around (positions + tail-beat clock advance)',min(moved)>0.05 and b2['fish'][0]['t']>a['fish'][0]['t'],'school moves %s m'%', '.join('%.2f'%x for x in moved))
    check('fish: stay inside the water (floor -1.9 .. surface 0)',all(f['ymin']>-1.9 and f['ymax']<0 for f in b2['fish']),', '.join('%.2f..%.2f'%(f['ymin'],f['ymax']) for f in b2['fish']))
    c=b2['schools'][0]['c']; await pg.evaluate("window.__pond.placeWater(%f,%f,0)"%(c[0],c[2])); await pg.wait_for_timeout(100)
    await pg.keyboard.down('e')
    for _ in range(40):
        await pg.wait_for_timeout(50)
        if (await st(pg))['y']<c[1]+0.15: break
    await pg.keyboard.up('e'); d0=(await v9(pg))['schools'][0]['dFrog']; await pg.wait_for_timeout(2500); d1=(await v9(pg))['schools'][0]['dFrog']
    check('fish: school scatters away from the frog',d1>d0+0.2,'mean distance %.2f -> %.2f m'%(d0,d1))
    f=(await v9(pg))['fish'][1]['c']; await pg.evaluate("window.__pond.placeWater(%f,%f,0)"%(f[0]+2.2,f[2]+2.2)); await pg.wait_for_timeout(300)
    await hold(pg,'e',1200); await pg.evaluate("window.__pond.setTod('day')"); await pg.wait_for_timeout(2500)
    f=(await v9(pg))['fish'][1]['c']; s=await st(pg)
    await pg.evaluate("window.__pond.camLook(%f,%f,%f,%f,%f,%f,50)"%(f[0]-s['x']+1.7,max(-1.5,f[1]-s['y']+0.25),f[2]-s['z']+1.7,f[0]-s['x'],f[1]-s['y'],f[2]-s['z'])); await pg.wait_for_timeout(500)
    await shot(pg,'fish_school_v9.png')
    # ---------------- turtles
    t0=(await v9(pg))['turtles']; await pg.wait_for_timeout(3000); t1=(await v9(pg))['turtles']
    tm=[math.hypot(x['x']-y['x'],x['z']-y['z']) for x,y in zip(t0,t1)]
    check('turtles: one crawls on the floor, one swims, they move',len(t1)>=2 and any(t['swimmer'] for t in t1) and any(not t['swimmer'] and abs(t['y']+1.9)<0.05 for t in t1) and max(tm)>0.05,'moved %s m'%', '.join('%.2f'%x for x in tm))
    check('turtles: legs animate (crawl / paddle)',any(abs(x['leg']-y['leg'])>0.02 for x,y in zip(t0,t1)))
    tt=[t for t in t1 if not t['swimmer']][0]; await pg.evaluate("window.__pond.placeWater(%f,%f,0)"%(tt['x']+0.6,tt['z'])); await hold(pg,'e',2200); await pg.wait_for_timeout(500)
    tt2=[t for t in (await v9(pg))['turtles'] if not t['swimmer']][0]
    check('turtles: startled by the frog -> pulls head and legs in',tt2['scared']>0 and tt2['retract']>0.4,'retract %.2f'%tt2['retract'])
    await pg.wait_for_timeout(3500); tt=[t for t in (await v9(pg))['turtles'] if not t['swimmer']][0]; s=await st(pg)
    await pg.evaluate("window.__pond.camLook(%f,%f,%f,%f,%f,%f,46)"%(tt['x']-s['x']+0.9,-1.35-s['y'],tt['z']-s['z']+0.9,tt['x']-s['x'],-1.8-s['y'],tt['z']-s['z'])); await pg.wait_for_timeout(500)
    await shot(pg,'turtle_v9.png')
    # ---------------- time of day + weather
    await pg.evaluate("window.__pond.setTod('night');window.__pond.setWeather('clear');window.__pond.reset()"); await pg.wait_for_timeout(800)
    n0=await at(pg); await pg.keyboard.press('n'); await pg.wait_for_timeout(1200); mid=await at(pg); await pg.wait_for_timeout(2500); d=await at(pg)
    check('time of day: N cycles night -> day with a smooth cross-fade',mid['tod']=='day' and 0.1<mid['wT']['day']<0.9 and d['wT']['day']>0.95,'day weight %.2f after 1.2 s, %.2f after 3.7 s'%(mid['wT']['day'],d['wT']['day']))
    check('time of day: day = bright blue sky, high sun key light, no stars / moon / fireflies',sum(d['skyTop'])>sum(n0['skyTop'])*4 and d['keyI']>n0['keyI']*1.4 and d['keyDirY']>0.7 and d['stars']<0.01 and not d['moon'] and not d['ff'],'sky %.2f vs %.2f'%(sum(d['skyTop']),sum(n0['skyTop'])))
    check('time of day: dragonflies fly by day (and avoid the frog)',d['dfly']>=3 and all(math.hypot(p[0],p[2])<26 and p[1]>0.2 for p in d['dflyPos']),'%d dragonflies'%d['dfly'])
    await pg.evaluate("window.__pond.camLook(4.5,2.4,6.5,-6,1.6,-10,64)"); await pg.wait_for_timeout(400); await shot(pg,'day_clear_v9.png')
    await pg.keyboard.press('n'); await pg.wait_for_timeout(4500); k=await at(pg)
    check('time of day: dusk = low warm sun, a few stars, fireflies return',k['tod']=='dusk' and k['keyDirY']<0.2 and 0<k['stars']<0.5 and k['ff'],'sun height %.2f'%k['keyDirY'])
    await shot(pg,'dusk_v9.png')
    await pg.keyboard.press('n')
    for _ in range(40):   # poll (the 2.5 s cross-fade must finish; a fixed sleep was flaky on slow machines)
        await pg.wait_for_timeout(250); k=await at(pg)
        if k['tod']=='night' and k['moon'] and k['stars']>0.8 and k['ff']: break
    check('time of day: back to night keeps the moon, stars and fireflies',k['tod']=='night' and k['moon'] and k['stars']>0.8 and k['ff'])
    clear=k['fogD']
    await pg.keyboard.press('g'); await pg.wait_for_timeout(4000); k=await at(pg)
    check('weather: G -> overcast (cloud cover, dimmer light)',k['wx']=='overcast' and k['cloud']>0.7 and k['keyI']<0.7*1.35,'cloud %.2f'%k['cloud'])
    await pg.evaluate("window.__pond.setTod('day')"); await pg.keyboard.press('g'); await pg.wait_for_timeout(4000); k=await at(pg)
    check('weather: rain = falling streaks + ripple rings on the water',k['wx']=='rain' and k['rain'] and k['ripples'] and k['rainN']>=500 and k['ripN']>=16,'%d drops, %d ripple rings'%(k['rainN'],k['ripN']))
    await shot(pg,'rain_v9.png')
    await pg.keyboard.press('g'); await pg.wait_for_timeout(4000); k=await at(pg)
    check('weather: fog lowers visibility (fog density x5+)',k['wx']=='fog' and k['sceneFog']>clear*5,'density %.3f vs clear %.3f'%(k['sceneFog'],clear))
    fr=(await v9(pg))['minimap']['fanR']
    check('weather: minimap view fan shrinks with the fog',fr<fanR*0.8,'radius %.1f m vs %.1f m clear'%(fr,fanR))
    await shot(pg,'fog_v9.png')
    await pg.keyboard.press('g'); await pg.wait_for_timeout(4000); k=await at(pg)
    check('weather: snow = drifting flakes',k['wx']=='snow' and k['snow'] and k['snowN']>=400 and not k['rain'],'%d flakes'%k['snowN'])
    await pg.evaluate("window.__pond.setTod('night')"); await pg.wait_for_timeout(4000); await shot(pg,'snow_v9.png')
    await pg.check('#thunderOn') if await pg.evaluate("!document.body.classList.contains('nopanel')") else await pg.evaluate("document.querySelector('#thunderOn').click()")
    s0=(await at(pg))['strikes']; await pg.keyboard.press('g'); flashes=[]
    for _ in range(80):
        await pg.wait_for_timeout(100); k=await at(pg); flashes.append(k['flash'])
        if k['strikes']>s0 and k['flash']>0.5: break
    check('weather: storm = heavy rain + lightning flashes (+ optional thunder)',k['wx']=='storm' and k['rain'] and k['strikes']>s0 and max(flashes)>0.5 and k['thunder'],'%d strikes, max flash %.2f'%(k['strikes']-s0,max(flashes)))
    await pg.wait_for_timeout(2500); await pg.evaluate("window.__pond.camLook(4.5,2.4,6.5,-6,3,-10,64)")
    await pg.wait_for_function("window.__pond.atmo().flash>0.5",timeout=20000); await shot(pg,'storm_v9.png')
    await pg.evaluate("document.querySelector('#thunderOn').click()")
    # headlamp in every time x weather combination
    bad=[]
    for t in ['day','dusk','night']:
        for w in ['clear','overcast','rain','fog','snow','storm']:
            await pg.evaluate("window.__pond.setTod('%s');window.__pond.setWeather('%s');window.__pond.setLamp(true)"%(t,w)); await pg.wait_for_timeout(250)
            L=(await v9(pg))['lamp']
            if not (L['on'] and L['beam'] and L['intensity']>3): bad.append(t+'/'+w)
    check('headlamp: usable in all 18 time x weather combinations',not bad,str(bad))
    await pg.evaluate("window.__pond.setLamp(false);window.__pond.setTod('day');window.__pond.setWeather('clear')")
    await pg.keyboard.press('3'); await pg.wait_for_timeout(2600); await hold(pg,'e',1200); await pg.evaluate("window.__pond.camTo(2.1,0.15,1.5)"); await pg.wait_for_timeout(600)
    s=await st(pg); check('daytime underwater still uses the dense underwater fog',s['under'] and s['fog']>0.15,'fog %.2f'%s['fog'])
    await pg.evaluate("window.__pond.setTod('night')")
    errs=[l for l in logs if l[0] in ('error','pageerror','http')]
    check('desktop: no console errors / no HTTP errors',not errs,str(errs[:3]))
    await pg.close()
async def phone(b):
    ctx=await b.new_context(viewport={'width':390,'height':844},device_scale_factor=3,is_mobile=True,has_touch=True)
    pg=await ctx.new_page(); logs=[]; watch(pg,logs)
    await pg.goto(URL); await pg.wait_for_function('window.__ready===true',timeout=180000); await pg.wait_for_timeout(1500)
    v=await v9(pg); a=await at(pg)
    check('phone 390x844: mobile tier (low particle quality, fewer fish)',v['mobile'] and a['quality']=='low' and sum(f['n'] for f in v['fish'])<=30,'quality %s, %d fish'%(a['quality'],sum(f['n'] for f in v['fish'])))
    vis=await pg.evaluate("['#tpad','#tact'].map(s=>getComputedStyle(document.querySelector(s)).display!=='none')")
    check('phone: on-screen D-pad + up/down buttons shown',all(vis))
    check('phone: minimap starts collapsed so it never covers the controls',not v['minimap']['on'])
    await pg.tap('#mmShow'); await pg.wait_for_timeout(700); v=await v9(pg)
    rs={s:rect(await pg.evaluate("(()=>{const r=document.querySelector('%s').getBoundingClientRect();return{left:r.left,top:r.top,right:r.right,bottom:r.bottom}})()"%s)) for s in ['#tpad','#tact','#hud']}
    mm=v['minimap']['rect']
    check('phone: expanded minimap does not overlap the D-pad, action buttons or HUD',v['minimap']['on'] and mm and not any(overlap(mm,r) for r in rs.values()) and mm[2]<=390 and mm[3]<=844,'minimap %s'%[round(x) for x in mm])
    await pg.tap('#mmIn'); z=(await v9(pg))['minimap']['zoom']; await pg.tap('#mmOut')
    check('phone: minimap zoom buttons work by touch',z==2)
    s0=await st(pg); box=await pg.evaluate("(()=>{const r=document.querySelector('#tpad .u').getBoundingClientRect();return[r.left+r.width/2,r.top+r.height/2]})()")
    cdp=await ctx.new_cdp_session(pg)
    await cdp.send('Input.dispatchTouchEvent',{'type':'touchStart','touchPoints':[{'x':box[0],'y':box[1]}]}); await pg.wait_for_timeout(1300)
    await cdp.send('Input.dispatchTouchEvent',{'type':'touchEnd','touchPoints':[]}); await pg.wait_for_timeout(1300); s1=await st(pg)
    check('phone: holding ▲ on the D-pad hops the frog',s1['log'].count('hop')>s0['log'].count('hop') and math.hypot(s1['x']-s0['x'],s1['z']-s0['z'])>0.5,'moved %.2f m'%math.hypot(s1['x']-s0['x'],s1['z']-s0['z']))
    await pg.tap('#lampBtn'); await pg.wait_for_timeout(500); check('phone: 头灯 button toggles the headlamp',(await v9(pg))['lamp']['on'])
    frames=[]
    for t,w in [('night','clear'),('day','rain'),('dusk','snow'),('night','storm'),('day','fog')]:
        await pg.evaluate("window.__pond.setTod('%s');window.__pond.setWeather('%s')"%(t,w)); await pg.wait_for_timeout(400)
        n=await pg.evaluate("new Promise(r=>{let n=0;const t0=performance.now();const f=()=>{n++;if(performance.now()-t0<1500)requestAnimationFrame(f);else r(n/((performance.now()-t0)/1000))};requestAnimationFrame(f)})")
        frames.append('%s/%s %.0f fps'%(t,w,n))
    k=await at(pg)
    check('phone: all time/weather combos run (low tier particle counts)',k['rainN']<=600 and k['ripN']<=20,'; '.join(frames)+' (headless software GL)')
    await pg.evaluate("window.__pond.setTod('night');window.__pond.setWeather('rain')"); await pg.wait_for_timeout(3000)
    await pg.screenshot(path=os.path.join(SHOT,'phone_390x844_v9.png'))
    errs=[l for l in logs if l[0] in ('error','pageerror','http')]
    check('phone: no console errors / no HTTP errors',not errs,str(errs[:3]))
    await ctx.close()
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(channel='chrome',args=['--autoplay-policy=no-user-gesture-required'])
        await desktop(b); await phone(b); await b.close()
    txt='\n'.join(R)+'\n\nRESULT: '+('ALL PASS' if ok_all else 'FAILURES')+' (%d checks)\n'%len(R)
    open(os.path.join(ROOT,'test_v9_report.txt'),'w',encoding='utf-8').write(txt); print('RESULT',ok_all)
asyncio.run(main())
