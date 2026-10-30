# v11b: back close-ups of the vest badge (启格科普 seal) - day + night headlamp, frog standing on its lily pad
# usage: python src/shots_v11b.py [url] [screens dir] [back distance] [cam height] [target height]
import asyncio,os,sys,math
from playwright.async_api import async_playwright
URL=sys.argv[1] if len(sys.argv)>1 else 'http://127.0.0.1:18977/qingyue-pond.html'
SHOT=sys.argv[2] if len(sys.argv)>2 else os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','screens-v11b')
D=float(sys.argv[3]) if len(sys.argv)>3 else 1.0; H=float(sys.argv[4]) if len(sys.argv)>4 else 0.5; T=float(sys.argv[5]) if len(sys.argv)>5 else 0.35
os.makedirs(SHOT,exist_ok=True)
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(channel='chrome')
        pg=await b.new_page(viewport={'width':1280,'height':800})
        await pg.goto(URL); await pg.wait_for_function('window.__ready===true',timeout=180000); await pg.wait_for_timeout(1500)
        await pg.evaluate("document.body.classList.add('nopanel');window.__pond.setHint(false)")
        for tod,lamp,name in (('day',False,'back_badge_day.png'),('night',True,'back_badge_night_headlamp.png')):
            await pg.evaluate("window.__pond.setTod('%s');window.__pond.setLamp(%s)"%(tod,'true' if lamp else 'false')); await pg.wait_for_timeout(800)
            s=await pg.evaluate('window.__pond.state()'); y=s['yaw']
            await pg.evaluate("window.__pond.camLook(%f,%f,%f,0,%f,0,35)"%(-math.sin(y)*D,H,-math.cos(y)*D,T)); await pg.wait_for_timeout(900)
            await pg.evaluate("for(const s of ['#hud','#toast','#mm','#mmShow','#hint'])document.querySelectorAll(s).forEach(e=>e.style.visibility='hidden')")
            await pg.screenshot(path=os.path.join(SHOT,name)); print('shot',name,s['where'],round(y,2),flush=True)
        # showcase page (qingyue-3d.html) uses the same qingyue.glb: back view, frog faces +z there
        pg=await b.new_page(viewport={'width':1280,'height':800})
        await pg.goto(URL.replace('qingyue-pond.html','qingyue-3d.html')); await pg.wait_for_function('window.__ready===true',timeout=180000); await pg.wait_for_timeout(1500)
        await pg.evaluate("const a=window.__api;a.cam.position.set(0,0.75,-2.2);a.controls.target.set(0,0.45,0);a.controls.update();document.querySelectorAll('#hint').forEach(e=>e.style.visibility='hidden')"); await pg.wait_for_timeout(900)
        await pg.screenshot(path=os.path.join(SHOT,'back_badge_viewer.png')); print('shot back_badge_viewer.png',flush=True)
        await b.close()
asyncio.run(main())
