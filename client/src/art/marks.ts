/**
 * The two marks the combat UI leans on: what an enemy intends, and Block.
 *
 * These were the last emoji in the game — ⚔ 🛡 ▲ ▼ on the intent badge and a
 * 🛡 on every block chip. Emoji are the wrong tool for a status glyph twice
 * over: they are drawn by whichever font the platform picks, so ⚔ arrives as a
 * flat multiplication sign on some systems and as a full-colour cartoon on
 * others, and they cannot take the colour of the badge they sit in. These do
 * both — one stroke weight, `currentColor`, sized to the text beside them.
 */

import type { IntentKind } from "../types";

const mark = (inner: string, px: number) =>
  `<svg class="mark" viewBox="-10 -10 20 20" width="${px}" height="${px}"
     aria-hidden="true">${inner}</svg>`.replace(/\s+/g, " ");

/** A raised blade, angled the way a blow arrives. Deliberately chunky: at the
 *  14px it is drawn at, a finely tapered sword is a diagonal smudge. */
const ATTACK =
  `<g transform="rotate(-32)">`
  + `<path d="M0 -9.6 L2.9 -4.6 L2.9 2.6 L-2.9 2.6 L-2.9 -4.6 Z" fill="currentColor"/>`
  + `<rect x="-6" y="2.6" width="12" height="2.6" rx="1.2" fill="currentColor"/>`
  + `<rect x="-1.5" y="5.2" width="3" height="4.4" rx="1.4" fill="currentColor"/></g>`;

const BLOCK =
  `<path d="M0 -8.6 q4.4 2.4 8 3 q0 8.4 -8 12.6 q-8 -4.2 -8 -12.6
     q3.6 -0.6 8 -3 z" fill="none" stroke="currentColor" stroke-width="1.9"
     stroke-linejoin="round"/>`;

const arrow = (up: boolean) =>
  `<path d="M0 ${up ? -8.4 : 8.4} L${up ? 6.4 : -6.4} ${up ? -0.6 : 0.6}
     H${up ? 2.8 : -2.8} V${up ? 8.4 : -8.4} H${up ? -2.8 : 2.8}
     V${up ? -0.6 : 0.6} H${up ? -6.4 : 6.4} Z" fill="currentColor"/>`;

const INTENT: Record<IntentKind, string> = {
  attack: ATTACK,
  block: BLOCK,
  buff: arrow(true),
  debuff: arrow(false),
};

export const intentMark = (kind: IntentKind, px = 14): string =>
  mark(INTENT[kind] ?? BLOCK, px);

/** The shield on every block chip, at text size. */
export const shieldMark = (px = 12): string => mark(BLOCK, px);
