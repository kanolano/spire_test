import { send } from "../actions";
import * as art from "../art/registry";
import { $, el, esc, LETTERS, tipAttrs } from "../dom";
import { S, render, lastTurn, sel, setLastTurn, setSel } from "../store";
import type { IntentKind, IntentView } from "../types";
import { cardEl } from "../ui/card";
import { statusChip } from "../ui/chips";
import { POTION_KEYS } from "../ui/topbar";

// Non-attack intents used to read "▲ buff". The move's own name says far more,
// and the tooltip carries the kind and whatever note it has.
const GLYPH: Record<IntentKind, string> = {
  attack: "⚔", block: "🛡", buff: "▲", debuff: "▼",
};
const KIND_TIP: Record<IntentKind, string> = {
  attack: "It will attack.",
  block: "It is defending.",
  buff: "It is strengthening itself.",
  debuff: "It will weaken you.",
};

function intentBadge(it: IntentView): string {
  const body = it.kind === "attack"
    ? `${GLYPH.attack} ${it.dmg}${(it.hits ?? 1) > 1 ? ` × ${it.hits}` : ""}`
      + `${it.extra ? " +" : ""}`
    : `${GLYPH[it.kind] || "●"} ${esc(it.name)}`;
  return `<div class="intent ${it.kind}"`
    + tipAttrs(it.name, it.note || KIND_TIP[it.kind] || "") + `>${body}</div>`;
}

export function renderCombat(st: HTMLElement) {
  const state = S();
  const cb = state.combat!;
  const p = state.player;
  const s = sel();

  st.appendChild(el("div", "sub", `${esc(cb.label)} &nbsp;·&nbsp; turn ${cb.turn}`));

  const foes = el("div");
  foes.id = "enemies";
  cb.enemies.forEach((e, i) => {
    const targetable = s && s.mode === "target" && e.alive;
    const d = el("div", "foe" + (e.alive ? "" : " dead") + (targetable ? " targetable" : ""));
    d.dataset.foe = String(i);
    d.innerHTML =
      (e.alive && e.intent ? intentBadge(e.intent)
        : e.alive ? "" : "<div class='intent'>slain</div>") +
      `<div class="sprite">${art.creature(e.key)}</div><div class="shadow"></div>` +
      `<div class="fname">${e.alive ? `<span style="color:var(--gold)">${LETTERS[i]}</span> · ` : ""}`
        + `${esc(e.name)}${e.block ? `<span class="block-badge">🛡 ${e.block}</span>` : ""}</div>` +
      `<div class="fbar"><i style="width:${Math.max(0, e.hp) / e.max_hp * 100}%"></i>`
        + `<span class="fnum">${Math.max(0, e.hp)} / ${e.max_hp}</span></div>` +
      `<div class="chips" style="justify-content:center;margin-top:6px">`
        + e.statuses.map(statusChip).join("") + `</div>`;

    if (e.alive) {
      d.onclick = () => clickFoe(i);
      d.tabIndex = 0;
      d.setAttribute("role", "button");
      const hp = `${Math.max(0, e.hp)} of ${e.max_hp} hit points`;
      const it = e.intent;
      d.setAttribute("aria-label", `${e.name}, ${hp}`
        + (it ? `, intent ${it.kind}${it.kind === "attack" ? ` ${it.dmg} damage` : ""}` : ""));
      d.addEventListener("keydown", (ev) => {
        if (ev.target !== d) return;   // a focused status chip is not a target pick
        if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); clickFoe(i); }
      });
    }
    foes.appendChild(d);
  });
  st.appendChild(foes);

  const bar = el("div");
  bar.id = "playerbar";
  bar.innerHTML =
    `<div class="barlog">${cb.log.slice(-3).map((l) => `<div>${esc(l)}</div>`).join("")}</div>` +
    `<div class="barmain">
       <div class="orb">${p.energy}<span style="font-size:12px;opacity:.6">/${p.max_energy}</span></div>
       <div>
         <div class="pname">${esc(p.name)}
           ${p.block ? `<span class="block-badge">🛡 ${p.block}</span>` : ""}</div>
         <div class="hpwrap" style="width:230px;margin-top:5px">
           <i class="hpfill" style="width:${Math.max(0, p.hp) / p.max_hp * 100}%"></i>
           <span class="hptext">${p.hp} / ${p.max_hp}</span></div>
       </div>
     </div>`;

  const right = el("div", "barright");
  right.innerHTML =
    `<div class="piles">
       <button data-act="pile" data-pile="draw_pile">draw ${cb.draw}</button>
       <button data-act="pile" data-pile="discard_pile">discard ${cb.discard}</button>
       <button data-act="pile" data-pile="exhaust_pile">exhaust ${cb.exhaust}</button>
     </div>`;
  bar.appendChild(right);
  st.appendChild(bar);

  const hand = el("div");
  hand.id = "hand";
  if (cb.turn !== lastTurn) { hand.className = "deal"; setLastTurn(cb.turn); }  // new hand only
  cb.hand.forEach((c, i) => hand.appendChild(cardEl(c, {
    combat: true,
    kbd: (i + 1) % 10,
    selected: !!s && s.kind === "card" && s.idx === i,
    pick: !!s && s.mode === "hand" && i !== s.idx,
    onclick: () => clickCard(i),
  })));
  st.appendChild(hand);

  const btn = el("button", s ? "cancel" : undefined,
    s ? "Cancel <kbd>Esc</kbd>" : "End turn <kbd>E</kbd>");
  btn.id = "endturn";
  btn.onclick = s
    ? () => { setSel(null); render(); }
    : () => void send({ type: "end_turn" });
  right.appendChild(btn);
}

/* ── interaction ───────────────────────────────────────────── */

const living = () =>
  S().combat!.enemies.map((e, j) => (e.alive ? j : -1)).filter((j) => j >= 0);

export function clickCard(i: number) {
  const cb = S().combat!;
  const c = cb.hand[i];
  if (!c) return;
  const s = sel();
  if (s && s.mode === "hand") {                     // picking a card to exhaust
    if (i === s.idx) return;
    void send({ type: "play", idx: s.idx, target: s.target ?? null, exhaust: i });
    return;
  }
  if (!c.playable) return;
  const alive = living();
  if (c.targeted && alive.length > 1) {
    setSel({ kind: "card", idx: i, mode: "target" });
    render();
    return;
  }
  const target = c.targeted ? alive[0]! : null;
  if (c.needs_hand && cb.hand.length > 1) {
    setSel({ kind: "card", idx: i, mode: "hand", target });
    render();
    return;
  }
  void send({ type: "play", idx: i, target, exhaust: null });
}

export function clickPotion(i: number) {
  const state = S();
  if (state.screen !== "combat") return;
  const q = state.player.potions[i];
  if (!q) return;
  const alive = living();
  if (q.targeted && alive.length > 1) {
    setSel({ kind: "potion", idx: i, mode: "target" });
    render();
    return;
  }
  void send({ type: "potion", idx: i, target: q.targeted ? alive[0]! : null });
}

export function clickFoe(i: number) {
  const s = sel();
  if (!s || s.mode !== "target") return;
  if (s.kind === "potion") {
    void send({ type: "potion", idx: s.idx, target: i });
    return;
  }
  const cb = S().combat!;
  const c = cb.hand[s.idx];
  if (c?.needs_hand && cb.hand.length > 1) {
    setSel({ ...s, mode: "hand", target: i });
    render();
    return;
  }
  void send({ type: "play", idx: s.idx, target: i, exhaust: null });
}

export function combatKeys(k: string, num: number, ev: KeyboardEvent) {
  const state = S();
  if (k === "e" || k === " ") {
    ev.preventDefault();
    if (!sel()) void send({ type: "end_turn" });
    return;
  }
  const potIdx = POTION_KEYS.indexOf(k);
  if (potIdx >= 0 && potIdx < state.player.max_potions) { clickPotion(potIdx); return; }
  const s = sel();
  if (s && s.mode === "target") {
    const fi = LETTERS.indexOf(k);
    const foe = state.combat!.enemies[fi];
    if (fi >= 0 && foe?.alive) { clickFoe(fi); return; }
  }
  if (num >= 0 && num < state.combat!.hand.length) clickCard(num);
}

export const combatHint = () =>
  `1–9 play · e end turn · a–d target · `
  + `${POTION_KEYS.slice(0, S().player.max_potions).split("").join(" ")} potions · `
  + `esc cancel · i deck`;

/** Used by the fx layer to find a rendered enemy. */
export const foeNode = (i: number) =>
  $("#stage").querySelector<HTMLElement>(`.foe[data-foe="${i}"]`);
