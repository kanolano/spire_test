/**
 * One tooltip element, fed by anything rendered with data-tip.
 *
 * Status chips were cursor:help with nothing behind them — the label is a
 * four-letter abbreviation and the game never said anywhere what it meant.
 * Relics and potions had native title=, which is slow to appear and shows
 * nothing at all on touch.
 */

import { $, esc } from "../dom";

let tipFor: Element | null = null;

export function showTip(node: Element) {
  const name = node.getAttribute("data-tip");
  if (!name) return;
  const desc = node.getAttribute("data-tip-desc");
  const tip = $("#tip");
  tip.innerHTML = `<b>${esc(name)}</b>` + (desc ? `<span>${esc(desc)}</span>` : "");
  tip.hidden = false;
  tipFor = node;
  placeTip(node);
}

function placeTip(node: Element) {
  const tip = $("#tip");
  const r = node.getBoundingClientRect();
  const pad = 8;
  const w = tip.offsetWidth;
  const h = tip.offsetHeight;
  const left = Math.min(
    Math.max(pad, r.left + r.width / 2 - w / 2),
    window.innerWidth - w - pad,
  );
  // below the chip, unless that would run off the bottom
  let top = r.bottom + pad;
  if (top + h > window.innerHeight - pad) top = r.top - h - pad;
  tip.style.left = Math.round(left) + "px";
  tip.style.top = Math.round(Math.max(pad, top)) + "px";
}

export function hideTip() {
  if (!tipFor) return;
  $("#tip").hidden = true;
  tipFor = null;
}

/**
 * Delegated, so anything rendered with data-tip picks it up without knowing
 * the tooltip exists.
 */
export function wireTooltips() {
  document.addEventListener("mouseover", (ev) => {
    const node = (ev.target as Element | null)?.closest("[data-tip]") ?? null;
    if (node === tipFor) return;
    hideTip();
    if (node) showTip(node);
  });
  document.addEventListener("mouseout", (ev) => {
    const to = (ev as MouseEvent).relatedTarget as Node | null;
    if (tipFor && !tipFor.contains(to)) hideTip();
  });
  document.addEventListener("focusin", (ev) => {
    const node = (ev.target as Element | null)?.closest("[data-tip]") ?? null;
    hideTip();
    if (node) showTip(node);
  });
  document.addEventListener("focusout", hideTip);

  // Touch has no hover: tap a chip to pin its tooltip, tap elsewhere to drop
  // it. Relics and potions are left out — they already open the overlay on
  // tap. Capture phase, because an enemy's chips sit inside the enemy: tapping
  // one to read it must not also pick that enemy as a target.
  document.addEventListener("click", (ev) => {
    const node = (ev.target as Element | null)
      ?.closest("[data-tip]:not([data-act])") ?? null;
    if (!node) { hideTip(); return; }
    if (node !== tipFor) showTip(node);
    ev.stopPropagation();
  }, true);

  window.addEventListener("scroll", hideTip, true);
  window.addEventListener("resize", hideTip);
}
