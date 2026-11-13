"""2nd-floor video-production office, true orthographic side view.
최성재의 소규모 영상 제작사 '볼더스튜디오' — 양재1동 2층 (사용자 지정 상호 Boulder Studio).
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
CO='볼더스튜디오'
GINKGO=[C('#6a4a08'),C('#a87a10'),C('#d8a818'),C('#f4cc3a')]
MAPLE=[C('#4a1008'),C('#8a1e10'),C('#c0361c'),C('#e2602a')]
BROWN=[C('#2a1c12'),C('#4a3220'),C('#6e4c2e'),C('#8e6a40')]
LEAFS=[GINKGO[2],GINKGO[3],GINKGO[1],MAPLE[2],MAPLE[1],BROWN[2]]
R=random.Random(202611)
rng=np.random.default_rng(202611)
LIGHTS=[]; SOLIDS=[]; ITEMS=[]

def dusk_view(cv,x0,y0,x1,y1):
    h=y1-y0; w=x1-x0
    cv.dgrad(x0,y0,x1,y0+int(h*0.45),C('#0a0c1c'),C('#3a2448'),True,steps=6,hg=-8)
    cv.dgrad(x0,y0+int(h*0.45),x1,y1,C('#3a2448'),C('#c86a3a'),True,steps=6,hg=-8)
    base=y1-6
    x=x0-4
    while x<x1:
        bw=R.randint(10,18); bh=R.randint(18,min(h-10,42))
        cv.rect(x,base-bh,x+bw,base,C('#121524'),-9)
        for wy in range(base-bh+3,base-3,5):
            for wx in range(x+2,x+bw-2,4):
                if R.random()<0.2: cv.px(wx,wy,C('#c8a070'),-9,emi=C('#6a5030'))
        x+=bw+R.randint(1,4)
    for tx in range(x0+8,x1-6,22):
        th=R.randint(10,18)
        cv.rect(tx,base-th,tx+1,base,C('#2a2010'),-8)
        for k in range(7):
            cv.px(tx+R.randint(-5,5),base-th+R.randint(-2,4),R.choice(LEAFS),-8)
    cv.rect(x0,y1-3,x1,y1,C('#2a2c32'),-7)

def blinds(cv,x0,y0,x1,y1,openness=0.55):
    cut=y0+int((y1-y0)*0.42)
    gap=3
    for y in range(y0,cut,gap):
        sl=C('#c8c0b0') if (y//gap)%2==0 else C('#b0a898')
        cv.rect(x0,y,x1,y+2,sl,-1)
    cv.rect(x0,cut,x1,cut+2,C('#8a8274'),-1)
    cv.rect(x0+2,cut,x0+3,y1,C('#6a6458'),-1)
    cv.rect(x1-3,cut,x1-2,y1,C('#6a6458'),-1)

def edit_desk(cv,x,floor,w=90,lit=True,news=False,dual=True):
    """Editing workstation in profile: desk, timeline monitor(s), news can play on one."""
    top=floor-26
    body=C('#2a2c30'); dark=C('#18191c')
    cv.rect(x,top,x+w,floor,body,3)
    cv.rect(x,top,x+w,top+3,C('#3a3e44'),3.5)
    cv.rect(x+2,top+8,x+w-2,floor,dark,2)
    cv.rect(x+2,top,x+5,floor,C('#222428'),3)
    cv.rect(x+w-5,top,x+w-2,floor,C('#222428'),3)
    # dual (or single) monitors
    mw=30 if dual else 36
    mx=x+8
    my=top-28
    def mon(mx,my,mw,news=False,lit=True):
        cv.rect(mx,my,mx+mw,top-3,C('#14161a'),4)
        if news:
            cv.rect(mx+1,my+1,mx+mw-1,top-5,C('#f0ece0'),3,emi=C('#d8d0b0'))
            cv.rect(mx+2,my+3,mx+mw-2,my+9,C('#c41a1a'),3,emi=C('#a01818'))
            cv.rect(mx+3,my+11,mx+mw-8,my+13,C('#2a2a2a'),3)
            cv.rect(mx+3,my+16,mx+mw-4,my+18,C('#3a3a3a'),3)
        elif lit:
            # timeline UI: dark editor + colored clips
            cv.rect(mx+1,my+1,mx+mw-1,top-5,C('#1a2230'),3,emi=C('#3a5878'))
            cv.rect(mx+2,my+3,mx+mw-2,my+14,C('#0c121c'),3,emi=C('#1a2838'))  # viewer
            ty=top-12
            cv.rect(mx+2,ty,mx+mw-2,top-6,C('#12161c'),3)
            for k,col in enumerate((C('#4a9ad8'),C('#d8a03a'),C('#3a8a5a'),C('#c05050'))):
                cv.rect(mx+3+k*6,ty+1,mx+7+k*6,ty+4,col,3,emi=mul(col,0.7))
        else:
            cv.rect(mx+1,my+1,mx+mw-1,top-5,C('#0c0e12'),3)
        cv.rect(mx+mw//2-2,top-5,mx+mw//2+2,top,C('#2a2c30'),3)
    mon(mx,my,mw,news=news,lit=lit)
    if dual:
        mon(mx+mw+6,my,mw,news=False,lit=lit)
    # keyboard / stream deck / mug
    cv.rect(x+10,top-2,x+34,top,C('#1a1c20'),3.5)
    cv.rect(x+w-18,top-5,x+w-12,top,C('#8a2a22'),3.5)
    # SSD / HDD brick on desk
    cv.rect(x+w-30,top-6,x+w-20,top,C('#3a3c42'),3.5)
    cv.px(x+w-22,top-5,C('#4af626') if lit else C('#2a4a2a'),4,emi=C('#2a9a18') if lit else None)
    return dict(x0=x,y0=top,x1=x+w,y1=floor)

def rack(cv,x,floor,w=26,h=62):
    """Equipment / HDD rack."""
    top=floor-h
    cv.rect(x,top,x+w,floor,C('#2a2c30'),3)
    cv.rect(x,top,x+w,top+2,C('#4a4e56'),3.5)
    for i,yy in enumerate(range(top+5,floor-4,9)):
        cv.rect(x+2,yy,x+w-2,yy+7,C('#1a1c20'),2.5)
        # drive LEDs
        cv.px(x+w-5,yy+3,C('#4af626') if i%2==0 else C('#c41a1a'),3.5,emi=C('#2a9a18') if i%2==0 else C('#801010'))
    return dict(x0=x,y0=top,x1=x+w,y1=floor)

def cooler(cv,x,floor):
    top=floor-44
    cv.rect(x,top+14,x+16,floor,C('#d8dce0'),3)
    cv.ellipse(x+8,top+10,8,10,C('#a8d4f0'),3.5,emi=C('#4a88b0'))
    cv.rect(x+6,top+22,x+10,top+26,C('#3a3d44'),3)
    cv.rect(x+2,floor-8,x+14,floor,C('#b0b4b8'),3)
    return dict(x0=x,y0=top+14,x1=x+16,y1=floor)

def tripod_cam(cv,x,floor):
    """Camera on a tripod, in profile."""
    # legs
    cv.line(x,floor,x+1,floor-34,C('#2a2c30'),3)
    cv.line(x-8,floor,x+1,floor-34,C('#2a2c30'),3)
    cv.line(x+8,floor,x+1,floor-34,C('#2a2c30'),3)
    # head / body
    cv.rect(x-7,floor-42,x+10,floor-34,C('#1a1c20'),4)
    cv.rect(x+10,floor-41,x+16,floor-36,C('#2a2c32'),4)  # lens
    cv.ellipse(x+16,floor-38,2,3,C('#12141a'),4)
    cv.rect(x-4,floor-45,x+4,floor-42,C('#3a3c42'),4)  # viewfinder
    return dict(x0=x-8,y0=floor-20,x1=x+9,y1=floor)  # low solid, can jump over? actually tall-ish. Don't block walk much — only the legs as a slim solid

def softbox(cv,x,floor):
    """Light stand + softbox."""
    cv.rect(x,floor-70,x+2,floor,C('#2a2c30'),3)
    cv.rect(x-3,floor-4,x+5,floor,C('#1a1c20'),3)
    # softbox
    cv.rect(x-10,floor-88,x+14,floor-68,C('#e8e6de'),4,emi=C('#d8d4c8'))
    cv.rect(x-9,floor-87,x+13,floor-69,C('#f4f2ea'),4,emi=C('#eeeae0'))
    LIGHTS.append(dict(x=x+2,y=floor-78,c=[1.0,0.96,0.88],r=130,i=0.7,cone=0,flick=0.02))
    return dict(x0=x-2,y0=floor-8,x1=x+4,y1=floor)

def gimbal(cv,x,floor):
    """Gimbal on a low stand / desk-height perch."""
    y=floor-22
    cv.rect(x,y,x+3,floor,C('#2a2c30'),3)
    cv.rect(x-4,y-8,x+8,y,C('#1a1c22'),4)
    cv.rect(x-1,y-14,x+6,y-8,C('#2a2c32'),4)
    cv.rect(x+6,y-13,x+11,y-10,C('#3a3c44'),4)  # tiny lens

def glass_door(cv,x,floor,w=40):
    """Glass office door with company sign 볼더스튜디오."""
    top=floor-80
    cv.rect(x-3,top-4,x+w+3,floor,C('#3a3d44'),3)
    # glass pane
    cv.dgrad(x,top,x+w,floor,C('#8aa0b8'),C('#3a4858'),True,steps=4,hg=1)
    cv.emi(x,top,x+w,floor,C('#2a3848'))
    # diagonal highlight
    for k in range(8):
        cv.px(x+6+k,top+10+k,C('#c8d8e8'),2)
    # company sign / logo on the glass — 볼더스튜디오 (Boulder Studio)
    tw=cv.textw(CO,'Galmuri9',9)
    # plaque may be slightly wider than the pane; keep it centered
    sx=x+(w-tw)//2; sy=top+14
    cv.rect(sx-4,sy-3,sx+tw+4,sy+26,C('#0A0A0A'),4)
    cv.rect(sx-4,sy-3,sx+tw+4,sy-1,C('#E61919'),4)
    cv.text(sx,sy,CO,C('#EAEAEA'),'Galmuri9',9,hg=4.2)
    bw=cv.textw('BOULDER STUDIO','Galmuri7',8)
    cv.text(x+(w-bw)//2,sy+12,'BOULDER STUDIO',C('#9a9a9a'),'Galmuri7',8,hg=4)
    cv.rect(x+w-8,floor-44,x+w-5,floor-40,C('#c8a04a'),4)
    cv.rect(x-3,top-4,x+w+3,top,C('#4a4e56'),3.5)
    return dict(x0=x-2,y0=top,x1=x+w+2,y1=floor)

def stairs(cv,x,floor):
    cv.rect(x,138,x+2,floor,C('#3a3d44'),2)
    cv.dgrad(x,138,x+90,floor,C('#101218'),C('#07080a'),True,steps=4,hg=-6)
    for i in range(8):
        sy=floor-i*8; sx=x+6+i*8
        cv.rect(sx,sy-8,x+90,sy,C('#3a3c42'),1)
        cv.rect(sx,sy-8,sx+8,sy-7,C('#6a6c72'),2)
    cv.rect(x+2,138,x+90,142,C('#2a2c32'),2)
    cv.rect(x+8,150,x+44,164,C('#1a1c22'),3)
    cv.text(x+10,152,'1층 ↓',C('#eaeaea'),'Galmuri9',10,hg=3.2)
    return dict(x0=x,y0=138,x1=x+8,y1=floor)

def whiteboard(cv,x,y,w=80,h=48):
    cv.rect(x,y,x+w,y+h,C('#e8e6dc'),2)
    cv.rect(x,y,x+w,y+2,C('#3a3c40'),2)
    # storyboard frames
    for i,xx in enumerate(range(x+4,x+w-16,18)):
        cv.rect(xx,y+6,xx+16,y+18,C('#d0cec4'),2)
        cv.rect(xx,y+20,xx+16,y+32,C('#d0cec4'),2)
        if i==0:
            cv.text(xx+1,y+8,'S1',C('#2a2a2a'),'Galmuri7',8,hg=2)
    cv.text(x+4,y+36,'11/컷리스트',C('#3a3a3a'),'Galmuri7',8,hg=2)

def build():
    cv=Cv(OW,OH)
    cv.rect(0,0,OW,118,C('#07080a'),-20)
    cv.rect(0,FEET+CURB,OW,OH,C('#07080a'),-20)
    # ceiling
    cv.rect(0,118,OW,138,C('#2a2c30'),2)
    cv.rect(0,136,OW,138,C('#1a1c20'),1)
    # cable tray under ceiling
    cv.rect(40,138,OW-40,142,C('#3a3c42'),3)
    for fx in (90,260,430,620,860,1080):
        # track lights, not office fluorescents
        cv.rect(fx,138,fx+18,144,C('#1a1c20'),4)
        cv.rect(fx+4,144,fx+14,148,C('#f0e8d0'),4,emi=C('#e8d8a8'))
        LIGHTS.append(dict(x=fx+9,y=148,c=[1.0,0.92,0.78],r=150,i=0.75,cone=1,flick=0.12 if fx in (620,860) else 0.04))
    # back wall — dark studio
    cv.rect(0,138,OW,FEET,C('#3a3c42'),0)
    for y in range(138,FEET,5):
        cv.rect(0,y,OW,y+1,mul(C('#3a3c42'),0.92),0)
    # acoustic foam band
    for xx in range(20,OW-20,8):
        for yy in range(FEET-40,FEET-8,8):
            cv.rect(xx,yy,xx+6,yy+6,C('#2e3036') if ((xx+yy)//8)%2==0 else C('#262830'),0.4)
    # left wall
    cv.rect(0,118,18,FEET+CURB,C('#2a2c30'),2)
    SOLIDS.append(dict(x0=0,y0=138,x1=18,y1=FEET))
    # windows
    wins=[(70,168,170,310),(200,168,300,310),(430,168,540,310),(560,168,660,310)]
    for x0,y0,x1,y1 in wins:
        cv.rect(x0-3,y0-3,x1+3,y1+3,C('#2a2c32'),2)
        dusk_view(cv,x0,y0,x1,y1)
        blinds(cv,x0,y0,x1,y1,0.5 if x0<400 else 0.25)
        cv.rect(x0-3,y1+3,x1+3,y1+6,C('#3a3c42'),2.5)
        LIGHTS.append(dict(x=(x0+x1)//2,y=y1-4,c=[1.0,0.7,0.4],r=70,i=0.3,cone=0,flick=0))
    # clock
    cv.ellipse(340,200,11,11,C('#e8e0d0'),3)
    cv.ellipse(340,200,9,9,C('#f4f0e8'),3)
    cv.rect(340,192,341,200,C('#1a1a1a'),3.5)
    cv.rect(340,200,347,201,C('#1a1a1a'),3.5)
    # company wall sign between windows
    cv.rect(312,220,428,252,C('#0A0A0A'),3)
    cv.text(322,224,CO,C('#EAEAEA'),'Galmuri9',10,hg=3.4)
    cv.text(322,236,'영상 · 양재1동 · 2층',C('#9a9a9a'),'Galmuri7',8,hg=3.2)
    # storyboard whiteboard
    whiteboard(cv,312,258,110,44)
    # safety still on the wall (news foreshadow)
    cv.rect(680,200,744,268,C('#f4f0e0'),2)
    cv.rect(680,200,744,212,C('#c41a1a'),2)
    cv.text(686,202,'대처요령',C('#f4f0e0'),'Galmuri9',10,hg=2.5)
    cv.text(684,216,'물리면 씻고',C('#1a1a1a'),'Galmuri7',8,hg=2)
    cv.text(684,226,'문을 잠글 것',C('#1a1a1a'),'Galmuri7',8,hg=2)
    cv.text(684,236,'소리 주의',C('#1a1a1a'),'Galmuri7',8,hg=2)
    cv.text(684,246,'물은 피함',C('#1a1a1a'),'Galmuri7',8,hg=2)
    # furniture / kit
    SOLIDS.append(rack(cv,22,FEET,24,66))
    SOLIDS.append(rack(cv,48,FEET,24,52))
    SOLIDS.append(cooler(cv,92,FEET))
    ITEMS.append(dict(k='water',x=100,y=FEET))
    # 성재's edit bay — news on the left monitor
    SOLIDS.append(edit_desk(cv,210,FEET,96,lit=True,news=True,dual=True))
    LIGHTS.append(dict(x=250,y=FEET-48,c=[0.95,0.92,0.8],r=90,i=1.05,cone=0,flick=0.08))
    # second edit bay
    SOLIDS.append(edit_desk(cv,350,FEET,86,lit=True,news=False,dual=True))
    # pelican / hard-case — jump tutorial
    cv.rect(510,FEET-16,562,FEET,C('#3a3a28'),3)
    cv.rect(510,FEET-16,562,FEET-14,C('#c8a02a'),3.5)
    cv.rect(518,FEET-22,542,FEET-16,C('#2a2a1c'),3)
    SOLIDS.append(dict(x0=510,y0=FEET-16,x1=562,y1=FEET))
    # third desk, dark
    SOLIDS.append(edit_desk(cv,580,FEET,74,lit=False,news=False,dual=False))
    # light stand + camera + gimbal in the open floor
    softbox(cv,670,FEET)
    tripod_cam(cv,700,FEET)
    gimbal(cv,730,FEET)
    # low lighting cart (half-wall stand-in before the door)
    cv.rect(748,FEET-20,790,FEET,C('#2a2c30'),2)
    cv.rect(748,FEET-20,790,FEET-18,C('#4a4e56'),2.5)
    cv.rect(752,FEET-28,762,FEET-20,C('#f0e8d0'),3,emi=C('#d8c898'))
    SOLIDS.append(dict(x0=748,y0=FEET-20,x1=790,y1=FEET))
    LIGHTS.append(dict(x=757,y=FEET-26,c=[1.0,0.94,0.8],r=50,i=0.4,cone=0,flick=0))
    # glass door with 볼더스튜디오 + infected stands in front
    glass_door(cv,818,FEET,42)
    # stairwell
    SOLIDS.append(stairs(cv,980,FEET))
    # floor
    for xx in range(0,OW):
        f=0.9+0.12*((xx*7)%5)/5
        # dark studio floor (not municipal linoleum)
        cv.px(xx,FEET,mul(C('#4a4c52'),f),1.8)
        cv.rect(xx,FEET,xx+1,FEET+5,mul(C('#3a3c42'),f),1.0)
        cv.rect(xx,FEET+5,xx+1,FEET+CURB,C('#24262a'),0.3)
        if R.random()<0.03: cv.px(xx,FEET+1,R.choice(LEAFS) if R.random()<0.3 else C('#2a2c30'),1.4)
    cv.rect(0,FEET+5,OW,FEET+6,C('#5a5c62'),2)
    cv.rect(0,FEET+CURB-1,OW,FEET+CURB,C('#1a1c20'),0)
    cv.rect(0,FEET+CURB,OW,FEET+CURB+8,C('#2a2c30'),-1)
    cv.rect(0,FEET+CURB+8,OW,FEET+CURB+10,C('#16181c'),-1)
    for lx,ly in ((180,FEET-1),(470,FEET-1),(640,FEET-1)):
        cv.px(lx,ly,R.choice(LEAFS),2); cv.px(lx+1,ly,R.choice(LEAFS),2)
    # extinguisher
    cv.rect(800,FEET-40,808,FEET-18,C('#c41a1a'),3)
    cv.rect(802,FEET-42,806,FEET-40,C('#2a2a2a'),3)

    files=cv.save(OUT+'L_office',strength=1.0,chunk=2048)
    Image.fromarray(cv.c,'RGBA').save('/tmp/L_office.png')
    meta=dict(
        world=dict(w=OW,h=OH,feet=FEET,low=FEET,slope0=99999,slope1=99999,water=99999,goal=99999,xmax=1260,ct0=108,name='office'),
        layers=[dict(name='office',p=1.0,w=OW,h=OH,chunks=files)],
        lights=LIGHTS,
        solids=SOLIDS,
        items=ITEMS,
        enemies=[['inf_a', 800]],
        exits=[dict(x=818,w=44,k='door'), dict(x=1040,w=80,k='stairs')],
        start=dict(x=250,face=1),
        notes=dict(
            location='볼더스튜디오 2층, 양재1동',
            company='볼더스튜디오',
            canon='볼더스튜디오 (Boulder Studio). 최성재가 운영하는 영상 제작사. 양재1동 2층.',
        ),
    )
    json.dump(meta, open(OUT+'office.json','w'), ensure_ascii=False, indent=2)
    print('office', OW, 'lights', len(LIGHTS), 'solids', len(SOLIDS), 'co', CO)

if __name__=='__main__':
    build()
