/**
 * The two climbers.
 *
 * The player had no sprite at all — combat was a row of monsters attacking a
 * status bar. They are built from the same kit as the bestiary so the fight
 * looks like it is happening between two things in one world, and they face
 * right, toward the enemies.
 */

import { body, eyes, GROUND, plates, shadow, weapon } from "./kit";
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

const HEROES: Record<string, Hero> = {
  sentinel: { ramp: "regal", svg: sentinel() },
  ashwalker: { ramp: "ash", svg: ashwalker() },
};

export const HERO_KEYS = Object.keys(HEROES);

/** Facing right, toward the enemies. */
export function heroSvg(cls: string): string {
  const hero = HEROES[cls] ?? HEROES["sentinel"]!;
  return `<svg class="csprite hero" viewBox="10 8 80 88" style="height:112px"
      preserveAspectRatio="xMidYMax meet" data-hero="${cls}" aria-hidden="true">
    ${shadow(40)}
    <g class="rig-body">${hero.svg}</g>
  </svg>`.replace(/\s+/g, " ");
}

/** Kept so kit changes that move the ground line show up here too. */
export const HERO_GROUND = GROUND;
