/*
 * static/js/flap_sound.js — the board's flap sound: a short synthesised clack.
 *
 * window.FlapSound.clack() plays one clack, thinned into a rattle when many
 * flaps fall at once, and does nothing while the sound is off. The sound is
 * off until the person turns it on (FlapSound.toggle(), from a tap), because
 * browsers hold audio until a tap and a page shouldn't make noise unasked.
 * The same sound as the display's (static/js/splitflap.js).
 */
(() => {
  const sound = {
    on: false, ctx: null, out: null, bufs: [], last: 0,
    init() {
      if (this.ctx) return;
      const Ctx = window.AudioContext || window.webkitAudioContext;
      if (!Ctx) return;
      this.ctx = new Ctx();
      const sr = this.ctx.sampleRate;
      for (let v = 0; v < 4; v++) {
        const n = Math.floor(sr * 0.03);
        const buf = this.ctx.createBuffer(1, n, sr);
        const data = buf.getChannelData(0);
        const tone = 1500 + v * 260;
        for (let i = 0; i < n; i++) {
          const t = i / sr;
          data[i] = (Math.random() * 2 - 1) * Math.exp(-t * 380) * 0.7
            + Math.sin(2 * Math.PI * tone * t) * Math.exp(-t * 700) * 0.35
            + Math.sin(2 * Math.PI * 180 * t) * Math.exp(-t * 120) * 0.3;
        }
        this.bufs.push(buf);
      }
      this.out = this.ctx.createGain();
      this.out.gain.value = 0.5;
      const lp = this.ctx.createBiquadFilter();
      lp.type = 'lowpass'; lp.frequency.value = 6000;
      this.out.connect(lp).connect(this.ctx.destination);
    },
    // Turns the sound on or off; call it from a tap, so the browser lets it play.
    toggle() {
      this.init();
      this.ctx?.resume?.();
      this.on = !this.on;
      return this.on;
    },
    clack() {
      if (!this.on || !this.ctx) return;
      const t = this.ctx.currentTime;
      if (t - this.last < 0.005) return;
      this.last = t;
      const src = this.ctx.createBufferSource();
      src.buffer = this.bufs[(Math.random() * this.bufs.length) | 0];
      src.playbackRate.value = 0.85 + Math.random() * 0.3;
      const g = this.ctx.createGain();
      g.gain.value = 0.08 + Math.random() * 0.08;
      src.connect(g).connect(this.out);
      src.start();
    },
  };
  window.FlapSound = sound;
})();
