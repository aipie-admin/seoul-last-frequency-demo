// Pure gameplay state: physics, player survival stats, infected AI (GDD §6.7), items.
export const M = 28; // px per metre
const clamp = (v, a, b) => Math.max(a, Math.min(b, v));

export class Game {
  constructor(world, sprites, audio, log, piles = []) {
    this.piles = piles; this.w = world; this.sp = sprites; this.audio = audio; this.log = log;
    this.reset();
  }
  ground(x) {
    const w = this.w;
    if (x < w.slope0) return w.feet;
    if (x < w.slope1) { const t = (x - w.slope0) / (w.slope1 - w.slope0); return w.feet + (w.low - w.feet) * (0.5 - 0.5 * Math.cos(t * Math.PI)); }
    return w.low;
  }
  reset() {
    const w = this.w;
    this.t = 0; this.over = null; this.stats = { bites: 0, shoves: 0, splashes: 0, items: 0 };
    this.p = {
      x: 70, y: w.feet, vx: 0, vy: 0, face: 1, onGround: true, crouch: false, run: false,
      blood: 100, stamina: 100, temp: 36.6, bleed: 0, exposed: false, water: 1, bandage: 0,
      torch: true, anim: 'idle', animT: 0, actT: 0, act: null, hurtT: 0, landT: 0, noise: 0, noiseShow: 0, lit: 0, dead: false, coyote: 0, jumpBuf: 0, invT: 0,
    };
    // props: [key, x]
    const P = [['car_white', 760], ['barricade', 1640], ['car_dark', 2050], ['car_taxi', 2950], ['ambulance', 3700], ['car_red', 4560]];
    this.props = P.map(([k, x]) => {
      const s = this.sp[k]; const top = w.feet - s.h + 1;
      const b = s.solid;
      return { k, x, y: top, w: s.w, h: s.h, solid: { x0: x + b[0], y0: top + b[1], x1: x + b[2], y1: top + b[3] } };
    });
    this.solids = this.props.map(p => p.solid);
    this.barrels = [{ x: 3400 }, { x: 5010 }].map(b => ({ ...b, y: w.feet - 44 + 1 }));
    const I = [['water', 980], ['note', 1320, 0], ['water', 1950], ['bandage', 2700], ['radio', 3300, 1], ['water', 3480], ['bandage', 4400], ['note', 5250, 2]];
    this.items = I.map(([k, x, n]) => ({ k, x, y: this.ground(x), taken: false, note: n }));
    const E = [['inf_b', 1180], ['inf_a', 2600], ['inf_d', 2420], ['inf_c', 2880], ['inf_b', 3600], ['inf_a', 3920], ['inf_d', 4140], ['inf_c', 4700], ['inf_a', 4930], ['inf_b', 5160], ['inf_c', 5330]];
    this.enemies = E.map(([k, x], i) => ({
      id: i, k, x, y: w.feet, vx: 0, vy: 0, home: x, face: i % 2 ? 1 : -1, para: k === 'inf_d',
      state: k === 'inf_d' ? 'lie' : 'idle', st: Math.random() * 2, anim: k === 'inf_d' ? 'lie' : 'idle', animT: Math.random(), cd: 0, lungeCd: 0, blocked: 0, seen: false,
      wanderTo: x, speedMul: 0.9 + Math.random() * 0.2, bang: 0,
    }));
    this.splashes = [];
    this.shake = 0; this.flash = 0;
    this.prompt = null;
    this.chased = 0;
    this.rain = { on: false, t: 0, next: 9999, scripted: false, dur: 0 };
    this.pileLogged = false;
  }
  // -------------------------------------------------------------------------------------
  collideX(o, hw, hh, dx) {
    o.x += dx;
    for (const s of this.solids) {
      if (o.y > s.y0 + 0.5 && o.y - hh < s.y1 && o.x + hw > s.x0 && o.x - hw < s.x1) {
        if (dx > 0) o.x = s.x0 - hw; else if (dx < 0) o.x = s.x1 + hw;
        return s;
      }
    }
    return null;
  }
  collideY(o, hw, hh, dy) {
    o.y += dy; let landed = false;
    const g = this.ground(o.x);
    if (o.y >= g) { o.y = g; landed = true; }
    for (const s of this.solids) {
      if (o.x + hw > s.x0 && o.x - hw < s.x1) {
        if (dy >= 0 && o.y >= s.y0 && o.y - dy <= s.y0 + 1) { o.y = s.y0; landed = true; }
        else if (dy < 0 && o.y - hh < s.y1 && o.y - hh - dy >= s.y1 - 1 && o.y > s.y1) { o.y = s.y1 + hh; o.vy = 0; }
      }
    }
    return landed;
  }
  inLight(x, y, lights) {
    let L = 0;
    for (const l of lights) { if (l.player) continue; const d = Math.hypot(l.x - x, l.y - (y - 24)); if (d < l.r) L = Math.max(L, (1 - d / l.r) * l.i); }
    return L;
  }
  // -------------------------------------------------------------------------------------
  update(dt, inp, lights) {
    if (this.over) { this.p.animT += dt; return; }
    this.t += dt;
    const p = this.p, w = this.w;
    p.animT += dt; p.invT -= dt; p.hurtT -= dt; p.landT -= dt; p.actT -= dt; p.coyote -= dt; p.jumpBuf -= dt;
    if (p.actT <= 0) p.act = null;
    const busy = p.act !== null || p.hurtT > 0;
    // crouch (height check under solids)
    const wantCrouch = inp.crouch && p.onGround;
    if (wantCrouch) p.crouch = true;
    else if (p.crouch) { // can we stand?
      const hw = 6; let blocked = false;
      for (const s of this.solids) if (p.x + hw > s.x0 && p.x - hw < s.x1 && p.y - 44 < s.y1 && p.y > s.y1) blocked = true;
      if (!blocked) p.crouch = false;
    }
    let dir = (inp.right ? 1 : 0) - (inp.left ? 1 : 0);
    if (busy && p.act !== 'interact') dir = 0;
    p.run = inp.run && dir !== 0 && !p.crouch && p.stamina > 1;
    const sp = p.crouch ? 30 : p.run ? 128 : 62;
    const target = dir * sp;
    const acc = p.onGround ? 900 : 420;
    p.vx += clamp(target - p.vx, -acc * dt, acc * dt);
    if (dir) p.face = dir;
    // jump
    if (inp.jumpPressed) p.jumpBuf = 0.15;
    if (p.onGround) p.coyote = 0.1;
    if (p.jumpBuf > 0 && p.coyote > 0 && !p.crouch && !busy && p.stamina > 8) {
      p.vy = -305; p.onGround = false; p.coyote = 0; p.jumpBuf = 0; p.stamina -= 10; this.audio.jump();
    }
    p.vy += 980 * dt; if (p.vy > 600) p.vy = 600;
    const hh = p.crouch ? 28 : 44, hw = 6;
    this.collideX(p, hw, hh, p.vx * dt);
    p.x = clamp(p.x, 10, w.water - 8);
    const wasAir = !p.onGround; const vyBefore = p.vy;
    const landed = this.collideY(p, hw, hh, p.vy * dt);
    if (landed) { if (wasAir && vyBefore > 150) { p.landT = 0.12; this.emitNoise(5 * M * Math.min(1.5, vyBefore / 300)); this.audio.step(1.4); } p.vy = 0; p.onGround = true; }
    else p.onGround = false;
    // stamina
    if (p.run) p.stamina -= 17 * dt;
    else p.stamina += (p.crouch ? 16 : 13) * dt * (Math.abs(p.vx) < 5 ? 1.4 : 1);
    p.stamina = clamp(p.stamina, 0, 100);
    // weather: autumn showers. Rain = infected falter (safe window)
    const rn = this.rain;
    if (!rn.scripted && p.x > 2250) { rn.scripted = true; this.startRain(13); }
    if (rn.on) { rn.t -= dt; if (rn.t <= 0) { rn.on = false; rn.next = 45 + Math.random() * 30; this.log('비 그침 — 감염자들이 다시 움직인다', 'alert'); } }
    else if (rn.scripted) { rn.next -= dt; if (rn.next <= 0) this.startRain(10 + Math.random() * 4); }
    // bleeding
    if (p.bleed > 0) { p.blood -= p.bleed * dt; p.bleed = Math.max(0, p.bleed - 0.12 * dt); }
    // noise this frame
    const moving = Math.abs(p.vx) > 8 && p.onGround;
    let nz = moving ? (p.crouch ? 0.7 * M : p.run ? 9 * M : 3 * M) : 0;
    const onPile = this.piles.some(([a, b]) => p.x > a && p.x < b) && p.onGround;
    if (onPile && moving) { nz = nz * 1.9 + 2 * M; if (!this.pileLogged) { this.pileLogged = true; this.log('낙엽 더미 — 발소리가 커진다. 웅크려도 소리가 난다', 'alert'); } }
    p.onPile = onPile;
    p.noise = Math.max(nz, p.noise - 300 * dt);
    p.noiseShow = Math.max(p.noise, p.noiseShow - 140 * dt);
    if (moving) { p.stepAcc = (p.stepAcc || 0) + Math.abs(p.vx) * dt; if (p.stepAcc > (p.run ? 26 : 22)) { p.stepAcc = 0; this.audio.step((p.crouch ? 0.35 : p.run ? 1.1 : 0.7) * (onPile ? 1.8 : 1), onPile); } }
    // actions
    if (inp.torchPressed) { p.torch = !p.torch; this.audio.click(); this.log(p.torch ? '손전등 ON — 시야 확보, 감염자 주의 유발' : '손전등 OFF — 어둠 속 은신'); }
    if (inp.shovePressed && !busy && p.stamina >= 20) this.shove();
    if (inp.splashPressed && !busy) this.splash();
    if (inp.bandagePressed && !busy) this.useBandage();
    // interact prompt
    this.prompt = null;
    for (const it of this.items) if (!it.taken && Math.abs(it.x - p.x) < 20 && Math.abs(it.y - p.y) < 30) { this.prompt = it; break; }
    if (inp.interactPressed && this.prompt && !busy) this.take(this.prompt);
    p.lit = this.inLight(p.x, p.y, lights) + (p.torch ? 0.6 : 0);
    // anim
    let a = 'idle';
    if (p.dead) a = 'dead';
    else if (p.hurtT > 0) a = 'hurt';
    else if (p.act) a = p.act;
    else if (!p.onGround) a = 'jump';
    else if (p.landT > 0) a = 'land';
    else if (p.crouch) a = Math.abs(p.vx) > 4 ? 'crouchwalk' : 'crouch';
    else if (Math.abs(p.vx) > 4) a = p.run || Math.abs(p.vx) > 90 ? 'run' : 'walk';
    if (a !== p.anim) { p.anim = a; p.animT = 0; }
    // enemies
    this.chased = 0;
    for (const e of this.enemies) this.updateEnemy(e, dt);
    // separation
    for (let i = 0; i < this.enemies.length; i++) for (let j = i + 1; j < this.enemies.length; j++) {
      const a1 = this.enemies[i], b1 = this.enemies[j]; const d = b1.x - a1.x;
      if (Math.abs(d) < 12 && a1.state !== 'lie' && b1.state !== 'lie') { const push = (12 - Math.abs(d)) * 0.5 * Math.sign(d || 1); a1.x -= push; b1.x += push; }
    }
    for (const s of this.splashes) s.t += dt; this.splashes = this.splashes.filter(s => s.t < 0.8);
    this.shake = Math.max(0, this.shake - dt * 6); this.flash = Math.max(0, this.flash - dt * 3);
    // end conditions
    if (p.blood <= 25 && !p.dead) { p.dead = true; p.anim = 'dead'; p.animT = 0; this.audio.death(); setTimeout(() => { this.over = 'dead'; }, 1600); this.overPending = 'dead'; }
    if (!p.dead && p.x >= w.goal && !this.overPending) { this.overPending = 'win'; this.audio.win(); setTimeout(() => { this.over = 'win'; }, 900); }
  }
  startRain(d) { const r = this.rain; r.on = true; r.t = d; r.dur = d; this.audio.rain?.(d); this.log('비 — 감염자들이 빗속에서 움츠러든다. 지금 지나가라', 'safe'); }
  emitNoise(r) { this.p.noise = Math.max(this.p.noise, r); }
  shove() {
    const p = this.p; p.act = 'shove'; p.actT = 0.32; p.animT = 0; p.stamina -= 20; this.stats.shoves++;
    this.emitNoise(5 * M); this.audio.shove();
    for (const e of this.enemies) {
      const dx = (e.x - p.x) * p.face;
      if (dx > -4 && dx < 34 && Math.abs(e.y - p.y) < 30 && e.state !== 'lie') { e.state = 'stagger'; e.st = 0.9; e.vx = p.face * 150; e.face = -p.face; this.shake = 0.4; }
    }
  }
  splash() {
    const p = this.p;
    if (p.water <= 0) { this.log('물이 없다.'); this.audio.click(); return; }
    p.water--; p.act = 'splash'; p.actT = 0.34; p.animT = 0; this.stats.splashes++;
    this.emitNoise(4 * M); this.audio.splash();
    this.splashes.push({ x: p.x + p.face * 16, y: p.y - 30, face: p.face, t: 0 });
    let hit = 0;
    for (const e of this.enemies) {
      const dx = (e.x - p.x) * p.face;
      if (dx > -6 && dx < 52 && Math.abs(e.y - p.y) < 34) { e.state = 'convulse'; e.st = 3.0; e.vx = p.face * 40; e.face = -p.face; hit++; this.audio.screech(0.6); }
    }
    this.log(hit ? `물 500ml 투척 — 감염자 ${hit} 경련(공수병)` : '물 500ml 투척 — 빗나감');
  }
  useBandage() {
    const p = this.p;
    if (p.bandage <= 0) { this.log('붕대 없음.'); this.audio.click(); return; }
    if (p.bleed <= 0 && p.blood >= 100) { this.log('출혈 없음.'); return; }
    p.bandage--; p.bleed = 0; p.blood = Math.min(100, p.blood + 12); p.act = 'interact'; p.actT = 0.6; p.animT = 0; this.audio.pickup();
    this.log('붕대 감음 — 출혈 정지, 혈액량 +12');
  }
  take(it) {
    const p = this.p; it.taken = true; this.stats.items++; p.act = 'interact'; p.actT = 0.4; p.animT = 0; this.audio.pickup();
    if (it.k === 'water') { p.water++; this.log('획득: 생수 500ml — [Q] 감염자에게 뿌리면 경련'); }
    if (it.k === 'bandage') { p.bandage++; this.log('획득: 압박 붕대 — [R] 출혈 정지'); }
    if (it.k === 'note' || it.k === 'radio') this.log(NOTES[it.note], 'note');
  }
  // -------------------------------------------------------------------------------------
  updateEnemy(e, dt) {
    const p = this.p, w = this.w;
    e.animT += dt; e.cd -= dt; e.lungeCd -= dt; e.st -= dt;
    const dx = p.x - e.x, adx = Math.abs(dx), dy = Math.abs(p.y - e.y);
    const HYD = w.water - 10 * M; // 공수병 회피 반경 10m
    const nearWater = e.x > HYD - 6;
    const night = 1.0, winter = 0.8;
    const walkV = 1.2 * M * winter * e.speedMul, chaseV = 2.1 * M * e.speedMul, lungeV = 4.0 * M;
    // perception
    const facing = Math.sign(dx) === e.face;
    let sight = (4 + 6 * Math.min(1.2, p.lit)) * M * (p.crouch ? 0.6 : 1);
    const sees = !p.dead && facing && adx < sight && dy < 60;
    const hears = !p.dead && p.noise * (this.rain.on ? 0.4 : 1) > adx && dy < 80;
    const close = !p.dead && adx < 1.2 * M && dy < 40;
    const aware = sees || hears || close;
    let mv = 0, anim = 'idle';
    if (this.rain.on && !['lie', 'rise', 'cower', 'hydro'].includes(e.state) && Math.abs(e.x - p.x) < 700) { e.state = 'cower'; e.st = 0.8 + Math.random() * 1.2; this.audio.screech(0.25); }
    switch (e.state) {
      case 'cower': {
        // 빗속 위축: 경련 후 웅크린 채 뒷걸음, 추격 중단
        anim = e.st > 0 || Math.sin(this.t * 3 + e.id) > 0.85 ? 'convulse' : 'idle';
        e.face = Math.sign(dx) || e.face; mv = adx < 160 ? -e.face * 14 : 0;
        if (!this.rain.on) { e.state = 'search'; e.st = 2; e.home = e.x; }
        break;
      }
      case 'lie': {
        anim = 'lie';
        if (!p.dead && adx < (p.crouch ? 0.8 : 1.4) * M && dy < 30) { e.state = 'rise'; e.st = 0.5; e.face = Math.sign(dx) || 1; this.audio.screech(0.9); }
        else if (hears && p.noise > 6 * M) { e.state = 'rise'; e.st = 0.7; e.face = Math.sign(dx) || 1; }
        break;
      }
      case 'rise': anim = 'rise'; if (e.st <= 0) { e.state = 'chase'; } break;
      case 'idle': case 'wander': case 'search': {
        anim = 'idle';
        if (aware) { e.state = 'alert'; e.st = 0.45; e.face = Math.sign(dx) || 1; this.audio.screech(Math.max(0.2, 1 - adx / 600)); break; }
        if (e.st <= 0) { e.wanderTo = e.home + (Math.random() * 160 - 80); e.st = 2 + Math.random() * 4; }
        const d = e.wanderTo - e.x;
        if (Math.abs(d) > 4 && e.st < 3) { mv = Math.sign(d) * walkV * 0.7; anim = 'walk'; }
        break;
      }
      case 'alert': anim = 'idle'; e.face = Math.sign(dx) || e.face; if (e.st <= 0) e.state = 'chase'; break;
      case 'chase': {
        this.chased = Math.max(this.chased, 1 - adx / 500);
        e.face = Math.sign(dx) || e.face;
        if (!aware && adx > 12 * M) { e.lost = (e.lost || 0) + dt; if (e.lost > 4) { e.state = 'search'; e.home = e.x; e.st = 3; e.lost = 0; } } else e.lost = 0;
        const v = e.para ? 0.75 * M : chaseV;
        mv = e.face * v; anim = e.para ? 'crawl' : 'run';
        if (!e.para && adx < 3.2 * M && adx > 0.8 * M && e.lungeCd <= 0 && dy < 20) { e.state = 'lunge'; e.st = 0.62; e.lungeCd = 3.2; this.audio.screech(1); }
        if (adx < 15 && dy < 36 && e.cd <= 0 && !p.dead) this.bite(e);
        break;
      }
      case 'lunge': mv = e.face * lungeV; anim = 'lunge'; if (adx < 15 && dy < 36 && e.cd <= 0) this.bite(e); if (e.st <= 0) { e.state = 'rest'; e.st = 1.1; } break;
      case 'rest': mv = e.face * 8; anim = 'idle'; if (e.st <= 0) e.state = 'chase'; if (adx < 15 && dy < 36 && e.cd <= 0) this.bite(e); break;
      case 'bite': anim = 'bite'; if (e.st <= 0) e.state = 'chase'; break;
      case 'stagger': anim = 'stagger'; e.vx *= Math.pow(0.02, dt); mv = e.vx; if (e.st <= 0) { e.state = 'chase'; } break;
      case 'convulse': anim = 'convulse'; e.vx *= Math.pow(0.05, dt); mv = e.vx; if (e.st <= 0) { e.state = 'chase'; e.lungeCd = 1.5; } break;
      case 'hydro': {
        // 공수병: 물가 접근 불가 — 경련 후 물러나 노려봄
        anim = e.st > 0 ? 'convulse' : 'idle'; mv = e.st > 0 ? -18 : 0; e.face = 1;
        if (e.st <= 0 && p.x < HYD - 30 && aware) e.state = 'chase';
        break;
      }
    }
    if (e.para && anim === 'run') anim = 'crawl';
    if (e.para && (anim === 'walk' || anim === 'lunge')) anim = 'crawl';
    if (e.para && !['lie', 'rise', 'crawl', 'bite', 'stagger', 'convulse'].includes(anim)) anim = 'crawl';
    // hydrophobia boundary
    if (e.x + mv * dt > HYD && mv > 0 && e.state !== 'hydro') {
      e.state = 'hydro'; e.st = 1.4; mv = 0; this.audio.screech(0.5);
      if (!this.hydroLogged) { this.hydroLogged = true; this.log('감염자가 물가 앞에서 경련한다 — 공수병. 물가로!', 'safe'); }
    }
    // move & collide
    const hw = 6, hh = e.para && e.state !== 'chase' ? 20 : 44;
    const before = e.x;
    const hit = this.collideX(e, hw, e.para ? 22 : hh, mv * dt);
    if (hit && (e.state === 'chase' || e.state === 'lunge')) {
      const height = this.ground(e.x) - hit.y0;
      e.blocked += dt;
      if (height < 48 && e.blocked > 0.5 && e.vy === 0 && !e.para) { e.vy = -290; e.blocked = 0; }   // vault over cars
      else if (height >= 48) { e.bang -= dt; if (e.bang <= 0) { e.bang = 0.9; this.audio.bang(Math.max(0.1, 1 - adx / 500)); } anim = e.para ? 'crawl' : 'bite'; } // barricade: can't pass gap
    } else e.blocked = 0;
    e.vy += 980 * dt;
    if (this.collideY(e, hw, 30, e.vy * dt)) e.vy = 0;
    if (e.x > HYD + 2) e.x = HYD + 2;
    if (anim !== e.anim) { e.anim = anim; e.animT = 0; }
  }
  bite(e) {
    const p = this.p;
    e.cd = 1.5; e.state = 'bite'; e.st = 0.5;
    if (p.invT > 0 || this.god) return;
    p.invT = 0.9; p.hurtT = 0.35; p.blood -= 13; p.bleed = Math.min(4, p.bleed + 1.5); p.vx = p.x > e.x ? 160 : -160; p.vy = -120; p.onGround = false;
    this.stats.bites++; this.shake = 1; this.flash = 1; this.audio.bite();
    if (!p.exposed) { p.exposed = true; this.log('물렸다 — 광견병 노출. 증상 전 PEP만 유효.', 'alert'); }
    else this.log('물림 — 출혈 증가', 'alert');
  }
}

export const NOTES = [
  '[메모 · 3층 현관] 김씨네 아들, 물린 지 이틀. 열, 침. 물컵을 보고 목이 조여 경련. 문은 밖에서 잠갔음.',
  '[무전 · 147.2MHz] "…물가에는 안 온다. 양재천 둔치로 내려가. 한강만 가면 산다…" (반복)',
  '[전단] 양재천 산책로 임시 대피 — 감염자는 열린 물을 피함. 결빙 구간 주의. 반포·잠원 집결.',
];
