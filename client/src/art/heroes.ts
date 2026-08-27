/**
 * The two climbers.
 *
 * The player had no sprite at all — combat was a row of monsters attacking a
 * status bar. They are built from the same kit as the bestiary so the fight
 * looks like it is happening between two things in one world, and they face
 * right, toward the enemies.
 */

import { body, eyes, GROUND, horns, plates, shadow, tendrils, weapon } from "./kit";
import type { RampName } from "./palette";

interface Hero {
  ramp: RampName;
  svg: string;
}

const sentinel = (): string =>
  body("tall", "regal", 40, 62)
  + plates("regal", 48, 30, 3)
  + eyes("regal", { y: 38, spread: 9, r: 2.4, slit: true })
  // Great helm brow.
  + `<path d="M34 34 q16 -12 32 0 q-16 -5 -32 0 z" fill="#331a10"
       stroke="#d9a75a" stroke-opacity=".55" stroke-width="1.4"/>`
  // Tower shield on the near arm, heavy blade on the far one.
  + `<g class="rig-limb"><path d="M28 46 q-8 14 -4 30 q10 4 14 -2 q2 -18 -2 -30 z"
       fill="#5b3a1c" stroke="#d9a75a" stroke-opacity=".5" stroke-width="1.5"/>
     <path d="M31 58 h10" stroke="#d9a75a" stroke-opacity=".45" stroke-width="1.4"/></g>`
  + weapon("regal", "blade");

const ashwalker = (): string =>
  body("tall", "ash", 32, 58)
  + eyes("ash", { y: 40, spread: 8, r: 2.2 })
  // Hood and trailing scarf — lighter silhouette than the Sentinel's.
  + `<path d="M35 40 q15 -18 30 0 q-15 -7 -30 0 z" fill="#241d24"
       stroke="#8c7a80" stroke-opacity=".5" stroke-width="1.4"/>`
  + `<path d="M36 44 q-14 10 -20 26 q10 0 16 -8" fill="#4e4148"
       stroke="#ff8a3c" stroke-opacity=".3" stroke-width="1.2"/>`
  + `<g class="rig-ember"><circle cx="22" cy="66" r="1.6" fill="#ff8a3c"/>
     <circle cx="17" cy="58" r="1.2" fill="#ff8a3c" opacity=".7"/></g>`
  + weapon("ash", "dagger");

// A body wired for weather: brine-blue, arcs of Coil crackling off one arm and
// a rime of Frost on the shoulder.
const stormbound = (): string =>
  body("tall", "brine", 34, 60)
  + eyes("brine", { y: 40, spread: 8, r: 2.4 })
  + `<path d="M35 40 q15 -14 30 0 q-15 -6 -30 0 z" fill="#152c3a"
       stroke="#7fc0dc" stroke-opacity=".5" stroke-width="1.4"/>`
  // Coil arcing off the near arm.
  + `<g class="rig-limb"><path d="M30 48 q-10 6 -8 16 q6 -2 6 -8 q4 6 -2 12"
       fill="none" stroke="#b6ecff" stroke-opacity=".8" stroke-width="1.6"
       stroke-linecap="round"/></g>`
  // Frost crystals on the far shoulder.
  + `<g class="rig-ember"><path d="M64 46 l3 -4 l3 4 l-3 4 z" fill="#b6ecff" opacity=".8"/>
     <path d="M60 52 l2 -3 l2 3 l-2 3 z" fill="#7fc0dc" opacity=".7"/></g>`;

// Bare hands and a vow: cloth-wrapped, unarmed, a ring of Mantra light at the
// brow and fists raised rather than a weapon.
const penitent = (): string =>
  body("tall", "cloth", 32, 58)
  + eyes("cloth", { y: 40, spread: 8, r: 2.2, slit: true })
  + `<path d="M36 40 q14 -16 28 0 q-14 -6 -28 0 z" fill="#2a1830"
       stroke="#a077b4" stroke-opacity=".5" stroke-width="1.4"/>`
  // Halo of Mantra.
  + `<circle cx="50" cy="30" r="10" fill="none" stroke="#e2a6ff" stroke-opacity=".5"
       stroke-width="1.2"/>`
  // Raised fists, wrapped.
  + `<g class="rig-limb"><circle cx="30" cy="52" r="5" fill="#5b3468"
       stroke="#a077b4" stroke-opacity=".5" stroke-width="1.4"/>
     <circle cx="70" cy="50" r="5" fill="#5b3468" stroke="#a077b4"
       stroke-opacity=".5" stroke-width="1.4"/></g>`;

// Thin, grey and patient: a spectral robe, hollow eyes, and wisps of the
// exhaust pile trailing off the hem.
const gravewright = (): string =>
  body("draped", "spectre", 34, 62)
  + eyes("spectre", { y: 40, spread: 9, r: 2.6 })
  + `<path d="M35 40 q15 -16 30 0 q-15 -6 -30 0 z" fill="#1d2436"
       stroke="#8fa2cc" stroke-opacity=".5" stroke-width="1.4"/>`
  // A reaping hook.
  + `<g class="rig-limb"><path d="M70 44 v26 M70 44 q10 -2 8 8"
       fill="none" stroke="#8fa2cc" stroke-opacity=".6" stroke-width="1.6"
       stroke-linecap="round"/></g>`
  + tendrils("spectre", 78, 4, 12);

// A deeper belt and a lit burner: ash-toned, a bandolier of vials across the
// chest and a flame at the near hand.
const emberbrewer = (): string =>
  body("tall", "ash", 34, 58)
  + eyes("ash", { y: 40, spread: 8, r: 2.2 })
  + `<path d="M35 40 q15 -14 30 0 q-15 -6 -30 0 z" fill="#241d24"
       stroke="#8c7a80" stroke-opacity=".5" stroke-width="1.4"/>`
  // Bandolier of potion vials.
  + `<g transform="rotate(28 50 56)">`
  + [40, 50, 60].map((x) =>
      `<rect x="${x}" y="52" width="4" height="8" rx="1.5" fill="#0f0b17"
         stroke="#a9803c" stroke-opacity=".6" stroke-width="1.1"/>`).join("")
  + `</g>`
  // Flame cupped in the near hand.
  + `<g class="rig-ember"><path d="M30 54 c-2 3 -2 6 0 7 c2 -1 2 -4 0 -7z"
       fill="#ff8a3c"/></g>`;

// Knows everything's true name and says them all out loud: a violet cowl, a
// third eye, and sigils orbiting a raised hand.
const hexbinder = (): string =>
  body("draped", "cloth", 32, 60)
  + eyes("cloth", { y: 42, spread: 8, r: 2.2 })
  + `<path d="M35 42 q15 -18 30 0 q-15 -7 -30 0 z" fill="#2a1830"
       stroke="#a077b4" stroke-opacity=".5" stroke-width="1.4"/>`
  // Third eye at the brow.
  + `<circle cx="50" cy="34" r="2.6" fill="#e2a6ff" opacity=".85"/>`
  // A sigil orbiting the raised near hand.
  + `<g class="rig-ember"><circle cx="28" cy="50" r="6" fill="none"
       stroke="#e2a6ff" stroke-opacity=".7" stroke-width="1.2"/>
     <path d="M24 50 h8 M28 46 v8" stroke="#e2a6ff" stroke-opacity=".6"
       stroke-width="1.1"/></g>`
  + horns("cloth", 30, 10, 10, 4);

const HEROES: Record<string, Hero> = {
  sentinel: { ramp: "regal", svg: sentinel() },
  ashwalker: { ramp: "ash", svg: ashwalker() },
  stormbound: { ramp: "brine", svg: stormbound() },
  penitent: { ramp: "cloth", svg: penitent() },
  gravewright: { ramp: "spectre", svg: gravewright() },
  emberbrewer: { ramp: "ash", svg: emberbrewer() },
  hexbinder: { ramp: "cloth", svg: hexbinder() },
};

export const HERO_KEYS = Object.keys(HEROES);

/** Facing right, toward the enemies. */
export function heroSvg(cls: string, px = 112): string {
  const hero = HEROES[cls] ?? HEROES["sentinel"]!;
  return `<svg class="csprite hero" viewBox="10 8 80 88" style="height:${px}px"
      preserveAspectRatio="xMidYMax meet" data-hero="${cls}" aria-hidden="true">
    ${shadow(40)}
    <g class="rig-body">${hero.svg}</g>
  </svg>`.replace(/\s+/g, " ");
}

/** Kept so kit changes that move the ground line show up here too. */
export const HERO_GROUND = GROUND;
