/**
 * Global input, all delegated at document level — deliberately, so no handler
 * is ever interpolated into an innerHTML string, which forced every render
 * function into global scope and ruled out a CSP.
 */

import { reconnect, send } from "./actions";
import { isPlaying, skip } from "./director";
import { isOffline } from "./net";
import { SCREENS } from "./render";
import { clickPotion } from "./screens/combat";
import { maybeS, render, S, sel, setSel } from "./store";
import {
  closeOverlay, confirmQuit, overlayOpen, pendingConfirm, showDeck, showHelp,
  showPile, showRelics,
} from "./ui/overlay";

export function wireInput() {
  document.addEventListener("keydown", (ev) => {
    if (ev.metaKey || ev.ctrlKey || ev.altKey) return;
    const k = ev.key.toLowerCase();

    // Impatience is the common case on a replayed turn: the first keypress
    // fast-forwards rather than queueing behind the animation.
    if (isPlaying() && !overlayOpen()) { ev.preventDefault(); skip(); return; }

    if (overlayOpen()) {
      // "1" confirms; Enter deliberately does not, so a stray keypress on the
      // continue-flavoured key cannot throw a run away.
      const confirm = pendingConfirm();
      if (confirm && k === "1") { closeOverlay(); confirm(); return; }
      if (k === "escape" || k === "i" || k === "?") closeOverlay();
      return;
    }
    if (isOffline()) return;

    const state = maybeS();
    if (k === "i") { if (state && state.screen !== "select") showDeck(); return; }
    if (k === "?" || (k === "/" && ev.shiftKey)) { showHelp(); return; }
    if (!state) return;

    if (k === "escape") {
      if (sel()) { setSel(null); render(); }
      else if (state.screen === "shop") void send({ type: "shop_leave" });
      else if (state.screen === "choose" && state.choose?.kind === "remove") {
        void send({ type: "choose", idx: null });
      }
      return;
    }

    SCREENS[state.screen]?.keys?.(k, "1234567890".indexOf(ev.key), ev);
  });

  document.addEventListener("click", (ev) => {
    if (isPlaying() && !overlayOpen()) { skip(); return; }
    const target = (ev.target as Element | null)?.closest<HTMLElement>("[data-act]");
    if (!target) return;
    const i = Number(target.dataset.i);
    switch (target.dataset.act) {
      case "deck":
        if (maybeS() && S().screen !== "select") showDeck();
        break;
      case "help": showHelp(); break;
      case "close-overlay": closeOverlay(); break;
      case "quit": if (maybeS()) confirmQuit(); break;
      case "relic": showRelics(); break;
      case "potion": clickPotion(i); break;
      case "pile": void showPile(target.dataset.pile!); break;
      case "reconnect": void reconnect(); break;
    }
  });

  // A machine coming back from sleep or a restarted server should recover.
  window.addEventListener("online", () => { if (isOffline()) void reconnect(); });
}
