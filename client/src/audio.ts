/**
 * Sound, synthesised in the browser.
 *
 * Not one audio file in the repo: every effect is built from oscillators and
 * a noise buffer at call time. That keeps the project text-only, keeps the
 * download at zero bytes, and means a sound is tuned by changing numbers
 * rather than by re-exporting a wav.
 *
 * Muted by default. Browsers refuse to start an AudioContext without a user
 * gesture anyway, so the context is created lazily on the first unmuted
 * sound and resumed on the first interaction.
 */

const KEY = "spire.sound";

let ctx: AudioContext | null = null;
let master: GainNode | null = null;
let noise: AudioBuffer | null = null;
let drone: { stop: () => void } | null = null;
let enabled = localStorage.getItem(KEY) === "on";

export const soundOn = () => enabled;

export function setSound(on: boolean) {
  enabled = on;
  localStorage.setItem(KEY, on ? "on" : "off");
  if (!on) {
    drone?.stop();
    drone = null;
    return;
  }
  ensure();
  startDrone();
}

function ensure(): AudioContext | null {
  if (!enabled) return null;
  if (!ctx) {
    const Ctor = window.AudioContext
      ?? (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
    if (!Ctor) return null;
    ctx = new Ctor();
    master = ctx.createGain();
    master.gain.value = 0.5;
    master.connect(ctx.destination);

    // One second of white noise, reused by every percussive sound.
    const n = ctx.sampleRate;
    noise = ctx.createBuffer(1, n, n);
    const data = noise.getChannelData(0);
    for (let i = 0; i < n; i++) data[i] = Math.random() * 2 - 1;
  }
  if (ctx.state === "suspended") void ctx.resume();
  return ctx;
}

/* ── building blocks ───────────────────────────────────────── */

interface ToneOpts {
  type?: OscillatorType;
  from: number;
  to?: number;
  dur: number;
  gain?: number;
  delay?: number;
  /** Lowpass cutoff, if the tone should be dulled. */
  cut?: number;
}

function tone(o: ToneOpts) {
  const c = ensure();
  if (!c || !master) return;
  const t = c.currentTime + (o.delay ?? 0);
  const osc = c.createOscillator();
  osc.type = o.type ?? "sine";
  osc.frequency.setValueAtTime(o.from, t);
  if (o.to != null) osc.frequency.exponentialRampToValueAtTime(Math.max(1, o.to), t + o.dur);

  const g = c.createGain();
  g.gain.setValueAtTime(0.0001, t);
  g.gain.exponentialRampToValueAtTime(o.gain ?? 0.2, t + 0.008);
  g.gain.exponentialRampToValueAtTime(0.0001, t + o.dur);

  let tail: AudioNode = g;
  if (o.cut) {
    const f = c.createBiquadFilter();
    f.type = "lowpass";
    f.frequency.value = o.cut;
    g.connect(f);
    tail = f;
  }
  osc.connect(g);
  tail.connect(master);
  osc.start(t);
  osc.stop(t + o.dur + 0.02);
}

interface BurstOpts {
  dur: number;
  gain?: number;
  delay?: number;
  type?: BiquadFilterType;
  from: number;
  to?: number;
  q?: number;
}

function burst(o: BurstOpts) {
  const c = ensure();
  if (!c || !master || !noise) return;
  const t = c.currentTime + (o.delay ?? 0);
  const src = c.createBufferSource();
  src.buffer = noise;

  const f = c.createBiquadFilter();
  f.type = o.type ?? "bandpass";
  f.Q.value = o.q ?? 1;
  f.frequency.setValueAtTime(o.from, t);
  if (o.to != null) f.frequency.exponentialRampToValueAtTime(Math.max(20, o.to), t + o.dur);

  const g = c.createGain();
  g.gain.setValueAtTime(0.0001, t);
  g.gain.exponentialRampToValueAtTime(o.gain ?? 0.16, t + 0.01);
  g.gain.exponentialRampToValueAtTime(0.0001, t + o.dur);

  src.connect(f);
  f.connect(g);
  g.connect(master);
  src.start(t);
  src.stop(t + o.dur + 0.02);
}

/* ── the sounds ────────────────────────────────────────────── */

export const sfx = {
  /** A blow that landed: noise crack over a low thud. */
  hit(power = 1) {
    burst({ from: 1800, to: 260, dur: 0.14, gain: 0.2 * power, q: 0.7 });
    tone({ type: "sine", from: 140, to: 45, dur: 0.18, gain: 0.34 * power, cut: 500 });
  },
  /** A blow that Block ate: metal, not meat. */
  blocked() {
    tone({ type: "triangle", from: 900, to: 780, dur: 0.16, gain: 0.12 });
    tone({ type: "triangle", from: 1350, to: 1180, dur: 0.12, gain: 0.07, delay: 0.01 });
    burst({ from: 3200, to: 1600, dur: 0.09, gain: 0.07, q: 2 });
  },
  /** Block going up. */
  guard() {
    tone({ type: "triangle", from: 320, to: 620, dur: 0.2, gain: 0.11 });
    burst({ from: 900, to: 2400, dur: 0.14, gain: 0.05, q: 1.4 });
  },
  /** A card leaving the hand. */
  card() {
    burst({ from: 700, to: 2600, dur: 0.13, gain: 0.07, q: 0.8 });
  },
  /** Energy spent. */
  spend() {
    tone({ type: "square", from: 520, to: 300, dur: 0.09, gain: 0.05, cut: 1600 });
  },
  /** Something died. */
  death() {
    tone({ type: "sawtooth", from: 220, to: 32, dur: 0.7, gain: 0.16, cut: 900 });
    burst({ from: 1200, to: 120, dur: 0.8, gain: 0.11, q: 0.6 });
  },
  heal() {
    tone({ type: "sine", from: 440, to: 660, dur: 0.22, gain: 0.1 });
    tone({ type: "sine", from: 660, to: 880, dur: 0.24, gain: 0.07, delay: 0.08 });
  },
  /** A status applied. */
  hex() {
    tone({ type: "triangle", from: 300, to: 180, dur: 0.26, gain: 0.08, cut: 1200 });
  },
  /** Cards dealt at the start of a turn. */
  deal(i: number) {
    burst({ from: 900, to: 2200, dur: 0.07, gain: 0.045, q: 1.2, delay: i * 0.045 });
  },
};

/* ── ambience ──────────────────────────────────────────────── */

/** Two detuned drones and a breath of filtered noise, very low. Rooms have a
 *  sound; silence is a choice the player did not make. */
function startDrone() {
  const c = ensure();
  if (!c || !master || !noise || drone) return;

  const g = c.createGain();
  g.gain.value = 0;
  g.gain.linearRampToValueAtTime(0.05, c.currentTime + 3);
  g.connect(master);

  const oscs = [55, 55.4, 82.5].map((hz, i) => {
    const o = c.createOscillator();
    o.type = i === 2 ? "triangle" : "sine";
    o.frequency.value = hz;
    const og = c.createGain();
    og.gain.value = i === 2 ? 0.25 : 0.6;
    o.connect(og);
    og.connect(g);
    o.start();
    return o;
  });

  const air = c.createBufferSource();
  air.buffer = noise;
  air.loop = true;
  const f = c.createBiquadFilter();
  f.type = "lowpass";
  f.frequency.value = 380;
  const ag = c.createGain();
  ag.gain.value = 0.12;
  air.connect(f);
  f.connect(ag);
  ag.connect(g);
  air.start();

  drone = {
    stop() {
      const end = c.currentTime + 0.6;
      g.gain.linearRampToValueAtTime(0, end);
      oscs.forEach((o) => o.stop(end + 0.05));
      air.stop(end + 0.05);
    },
  };
}

/** Browsers will not start audio without a gesture; catch the first one. */
export function wireAudioUnlock() {
  const unlock = () => {
    if (enabled) { ensure(); startDrone(); }
  };
  document.addEventListener("pointerdown", unlock, { once: false });
  document.addEventListener("keydown", unlock, { once: false });
}
