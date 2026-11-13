// Procedural WebAudio: wind bed, snow footsteps, infected screeches, heartbeat.
export class Audio {
  constructor() { this.ctx = null; this.on = true; }
  start() {
    if (this.ctx) return;
    const C = window.AudioContext || window.webkitAudioContext; if (!C) return;
    this.ctx = new C(); const c = this.ctx;
    this.master = c.createGain(); this.master.gain.value = 0.7; this.master.connect(c.destination);
    const len = c.sampleRate * 2; const b = c.createBuffer(1, len, c.sampleRate); const d = b.getChannelData(0);
    for (let i = 0; i < len; i++) d[i] = Math.random() * 2 - 1; this.noiseBuf = b;
    // wind
    const n = c.createBufferSource(); n.buffer = b; n.loop = true;
    const f = c.createBiquadFilter(); f.type = 'bandpass'; f.frequency.value = 420; f.Q.value = 0.6;
    const g = c.createGain(); g.gain.value = 0.10;
    const lfo = c.createOscillator(); lfo.frequency.value = 0.09; const lg = c.createGain(); lg.gain.value = 260; lfo.connect(lg); lg.connect(f.frequency);
    const lfo2 = c.createOscillator(); lfo2.frequency.value = 0.13; const lg2 = c.createGain(); lg2.gain.value = 0.05; lfo2.connect(lg2); lg2.connect(g.gain);
    n.connect(f); f.connect(g); g.connect(this.master); n.start(); lfo.start(); lfo2.start();
    // heartbeat bus
    this.hb = 0; this.hbT = 0;
  }
  noise(dur, freq, q, gain, type = 'bandpass', sweep = 0) {
    const c = this.ctx; if (!c) return;
    const s = c.createBufferSource(); s.buffer = this.noiseBuf; s.playbackRate.value = 0.8 + Math.random() * 0.4;
    const f = c.createBiquadFilter(); f.type = type; f.frequency.value = freq; f.Q.value = q;
    if (sweep) f.frequency.exponentialRampToValueAtTime(Math.max(40, freq * sweep), c.currentTime + dur);
    const g = c.createGain(); g.gain.setValueAtTime(gain, c.currentTime); g.gain.exponentialRampToValueAtTime(0.001, c.currentTime + dur);
    s.connect(f); f.connect(g); g.connect(this.master); s.start(c.currentTime, Math.random()); s.stop(c.currentTime + dur + 0.05);
  }
  tone(freq, dur, gain, type = 'sine', to = 0) {
    const c = this.ctx; if (!c) return;
    const o = c.createOscillator(); o.type = type; o.frequency.value = freq; if (to) o.frequency.exponentialRampToValueAtTime(to, c.currentTime + dur);
    const g = c.createGain(); g.gain.setValueAtTime(gain, c.currentTime); g.gain.exponentialRampToValueAtTime(0.001, c.currentTime + dur);
    o.connect(g); g.connect(this.master); o.start(); o.stop(c.currentTime + dur + 0.05);
  }
  step(k = 1, leaves = false) {
    if (leaves) { this.noise(0.22, 3200 + Math.random() * 1500, 0.5, 0.09 * k, 'highpass', 0.6); this.noise(0.12, 1400, 0.8, 0.06 * k, 'bandpass'); return; }
    this.noise(0.05, 900 + Math.random() * 300, 1.2, 0.07 * k, 'bandpass'); this.noise(0.05, 220, 1, 0.08 * k, 'lowpass'); }
  rain(d) {
    const c = this.ctx; if (!c) return;
    const s = c.createBufferSource(); s.buffer = this.noiseBuf; s.loop = true;
    const f = c.createBiquadFilter(); f.type = 'highpass'; f.frequency.value = 1800;
    const g = c.createGain(); const now = c.currentTime; g.gain.setValueAtTime(0.0001, now); g.gain.exponentialRampToValueAtTime(0.14, now + 1.5); g.gain.setValueAtTime(0.14, now + d - 1.5); g.gain.exponentialRampToValueAtTime(0.0001, now + d);
    s.connect(f); f.connect(g); g.connect(this.master); s.start(); s.stop(now + d + 0.1);
  }
  jump() { this.noise(0.12, 900, 0.7, 0.08); }
  click() { this.tone(1400, 0.04, 0.05, 'square'); }
  pickup() { this.tone(660, 0.07, 0.06, 'square'); setTimeout(() => this.tone(990, 0.09, 0.05, 'square'), 70); }
  shove() { this.noise(0.18, 300, 0.8, 0.25, 'lowpass'); }
  splash() { this.noise(0.5, 2500, 0.5, 0.18, 'highpass', 0.4); }
  bite() { this.noise(0.25, 200, 0.7, 0.5, 'lowpass'); this.tone(90, 0.3, 0.3, 'sine', 50); }
  bang(v) { this.noise(0.14, 160, 1, 0.35 * v, 'lowpass'); }
  headbang() {
    this.noise(0.32, 80, 0.7, 0.6, 'lowpass');
    this.noise(0.22, 200, 1.1, 0.42, 'lowpass');
    this.tone(68, 0.28, 0.32, 'sine', 36);
    this.noise(0.14, 2000, 0.7, 0.14, 'highpass', 0.45);
  }
  screech(v = 1) {
    const c = this.ctx; if (!c || v < 0.05) return; const now = c.currentTime;
    if (this._lastScreech && now - this._lastScreech < 0.4) return; this._lastScreech = now;
    const o = c.createOscillator(); o.type = 'sawtooth'; const base = 380 + Math.random() * 220; o.frequency.setValueAtTime(base, now); o.frequency.exponentialRampToValueAtTime(base * 0.55, now + 0.6);
    const vib = c.createOscillator(); vib.frequency.value = 23; const vg = c.createGain(); vg.gain.value = 40; vib.connect(vg); vg.connect(o.frequency);
    const f = c.createBiquadFilter(); f.type = 'bandpass'; f.frequency.value = 1200; f.Q.value = 2;
    const g = c.createGain(); g.gain.setValueAtTime(0.0001, now); g.gain.exponentialRampToValueAtTime(0.12 * v, now + 0.05); g.gain.exponentialRampToValueAtTime(0.001, now + 0.65);
    o.connect(f); f.connect(g); g.connect(this.master); o.start(); vib.start(); o.stop(now + 0.7); vib.stop(now + 0.7);
    this.noise(0.5, 2200, 1.5, 0.05 * v, 'bandpass', 0.5);
  }
  death() { this.tone(110, 1.6, 0.25, 'sawtooth', 40); }
  win() { [523, 659, 784].forEach((f, i) => setTimeout(() => this.tone(f, 0.5, 0.06, 'triangle'), i * 140)); }
  update(dt, chased) {
    if (!this.ctx) return;
    this.hbT -= dt;
    if (chased > 0.05 && this.hbT <= 0) { this.hbT = 0.75 - chased * 0.35; this.tone(55, 0.12, 0.35 * chased, 'sine', 40); setTimeout(() => this.tone(50, 0.1, 0.25 * chased, 'sine', 38), 140); }
  }
}
