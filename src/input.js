// Keyboard + touch input with edge-triggered actions.
export class Input {
  constructor() {
    this.k = new Set(); this.edges = new Set(); this.touch = {};
    const map = { ArrowLeft: 'left', KeyA: 'left', ArrowRight: 'right', KeyD: 'right', ShiftLeft: 'run', ShiftRight: 'run', KeyS: 'crouch', ArrowDown: 'crouch', ControlLeft: 'crouch', KeyC: 'crouch',
      Space: 'jump', KeyW: 'jump', ArrowUp: 'jump', KeyE: 'interact', KeyQ: 'splash', KeyF: 'torch', KeyJ: 'shove', KeyR: 'bandage', Escape: 'pause', KeyP: 'pause', Enter: 'confirm' };
    this.map = map;
    addEventListener('keydown', e => { const a = map[e.code]; if (!a) return; if (!this.k.has(a)) this.edges.add(a); this.k.add(a); if (e.code === 'Space' || e.code.startsWith('Arrow')) e.preventDefault(); });
    addEventListener('keyup', e => { const a = map[e.code]; if (a) this.k.delete(a); });
    addEventListener('blur', () => this.k.clear());
    addEventListener('mousedown', e => { if (e.button === 0 && e.target.id === 'gl') { this.edges.add('shove'); } });
  }
  bindTouch(root) {
    root.querySelectorAll('[data-t]').forEach(el => {
      const a = el.dataset.t;
      const down = e => { e.preventDefault(); if (a === 'run') { this.runToggle = !this.runToggle; el.classList.toggle('on', this.runToggle); return; } this.touch[a] = true; this.edges.add(a); el.classList.add('on'); };
      const up = e => { e.preventDefault(); if (a === 'run') return; this.touch[a] = false; el.classList.remove('on'); };
      el.addEventListener('touchstart', down, { passive: false }); el.addEventListener('touchend', up, { passive: false }); el.addEventListener('touchcancel', up, { passive: false });
      el.addEventListener('mousedown', down); el.addEventListener('mouseup', up); el.addEventListener('mouseleave', up);
    });
  }
  read() {
    const h = a => this.k.has(a) || !!this.touch[a];
    const e = a => this.edges.has(a);
    const s = { left: h('left'), right: h('right'), run: h('run') || !!this.runToggle, crouch: h('crouch'), jumpPressed: e('jump'), interactPressed: e('interact'), splashPressed: e('splash'),
      torchPressed: e('torch'), shovePressed: e('shove'), bandagePressed: e('bandage'), pausePressed: e('pause'), confirmPressed: e('confirm') };
    this.edges.clear(); return s;
  }
}
