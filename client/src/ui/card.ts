/** The one card factory, used by combat, rewards, shop, pickers and the deck. */

import { el, esc } from "../dom";
import type { CardView } from "../types";

export interface CardOpts {
  combat?: boolean;
  dim?: boolean;
  static?: boolean;
  pick?: boolean;
  selected?: boolean;
  kbd?: number | string | null;
  price?: number | null;
  onclick?: () => void;
}

export function cardEl(c: CardView, opts: CardOpts = {}): HTMLDivElement {
  const cls = "card t-" + c.type
    + (c.upgraded ? " up" : "")
    + (opts.dim || (c.playable === false && opts.combat) ? " unplayable" : "")
    + (opts.static ? " static" : "")
    + (opts.pick ? " pick" : "");
  const d = el("div", cls);
  // Stable identity, so a card can be tracked from hand to target to discard.
  d.dataset.uid = String(c.uid);
  d.innerHTML =
    `<div class="cost">${c.cost}</div>` +
    (opts.kbd != null ? `<div class="kbd">${opts.kbd}</div>` : "") +
    `<div class="cname">${esc(c.name)}</div><div class="ctype">${c.type}</div>` +
    `<div class="cdesc">${esc(c.desc)}</div>` +
    (opts.price != null ? `<div class="price">${opts.price} gold</div>` : "");

  if (opts.onclick) {
    // Cards are divs, so they need the button contract spelled out.
    const go = opts.onclick;
    d.onclick = go;
    d.tabIndex = 0;
    d.setAttribute("role", "button");
    d.addEventListener("keydown", (ev) => {
      if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); go(); }
    });
  }
  d.setAttribute("aria-label",
    `${c.name}, ${c.type.toLowerCase()}, cost ${c.cost}. ${c.desc}` +
    (opts.price != null ? ` Price ${opts.price} gold.` : "") +
    (c.playable === false && opts.combat ? " Not playable right now." : ""));
  if (opts.selected) {
    d.classList.add("sel");
    d.setAttribute("aria-pressed", "true");
  }
  return d;
}

/**
 * A card stacked with what it becomes when upgraded. Used by the upgrade
 * picker and by the deck overlay, so "what does + do to this?" is answerable
 * at any time rather than only at the moment you commit to it.
 */
export function withUpgrade(card: HTMLElement, c: CardView, onclick: (() => void) | null) {
  const stack = el("div", "upstack");
  stack.appendChild(card);
  const up = c.up!;
  const to = el("div", "upto",
    `<div class="upname">${esc(up.name)}` +
    (up.cost !== c.cost ? `<span class="upcost">${c.cost} → ${up.cost}</span>` : "") +
    `</div><div class="updesc">${esc(up.desc)}</div>`);
  if (onclick) to.onclick = onclick;
  else to.classList.add("static");
  stack.appendChild(to);
  return stack;
}
