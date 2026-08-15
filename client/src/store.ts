/**
 * Client state: the last two server snapshots, and what the player is
 * part-way through choosing.
 *
 * `render` is registered rather than imported so that actions.ts does not have
 * to import render.ts, which imports the screens, which send actions. The
 * indirection is only there to keep that cycle from existing.
 */

import type { State } from "./types";

/** A card or potion mid-play, waiting on a target or an extra choice. */
export interface Selection {
  kind: "card" | "potion";
  idx: number;
  mode: "target" | "hand";
  target?: number | null;
}

let state: State | null = null;
let previous: State | null = null;
let selection: Selection | null = null;

/** Share today's seed with everyone else. Client-only. */
export let dailyMode = false;
export const setDailyMode = (on: boolean) => { dailyMode = on; };

/** So animations only fire on real changes, not on a re-render. */
export let lastScreen: string | null = null;
export let lastTurn = -1;
export let pendingFx = false;

export const setLastScreen = (s: string | null) => { lastScreen = s; };
export const setLastTurn = (t: number) => { lastTurn = t; };
export const setPendingFx = (on: boolean) => { pendingFx = on; };

/** The current snapshot. Throws if read before boot — every screen renderer
 *  runs after a successful fetch, so this is a bug, not a state. */
export function S(): State {
  if (!state) throw new Error("read state before boot");
  return state;
}
export const maybeS = () => state;
export const prev = () => previous;

export function setState(next: State, keepPrev = false) {
  if (!keepPrev) previous = state;
  state = next;
}

export const sel = () => selection;
export const setSel = (s: Selection | null) => { selection = s; };

export function resetForNewRun() {
  previous = null;
  selection = null;
  pendingFx = false;
  lastScreen = null;
  lastTurn = -1;
}

let renderHook: (() => void) | null = null;
export const onRender = (fn: () => void) => { renderHook = fn; };
export const render = () => renderHook?.();
