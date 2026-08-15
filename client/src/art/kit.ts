/**
 * The parts every creature is built from.
 *
 * Drawing 29 monsters one path at a time gives you 29 unrelated drawings.
 * These are the shared vocabulary: a dozen primitives, each parameterised, so
 * a monster is a short composition rather than a bespoke illustration. When a
 * creature genuinely fights the kit it gets a bespoke body path instead — but
 * it still takes its eyes, rim and palette from here.
 *
 * Everything is drawn in a 100×100 box with the ground at y=88.
 */

import { bodyGrad, GLOW_HARD, GLOW_SOFT, INNER_SHADE } from "./defs";
import { RAMPS, type RampName } from "./palette";

export const GROUND = 88;

/* ── bodies ────────────────────────────────────────────────── */

export type BodyShape =
  | "blob"     // low and wide — grubs, slimes
  | "squat"    // wider than tall, planted — gremlins, beasts
  | "tall"     // upright — cultists, wardens
  | "orb"      // round and floating
  | "shard"    // angular, built — sentries, golems
  | "draped"   // robed, hem on the ground
  | "coil";    // segmented worm

/** The silhouette. `w` and `h` are the creature's footprint in the 100 box. */
export function body(shape: BodyShape, ramp: RampName, w: number, h: number): string {
  const cx = 50;
  const bottom = GROUND;
  const top = bottom - h;
  const hw = w / 2;
  const fill = `url(#${bodyGrad(ramp)})`;
  const r = RAMPS[ramp];
  const skin = `fill="${fill}" stroke="${r.rim}" stroke-opacity=".6" stroke-width="1.7"`;

  let path: string;
  switch (shape) {
    case "blob":
      path = `M${cx - hw} ${bottom} Q${cx - hw * 1.05} ${top + h * 0.15} ${cx - hw * 0.45} ${top}`
        + ` Q${cx} ${top - h * 0.16} ${cx + hw * 0.45} ${top}`
        + ` Q${cx + hw * 1.05} ${top + h * 0.15} ${cx + hw} ${bottom} Z`;
      break;
    case "squat":
      path = `M${cx - hw} ${bottom} L${cx - hw * 0.92} ${top + h * 0.42}`
        + ` Q${cx - hw * 0.78} ${top} ${cx} ${top}`
        + ` Q${cx + hw * 0.78} ${top} ${cx + hw * 0.92} ${top + h * 0.42}`
        + ` L${cx + hw} ${bottom} Z`;
      break;
    case "tall":
      path = `M${cx - hw} ${bottom} L${cx - hw * 0.62} ${top + h * 0.26}`
        + ` Q${cx - hw * 0.5} ${top} ${cx} ${top}`
        + ` Q${cx + hw * 0.5} ${top} ${cx + hw * 0.62} ${top + h * 0.26}`
        + ` L${cx + hw} ${bottom} Z`;
      break;
    case "orb":
      return `<ellipse cx="${cx}" cy="${bottom - h / 2}" rx="${hw}" ry="${h / 2}" ${skin}/>`
        + `<ellipse cx="${cx}" cy="${bottom - h / 2}" rx="${hw}" ry="${h / 2}"`
        + ` fill="url(#${INNER_SHADE})"/>`;
    case "shard":
      path = `M${cx} ${top} L${cx + hw} ${top + h * 0.3} L${cx + hw * 0.72} ${bottom}`
        + ` L${cx - hw * 0.72} ${bottom} L${cx - hw} ${top + h * 0.3} Z`;
      break;
    case "draped":
      path = `M${cx - hw} ${bottom} Q${cx - hw * 0.72} ${top + h * 0.3} ${cx - hw * 0.34} ${top}`
        + ` Q${cx} ${top - h * 0.1} ${cx + hw * 0.34} ${top}`
        + ` Q${cx + hw * 0.72} ${top + h * 0.3} ${cx + hw} ${bottom}`
        + ` q${-w * 0.16} ${3} ${-w * 0.25} 0 q${-w * 0.16} ${3} ${-w * 0.25} 0`
        + ` q${-w * 0.16} ${3} ${-w * 0.25} 0 q${-w * 0.16} ${3} ${-w * 0.25} 0 Z`;
      break;
    case "coil": {
      // A tapering body that rears up at the head end. Drawn as one outline
      // with segment creases over it — stacked ellipses read as a pile of
      // stones rather than as anything alive.
      const tail = cx - hw;
      const headY = bottom - h;
      const outline =
        `M${tail} ${bottom} q${-4} ${-8} ${4} ${-12}`
        + ` q${hw * 0.5} ${-6} ${hw * 0.75} ${-(h * 0.28)}`
        + ` q${hw * 0.4} ${-(h * 0.5)} ${hw * 0.95} ${-(h * 0.34)}`
        + ` q${hw * 0.55} ${h * 0.16} ${hw * 0.42} ${h * 0.46}`
        + ` q${-hw * 0.2} ${h * 0.44} ${-hw * 0.5} ${h * 0.5}`
        + ` z`;
      const creases = [0.3, 0.5, 0.68].map((t) => {
        const x = tail + w * t;
        const y = bottom - h * (0.18 + t * 0.5);
        return `<path d="M${x} ${y} q6 ${h * 0.14} 0 ${h * 0.26}"
          stroke="${r.ink}" stroke-opacity=".45" stroke-width="1.6" fill="none"/>`;
      }).join("");
      return `<path d="${outline}" ${skin}/>`
        + `<path d="${outline}" fill="url(#${INNER_SHADE})"/>${creases}`
        + `<!-- head end at y≈${Math.round(headY)} -->`;
    }
  }
  return `<path d="${path}" ${skin}/>`
    + `<path d="${path}" fill="url(#${INNER_SHADE})"/>`;
}

/* ── eyes ──────────────────────────────────────────────────── */

export interface EyeOpts {
  n?: number;
  y?: number;
  spread?: number;
  r?: number;
  /** A single wide slit instead of round eyes. */
  slit?: boolean;
}

/** The strongest identity signal a sprite has, and the thing that flashes when
 *  the creature is hit — hence its own rig class. */
export function eyes(ramp: RampName, o: EyeOpts = {}): string {
  const { n = 2, y = 46, spread = 11, r = 3.2, slit = false } = o;
  const glow = RAMPS[ramp].glow;
  const out: string[] = [];
  for (let i = 0; i < n; i++) {
    const x = n === 1 ? 50 : 50 + (i - (n - 1) / 2) * spread;
    out.push(slit
      ? `<rect x="${x - r * 1.5}" y="${y - r * 0.4}" width="${r * 3}" height="${r * 0.8}"
           rx="${r * 0.4}" fill="${glow}"/>`
      : `<circle cx="${x}" cy="${y}" r="${r}" fill="${glow}"/>`);
  }
  return `<g class="rig-eye" filter="url(#${GLOW_HARD})">${out.join("")}</g>`;
}

/* ── features ──────────────────────────────────────────────── */

export function horns(ramp: RampName, y = 40, spread = 14, len = 14, curve = 6): string {
  const c = RAMPS[ramp].rim;
  const one = (dir: number) =>
    `<path d="M${50 + dir * spread} ${y} q${dir * curve} ${-len * 0.55} ${dir * (curve * 0.4)} ${-len}"
       stroke="${c}" stroke-width="3.2" stroke-linecap="round" fill="none" opacity=".85"/>`;
  return `<g class="rig-horn">${one(-1)}${one(1)}</g>`;
}

/** A hinged maw. Opens during an attack wind-up, which is what the rig class
 *  is for. */
export function jaw(ramp: RampName, y = 58, w = 22): string {
  const r = RAMPS[ramp];
  const hw = w / 2;
  const teeth = Array.from({ length: 5 }, (_, i) => {
    const x = 50 - hw + (w / 4) * i;
    return `<path d="M${x} ${y} l${w / 8} ${5} l${w / 8} ${-5}" fill="${r.rim}" opacity=".9"/>`;
  }).join("");
  return `<g class="rig-jaw">`
    + `<path d="M${50 - hw} ${y} q${hw} ${11} ${w} 0 z" fill="${r.ink}"`
    + ` stroke="${r.rim}" stroke-opacity=".5"/>${teeth}</g>`;
}

export function wings(ramp: RampName, y = 44, span = 26): string {
  const c = RAMPS[ramp].shade;
  const rim = RAMPS[ramp].rim;
  const one = (dir: number) =>
    `<path d="M${50 + dir * 9} ${y} q${dir * span} ${-14} ${dir * (span * 1.05)} ${6}
       q${-dir * span * 0.45} ${2} ${-dir * span * 1.05} ${4} z"
       fill="${c}" stroke="${rim}" stroke-opacity=".35"/>`;
  return `<g class="rig-wing">${one(-1)}${one(1)}</g>`;
}

export function spikes(ramp: RampName, y = 42, w = 34, n = 5, len = 9): string {
  const c = RAMPS[ramp].rim;
  const step = w / (n - 1);
  const out = Array.from({ length: n }, (_, i) => {
    const x = 50 - w / 2 + step * i;
    const h = len * (1 - Math.abs(i - (n - 1) / 2) / n);
    return `<path d="M${x - 3} ${y} L${x} ${y - h - 3} L${x + 3} ${y} z" fill="${c}" opacity=".8"/>`;
  }).join("");
  return `<g class="rig-spike">${out}</g>`;
}

/** Tapered limbs. Two by default, animated as one group. */
export function limbs(ramp: RampName, y = 62, spread = 20, len = 18, droop = 8): string {
  const c = RAMPS[ramp].shade;
  const rim = RAMPS[ramp].rim;
  const one = (dir: number) =>
    `<path d="M${50 + dir * spread * 0.5} ${y} q${dir * len * 0.7} ${droop * 0.3}
       ${dir * len} ${droop}" stroke="${c}" stroke-width="5.5" stroke-linecap="round"
       fill="none"/>`
    + `<path d="M${50 + dir * spread * 0.5} ${y} q${dir * len * 0.7} ${droop * 0.3}
       ${dir * len} ${droop}" stroke="${rim}" stroke-width="1.2" stroke-linecap="round"
       fill="none" opacity=".4"/>`;
  return `<g class="rig-limb">${one(-1)}${one(1)}</g>`;
}

export function tendrils(ramp: RampName, y = 70, n = 4, len = 14): string {
  const c = RAMPS[ramp].shade;
  const out = Array.from({ length: n }, (_, i) => {
    const x = 50 + (i - (n - 1) / 2) * 9;
    const sway = i % 2 ? 4 : -4;
    return `<path d="M${x} ${y} q${sway} ${len * 0.6} ${sway * 0.4} ${len}"
      stroke="${c}" stroke-width="2.6" stroke-linecap="round" fill="none"/>`;
  }).join("");
  return `<g class="rig-limb">${out}</g>`;
}

/** Armour plating, for anything built. */
export function plates(ramp: RampName, y = 50, w = 30, rows = 3): string {
  const r = RAMPS[ramp];
  const out = Array.from({ length: rows }, (_, i) =>
    `<rect x="${50 - w / 2}" y="${y + i * 9}" width="${w}" height="6" rx="1.6"
       fill="${r.shade}" stroke="${r.rim}" stroke-opacity=".4"/>`).join("");
  return `<g class="rig-plate">${out}</g>`;
}

/** Embers escaping a body — the thing that ties the ash creatures together. */
export function embers(ramp: RampName, y = 40, n = 5): string {
  const glow = RAMPS[ramp].glow;
  const out = Array.from({ length: n }, (_, i) => {
    const x = 50 + (i - (n - 1) / 2) * 8 + (i % 2 ? 3 : -3);
    const yy = y - (i % 3) * 7;
    return `<circle cx="${x}" cy="${yy}" r="${1.6 - (i % 3) * 0.35}" fill="${glow}"/>`;
  }).join("");
  return `<g class="rig-ember" filter="url(#${GLOW_SOFT})" opacity=".85">${out}</g>`;
}

/** Glowing fissures, for stone that is barely holding together. */
export function cracks(ramp: RampName): string {
  const glow = RAMPS[ramp].glow;
  return `<g class="rig-ember" filter="url(#${GLOW_SOFT})" opacity=".8">`
    + `<path d="M44 46 l4 8 l-3 6 l5 7" stroke="${glow}" stroke-width="1.5" fill="none"/>`
    + `<path d="M58 52 l-3 7 l4 5" stroke="${glow}" stroke-width="1.2" fill="none"/></g>`;
}

/** A held weapon. `kind` picks the silhouette. */
export function weapon(ramp: RampName, kind: "blade" | "axe" | "club" | "dagger"): string {
  const r = RAMPS[ramp];
  const steel = "#b9c2d4";
  const haft = `<rect x="70" y="44" width="3" height="34" rx="1.5" fill="${r.ink}"/>`;
  const head = {
    blade: `<path d="M71.5 46 l6 -22 l-6 -6 l-6 6 z" fill="${steel}" opacity=".9"/>`,
    axe: `<path d="M71.5 40 q14 -6 12 -18 q-14 2 -20 10 z" fill="${steel}" opacity=".9"/>`,
    club: `<ellipse cx="71.5" cy="34" rx="9" ry="12" fill="${r.shade}"
             stroke="${r.rim}" stroke-opacity=".4"/>`,
    dagger: `<path d="M71.5 46 l4 -14 l-4 -4 l-4 4 z" fill="${steel}" opacity=".9"/>`,
  }[kind];
  return `<g class="rig-weapon">${haft}${head}</g>`;
}

/** A crown or halo, for the things at the top of the act. */
export function crown(ramp: RampName, y = 26): string {
  const glow = RAMPS[ramp].glow;
  return `<g class="rig-crown" filter="url(#${GLOW_SOFT})">`
    + `<path d="M38 ${y} l4 -9 l4 6 l4 -10 l4 10 l4 -6 l4 9 z"
        fill="${glow}" opacity=".9"/></g>`;
}

/** The ground contact. Tracks a lunge, so it gets its own class. */
export function shadow(w = 46): string {
  return `<ellipse class="rig-shadow" cx="50" cy="${GROUND + 3}" rx="${w / 2}" ry="4"
    fill="#000" opacity=".45"/>`;
}
