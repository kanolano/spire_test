/**
 * One table per screen: how to draw it, what the hint bar says, and which keys
 * it answers to. These used to be three separate if-chains that had to be kept
 * in sync by hand.
 */

import { play as playFx } from "./director";
import { $, el, esc } from "./dom";
import {
  combatHint, combatKeys, mountCombat, unmountCombat, updateCombat,
} from "./screens/combat";
import {
  eventKeys, renderEvent, renderTreasure, treasureKeys,
} from "./screens/event";
import { mapKeys, renderMap } from "./screens/map";
import { endKeys, renderEnd, renderSelect, selectKeys } from "./screens/meta";
import {
  chooseKeys, renderChoose, renderReward, rewardHint, rewardKeys,
} from "./screens/reward";
import { renderShop, shopKeys } from "./screens/shop";
import { renderRest, restKeys } from "./screens/rest";
import {
  lastScreen, pendingFx, prev, S, setLastScreen, setPendingFx,
} from "./store";
import type { Screen } from "./types";
import { hideTip } from "./ui/tooltip";
import { renderTop } from "./ui/topbar";

interface ScreenDef {
  render: (st: HTMLElement) => void;
  hint: string | (() => string);
  keys?: (k: string, num: number, ev: KeyboardEvent) => void;
}

export const SCREENS: Record<Screen, ScreenDef> = {
  select: {
    render: renderSelect,
    hint: "1–9 pick a class",
    keys: selectKeys,
  },
  map: {
    render: renderMap,
    hint: "click a node or press its letter · i deck · ? help",
    keys: mapKeys,
  },
  combat: {
    render: mountCombat,
    hint: combatHint,
    keys: combatKeys,
  },
  reward: {
    render: renderReward,
    hint: rewardHint,
    keys: rewardKeys,
  },
  choose: {
    render: renderChoose,
    hint: "1–9 pick",
    keys: chooseKeys,
  },
  rest: {
    render: renderRest,
    hint: "1 rest · 2 smith · 3 purge",
    keys: restKeys,
  },
  shop: {
    render: renderShop,
    hint: "1–5 cards · r relic · q w e potions · x removal · esc leave",
    keys: shopKeys,
  },
  event: {
    render: renderEvent,
    hint: "1–3 choose · enter continue",
    keys: eventKeys,
  },
  treasure: {
    render: renderTreasure,
    hint: "enter continue",
    keys: treasureKeys,
  },
  gameover: {
    render: (st) => renderEnd(st, false),
    hint: "enter to climb again · c to change class",
    keys: endKeys,
  },
  win: {
    render: (st) => renderEnd(st, true),
    hint: "enter to climb again · c to change class",
    keys: endKeys,
  },
};

export function render() {
  hideTip();                 // whatever it was anchored to is about to be replaced
  renderTop();
  const state = S();
  const st = $("#stage");
  const staying = state.screen === "combat" && lastScreen === "combat";
  const animate = pendingFx;
  setPendingFx(false);

  // Combat is the one screen that survives a state change. Everything else is
  // still cheapest to rebuild, and none of it needs node identity.
  if (staying) {
    hint();
    // The director starts from the previous snapshot and reconciles to this
    // one; on a re-render with nothing new to show (cancelling a selection)
    // it just updates.
    if (animate) playFx(prev(), state, state.fx ?? []);
    else updateCombat(state);
    announceCombat();
    return;
  }

  if (lastScreen === "combat") unmountCombat();
  st.innerHTML = "";
  const changed = state.screen !== lastScreen;
  st.className = "screen-" + state.screen;
  // Every screen change used to be the same 0.22s fade, so leaving a shop and
  // walking into a fight felt identical. Direction of travel now shows.
  if (changed) { void st.offsetWidth; st.classList.add(transition(lastScreen, state.screen)); }
  setLastScreen(state.screen);

  if (state.banner) {
    st.appendChild(el("div", "result",
      `<b>${esc(state.banner[0])}</b><br>${esc(state.banner[1])}`));
    announce(`${state.banner[0]}. ${state.banner[1]}`);
  }

  const screen = SCREENS[state.screen];
  if (screen) screen.render(st);
  else st.appendChild(el("div", "center", "…"));

  hint();
  announceCombat();
}

/**
 * Which way the screen moved.
 *
 * The map is the hub: everything else is somewhere you went *into* from it, so
 * arriving at the map is coming back. The three screens that are not part of a
 * climb at all — picking a class, and the two endings — do not travel; they
 * settle.
 */
function transition(from: string | null, to: string): string {
  if (!from || to === "select" || to === "gameover" || to === "win") return "enter-settle";
  if (to === "map") return "enter-back";
  return "enter-fwd";
}

function hint() {
  const screen = SCREENS[S().screen];
  const h = screen ? (typeof screen.hint === "function" ? screen.hint() : screen.hint) : "";
  $("#hint").textContent = h;
}

/**
 * The combat log and the floating damage numbers are purely visual; without
 * this the game is silent to assistive tech.
 */
let lastAnnounced = "";
export function announce(text: string) {
  if (!text || text === lastAnnounced) return;
  lastAnnounced = text;
  $("#announcer").textContent = text;
}

function announceCombat() {
  const state = S();
  if (!state.combat) return;
  const tail = state.combat.log.slice(-2).join(". ");
  const p = state.player;
  announce(`${tail}. You have ${p.hp} of ${p.max_hp} hit points`
    + (p.block ? `, ${p.block} block` : "") + ".");
}
