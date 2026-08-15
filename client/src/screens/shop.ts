import { send } from "../actions";
import { ctaButton, el, esc } from "../dom";
import { S } from "../store";
import type { Action } from "../types";
import { cardEl } from "../ui/card";

// The shop needs its own letters: POTION_KEYS[2] is "r", which the relic wants.
const SHOP_POTION_KEYS = "qwe";

/** letter -> action, rebuilt by renderShop. */
let SHOP_KEYS: Record<string, Action | null> = {};

export function renderShop(st: HTMLElement) {
  const state = S();
  const sh = state.shop!;
  const gold = state.player.gold;

  st.appendChild(el("h2", "title", "The merchant"));
  st.appendChild(el("div", "sub", `Your gold: ${gold}`));

  const row = el("div", "row");
  row.style.margin = "18px 0 26px";
  sh.cards.forEach((c, i) => row.appendChild(cardEl(c, {
    price: c.price ?? null, kbd: i + 1, dim: (c.price ?? 0) > gold,
    onclick: () => {
      if ((c.price ?? 0) <= gold) void send({ type: "shop_buy", what: "card", idx: i });
    },
  })));
  st.appendChild(row);

  SHOP_KEYS = {};
  // Everything below the cards used to be mouse-only, and its "not enough
  // gold" was a native title= that never appeared on touch.
  const stall = (
    kbd: string, name: string, desc: string, price: number,
    action: Action, blocked?: string,
  ) => {
    const it = el("div", "item",
      `<span class="nm">${esc(name)}</span><span class="ds">${esc(desc)}</span>`);
    const b = el("button", "buy", `<kbd>${kbd}</kbd> ${price} gold`);
    const why = blocked || (gold < price ? "Not enough gold" : "");
    b.disabled = Boolean(why);
    if (why) b.setAttribute("data-tip", why);
    else b.onclick = () => void send(action);
    it.appendChild(b);
    st.appendChild(it);
    SHOP_KEYS[kbd] = why ? null : action;
  };

  if (sh.relic) {
    stall("r", sh.relic.name, sh.relic.desc, sh.relic_price,
      { type: "shop_buy", what: "relic" });
  }
  const full = state.player.potions.length >= state.player.max_potions;
  sh.potions.forEach((q, i) =>
    stall(SHOP_POTION_KEYS[i]!, q.name, q.desc, q.price ?? 0,
      { type: "shop_buy", what: "potion", idx: i },
      full ? "Your potion slots are full" : ""));
  if (!sh.removed) {
    stall("x", "Card removal", "Purge one card from your deck.", sh.removal_price,
      { type: "shop_buy", what: "removal" });
  }

  st.appendChild(ctaButton("Leave <kbd>Esc</kbd>", () => void send({ type: "shop_leave" })));
}

export function shopKeys(k: string, num: number) {
  const state = S();
  const sh = state.shop!;
  const card = sh.cards[num];
  if (num >= 0 && card && (card.price ?? 0) <= state.player.gold) {
    void send({ type: "shop_buy", what: "card", idx: num });
    return;
  }
  const action = SHOP_KEYS[k];
  if (action) void send(action);
}
