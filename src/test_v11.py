# v11 headless test: detailed animals (Blender glb) - files + budgets, loading, skinning / LOD / feather fold, animation really playing,
# turtle (retract, breathing at the surface, basking on a lily pad -> slide in -> climb back), kingfisher catches + eats a fish,
# egret flees -> spread wings / S-neck -> lands back, night heron (hunched, strike, eyeshine in the headlamp), little grebe dive + surface,
# wet look in rain, radar unaffected, phone viewport (390x844); close-up screenshots (day / night headlamp / rain / phone) + v10 vs v11 comparisons.
# usage: python src/test_v11.py [url] [screens dir]   -> prints PASS/FAIL per check, writes test_v11_report.txt + screenshots
import asyncio,os,sys,math,glob
from playwright.async_api import async_playwright
from PIL import Image,ImageDraw
URL=sys.argv[1] if len(sys.argv)>1 else 'http://127.0.0.1:18977/qingyue-pond.html'
ROOT=os.path.join(os.path.dirname(os.path.abspath(__file__)),'..')
SHOT=sys.argv[2] if len(sys.argv)>2 else os.path.join(os.path.expanduser('~'),'Tilo工作台','20261028-青跃三维','screens-v11')
os.makedirs(SHOT,exist_ok=True)
KINDS=['turtle','egret','heron','kingfisher','grebe']
R=[];ok_all=True
def check(name,cond,info=''):
    global ok_all
    ok_all&=bool(cond); R.append(('PASS' if cond else 'FAIL')+'  '+name+('  | '+info if info else '')); print(R[-1],flush=True)
async def v11(pg): return await pg.evaluate('window.__pond.v11()')
async def st(pg): return await pg.evaluate('window.__pond.state()')
async def wait(pg,ms): await pg.wait_for_timeout(ms)
def watch(pg,logs):
    pg.on('console',lambda m:logs.append((m.type,m.text))); pg.on('pageerror',lambda e:logs.append(('pageerror',str(e))))
    pg.on('response',lambda r:logs.append(('http',r.status,r.url)) if r.status>=400 else None)
def dist(a,b): return math.dist(a,b)
async def shot(pg,name):
    await pg.evaluate("for(const s of ['#hud','#toast','#mm','#mmShow'])document.querySelectorAll(s).forEach(e=>e.style.visibility='hidden')")
    await pg.screenshot(path=os.path.join(SHOT,name))
    await pg.evaluate("for(const s of ['#hud','#toast','#mm','#mmShow'])document.querySelectorAll(s).forEach(e=>e.style.visibility='')")
async def open_page(b,w=1280,h=800,q=''):
    pg=await b.new_page(viewport={'width':w,'height':h}); logs=[]; watch(pg,logs)
    await pg.goto(URL+q); await pg.wait_for_function('window.__ready===true',timeout=180000); await wait(pg,1200)
    await pg.evaluate("document.body.classList.add('nopanel');window.__pond.setHint(false)")
    return pg,logs
async def until(pg,fn,secs=25,step=250):
    v=None
    for _ in range(int(secs*1000/step)):
        v=await v11(pg)
        if fn(v): return v
        await wait(pg,step)
    return v
# frame a creature: frog in the water `back` m toward the pond centre (facing it), camera `d` m in front of it, looking at height `h`
async def closeup(pg,x,y,z,d,h,back=1.6,side=0.55,lamp=False,face=None,fov=40,up=0.12):
    a=math.atan2(z,x); fx,fz=x-math.cos(a)*(d+back),z-math.sin(a)*(d+back)
    await pg.evaluate("window.__pond.placeWater(%f,%f,%f)"%(fx,fz,math.atan2(x-fx,z-fz)))
    if face is not None: await pg.evaluate("window.__pond.birdHome(%d,%f,%f,%f)"%(face,x,z,math.atan2(fx-x,fz-z)+0.45))
    await pg.evaluate("window.__pond.setLamp(%s)"%('true' if lamp else 'false')); await wait(pg,700)
    s=await st(pg); cx,cz=x-math.cos(a)*d+math.sin(a)*side,z-math.sin(a)*d-math.cos(a)*side
    await pg.evaluate("window.__pond.camLook(%f,%f,%f,%f,%f,%f,%d)"%(cx-s['x'],y+h+up-s['y'],cz-s['z'],x-s['x'],y+h-s['y'],z-s['z'],fov)); await wait(pg,600)
FRAME={'egret':(3.0,0.75,0.12),'heron':(2.4,0.5,0.12),'kingfisher':(0.95,0.14,0.1),'grebe':(1.1,0.06,0.42)}
async def bird_closeup(pg,kind,name,lamp=False,states=('stand','forage','perch','swim'),secs=40):
    v=await until(pg,lambda v:any(b['kind']==kind and b['visible'] and b['state'] in states for b in v['birds']),secs)
    i=next((i for i,b in enumerate(v['birds']) if b['kind']==kind and b['visible'] and b['state'] in states),None)
    if i is None: return None
    b=v['birds'][i]; d,h,up=FRAME[kind]; await closeup(pg,b['x'],b['y'],b['z'],d,h,lamp=lamp,face=i,up=up)
    if name: await shot(pg,name)
    return i

async def desktop(b):
    pg,logs=await open_page(b)
    # ---------------- files, loading, budgets
    sizes={k:os.path.getsize(os.path.join(ROOT,'animals',k+'.glb')) for k in KINDS}
    check('files: one glb per animal, each < 1.5 MB (WebP textures)',all(s<1.5*1024*1024 for s in sizes.values()),', '.join('%s %.0f KB'%(k,s/1024) for k,s in sizes.items()))
    big=[f for f in glob.glob(os.path.join(ROOT,'animals','*')) if f.endswith(('.blend','.fbx','.zip','.png'))]
    check('files: no blend / fbx / zip / loose png sources next to the runtime models',not big,str(big))
    v=await v11(pg)
    check('loading: all five models load (turtle, egret, night heron, kingfisher, little grebe), no errors',all(v['loaded'][k] for k in KINDS) and not v['errors'],str(v['loaded'])+' '+str(v['errors']))
    inf=v['info']
    check('budget: LOD0 <= 20k triangles per animal (body + feathers + eyes / + shell), LOD1 <= 6k',all(inf[k]['lod0']<=20000 and inf[k]['lod1']<=6000 for k in KINDS),
          ', '.join('%s %d/%d'%(k,inf[k]['lod0'],inf[k]['lod1']) for k in KINDS))
    texok=all(int(t.split('x')[0])<=1024 and int(t.split('x')[1].split(' ')[0])<=1024 for k in KINDS for t in inf[k]['textures'])
    check('budget: textures <= 1024 px (baked colour / normal / roughness; shared feather atlas)',texok,'%d textures'%sum(len(inf[k]['textures']) for k in KINDS))
    ms={k:inf[k]['meshes'] for k in KINDS}
    check('models: skinned bodies + LOD1 on every animal, feather cards with a "fold" morph on every bird, a separate carapace on the turtle',
          all(any(m['skinned'] and m['name'].endswith('_body') for m in ms[k]) and any(m['name'].endswith('_LOD1') for m in ms[k]) for k in KINDS)
          and all(any(m['name'].endswith('_feathers') and 'fold' in m['morphs'] for m in ms[k]) for k in KINDS if k!='turtle') and any(m['name']=='turtle_shell' for m in ms['turtle']),
          '; '.join('%s: %s'%(k,','.join(m['name'].split('_',1)[1] for m in ms[k])) for k in KINDS))
    check('scene: every turtle and every bird uses the v11 model',all(t['v11'] for t in v['turtles']) and all(x['v11'] for x in v['birds']),'%d turtles, %d birds'%(len(v['turtles']),len(v['birds'])))
    # ---------------- animation really plays (bones move relative to the body)
    rel=lambda t,k:[t[k][i]-[t['x'],t['y'],t['z']][i] for i in range(3)]
    sw=[i for i,t in enumerate(v['turtles']) if t['surf']=='swim' and not t['basker']]
    a0=v['turtles']; await wait(pg,1200); a1=(await v11(pg))['turtles']
    moved=max(dist(rel(a0[i],'foot'),rel(a1[i],'foot')) for i in sw)
    check('animation: turtle limbs move (paddling / crawling, bones driven every frame)',moved>0.01,'max foot move %.3f m'%moved)
    # ---------------- LOD
    lo=v['lod']['turtle']
    check('LOD: near turtles use LOD0, far ones LOD1 (desktop switch at %.1f m)'%v['lodDist']['turtle'],lo[0]>=1 and lo[1]>=1,'LOD0 %d, LOD1 %d'%tuple(lo))
    # ---------------- turtle: basking on a lily pad
    bk=[i for i,t in enumerate(v['turtles']) if t['basker']]
    check('turtle: some bask on lily pads near the start (head up, legs splayed)',len(bk)>=1 and all(v['turtles'][i]['basker']=='pad' and v['turtles'][i]['y']>-0.02 for i in bk),
          ', '.join('%s y %.2f'%(v['turtles'][i]['basker'],v['turtles'][i]['y']) for i in bk))
    t=v['turtles'][bk[0]]; await pg.evaluate("window.__pond.setTod('day',true);window.__pond.setWeather('clear',true);window.__pond.v11Calm(true)"); await wait(pg,3000)
    await closeup(pg,t['x'],t['y'],t['z'],1.3,0.1,back=1.5); await shot(pg,'turtle_basking_day.png')
    await pg.evaluate("window.__pond.v11Calm(false)")
    e0=(await v11(pg))['events']; d0=(await pg.evaluate('window.__pond.audio()'))['events'].get('turtleDive',0)
    await pg.evaluate("window.__pond.baskDive(0)")
    v=await until(pg,lambda v:v['turtles'][bk[0]]['basker']=='swim',6)
    d1=(await pg.evaluate('window.__pond.audio()'))['events'].get('turtleDive',0)
    check('turtle: startled on the pad -> slides into the water (splash + plop) and swims off under water',v['turtles'][bk[0]]['basker']=='swim' and v['events']['turtleBaskDive']>e0['turtleBaskDive'] and v['turtles'][bk[0]]['y']<-0.1,
          'state %s, y %.2f, plop sounds +%d'%(v['turtles'][bk[0]]['basker'],v['turtles'][bk[0]]['y'],d1-d0))
    await pg.evaluate("window.__pond.reset()")
    v=await until(pg,lambda v:v['turtles'][bk[0]]['basker']=='pad' and v['events']['turtleClimb']>e0['turtleClimb'],40)
    check('turtle: when the frog has gone it swims back and climbs onto its pad again',v['turtles'][bk[0]]['basker']=='pad' and v['events']['turtleClimb']>e0['turtleClimb'],'state %s'%v['turtles'][bk[0]]['basker'])
    # ---------------- turtle: breathing at the surface (only the head out)
    i=await pg.evaluate("window.__pond.turtleSurface(0)")
    v=await until(pg,lambda v:v['turtles'][i]['surf']=='bask' and v['turtles'][i]['breath']>0.6,30)
    t=v['turtles'][i]
    check('turtle: comes up to breathe - snout up, the head breaks the surface while the shell stays just under',t['surf']=='bask' and t['pitch']<-0.15 and t['head'][1]>-0.06 and t['y']<-0.1,
          'pitch %.2f, head y %.2f, body y %.2f'%(t['pitch'],t['head'][1],t['y']))
    await closeup(pg,t['x'],t['y'],t['z'],1.3,0.2,back=1.3); await shot(pg,'turtle_breathing_day.png')
    # ---------------- turtle: retracts the head when the frog comes close
    v=await v11(pg); ci=[k for k,t in enumerate(v['turtles']) if t['y']<-1.7]   # crawlers on the pond floor
    k=ci[0]; t=v['turtles'][k]; hd0=dist(rel(t,'head'),[0,0,0])
    await pg.evaluate("window.__pond.placeWater(%f,%f,0)"%(t['x']+0.6,t['z'])); await pg.keyboard.down('e'); await wait(pg,2200); await pg.keyboard.up('e')
    v=await until(pg,lambda v:v['turtles'][k]['retract']>0.6,4); t=v['turtles'][k]; hd1=dist(rel(t,'head'),[0,0,0])
    check('turtle: startled -> head pulled back into the shell (head bone moves in), legs drawn in',t['retract']>0.6 and hd1<hd0-0.04*1.35,'retract %.2f, head %.2f -> %.2f m from the body origin'%(t['retract'],hd0,hd1))
    s=await st(pg); await pg.evaluate("window.__pond.camLook(%f,%f,%f,%f,%f,%f,42)"%(t['x']-s['x']-0.75,-1.5-s['y'],t['z']-s['z']+0.75,t['x']-s['x'],-1.78-s['y'],t['z']-s['z'])); await wait(pg,300)   # from the side away from the frog
    await shot(pg,'turtle_retract_underwater.png')
    # ---------------- day birds: close-ups, egret flee / land, wading steps, kingfisher catch, grebe dive
    await pg.evaluate("window.__pond.reset();window.__pond.v11Calm(true)")
    for kd in ('egret','kingfisher','grebe'):
        i=await bird_closeup(pg,kd,kd+'_day.png')
        check('%s: lands by day and is rendered close up (screenshot %s_day.png)'%(kd,kd),i is not None)
    # animation: a standing/foraging egret's head bone moves relative to its feet
    v=await v11(pg); ei=next(i for i,x in enumerate(v['birds']) if x['kind']=='egret' and x['state'] in ('stand','forage'))
    hs=[]
    for _ in range(14):
        x=(await v11(pg))['birds'][ei]; hs.append([x['head'][j]-[x['x'],x['y'],x['z']][j] for j in range(3)]); await wait(pg,250)
    span=max(dist(a,c) for a in hs for c in hs)
    check('animation: egret neck / head pose changes over time (stand, look around, peck)',span>0.05,'head moved %.2f m relative to the feet'%span)
    e0=(await v11(pg))['events']; await wait(pg,9000); e1=(await v11(pg))['events']
    check('egret: wades slowly through the shallows while foraging (leg steps)',e1['egretStep']>e0['egretStep'],'+%d steps in 9 s'%(e1['egretStep']-e0['egretStep']))
    # kingfisher: forced plunge -> fish in the bill -> back to the perch -> beats + swallows it (start from an idle bird on its twig)
    await until(pg,lambda v:any(x['kind']=='kingfisher' and x['state']=='perch' and not x['prey'] and x['eatT']==0 for x in v['birds']),20); e1=(await v11(pg))['events']
    await pg.evaluate("window.__pond.kfDive(true)")
    v=await until(pg,lambda v:v['events']['kfCatch']>e1['kfCatch'],6)
    kf=next(x for x in v['birds'] if x['kind']=='kingfisher')
    check('kingfisher: plunges into the water and comes up with a fish in its bill (catch event)',v['events']['kfDive']>e1['kfDive'] and v['events']['kfCatch']>e1['kfCatch'] and kf['prey'],
          'dives +%d, catches +%d, fish in bill %s'%(v['events']['kfDive']-e1['kfDive'],v['events']['kfCatch']-e1['kfCatch'],kf['prey']))
    v=await until(pg,lambda v:next(x for x in v['birds'] if x['kind']=='kingfisher')['eatT']>0,10); ki=next(i for i,x in enumerate(v['birds']) if x['kind']=='kingfisher'); kf=v['birds'][ki]
    await closeup(pg,kf['x'],kf['y'],kf['z'],0.75,0.14,back=1.4,side=0.3,face=ki,up=0.08); await shot(pg,'kingfisher_with_fish.png')
    v=await until(pg,lambda v:v['events']['kfEat']>e1['kfEat'],15); kf=next(x for x in v['birds'] if x['kind']=='kingfisher')   # game time is clamped per frame: slow headless frames stretch the 2.8 s meal
    check('kingfisher: flies back to its twig, beats the fish and swallows it (eat event, fish gone)',v['events']['kfEat']>e1['kfEat'] and not kf['prey'] and kf['state']=='perch','state %s, fish %s'%(kf['state'],kf['prey']))
    v=await until(pg,lambda v:v['events']['grebeDive']>e1['grebeDive'] and v['events']['grebeUp']>e1['grebeUp'],40)
    check('little grebe: dives (tips forward, slips under) and pops up again',v['events']['grebeDive']>e1['grebeDive'] and v['events']['grebeUp']>e1['grebeUp'],
          'dives +%d, surfacings +%d'%(v['events']['grebeDive']-e1['grebeDive'],v['events']['grebeUp']-e1['grebeUp']))
    # egret flee -> wings spread (fold morph off), neck folded into an S, wing beats -> lands back with folded wings
    await pg.evaluate("window.__pond.v11Calm(false)")
    v=await until(pg,lambda v:any(x['kind']=='egret' and x['state'] in ('stand','forage') for x in v['birds']),30)
    i=next(i for i,x in enumerate(v['birds']) if x['kind']=='egret' and x['state'] in ('stand','forage')); e=v['birds'][i]
    a=math.atan2(e['z'],e['x']); await pg.evaluate("window.__pond.placeWater(%f,%f,0)"%(e['x']-math.cos(a)*2.4,e['z']-math.sin(a)*2.4))
    v=await until(pg,lambda v:v['birds'][i]['state']=='fly' and v['birds'][i]['fold']<0.2,4); e=v['birds'][i]
    ws=[]
    for _ in range(12):
        x=(await v11(pg))['birds'][i]; ws.append(x['wingBone'][1]-x['y']); await wait(pg,60)
    check('egret: flees - wings unfold (feather fold morph -> 0) and really beat (wing-tip bone swings up and down)',e['state']=='fly' and e['fold']<0.2 and max(ws)-min(ws)>0.15,
          'fold %.2f, wing tip height range %.2f m'%(e['fold'],max(ws)-min(ws)))
    s=await st(pg); x=(await v11(pg))['birds'][i]; dd=math.dist([x['x'],x['y'],x['z']],[s['x'],s['y'],s['z']])
    await pg.evaluate("window.__pond.camLook(0,0.6,0,%f,%f,%f,%d)"%(x['x']-s['x'],x['y']-s['y'],x['z']-s['z'],max(10,min(40,int(2*math.degrees(math.atan2(1.4,dd))))))); await wait(pg,120); await shot(pg,'egret_flight.png')   # telephoto on the bird
    await pg.evaluate("window.__pond.reset()")
    v=await until(pg,lambda v:v['birds'][i]['state'] in ('stand','forage') and v['birds'][i]['fold']>0.9,35)
    check('egret: circles back, glides in and lands in the reeds again with folded wings',v['birds'][i]['state'] in ('stand','forage') and v['birds'][i]['fold']>0.9,'state %s, fold %.2f'%(v['birds'][i]['state'],v['birds'][i]['fold']))
    # ---------------- night: night heron hunched, strike, eyeshine in the headlamp; turtle under the lamp
    await pg.evaluate("window.__pond.v11Calm(true);window.__pond.setTod('night',true)")
    i=await bird_closeup(pg,'heron','heron_night.png')
    check('night heron: arrives at night and stands hunched in the reeds',i is not None)
    if i is not None:
        # eyeshine: the frog sits on the start pad with the lamp on (a swimming frog's lamp points down into the water), the heron wades 5 m ahead
        await pg.evaluate("window.__pond.reset();window.__pond.setLamp(true)"); await wait(pg,900); s=await st(pg)
        hx,hz=s['x']+math.sin(s['yaw'])*5,s['z']+math.cos(s['yaw'])*5
        await pg.evaluate("window.__pond.birdHome(%d,%f,%f,%f)"%(i,hx,hz,s['yaw']+math.pi+0.35)); await wait(pg,1500)
        h=(await v11(pg))['birds'][i]
        check('night heron: its eyes shine red in the headlamp beam (eyeshine from the pupil)',h['shine']>0.5,'shine %.2f'%h['shine'])
        await pg.evaluate("window.__pond.camLook(%f,%f,%f,%f,%f,%f,16)"%(math.cos(s['yaw'])*0.9,0.55,-math.sin(s['yaw'])*0.9,hx-s['x'],h['y']+0.75-s['y'],hz-s['z'])); await wait(pg,500)   # beside the frog, telephoto
        await shot(pg,'heron_night_headlamp.png')
        h0=[h['head'][j]-[h['x'],h['y'],h['z']][j] for j in range(3)]
        await pg.evaluate("window.__pond.heronStrike(%d)"%i); await wait(pg,200); h=(await v11(pg))['birds'][i]
        h1=[h['head'][j]-[h['x'],h['y'],h['z']][j] for j in range(3)]
        check('night heron: ambush strike - the hunched neck shoots out',dist(h0,h1)>0.12,'head moved %.2f m'%dist(h0,h1))
    v=await v11(pg); t=next(t for t in v['turtles'] if t['y']<-1.7)
    await closeup(pg,t['x'],t['y'],t['z'],1.2,0.12,back=1.0,lamp=True); await shot(pg,'turtle_night_headlamp.png')
    # ---------------- rain: wet look, birds shelter; close-ups
    await pg.evaluate("window.__pond.setTod('day',true);window.__pond.setWeather('rain',true)")
    v=await until(pg,lambda v:v['wet']>0.6,15)
    check('rain: animals get the wet look (glossier shell / skin, darker feathers)',v['wet']>0.6,'wet %.2f'%v['wet'])
    await bird_closeup(pg,'egret','egret_rain.png',secs=40)
    v=await v11(pg); t=v['turtles'][bk[0]]
    if t['basker']=='pad': await closeup(pg,t['x'],t['y'],t['z'],1.3,0.1,back=1.5); await shot(pg,'turtle_rain.png')
    # ---------------- radar unaffected
    await pg.evaluate("window.__pond.setWeather('clear',true);window.__pond.mmLayer('radar')"); await wait(pg,1500)
    mm=(await pg.evaluate('window.__pond.v10()'))['minimap']; v=await v11(pg)
    tu=[x for x in mm['icons'] if x['kind']=='turtle']
    check('radar: still only large animals - every turtle (incl. the baskers) and the big birds, never fish',len(tu)==len(v['turtles']) and not any(x['kind']=='fish' for x in mm['icons']),'%d turtle icons for %d turtles'%(len(tu),len(v['turtles'])))
    check('desktop page: no console errors',not logs,str(logs[:3]))
    await pg.close()

async def compare(b):
    """same shots with the v10 procedural animals (?animals=v10) and the v11 models, side by side"""
    out=[]
    for q,tag in (('?animals=v10','v10'),('','v11')):
        pg,logs=await open_page(b,q=q); await pg.evaluate("window.__pond.v11Calm(true);window.__pond.setTod('day',true);window.__pond.setWeather('clear',true)"); await wait(pg,2500)
        v=await pg.evaluate('window.__pond.v9()'); T=v['turtles']   # the most isolated floor crawler (no other turtle in the frame)
        iso=lambda t:min(math.hypot(t['x']-o['x'],t['z']-o['z']) for o in T if o is not t)
        t=max([t for t in T if t['y']<-1.7],key=iso)
        await closeup(pg,t['x'],t['y'],t['z'],1.3,0.1,back=1.2); await shot(pg,'_cmp_turtle_%s.png'%tag)
        for kd in ('egret','kingfisher'):
            await bird_closeup(pg,kd,'_cmp_%s_%s.png'%(kd,tag))
        out.append(logs); await pg.close()
    for kd in ('turtle','egret','kingfisher'):
        A=Image.open(os.path.join(SHOT,'_cmp_%s_v10.png'%kd));B=Image.open(os.path.join(SHOT,'_cmp_%s_v11.png'%kd))
        W=Image.new('RGB',(A.width+B.width,A.height));W.paste(A,(0,0));W.paste(B,(A.width,0));d=ImageDraw.Draw(W)
        for x,txt in ((20,'v10'),(A.width+20,'v11')): d.rectangle([x-8,14,x+60,50],fill=(0,0,0)); d.text((x,22),txt,fill=(255,255,255))
        W.save(os.path.join(SHOT,'compare_v10_v11_%s.png'%kd))
        for f in ('_cmp_%s_v10.png'%kd,'_cmp_%s_v11.png'%kd): os.remove(os.path.join(SHOT,f))
    check('comparison: v10 and v11 close-ups rendered side by side (compare_v10_v11_*.png)',all(os.path.exists(os.path.join(SHOT,'compare_v10_v11_%s.png'%k)) for k in ('turtle','egret','kingfisher')))
    check('comparison pages: no console errors (v10 fallback still works)',not any(out),str([l[:2] for l in out]))

async def phone(b):
    ctx=await b.new_context(viewport={'width':390,'height':844},device_scale_factor=2,is_mobile=True,has_touch=True)
    pg=await ctx.new_page(); logs=[]; watch(pg,logs)
    await pg.goto(URL); await pg.wait_for_function('window.__ready===true',timeout=180000); await wait(pg,1500)
    await pg.evaluate("window.__pond.setHint(false)"); v=await v11(pg)
    check('phone: all models load; LOD switches closer (turtle %.1f m) and fewer animals'%v['lodDist']['turtle'],all(v['loaded'].values()) and v['lodDist']['turtle']<4 and len(v['turtles'])<=8,
          '%d turtles, %d birds, LOD0/LOD1 turtles %s'%(len(v['turtles']),len(v['birds']),v['lod']['turtle']))
    t=next(t for t in v['turtles'] if t['basker']); await pg.evaluate("window.__pond.v11Calm(true);window.__pond.setTod('day',true)"); await wait(pg,2600)
    await closeup(pg,t['x'],t['y'],t['z'],1.4,0.1,back=1.4,fov=55); await shot(pg,'phone_390x844_turtle.png')
    i=await bird_closeup(pg,'egret',None)
    if i is not None: await shot(pg,'phone_390x844_egret.png')
    fr=await pg.evaluate("new Promise(r=>{let n=0;const t0=performance.now();const f=()=>{n++;if(performance.now()-t0<2000)requestAnimationFrame(f);else r(n/2)};requestAnimationFrame(f)})")
    check('phone 390x844: runs with the new animals, no console errors',not logs,'%.0f fps headless; %s'%(fr,str(logs[:2])))
    await ctx.close()

async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(channel='chrome')
        await desktop(b); await compare(b); await phone(b); await b.close()
    txt='\n'.join(R)+'\n\n%d / %d passed\n'%(sum(r.startswith('PASS') for r in R),len(R))
    open(os.path.join(ROOT,'test_v11_report.txt'),'w',encoding='utf-8').write(txt); print('RESULT',ok_all)
asyncio.run(main())
