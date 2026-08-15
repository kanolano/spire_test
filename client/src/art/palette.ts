/**
 * The colour vocabulary every creature draws from.
 *
 * A set of 29 sprites drawn one at a time turns into clipart. What stops that
 * is a fixed number of ramps: each creature picks one, and gets its body
 * gradient, rim light and eye glow from it. Family resemblance is then a
 * property of the system rather than something to remember.
 *
 * The ramps are pulled toward the palette already in app.css — ash, ember,
 * old gold, dried blood — so the creatures sit in the room they are lit by.
 */

export interface Ramp {
  /** Deepest tone: the bottom of the body, and its silhouette. */
  ink: string;
  /** Body top, where the light falls. */
  shade: string;
  /** Rim light along the upper edge. */
  rim: string;
  /** Eyes, cracks, embers — the one saturated thing in the sprite. */
  glow: string;
}

export const RAMPS = {
  /** Grubs, beasts, anything with warm dead skin. */
  flesh: { ink: "#3a1f1e", shade: "#8a4a3f", rim: "#c98a72", glow: "#ffb08a" },
  /** Ash-born: charcoal bodies lit from inside. */
  ash: { ink: "#241d24", shade: "#4e4148", rim: "#8c7a80", glow: "#ff8a3c" },
  /** Slimes and oozes. */
  ooze: { ink: "#173322", shade: "#3f8452", rim: "#84d09a", glow: "#b8ffcf" },
  /** The blue slime family, so the two read apart at a glance. */
  brine: { ink: "#152c3a", shade: "#356f8e", rim: "#7fc0dc", glow: "#b6ecff" },
  /** Gremlins: sickly, bright, unpleasant. */
  bile: { ink: "#2a2f16", shade: "#657033", rim: "#a8b566", glow: "#d8ff6e" },
  /** Stone, metal, anything built rather than born. */
  stone: { ink: "#22222c", shade: "#4c4c5c", rim: "#8a8aa0", glow: "#ffc36a" },
  /** Cultists, mystics, the Chosen — cloth and candlelight. */
  cloth: { ink: "#2a1830", shade: "#5b3468", rim: "#a077b4", glow: "#e2a6ff" },
  /** Ghosts and the merely dead. */
  spectre: { ink: "#1d2436", shade: "#3d4b6b", rim: "#8fa2cc", glow: "#bfe4ff" },
  /** Bone. */
  bone: { ink: "#332e26", shade: "#8c8271", rim: "#d6cbb4", glow: "#ffeccb" },
  /** Bosses and anything that should look expensive. */
  regal: { ink: "#331a10", shade: "#7d4a1c", rim: "#d9a75a", glow: "#ffd482" },
} as const satisfies Record<string, Ramp>;

export type RampName = keyof typeof RAMPS;

export const RAMP_NAMES = Object.keys(RAMPS) as RampName[];
