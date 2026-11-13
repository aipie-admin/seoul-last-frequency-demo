import numpy as np, math, json, random
from PIL import Image
from lib import Cv, hx, mul, lerp, outline, BAYER
OUT='/workspace/seoul_survival/webgl/public/px/'
LW=6400; WH=560; FEET=412; LOW=482
SLOPE0=5520; SLOPE1=5780; WATER_X=6100; GOAL_X=5840
VIEW_MAXW=720
def lw(p): return int(math.ceil(((LW-VIEW_MAXW)*p+VIEW_MAXW)/16)*16)
C=lambda s:hx(s)
SNOW=[C('#7f8ea6'),C('#a7b4c8'),C('#c9d3e2'),C('#e8eef6')]
rng=np.random.default_rng(2026); R=random.Random(2026)
def vnoise(w,h,octs):
    acc=np.zeros((h,w),np.float32); tot=0
    for sc,a in octs:
        g=rng.random((h//sc+2,w//sc+2)).astype(np.float32)
        im=Image.fromarray((g*255).astype(np.uint8)).resize(((w//sc+2)*sc,(h//sc+2)*sc),Image.BICUBIC)
        acc+=np.asarray(im,np.float32)[:h,:w]/255*a; tot+=a
    return acc/tot
LIGHTS=[]; PROPS=[]; SOLIDS=[]; ITEMS=[]; ENEMIES=[]; ANIMS=[]; ZONES=[]

def snowcap(cv,x0,x1,y,maxh=3,hg=2.0):
    x0=int(x0); x1=int(x1); h=0.0
    for x in range(x0,x1):
        h=max(1,min(maxh,h+R.choice([-1,0,0,1]))) if x>x0 else R.randint(1,maxh)
        hh=int(h) if x not in (x0,x1-1) else 1
        for k in range(hh):
            col=SNOW[3] if k==hh-1 else SNOW[2]
            cv.px(x,y-1-k,col,hg+k*0.5)
        cv.px(x,y,SNOW[1],hg-0.5)

def brick(cv,x0,y0,x1,y1,base,rngl):
    cv.rect(x0,y0,x1,y1,mul(base,0.55),0)
    for yy in range(y0,y1,4):
        off=0 if ((yy-y0)//4)%2==0 else 4
        for xx in range(x0-off,x1,8):
            f=0.88+0.22*rngl.random()
            cv.rect(max(x0,xx),yy,min(x1,xx+7),min(y1,yy+3),mul(base,f),0.8)
            if rngl.random()<0.25: cv.px(max(x0,xx)+1,yy,mul(base,f*1.12),0.9)

def tiles(cv,x0,y0,x1,y1,base,size=5):
    cv.rect(x0,y0,x1,y1,mul(base,0.8),0)
    for yy in range(y0,y1,size):
        for xx in range(x0,x1,size):
            f=0.94+0.1*rng.random()
            cv.rect(xx,yy,min(x1,xx+size-1),min(y1,yy+size-1),mul(base,f),0.5)

def window(cv,x,y,w,h,lit=0.0,bars=False,curtain=None,frame=C('#8b9099'),warm=True,kind=0):
    cv.rect(x-1,y-1,x+w+1,y+h+1,frame,1.5)
    if lit>0:
        g0=C('#ffcf8a') if warm else C('#cfe2ff')
        g1=C('#c98a4a') if warm else C('#7f98c8')
        cv.dgrad(x,y,x+w,y+h,g0,g1,True,steps=4,hg=-2)
        e=mul(g0,lit)
        cv.emi(x,y,x+w,y+h,e)
        # interior hints
        if kind==1:   # shelf / furniture silhouettes
            cv.rect(x+1,y+h-5,x+w//2,y+h,mul(g1,0.45),-2); cv.emi(x+1,y+h-5,x+w//2,y+h,mul(e,0.3))
        elif kind==2: # hanging lamp + person silhouette
            cv.rect(x+w//2,y,x+w//2+1,y+3,mul(g1,0.4),-2)
            cx=x+w-6
            cv.rect(cx,y+h-9,cx+3,y+h,C('#2a1c18'),-2); cv.rect(cx,y+h-12,cx+3,y+h-9,C('#2a1c18'),-2); cv.emi(cx,y+h-12,cx+3,y+h,(30,20,12))
        elif kind==3: # tv glow
            cv.dgrad(x,y,x+w,y+h,C('#9ab4ff'),C('#30406a'),True,steps=3,hg=-2); cv.emi(x,y,x+w,y+h,mul(C('#6a86d8'),lit))
        if curtain is not None:
            cw=max(2,w//4)
            cv.rect(x,y,x+cw,y+h,curtain,-1); cv.rect(x+w-cw,y,x+w,y+h,curtain,-1)
            cv.emi(x,y,x+cw,y+h,mul(curtain,0.35*lit)); cv.emi(x+w-cw,y,x+w,y+h,mul(curtain,0.35*lit))
    else:
        cv.dgrad(x,y,x+w,y+h,C('#151b26'),C('#0b0e14'),True,steps=3,hg=-2)
        # sky reflection diagonal
        for k in range(min(w,h)):
            if x+k+2<x+w: cv.px(x+k+2,y+h-1-k,C('#26303f'),-2)
    if w>8: cv.rect(x+w//2,y,x+w//2+1,y+h,frame,1)
    if bars:
        for xx in range(x+1,x+w,3): cv.rect(xx,y-1,xx+1,y+h+1,C('#3a3d44'),2.5)
        cv.rect(x-1,y+h//2,x+w+1,y+h//2+1,C('#3a3d44'),2.5)
    cv.rect(x-2,y+h+1,x+w+2,y+h+3,C('#9a9690'),2.5)
    snowcap(cv,x-2,x+w+2,y+h+1,2,3)

def acunit(cv,x,y):
    cv.rect(x,y,x+12,y+9,C('#b9bcc0'),4); cv.rect(x,y+8,x+12,y+9,C('#7c8086'),4)
    cv.ellipse(x+5,y+4.5,3.2,3.2,C('#5b5f66'),3.5); cv.px(x+5,y+4,C('#2a2d33'),3)
    cv.rect(x+1,y+9,x+2,y+11,C('#4a4d52'),3); cv.rect(x+10,y+9,x+11,y+11,C('#4a4d52'),3)
    snowcap(cv,x,x+12,y,2,5)

def gaspipe(cv,x0,x1,y,vert_to=None):
    cv.rect(x0,y,x1,y+2,C('#b89c2c'),3); cv.rect(x0,y,x1,y+1,C('#d8bc4a'),3.5)
    if vert_to: cv.rect(x1-2,y,x1,vert_to,C('#a88c22'),3)

def sign(cv,x,y,w,h,txt,bg,fg,lit=1.0,font='Galmuri11-Bold',size=12,border=None):
    cv.rect(x,y,x+w,y+h,bg,3)
    if border: cv.rect(x,y,x+w,y+1,border,3.5); cv.rect(x,y+h-1,x+w,y+h,border,3)
    tw=cv.textw(txt,font,size)
    tx=x+(w-tw)//2; ty=y+(h-size)//2+1
    cv.text(tx,ty,txt,fg,font,size,emi=mul(fg,lit) if lit>0 else None,hg=3.5)
    if lit>0:
        cv.emi(x,y,x+w,y+h,mul(bg,0.55*lit))
        cv.text(tx,ty,txt,fg,font,size,emi=mul(fg,lit),hg=3.5)
    snowcap(cv,x,x+w,y,2,4.5)

def vsign(cv,x,y,txts,bg,fg,lit=1.0):
    w=13; h=len(txts)*12+4
    cv.rect(x,y,x+w,y+h,bg,4); cv.rect(x,y,x+1,y+h,mul(bg,1.3),4.5)
    for i,t in enumerate(txts):
        cv.text(x+1,y+3+i*12,t,fg,'Galmuri11-Bold',12,emi=mul(fg,lit) if lit>0 else None,hg=4.5)
    if lit>0: cv.emi(x,y,x+w,y+h,mul(bg,0.4*lit))
    snowcap(cv,x,x+w,y,2,5)

def roof(cv,x,w,top,kind=0):
    cv.rect(x-1,top-3,x+w+1,top,C('#6e6b66'),3)
    snowcap(cv,x-1,x+w+1,top-3,4,4)
    if kind==1:  # water tank + rooftop hut
        hx_=x+w-30
        cv.rect(hx_,top-22,hx_+22,top-3,C('#7b7f86'),2); cv.rect(hx_+3,top-16,hx_+9,top-3,C('#3a2c22'),1)
        cv.rect(hx_-1,top-24,hx_+23,top-22,C('#5a5e66'),3); snowcap(cv,hx_-1,hx_+23,top-24,4,4)
        if R.random()<0.6:
            cv.rect(hx_+12,top-15,hx_+19,top-9,C('#ffcf8a'),-1); cv.emi(hx_+12,top-15,hx_+19,top-9,C('#d89a50'))
    if kind in (1,2):
        tx=x+8
        cv.ellipse(tx+7,top-11,8,8,C('#b8bec6'),2,dome=3); cv.rect(tx,top-11,tx+15,top-3,C('#a8aeb6'),2)
        for k in range(0,15,3): cv.rect(tx+k,top-11,tx+k+1,top-3,C('#8c929a'),2.5)
        snowcap(cv,tx+1,tx+14,top-18,3,5)
    if R.random()<0.5:
        ax=x+w//2; cv.rect(ax,top-26,ax+1,top-3,C('#3c3f44'),2); cv.rect(ax-6,top-22,ax+7,top-21,C('#3c3f44'),2); cv.rect(ax-4,top-18,ax+5,top-17,C('#3c3f44'),2)

def villa(cv,x,w,base,floors,palette=None,ground='pilotis'):
    FH=30
    top=base-floors*FH-34
    col=palette or R.choice([C('#6b3b2e'),C('#7d5a40'),C('#5e5650'),C('#875042')])
    brick(cv,x,top,x+w,base,col,rng)
    # floor bands
    for f in range(floors+1):
        y=base-34-f*FH
        cv.rect(x,y-2,x+w,y,C('#a39d94'),2); snowcap(cv,x,x+w,y-2,2,3)
    # ground floor
    if ground=='pilotis':
        cv.rect(x+4,base-30,x+w-4,base,C('#0c0d10'),-6)
        cv.dgrad(x+4,base-30,x+w-4,base-22,C('#1a1c22'),C('#0c0d10'),steps=3,hg=-6)
        for cx in (x+4,x+w//2-3,x+w-10): cv.rect(cx,base-32,cx+6,base,C('#8d8a84'),2)
        cv.rect(x+w//2+8,base-28,x+w//2+16,base-26,C('#fff2d8'),-5); cv.emi(x+w//2+8,base-28,x+w//2+16,base-26,C('#ffe2b0'))
        LIGHTS_LOCAL.append((x+w//2+12,base-24,C('#ffd9a0'),70,0.6))
    else:
        dx=x+w//2-9
        cv.rect(dx-2,base-30,dx+20,base,C('#8d8a84'),1)
        cv.rect(dx,base-28,dx+18,base,C('#ffd9a0'),-3); cv.emi(dx,base-28,dx+18,base,C('#b88a50'))
        cv.rect(dx+8,base-28,dx+10,base,C('#3a3d44'),0)
        cv.rect(dx-4,base-34,dx+22,base-31,C('#5c5f66'),3); snowcap(cv,dx-4,dx+22,base-34,3,4)
        LIGHTS_LOCAL.append((dx+9,base-20,C('#ffd9a0'),80,0.7))
    for f in range(floors):
        y=base-34-(f+1)*FH+6
        nwin=max(2,w//48)
        sp=w/(nwin)
        for i in range(nwin):
            wx=int(x+sp*i+sp/2-11)
            lit=R.random()<0.28
            window(cv,wx,y,22,15,lit=1.0 if lit else 0,bars=R.random()<0.7,
                   curtain=R.choice([None,C('#c8a8a0'),C('#8aa0b8'),C('#d8c8a0')]) if lit else None,
                   warm=R.random()<0.8,kind=R.choice([0,1,2,3]))
            if R.random()<0.45: acunit(cv,wx+(26 if i%2==0 else -15),y+8)
        if R.random()<0.6: gaspipe(cv,x+2,x+w-2,y+20)
    roof(cv,x,w,top,R.choice([0,1,2]))
    cv.rect(x+w-3,top,x+w-1,base-2,C('#8a8f96'),3)  # drain pipe
    return top

def shop(cv,x,w,base,floors,name,bg,fg,lit=1.0,upper=None,interior='store',shutter=0.0,vtxt=None):
    FH=28
    top=base-40-floors*FH
    tcol=R.choice([C('#b7aa94'),C('#9aa0a6'),C('#c4b8a2'),C('#8c8072')])
    tiles(cv,x,top,x+w,base-40,tcol,5)
    for f in range(floors):
        y=base-40-(f+1)*FH+5
        cv.rect(x+3,y-1,x+w-3,y+18,C('#5e646c'),1.5)
        lt=R.random()<0.14
        if lt:
            cv.dgrad(x+4,y,x+w-4,y+17,C('#c8d4f0'),C('#7a88a8'),steps=3,hg=-2); cv.emi(x+4,y,x+w-4,y+17,C('#4a5674'))
            for k in range(x+8,x+w-8,14): cv.rect(k,y+10,k+8,y+17,C('#5a6278'),-2)
        else:
            cv.dgrad(x+4,y,x+w-4,y+17,C('#161c26'),C('#0b0e14'),steps=3,hg=-2)
        for k in range(x+4,x+w-4,24): cv.rect(k,y,k+1,y+17,C('#5e646c'),1)
        if upper and f<len(upper) and upper[f]:
            t=upper[f]; tw=cv.textw(t,'Galmuri11-Bold',12)
            cv.text(x+(w-tw)//2,y+3,t,C('#f2f2f2') if f%2 else C('#ff5a4a'),'Galmuri11-Bold',12,emi=(C('#f2f2f2') if lt else None),hg=-1)
        cv.rect(x+2,y+18,x+w-2,y+20,C('#8f8a82'),2.5); snowcap(cv,x+2,x+w-2,y+18,2,3)
    # storefront
    cv.rect(x,base-40,x+w,base,C('#3a3d44'),1)
    sx0=x+4; sx1=x+w-4; sy0=base-26; sy1=base
    if interior=='store' and lit>0:
        cv.dgrad(sx0,sy0,sx1,sy1,C('#fbfcff'),C('#c8d4e8'),steps=4,hg=-3); cv.emi(sx0,sy0,sx1,sy1,C('#c6d2e8'))
        for k in range(sx0+4,sx1-4,10):
            for sh in range(3):
                yy=sy0+5+sh*7; cv.rect(k,yy,k+7,yy+4,R.choice([C('#e04848'),C('#3c78d8'),C('#f0c040'),C('#48a858'),C('#f0f0f0')]),-2)
                cv.rect(k,yy+4,k+7,yy+5,C('#8a90a0'),-2)
        LIGHTS_LOCAL.append(((sx0+sx1)//2,base-12,C('#dfe8ff'),120,1.0))
    elif interior=='pharm' and lit>0:
        cv.dgrad(sx0,sy0,sx1,sy1,C('#e8fff0'),C('#a8d0b8'),steps=4,hg=-3); cv.emi(sx0,sy0,sx1,sy1,C('#80b090'))
        LIGHTS_LOCAL.append(((sx0+sx1)//2,base-12,C('#c8ffd8'),90,0.7))
    elif interior=='warm' and lit>0:
        cv.dgrad(sx0,sy0,sx1,sy1,C('#ffd49a'),C('#a8683a'),steps=4,hg=-3); cv.emi(sx0,sy0,sx1,sy1,C('#b07040'))
        for k in range(sx0+6,sx1-6,16): cv.rect(k,sy1-8,k+9,sy1-6,C('#5a3420'),-2); cv.rect(k+4,sy1-6,k+5,sy1,C('#5a3420'),-2)
        LIGHTS_LOCAL.append(((sx0+sx1)//2,base-12,C('#ffc080'),90,0.8))
    else:
        cv.dgrad(sx0,sy0,sx1,sy1,C('#11151c'),C('#07090c'),steps=3,hg=-3)
        # broken glass
        bx=R.randint(sx0+4,max(sx0+5,sx1-10)); cv.line(bx,sy0+2,bx+6,sy0+12,C('#5a6a80'),-1); cv.line(bx+6,sy0+12,bx+2,sy0+20,C('#5a6a80'),-1)
    for k in range(sx0,sx1,22): cv.rect(k,sy0,k+1,sy1,C('#7c828a'),1)
    # shutter
    if shutter>0:
        sh=int((sy1-sy0)*shutter)
        for yy in range(sy0,sy0+sh):
            cv.rect(sx0,yy,sx1,yy+1,C('#8a8e94') if yy%2 else C('#6c7076'),2 if yy%2 else 1)
        cv.rect(sx0,sy0+sh-1,sx1,sy0+sh,C('#3c3f44'),2.5)
        if R.random()<0.6:
            gx=R.randint(sx0+4,max(sx0+6,sx1-30)); cv.text(gx,sy0+3,R.choice(['살려줘','물 있음','감염','X','3층 생존']),C('#c41a1a'),'Galmuri9',10,hg=2.2)
    # awning / signboard
    sign(cv,x+1,base-40,w-2,14,name,bg,fg,lit)
    if vtxt: vsign(cv,x+w-16,top+10,vtxt,R.choice([C('#1c3c8c'),C('#8c1c1c'),C('#1c6c3c')]),C('#ffffff'),lit*0.9 if R.random()<0.7 else 0)
    roof(cv,x,w,top,R.choice([0,2]))
    return top

def streetlamp(cv,x,base,kind='led'):
    top=base-112
    cv.rect(x,top,x+3,base,C('#5c6068'),3); cv.rect(x,top,x+1,base,C('#7c8088'),3.5)
    cv.rect(x-1,base-14,x+4,base,C('#4c5058'),3.5)
    for k in range(18):
        cv.px(x+1+k, top-int(4*math.sin(k/18*math.pi))+ (0), C('#5c6068'),3)
        cv.px(x+1+k, top+1-int(4*math.sin(k/18*math.pi)), C('#4a4e56'),3)
    hx_=x+16
    cv.rect(hx_,top-2,hx_+12,top+2,C('#3a3d44'),4)
    col=C('#ffb466') if kind=='sodium' else C('#e2ecff')
    cv.rect(hx_+1,top+2,hx_+11,top+3,col,4,emi=col)
    snowcap(cv,hx_,hx_+12,top-2,2,5)
    LIGHTS.append(dict(x=hx_+6,y=top+4,c=[c/255 for c in col],r=150 if kind=='led' else 130,i=1.15 if kind=='led' else 1.0,cone=1,flick=0))

def utilpole(cv,x,base,h=150):
    cv.rect(x,base-h,x+5,base,C('#6a6660'),3); cv.rect(x,base-h,x+2,base,C('#8a857e'),3.5)
    for k in range(base-h+10,base-30,14): cv.rect(x+1,k,x+4,k+1,C('#4a4640'),3.5)
    cv.rect(x-10,base-h+8,x+15,base-h+10,C('#4a4640'),4)
    cv.rect(x-8,base-h+20,x+1,base-h+30,C('#5a5e66'),4.5)  # transformer
    for k,yy in enumerate((base-h+40,base-h+52)):
        cv.rect(x+5,yy,x+12,yy+8,C('#d8d4cc'),4); cv.text(x+5,yy,'광',C('#c41a1a'),'Galmuri7',8,hg=4.5) if k==0 else None
    return (x+2,base-h+9)

def wire(cv,a,b,sag=14,col=C('#15161a')):
    n=int(abs(b[0]-a[0]))
    for i in range(n+1):
        t=i/max(1,n); x=a[0]+(b[0]-a[0])*t; y=a[1]+(b[1]-a[1])*t+sag*4*t*(1-t)
        cv.px(x,y,col,6)

# ------------------------------------------------------------------ STREET (p=1)
LIGHTS_LOCAL=[]
def street():
    cv=Cv(LW,WH)
    BASE=368
    # far backdrop wall (dark) so gaps show alleys
    x=0
    plan=[
     ('villa',230,4,dict(ground='entry',palette=C('#7d5a40'))),
     ('shop',150,3,dict(name='편의점 24',bg=C('#1f6fd0'),fg=C('#ffffff'),interior='store',upper=['','영어·수학','']) ),
     ('shop',120,3,dict(name='온누리약국',bg=C('#1c8a4c'),fg=C('#ffffff'),interior='pharm',vtxt=['치','과'],upper=['','','필라테스'])),
     ('alley',26,0,{}),
     ('shop',140,4,dict(name='양재 치킨·호프',bg=C('#e8b018'),fg=C('#3a1a0a'),interior='dark',shutter=0.6,upper=['노래연습장','','','당구'])),
     ('shop',130,2,dict(name='공인중개사',bg=C('#2a2e78'),fg=C('#ffe060'),interior='dark',shutter=1.0,lit=0)),
     ('shop',150,4,dict(name='김밥나라',bg=C('#d43a2a'),fg=C('#fff4d8'),interior='warm',lit=0.7,vtxt=['학','원'],upper=['수학 학원','','PC','임대문의'])),
     ('shop',120,3,dict(name='세탁',bg=C('#3a8ad0'),fg=C('#ffffff'),interior='dark',shutter=0.85,lit=0)),
     ('gap',40,0,{}),  # intersection 1450-1750 handled below
    ]
    def place(plan,x):
        for kind,w,fl,kw in plan:
            if kind=='villa': villa(cv,x,w,BASE,fl,palette=kw.get('palette'),ground=kw.get('ground','pilotis'))
            elif kind=='shop':
                shop(cv,x,w,BASE,fl,kw['name'],kw['bg'],kw['fg'],kw.get('lit',1.0),kw.get('upper'),kw.get('interior','store'),kw.get('shutter',0),kw.get('vtxt'))
            elif kind=='alley':
                cv.dgrad(x,200,x+w,BASE,C('#0a0c12'),C('#14161c'),steps=4,hg=-14)
                cv.rect(x+w//2-1,BASE-60,x+w//2+1,BASE-58,C('#ffb466'),-10,emi=C('#a06a30'))
                LIGHTS_LOCAL.append((x+w//2,BASE-50,C('#ffb466'),60,0.5))
            x+=w
        return x
    x=place(plan,0)
    # intersection 1450..1750: cross road going back (perspective), traffic light
    IX0,IX1=1460,1760
    cv.dgrad(IX0,150,IX1,BASE,C('#06070a'),C('#0e1016'),steps=4,hg=-20)
    # receding road
    cv.poly([(IX0+40,BASE),(IX1-40,BASE),(IX1-110,300),(IX0+110,300)],C('#1c1e23'),-15)
    for k in range(5):
        y=BASE-6-k*13; cv.rect(IX0+120-k*0, y, IX1-120+k*0, y+2, C('#3a3c42'),-15)
    # distant buildings through intersection
    for i,bx in enumerate(range(IX0+10,IX1-10,48)):
        h=R.randint(110,190); cv.rect(bx,300-h,bx+44,300,C('#121620'),-18)
        for wy in range(300-h+8,296,12):
            for wx in range(bx+4,bx+40,9):
                if R.random()<0.2: cv.rect(wx,wy,wx+5,wy+6,C('#c8a070'),-18,emi=C('#6a5032'))
    # bus in back lane (static wreck)
    bx=IX0+150; by=BASE+6
    bus=Cv(150,62)
    bus.rect(2,4,148,52,C('#3a9a5a'),3); bus.rect(2,4,148,8,C('#2c7a46'),4)
    bus.rect(2,40,148,52,C('#2a2e34'),2)
    for k in range(8,140,18): bus.rect(k,12,k+15,30,C('#1a222c'),0); bus.rect(k,12,k+15,14,C('#2c3644'),0)
    bus.rect(120,12,146,30,C('#ffd9a0'),0,emi=C('#806040'))
    bus.text(10,32,'4412 양재',C('#ffffff'),'Galmuri9',10,emi=C('#d0d0d0'),hg=3.5)
    bus.ellipse(26,52,8,8,C('#15161a'),3,dome=3); bus.ellipse(118,52,8,8,C('#15161a'),3,dome=3)
    bus.ellipse(26,52,3,3,C('#6a6e76'),5); bus.ellipse(118,52,3,3,C('#6a6e76'),5)
    snowcap(bus,4,146,4,4,6)
    cv.blit(bus,bx,by-58)
    x=IX1
    plan2=[
     ('villa',180,4,dict()),('alley',22,0,{}),('villa',200,3,dict(ground='entry')),('villa',170,4,dict()),
     ('shop',120,2,dict(name='세탁소',bg=C('#3a8ad0'),fg=C('#ffffff'),interior='dark',shutter=1.0,lit=0)),
     ('villa',210,4,dict(ground='entry')),('alley',26,0,{}),('villa',180,3,dict()),('villa',200,4,dict(ground='entry')),
    ]
    x=place(plan2,x)
    # station commercial block ~3150..4300
    x=max(x,3150)
    shop(cv,x,260,BASE,6,'양재 메디컬',C('#e8e8e8'),C('#1c3c8c'),0.6,['내과·이비인후과','','치과','영어학원','','헬스'],'pharm',0,['병','원'])
    # subway entrance
    sx=x+270; 
    cv.rect(sx,BASE-46,sx+90,BASE,C('#2a2e36'),1)
    cv.dgrad(sx+6,BASE-36,sx+84,BASE,C('#020203'),C('#0c0e12'),steps=3,hg=-8)
    for k in range(6): cv.rect(sx+10+k*6,BASE-30+k*5,sx+80,BASE-29+k*5,C('#20232a'),-6)
    cv.rect(sx,BASE-52,sx+90,BASE-44,C('#3a3d44'),3); snowcap(cv,sx,sx+90,BASE-52,3,4)
    sign(cv,sx+18,BASE-70,54,15,'양재역 ③',C('#1a1c22'),C('#f0f0f0'),0.9)
    cv.text(sx+4,BASE-36,'출입통제',C('#c41a1a'),'Galmuri9',10,hg=1)
    x=sx+100
    shop(cv,x,170,BASE,7,'24시 해장국',C('#5a2a1a'),C('#ffd9a0'),0.8,['','오피스텔','','','','','회계'],'warm',0.3)
    x+=170
    shop(cv,x,150,BASE,5,'휴대폰',C('#c41a1a'),C('#ffffff'),0,['','','','',''],'dark',0.4)
    x+=150
    villa(cv,x,200,BASE,4); x+=200
    shop(cv,x,140,BASE,3,'꽃집',C('#e86a9a'),C('#ffffff'),0,['','',''],'dark',1.0); x+=140
    # 4300-5400 quieter: low fence, apartments complex wall + trees
    x=max(x,4300)
    cv.dgrad(x,180,5420,BASE,C('#0b0e16'),C('#121620'),steps=4,hg=-16)
    for ax in range(x+20,5400,150):
        h=R.randint(150,200)
        cv.rect(ax,BASE-h,ax+120,BASE-30,C('#3c4250'),-10)
        for fy in range(BASE-h+10,BASE-40,12):
            for fx in range(ax+6,ax+116,10):
                if R.random()<0.15: cv.rect(fx,fy,fx+6,fy+7,C('#ffcf8a'),-10,emi=C('#a07848'))
                else: cv.rect(fx,fy,fx+6,fy+7,C('#1a1e28'),-10)
        cv.text(ax+40,BASE-h+2,f'{R.randint(101,112)}동',C('#d0d4dc'),'Galmuri9',10,hg=-9)
        snowcap(cv,ax,ax+120,BASE-h,3,-8)
    # concrete wall + fence
    cv.rect(x,BASE-30,5420,BASE,C('#6c6a66'),1); 
    for k in range(x,5420,6): cv.rect(k,BASE-30,k+1,BASE,C('#5a5854'),0.6)
    snowcap(cv,x,5420,BASE-30,4,3)
    for k in range(x,5420,10): cv.rect(k,BASE-52,k+1,BASE-30,C('#2a2d33'),4)
    cv.rect(x,BASE-52,5420,BASE-50,C('#2a2d33'),4)
    # road sign to 양재천
    gx=4980
    cv.rect(gx,BASE-120,gx+3,BASE+20,C('#8a8f96'),4)
    cv.rect(gx-40,BASE-140,gx+50,BASE-112,C('#1a5a9a'),5); cv.rect(gx-39,BASE-139,gx+49,BASE-138,C('#ffffff'),5.2)
    cv.text(gx-34,BASE-135,'양재천 →',C('#ffffff'),'Galmuri11-Bold',12,hg=5.5)
    cv.text(gx-34,BASE-123,'Yangjaecheon',C('#cfe0f0'),'Galmuri7',8,hg=5.5)
    snowcap(cv,gx-40,gx+50,BASE-140,3,6)
    # ---------------- park + slope + 둔치
    P0=5420
    # ground profile polygon for park/slope/둔치
    def gy(xx):
        if xx<SLOPE0: return FEET
        if xx<SLOPE1: 
            t=(xx-SLOPE0)/(SLOPE1-SLOPE0); return FEET+(LOW-FEET)*(0.5-0.5*math.cos(t*math.pi))
        return LOW
    # retaining wall on back side down to 둔치
    for xx in range(P0,LW):
        g=int(gy(xx))
        bh=int(10+5*math.sin(xx*0.02)+3*math.sin(xx*0.07))
        top=min(g-12,FEET-6)-bh if xx<SLOPE1 else g-12-bh
        cv.rect(xx,top,xx+1,g,C('#3a4256'),-4)
        cv.px(xx,top,SNOW[1],-3); cv.px(xx,top+1,lerp(C('#3a4256'),SNOW[0],0.5),-3)
        if (xx*7+top)%11==0: cv.rect(xx,top+3,xx+1,top+6,C('#2a3040'),-4)
    # bare trees
    for tx in (5450,5600,5730,5900,6030):
        tree(cv,tx,int(gy(tx))-10,R.randint(70,100))
    sign(cv,5440,FEET-72,72,15,'양재천 산책로',C('#2a5a3a'),C('#ffffff'),0.5)
    cv.rect(5474,FEET-57,5477,FEET-30,C('#6a6e76'),3)
    # 둔치 lamps
    for lx in (5700,5980):
        g=int(gy(lx))-28
        cv.rect(lx,g-62,lx+2,g,C('#40444c'),3); cv.rect(lx-3,g-66,lx+5,g-62,C('#2a2d33'),4)
        cv.rect(lx-2,g-62,lx+4,g-61,C('#b8f0c8'),4,emi=C('#b8f0c8'))
        LIGHTS.append(dict(x=lx+1,y=g-60,c=[0.72,0.94,0.8],r=120,i=0.8,cone=1,flick=0.15 if lx==5980 else 0))
    # benches
    for bxx in (5820,5940):
        g=int(gy(bxx))-26
        cv.rect(bxx,g,bxx+26,g+3,C('#5a3e2a'),3); cv.rect(bxx,g-8,bxx+26,g-6,C('#5a3e2a'),3)
        cv.rect(bxx+2,g+3,bxx+4,g+10,C('#2a2d33'),2); cv.rect(bxx+22,g+3,bxx+24,g+10,C('#2a2d33'),2)
        snowcap(cv,bxx,bxx+26,g,3,4)
    # ---------------- sidewalk + road (x<5420)
    for xx in range(0,P0):
        pass
    cv.rect(0,BASE,P0,BASE+16,C('#5a5c62'),0)
    for yy in range(BASE,BASE+16,4):
        off=0 if ((yy-BASE)//4)%2 else 5
        for xx in range(-off,P0,10):
            f=0.85+0.25*rng.random(); c=C('#7a5c58') if ((xx//10)%7==3) else C('#6c6e74')
            cv.rect(xx,yy,xx+9,yy+3,mul(c,f),0.6)
    # snow on sidewalk: lumpy cover, cleared path near shops
    for xx in range(0,P0):
        h=int(4+3*math.sin(xx*0.031)+2*math.sin(xx*0.11)+rng.random()*1.2)
        cv.rect(xx,BASE+16-h,xx+1,BASE+16,SNOW[2],1.5)
        cv.px(xx,BASE+16-h,SNOW[3],2)
    cv.rect(0,BASE+16,P0,BASE+20,C('#8c8e94'),2.5); snowcap(cv,0,P0,BASE+16,3,3)
    # road
    RY0=BASE+20; RY1=448
    P0=SLOPE0
    cv.dgrad(0,RY0,P0,RY1,C('#1c1e23'),C('#26282e'),steps=4,hg=0)
    cv.noise(0,RY0,P0,RY1,[(C('#2c2e34'),0.05),(C('#17181c'),0.05)],rng)
    # tire tracks (wet, darker, reflective) and slush
    for ty in (RY0+8,RY0+14,RY0+30,RY0+36):
        for xx in range(0,P0):
            if math.sin(xx*0.013+ty)>-0.6: cv.px(xx,ty+int(1.5*math.sin(xx*0.02+ty)),C('#121316'),-0.3)
    nz=vnoise(P0,RY1-RY0,[(64,6),(16,3),(4,1)])
    sub=cv.c[RY0:RY1,0:P0]
    m1=nz>0.66; m2=(nz>0.58)&~m1&((np.add.outer(np.arange(RY1-RY0),np.arange(P0))%2)==0)
    sub[m1,:3]=SNOW[1]; sub[m2,:3]=SNOW[0]
    cv.hg[RY0:RY1,0:P0][m1]=0.6
    m3=(nz>0.70); sub[m3,:3]=SNOW[2]
    wet=(nz<0.32); sub[wet,:3]=(sub[wet,:3].astype(np.float32)*0.7).astype(np.uint8)
    # lane markings: yellow double center line and dashed white
    for xx in range(0,P0):
        if not (IX0<xx<IX1):
            if math.sin(xx*0.05)>-0.85: cv.px(xx,RY0+4,C('#c8a02a'),0.3); cv.px(xx,RY0+6,C('#c8a02a'),0.3)
            if (xx//24)%2==0 and math.sin(xx*0.02)>-0.5: cv.px(xx,RY0+24,C('#b8bcc4'),0.3)
    # crosswalk
    for xx in range(IX0+20,IX1-20,14): cv.rect(xx,RY0,xx+8,RY1,C('#b0b4bc'),0.4)
    cv.noise(IX0,RY0,IX1,RY1,[(SNOW[1],0.08)],rng)
    # front curb (near side)
    cv.rect(0,RY1,P0,RY1+4,C('#7c7e84'),2); cv.rect(0,RY1+4,P0,WH,C('#0b0c10'),0)
    # park ground & slope
    for xx in range(SLOPE0,SLOPE0+60):  # snowdrift where road meets the park slope
        hh=int((xx-SLOPE0)*0.9)
        cv.rect(xx,RY0+max(0,20-hh//2),xx+1,RY1+4,SNOW[2] if (xx+hh)%7 else SNOW[1],1.2)
    for xx in range(SLOPE0,LW):
        g=int(gy(xx))
        cv.rect(xx,g-12,xx+1,WH,C('#0b0c10'),0)
        if xx<WATER_X+6:
            # walkable snow surface band
            cv.rect(xx,g-12,xx+1,g+8,SNOW[2] if xx<SLOPE1 else SNOW[1],1)
            cv.px(xx,g-12,SNOW[3],2); cv.px(xx,g-11,SNOW[3],1.8)
            if SLOPE0<=xx<SLOPE1 and (xx-SLOPE0)%9<2: cv.rect(xx,g-10,xx+1,g-4,SNOW[0],0.5)
            if xx>=SLOPE1:
                cv.rect(xx,g-6,xx+1,g-2,C('#5a5450'),0.4)  # gravel path line
        # stone embankment edge at water
    for yy in range(LOW-14,WH):
        for xx in range(WATER_X-12,WATER_X+4):
            if (xx+yy*3)%7<5: cv.px(xx,yy,mul(C('#5a5e66'),0.7+0.3*((xx*13+yy*7)%5)/5),1+0.4*((xx+yy)%3))
    snowcap(cv,WATER_X-12,WATER_X+4,LOW-14,3,3)
    # rail along park edge top
    for k in range(P0,SLOPE0+20,12): cv.rect(k,FEET-34,k+2,FEET-12,C('#4a4e56'),4)
    cv.rect(P0,FEET-34,SLOPE0+20,FEET-32,C('#5a5e66'),4); snowcap(cv,P0,SLOPE0+20,FEET-34,2,5)
    # streetlamps
    for lx in list(range(90,IX0-40,300))+list(range(IX1+60,4300,300))+[4420,4740,5060,5340]:
        streetlamp(cv,lx,BASE+12,'sodium' if (lx//300)%3==1 else 'led')
    # utility poles + wires
    tops=[]
    for px_ in range(250,5400,520):
        tops.append(utilpole(cv,px_,BASE+8,150))
    for a,b in zip(tops,tops[1:]):
        wire(cv,a,b,16); wire(cv,(a[0],a[1]+4),(b[0],b[1]+4),20,C('#1c1d22')); wire(cv,(a[0]-8,a[1]),(b[0]-8,b[1]),12)
    # graffiti / posters
    for gx in (640,2280,3060,4520):
        cv.text(gx,BASE-24,R.choice(['물가로 가라','한강','물 = 안전','물리면 끝']),C('#e6402c'),'Galmuri11-Bold',12,hg=1.5)
    for L in LIGHTS_LOCAL:
        LIGHTS.append(dict(x=L[0],y=L[1],c=[c/255 for c in L[2]],r=L[3],i=L[4],cone=0,flick=0.05))
    return cv

def tree(cv,x,base,h):
    def br(x0,y0,ang,L,w,d):
        if d==0 or L<3: return
        x1=x0+L*math.sin(ang); y1=y0-L*math.cos(ang)
        n=int(L)+1
        for i in range(n):
            t=i/max(1,n-1); xx=x0+(x1-x0)*t; yy=y0+(y1-y0)*t
            ww=max(1,int(w*(1-t*0.4)))
            cv.rect(int(xx-ww/2),int(yy),int(xx-ww/2)+ww,int(yy)+1,C('#2a2420') if d>2 else C('#3a322c'),3)
            if ang>-0.9 and ang<0.9 and i%2==0 and w<3: cv.px(xx,yy-1,SNOW[2],3.5)
        k=R.choice([2,2,3])
        for j in range(k):
            br(x1,y1,ang+R.uniform(-0.75,0.75),L*R.uniform(0.6,0.78),max(1,w*0.65),d-1)
    br(x,base,R.uniform(-0.1,0.1),h*0.38,5,6)

# ------------------------------------------------------------------ parallax layers
def sky():
    W=lw(0.03); cv=Cv(W,WH)
    cv.dgrad(0,0,W,300,C('#070a14'),C('#1e2036'),steps=10)
    cv.dgrad(0,300,W,WH,C('#1e2036'),C('#4a3446'),steps=8)
    # clouds: dithered bands lit from below by city glow
    for k in range(40):
        cx=R.randint(0,W); cy=R.randint(120,330); rw=R.randint(60,200); rh=R.randint(6,16)
        cv.ellipse(cx,cy,rw,rh,lerp(C('#141626'),C('#3a3048'),(cy-120)/210))
    # moon behind cloud
    cv.ellipse(W*0.72,170,9,9,C('#d8dce8'),emi=C('#9aa0b8')); cv.ellipse(W*0.72+3,168,8,8,C('#151826'))
    return cv

def skyline(W,base,hmin,hmax,col,wincol,density,lit,p,seed,mountain=False,towers=False):
    cv=Cv(W,WH); r=random.Random(seed)
    if mountain:
        for xx in range(W):
            h=int(70+40*math.sin(xx*0.004+1)+20*math.sin(xx*0.013)+8*math.sin(xx*0.05))
            cv.rect(xx,base-60-h,xx+1,base,mul(col,0.8),0)
            # snow on ridges
            cv.px(xx,base-60-h,lerp(col,SNOW[1],0.45),0)
            if (xx*7)%13<4: cv.px(xx,base-59-h,lerp(col,SNOW[1],0.25),0)
        cv.text(int(W*0.18),base-150,'',col)
    x=0
    while x<W:
        w=r.randint(28,70); h=r.randint(hmin,hmax)
        if towers and r.random()<0.18: h=int(hmax*1.6); w=r.randint(30,44)
        top=base-h
        cv.rect(x,top,x+w,base,col,0)
        cv.rect(x,top,x+1,base,mul(col,1.25),0)
        for wy in range(top+5,base-4,7 if p<0.3 else 9):
            for wx in range(x+3,x+w-3,5 if p<0.3 else 7):
                if r.random()<density:
                    lc=r.choice(wincol)
                    cv.rect(wx,wy,wx+(2 if p<0.3 else 3),wy+(3 if p<0.3 else 4),lc,0,emi=mul(lc,lit))
        if r.random()<0.25:
            cv.px(x+w//2,top-1,C('#ff3020'),0,emi=C('#ff3020'))  # aviation light
            ANIMS.append(dict(kind='blink',layer=p,x=x+w//2,y=top-1))
        if r.random()<0.12 and p>0.2:
            # red neon church cross
            cx=x+w//2; cv.rect(cx,top-16,cx+1,top-2,C('#ff2a2a'),0,emi=C('#ff3a3a')); cv.rect(cx-4,top-12,cx+5,top-11,C('#ff2a2a'),0,emi=C('#ff3a3a'))
        snowcap(cv,x,x+w,top,2,0)
        x+=w+r.randint(0,10)
    return cv

def far():
    W=lw(0.15); cv=Cv(W,WH)
    m=skyline(W,330,40,110,C('#121524'),[C('#c8a070'),C('#8090b0')],0.10,0.7,0.15,11,mountain=True)
    cv.blit(m,0,0)
    # haze band
    cv.ditherfill(0,300,W,340,C('#2a2638'),0.35)
    return cv
def mid2():
    W=lw(0.35); cv=Cv(W,WH)
    m=skyline(W,350,70,170,C('#171b28'),[C('#d8a868'),C('#90a8d0'),C('#e8c890')],0.14,0.85,0.35,22,towers=True)
    cv.blit(m,0,0)
    # 도곡동 towers near the end (across the stream)
    for i,tx in enumerate(range(W-420,W-60,90)):
        h=230+i*18; cv.rect(tx,350-h,tx+46,350,C('#1a1f2e'),0)
        cv.rect(tx+20,350-h-20,tx+22,350-h,C('#3a3f4a'),0); cv.px(tx+21,350-h-21,C('#ff3020'),0,emi=C('#ff3020'))
        for wy in range(350-h+6,346,8):
            for wx in range(tx+4,tx+44,6):
                if R.random()<0.22: cv.rect(wx,wy,wx+3,wy+4,C('#cfdcf0'),0,emi=C('#8090b8'))
    cv.ditherfill(0,320,W,360,C('#22243a'),0.4)
    return cv
def mid1():
    W=lw(0.6); cv=Cv(W,WH)
    x=0; base=366
    while x<3240:
        w=R.randint(90,150); fl=R.randint(4,8)
        if R.random()<0.5:
            villa(cv,x,w,base,min(fl,5))
        else:
            shop(cv,x,w,base,fl,R.choice(['','','','노래방','당구장','PC방','순대국','커피','정형외과','이비인후과']),R.choice([C('#20307a'),C('#7a2020'),C('#206a3a'),C('#5a5a5a')]),C('#ffffff'),R.choice([0,0,0.6]),
                 [R.choice(['','','','영어','수학','태권도','미술','교회','헬스','PC']) for _ in range(fl)],'dark',R.choice([0,0.6,1.0]),
                 R.choice([None,None,['노','래'],['약','국'],['교','회']]))
        x+=w+R.randint(0,6)
    # stream valley: opposite bank trees + embankment road lamps
    for xx in range(x,W):
        h=int(18+6*math.sin(xx*0.03)+4*math.sin(xx*0.11))
        cv.rect(xx,base-h,xx+1,base+40,C('#1a2030'),0); cv.px(xx,base-h,SNOW[0],0)
    for tx in range(x+30,W,70): tree(cv,tx,base-12,R.randint(50,80))
    for lx in range(x+60,W,110):
        cv.rect(lx,base-70,lx+1,base-14,C('#2a2e38'),0); cv.rect(lx-2,base-72,lx+3,base-70,C('#ffcf8a'),0,emi=C('#ffcf8a'))
    # atmospheric perspective: darken + push toward fog blue
    f=np.array([0.42,0.46,0.58],np.float32); fogc=np.array(C('#1c2032'),np.float32)
    cv.c[...,:3]=(cv.c[...,:3].astype(np.float32)*f+fogc*0.35).clip(0,255).astype(np.uint8)
    cv.e[...]=(cv.e.astype(np.float32)*0.6).astype(np.uint8)
    return cv

def fg():
    W=lw(1.25); cv=Cv(W,WH)
    # snowbanks along bottom, poles, guard rails; mostly dark silhouettes with snow tops
    for xx in range(W):
        h=int(16+10*math.sin(xx*0.011)+6*math.sin(xx*0.037)+3*math.sin(xx*0.13))
        if xx>6900: continue
        top=(WH-90-h) if xx<6700 else (WH-90-h+int((xx-6700)*0.6))
        cv.rect(xx,top,xx+1,WH,C('#0c0e14'),0)
        cv.px(xx,top,SNOW[1],1); cv.px(xx,top+1,SNOW[0],0.5)
    x=200
    while x<6500:
        k=R.random()
        if k<0.3:
            # guardrail segment
            for px_ in range(x,x+120,24): cv.rect(px_,WH-100,px_+4,WH,C('#14161c'),2)
            cv.rect(x,WH-98,x+124,WH-90,C('#1c1f26'),3); cv.rect(x,WH-98,x+124,WH-97,C('#3a3e48'),3.5)
            snowcap(cv,x,x+124,WH-98,3,4)
            x+=R.randint(260,420)
        elif k<0.55:
            # pole silhouette
            cv.rect(x,0,x+9,WH,C('#0e1016'),3); cv.rect(x,0,x+1,WH,C('#262a34'),3)
            x+=R.randint(300,500)
        elif k<0.75:
            # dead shrub
            for j in range(14):
                a=R.uniform(-1.1,1.1); L=R.randint(10,26)
                cv.line(x,WH-66,x+L*math.sin(a),WH-66-L*math.cos(a),C('#0e1014'),2)
            x+=R.randint(200,360)
        else:
            # parked car silhouette front
            cv.ellipse(x+40,WH-64,46,18,C('#0f1117'),2,dome=4); cv.rect(x-6,WH-70,x+86,WH,C('#0f1117'),2)
            snowcap(cv,x+4,x+76,WH-82,4,5)
            x+=R.randint(320,500)
    # dry reeds (갈대) at the stream edge, frozen
    for rx in range(6880,W,3):
        if R.random()<0.55:
            hgt=R.randint(18,46); lean=R.uniform(-0.25,0.35); base_=WH-R.randint(0,10)
            for k in range(hgt):
                cv.px(rx+int(lean*k*0.6),base_-k,C('#121014') if k<hgt-5 else C('#3a3026'),2)
            cv.px(rx+int(lean*hgt*0.6),base_-hgt,SNOW[1],2.5)
    return cv

# ------------------------------------------------------------------ props
def car(color,kind='sedan',hazard=False,crashed=False):
    W,H=(104,44) if kind!='suv' else (108,50)
    cv=Cv(W,H)
    body=C(color); dark=mul(body,0.6); light=mul(body,1.25)
    gl=H-10
    if kind=='sedan':
        pts=[(4,gl-14),(14,gl-18),(30,gl-20),(40,gl-32),(70,gl-32),(82,gl-20),(100,gl-17),(102,gl-6),(98,gl),(6,gl),(2,gl-6)]
    elif kind=='suv':
        pts=[(3,gl-18),(10,gl-22),(18,gl-24),(26,gl-38),(84,gl-38),(94,gl-24),(104,gl-20),(105,gl-6),(102,gl),(5,gl),(2,gl-8)]
    else:
        pts=[(4,gl-14),(14,gl-18),(30,gl-20),(40,gl-32),(70,gl-32),(82,gl-20),(100,gl-17),(102,gl-6),(98,gl),(6,gl),(2,gl-6)]
    m=cv.poly(pts,body,3)
    # height dome
    yy,xx=np.nonzero(m)
    for y_,x_ in zip(yy,xx):
        cv.hg[y_,x_]=3+2*math.sin((y_-(gl-38))/38*math.pi)
    # shading top highlight / bottom dark
    for y_,x_ in zip(yy,xx):
        t=(y_-(gl-38))/38
        if t>0.75: cv.c[y_,x_,:3]=dark
        elif t<0.42 and (x_+y_)%2==0: cv.c[y_,x_,:3]=light
    # windows
    if kind=='suv':
        wpts=[(29,gl-35),(82,gl-35),(90,gl-24),(22,gl-24)]
    else:
        wpts=[(42,gl-30),(68,gl-30),(78,gl-20),(33,gl-20)]
    cv.poly(wpts,C('#141a24'),1)
    cx=(wpts[0][0]+wpts[1][0])//2; cv.rect(cx,wpts[0][1],cx+2,gl-20,body,3)
    for k in range(6): cv.px(wpts[0][0]+4+k,wpts[0][1]+1+k,C('#3a4658'),1)
    # door lines, handle
    cv.rect(cx,gl-20,cx+1,gl-4,dark,2); cv.rect(cx-14,gl-16,cx-10,gl-15,mul(body,1.4),3.5)
    # lights
    cv.rect(98,gl-15,102,gl-11,C('#fff6e0'),3.5); cv.rect(3,gl-14,6,gl-10,C('#c02020'),3.5)
    if hazard:
        cv.emi(98,gl-15,102,gl-11,(0,0,0))
    # wheels
    for wx in (24,80):
        cv.ellipse(wx,gl,9,9,C('#101114'),2,dome=3); cv.ellipse(wx,gl,4,4,C('#7a7e86'),4,dome=1); cv.px(wx,gl,C('#2a2d33'),4)
        cv.rect(wx-10,gl-10,wx+11,gl-8,mul(body,0.45),2)
    if crashed:
        cv.poly([(96,gl-18),(103,gl-14),(102,gl-4),(94,gl-2)],mul(body,0.5),1)
        cv.line(84,gl-18,96,gl-10,C('#0a0a0a'),1)
    # snow on roof/hood/trunk
    top={}
    for x_ in range(W):
        col=np.nonzero(cv.c[:,x_,3])[0]
        if len(col): top[x_]=col.min()
    for x_,t in top.items():
        if t<gl-8:
            h=2+int(2*math.sin(x_*0.3))+ (2 if 40<x_<70 else 0)
            for k in range(h): cv.px(x_,t-1-k,SNOW[3] if k==h-1 else SNOW[2],5+k*0.4)
    a=cv.c.copy(); outline(cv.c)
    return cv,(4,gl-34,W-4,gl) 

def ambulance():
    W,H=124,58; cv=Cv(W,H); gl=H-10
    cv.rect(4,gl-40,92,gl,C('#e8eaee'),3); cv.poly([(92,gl-30),(108,gl-28),(120,gl-16),(120,gl-2),(92,gl)],C('#e8eaee'),3)
    cv.poly([(95,gl-27),(107,gl-26),(116,gl-16),(95,gl-16)],C('#141a24'),1)
    cv.rect(4,gl-20,120,gl-14,C('#d02020'),3.2); cv.rect(4,gl-4,120,gl,C('#9a9ca2'),2)
    cv.rect(40,gl-36,52,gl-24,C('#d02020'),3.3); cv.rect(44,gl-40+0,48,gl-20,C('#d02020'),3.3)
    cv.rect(44,gl-36,48,gl-24,C('#d02020'),3.3); cv.rect(40,gl-32,52,gl-28,C('#d02020'),3.3)
    cv.text(60,gl-36,'119',C('#d02020'),'Galmuri11-Bold',12,hg=3.5)
    cv.rect(12,gl-36,30,gl-24,C('#141a24'),1)
    cv.rect(84,gl-44,100,gl-40,C('#3a3d44'),4)
    cv.rect(84,gl-44,91,gl-41,C('#ff2020'),4.5); cv.rect(93,gl-44,100,gl-41,C('#2050ff'),4.5)
    for wx in (26,100):
        cv.ellipse(wx,gl,9,9,C('#101114'),2,dome=3); cv.ellipse(wx,gl,4,4,C('#7a7e86'),4,dome=1)
    for x_ in range(4,92):
        for k in range(R.randint(2,4)): cv.px(x_,gl-41-k,SNOW[2] if k else SNOW[3],5)
    outline(cv.c)
    return cv,(4,gl-40,120,gl)

def barricade():
    W,H=70,60; cv=Cv(W,H)
    # two A-frame legs + top boards with stripes; gap under (crouch)
    for lx in (6,58):
        cv.line(lx,H-1,lx+4,H-50,C('#6a6e76'),3); cv.line(lx+8,H-1,lx+4,H-50,C('#6a6e76'),3)
    for by in (H-52,H-40):
        cv.rect(2,by,68,by+9,C('#f0f0f0'),4)
        for k in range(2,68,10):
            cv.poly([(k,by),(k+5,by),(k+1,by+9),(k-4,by+9)],C('#d02020'),4.2)
    cv.text(10,H-52+0,'통제',C('#101010'),'Galmuri9',10,hg=4.5)
    snowcap(cv,2,68,H-52,3,5)
    # police tape drooping
    for x_ in range(0,W):
        y=H-26+int(4*math.sin(x_/W*math.pi))
        cv.px(x_,y,C('#f0d020') if (x_//4)%2 else C('#1a1a1a'),4)
    outline(cv.c)
    return cv,(2,H-52,68,H-31)

def barrel_frames():
    fr=[]
    for i in range(4):
        cv=Cv(28,44)
        cv.rect(4,16,24,44,C('#3a3226'),2); 
        for y in (18,28,38): cv.rect(4,y,24,y+2,C('#2a241c'),3)
        cv.rect(4,16,6,44,C('#5a4a36'),2.5)
        for k in range(10):
            fx=8+R.randint(0,12); fh=R.randint(6,16)
            for j in range(fh):
                t=j/fh
                col=lerp(C('#fff0a0'),C('#d02010'),t)
                cv.px(fx+int(1.5*math.sin(j*0.6+i+k)),15-j,col,emi=col)
        for k in range(6):
            cv.px(R.randint(6,22),R.randint(0,10),C('#ffb050'),emi=C('#ffb050'))
        outline(cv.c)
        fr.append(cv)
    return fr

def item(kind):
    cv=Cv(16,16)
    if kind=='water':
        cv.rect(5,3,10,15,C('#a8d4f0'),3); cv.rect(6,4,9,14,C('#6ab0e0'),3.5); cv.rect(6,1,9,3,C('#2060c0'),4); cv.rect(5,8,10,10,C('#ffffff'),3.6)
    elif kind=='bandage':
        cv.rect(2,5,14,12,C('#e8e4dc'),3); cv.rect(7,6,9,11,C('#d02020'),3.5); cv.rect(4,8,12,9,C('#d02020'),3.5)
    elif kind=='note':
        cv.rect(3,3,13,14,C('#d8d0b8'),2); 
        for y in range(5,13,2): cv.rect(4,y,12,y+1,C('#5a5a6a'),2.2)
    elif kind=='radio':
        cv.rect(3,5,13,15,C('#2a2d33'),3); cv.rect(10,0,11,5,C('#4a4d52'),3); cv.rect(5,7,11,10,C('#4af626'),3.5,emi=C('#2a9a18'))
    outline(cv.c)
    return cv

def save_sprite(cv,name):
    cv.save(OUT+name,strength=0.9)
    return dict(w=cv.w,h=cv.h)

if __name__=='__main__':
    meta={'world':dict(w=LW,h=WH,feet=FEET,low=LOW,slope0=SLOPE0,slope1=SLOPE1,water=WATER_X,goal=GOAL_X,ct0=150),'layers':[],'sprites':{}}
    layers=[('sky',0.03,sky),('far',0.15,far),('mid2',0.35,mid2),('mid1',0.6,mid1),('street',1.0,street),('fg',1.25,fg)]
    for name,p,fn in layers:
        cv=fn()
        files=cv.save(OUT+'L_'+name,strength=1.0,chunk=2048)
        meta['layers'].append(dict(name=name,p=p,w=cv.w,h=cv.h,chunks=files))
        Image.fromarray(cv.c,'RGBA').save('/tmp/L_'+name+'.png')
        print(name,cv.w)
    # props
    props={'car_white':car('#d8dade','sedan'),'car_dark':car('#2c3038','suv'),'car_taxi':car('#d88a2a','sedan',hazard=True,crashed=True),'car_red':car('#8a1c1c','sedan',crashed=True),
           'ambulance':ambulance(),'barricade':barricade()}
    for k,(cv,box) in props.items():
        meta['sprites'][k]=dict(save_sprite(cv,'S_'+k),solid=box)
        Image.fromarray(cv.c,'RGBA').resize((cv.w*4,cv.h*4),Image.NEAREST).save('/tmp/S_'+k+'.png')
    fr=barrel_frames()
    strip=Cv(28*4,44)
    for i,f in enumerate(fr): strip.blit(f,i*28,0)
    meta['sprites']['barrel']=dict(save_sprite(strip,'S_barrel'),frames=4,fw=28)
    for k in ('water','bandage','note','radio'):
        meta['sprites']['item_'+k]=save_sprite(item(k),'S_item_'+k)
    meta['lights']=LIGHTS
    meta['anims']=ANIMS
    json.dump(meta,open(OUT+'world.json','w'))
    print('lights',len(LIGHTS))
