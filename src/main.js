import '@fontsource/ibm-plex-sans-kr/700.css';
import '@fontsource/ibm-plex-mono/500.css';
import './style.css';
import * as THREE from 'three';
import { Renderer, makeTex } from './render.js';
import { Game, M } from './game.js';
import { Audio } from './audio.js';
import { Input } from './input.js';

const $ = s => document.querySelector(s);
const BASE = import.meta.env.BASE_URL + 'px/';
const DBG = new URLSearchParams(location.search);
const QUAL = { low: { label: '저', snow: [250, 500, 120], vol: 0, fog: 0, maxL: 10 }, mid: { label: '중', snow: [600, 1200, 220], vol: 1, fog: 1, maxL: 16 }, high: { label: '고', snow: [900, 1400, 260], vol: 1, fog: 1, maxL: 20 } };
const coarse = matchMedia('(pointer:coarse)').matches;
let qKey = new URLSearchParams(location.search).get('q') || (coarse ? 'mid' : 'high');

function loadImg(url) { return new Promise((res, rej) => { const i = new Image(); i.onload = () => res(i); i.onerror = () => rej(new Error('load ' + url)); i.src = url; }); }

async function boot() {
  const R = new Renderer($('#gl'));
  const [world, chars, office] = await Promise.all([fetch(BASE + 'world.json').then(r => r.json()), fetch(BASE + 'chars.json').then(r => r.json()), fetch(BASE + 'office.json').then(r => r.json())]);
  const W = world.world;
  // ---------------- asset list
  const urls = [];
  for (const L of world.layers) L.chunks.forEach((c, i) => { const s = L.chunks.length > 1 ? '_' + i : ''; for (const k of ['a', 'n', 'e']) urls.push(`L_${L.name}${s}_${k}.webp`); });
  for (const k of Object.keys(world.sprites)) for (const t of ['a', 'n', 'e']) urls.push(`S_${k}_${t}.webp`);
  for (const k of Object.keys(chars.sheets)) for (const t of ['a', 'n']) urls.push(`${k}_${t}.webp`);
  for (const L of office.layers) L.chunks.forEach((c, i) => { const s = L.chunks.length > 1 ? '_' + i : ''; for (const k of ['a', 'n', 'e']) urls.push(`L_${L.name}${s}_${k}.webp`); });
  const tex = {}; let done = 0;
  await Promise.all(urls.map(u => loadImg(BASE + u).then(img => { tex[u] = makeTex(img); done++; $('#loadPct').textContent = String(Math.round(done / urls.length * 100)).padStart(2, '0') + '%'; })));
  const T = n => tex[n];

  // ---------------- layers
  const ORDER = { sky: 0, far: 10, mid2: 20, mid1: 30, street: 40, fg: 70 };
  const LCONF = { sky: { light: 0, fog: 0, emi: 1.4 }, far: { light: 0, fog: 0.30, emi: 1.6 }, mid2: { light: 0, fog: 0.22, emi: 1.5 }, mid1: { light: 0.12, fog: 0.10, emi: 1.4 }, street: { light: 1, fog: 0, emi: 1.25 }, fg: { light: 0.55, fog: 0, emi: 1 } };
  const layers = world.layers.map(L => {
    const cf = LCONF[L.name];
    const meshes = L.chunks.map((c, i) => {
      const s = L.chunks.length > 1 ? '_' + i : '';
      const mat = R.spriteMat({ map: T(`L_${L.name}${s}_a.webp`), nrm: T(`L_${L.name}${s}_n.webp`), emi: T(`L_${L.name}${s}_e.webp`), layerLight: cf.light, emiStr: cf.emi, fogAmt: cf.fog });
      mat.uniforms.uFogCol.value.set(0x2a2032).convertSRGBToLinear();
      if (L.name === 'fg') mat.uniforms.uDark.value = 0.55;
      const m = R.quad(c.w, L.h, mat, ORDER[L.name]); m.userData = { x: c.x, w: c.w, h: L.h };
      return m;
    });
    return { ...L, meshes, py: L.p < 1 ? L.p : 1 };
  });
  const officeMeshes = office.layers[0].chunks.map((c, i) => {
    const s = office.layers[0].chunks.length > 1 ? '_' + i : '';
    const mat = R.spriteMat({ map: T(`L_office${s}_a.webp`), nrm: T(`L_office${s}_n.webp`), emi: T(`L_office${s}_e.webp`), layerLight: 1, emiStr: 1.3, fogAmt: 0 });
    const m = R.quad(c.w, office.layers[0].h, mat, 41); m.userData = { x: c.x, w: c.w, h: office.layers[0].h }; m.visible = false; return m;
  });
  // ---------------- fog sheets, volumetrics, snow, water
  const fogs = [
    R.fogSheet(15, { color: 0x3a2a3a, density: 0.5, y0: 220, y1: 340, speed: 0.05, scale: 120, par: 0.25 }),
    R.fogSheet(25, { color: 0x2e2a3c, density: 0.4, y0: 260, y1: 360, speed: 0.07, scale: 90, par: 0.45 }),
    R.fogSheet(35, { color: 0x2a2a3a, density: 0.3, y0: 300, y1: 380, speed: 0.1, scale: 70, par: 0.8 }),
    R.fogSheet(62, { color: 0x3a3440, density: 0.12, y0: 430, y1: 500, speed: 0.16, scale: 60, par: 1.0 }),
  ];
  const water = R.water(43, W);
  const vol = R.volumetrics(58);
  let snows = [];
  function buildSnow() {
    snows.forEach(s => { R.scene.remove(s); s.geometry.dispose(); s.material.dispose(); });
    const q = QUAL[qKey].snow;
    snows = [R.leaves(26, Math.round(q[0] * 0.25), 0.4, 1, 4, 0.6), R.leaves(56, Math.round(q[1] * 0.18), 1.0, 1, 6.5, 1.0), R.leaves(72, Math.round(q[2] * 0.2), 1.3, 2, 10, 1.1)];
  }
  buildSnow();
  const rainMesh = R.rain(64, 900);
  // ---------------- props / items / barrels
  const game = new Game(W, world.sprites, audio, log, world.leafPiles || []);
  game.attachOffice(office);
  game.enter('street');
  const bs = world.sprites.barrel;
  let propMeshes = [], barrelMeshes = [], itemMeshes = [];
  function buildItems() {
    itemMeshes.forEach(m => R.scene.remove(m));
    itemMeshes = game.items.map(it => { const mat = R.spriteMat({ map: T(`S_item_${it.k}_a.webp`), nrm: T(`S_item_${it.k}_n.webp`), emi: T(`S_item_${it.k}_e.webp`), emiStr: 1.5 }); const m = R.quad(16, 16, mat, 47); m.userData = it; return m; });
  }
  function buildProps() {
    propMeshes.forEach(m => R.scene.remove(m));
    barrelMeshes.forEach(m => R.scene.remove(m));
    propMeshes = game.props.map(p => {
      const mat = R.spriteMat({ map: T(`S_${p.k}_a.webp`), nrm: T(`S_${p.k}_n.webp`), emi: T(`S_${p.k}_e.webp`) });
      const m = R.quad(p.w, p.h, mat, 45); m.userData = p; return m;
    });
    barrelMeshes = game.barrels.map(b => {
      const mat = R.spriteMat({ map: T('S_barrel_a.webp'), nrm: T('S_barrel_n.webp'), emi: T('S_barrel_e.webp'), emiStr: 2.2 });
      mat.uniforms.uUvRect.value.set(0, 0, bs.fw / bs.w, 1);
      const m = R.quad(bs.fw, bs.h, mat, 46); m.userData = b; return m;
    });
  }
  buildProps();
  buildItems();
  // ---------------- characters
  const sheets = chars.sheets;
  function charMesh(kind, order) {
    const sh = sheets[kind];
    const mat = R.spriteMat({ map: T(`${kind}_a.webp`), nrm: T(`${kind}_n.webp`) });
    mat.uniforms.uDark.value = 1.3; const m = R.quad(64, 64, mat, order); m.userData.kind = kind; return m;
  }
  let enemyMeshes = [], blobs = [];
  const playerMesh = charMesh('player', 52);
  const blobMat = new THREE.ShaderMaterial({ vertexShader: `varying vec2 vUv; void main(){vUv=uv; gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0);}`,
    fragmentShader: `varying vec2 vUv; void main(){ vec2 q=(vUv-0.5)*2.0; float d=dot(q,q); if(d>1.0) discard; gl_FragColor=vec4(0.0,0.0,0.02, d<0.45?0.55:0.3);} `, transparent: true, depthTest: false, side: THREE.DoubleSide });
  function buildBlobs() {
    blobs.forEach(m => R.scene.remove(m));
    blobs = Array.from({ length: game.enemies.length + 1 }, () => { const m = new THREE.Mesh(new THREE.PlaneGeometry(22, 5), blobMat); m.renderOrder = 44; m.frustumCulled = false; R.scene.add(m); return m; });
  }
  function buildEnemies() { enemyMeshes.forEach(m => R.scene.remove(m)); enemyMeshes = game.enemies.map((e, i) => charMesh(e.k, 50 + i * 0.01)); buildBlobs(); }
  function rebuildScene() { buildProps(); buildItems(); buildEnemies(); }
  buildEnemies();
  // splash particles
  const splashPts = new THREE.Points(new THREE.BufferGeometry().setAttribute('position', new THREE.BufferAttribute(new Float32Array(120 * 3), 3)),
    new THREE.PointsMaterial({ color: 0x9fd0ff, size: 2, sizeAttenuation: false, transparent: true, depthTest: false }));
  splashPts.renderOrder = 54; splashPts.frustumCulled = false; R.scene.add(splashPts);

  function setFrame(mesh, kind, anim, t, face, once) {
    const sh = sheets[kind]; const A = sh.anims[anim] || sh.anims.idle;
    let f = Math.floor(t * A.fps); f = once ? Math.min(f, A.n - 1) : f % A.n;
    mesh.material.uniforms.uUvRect.value.set(f * 64 / sh.w, A.row * 64 / sh.h, 64 / sh.w, 64 / sh.h);
    mesh.material.uniforms.uFlip.value = face;
  }
  // ---------------- UI
  const ui = { mode: 'loading', logs: [] };
  function log(msg, cls = '') {
    ui.logs.push({ msg, cls }); if (ui.logs.length > 4) ui.logs.shift();
    $('#log').innerHTML = ui.logs.map(l => `<p class="${l.cls}">${l.msg}</p>`).join('');
  }
  function setMode(m) {
    ui.mode = m;
    $('#title').classList.toggle('hidden', m !== 'title');
    $('#hud').classList.toggle('hidden', !(m === 'play' || m === 'pause'));
    $('#end').classList.toggle('hidden', !(m === 'dead' || m === 'win'));
    $('#touch').classList.toggle('hidden', !(coarse && m === 'play'));
    if (m !== 'pause') $('#help').classList.add('hidden');
    if (m !== 'play') { $('#news').classList.add('hidden'); $('#tutor').classList.add('hidden'); }
  }
  $('#qLabel').textContent = QUAL[qKey].label;
  $('#btnQuality').onclick = () => { qKey = qKey === 'high' ? 'mid' : qKey === 'mid' ? 'low' : 'high'; $('#qLabel').textContent = QUAL[qKey].label; R.quality = qKey; buildSnow(); };
  R.quality = qKey;
  $('#btnHelp').onclick = () => { $('#help').classList.remove('hidden'); $('#helpCloseTxt').textContent = '돌아가기'; };
  $('#btnHelpClose').onclick = () => { $('#help').classList.add('hidden'); if (ui.mode === 'pause') setMode('play'); };
  let opening = null, openT = 0, fading = null;
  const EYE = 292;
  function skipNews() {
    if (opening !== 'news' && opening !== 'flicker') return;
    opening = 'play';
    $('#news').classList.add('hidden');
    $('#hud').classList.remove('hidden');
    log('뉴스: 물리면 씻고 PEP. 소리·빛에 반응. 물을 두려워한다.', 'note');
    log('[A/D] 이동  [F] 손전등  [E] 줍기  [Q] 물');
  }
  const startGame = () => {
    audio.start(); game.enter('office'); rebuildScene(); rainAmt = 0; ui.logs = []; $('#log').innerHTML = '';
    log('11월 · 17:12 · 서초 하천관리센터 2층. 해가 진다.');
    camX = Math.max(0, game.p.x - 200); camTop = game.w.ct0 ?? 108;
    opening = 'flicker'; openT = 0; fading = null;
    setMode('play');
    $('#hud').classList.add('hidden');
    $('#news').classList.add('hidden');
    $('#tutor').classList.add('hidden');
    $('#fade').classList.remove('on');
  };
  $('#btnStart').onclick = startGame; $('#btnRetry').onclick = startGame;
  $('#btnTitle').onclick = () => { opening = null; game.enter('street'); rebuildScene(); setMode('title'); $('#news').classList.add('hidden'); $('#fade').classList.remove('on'); };
  $('#btnNewsSkip').onclick = skipNews;
  input.bindTouch($('#touch'));

  // ---------------- camera
  let camX = 0, camTop = 108, titleT = 0, rainAmt = 0;
  const lightsWorldStreet = world.lights.map(l => ({ ...l, i: l.cone ? l.i * 0.8 : l.i, z: l.cone ? 34 : 18, cos: 0.42 }));
  const lightsWorldOffice = office.lights.map(l => ({ ...l, i: l.cone ? l.i * 0.85 : l.i, z: l.cone ? 28 : 16, cos: 0.4 }));
  const tmpL = [];
  function lightsWorld() { return game.scene === 'office' ? lightsWorldOffice : lightsWorldStreet; }
  function gatherLights(t) {
    tmpL.length = 0;
    const p = game.p;
    const push = (L) => { const sx = L.x - camX, sy = L.y - camTop; if (sx < -L.r || sx > R.W + L.r || sy < -L.r || sy > R.H + L.r) return; tmpL.push({ ...L, sx, sy }); };
    if (ui.mode !== 'title' && p.torch && !p.dead) {
      const hx = p.x + p.face * 11, hy = p.y - (p.crouch ? 20 : 31);
      const dy = 0.16; const n = Math.hypot(1, dy);
      tmpL.push({ sx: hx - camX, sy: hy - camTop, r: 240, i: 1.8, c: [1.0, 0.95, 0.82], z: 10, cone: 1, dx: p.face / n, dy: dy / n, cos: 0.92, pri: 1e9 });
      tmpL.push({ sx: hx - camX, sy: hy - camTop, r: 46, i: 0.35, c: [1, 0.95, 0.85], z: 16, cone: 0, pri: 1e9 });
    }
    for (const L of lightsWorld()) { let i = L.i; if (L.flick) i *= (Math.sin(t * 37 + L.x) > 0.75 - L.flick * 4 ? 1 : 0.15 + 0.85 * (Math.sin(t * 3 + L.x) * 0.5 + 0.5)); push({ ...L, i, c: L.c, dx: 0, dy: 1 }); }
    for (const b of game.barrels) push({ x: b.x + 14, y: b.y + 8, r: 130, i: 1.25 + 0.25 * Math.sin(t * 13 + b.x) + 0.15 * Math.sin(t * 29), c: [1.0, 0.55, 0.22], z: 22, cone: 0 });
    const amb = game.props.find(p => p.k === 'ambulance');
    if (amb) { const ph = Math.floor(t * 3.2) % 2; push({ x: amb.x + 92, y: amb.y + 4, r: 170, i: 1.4, c: ph ? [1, 0.1, 0.08] : [0.15, 0.3, 1], z: 30, cone: 0 }); }
    const taxi = game.props.find(p => p.k === 'car_taxi');
    if (taxi && Math.floor(t * 1.6) % 2) { push({ x: taxi.x + 100, y: taxi.y + 22, r: 70, i: 1.0, c: [1, 0.6, 0.1], z: 10, cone: 0 }); push({ x: taxi.x + 4, y: taxi.y + 22, r: 70, i: 1.0, c: [1, 0.6, 0.1], z: 10, cone: 0 }); }
    for (const it of game.items) if (!it.taken) push({ x: it.x, y: it.y - 10, r: 26, i: 0.5 + 0.3 * Math.sin(t * 4 + it.x), c: [0.8, 0.9, 1], z: 12, cone: 0 });
    const cx = R.W / 2, cy = R.H / 2;
    tmpL.forEach(L => { L.pri = L.pri ?? (L.i * L.r / (60 + Math.hypot(L.sx - cx, L.sy - cy))); });
    tmpL.sort((a, b) => b.pri - a.pri);
    tmpL.length = Math.min(tmpL.length, QUAL[qKey].maxL);
    R.setLights(tmpL);
    return tmpL;
  }

  // ---------------- loop
  let last = performance.now();
  setMode('title');
  $('#loading').classList.add('hidden');
  window.__game = game; window.__R = R; window.__skipNews = skipNews; window.__toStreet = () => { game.leaveOffice = true; }; window.__opening = () => opening;
  function frame(now) {
    const dt = Math.min(0.05, (now - last) / 1000); last = now;
    R.time.value += dt;
    const t = R.time.value;
    const inp = input.read();
    if (ui.mode === 'title' && inp.confirmPressed) startGame();
    if ((opening === 'flicker' || opening === 'news') && (inp.confirmPressed || inp.jumpPressed || inp.interactPressed)) skipNews();
    if ((ui.mode === 'play' || ui.mode === 'pause') && inp.pausePressed && opening === 'play') {
      if (ui.mode === 'play') { setMode('pause'); $('#help').classList.remove('hidden'); $('#helpCloseTxt').textContent = '계속하기'; }
      else setMode('play');
    }
    if (opening === 'flicker') {
      openT += dt;
      if (openT > 1.5) { opening = 'news'; $('#news').classList.remove('hidden'); }
    }
    if (game.leaveOffice && !fading) {
      fading = 'to-street';
      $('#fade').classList.add('on'); $('#tutor').classList.add('hidden');
      const keep = { blood: game.p.blood, bleed: game.p.bleed, exposed: game.p.exposed, water: Math.max(1, game.p.water), bandage: game.p.bandage, torch: game.p.torch, stats: { ...game.stats } };
      setTimeout(() => {
        game.enter('street', keep);
        if (keep.stats) game.stats = keep.stats;
        rebuildScene();
        camX = 0; camTop = game.w.ct0 ?? 108;
        log('1층. 양재동 골목. 무전: "물가로 가라." — 목표: 양재천 둔치', 'note');
        $('#fade').classList.remove('on');
        fading = null; opening = 'play';
      }, 650);
    }
    const worldLights = lightsWorld().map(l => ({ x: l.x, y: l.y, r: l.r * 0.8, i: l.i })).concat(game.barrels.map(b => ({ x: b.x + 14, y: b.y, r: 110, i: 1 })));
    const canPlay = ui.mode === 'play' && opening === 'play' && !fading;
    if (canPlay) game.update(dt, inp, worldLights);
    if (ui.mode === 'play' && game.over) endScreen(game.over);
    audio.update(dt, canPlay ? game.chased : 0);
    // camera — eye-level true side view (ground near the bottom of the frame)
    const p = game.p;
    const maxX = Math.max(0, (game.w.xmax ?? game.w.w) - R.W);
    if (ui.mode === 'title') {
      titleT += dt; const span = 1500; const u = (Math.sin(titleT * 0.035 - 1.57) * 0.5 + 0.5);
      camX = 40 + u * span; camTop = game.streetWorld.ct0 ?? 108;
    } else {
      const tx = p.x - R.W * 0.42 + p.face * 34;
      camX += (tx - camX) * Math.min(1, dt * 3.2);
      const ty = Math.max(0, Math.min(game.w.h - R.H, p.y - EYE));
      camTop += (ty - camTop) * Math.min(1, dt * 3);
    }
    camX = Math.max(0, Math.min(maxX, camX));
    const sh = game.shake * 3;
    const cX = Math.round(camX + (Math.random() - 0.5) * sh), cT = Math.round(camTop + (Math.random() - 0.5) * sh);
    const saveX = camX, saveT = camTop; camX = cX; camTop = cT;
    const Ls = gatherLights(t);
    // layers
    const inOff = game.scene === 'office';
    for (const L of layers) {
      const ox = Math.round(cX * L.p), top = Math.round(-150 - (cT - 150) * L.py);
      for (const m of L.meshes) { const d = m.userData; m.position.set(d.x - ox + d.w / 2, top + d.h / 2, 0); m.visible = !inOff && d.x - ox < R.W && d.x - ox + d.w > 0; }
    }
    for (const m of officeMeshes) {
      const d = m.userData; const top = -cT;
      m.position.set(d.x - cX + d.w / 2, top + d.h / 2, 0);
      m.visible = inOff && d.x - cX < R.W && d.x - cX + d.w > 0;
    }
    for (const f of fogs) { f.material.uniforms.uCamX.value = cX; f.material.uniforms.uCamY.value = cT; f.material.uniforms.uOn.value = inOff ? 0 : (DBG.has('nofog') ? 0 : QUAL[qKey].fog) * (1 + rainAmt * 0.6); }
    water.material.uniforms.uCamX.value = cX; water.material.uniforms.uCamY.value = cT;
    vol.material.uniforms.uCamX.value = cX; vol.material.uniforms.uOn.value = QUAL[qKey].vol; vol.visible = !inOff && QUAL[qKey].vol > 0 && !DBG.has('novol');
    const raining = !inOff && ui.mode === 'play' && game.rain.on;
    rainAmt += ((raining ? 1 : 0) - rainAmt) * Math.min(1, dt * 1.5);
    for (const s of snows) { s.material.uniforms.uCamX.value = cX; s.material.uniforms.uCamY.value = cT; s.material.uniforms.uRain.value = rainAmt; s.visible = !inOff; }
    rainMesh.material.uniforms.uCamX.value = cX; rainMesh.material.uniforms.uCamY.value = cT; rainMesh.material.uniforms.uOn.value = rainAmt; rainMesh.visible = !inOff && rainAmt > 0.02;
    water.visible = !inOff; water.material.uniforms.uRain.value = rainAmt;
    if (opening === 'flicker') {
      const k = (Math.sin(openT * 37) > 0.55 || Math.sin(openT * 11) > 0.92) ? 1 : 0.06;
      R.amb.value.setRGB(0.05 * k, 0.05 * k, 0.06 * k);
    } else if (inOff) R.amb.value.setRGB(0.13, 0.13, 0.12);
    else R.amb.value.setRGB(0.17 - rainAmt * 0.04, 0.17 - rainAmt * 0.02, 0.24);
    for (const m of propMeshes) { const d = m.userData; m.position.set(d.x - cX + d.w / 2, d.y - cT + d.h / 2, 0); }
    for (const m of barrelMeshes) { const d = m.userData; m.position.set(d.x - cX + 14, d.y - cT + 22, 0); m.material.uniforms.uUvRect.value.x = (Math.floor(t * 9 + d.x) % 4) * bs.fw / bs.w; }
    for (const m of itemMeshes) { const d = m.userData; m.visible = !d.taken; m.position.set(Math.round(d.x - cX), Math.round(d.y - cT - 8 + (Math.sin(t * 3 + d.x) > 0.6 ? -1 : 0)), 0); m.material.uniforms.uEmiStr.value = 1 + Math.sin(t * 4) * 0.5; }
    // characters
    game.enemies.forEach((e, i) => {
      const m = enemyMeshes[i];
      setFrame(m, e.k, e.anim, e.animT, e.face, e.anim === 'rise' || e.anim === 'lunge');
      m.position.set(Math.round(e.x - cX), Math.round(e.y - cT - 61 + 32), 0);
      m.material.uniforms.uFlash.value = 0;
      blobs[i].position.set(Math.round(e.x - cX), Math.round(e.y - cT), 0); blobs[i].visible = e.anim !== 'lie';
    });
    playerMesh.visible = true;
    setFrame(playerMesh, 'player', p.anim, p.animT, p.face, ['dead', 'interact', 'shove', 'splash', 'hurt'].includes(p.anim));
    playerMesh.position.set(Math.round(p.x - cX), Math.round(p.y - cT - 61 + 32), 0);
    playerMesh.material.uniforms.uFlash.value = p.invT > 0 && Math.floor(p.invT * 16) % 2 ? 0.5 : 0;
    blobs[game.enemies.length].position.set(Math.round(p.x - cX), Math.round(p.y - cT), 0);
    // splash particles
    const pos = splashPts.geometry.attributes.position.array; let k = 0;
    for (const s of game.splashes) for (let j = 0; j < 30 && k < 120; j++, k++) {
      const a = (j / 30) * 1.2 - 0.6, v = 120 + (j * 37 % 60);
      pos[k * 3] = Math.round(s.x - cX + s.face * Math.cos(a) * v * s.t); pos[k * 3 + 1] = Math.round(s.y - cT + Math.sin(a) * v * s.t + 260 * s.t * s.t); pos[k * 3 + 2] = 0;
    }
    for (; k < 120; k++) { pos[k * 3] = -99; pos[k * 3 + 1] = -99; }
    splashPts.geometry.attributes.position.needsUpdate = true;
    // post uniforms
    const c = R.post.comp.uniforms;
    c.uHurt.value = Math.max(game.flash * 0.6, p.blood < 50 ? (50 - p.blood) / 50 * (0.35 + 0.15 * Math.sin(t * 5)) : 0);
    c.uCold.value = rainAmt * 0.6;
    c.uDesat.value = ui.mode === 'play' ? Math.max(0, (60 - p.blood) / 60) : 0;
    c.uFade.value = ui.mode === 'dead' ? 0.4 : 1;
    R.render();
    camX = saveX; camTop = saveT;
    if (ui.mode === 'play') { hud(t); updateTutor(); }
    requestAnimationFrame(frame);
  }
  function updateTutor() {
    const el = $('#tutor');
    if (game.scene !== 'office' || opening !== 'play' || fading) { el.classList.add('hidden'); return; }
    const p = game.p, t = game.tut, nearInf = game.enemies.some(e => Math.abs(e.x - p.x) < 110);
    if (Math.abs(p.vx) > 8) t.move = true;
    if (p.torch) t.torch = true;
    if (p.anim === 'jump') t.jump = true;
    if (game.prompt && game.prompt.k === 'water') t.water = true;
    let key, txt;
    if (!t.torch) { key = 'F'; txt = '손전등 — 시야를 밝혀라'; }
    else if (!t.move) { key = 'A / D'; txt = '이동'; }
    else if (game.prompt && game.prompt.k === 'water') { key = 'E'; txt = '줍기 — 생수 500ml'; }
    else if (p.x > 490 && p.x < 590 && !t.jump) { key = 'SPACE'; txt = '점프 — 넘어가기'; }
    else if (p.run && t.move) { key = 'SHIFT'; txt = '달리기 — 발소리가 커진다'; t.run = true; }
    else if (nearInf && p.water > 0 && !t.splash) { key = 'Q'; txt = '물 뿌리기 — 감염자는 물을 두려워한다'; }
    else if (nearInf) { key = '!'; txt = '문 앞의 감염자. 소리에 반응한다'; }
    else { el.classList.add('hidden'); return; }
    if (p.act === 'splash') t.splash = true;
    el.classList.remove('hidden');
    $('#tutorKey').textContent = key;
    $('#tutorTxt').textContent = txt;
  }
  // ---------------- HUD
  let hudT = 0;
  function bar(id, v, crit) { const el = $(id); el.firstElementChild.style.width = `calc(${Math.max(0, Math.min(100, v))}% - 2px)`; el.classList.toggle('crit', !!crit); }
  function hud(t) {
    if (t - hudT < 0.08) return; hudT = t;
    const p = game.p;
    bar('#bBlood', (p.blood - 25) / 75 * 100, p.blood < 50); $('#vBlood').textContent = Math.max(0, Math.round(p.blood));
    bar('#bStam', p.stamina, p.stamina < 20); $('#vStam').textContent = Math.round(p.stamina);
    const rn = game.rain; bar('#bTemp', rn.on ? rn.t / rn.dur * 100 : 0, false); $('#vTemp').textContent = rn.on ? Math.ceil(rn.t) + 's' : '—';
    $('#lTemp').textContent = rn.on ? '비 · 위축' : '날씨 · 맑음';
    $('#vBleed').textContent = p.bleed > 0.05 ? `진행 −${p.bleed.toFixed(1)}/s` : '없음';
    $('#vBleed').style.color = p.bleed > 0.05 ? 'var(--red)' : '';
    $('#vExpo').textContent = p.exposed ? '광견병 노출 · 확인됨' : '광견병 노출 · 없음';
    $('#vExpo').style.color = p.exposed ? 'var(--red)' : 'var(--dim)';
    $('#vWater').textContent = p.water; $('#vBand').textContent = p.bandage; $('#vTorch').textContent = p.torch ? 'ON' : 'OFF';
    const total = W.goal - 70, rem = Math.max(0, W.goal - p.x);
    $('#trk').style.width = (100 - rem / total * 100) + '%';
    $('#vDist').textContent = `잔여 ${String(Math.round(rem / M)).padStart(3, '0')}M`;
    const inZone = p.x > W.water - 10 * M - 30;
    $('#vZone').textContent = inZone ? '공수병 회피구역 ▮ 안전' : '공수병 회피구역 밖'; $('#vZone').classList.toggle('on', inZone);
    bar('#bNoise', p.noiseShow / (10 * M) * 100, p.noiseShow > 6 * M); $('#vNoise').textContent = Math.round(p.noiseShow / M) + 'M';
    const lit = Math.min(1, p.lit / 1.4); bar('#bLit', lit * 100, lit > 0.7); $('#vLit').textContent = lit > 0.7 ? '노출' : lit > 0.35 ? '희미' : '어둠';
    const pr = game.prompt;
    $('#prompt').classList.toggle('hidden', !pr);
    if (pr) $('#promptTxt').textContent = { water: '줍기 — 생수 500ml', bandage: '줍기 — 압박 붕대', note: '읽기 — 메모', radio: '듣기 — 무전기' }[pr.k];
    $('#alarm').classList.toggle('hidden', game.chased < 0.05);
  }
  function endScreen(kind) {
    const p = game.p, s = game.stats;
    $('#end').classList.toggle('dead', kind === 'dead');
    $('#eTitle').textContent = kind === 'dead' ? '사망' : '도달';
    $('#eCode').textContent = kind === 'dead' ? 'STATUS / 0xDEAD · 출혈성 쇼크' : 'STATUS / 0x0A · SEC 01 CLEAR';
    $('#eCause').innerHTML = kind === 'dead'
      ? `혈액량 ${Math.max(0, Math.round(p.blood))} — 양재동 ${Math.round(p.x / M)}M 지점에서 쓰러졌다.${p.exposed ? '<br/><b>광견병 노출 상태였다.</b> 살아남았더라도 PEP가 필요했다.' : ''}`
      : `양재천 둔치. 감염자들이 물가 앞에서 멈춰 경련한다 — 공수병.${p.exposed ? '<br/><b>광견병 노출.</b> 증상 전에 PEP를 찾아야 한다.' : ''}<br/>다음 구간: SEC 02 서초동 [미구현]`;
    const tt = game.t; const mm = Math.floor(tt / 60), ss = Math.floor(tt % 60);
    $('#eStats').innerHTML = [['소요', `${mm}:${String(ss).padStart(2, '0')}`], ['물림', s.bites], ['혈액량', Math.max(0, Math.round(p.blood))], ['이동', Math.round((p.x - 70) / M) + 'M']].map(([a, b]) => `<div><dt>${a}</dt><dd>${b}</dd></div>`).join('');
    setMode(kind);
  }
  requestAnimationFrame(frame);
  addEventListener('resize', () => R.resize());
}
const audio = new Audio();
const input = new Input();
boot().catch(e => { console.error(e); const l = document.querySelector('#loadPct'); if (l) l.textContent = 'ERR'; });
