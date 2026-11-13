import numpy as np, math, json
from PIL import Image
from lib import hx, outline
CW=CH=64
GROUND=61
def ramp(*h): return [np.array(hx(c),np.float32) for c in h]
PAL={
 'player':{
  'coat':ramp('#121419','#1f232c','#323846','#4b5466'),
  'pants':ramp('#191f2c','#243046','#324366','#435887'),
  'boot':ramp('#24180f','#3a281a','#523c28','#6c5236'),
  'skin':ramp('#6e4234','#9f624a','#c58a6a','#e0ae8c'),
  'hair':ramp('#0a0a0e','#15151b','#20202c','#2e2e3c'),
  'cap':ramp('#2a2c31','#40434a','#5b5f68','#7a7f8a'),
  'scarf':ramp('#520a0a','#8a1212','#c41a1a','#e8402c'),
  'pack':ramp('#262a19','#383e25','#4e5633','#677245'),
  'torch':ramp('#1c1e22','#363940','#575c66','#8a909c'),
  'glove':ramp('#141416','#222226','#34343a','#48484f'),
 },
 'inf_a':{ # hospital gown
  'coat':ramp('#3e4c56','#5c707e','#7e96a4','#a6bcc8'),
  'pants':ramp('#4c4038','#76665a','#988878','#b8a896'),
  'boot':ramp('#4c4038','#76665a','#988878','#b8a896'),
  'skin':ramp('#4f463e','#7a6c60','#9e8e7e','#bfae9c'),
  'hair':ramp('#16120e','#241e18','#342c24','#463c30'),
  'glove':ramp('#4f463e','#7a6c60','#9e8e7e','#bfae9c'),
 },
 'inf_b':{ # office worker
  'coat':ramp('#5e5c58','#8e8b84','#b8b4aa','#dcd8cc'),
  'pants':ramp('#18191d','#262a30','#383c45','#4c515c'),
  'boot':ramp('#0e0e10','#1a1a1e','#28282e','#38383f'),
  'skin':ramp('#5a4a40','#86705f','#a99280','#c9b29e'),
  'hair':ramp('#0c0b0a','#181614','#26221e','#36302a'),
  'glove':ramp('#5a4a40','#86705f','#a99280','#c9b29e'),
 },
 'inf_c':{ # beige long padding
  'coat':ramp('#423626','#66543c','#8c7756','#b29c74'),
  'pants':ramp('#1a1c22','#282c34','#3a3f4a','#4f5562'),
  'boot':ramp('#1c1612','#2e241c','#433628','#5a4a38'),
  'skin':ramp('#584a42','#836f62','#a59080','#c4ae9c'),
  'hair':ramp('#2a2018','#3e3024','#544232','#6c5642'),
  'glove':ramp('#584a42','#836f62','#a59080','#c4ae9c'),
 },
 'inf_d':{ # elderly cardigan (paralytic)
  'coat':ramp('#34262c','#523a44','#72545f','#93727e'),
  'pants':ramp('#2c2822','#443e34','#5e5648','#7a705e'),
  'boot':ramp('#121212','#1e1e1e','#2c2c2c','#3c3c3c'),
  'skin':ramp('#56483f','#7f6c5f','#a08c7c','#bea898'),
  'hair':ramp('#5a5856','#7e7c78','#a2a09a','#c4c2bc'),
  'glove':ramp('#56483f','#7f6c5f','#a08c7c','#bea898'),
 },
}
BLOOD=np.array(hx('#4a0c0c'),np.float32)

def P(a,ang,L): return (a[0]+L*math.sin(ang), a[1]+L*math.cos(ang))
def U(a,ang,L): return (a[0]+L*math.sin(ang), a[1]-L*math.cos(ang))

def build(p, kind):
    """p: pose dict -> list of parts (capsules) in local coords with hip at (0,0)"""
    g=lambda k,d=0.0: p.get(k,d)
    hip=(0.0,0.0)
    lean=g('lean'); 
    sho=U(hip,lean,15)
    neck=U(sho,lean+g('head')*0.5,2.5)
    head=U(neck,lean+g('head'),5)
    parts=[]
    def cap(a,b,r0,r1,z,mat,tag=None): parts.append(dict(a=a,b=b,r0=r0,r1=r1,z=z,mat=mat,tag=tag))
    # legs
    for side,z in (('B',-4),('F',4)):
        th=g('th'+side); sh=g('sh'+side)
        knee=P(hip,th,12); ank=P(knee,th+sh,12)
        foot=(ank[0]+4.5*math.cos(g('ft'+side,0)), ank[1]+0.5)
        zz=z-(1 if side=='B' else 0)
        cap(hip,knee,4.2,3.6,zz,'pants'); cap(knee,ank,3.4,2.8,zz,'pants')
        cap((ank[0]-0.5,ank[1]),foot,2.6,2.2,zz,'boot')
        if kind=='player' or kind in ('inf_c',):
            cap(hip,P(hip,th,10),5.6,5.0,zz+0.5,'coat','hem')  # long coat over thigh
        if kind=='inf_a':
            cap(hip,P(hip,th,8),5.2,4.6,zz+0.5,'coat','hem')
    # torso
    if kind=='player':
        bp=U((hip[0]-5*math.cos(lean),hip[1]-5*math.sin(lean)),lean,9)
        cap((hip[0]-4.5*math.cos(lean)+0.3, hip[1]-4-4.5*math.sin(lean)), bp,4.6,5.2,-3,'pack')
    cap(hip,sho,6.4,6.6,0,'coat','torso')
    # arms
    for side,z in (('B',-5),('F',5)):
        sa=g('ua'+side); la=g('la'+side)
        s0=(sho[0]+(0 if side=='F' else -0.5), sho[1]+1.5)
        elb=P(s0,sa,9.5); wr=P(elb,sa+la,9)
        cap(s0,elb,3.4,3.0,z,'coat','sleeve'); cap(elb,wr,3.0,2.6,z,'coat','sleeve')
        hand=P(wr,sa+la,2.0)
        cap(wr,hand,2.3,2.1,z+0.5,'glove' if kind=='player' else 'skin')
        if kind=='player' and side=='F' and p.get('torch',True):
            tip=P(hand,sa+la+1.5708*0.9,5.5)
            cap(hand,tip,1.6,1.9,z+1,'torch','torch')
    # head
    cap(neck,head,3.0,6.0,1,'skin','head')
    if kind=='player':
        s1=U(sho,lean,0.2); s2=U(sho,lean,2.6)
        cap(s1,s2,4.3,3.9,1.2,'scarf')
        tail=(s1[0]-5.5,s1[1]+5+p.get('scarfw',0))
        cap(s1,tail,2.0,1.6,-2,'scarf')
    return parts, dict(hip=hip,sho=sho,neck=neck,head=head,lean=lean,headang=lean+g('head'))

def raster(parts, ox, oy, rot=0.0, piv=(0,0)):
    W,H=CW,CH
    yy,xx=np.mgrid[0:H,0:W].astype(np.float32)
    px=xx+0.5; py=yy+0.5
    zb=np.full((H,W),-1e9,np.float32); mat=np.full((H,W),-1,np.int32)
    N=np.zeros((H,W,3),np.float32); T=np.zeros((H,W),np.float32); TAG=np.zeros((H,W),np.int32)
    cr,sr=math.cos(rot),math.sin(rot)
    def tr(p):
        x=p[0]-piv[0]; y=p[1]-piv[1]
        return (x*cr-y*sr+piv[0]+ox, x*sr+y*cr+piv[1]+oy)
    mats=[]; tags={'torso':1,'hem':2,'sleeve':3,'head':4,'torch':5}
    for i,pt in enumerate(parts):
        a=tr(pt['a']); b=tr(pt['b'])
        ab=np.array([b[0]-a[0],b[1]-a[1]],np.float32); L2=float(ab@ab)+1e-6
        t=np.clip(((px-a[0])*ab[0]+(py-a[1])*ab[1])/L2,0,1)
        cx=a[0]+ab[0]*t; cy=a[1]+ab[1]*t
        r=pt['r0']+(pt['r1']-pt['r0'])*t
        dx=px-cx; dy=py-cy; d2=dx*dx+dy*dy
        m=d2<r*r
        if not m.any(): continue
        h=np.sqrt(np.clip(r*r-d2,0,None))
        depth=pt['z']*3+h
        w=m&(depth>zb)
        zb[w]=depth[w]; mat[w]=i
        rr=np.maximum(r,1e-3)
        N[...,0][w]=(dx/rr)[w]; N[...,1][w]=(-dy/rr)[w]; N[...,2][w]=(h/rr)[w]
        T[w]=(t*math.sqrt(L2))[w]; TAG[w]=tags.get(pt['tag'],0)
    return mat,N,T,TAG,zb

KEY=np.array([0.35,0.55,0.76],np.float32); KEY/=np.linalg.norm(KEY)
def shade(parts,mat,N,T,TAG,zb,kind,extra=None):
    H,W=mat.shape
    out=np.zeros((H,W,4),np.uint8); nrm=np.zeros((H,W,4),np.uint8)
    pal=PAL[kind]
    a=mat>=0
    nl=np.linalg.norm(N,axis=-1,keepdims=True)+1e-6; Nn=N/nl
    v=0.30+0.42*Nn[...,2]+0.38*np.clip((Nn*KEY).sum(-1),0,1)
    idx=np.digitize(v,[0.52,0.72,0.92]).astype(np.int32)
    # quilting on coat torso / hem
    q=((TAG==1)|(TAG==2))&a
    if kind in ('player','inf_c'):
        line=(np.mod(T,4.5)<1.0)&q
        idx[line]-=1
        Nn[...,1][line]-=0.35
    for i,pt in enumerate(parts):
        m=mat==i
        if not m.any(): continue
        r=pal[pt['mat']] if pt['mat'] in pal else PAL['player'][pt['mat']]
        ii=idx[m]-(1 if pt['z']<0 else 0)
        ii=np.clip(ii,0,3)
        cols=np.stack(r)[ii]
        out[m,:3]=cols.astype(np.uint8); out[m,3]=255
    nn=Nn/ (np.linalg.norm(Nn,axis=-1,keepdims=True)+1e-6)
    nrm[...,:3]=((nn*0.5+0.5)*255).astype(np.uint8); nrm[...,3]=out[...,3]
    return out,nrm

def face(out,info,ox,oy,kind,rot=0.0,piv=(0,0),fr=0,hurt=False):
    """face details: eye, mouth, hair/beanie, drool"""
    hx_,hy_=info['head']; ang=info['headang']
    cr,sr=math.cos(rot),math.sin(rot)
    def tr(x,y):
        x-=piv[0]; y-=piv[1]
        return (int(round(x*cr-y*sr+piv[0]+ox-0.5)), int(round(x*sr+y*cr+piv[1]+oy-0.5)))
    def put(lx,ly,col):
        # lx forward, ly up in head frame
        x=hx_+lx*math.cos(ang)+ly*math.sin(ang); y=hy_+lx*math.sin(ang)-ly*math.cos(ang)
        X,Y=tr(x,y)
        if 0<=X<CW and 0<=Y<CH and out[Y,X,3]>0: out[Y,X,:3]=col
    pal=PAL[kind]
    hair=pal['hair']; 
    if kind=='player':
        cap=PAL['player']['cap']
        for ly in range(1,7):
            for lx in range(-6,6):
                if lx*lx+ (ly-0.5)**2 <= 36 and ly>=1.5:
                    put(lx,ly,cap[2] if ly>4 or lx>2 else cap[1])
        for lx in range(-6,6): put(lx,1.5,cap[3] if lx>0 else cap[2])  # fold band
        for lx in range(-6,-2):
            for ly in range(-3,1): put(lx,ly,hair[1])
        put(3,-0.3,np.array((20,16,16))); put(4.6,-2,pal['skin'][1]); 
        put(2,-3.5,pal['skin'][0]) # mouth hint
    else:
        for ly in range(1,6):
            for lx in range(-6,4):
                if lx*lx+(ly+1)**2<=30: put(lx,ly,hair[2] if (lx+ly+fr)%3 else hair[1])
        for lx in range(-6,-2):
            for ly in range(-4,1):
                if (lx+ly)%2==0: put(lx,ly,hair[1])
        put(3,0,np.array((70,10,10))); put(3,-0.9,np.array((120,30,26)))  # bloodshot eye
        put(4.5,-3,np.array((30,14,14))); put(3.5,-3.2,np.array((30,14,14)))  # open mouth
        put(4.5,-4.2,np.array((214,222,224))); 
        if fr%2==0: put(4.5,-5.2,np.array((196,206,210)))  # drool
        if kind=='inf_b':
            pass

def render_frame(kind,p,rot=0.0,extra=None,fr=0):
    parts,info=build(p,kind)
    # place: find lowest foot after rotation
    ox,oy=32,0
    mat,N,T,TAG,zb=raster(parts,ox,40,rot,(0,0))
    ys=np.nonzero(mat>=0)[0]
    shift=GROUND-ys.max() if len(ys) else 0
    oy=40+shift+p.get('lift',0)
    mat,N,T,TAG,zb=raster(parts,ox+p.get('dx',0),oy,rot,(0,0))
    out,nrm=shade(parts,mat,N,T,TAG,zb,kind)
    face(out,info,ox+p.get('dx',0),oy,kind,rot,(0,0),fr)
    if kind=='inf_b':
        rng=np.random.default_rng(3)
        m=(mat>=0)&(TAG==1)
        ys,xs=np.nonzero(m)
        for k in range(min(14,len(ys))):
            j=rng.integers(len(ys)); out[ys[j],xs[j],:3]=BLOOD
            if ys[j]+1<CH and out[ys[j]+1,xs[j],3]: out[ys[j]+1,xs[j],:3]=BLOOD*0.8
    outline(out)
    return out,nrm

S=math.sin; C=math.cos; PI=math.pi
def walk(i,n,amp=0.5,bend=0.85,arm=0.45,lean=0.06,la=0.35,limp=0.0,head=0.0,torch=True,uaF0=0.0):
    f=2*PI*i/n
    return dict(lean=lean,head=head,
        thF=amp*S(f), shF=-0.08-bend*max(0,C(f)), thB=-amp*S(f)*(1-limp), shB=-0.08-bend*max(0,-C(f))*(1-limp*0.6),
        ftF=0.15*S(f), ftB=-0.15*S(f),
        uaF=-arm*S(f)+uaF0, laF=la+0.15*max(0,S(f)), uaB=arm*S(f), laB=la+0.15*max(0,-S(f)),
        torch=torch, scarfw=1.5*S(f*2))

def player_anims():
    A={}
    A['idle']=[dict(lean=0.03+0.01*S(2*PI*i/6),head=0.02*S(2*PI*i/6),thF=0.1,shF=-0.12,thB=-0.08,shB=-0.05,uaF=0.25,laF=0.9,uaB=-0.05,laB=0.25,scarfw=S(2*PI*i/6)) for i in range(6)]
    A['walk']=[walk(i,8,uaF0=0.25) for i in range(8)]
    A['run']=[walk(i,8,amp=0.85,bend=1.5,arm=0.9,lean=0.22,la=1.25) for i in range(8)]
    A['crouch']=[dict(lean=0.55,head=-0.35,thF=1.35,shF=-2.25,thB=0.9,shB=-2.0,uaF=0.9,laF=0.7,uaB=0.4,laB=0.9,lift=0, scarfw=S(i*3)) for i in range(2)]
    A['crouchwalk']=[(lambda d:(d.update(dict(lean=0.55,head=-0.35)),d)[1])(dict(thF=1.1+0.35*S(2*PI*i/8),shF=-2.0-0.3*max(0,C(2*PI*i/8)),thB=1.1-0.35*S(2*PI*i/8),shB=-2.0-0.3*max(0,-C(2*PI*i/8)),uaF=0.9,laF=0.7,uaB=0.4+0.2*S(2*PI*i/8),laB=0.9)) for i in range(8)]
    A['jump']=[dict(lean=0.15,head=0.1,thF=1.0,shF=-1.4,thB=-0.15,shB=-0.9,uaF=2.2,laF=0.4,uaB=-0.6,laB=0.5,scarfw=-3),
               dict(lean=0.1,head=0.05,thF=0.5,shF=-0.6,thB=-0.25,shB=-0.4,uaF=1.4,laF=0.5,uaB=-0.9,laB=0.3,scarfw=3)]
    A['land']=[dict(lean=0.35,head=-0.2,thF=0.9,shF=-1.6,thB=0.5,shB=-1.4,uaF=0.6,laF=0.8,uaB=0.2,laB=0.5)]
    A['interact']=[dict(lean=0.35+0.25*t,head=-0.3*t,thF=0.6+0.5*t,shF=-0.8-0.9*t,thB=0.2+0.5*t,shB=-0.6-0.9*t,uaF=0.6+0.4*t,laF=0.3,uaB=0.0,laB=0.4,torch=True) for t in (0,0.5,1,0.6)]
    A['hurt']=[dict(lean=-0.3,head=-0.5,thF=0.4,shF=-0.4,thB=-0.3,shB=-0.3,uaF=1.8,laF=1.6,uaB=1.0,laB=1.4,dx=-2),
               dict(lean=-0.15,head=-0.3,thF=0.3,shF=-0.3,thB=-0.2,shB=-0.3,uaF=1.2,laF=1.4,uaB=0.6,laB=1.0,dx=-1)]
    A['splash']=[dict(lean=0.05,head=0.0,thF=0.3,shF=-0.2,thB=-0.2,shB=-0.1,uaF=-0.6,laF=1.6,uaB=0.0,laB=0.3,torch=False),
                 dict(lean=0.2,head=0.05,thF=0.5,shF=-0.2,thB=-0.35,shB=-0.1,uaF=1.0,laF=0.6,uaB=-0.4,laB=0.3,torch=False),
                 dict(lean=0.28,head=0.1,thF=0.6,shF=-0.3,thB=-0.4,shB=-0.1,uaF=1.75,laF=0.0,uaB=-0.6,laB=0.3,torch=False),
                 dict(lean=0.18,head=0.05,thF=0.45,shF=-0.25,thB=-0.3,shB=-0.1,uaF=1.4,laF=0.2,uaB=-0.3,laB=0.3,torch=False)]
    A['shove']=[dict(lean=-0.05,thF=0.3,shF=-0.3,thB=-0.2,shB=-0.2,uaF=0.6,laF=1.8,uaB=0.6,laB=1.8,torch=False),
                dict(lean=0.32,thF=0.7,shF=-0.4,thB=-0.5,shB=-0.1,uaF=1.55,laF=0.05,uaB=1.45,laB=0.05,torch=False),
                dict(lean=0.3,thF=0.65,shF=-0.4,thB=-0.45,shB=-0.1,uaF=1.5,laF=0.15,uaB=1.4,laB=0.15,torch=False),
                dict(lean=0.12,thF=0.4,shF=-0.3,thB=-0.25,shB=-0.2,uaF=0.9,laF=0.8,uaB=0.7,laB=0.8,torch=False)]
    A['dead']=[('rot',dict(lean=-0.2,head=-0.4,thF=0.3,shF=-0.6,thB=0.1,shB=-0.4,uaF=1.6,laF=1.0,uaB=1.2,laB=1.0),r) for r in (-0.3,-0.8,-1.3,-1.52)]
    return A

def inf_anims(kind):
    A={}
    hunch=0.42
    A['idle']=[dict(lean=hunch+0.04*S(2*PI*i/6),head=0.45+0.12*S(2*PI*i/6+1),thF=0.12,shF=-0.25,thB=-0.05,shB=-0.2,uaF=0.35+0.05*S(2*PI*i/6),laF=0.25,uaB=0.15,laB=0.15) for i in range(6)]
    A['walk']=[(lambda d:(d.update(dict(lean=hunch+0.06*S(4*PI*i/8),head=0.5+0.1*S(2*PI*i/8),uaF=0.45+0.15*S(2*PI*i/8),laF=0.3,uaB=0.2-0.15*S(2*PI*i/8),laB=0.2)),d)[1])(walk(i,8,amp=0.38,bend=0.6,limp=0.55)) for i in range(8)]
    A['run']=[(lambda d:(d.update(dict(lean=0.55,head=0.35,uaF=1.1+0.6*S(2*PI*i/8),laF=0.2,uaB=1.0-0.6*S(2*PI*i/8),laB=0.3)),d)[1])(walk(i,8,amp=0.85,bend=1.5,lean=0.55)) for i in range(8)]
    A['lunge']=[dict(lean=0.7,head=0.2,thF=0.9,shF=-0.6,thB=-0.7,shB=-0.4,uaF=1.6,laF=0.0,uaB=1.4,laB=0.1,lift=2),
                dict(lean=0.85,head=0.15,thF=0.5,shF=-0.3,thB=-0.9,shB=-0.6,uaF=1.75,laF=-0.1,uaB=1.6,laB=0.0,lift=3),
                dict(lean=0.8,head=0.15,thF=0.7,shF=-0.9,thB=-0.6,shB=-0.6,uaF=1.65,laF=0.0,uaB=1.55,laB=0.0,lift=1),
                dict(lean=0.6,head=0.3,thF=0.8,shF=-1.1,thB=-0.2,shB=-0.6,uaF=1.4,laF=0.3,uaB=1.2,laB=0.3)]
    A['bite']=[dict(lean=0.55+0.15*k,head=0.6+0.2*k,thF=0.5,shF=-0.6,thB=-0.4,shB=-0.3,uaF=1.3,laF=0.7,uaB=1.2,laB=0.8) for k in (0,1,0.5,1)]
    rng=np.random.default_rng(11)
    A['convulse']=[dict(lean=-0.35+0.15*rng.standard_normal(),head=-0.85+0.25*rng.standard_normal(),thF=0.25+0.2*rng.standard_normal(),shF=-0.5,thB=-0.25,shB=-0.4,
                        uaF=0.8+0.3*rng.standard_normal(),laF=2.2+0.3*rng.standard_normal(),uaB=0.6+0.3*rng.standard_normal(),laB=2.1,dx=int(rng.integers(-2,3))) for i in range(6)]
    A['stagger']=[dict(lean=-0.3,head=-0.5,thF=0.3,shF=-0.3,thB=-0.5,shB=-0.3,uaF=1.0,laF=1.0,uaB=0.6,laB=1.2,dx=-2),
                  dict(lean=-0.1,head=-0.2,thF=0.5,shF=-0.6,thB=-0.3,shB=-0.4,uaF=0.6,laF=0.6,uaB=0.3,laB=0.8,dx=-1),
                  dict(lean=0.2,head=0.2,thF=0.3,shF=-0.6,thB=-0.1,shB=-0.4,uaF=0.4,laF=0.4,uaB=0.2,laB=0.4)]
    if kind=='inf_d':
        lie=dict(lean=0.0,head=0.3,thF=0.6,shF=-0.9,thB=0.3,shB=-0.7,uaF=0.9,laF=1.2,uaB=0.3,laB=0.6)
        A['lie']=[('rot',dict(lie,head=0.3+0.15*S(i*2.1),uaF=0.9+0.2*S(i*1.3)),1.45) for i in range(4)]
        A['rise']=[('rot',dict(lean=0.5,head=0.4,thF=1.2,shF=-2.0,thB=0.9,shB=-1.9,uaF=1.2,laF=0.5,uaB=0.8,laB=0.5),r) for r in (1.2,0.8,0.4)]+[('rot',dict(lean=0.6,head=0.4,thF=1.2,shF=-2.0,thB=0.9,shB=-1.9,uaF=1.5,laF=0.3,uaB=1.2,laB=0.3),0.0)]
        A['crawl']=[('rot',dict(lean=0.3,head=0.6,thF=1.2+0.3*S(2*PI*i/6),shF=-1.8,thB=1.0-0.3*S(2*PI*i/6),shB=-1.8,uaF=1.6+0.4*S(2*PI*i/6),laF=0.2,uaB=1.4-0.4*S(2*PI*i/6),laB=0.2),0.7) for i in range(6)]
    return A

def sheet(kind,anims,fps):
    rows=list(anims.keys()); ncol=max(len(v) for v in anims.values())
    A=np.zeros((CH*len(rows),CW*ncol,4),np.uint8); Nm=np.zeros_like(A)
    meta={}
    for r,name in enumerate(rows):
        for c,fr in enumerate(anims[name]):
            rot=0.0
            if isinstance(fr,tuple): _,fr,rot=fr
            o,n=render_frame(kind,fr,rot,fr=c)
            A[r*CH:(r+1)*CH,c*CW:(c+1)*CW]=o; Nm[r*CH:(r+1)*CH,c*CW:(c+1)*CW]=n
        meta[name]={'row':r,'n':len(anims[name]),'fps':fps.get(name,8)}
    return A,Nm,meta

if __name__=='__main__':
    import sys
    out='/workspace/seoul_survival/webgl/public/px/'
    allmeta={'cell':[CW,CH],'sheets':{}}
    FPS={'idle':5,'walk':10,'run':14,'crouch':3,'crouchwalk':9,'jump':1,'land':1,'interact':10,'hurt':10,'splash':12,'shove':14,'dead':8,'lunge':12,'bite':10,'convulse':16,'stagger':10,'lie':3,'rise':8,'crawl':6}
    jobs=[('player',player_anims())]+[(k,inf_anims(k)) for k in ('inf_a','inf_b','inf_c','inf_d')]
    for kind,anims in jobs:
        A,Nm,meta=sheet(kind,anims,FPS)
        Image.fromarray(A,'RGBA').save(out+kind+'_a.webp','WEBP',lossless=True,exact=True)
        Image.fromarray(Nm,'RGBA').save(out+kind+'_n.webp','WEBP',lossless=True,exact=True)
        allmeta['sheets'][kind]={'w':A.shape[1],'h':A.shape[0],'anims':meta}
        # preview
        Image.fromarray(A,'RGBA').resize((A.shape[1]*3,A.shape[0]*3),Image.NEAREST).save('/tmp/prev_'+kind+'.png')
    json.dump(allmeta,open(out+'chars.json','w'))
    print('chars ok')
