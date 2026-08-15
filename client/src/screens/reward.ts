/**
 * Rewards used to be granted the instant the last enemy died and reported as
 * one run-on sentence. Each one is now a row you take or leave, and the screen
 * stays put until you say you are done.
 */

import { send } from "../actions";
import * as art from "../art/registry";
import { ctaButton, el, esc, staggerIn } from "../dom";
import { S } from "../store";
import { cardEl, withUpgrade } from "../ui/card";

const REWARD_TITLE: Record<string, string> = {
  monster: "Victory", elite: "Elite slain", boss: "Boss slain",
};

interface RowOpts {
  kbd: string;
  taken: boolean;
  blocked?: string | null;
  onclick: () => void;
}

function rewardRow(icon: string, name: string, desc: string, opts: RowOpts) {
  const row = el("div", "item reward-row");
  row.innerHTML = `<span class="rico" aria-hidden="true">${icon}</span>`
    + `<span class="nm">${esc(name)}</span><span class="ds">${esc(desc)}</span>`;
  if (opts.taken) {
    row.appendChild(el("span", "ghost taken", "Taken"));
    row.classList.add("done");
    return row;
  }
  const b = el("button", "buy", `Take <kbd>${opts.kbd}</kbd>`);
  b.onclick = opts.onclick;
  if (opts.blocked) { b.disabled = true; b.title = opts.blocked; }
  row.appendChild(b);
  return row;
}

export function renderReward(st: HTMLElement) {
  const r = S().reward!;
  st.appendChild(el("h2", "title", REWARD_TITLE[r.kind] || "Victory"));
  if (r.log && r.log.length) {
    st.appendChild(el("div", "combatlog", r.log.map(esc).join("<br>")));
  }
  st.appendChild(el("div", "sub", `You find ${r.gold} gold.`));

  const items = el("div", "rewards");
  if (r.relic) {
    items.appendChild(rewardRow(art.relic(r.relic.key), r.relic.name, r.relic.desc, {
      kbd: "R", taken: r.relic_taken,
      onclick: () => void send({ type: "reward", what: "relic" }),
    }));
  }
  if (r.potion) {
    items.appendChild(rewardRow(art.potion(r.potion.key), r.potion.name, r.potion.desc, {
      kbd: "P", taken: r.potion_taken,
      blocked: r.potions_full ? "Your potion slots are full" : null,
      onclick: () => void send({ type: "reward", what: "potion" }),
    }));
  }
  if (items.children.length) { staggerIn(items.children); st.appendChild(items); }

  if (r.card_taken) {
    st.appendChild(el("div", "center ghost", "Card added to your deck."));
  } else {
    st.appendChild(el("div", "center ghost", "Choose one card to add to your deck"));
    const row = el("div", "row");
    row.style.marginTop = "16px";
    r.cards.forEach((c, i) => row.appendChild(cardEl(c, {
      kbd: i + 1,
      onclick: () => void send({ type: "reward", what: "card", idx: i }),
    })));
    // Dealt after the relic and potion rows have landed, so the eye is led
    // down the screen in the order the choices are made.
    staggerIn(row.children, 0.06, 0.16);
    st.appendChild(row);
  }

  const left = (r.relic && !r.relic_taken)
    || (r.potion && !r.potion_taken && !r.potions_full)
    || !r.card_taken;
  st.appendChild(ctaButton(
    (left ? "Leave the rest" : "Continue") + " <kbd>Enter</kbd>",
    () => void send({ type: "reward_done" }),
    left ? "tbtn" : "cta"));
}

export const rewardHint = () => {
  const r = S().reward!;
  return [
    !r.card_taken ? "1–3 take a card" : null,
    r.relic && !r.relic_taken ? "r relic" : null,
    r.potion && !r.potion_taken && !r.potions_full ? "p potion" : null,
    "enter continue",
  ].filter(Boolean).join(" · ");
};

export function rewardKeys(k: string, num: number) {
  const r = S().reward!;
  if (k === "enter" || k === "s") { void send({ type: "reward_done" }); return; }
  if (k === "r" && r.relic && !r.relic_taken) {
    void send({ type: "reward", what: "relic" }); return;
  }
  if (k === "p" && r.potion && !r.potion_taken && !r.potions_full) {
    void send({ type: "reward", what: "potion" }); return;
  }
  if (!r.card_taken && num >= 0 && num < r.cards.length) {
    void send({ type: "reward", what: "card", idx: num });
  }
}

export function renderChoose(st: HTMLElement) {
  const ch = S().choose!;
  st.appendChild(el("h2", "title", esc(ch.title)));
  if (ch.kind === "upgrade") {
    st.appendChild(el("div", "sub", "Each card is shown with what it becomes."));
  }
  const row = el("div", "row");
  row.style.marginTop = "14px";
  ch.cards.forEach((c, i) => {
    const go = () => void send({ type: "choose", idx: i });
    const card = cardEl(c, { pick: true, kbd: i < 9 ? i + 1 : null, onclick: go });
    if (ch.kind !== "upgrade" || !c.up) { row.appendChild(card); return; }
    row.appendChild(withUpgrade(card, c, go));
  });
  // A whole deck can land here, so the step is short: 20 cards at 0.05s each
  // would take a second to finish dealing.
  staggerIn(row.children, 0.02);
  st.appendChild(row);
  if (ch.kind === "remove") {
    st.appendChild(ctaButton("Change my mind <kbd>Esc</kbd>",
      () => void send({ type: "choose", idx: null })));
  }
}

export function chooseKeys(_k: string, num: number) {
  if (num >= 0 && num < S().choose!.cards.length) void send({ type: "choose", idx: num });
}
