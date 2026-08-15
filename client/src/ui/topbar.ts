import * as art from "../art/registry";
import { $, esc, tipAttrs } from "../dom";
import { S } from "../store";
import { statusChip } from "./chips";

const POTION_KEYS = "qwrtyu";   // was hardcoded as "qwr" in three places

export { POTION_KEYS };

export function renderTop() {
  const st = S();
  const p = st.player;
  // No run in progress yet — the placeholder player behind the select screen
  // is not yours.
  $("#top").style.visibility = st.screen === "select" ? "hidden" : "visible";
  $("#s-act").textContent =
    `Act ${st.act}` + (st.floor > 0 ? ` · Floor ${st.floor}` : "");

  const pct = Math.max(0, p.hp) / p.max_hp * 100;
  $("#s-hp").style.width = pct + "%";
  $("#s-hpwrap").classList.toggle("low", pct < 35);
  $("#s-hptext").textContent = `${p.hp} / ${p.max_hp}`;
  $("#s-gold").innerHTML =
    `<span class="ic" style="color:var(--gold)">◉</span> ${p.gold}`;
  $("#s-decksize").textContent = `(${p.deck_size})`;
  $("#s-status").innerHTML = p.statuses.map(statusChip).join("");

  // Native title= is slow and invisible on touch, so these use the same
  // tooltip as the status chips and stay buttons that open the overlay.
  $("#s-relics").innerHTML = p.relics.map((r, i) =>
    `<button class="icon" data-act="relic" data-i="${i}"`
    + tipAttrs(r.name, r.desc)
    + ` aria-label="${esc(r.name)}: ${esc(r.desc)}">`
    + `${art.relic(r.key)}</button>`).join("");

  $("#s-potions").innerHTML = p.potions.map((q, i) =>
    `<button class="icon potion" data-act="potion" data-i="${i}"`
    + tipAttrs(q.name, q.desc)
    + ` aria-label="${esc(q.name)}: ${esc(q.desc)}">`
    + `${art.potion(q.key)}`
    + `<span class="key" aria-hidden="true">${POTION_KEYS[i] || ""}</span>`
    + `</button>`).join("");
}
