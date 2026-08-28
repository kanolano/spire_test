/**
 * The page skeleton the client expects to already exist.
 *
 * `dom.$` throws on a missing element by design, so every module that touches
 * the page needs index.html's shell in place before it is imported. Kept in
 * one place and derived from the real ids rather than copied per test, so a
 * renamed element breaks the tests loudly instead of one at a time.
 */

export const SHELL_IDS = [
  "top", "s-act", "s-hp", "s-hpwrap", "s-hptext", "s-gold", "s-decksize",
  "s-relics", "s-potions", "s-status", "s-sound", "stage", "hint", "toasts",
  "tip", "announcer", "curtain", "curtain-msg",
] as const;

export function mountShell(): void {
  document.body.innerHTML =
    SHELL_IDS.map((id) => `<div id="${id}"></div>`).join("")
    + `<div id="overlay"><button class="close"></button>`
    + `<div id="overlay-title"></div><div id="overlay-body"></div></div>`;
}

/** A minimal but structurally honest server snapshot. */
export function fakeState(over: Record<string, unknown> = {}) {
  return {
    screen: "map",
    fx: [],
    act: 1,
    ascension: 0,
    floor: 1,
    floors_cleared: 0,
    elites_killed: 0,
    banner: null,
    killer: "—",
    seed: 1,
    pending: { kind: "map_node", options: [0] },
    player: {
      name: "The Sentinel", cls: "sentinel", hp: 70, max_hp: 75, block: 0,
      gold: 99, deck_size: 10, statuses: [], relics: [], potions: [],
      max_potions: 3, energy: 3, max_energy: 3,
    },
    deck: [],
    map: {
      floors: [[{ type: "monster", edges: [] }]],
      cur_floor: -1, cur_idx: 0, visited: [], reachable: [0],
      act_name: "The Ashen Reach", act_theme: "ash",
    },
    // Screens read their own slice of the snapshot, so a state that names a
    // screen has to carry that screen's payload or the renderer throws.
    reward: {
      gold: 12, kind: "monster", log: [], relic: null, potion: null,
      cards: [], relic_taken: false, potion_taken: false, card_taken: false,
      potions_full: false,
    },
    shop: {
      relic_price: 150, removal_price: 75, removed: false,
      cards: [], relic: null, potions: [],
    },
    combat: {
      label: "COMBAT — floor 1", kind: "monster", turn: 1, energy: 3,
      enemies: [{
        key: "jaw_worm", name: "Jaw Worm", hp: 40, max_hp: 40, block: 0,
        alive: true, statuses: [],
        intent: { kind: "attack", damage: 11, hits: 1, extra: false, note: "" },
      }],
      hand: [], draw: 5, discard: 0, exhaust: 0, log: [],
    },
    classes: [],
    ascension_ladder: [],
    ...over,
  } as never;
}

/** A card shaped the way the server actually sends one. */
export function fakeCard(over: Record<string, unknown> = {}) {
  return {
    i: null, uid: 1, key: "strike", name: "Strike", type: "ATTACK",
    cost: 1, desc: "Deal 6 damage.", upgraded: false, playable: true,
    targeted: true, requires: null, up: null,
    ...over,
  } as never;
}

/**
 * jsdom has no matchMedia, and `reducedMotion()` asks it whether to animate.
 * Defaults to "no preference" so tests exercise the animated path unless they
 * say otherwise.
 */
export function stubMatchMedia(matches = false): void {
  Object.defineProperty(window, "matchMedia", {
    writable: true, configurable: true,
    value: (query: string) => ({
      matches, media: query, onchange: null,
      addEventListener() {}, removeEventListener() {},
      addListener() {}, removeListener() {}, dispatchEvent: () => false,
    }),
  });
}

