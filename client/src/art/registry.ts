/**
 * The art registry — the single source of truth for what the client can draw.
 *
 * `manifest()` is evaluated at build time by the art-manifest Vite plugin and
 * written to static/art-manifest.json, which tests/test_content.py checks
 * against the Python content tables. Keys here are **content ids**, not display
 * names, so renaming a monster in the tables cannot orphan its art.
 */

import { creatureSvg, CREATURE_KEYS } from "./creatures";

export const RELICS: Record<string, string> = {
  burning_blood: "🩸",
  bag_of_marbles: "🔮",
  anchor: "⚓",
  vajra: "🔱",
  oddly_smooth_stone: "🥚",
  bronze_scales: "⚖️",
  blood_vial: "🧪",
  lantern: "🏮",
  happy_flower: "🌼",
  pen_nib: "🖋️",
  strawberry: "🍓",
  meat_on_bone: "🍖",
  kunai: "🗡️",
  bag_of_prep: "🎒",
  art_of_war: "📜",
  ash_phial: "⚱️",
  emberheart: "🫀",
  ashglass_vial: "🫙",
  smoulder_stone: "🪨",
  grave_ash: "⚰️",
  bone_dice: "🎲",
  oathkeeper: "🕯️",
  hollow_lantern: "🏮",
};

export const POTIONS: Record<string, string> = {
  fire: "🔥",
  block: "🛡️",
  strength: "💪",
  energy: "⚡",
  swift: "💨",
  explosive: "💥",
  weak: "🌀",
  fear: "😱",
  blood: "🩸",
};

export const FALLBACK = { creature: "👾", relic: "◈", potion: "🧪" } as const;

export function creature(key: string): string {
  return creatureSvg(key) ?? FALLBACK.creature;
}
export function relic(key: string): string {
  return RELICS[key] ?? FALLBACK.relic;
}
export function potion(key: string): string {
  return POTIONS[key] ?? FALLBACK.potion;
}

/** Read at build time by the art-manifest plugin. */
export function manifest() {
  return {
    creatures: CREATURE_KEYS,
    relics: Object.keys(RELICS),
    potions: Object.keys(POTIONS),
  };
}
