/**
 * The bestiary, composed from the kit.
 *
 * Each entry is a short recipe, not an illustration: a silhouette, a ramp, and
 * two or three features. That is what keeps 29 of them looking like one hand.
 * Keys are content ids from spire_of_ash/content/monsters.py — never display
 * names, so renaming a monster cannot orphan its art.
 *
 * Every sprite is rigged: `.rig-body` breathes and takes hits, `.rig-eye`
 * flashes, `.rig-jaw` opens on a wind-up, `.rig-shadow` tracks a lunge. The
 * director animates those classes without knowing which creature it has.
 */

import {
  body, crown, embers, eyes, horns, jaw, limbs, plates, shadow,
  spikes, tendrils, weapon, wings, type BodyShape,
} from "./kit";
import type { RampName } from "./palette";

interface Spec {
  ramp: RampName;
  shape: BodyShape;
  w: number;
  h: number;
  /** Drawn behind the body — wings, extra limbs. */
  back?: string;
  /** Drawn over the body. */
  front?: string;
  /** Bosses and elites read bigger. */
  scale?: number;
  /** Floats instead of standing. */
  float?: boolean;
}

const S: Record<string, Spec> = {
  /* ── act 1 rabble ── */
  jaw_worm: {
    ramp: "flesh", shape: "coil", w: 58, h: 48,
    // Head is at the right of the coil, so its face goes there rather than
    // in the middle of the body.
    front: `<g transform="translate(14,-6)">`
      + eyes("flesh", { y: 52, spread: 8, r: 2.4 }) + jaw("flesh", 60, 20) + `</g>`,
  },
  cultist: {
    ramp: "cloth", shape: "draped", w: 34, h: 58,
    front: eyes("cloth", { y: 42, spread: 8, r: 2.4, slit: true })
      + horns("cloth", 38, 9, 12, 3),
  },
  louse: {
    ramp: "flesh", shape: "blob", w: 42, h: 30,
    back: limbs("flesh", 74, 30, 15, 8),
    front: eyes("flesh", { n: 4, y: 66, spread: 7, r: 1.8 }) + spikes("flesh", 62, 24, 4, 6),
  },
  fungi: {
    ramp: "ooze", shape: "squat", w: 40, h: 44,
    front: `<ellipse cx="50" cy="46" rx="26" ry="13" fill="#6d3f52"
              stroke="#a9748a" stroke-opacity=".4"/>`
      + `<circle cx="41" cy="43" r="3" fill="#e2b3c4" opacity=".7"/>`
      + `<circle cx="57" cy="45" r="2.2" fill="#e2b3c4" opacity=".7"/>`
      + eyes("ooze", { y: 62, spread: 9, r: 2.4 }),
  },
  acid_slime: {
    ramp: "ooze", shape: "blob", w: 50, h: 38,
    front: eyes("ooze", { y: 66, spread: 11, r: 3 })
      + `<path d="M34 58 q16 10 32 0" stroke="#84d09a" stroke-opacity=".5"
           stroke-width="1.4" fill="none"/>`,
  },
  spike_slime: {
    ramp: "brine", shape: "blob", w: 50, h: 38,
    front: spikes("brine", 58, 30, 5, 8) + eyes("brine", { y: 70, spread: 11, r: 3 }),
  },
  small_slime: {
    ramp: "brine", shape: "blob", w: 30, h: 24, scale: 0.85,
    front: eyes("brine", { y: 76, spread: 7, r: 2.2 }),
  },
  mad_gremlin: {
    ramp: "bile", shape: "squat", w: 30, h: 34,
    front: eyes("bile", { y: 62, spread: 8, r: 2.6 }) + jaw("bile", 71, 16)
      + horns("bile", 58, 10, 10, 4),
  },
  sneaky_gremlin: {
    ramp: "bile", shape: "squat", w: 26, h: 32,
    front: eyes("bile", { y: 64, spread: 7, r: 2.2, slit: true })
      + weapon("bile", "dagger"),
  },
  fat_gremlin: {
    ramp: "bile", shape: "blob", w: 42, h: 36,
    front: eyes("bile", { y: 62, spread: 10, r: 2.8 }) + jaw("bile", 70, 20),
  },
  shield_gremlin: {
    ramp: "bile", shape: "squat", w: 30, h: 34,
    front: eyes("bile", { y: 62, spread: 8, r: 2.4 })
      + `<circle cx="72" cy="60" r="12" fill="#4c4c5c" stroke="#8a8aa0"
           stroke-opacity=".5" stroke-width="1.5"/>`
      + `<circle cx="72" cy="60" r="4" fill="#8a8aa0" opacity=".6"/>`,
  },
  sentry: {
    // A floating diamond eye, not a plated stack — it has to read apart from
    // Lagavulin and the Guardian, which share its ramp.
    ramp: "stone", shape: "shard", w: 30, h: 48, float: true,
    front: eyes("stone", { n: 1, y: 50, r: 6 })
      + `<path d="M50 30 L64 50 L50 70 L36 50 Z" fill="none" stroke="#8a8aa0"
           stroke-opacity=".55" stroke-width="1.8"/>`
      + `<path d="M50 22 v8 M50 70 v8" stroke="#ffc36a" stroke-opacity=".6"
           stroke-width="1.6"/>`,
  },
  byrd: {
    ramp: "spectre", shape: "orb", w: 30, h: 30, float: true,
    back: wings("spectre", 50, 24),
    front: eyes("spectre", { y: 48, spread: 8, r: 2.4 })
      + `<path d="M50 56 l7 6 l-7 4 z" fill="#d6cbb4"/>`
      + limbs("spectre", 72, 12, 8, 10),
  },
  chosen: {
    // Hooded and hunched, with the inverted sigil it hexes you with. The three
    // cloth-ramp casters have to differ in silhouette, not just in trim.
    ramp: "cloth", shape: "draped", w: 40, h: 54,
    front: `<path d="M32 46 q18 -22 36 0 q-18 -8 -36 0 z" fill="#2a1830"
              stroke="#a077b4" stroke-opacity=".5" stroke-width="1.5"/>`
      + eyes("cloth", { y: 50, spread: 10, r: 2.8 })
      + `<path d="M50 76 v-16 M42 68 h16" stroke="#e2a6ff" stroke-width="2.2"
           opacity=".8" fill="none"/>`,
  },
  mystic: {
    // Tall, thin, arms up — the healer of the group.
    ramp: "cloth", shape: "tall", w: 28, h: 62,
    back: `<g class="rig-limb">`
      + `<path d="M40 52 q-14 -10 -16 -24" stroke="#5b3468" stroke-width="5"
           stroke-linecap="round" fill="none"/>`
      + `<path d="M60 52 q14 -10 16 -24" stroke="#5b3468" stroke-width="5"
           stroke-linecap="round" fill="none"/></g>`,
    front: eyes("cloth", { n: 3, y: 40, spread: 7, r: 1.9 })
      + `<circle cx="50" cy="24" r="8" fill="none" stroke="#e2a6ff"
           stroke-width="1.8" opacity=".8"/>`,
  },

  /* ── the ash line, added for this Spire ── */
  ash_pup: {
    ramp: "ash", shape: "squat", w: 36, h: 30,
    back: limbs("ash", 76, 26, 12, 8),
    front: eyes("ash", { y: 64, spread: 10, r: 2.6 }) + jaw("ash", 72, 18)
      + embers("ash", 54, 4),
  },
  slag_golem: {
    // Boulder shoulders and a molten seam down the middle.
    ramp: "stone", shape: "squat", w: 52, h: 54,
    back: `<circle cx="26" cy="50" r="12" fill="#3f3f4c" stroke="#8a8aa0"
             stroke-opacity=".4"/>`
      + `<circle cx="74" cy="50" r="12" fill="#3f3f4c" stroke="#8a8aa0"
             stroke-opacity=".4"/>`,
    front: eyes("stone", { y: 50, spread: 12, r: 3.2 })
      + `<path d="M50 58 l-5 12 l6 6 l-4 10" stroke="#ffc36a" stroke-width="2.4"
           fill="none" stroke-linecap="round" opacity=".85"/>`
      + embers("stone", 40, 4),
  },
  cinder_moth: {
    ramp: "ash", shape: "blob", w: 20, h: 34, float: true,
    // Moth wings are the whole silhouette; the body is barely there.
    back: `<g class="rig-wing">`
      + `<path d="M44 48 q-30 -22 -32 2 q-2 20 30 14 z" fill="#6b4a3a"
           stroke="#ff8a3c" stroke-opacity=".45" stroke-width="1.2"/>`
      + `<path d="M56 48 q30 -22 32 2 q2 20 -30 14 z" fill="#6b4a3a"
           stroke="#ff8a3c" stroke-opacity=".45" stroke-width="1.2"/>`
      + `<circle cx="24" cy="52" r="3.4" fill="#ff8a3c" opacity=".55"/>`
      + `<circle cx="76" cy="52" r="3.4" fill="#ff8a3c" opacity=".55"/></g>`,
    front: eyes("ash", { y: 48, spread: 5, r: 2 }) + embers("ash", 34, 5)
      + `<path d="M47 42 q-4 -9 -7 -12 M53 42 q4 -9 7 -12" stroke="#8c7a80"
           stroke-width="1.4" fill="none" stroke-linecap="round"/>`,
  },
  bone_picker: {
    // A hunched carrion bird: folded wings, long beak, ribs showing.
    ramp: "bone", shape: "blob", w: 34, h: 44,
    back: `<g class="rig-wing">`
      + `<path d="M34 50 q-16 6 -14 26 q10 -8 16 -10 z" fill="#6b6154"
           stroke="#d6cbb4" stroke-opacity=".35"/>`
      + `<path d="M66 50 q16 6 14 26 q-10 -8 -16 -10 z" fill="#6b6154"
           stroke="#d6cbb4" stroke-opacity=".35"/></g>`,
    front: eyes("bone", { y: 54, spread: 10, r: 2.2 })
      + `<path d="M50 58 l18 7 l-18 5 z" fill="#e6dcc4" stroke="#332e26"
           stroke-opacity=".45"/>`
      + `<path d="M40 72 h20 M42 78 h16" stroke="#d6cbb4" stroke-opacity=".4"
           stroke-width="1.5"/>`,
  },

  /* ── elites ── */
  gremlin_nob: {
    ramp: "bile", shape: "squat", w: 48, h: 52, scale: 1.12,
    front: eyes("bile", { y: 50, spread: 13, r: 3.4 }) + horns("bile", 44, 16, 18, 7)
      + jaw("bile", 62, 26),
  },
  lagavulin: {
    // Asleep behind its shell for the first turns, so: a hunkered carapace
    // with the eyes barely showing under the lip.
    ramp: "stone", shape: "blob", w: 60, h: 40, scale: 1.12,
    front: `<path d="M20 76 q30 -34 60 0 z" fill="#3a3a48" stroke="#8a8aa0"
              stroke-opacity=".5" stroke-width="1.6"/>`
      + `<path d="M30 70 q20 -18 40 0" stroke="#8a8aa0" stroke-opacity=".35"
           stroke-width="1.4" fill="none"/>`
      + eyes("stone", { y: 78, spread: 15, r: 2.4, slit: true }),
  },
  book_of_stabbing: {
    ramp: "cloth", shape: "shard", w: 44, h: 50, scale: 1.12,
    front: `<rect x="30" y="42" width="40" height="30" rx="2" fill="#5b3468"
              stroke="#a077b4" stroke-opacity=".5" stroke-width="1.5"/>`
      + `<path d="M50 42 v30" stroke="#2a1830" stroke-width="2"/>`
      + eyes("cloth", { n: 1, y: 56, r: 5 })
      + spikes("cloth", 42, 34, 6, 10),
  },
  taskmaster: {
    ramp: "regal", shape: "tall", w: 38, h: 58, scale: 1.12,
    front: eyes("regal", { y: 40, spread: 10, r: 2.8 }) + weapon("regal", "axe")
      + plates("regal", 52, 26, 2),
  },
  ash_warden: {
    ramp: "ash", shape: "tall", w: 44, h: 62, scale: 1.18,
    front: eyes("ash", { y: 38, spread: 12, r: 3.2 }) + plates("ash", 50, 32, 3)
      + embers("ash", 34, 6) + weapon("ash", "blade"),
  },

  /* ── bosses ── */
  guardian: {
    ramp: "stone", shape: "shard", w: 58, h: 62, scale: 1.3,
    front: eyes("stone", { n: 1, y: 44, r: 7 }) + plates("stone", 56, 42, 3)
      + spikes("stone", 34, 40, 5, 12),
  },
  hexaghost: {
    ramp: "spectre", shape: "blob", w: 44, h: 52, scale: 1.3, float: true,
    // Six flames orbiting a hollow — the name is the design.
    back: `<g class="rig-ember">`
      + Array.from({ length: 6 }, (_, i) => {
        const a = (i / 6) * Math.PI * 2 - Math.PI / 2;
        const x = 50 + Math.cos(a) * 30;
        const y = 52 + Math.sin(a) * 26;
        return `<path d="M${x} ${y + 6} q-5 -6 0 -11 q5 5 0 11 z"
          fill="#bfe4ff" opacity=".75"/>`;
      }).join("") + `</g>`,
    front: eyes("spectre", { n: 2, y: 48, spread: 13, r: 3.4 })
      + `<path d="M38 64 q12 10 24 0" stroke="#bfe4ff" stroke-opacity=".5"
           stroke-width="1.6" fill="none"/>`
      + tendrils("spectre", 76, 5, 12),
  },
  slime_boss: {
    ramp: "ooze", shape: "blob", w: 66, h: 54, scale: 1.3,
    front: eyes("ooze", { y: 56, spread: 18, r: 4.5 }) + jaw("ooze", 70, 34),
  },
  champ: {
    ramp: "regal", shape: "tall", w: 46, h: 64, scale: 1.34,
    front: eyes("regal", { y: 36, spread: 12, r: 3.2 }) + plates("regal", 46, 34, 3)
      + weapon("regal", "blade") + horns("regal", 34, 12, 12, 4),
  },
  ashen_sovereign: {
    ramp: "regal", shape: "draped", w: 52, h: 70, scale: 1.4,
    front: crown("regal", 22) + eyes("regal", { n: 3, y: 36, spread: 11, r: 3 })
      + embers("regal", 30, 7) + plates("regal", 52, 30, 2)
      + tendrils("regal", 74, 5, 12),
  },
};

/** A normal creature's on-screen height. Elites and bosses scale off it, and
 *  are allowed to grow up out of their slot — looming is the point. */
const BASE_PX = 104;

/**
 * Render one creature as an inline SVG string.
 *
 * Size comes from the element's height, not a transform inside it. Scaling the
 * contents about the ground line pushed crowns and spikes outside the viewBox,
 * where they overlapped whatever sat above — all the drawing stays inside
 * 0..100 and the whole sprite grows instead.
 */
export function creatureSvg(key: string): string | null {
  const spec = S[key];
  if (!spec) return null;
  const height = Math.round((spec.scale ?? 1) * BASE_PX);
  // Cropped rather than zoomed: the drawings only ever use the middle of the
  // 100 box, and every coordinate in the kit is tuned to that box, so trimming
  // the empty margin fills the frame without moving a single feature.
  return `<svg class="csprite" viewBox="10 8 80 88"
      style="height:${height}px" preserveAspectRatio="xMidYMax meet"
      data-creature="${key}" aria-hidden="true">
    ${shadow(spec.w * 0.95)}
    <g class="rig-body">
      ${spec.back ?? ""}
      ${body(spec.shape, spec.ramp, spec.w, spec.h)}
      ${spec.front ?? ""}
    </g>
  </svg>`.replace(/\s+/g, " ");
}

export const CREATURE_KEYS = Object.keys(S);
export const hasCreature = (key: string) => key in S;

/** Anything float-y bobs on a longer, looser cycle. */
export const floats = (key: string) => Boolean(S[key]?.float);
