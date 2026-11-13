import asyncio, sys, os
from playwright.async_api import async_playwright
from PIL import Image
URL=sys.argv[1] if len(sys.argv)>1 else 'http://localhost:4791/'
OUT='/workspace/seoul_survival/webgl/shots/'
os.makedirs(OUT, exist_ok=True)

async def to_webp(path_png):
    im=Image.open(path_png).convert('RGB')
    webp=path_png.rsplit('.',1)[0]+'.webp'
    im.save(webp,'WEBP',quality=90,method=4)
    os.remove(path_png)
    return webp

async def shot(pg, name, wait=400):
    await pg.wait_for_timeout(wait)
    png=OUT+name+'.png'
    await pg.screenshot(path=png)
    return await to_webp(png)

async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--ignore-gpu-blocklist','--autoplay-policy=no-user-gesture-required','--no-sandbox'])
        pg=await b.new_page(viewport={'width':1280,'height':720})
        errs=[]
        pg.on('console',lambda m: errs.append(f'{m.type}: {m.text}') if m.type in ('error','warning') else None)
        pg.on('pageerror',lambda e: errs.append(f'pageerror: {e}'))
        await pg.goto(URL)
        await pg.wait_for_selector('#loading.hidden',state='attached',timeout=90000)
        await pg.wait_for_timeout(2500)
        await shot(pg,'01_title',800)

        await pg.click('#btnStart')
        # flicker then news
        await pg.wait_for_function("()=>!document.querySelector('#news').classList.contains('hidden')", timeout=8000)
        await shot(pg,'10_news',700)

        await pg.evaluate("()=>window.__skipNews&&window.__skipNews()")
        await pg.wait_for_function("()=>document.querySelector('#news').classList.contains('hidden')", timeout=5000)
        await pg.wait_for_timeout(600)
        # office interior, turn on torch for visibility
        await pg.evaluate("()=>{const g=window.__game; g.p.torch=true;}")
        await shot(pg,'09_office',900)

        # control prompt (move / flashlight already done; show A/D or jump area)
        await pg.evaluate("()=>{const g=window.__game; g.p.x=250; g.p.torch=true; g.tut.torch=true; g.tut.move=false;}")
        await shot(pg,'11_controls',800)

        # door infected
        await pg.evaluate("()=>{const g=window.__game; g.p.x=700; g.p.face=1; g.p.torch=true; g.p.water=2; g.tut.torch=true; g.tut.move=true; g.god=true; const e=g.enemies[0]; if(e){e.x=800;e.y=g.w.feet;e.state='idle';e.face=-1;}}")
        await pg.wait_for_timeout(1000)
        await shot(pg,'12_door',800)

        # U26: splash → flee, then wall headSmash
        await pg.evaluate("()=>{const g=window.__game; g.p.x=700; g.p.y=g.w.feet; g.p.face=1; g.p.water=Math.max(2,g.p.water); g.p.act=null; g.p.actT=0; g.god=true; const e=g.enemies[0]; if(e){e.x=800;e.y=g.w.feet;e.state='idle';e.st=0;e.face=-1;} g.splash();}")
        await pg.wait_for_timeout(450)
        await shot(pg,'14_flee',200)
        await pg.wait_for_function("()=>{const e=window.__game.enemies[0]; return e && (e.state==='bang'||e.state==='down');}", timeout=6000)
        await pg.wait_for_timeout(80)
        await shot(pg,'15_wall_death',250)

        # go to street (side-view after)
        await pg.evaluate("()=>{window.__toStreet();}")
        await pg.wait_for_timeout(1400)
        await pg.evaluate("()=>{const g=window.__game; g.p.x=220; g.p.torch=true; g.p.battery=100; g.god=true;}")
        await pg.keyboard.down('KeyD'); await pg.wait_for_timeout(1800); await pg.keyboard.up('KeyD')
        await shot(pg,'02_street',800)

        # U27: running beam follows phone/arm
        await pg.evaluate("()=>{const g=window.__game; g.p.x=380; g.p.face=1; g.p.torch=true; g.p.battery=100; g.god=true; g.p.stamina=100;}")
        await pg.keyboard.down('ShiftLeft')
        await pg.keyboard.down('KeyD')
        await pg.wait_for_timeout(900)
        await shot(pg,'16_beam_run',150)
        await pg.keyboard.up('KeyD')
        await pg.keyboard.up('ShiftLeft')

        # leaves (stay on street, look at trees)
        await pg.evaluate("()=>{const g=window.__game; g.p.x=900; g.god=true;}")
        await pg.wait_for_timeout(2000)
        await shot(pg,'13_leaves',800)

        await pg.evaluate("()=>{const g=window.__game; g.p.x=1060; g.god=true; }"); await pg.wait_for_timeout(1500)
        await shot(pg,'03_infected',600)

        await pg.evaluate("()=>{const g=window.__game; g.p.x=2480; }"); await pg.wait_for_timeout(2600)
        await shot(pg,'04_rain',600)

        await pg.evaluate("()=>{const g=window.__game; g.rain.on=false; g.rain.next=999; g.p.x=3300; g.enemies.forEach(e=>{if(e.x<3000)e.x=200});}"); await pg.wait_for_timeout(2400)
        await shot(pg,'05_station',600)

        await pg.evaluate("()=>{const g=window.__game; g.p.x=5560; g.p.blood=100; g.p.bleed=0; g.god=true; }")
        await pg.keyboard.down('KeyD'); await pg.wait_for_timeout(1800); await pg.keyboard.up('KeyD')
        await shot(pg,'06_stream',600)

        await pg.evaluate("()=>{window.__game.p.x=5790;}")
        await pg.keyboard.down('KeyD'); await pg.wait_for_timeout(3000); await pg.keyboard.up('KeyD')
        await pg.wait_for_timeout(1800)
        await shot(pg,'07_win',600)

        fps=await pg.evaluate("()=>new Promise(r=>{let n=0;const t0=performance.now();function f(){n++; if(performance.now()-t0<2000) requestAnimationFrame(f); else r(n/2);} requestAnimationFrame(f);})")
        print('fps(swiftshader)',fps)
        print('ERRORS:' if errs else 'NO CONSOLE ERRORS');
        [print(' ',e) for e in errs[:40]]
        await b.close()
asyncio.run(main())
