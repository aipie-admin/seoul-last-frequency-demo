"""2nd-floor office interior, true orthographic side view.
서초 하천관리센터 양재1동 2층 (bible names the org, not the floor/address).
"""
import json, math, random
import numpy as np
from PIL import Image
from lib import Cv, hx, mul, lerp, outline

OUT='/workspace/seoul_survival/webgl/public/px/'
C=lambda s:hx(s)
OW,OH=1280,560
FEET=400
CURB=10
GINKGO=[C('#6a4a08'),C('#a87a10'),C('#d8a818'),C('#f4cc3a')]
MAPLE=[C('#4a1008'),C('#8a1e10'),C('#c0361c'),C('#e2602a')]
BROWN=[C('#2a1c12'),C('#4a3220'),C('#6e4c2e'),C('#8e6a40')]
LEAFS=[GINKGO[2],GINKGO[3],GINKGO[1],MAPLE[2],MAPLE[1],BROWN[2]]
R=random.Random(202611)
rng=np.random.default_rng(202611)
LIGHTS=[]; SOLIDS=[]; ITEMS=[]

def dusk_view(cv,x0,y0,x1,y1):
    """Autumn dusk 양재동 through the window, flat profile."""
    h=y1-y0; w=x1-x0
    # sky: deep violet to rust
    cv.dgrad(x0,y0,x1,y0+int(h*0.45),C('#0a0c1c'),C('#3a2448'),True,steps=6,hg=-8)
    cv.dgrad(x0,y0+int(h*0.45),x1,y1,C('#3a2448'),C('#c86a3a'),True,steps=6,hg=-8)
    # far buildings
    base=y1-6
    x=x0-4
    while x<x1:
        bw=R.randint(10,18); bh=R.randint(18,min(h-10,42))
        cv.rect(x,base-bh,x+bw,base,C('#121524'),-9)
        for wy in range(base-bh+3,base-3,5):
            for wx in range(x+2,x+bw-2,4):
                if R.random()<0.2: cv.px(wx,wy,C('#c8a070'),-9,emi=C('#6a5030'))
        x+=bw+R.randint(1,4)
    # ginkgo silhouettes
    for tx in range(x0+8,x1-6,22):
        th=R.randint(10,18)
        cv.rect(tx,base-th,tx+1,base,C('#2a2010'),-8)
        for k in range(7):
            cv.px(tx+R.randint(-5,5),base-th+R.randint(-2,4),R.choice(LEAFS),-8)
    # ledge
    cv.rect(x0,y1-3,x1,y1,C('#2a2c32'),-7)

def blinds(cv,x0,y0,x1,y1,openness=0.55):
    """Venetian blinds pulled mid-way so dusk 양재동 remains visible."""
    cut=y0+int((y1-y0)*0.42)
    # gathered slats in the upper third
    gap=3
    for y in range(y0,cut,gap):
        sl=C('#c8c0b0') if (y//gap)%2==0 else C('#b0a898')
        cv.rect(x0,y,x1,y+2,sl,-1)
    cv.rect(x0,cut,x1,cut+2,C('#8a8274'),-1)
    # cords
    cv.rect(x0+2,cut,x0+3,y1,C('#6a6458'),-1)
    cv.rect(x1-3,cut,x1-2,y1,C('#6a6458'),-1)

def desk(cv,x,floor,w=78,lit=True,news=False):
    """Office desk in profile. Returns solid box."""
    top=floor-28
    body=C('#5a4a38'); dark=C('#3a2e24')
    cv.rect(x,top,x+w,floor,body,3)
    cv.rect(x,top,x+w,top+3,C('#6e5a44'),3.5)
    cv.rect(x+2,top+8,x+w-2,floor,dark,2)
    # legs
    cv.rect(x+2,top,x+5,floor,C('#4a3c2e'),3)
    cv.rect(x+w-5,top,x+w-2,floor,C('#4a3c2e'),3)
    # monitor
    mx=x+w//2-14; my=top-26
    cv.rect(mx,my,mx+28,top-4,C('#1a1c20'),4)
    cv.rect(mx+1,my+1,mx+27,top-6,C('#8ab0d8') if (lit and not news) else (C('#f4f0e0') if news else C('#0c1018')),3,
            emi=(C('#6a88b0') if (lit and not news) else (C('#d8d0b0') if news else None)))
    if news:
        cv.rect(mx+2,my+3,mx+26,my+8,C('#c41a1a'),3,emi=C('#a01818'))
        cv.rect(mx+3,my+10,mx+18,my+12,C('#2a2a2a'),3)
    cv.rect(mx+12,top-6,mx+16,top,C('#2a2c30'),3)
    # papers / mug
    cv.rect(x+6,top-2,x+22,top,C('#e8e0c8'),3.5)
    cv.rect(x+w-16,top-5,x+w-11,top,C('#8a2a22'),3.5)
    return dict(x0=x,y0=top,x1=x+w,y1=floor)

def cabinet(cv,x,floor,w=28,h=56):
    top=floor-h
    cv.rect(x,top,x+w,floor,C('#4a5248'),3)
    cv.rect(x,top,x+w,top+2,C('#6a7268'),3.5)
    for yy in range(top+6,floor-4,12):
        cv.rect(x+2,yy,x+w-2,yy+10,C('#3a4238'),2.5)
        cv.rect(x+w-8,yy+4,x+w-5,yy+6,C('#c8c090'),3.5)
    return dict(x0=x,y0=top,x1=x+w,y1=floor)

def cooler(cv,x,floor):
    top=floor-44
    cv.rect(x,top+14,x+16,floor,C('#d8dce0'),3)
    cv.ellipse(x+8,top+10,8,10,C('#a8d4f0'),3.5,emi=C('#4a88b0'))
    cv.rect(x+6,top+22,x+10,top+26,C('#3a3d44'),3)
    cv.rect(x+2,floor-8,x+14,floor,C('#b0b4b8'),3)
    return dict(x0=x,y0=top+14,x1=x+16,y1=floor)

def door(cv,x,floor,w=36):
    top=floor-78
    cv.rect(x-3,top-4,x+w+3,floor,C('#3a3d44'),3)
    cv.rect(x,top,x+w,floor,C('#6a5a48'),3)
    cv.rect(x+4,top+6,x+w-4,top+36,C('#1a1c22'),1)  # narrow glass
    # infected silhouette will be a sprite; dark hall beyond
    cv.dgrad(x+4,top+6,x+w-4,top+36,C('#12141a'),C('#07080c'),True,steps=3,hg=-2)
    cv.rect(x+w-8,floor-42,x+w-5,floor-38,C('#c8a04a'),4)
    cv.rect(x-3,top-4,x+w+3,top,C('#4a4e56'),3.5)
    return dict(x0=x-2,y0=top,x1=x+w+2,y1=floor)

def stairs(cv,x,floor):
    """Stairwell down, in profile — steps descending to the right."""
    cv.rect(x,138,x+2,floor,C('#3a3d44'),2)
    cv.dgrad(x,138,x+90,floor,C('#101218'),C('#07080a'),True,steps=4,hg=-6)
    # steps
    for i in range(8):
        sy=floor-i*8; sx=x+6+i*8
        cv.rect(sx,sy-8,x+90,sy,C('#3a3c42'),1)
        cv.rect(sx,sy-8,sx+8,sy-7,C('#6a6c72'),2)
    cv.rect(x+2,138,x+90,142,C('#2a2c32'),2)
    # sign
    cv.rect(x+8,150,x+44,164,C('#1a1c22'),3)
    cv.text(x+10,152,'1층 ↓',C('#eaeaea'),'Galmuri9',10,hg=3.2)
    return dict(x0=x,y0=138,x1=x+8,y1=floor)  # only the left wall is solid

def build():
    cv=Cv(OW,OH)
    # void above ceiling / below slab
    cv.rect(0,0,OW,118,C('#07080a'),-20)
    cv.rect(0,FEET+CURB,OW,OH,C('#07080a'),-20)
    # ceiling slab (2nd floor)
    cv.rect(0,118,OW,138,C('#5a564e'),2)
    cv.rect(0,136,OW,138,C('#3a3832'),1)
    # fluorescent fixtures
    for fx in (90,260,430,620,860,1080):
        cv.rect(fx,138,fx+70,144,C('#d8dce0'),4,emi=C('#c8d0d8'))
        cv.rect(fx+2,144,fx+68,146,C('#f0f4f0'),4,emi=C('#e8eee8'))
        LIGHTS.append(dict(x=fx+35,y=146,c=[0.92,0.95,0.88],r=160,i=0.85,cone=1,flick=0.18 if fx in (620,860) else 0.05))
    # back wall
    cv.rect(0,138,OW,FEET,C('#8a8478'),0)
    for y in range(138,FEET,6):
        cv.rect(0,y,OW,y+1,mul(C('#8a8478'),0.94),0)
    # dado
    cv.rect(0,FEET-36,OW,FEET,C('#5a5e56'),0.6)
    cv.rect(0,FEET-36,OW,FEET-35,C('#3a3e36'),1)
    # left wall
    cv.rect(0,118,18,FEET+CURB,C('#6a665c'),2)
    # windows — 2nd floor looking out at 양재동 dusk
    wins=[(70,168,170,310),(200,168,300,310),(430,168,540,310),(560,168,660,310)]
    for x0,y0,x1,y1 in wins:
        cv.rect(x0-3,y0-3,x1+3,y1+3,C('#3a3d44'),2)
        dusk_view(cv,x0,y0,x1,y1)
        blinds(cv,x0,y0,x1,y1,0.5 if x0<400 else 0.25)
        cv.rect(x0-3,y1+3,x1+3,y1+6,C('#6a6e66'),2.5)
        # warm interior spill on the sill
        LIGHTS.append(dict(x=(x0+x1)//2,y=y1-4,c=[1.0,0.7,0.4],r=70,i=0.35,cone=0,flick=0))
    # wall clock
    cv.ellipse(340,200,11,11,C('#e8e0d0'),3)
    cv.ellipse(340,200,9,9,C('#f4f0e8'),3)
    cv.rect(340,192,341,200,C('#1a1a1a'),3.5)
    cv.rect(340,200,347,201,C('#1a1a1a'),3.5)
    # org sign + duty board
    cv.rect(312,220,428,248,C('#1a1c22'),3)
    cv.text(318,224,'서초 하천관리센터',C('#eaeaea'),'Galmuri9',10,hg=3.2)
    cv.text(318,236,'배수·수문 당직   2층',C('#c8c8c8'),'Galmuri7',8,hg=3.2)
    cv.rect(312,252,428,292,C('#e8e0c8'),2)
    cv.text(318,256,'당직일지  11월',C('#2a2a2a'),'Galmuri7',8,hg=2.2)
    cv.text(318,268,'야간 이상 없음',C('#4a4a4a'),'Galmuri7',8,hg=2.2)
    cv.text(318,278,'양재천 수문 닫힘',C('#4a4a4a'),'Galmuri7',8,hg=2.2)
    # safety poster (foreshadows news guidelines)
    cv.rect(680,200,744,268,C('#f4f0e0'),2)
    cv.rect(680,200,744,212,C('#c41a1a'),2)
    cv.text(686,202,'대처요령',C('#f4f0e0'),'Galmuri9',10,hg=2.5)
    cv.text(684,216,'물리면 씻고',C('#1a1a1a'),'Galmuri7',8,hg=2)
    cv.text(684,226,'문을 잠글 것',C('#1a1a1a'),'Galmuri7',8,hg=2)
    cv.text(684,236,'소리 주의',C('#1a1a1a'),'Galmuri7',8,hg=2)
    cv.text(684,246,'물은 피함',C('#1a1a1a'),'Galmuri7',8,hg=2)
    # furniture
    SOLIDS.append(cabinet(cv,24,FEET,28,70))
    SOLIDS.append(cabinet(cv,52,FEET,26,52))
    SOLIDS.append(cooler(cv,92,FEET))
    ITEMS.append(dict(k='water',x=100,y=FEET))
    # 지석's desk (start) — news monitor
    SOLIDS.append(desk(cv,220,FEET,86,lit=True,news=True))
    LIGHTS.append(dict(x=263,y=FEET-48,c=[0.95,0.92,0.8],r=90,i=1.1,cone=0,flick=0.08))
    # thermos / papers already on desk; a fallen chair (jump cue) at 520
    SOLIDS.append(desk(cv,360,FEET,74,lit=True,news=False))
    # low toppled cabinet / box — jump tutorial
    cv.rect(510,FEET-18,558,FEET,C('#4a463e'),3)
    cv.rect(510,FEET-18,558,FEET-16,C('#6a665c'),3.5)
    cv.rect(518,FEET-26,548,FEET-18,C('#5a4a38'),3)
    SOLIDS.append(dict(x0=510,y0=FEET-18,x1=558,y1=FEET))
    SOLIDS.append(desk(cv,580,FEET,70,lit=False,news=False))
    # reception half-wall before the door
    cv.rect(700,FEET-22,768,FEET,C('#6a6e66'),2)
    cv.rect(700,FEET-22,768,FEET-20,C('#8a8e86'),2.5)
    SOLIDS.append(dict(x0=700,y0=FEET-22,x1=768,y1=FEET))
    # door + infected stands in front (sprite, not painted)
    door(cv,820,FEET,36)
    # hall plaque
    cv.rect(800,FEET-92,856,FEET-80,C('#1a1c22'),3)
    cv.text(806,FEET-90,'당직실',C('#eaeaea'),'Galmuri7',8,hg=3)
    # stairwell
    SOLIDS.append(stairs(cv,980,FEET))
    # floor strip (true side view)
    for xx in range(0,OW):
        f=0.9+0.12*((xx*7)%5)/5
        cv.px(xx,FEET,mul(C('#9a8e7a'),f),1.8)
        cv.rect(xx,FEET,xx+1,FEET+5,mul(C('#7a6e5a'),f),1.0)
        cv.rect(xx,FEET+5,xx+1,FEET+CURB,C('#3a342c'),0.3)
        if R.random()<0.03: cv.px(xx,FEET+1,R.choice(LEAFS) if R.random()<0.3 else C('#5a4e3c'),1.4)
    cv.rect(0,FEET+5,OW,FEET+6,C('#aea290'),2)
    cv.rect(0,FEET+CURB-1,OW,FEET+CURB,C('#2a241c'),0)
    # slab edge — hint that this is a 2nd floor
    cv.rect(0,FEET+CURB,OW,FEET+CURB+8,C('#4a463e'),-1)
    cv.rect(0,FEET+CURB+8,OW,FEET+CURB+10,C('#2a2822'),-1)
    # a couple of dropped leaves that blew in near the window
    for lx,ly in ((180,FEET-1),(470,FEET-1),(640,FEET-1)):
        cv.px(lx,ly,R.choice(LEAFS),2); cv.px(lx+1,ly,R.choice(LEAFS),2)
    # wall outlet / fire extinguisher
    cv.rect(760,FEET-40,768,FEET-18,C('#c41a1a'),3)
    cv.rect(762,FEET-42,766,FEET-40,C('#2a2a2a'),3)

    files=cv.save(OUT+'L_office',strength=1.0,chunk=2048)
    Image.fromarray(cv.c,'RGBA').save('/tmp/L_office.png')
    meta=dict(
        world=dict(w=OW,h=OH,feet=FEET,low=FEET,slope0=99999,slope1=99999,water=99999,goal=99999,xmax=1260,ct0=108,name='office'),
        layers=[dict(name='office',p=1.0,w=OW,h=OH,chunks=files)],
        lights=LIGHTS,
        solids=SOLIDS,
        items=ITEMS,
        enemies=[['inf_a', 800]],
        exits=[dict(x=820,w=40,k='door'), dict(x=1040,w=80,k='stairs')],
        start=dict(x=250,face=1),
        notes=dict(
            location='서초 하천관리센터 2층, 양재1동',
            canon='바이블은 소속(서초 하천관리센터)만 명시. 층·번지는 미기재라 양재1동 2층으로 가정.',
        ),
    )
    json.dump(meta, open(OUT+'office.json','w'), ensure_ascii=False, indent=2)
    print('office', OW, 'lights', len(LIGHTS), 'solids', len(SOLIDS))

if __name__=='__main__':
    build()
