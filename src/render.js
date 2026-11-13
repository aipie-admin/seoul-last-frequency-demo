// Pixel-perfect 2D renderer on Three.js: internal low-res RT, normal-mapped lit sprites,
// parallax layers, volumetric light shafts, fog sheets, snow, water, bloom + grade composite.
import * as THREE from 'three';

export const MAXL = 20;
const BAYER = `
float bayer4(vec2 p){ ivec2 i=ivec2(mod(p,4.0)); int idx=i.x+i.y*4;
  int m[16]=int[16](0,8,2,10,12,4,14,6,3,11,1,9,15,7,13,5); return (float(m[idx])+0.5)/16.0; }
float hash12(vec2 p){ vec3 p3=fract(vec3(p.xyx)*.1031); p3+=dot(p3,p3.yzx+33.33); return fract((p3.x+p3.y)*p3.z); }
float vnoise(vec2 p){ vec2 i=floor(p), f=fract(p); f=f*f*(3.0-2.0*f);
  return mix(mix(hash12(i),hash12(i+vec2(1,0)),f.x),mix(hash12(i+vec2(0,1)),hash12(i+vec2(1,1)),f.x),f.y); }
float fbm(vec2 p){ float a=0.5,s=0.0; for(int i=0;i<4;i++){ s+=a*vnoise(p); p*=2.03; a*=0.5;} return s; }
`;
const LIGHT_UNI = `
uniform vec4 uLP[${MAXL}]; // x,y screen(y-down), z height, w radius
uniform vec4 uLC[${MAXL}]; // rgb, intensity
uniform vec4 uLD[${MAXL}]; // dir.xy (y-down), cosCone, cone flag (0 omni,1 spot)
uniform int uNL;
uniform vec2 uRes;
`;
const LIGHT_FN = `
vec3 lightAt(vec2 sp, vec3 n, float rim){
  vec3 acc=vec3(0.0);
  for(int i=0;i<${MAXL};i++){
    if(i>=uNL) break;
    vec4 P=uLP[i]; vec4 C=uLC[i]; vec4 D=uLD[i];
    vec2 d=P.xy-sp; float dist=length(d);
    if(dist>P.w) continue;
    float att=1.0-dist/P.w; att*=att;
    vec3 L=normalize(vec3(d.x,-d.y,P.z));
    float nd=max(dot(n,L),0.0)*0.85+0.15;
    float spot=1.0;
    if(D.w>0.5){ vec2 tf=normalize(-d+vec2(0.0001)); spot=smoothstep(D.z,D.z+0.12,dot(tf,D.xy)); spot=max(spot,0.18*step(dist,P.w*0.25)); }
    acc+=C.rgb*C.a*att*nd*spot;
  }
  return acc;
}
`;

const spriteVS = `
varying vec2 vUv;
uniform vec4 uUvRect; // u0,v0,du,dv
uniform float uFlip;
void main(){
  vec2 uv=uv; if(uFlip<0.0) uv.x=1.0-uv.x;
  vUv=uUvRect.xy+uv*uUvRect.zw;
  gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0);
}`;
const spriteFS = `
precision highp float;
varying vec2 vUv;
uniform sampler2D uMap, uNrm, uEmi;
uniform float uHasN, uHasE, uFlip, uLayerLight, uEmiStr, uFogAmt, uFlash, uAlpha, uTime, uBands, uDark;
uniform vec3 uAmb, uFogCol, uTint;
${LIGHT_UNI}
${BAYER}
${LIGHT_FN}
void main(){
  vec4 a=texture2D(uMap,vUv);
  if(a.a<0.5) discard;
  vec3 n=vec3(0.0,0.0,1.0);
  if(uHasN>0.5){ n=texture2D(uNrm,vUv).xyz*2.0-1.0; n.x*=uFlip; n=normalize(n); }
  vec2 sp=vec2(gl_FragCoord.x, uRes.y-gl_FragCoord.y);
  vec3 lit=uAmb*(0.75+0.25*n.z);
  if(uLayerLight>0.0) lit+=lightAt(sp,n,0.0)*uLayerLight;
  // banded + ordered dither -> pixel art friendly light steps
  float b=bayer4(gl_FragCoord.xy);
  vec3 lq=floor(lit*uBands+b)/uBands;
  vec3 col=a.rgb*a.rgb*lq*uTint; // albedo to ~linear
  if(uHasE>0.5){ vec3 e=texture2D(uEmi,vUv).rgb; col+=e*e*uEmiStr; }
  col=mix(col,uFogCol,uFogAmt);
  col=mix(col,vec3(1.0,0.25,0.2),uFlash);
  col*=uDark;
  gl_FragColor=vec4(col,uAlpha);
}`;

export function makeTex(img, opts = {}) {
  const t = new THREE.Texture(img);
  t.magFilter = THREE.NearestFilter; t.minFilter = THREE.NearestFilter; t.generateMipmaps = false;
  t.flipY = false; t.colorSpace = THREE.NoColorSpace; t.needsUpdate = true;
  t.wrapS = t.wrapT = THREE.ClampToEdgeWrapping;
  return t;
}

export class Renderer {
  constructor(canvas) {
    this.canvas = canvas;
    this.gl = new THREE.WebGLRenderer({ canvas, antialias: false, alpha: false, powerPreference: 'high-performance' });
    this.gl.setPixelRatio(1);
    this.gl.autoClear = false;
    this.H = 360; this.W = 640; this.S = 2;
    this.scene = new THREE.Scene();
    this.cam = new THREE.OrthographicCamera(0, 640, 0, 360, -1000, 1000);
    this.lightU = { uLP: { value: Array.from({ length: MAXL }, () => new THREE.Vector4()) }, uLC: { value: Array.from({ length: MAXL }, () => new THREE.Vector4()) }, uLD: { value: Array.from({ length: MAXL }, () => new THREE.Vector4()) }, uNL: { value: 0 }, uRes: { value: new THREE.Vector2(640, 360) } };
    this.time = { value: 0 };
    this.amb = { value: new THREE.Color(0.16, 0.19, 0.30) };
    this.quality = 'high';
    this.frame = 0;
    this.post = {};
    this.resize();
    this.buildPost();
  }
  resize() {
    const dpr = Math.min(window.devicePixelRatio || 1, 3);
    const iw = window.innerWidth * dpr, ih = window.innerHeight * dpr;
    this.H = 360;
    let W = Math.round((iw / ih) * this.H / 2) * 2; W = Math.max(480, Math.min(720, W));
    this.W = W;
    this.S = Math.max(1, Math.floor(Math.min(iw / W, ih / this.H)));
    const cw = W * this.S, ch = this.H * this.S;
    this.gl.setSize(cw, ch, false);
    this.canvas.style.width = (cw / dpr) + 'px'; this.canvas.style.height = (ch / dpr) + 'px';
    this.cam.left = 0; this.cam.right = W; this.cam.top = 0; this.cam.bottom = this.H; this.cam.updateProjectionMatrix();
    this.lightU.uRes.value.set(W, this.H);
    if (this.rt) this.allocRT();
  }
  allocRT() {
    const o = { type: THREE.HalfFloatType, magFilter: THREE.NearestFilter, minFilter: THREE.NearestFilter, depthBuffer: false };
    this.rt?.dispose(); this.rtB1?.dispose(); this.rtB2?.dispose();
    this.rt = new THREE.WebGLRenderTarget(this.W, this.H, o);
    const lo = { type: THREE.HalfFloatType, magFilter: THREE.LinearFilter, minFilter: THREE.LinearFilter, depthBuffer: false };
    this.rtB1 = new THREE.WebGLRenderTarget(this.W >> 1, this.H >> 1, lo);
    this.rtB2 = new THREE.WebGLRenderTarget(this.W >> 1, this.H >> 1, lo);
    if (this.post.comp) { this.post.comp.uniforms.uRes.value.set(this.W, this.H); }
  }
  spriteMat({ map, nrm, emi, layerLight = 1, emiStr = 1, fogAmt = 0, bands = 6 }) {
    const m = new THREE.ShaderMaterial({
      vertexShader: spriteVS, fragmentShader: spriteFS, transparent: false, depthTest: false, depthWrite: false, side: THREE.DoubleSide,
      uniforms: {
        uMap: { value: map }, uNrm: { value: nrm || map }, uEmi: { value: emi || map },
        uHasN: { value: nrm ? 1 : 0 }, uHasE: { value: emi ? 1 : 0 }, uFlip: { value: 1 }, uUvRect: { value: new THREE.Vector4(0, 0, 1, 1) },
        uLayerLight: { value: layerLight }, uEmiStr: { value: emiStr }, uFogAmt: { value: fogAmt }, uFogCol: { value: new THREE.Color(0.05, 0.06, 0.10) },
        uFlash: { value: 0 }, uAlpha: { value: 1 }, uTime: this.time, uBands: { value: bands }, uAmb: this.amb, uTint: { value: new THREE.Color(1, 1, 1) }, uDark: { value: 1 },
        ...this.lightU,
      },
    });
    return m;
  }
  quad(w, h, mat, order) {
    const g = new THREE.PlaneGeometry(w, h);
    const mesh = new THREE.Mesh(g, mat); mesh.renderOrder = order; mesh.frustumCulled = false;
    this.scene.add(mesh); return mesh;
  }
  // full-screen procedural layers ---------------------------------------------------------
  fsQuad(frag, uniforms, order, blending = THREE.NormalBlending) {
    const mat = new THREE.ShaderMaterial({
      vertexShader: `varying vec2 vUv; void main(){ vUv=uv; gl_Position=vec4(position.xy*2.0,0.0,1.0);} `,
      fragmentShader: frag, uniforms: { ...uniforms, ...this.lightU, uTime: this.time }, transparent: true, depthTest: false, depthWrite: false, blending,
    });
    const m = new THREE.Mesh(new THREE.PlaneGeometry(1, 1), mat); m.renderOrder = order; m.frustumCulled = false; this.scene.add(m); return m;
  }
  fogSheet(order, { color, density, y0, y1, speed, scale, par }) {
    return this.fsQuad(`
      precision highp float; varying vec2 vUv; uniform float uTime; uniform vec3 uCol; uniform float uDen,uY0,uY1,uSpeed,uScale,uCamX,uCamY,uPar,uOn;
      ${LIGHT_UNI} ${BAYER}
      void main(){
        vec2 sp=vec2(gl_FragCoord.x, uRes.y-gl_FragCoord.y);
        float wy=sp.y+uCamY;
        float band=smoothstep(uY0-40.0,uY0,wy)*(1.0-smoothstep(uY1,uY1+60.0,wy));
        vec2 q=vec2((sp.x+uCamX*uPar)/uScale + uTime*uSpeed, wy/(uScale*0.35));
        float n=fbm(q+vec2(0.0,uTime*0.03))*1.3-0.25;
        float a=clamp(n*band*uDen,0.0,1.0);
        // light scatter in fog
        vec3 sc=vec3(0.0);
        for(int i=0;i<${MAXL};i++){ if(i>=uNL) break; vec2 d=uLP[i].xy-sp; float r=uLP[i].w*1.1; float t=1.0-clamp(length(d)/r,0.0,1.0); sc+=uLC[i].rgb*uLC[i].a*t*t*0.9; }
        float b=bayer4(gl_FragCoord.xy);
        a=min(a,0.5)*uOn;
        gl_FragColor=vec4(uCol+min(sc*0.12,vec3(0.35)), a);
      }`, { uCol: { value: new THREE.Color(color) }, uDen: { value: density }, uY0: { value: y0 }, uY1: { value: y1 }, uSpeed: { value: speed }, uScale: { value: scale }, uCamX: { value: 0 }, uCamY: { value: 0 }, uPar: { value: par }, uOn: { value: 1 } }, order);
  }
  volumetrics(order) {
    return this.fsQuad(`
      precision highp float; varying vec2 vUv; uniform float uTime; uniform float uOn, uCamX;
      ${LIGHT_UNI} ${BAYER}
      void main(){
        vec2 sp=vec2(gl_FragCoord.x, uRes.y-gl_FragCoord.y);
        vec3 acc=vec3(0.0);
        for(int i=0;i<${MAXL};i++){
          if(i>=uNL) break;
          vec4 D=uLD[i]; if(D.w<0.5) continue;
          vec4 P=uLP[i]; vec2 d=sp-P.xy; float dist=length(d); float R=P.w*1.15;
          if(dist>R) continue;
          float c=dot(normalize(d+vec2(0.0001)),D.xy);
          float cone=smoothstep(D.z-0.02,D.z+0.10,c);
          float fall=pow(1.0-dist/R,1.6);
          float dust=0.55+0.45*fbm(vec2((sp.x+uCamX)*0.035, sp.y*0.05-uTime*0.6));
          acc+=uLC[i].rgb*uLC[i].a*cone*fall*dust;
        }
        float b=bayer4(gl_FragCoord.xy);
        acc=acc*0.085;
        gl_FragColor=vec4(acc*uOn,1.0);
      }`, { uOn: { value: 1 }, uCamX: { value: 0 } }, order, THREE.AdditiveBlending);
  }
  water(order, world) {
    return this.fsQuad(`
      precision highp float; varying vec2 vUv; uniform float uTime; uniform float uCamX,uCamY,uX0,uY0,uRain;
      ${LIGHT_UNI} ${BAYER}
      void main(){
        vec2 sp=vec2(gl_FragCoord.x, uRes.y-gl_FragCoord.y);
        vec2 w=sp+vec2(uCamX,uCamY);
        if(w.x<uX0 || w.y<uY0-2.0) discard;
        float depth=max(0.0,w.y-uY0);
        // side-view water body: dark below a thin horizontal surface
        vec3 base=mix(vec3(0.06,0.10,0.14),vec3(0.010,0.018,0.03),clamp(depth/50.0,0.0,1.0));
        float wave=sin(w.x*0.11+uTime*0.7)*1.2 + sin(w.x*0.31+uTime*1.1)*0.5;
        float surface=1.0-smoothstep(0.0,3.0,abs((w.y-uY0)-wave));
        vec3 col=base;
        col=mix(col,vec3(0.28,0.34,0.40),surface*0.85);
        // horizontal caustics (profile bands, not top-down rings)
        float cau=step(0.7,vnoise(vec2(w.x*0.04+uTime*0.15, floor((w.y-uY0)/3.0)*0.7)));
        col+=cau*vec3(0.04,0.06,0.08)*(1.0-clamp(depth/40.0,0.0,1.0));
        for(int i=0;i<${MAXL};i++){ if(i>=uNL) break;
          vec4 P=uLP[i]; float dx=abs(sp.x-P.x);
          float f=clamp(1.0-dx/280.0,0.0,1.0)*clamp(1.0-abs(P.y-(uY0-uCamY))/80.0,0.0,1.0);
          col+=uLC[i].rgb*uLC[i].a*f*0.18*(1.0-clamp(depth/50.0,0.0,0.85))*surface;
        }
        // leaves drifting on the surface line
        float lf=hash12(floor(vec2(w.x-uTime*1.4,uY0)*vec2(0.35,1.0)));
        if(lf>0.988 && abs(w.y-uY0-wave)<2.5) col=mix(vec3(0.55,0.38,0.06),vec3(0.5,0.12,0.05),step(0.995,lf))*0.7;
        // rain hits the surface only
        float drop=step(0.96,hash12(floor(vec2(w.x*0.5,floor(uTime*6.0)))))*uRain;
        if(drop>0.5 && abs(w.y-uY0)<3.0) col+=vec3(0.16,0.18,0.22);
        float b=bayer4(gl_FragCoord.xy); col=floor(col*24.0+b)/24.0;
        gl_FragColor=vec4(col,1.0);
      }`, { uCamX: { value: 0 }, uCamY: { value: 0 }, uX0: { value: world.water }, uY0: { value: world.low + 6 }, uRain: { value: 0 } }, order);
  }
  leaves(order, count, par, size, speed, bright) {
    const g = new THREE.BufferGeometry();
    const a = new Float32Array(count * 4);
    for (let i = 0; i < count; i++) { a[i * 4] = Math.random(); a[i * 4 + 1] = Math.random(); a[i * 4 + 2] = Math.random(); a[i * 4 + 3] = Math.random(); }
    g.setAttribute('position', new THREE.BufferAttribute(new Float32Array(count * 3), 3));
    g.setAttribute('seed', new THREE.BufferAttribute(a, 4));
    const mat = new THREE.ShaderMaterial({
      vertexShader: `
        attribute vec4 seed; uniform float uTime,uCamX,uCamY,uPar,uSize,uSpeed,uWind,uRain; varying vec3 vC; varying float vA; varying float vFlip;
        ${LIGHT_UNI}
        void main(){
          float W=uRes.x+60.0, H=uRes.y+40.0;
          float t=uTime*uSpeed*(0.45+0.55*seed.z);
          float gust=sin(uTime*0.12+seed.w*3.0)*0.5+0.5;
          float sway=sin(uTime*(0.32+seed.w*0.35)+seed.x*6.0)*22.0 + sin(uTime*(0.7+seed.z*0.4)+seed.w*11.0)*8.0;
          float x=mod(seed.x*W + t*uWind*(0.3+0.45*gust) + sway - uCamX*uPar, W)-30.0;
          float y=mod(seed.y*H + t*(0.32+uRain*0.7) + sin(t*0.14+seed.w)*10.0 - uCamY*uPar, H)-20.0;
          x=floor(x)+0.5; y=floor(y)+0.5;
          vec3 acc=vec3(0.0);
          for(int i=0;i<${MAXL};i++){ if(i>=uNL) break; vec4 P=uLP[i]; vec2 d=vec2(x,y)-P.xy; float dist=length(d); if(dist>P.w*1.2) continue;
            float cone= uLD[i].w>0.5 ? smoothstep(uLD[i].z-0.05,uLD[i].z+0.1,dot(normalize(d+0.0001),uLD[i].xy)) : 1.0;
            acc+=uLC[i].rgb*uLC[i].a*cone*pow(1.0-dist/(P.w*1.2),1.5); }
          float k=fract(seed.w*7.31);
          vec3 base = k<0.45 ? vec3(0.85,0.62,0.10) : k<0.7 ? vec3(0.70,0.18,0.08) : k<0.88 ? vec3(0.45,0.28,0.14) : vec3(0.95,0.78,0.25);
          vC=base*(0.18+acc*1.6); vA=1.0;
          vFlip=step(0.0,sin(uTime*(0.85+seed.z*1.5)+seed.x*40.0)); // slow tumble: flat <-> edge
          gl_PointSize= uSize*(seed.z>0.8?2.0:1.0);
          gl_Position=projectionMatrix*viewMatrix*vec4(x,y,0.0,1.0);
        }`,
      fragmentShader: `precision highp float; varying vec3 vC; varying float vA; varying float vFlip; uniform float uBright;
        void main(){ vec2 c=gl_PointCoord-0.5; if(vFlip<0.5 && abs(c.y)>0.26) discard; gl_FragColor=vec4(vC*uBright, vA); }`,
      uniforms: { ...this.lightU, uTime: this.time, uCamX: { value: 0 }, uCamY: { value: 0 }, uPar: { value: par }, uSize: { value: size }, uSpeed: { value: speed }, uWind: { value: 14 }, uBright: { value: bright }, uRain: { value: 0 } },
      transparent: true, depthTest: false, depthWrite: false,
    });
    const p = new THREE.Points(g, mat); p.renderOrder = order; p.frustumCulled = false; this.scene.add(p); return p;
  }
  rain(order, count) {
    // short slanted streaks as line segments, pixel-snapped
    const g = new THREE.BufferGeometry();
    const seeds = new Float32Array(count * 2 * 4); const pos = new Float32Array(count * 2 * 3);
    for (let i = 0; i < count; i++) { const s = [Math.random(), Math.random(), Math.random(), Math.random()]; for (let e = 0; e < 2; e++) { seeds.set(s, (i * 2 + e) * 4); pos[(i * 2 + e) * 3] = e; } }
    g.setAttribute('position', new THREE.BufferAttribute(pos, 3)); g.setAttribute('seed', new THREE.BufferAttribute(seeds, 4));
    const mat = new THREE.ShaderMaterial({
      vertexShader: `attribute vec4 seed; uniform float uTime,uCamX,uCamY; uniform vec2 uRes2; varying float vA;
        void main(){ float W=uRes2.x+80.0,H=uRes2.y+40.0; float t=uTime*(420.0+seed.z*160.0);
          float x=mod(seed.x*W - uCamX*1.1 - t*0.18, W)-20.0; float y=mod(seed.y*H + t - uCamY, H)-20.0;
          float L=6.0+seed.w*6.0; x=floor(x - position.x*L*0.18); y=floor(y - position.x*L);
          vA=0.25+0.35*seed.w; gl_Position=projectionMatrix*viewMatrix*vec4(x+0.5,y+0.5,0.0,1.0); }`,
      fragmentShader: `precision highp float; varying float vA; uniform float uOn; void main(){ gl_FragColor=vec4(0.55,0.62,0.72,vA*uOn); }`,
      uniforms: { uTime: this.time, uCamX: { value: 0 }, uCamY: { value: 0 }, uRes2: this.lightU.uRes, uOn: { value: 0 } }, transparent: true, depthTest: false, depthWrite: false,
    });
    const l = new THREE.LineSegments(g, mat); l.renderOrder = order; l.frustumCulled = false; this.scene.add(l); return l;
  }
  // post --------------------------------------------------------------------------------
  buildPost() {
    this.allocRT();
    const vs = `varying vec2 vUv; void main(){ vUv=uv; gl_Position=vec4(position.xy*2.0,0.0,1.0);} `;
    const mk = (fs, u) => new THREE.ShaderMaterial({ vertexShader: vs, fragmentShader: fs, uniforms: u, depthTest: false, depthWrite: false });
    this.post.bright = mk(`precision highp float; varying vec2 vUv; uniform sampler2D t; uniform vec2 px;
      void main(){ vec3 c=vec3(0.0); for(int i=0;i<2;i++)for(int j=0;j<2;j++){ vec3 s=texture2D(t,vUv+vec2(float(i)-0.5,float(j)-0.5)*px).rgb; float l=dot(s,vec3(0.3,0.59,0.11)); c+=s*smoothstep(0.35,0.9,l);} gl_FragColor=vec4(c*0.25,1.0);} `,
      { t: { value: null }, px: { value: new THREE.Vector2() } });
    this.post.blur = mk(`precision highp float; varying vec2 vUv; uniform sampler2D t; uniform vec2 dir;
      void main(){ float w[5]; w[0]=0.227;w[1]=0.194;w[2]=0.121;w[3]=0.054;w[4]=0.016; vec3 c=texture2D(t,vUv).rgb*w[0];
      for(int i=1;i<5;i++){ c+=texture2D(t,vUv+dir*float(i)).rgb*w[i]; c+=texture2D(t,vUv-dir*float(i)).rgb*w[i]; } gl_FragColor=vec4(c,1.0);} `,
      { t: { value: null }, dir: { value: new THREE.Vector2() } });
    this.post.comp = mk(`precision highp float; varying vec2 vUv; uniform sampler2D tS,tB; uniform vec2 uRes; uniform float uTime,uBloom,uGrain,uVig,uHurt,uCold,uFade,uDesat,uStep;
      ${BAYER}
      vec3 aces(vec3 x){ return clamp((x*(2.51*x+0.03))/(x*(2.43*x+0.59)+0.14),0.0,1.0); }
      void main(){
        vec2 ip=floor(vUv*uRes)+0.5; vec2 uv=ip/uRes;
        vec3 c=texture2D(tS,uv).rgb;
        vec3 bl=texture2D(tB,uv).rgb;
        float b=bayer4(ip);
        
        c+=bl*uBloom;
        c*=1.35;
        c=aces(c);
        c=pow(c,vec3(1.0/2.2));
        // grade: cool shadows, warm highlights, slight desat
        float l=dot(c,vec3(0.299,0.587,0.114));
        c=mix(c,c*vec3(0.90,0.92,1.12),(1.0-l)*0.45);
        c=mix(c,c*vec3(1.12,1.0,0.84),l*0.55);
        c=mix(vec3(l),c,0.88-uDesat*0.7);
        // vignette (quantized)
        vec2 q=uv-0.5; float v=1.0-dot(q,q)*uVig; c*=v;
        // hurt / cold edges
        float e=smoothstep(0.18,0.62,length(q*vec2(1.0,1.2)));
        c=mix(c,vec3(0.55,0.02,0.02),e*uHurt);
        c=mix(c,c*vec3(0.80,0.88,1.0),uCold); // rain: cooler, darker
        // grain per internal pixel, stepped at 12 fps
        float g=hash12(ip+floor(uTime*12.0)*17.31)-0.5; c+=g*uGrain;
        c*=uFade;
        gl_FragColor=vec4(c,1.0);
      }`, { tS: { value: null }, tB: { value: null }, uRes: { value: new THREE.Vector2(this.W, this.H) }, uTime: this.time, uBloom: { value: 0.9 }, uGrain: { value: 0.045 }, uVig: { value: 1.1 }, uHurt: { value: 0 }, uCold: { value: 0 }, uFade: { value: 1 }, uDesat: { value: 0 }, uStep: { value: 0 } });
    this.fs = new THREE.Mesh(new THREE.PlaneGeometry(1, 1), this.post.bright); this.fs.frustumCulled = false;
    this.fsScene = new THREE.Scene(); this.fsScene.add(this.fs);
    this.fsCam = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);
  }
  pass(mat, target) { this.fs.material = mat; this.gl.setRenderTarget(target); this.gl.render(this.fsScene, this.fsCam); }
  setLights(list) {
    const n = Math.min(MAXL, list.length);
    for (let i = 0; i < n; i++) {
      const L = list[i];
      this.lightU.uLP.value[i].set(L.sx, L.sy, L.z ?? 40, L.r);
      this.lightU.uLC.value[i].set(L.c[0], L.c[1], L.c[2], L.i);
      this.lightU.uLD.value[i].set(L.dx ?? 0, L.dy ?? 1, L.cos ?? 0.55, L.cone ? 1 : 0);
    }
    this.lightU.uNL.value = n;
  }
  render() {
    this.frame++;
    const g = this.gl;
    g.setRenderTarget(this.rt); g.setClearColor(0x000000, 1); g.clear();
    g.render(this.scene, this.cam);
    const bloomOn = this.quality !== 'low';
    if (bloomOn) {
      this.post.bright.uniforms.t.value = this.rt.texture; this.post.bright.uniforms.px.value.set(1 / this.W, 1 / this.H);
      this.pass(this.post.bright, this.rtB1);
      const w = this.W >> 1, h = this.H >> 1;
      for (let k = 0; k < 2; k++) {
        this.post.blur.uniforms.t.value = this.rtB1.texture; this.post.blur.uniforms.dir.value.set((1.5 + k) / w, 0); this.pass(this.post.blur, this.rtB2);
        this.post.blur.uniforms.t.value = this.rtB2.texture; this.post.blur.uniforms.dir.value.set(0, (1.5 + k) / h); this.pass(this.post.blur, this.rtB1);
      }
    }
    const c = this.post.comp.uniforms;
    c.tS.value = this.rt.texture; c.tB.value = this.rtB1.texture; c.uBloom.value = bloomOn ? 1.0 : 0.0;
    this.pass(this.post.comp, null);
  }
}
