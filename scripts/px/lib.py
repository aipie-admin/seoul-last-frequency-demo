import numpy as np, math, random
from PIL import Image, ImageFont, ImageDraw
FONT_DIR='/workspace/seoul_survival/webgl/node_modules/galmuri/dist/'
BAYER=np.array([[0,8,2,10],[12,4,14,6],[3,11,1,9],[15,7,13,5]],np.float32)/16.0
def hx(s):
    s=s.lstrip('#'); return (int(s[0:2],16),int(s[2:4],16),int(s[4:6],16))
def mul(c,f): return tuple(int(max(0,min(255,v*f))) for v in c[:3])
def lerp(a,b,t): return tuple(int(a[i]+(b[i]-a[i])*t) for i in range(3))
_fonts={}
def font(name='Galmuri11-Bold',size=12):
    k=(name,size)
    if k not in _fonts: _fonts[k]=ImageFont.truetype(FONT_DIR+name+'.ttf',size)
    return _fonts[k]

class Cv:
    """albedo RGBA + height + emissive RGB, y-down pixel canvas"""
    def __init__(s,w,h):
        s.w,s.h=w,h
        s.c=np.zeros((h,w,4),np.uint8)
        s.hg=np.zeros((h,w),np.float32)
        s.e=np.zeros((h,w,3),np.uint8)
    def _clip(s,x0,y0,x1,y1):
        x0=max(0,int(x0)); y0=max(0,int(y0)); x1=min(s.w,int(x1)); y1=min(s.h,int(y1))
        return x0,y0,x1,y1
    def rect(s,x0,y0,x1,y1,col,hg=None,emi=None,a=255):
        x0,y0,x1,y1=s._clip(x0,y0,x1,y1)
        if x1<=x0 or y1<=y0: return
        s.c[y0:y1,x0:x1,:3]=col[:3]; s.c[y0:y1,x0:x1,3]=a
        if hg is not None: s.hg[y0:y1,x0:x1]=hg
        if emi is not None: s.e[y0:y1,x0:x1]=emi[:3]
        elif col is not None: s.e[y0:y1,x0:x1]=0
    def emi(s,x0,y0,x1,y1,col):
        x0,y0,x1,y1=s._clip(x0,y0,x1,y1)
        if x1>x0 and y1>y0: s.e[y0:y1,x0:x1]=col[:3]
    def px(s,x,y,col,hg=None,emi=None):
        x=int(x); y=int(y)
        if 0<=x<s.w and 0<=y<s.h:
            s.c[y,x,:3]=col[:3]; s.c[y,x,3]=255
            if hg is not None: s.hg[y,x]=hg
            if emi is not None: s.e[y,x]=emi[:3]
    def addh(s,x0,y0,x1,y1,dh):
        x0,y0,x1,y1=s._clip(x0,y0,x1,y1)
        if x1>x0 and y1>y0: s.hg[y0:y1,x0:x1]+=dh
    def shade(s,x0,y0,x1,y1,f):
        x0,y0,x1,y1=s._clip(x0,y0,x1,y1)
        if x1>x0 and y1>y0:
            s.c[y0:y1,x0:x1,:3]=np.clip(s.c[y0:y1,x0:x1,:3].astype(np.float32)*f,0,255).astype(np.uint8)
    def dgrad(s,x0,y0,x1,y1,c0,c1,vertical=True,a=255,steps=6,hg=None):
        """ordered-dither gradient quantized to `steps` tones"""
        x0,y0,x1,y1=s._clip(x0,y0,x1,y1)
        if x1<=x0 or y1<=y0: return
        hh=y1-y0; ww=x1-x0
        yy,xx=np.mgrid[y0:y1,x0:x1]
        t=((yy-y0)/max(1,hh-1)) if vertical else ((xx-x0)/max(1,ww-1))
        tq=np.floor(t*(steps-1)+BAYER[yy%4,xx%4])/(steps-1)
        tq=np.clip(tq,0,1)[...,None]
        c0=np.array(c0[:3],np.float32); c1=np.array(c1[:3],np.float32)
        s.c[y0:y1,x0:x1,:3]=(c0+(c1-c0)*tq).astype(np.uint8); s.c[y0:y1,x0:x1,3]=a
        if hg is not None: s.hg[y0:y1,x0:x1]=hg
    def ditherfill(s,x0,y0,x1,y1,col,level,hg=None):
        """sparse ordered dither of col over region (level 0..1)"""
        x0,y0,x1,y1=s._clip(x0,y0,x1,y1)
        if x1<=x0 or y1<=y0: return
        yy,xx=np.mgrid[y0:y1,x0:x1]
        m=BAYER[yy%4,xx%4]<level
        sub=s.c[y0:y1,x0:x1]
        sub[m,:3]=col[:3]; sub[m,3]=255
        if hg is not None: s.hg[y0:y1,x0:x1][m]=hg
    def noise(s,x0,y0,x1,y1,cols,rng,scale=1.0,hgv=None):
        """speckle texture: random choose between cols weighted"""
        x0,y0,x1,y1=s._clip(x0,y0,x1,y1)
        if x1<=x0 or y1<=y0: return
        r=rng.random((y1-y0,x1-x0))
        sub=s.c[y0:y1,x0:x1]
        n=len(cols)
        for i,(col,p) in enumerate(cols):
            m=r<p
            sub[m,:3]=col[:3]; sub[m,3]=255
            if hgv is not None: s.hg[y0:y1,x0:x1][m]+=hgv[i]
            r=np.where(m,2,r-p)
    def text(s,x,y,txt,col,fname='Galmuri11-Bold',size=12,emi=None,hg=None):
        f=font(fname,size)
        bb=f.getbbox(txt)
        W=bb[2]+2; H=bb[3]+2
        im=Image.new('L',(W,H),0); d=ImageDraw.Draw(im); d.fontmode='1'
        d.text((0,0),txt,fill=255,font=f)
        m=np.asarray(im)>127
        ys,xs=np.nonzero(m)
        for yy,xx in zip(ys,xs):
            s.px(x+xx,y+yy-bb[1],col,hg,emi)
        return bb[2]-bb[0]
    def textw(s,txt,fname='Galmuri11-Bold',size=12):
        bb=font(fname,size).getbbox(txt); return bb[2]-bb[0]
    def line(s,x0,y0,x1,y1,col,hg=None,emi=None):
        n=int(max(abs(x1-x0),abs(y1-y0)))+1
        for i in range(n):
            t=i/max(1,n-1); s.px(round(x0+(x1-x0)*t),round(y0+(y1-y0)*t),col,hg,emi)
    def poly(s,pts,col,hg=None,emi=None):
        im=Image.new('L',(s.w,s.h),0); ImageDraw.Draw(im).polygon([(int(a),int(b)) for a,b in pts],fill=255)
        m=np.asarray(im)>0
        s.c[m,:3]=col[:3]; s.c[m,3]=255
        if hg is not None: s.hg[m]=hg
        if emi is not None: s.e[m]=emi[:3]
        else: s.e[m]=0
        return m
    def ellipse(s,cx,cy,rx,ry,col,hg=None,emi=None,dome=0):
        x0,y0,x1,y1=s._clip(cx-rx-1,cy-ry-1,cx+rx+2,cy+ry+2)
        if x1<=x0 or y1<=y0: return
        yy,xx=np.mgrid[y0:y1,x0:x1]
        d=((xx+.5-cx)/max(rx,.5))**2+((yy+.5-cy)/max(ry,.5))**2
        m=d<=1
        s.c[y0:y1,x0:x1][m,:3]=col[:3]; s.c[y0:y1,x0:x1][m,3]=255
        if hg is not None: s.hg[y0:y1,x0:x1][m]=hg+dome*np.sqrt(np.clip(1-d[m],0,1))
        if emi is not None: s.e[y0:y1,x0:x1][m]=emi[:3]
        else: s.e[y0:y1,x0:x1][m]=0
    def blit(s,o,x,y):
        """composite another Cv (alpha>0 overwrite)"""
        x=int(x); y=int(y)
        sx0=max(0,-x); sy0=max(0,-y); dx0=max(0,x); dy0=max(0,y)
        w=min(o.w-sx0,s.w-dx0); h=min(o.h-sy0,s.h-dy0)
        if w<=0 or h<=0: return
        src=o.c[sy0:sy0+h,sx0:sx0+w]; m=src[...,3]>0
        s.c[dy0:dy0+h,dx0:dx0+w][m]=src[m]
        s.hg[dy0:dy0+h,dx0:dx0+w][m]=o.hg[sy0:sy0+h,sx0:sx0+w][m]
        s.e[dy0:dy0+h,dx0:dx0+w][m]=o.e[sy0:sy0+h,sx0:sx0+w][m]
    def normals(s,strength=1.0,nrm_override=None):
        h=s.hg
        gx=np.zeros_like(h); gy=np.zeros_like(h)
        gx[:,1:-1]=(h[:,2:]-h[:,:-2])*0.5; gy[1:-1,:]=(h[2:,:]-h[:-2,:])*0.5
        a=s.c[...,3]>0
        # stop gradients across alpha edges (avoid huge rims)
        gx=np.clip(gx,-3,3); gy=np.clip(gy,-3,3)
        nx=-gx*strength; ny=gy*strength; nz=np.ones_like(h)
        l=np.sqrt(nx*nx+ny*ny+nz*nz)
        n=np.stack([nx/l,ny/l,nz/l],-1)
        out=np.zeros((s.h,s.w,4),np.uint8)
        out[...,:3]=((n*0.5+0.5)*255).astype(np.uint8); out[...,3]=s.c[...,3]
        return out
    def save(s,path,strength=1.0,emissive=True,nrm=True,chunk=None):
        files=[]
        def sv(arr,p,mode):
            Image.fromarray(arr,mode).save(p,'WEBP',lossless=True,quality=100,method=4,exact=True)
        N=s.normals(strength) if nrm else None
        E=None
        if emissive:
            E=np.zeros((s.h,s.w,4),np.uint8); E[...,:3]=s.e; E[...,3]=255
        if chunk is None: chunk=s.w
        i=0
        for x0 in range(0,s.w,chunk):
            x1=min(s.w,x0+chunk); suf=f'_{i}' if chunk<s.w else ''
            sv(np.ascontiguousarray(s.c[:,x0:x1]),f'{path}{suf}_a.webp','RGBA')
            if nrm: sv(np.ascontiguousarray(N[:,x0:x1]),f'{path}{suf}_n.webp','RGBA')
            if emissive: sv(np.ascontiguousarray(E[:,x0:x1]),f'{path}{suf}_e.webp','RGBA')
            files.append({'x':x0,'w':x1-x0}); i+=1
        return files

def outline(c, col_fn=None, alpha_src=None):
    """selective outline: alpha pixels touching transparency get darkened"""
    a=c[...,3]>0
    edge=np.zeros_like(a)
    edge[1:,:]|=~a[:-1,:]; edge[:-1,:]|=~a[1:,:]; edge[:,1:]|=~a[:,:-1]; edge[:,:-1]|=~a[:,1:]
    edge&=a
    c[edge,:3]=(c[edge,:3].astype(np.float32)*0.45).astype(np.uint8)
    return edge
