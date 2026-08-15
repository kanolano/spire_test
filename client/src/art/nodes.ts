/**
 * The map's node icons.
 *
 * The map was the last place still drawing with Unicode: ⚔ ☠ ? ♨ $ ◈ ♛. Those
 * are seven glyphs from seven different type designers, they render differently
 * on every platform, and two of them (♨ and ◈) are commonly missing entirely.
 *
 * Each icon is drawn in a 20×20 box centred on the origin, so it can be dropped
 * onto a node with a single translate — the map already knows where the discs
 * are, and does not want to know how big the art is.
 */

import type { NodeKind } from "../types";

export interface NodeArt {
  /** Markup, centred on (0,0), coloured by `currentColor`. */
  icon: string;
  /** The node's accent, used for the disc ring and the legend. */
  color: string;
  /** What the player calls it. */
  title: string;
}

/* Every icon is stroked in currentColor at a consistent weight, so the set
   reads as one hand at 17px the way the sprite kit does at 104px. */
const S = `fill="none" stroke="currentColor" stroke-width="1.7"
  stroke-linecap="round" stroke-linejoin="round"`;

/**
 * Crossed blades — one sword, mirrored.
 *
 * Drawn as a shape rather than as strokes: four lines at 1.7px read as an X
 * with hooks on it at map size, not as weapons.
 */
const sword = (d: number) =>
  `<g transform="rotate(${38 * d})">`
  + `<path d="M0 -9.5 L1.9 -6.2 L1.9 3 L-1.9 3 L-1.9 -6.2 Z" fill="currentColor"/>`
  + `<rect x="-4.8" y="3" width="9.6" height="1.9" rx=".9" fill="currentColor"/>`
  + `<path d="M0 5.4 L0 8.2" ${S} stroke-width="2"/>`
  + `<circle cx="0" cy="9.2" r="1.3" fill="currentColor"/></g>`;

const MONSTER = sword(1) + sword(-1);

const ELITE =
  // A horned skull: the elite is the same fight with something worse in it.
  `<path d="M-5.6 -0.5 q0 -6.6 5.6 -6.6 q5.6 0 5.6 6.6 q0 3.4 -2.6 4.6
     l0 2.8 q-3 1.6 -6 0 l0 -2.8 q-2.6 -1.2 -2.6 -4.6 z" ${S}/>`
  + `<circle cx="-2.4" cy="-1.2" r="1.5" fill="currentColor"/>`
  + `<circle cx="2.4" cy="-1.2" r="1.5" fill="currentColor"/>`
  + `<path d="M-5.4 -3.6 q-4 -1.4 -4.2 -5.4" ${S}/>`
  + `<path d="M5.4 -3.6 q4 -1.4 4.2 -5.4" ${S}/>`
  + `<path d="M-1.4 3.4 h2.8" ${S}/>`;

const EVENT =
  // An open eye: something is watching, and you cannot tell what it wants.
  `<path d="M-8.6 0.4 q8.6 -7.6 17.2 0 q-8.6 7.6 -17.2 0 z" ${S}/>`
  + `<circle cx="0" cy="0.4" r="2.6" fill="currentColor"/>`
  + `<path d="M-6.4 -4.8 l-1.6 -2.8 M0 -6.2 l0 -3.2 M6.4 -4.8 l1.6 -2.8" ${S}/>`;

const REST =
  // Two logs and a flame with a curl in it — a symmetrical teardrop reads as
  // a leaf, which is how the campfire node came to look like a tree.
  `<path d="M-7.6 7.4 L4.6 2.2 M7.6 7.4 L-4.6 2.2" ${S} stroke-width="2.4"/>`
  // Outlined, with the inner lick showing: filled, a flame is a leaf.
  + `<path class="rig-flame" d="M0.8 -9.6 q4 4 4 6.9 a4.6 4.6 0 0 1 -9.2 0
       q0 -2.2 2.2 -4.2 q0.3 2.3 1.6 2.9 q0.9 -2.9 1.4 -5.6 z" ${S}/>`
  + `<circle cx="0.4" cy="1.6" r="1.3" fill="currentColor" opacity=".9"/>`;

const SHOP =
  // A merchant's scales — gold, like treasure, but a trade rather than a find.
  `<path d="M0 -8.4 v13.6 M-7.6 -5 h15.2 M-4.6 7.6 h9.2" ${S}/>`
  + `<path d="M-4.4 5.2 L-2.4 7.6 M4.4 5.2 L2.4 7.6" ${S}/>`
  + `<path d="M-10.2 -5 q2.6 5.6 5.2 0 z" ${S}/>`
  + `<path d="M5 -5 q2.6 5.6 5.2 0 z" ${S}/>`
  + `<circle cx="0" cy="-8.4" r="1.5" fill="currentColor"/>`;

const TREASURE =
  `<rect x="-8.4" y="-2.6" width="16.8" height="9.6" rx="1.4" ${S}/>`
  + `<path d="M-8.4 -2.6 q8.4 -6.6 16.8 0" ${S}/>`
  + `<path d="M-8.4 1 h16.8" ${S}/>`
  + `<rect x="-1.8" y="-0.6" width="3.6" height="4.4" rx="1"
       fill="currentColor"/>`;

const BOSS =
  `<path d="M-8.4 6 L-8.4 -5.6 l4.6 3.6 L0 -8.6 l3.8 6.6 l4.6 -3.6 L8.4 6 z" ${S}/>`
  + `<circle cx="-4.4" cy="2.4" r="1.2" fill="currentColor"/>`
  + `<circle cx="0" cy="2.4" r="1.2" fill="currentColor"/>`
  + `<circle cx="4.4" cy="2.4" r="1.2" fill="currentColor"/>`;

export const NODE_ART: Record<NodeKind, NodeArt> = {
  monster: { icon: MONSTER, color: "#c8503f", title: "Combat" },
  elite: { icon: ELITE, color: "#a874d4", title: "Elite" },
  event: { icon: EVENT, color: "#4e9ec4", title: "Unknown" },
  rest: { icon: REST, color: "#6fbf73", title: "Campfire" },
  shop: { icon: SHOP, color: "#e3b86a", title: "Merchant" },
  treasure: { icon: TREASURE, color: "#e3b86a", title: "Treasure" },
  boss: { icon: BOSS, color: "#c8503f", title: "Boss" },
};

export const NODE_KINDS = Object.keys(NODE_ART) as NodeKind[];

/** The icon placed at a point on the map, at `scale` of its drawn size. */
export function nodeIcon(kind: NodeKind, x: number, y: number, scale = 1): string {
  const art = NODE_ART[kind];
  return `<g class="nicon" transform="translate(${x} ${y}) scale(${scale})"
    color="${art.color}">${art.icon}</g>`;
}

/** The same icon, standalone, for the legend and anywhere outside the map. */
export function nodeBadge(kind: NodeKind, px = 18): string {
  const art = NODE_ART[kind];
  return `<svg class="nbadge" viewBox="-11 -11 22 22" width="${px}" height="${px}"
    color="${art.color}" aria-hidden="true">${art.icon}</svg>`;
}
