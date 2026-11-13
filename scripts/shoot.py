import asyncio, sys
from playwright.async_api import async_playwright
URL=sys.argv[1] if len(sys.argv)>1 else 'http://localhost:4791/'
OUT='/workspace/seoul_survival/webgl/shots/'
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(args=['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--ignore-gpu-blocklist','--autoplay-policy=no-user-gesture-required'])
        pg=await b.new_page(viewport={'width':1280,'height':720})
        errs=[]
        pg.on('console',lambda m: errs.append(f'{m.type}: {m.text}') if m.type in ('error','warning') else None)
        pg.on('pageerror',lambda e: errs.append(f'pageerror: {e}'))
        await pg.goto(URL); 
        await pg.wait_for_selector('#loading.hidden',state='attached',timeout=60000)
        await pg.wait_for_timeout(2500)
        await pg.screenshot(path=OUT+'01_title.png')
        await pg.click('#btnStart'); await pg.wait_for_timeout(800)
        await pg.keyboard.down('KeyD'); await pg.wait_for_timeout(2600); await pg.keyboard.up('KeyD')
        await pg.screenshot(path=OUT+'02_street.png')
        # teleport for coverage shots
        await pg.evaluate("()=>{const g=window.__game; g.p.x=1060; g.god=true; }"); await pg.wait_for_timeout(1500)
        await pg.screenshot(path=OUT+'03_infected.png')
        await pg.evaluate("()=>{const g=window.__game; g.p.x=2480; }"); await pg.wait_for_timeout(2600)
        await pg.screenshot(path=OUT+'04_rain.png')
        await pg.evaluate("()=>{const g=window.__game; g.rain.on=false; g.rain.next=999; g.p.x=3300; g.enemies.forEach(e=>{if(e.x<3000)e.x=200});}"); await pg.wait_for_timeout(2400)
        await pg.screenshot(path=OUT+'05_station.png')
        await pg.evaluate("()=>{const g=window.__game; g.p.x=5560; g.p.blood=100; g.p.bleed=0; g.god=true; }")
        await pg.keyboard.down('KeyD'); await pg.wait_for_timeout(1800); await pg.keyboard.up('KeyD')
        await pg.screenshot(path=OUT+'06_stream.png')
        await pg.evaluate("()=>{window.__game.p.x=5790;}")
        await pg.keyboard.down('KeyD'); await pg.wait_for_timeout(3000); await pg.keyboard.up('KeyD')
        await pg.wait_for_timeout(1800)
        await pg.screenshot(path=OUT+'07_win.png')
        fps=await pg.evaluate("()=>new Promise(r=>{let n=0;const t0=performance.now();function f(){n++; if(performance.now()-t0<2000) requestAnimationFrame(f); else r(n/2);} requestAnimationFrame(f);})")
        print('fps(swiftshader)',fps)
        print('ERRORS:' if errs else 'NO CONSOLE ERRORS'); [print(' ',e) for e in errs[:30]]
        await b.close()
asyncio.run(main())
