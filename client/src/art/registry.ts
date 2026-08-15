/**
 * The art registry — the single source of truth for what the client can draw.
 *
 * `manifest()` is evaluated at build time by the art-manifest Vite plugin and
 * written to static/art-manifest.json, which tests/test_content.py checks
 * against the Python content tables. Keys here are **content ids**, not display
 * names, so renaming a monster in the tables cannot orphan its art.
 */

import { creatureSvg, CREATURE_KEYS } from "./creatures";
import {
  POTION_KEYS_ART, RELIC_KEYS, potionSigil, relicSigil,
} from "./sigils";

/** Only reached if a content id has no art, which the manifest test prevents. */
export const FALLBACK = { creature: "👾", relic: "◈", potion: "🧪" } as const;

export const creature = (key: string) => creatureSvg(key) ?? FALLBACK.creature;
export const relic = (key: string) => relicSigil(key) ?? FALLBACK.relic;
export const potion = (key: string) => potionSigil(key) ?? FALLBACK.potion;

/** Read at build time by the art-manifest plugin. */
export function manifest() {
  return {
    creatures: CREATURE_KEYS,
    relics: RELIC_KEYS,
    potions: POTION_KEYS_ART,
  };
}
