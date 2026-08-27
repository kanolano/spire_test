/**
 * One canvas for everything that drifts, sparks or burns off.
 *
 * This replaces the eight `<i>` elements in the shell that were the entire
 * ambience budget: eight fixed columns, each on a hard-coded CSS animation, so
 * the ash always rose in the same eight places and nothing else could ever
 * emit a particle. A canvas costs one element and can be aimed — a blow that
 * lands throws sparks off the thing it hit, and a creature that dies goes up
 * as motes from where it stood.
 *
 * Bounded on purpose: a hard particle cap, no work at all while the tab is
 * hidden, and nothing mounted under reduced motion — where the whole point is
 * that the screen holds still.
 */

import { reducedMotion } from "./director";

/** Above the stage so sparks are not hidden behind the sprite that threw
 *  them, below the top bar, toasts and the overlay. */
const Z = 5;
const MAX = 280;

type Kind = "ash" | "spark" | "mote";

interface P {
  x: number; y: number;
  vx: number; vy: number;
  r: number;
  age: number;
  life: number;
  col: [number, number, number];
  kind: Kind;
  /** Phase for the sideways sway, so ash does not rise in straight lines. */
  ph: number;
}

const EMBER: [number, number, number] = [255, 150, 78];
const PALE: [number, number, number] = [214, 203, 180];
const BLOOD: [number, number, number] = [255, 123, 98];
const STEEL: [number, number, number] = [150, 211, 236];

let canvas: HTMLCanvasElement | null = null;
let ctx: CanvasRenderingContext2D | null = null;
let ps: P[] = [];
let raf = 0;
let last = 0;
let sinceAsh = 0;
let w = 0;
let h = 0;

const rand = (a: number, b: number) => a + Math.random() * (b - a);

/** Never grow past the cap: the oldest ambient particle gives way first, and
 *  a burst is never dropped in favour of drifting ash. */
function push(p: P) {
  if (ps.length >= MAX) {
    const i = ps.findIndex((q) => q.kind === "ash");
    if (i >= 0) ps.splice(i, 1);
    else return;
  }
  ps.push(p);
}

export function mountParticles(): void {
  if (canvas || reducedMotion()) return;

  canvas = document.createElement("canvas");
  canvas.id = "particles";
  canvas.setAttribute("aria-hidden", "true");
  canvas.style.cssText =
    `position:fixed;inset:0;pointer-events:none;z-index:${Z}`;
  document.body.appendChild(canvas);
  ctx = canvas.getContext("2d");

  resize();
  window.addEventListener("resize", resize);
  // A hidden tab still fires rAF in some browsers and none in others; either
  // way there is nothing to draw, and no reason to keep integrating.
  document.addEventListener("visibilitychange", () => {
    if (document.hidden) stop(); else start();
  });
  start();
}

function resize() {
  if (!canvas || !ctx) return;
  const dpr = Math.min(2, window.devicePixelRatio || 1);
  w = window.innerWidth;
  h = window.innerHeight;
  canvas.width = Math.floor(w * dpr);
  canvas.height = Math.floor(h * dpr);
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
}

function start() {
  if (raf || !canvas) return;
  last = performance.now();
  raf = requestAnimationFrame(frame);
}

function stop() {
  cancelAnimationFrame(raf);
  raf = 0;
}

/* ── emitters ──────────────────────────────────────────────── */

/** The ambient drift: embers climbing the screen, from anywhere along it. */
function ash() {
  push({
    x: rand(0, w), y: h + 6,
    vx: rand(-6, 6), vy: rand(-26, -11),
    r: rand(0.8, 1.9), age: 0, life: rand(7, 13),
    col: EMBER, kind: "ash", ph: rand(0, 6.28),
  });
}

/**
 * A blow landing. `power` scales the count, so a big hit throws more.
 * Blocked hits spark steel-coloured instead of red — the same distinction the
 * audio makes between meat and metal.
 */
export function sparks(anchor: Element, power = 1, blocked = false): void {
  if (!canvas) return;
  const r = anchor.getBoundingClientRect();
  const n = Math.round(Math.min(26, 8 + power * 12));
  for (let i = 0; i < n; i++) {
    const a = rand(0, Math.PI * 2);
    const sp = rand(60, 260) * (blocked ? 0.7 : 1);
    push({
      x: r.left + r.width / 2 + rand(-8, 8),
      y: r.top + r.height * 0.45 + rand(-10, 10),
      vx: Math.cos(a) * sp, vy: Math.sin(a) * sp - 40,
      r: rand(1, 2.4), age: 0, life: rand(0.35, 0.75),
      col: blocked ? STEEL : BLOOD, kind: "spark", ph: 0,
    });
  }
}

/** Something died. What is left of it goes up. */
export function motes(anchor: Element): void {
  if (!canvas) return;
  const r = anchor.getBoundingClientRect();
  for (let i = 0; i < 22; i++) {
    push({
      x: r.left + rand(0, r.width),
      y: r.top + rand(r.height * 0.35, r.height),
      vx: rand(-14, 14), vy: rand(-46, -16),
      r: rand(0.9, 2.2), age: 0, life: rand(0.9, 1.7),
      col: i % 3 ? PALE : EMBER, kind: "mote", ph: rand(0, 6.28),
    });
  }
}

/* ── the loop ──────────────────────────────────────────────── */

function frame(now: number) {
  raf = requestAnimationFrame(frame);
  if (!ctx) return;

  // Clamped: coming back from a background tab must not teleport everything.
  const dt = Math.min(0.05, (now - last) / 1000);
  last = now;

  sinceAsh += dt;
  const ambient = ps.reduce((n, p) => n + (p.kind === "ash" ? 1 : 0), 0);
  if (sinceAsh > 0.26 && ambient < 34) { sinceAsh = 0; ash(); }

  ctx.clearRect(0, 0, w, h);
  ctx.globalCompositeOperation = "lighter";

  for (let i = ps.length - 1; i >= 0; i--) {
    const p = ps[i]!;
    p.age += dt;
    if (p.age >= p.life || p.y < -20) { ps.splice(i, 1); continue; }

    if (p.kind === "spark") {
      p.vy += 420 * dt;                       // sparks fall
      p.vx *= 1 - 2.4 * dt;
      p.vy *= 1 - 1.1 * dt;
    } else {
      p.x += Math.sin(now / 900 + p.ph) * 7 * dt;   // ash and motes sway
      p.vy *= 1 - 0.25 * dt;
    }
    p.x += p.vx * dt;
    p.y += p.vy * dt;

    // Fade in over the first tenth of a life, out over the last half.
    const t = p.age / p.life;
    const a = (p.kind === "ash" ? 0.42 : 0.95)
      * Math.min(1, t / 0.1) * Math.min(1, (1 - t) / 0.5);
    const [cr, cg, cb] = p.col;
    ctx.fillStyle = `rgba(${cr},${cg},${cb},${a.toFixed(3)})`;
    ctx.beginPath();
    ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
    ctx.fill();
  }

  ctx.globalCompositeOperation = "source-over";
}

/** Test hook: how much is on screen, and whether the loop is running. */
export const particleStats = () => ({ count: ps.length, running: Boolean(raf) });
