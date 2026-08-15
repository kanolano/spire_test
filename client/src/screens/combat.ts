/**
 * The combat screen, which — unlike every other screen — is not rebuilt on
 * each state change.
 *
 * `render()` used to do `stage.innerHTML = ""` unconditionally, so nothing
 * survived long enough to animate: a card could not fly anywhere because the
 * card that would have flown had already been destroyed. Combat now mounts
 * once and reconciles, keying enemies by index (they never reorder — dead ones
 * stay in place) and hand cards by their per-instance uid.
 *
 * Direct DOM handles are kept in `scene` so the director can drive individual
 * parts of it mid-timeline without a lookup or a re-render.
 */

import { send } from "../actions";
import * as art from "../art/registry";
import { el, esc, LETTERS, tipAttrs } from "../dom";
import { S, sel, setSel } from "../store";
import type { CardView, EnemyView, IntentKind, IntentView, State } from "../types";
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

export interface FoeNodes {
  root: HTMLElement;
  intent: HTMLElement;
  sprite: HTMLElement;
  body: HTMLElement;
  name: HTMLElement;
  barFill: HTMLElement;
  barNum: HTMLElement;
  chips: HTMLElement;
}

interface Scene {
  stage: HTMLElement;
  head: HTMLElement;
  foes: FoeNodes[];
  bar: HTMLElement;
  log: HTMLElement;
  orb: HTMLElement;
  pname: HTMLElement;
  hpFill: HTMLElement;
  hpText: HTMLElement;
  piles: HTMLElement;
  endturn: HTMLButtonElement;
  hand: HTMLElement;
  cards: Map<number, HTMLElement>;
}

let scene: Scene | null = null;

export const combatScene = () => scene;
export const foeNode = (i: number) => scene?.foes[i]?.root ?? null;
export const cardNode = (uid: number) => scene?.cards.get(uid) ?? null;

/** Called when leaving combat, so the next fight builds a fresh scene. */
export function unmountCombat() {
  scene = null;
}

function intentHtml(it: IntentView): string {
  return it.kind === "attack"
    ? `${GLYPH.attack} ${it.dmg}${(it.hits ?? 1) > 1 ? ` × ${it.hits}` : ""}`
      + `${it.extra ? " +" : ""}`
    : `${GLYPH[it.kind] || "●"} ${esc(it.name)}`;
}

/* ── mount ─────────────────────────────────────────────────── */

export function mountCombat(stage: HTMLElement) {
  const state = S();
  const cb = state.combat!;

  const head = el("div", "sub");
  stage.appendChild(head);

  const foesWrap = el("div");
  foesWrap.id = "enemies";
  const foes: FoeNodes[] = cb.enemies.map((_e, i) => {
    const root = el("div", "foe");
    root.dataset.foe = String(i);
    const intent = el("div", "intent");
    // The sprite sits inside a wrapper so idle bob (on .sprite) and directed
    // motion like a lunge (on .foe-body) never fight over one transform.
    const body = el("div", "foe-body");
    const sprite = el("div", "sprite");
    body.appendChild(sprite);
    const shadow = el("div", "shadow");
    const name = el("div", "fname");
    const bar = el("div", "fbar");
    const barFill = el("i");
    const barNum = el("span", "fnum");
    bar.appendChild(barFill);
    bar.appendChild(barNum);
    const chips = el("div", "chips foe-chips");

    root.append(intent, body, shadow, name, bar, chips);

    root.tabIndex = 0;
    root.setAttribute("role", "button");
    root.onclick = () => clickFoe(i);
    root.addEventListener("keydown", (ev) => {
      if (ev.target !== root) return;   // a focused status chip is not a target pick
      if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); clickFoe(i); }
    });
    foesWrap.appendChild(root);
    return { root, intent, sprite, body, name, barFill, barNum, chips };
  });
  stage.appendChild(foesWrap);

  const bar = el("div");
  bar.id = "playerbar";
  const log = el("div", "barlog");
  const main = el("div", "barmain");
  const orb = el("div", "orb");
  const pcol = el("div");
  const pname = el("div", "pname");
  const hpwrap = el("div", "hpwrap");
  hpwrap.style.cssText = "width:230px;margin-top:5px";
  const hpFill = el("i", "hpfill");
  const hpText = el("span", "hptext");
  hpwrap.append(hpFill, hpText);
  pcol.append(pname, hpwrap);
  main.append(orb, pcol);

  const right = el("div", "barright");
  const piles = el("div", "piles");
  const endturn = el("button");
  endturn.id = "endturn";
  right.append(piles, endturn);

  bar.append(log, main, right);
  stage.appendChild(bar);

  const hand = el("div");
  hand.id = "hand";
  stage.appendChild(hand);

  scene = {
    stage, head, foes, bar, log, orb, pname, hpFill, hpText,
    piles, endturn, hand, cards: new Map(),
  };
  updateCombat();
}

/* ── update ────────────────────────────────────────────────── */

/**
 * Reconcile the mounted scene against a snapshot.
 *
 * Defaults to the live state, but the director passes the *previous* snapshot
 * first so the timeline starts from what the player was looking at rather than
 * from the outcome.
 */
export function updateCombat(state: State = S()) {
  if (!scene) return;
  const cb = state.combat;
  if (!cb) return;
  const p = state.player;
  const s = sel();

  scene.head.innerHTML = `${esc(cb.label)} &nbsp;·&nbsp; turn ${cb.turn}`;

  cb.enemies.forEach((e, i) => {
    const n = scene!.foes[i];
    if (n) updateFoe(n, e, i, Boolean(s && s.mode === "target" && e.alive));
  });

  scene.log.innerHTML = cb.log.slice(-3).map((l) => `<div>${esc(l)}</div>`).join("");
  scene.orb.innerHTML =
    `${p.energy}<span style="font-size:12px;opacity:.6">/${p.max_energy}</span>`;
  scene.pname.innerHTML = esc(p.name)
    + (p.block ? `<span class="block-badge">🛡 ${p.block}</span>` : "");
  scene.hpFill.style.width = Math.max(0, p.hp) / p.max_hp * 100 + "%";
  scene.hpText.textContent = `${p.hp} / ${p.max_hp}`;
  scene.piles.innerHTML =
    `<button data-act="pile" data-pile="draw_pile">draw ${cb.draw}</button>`
    + `<button data-act="pile" data-pile="discard_pile">discard ${cb.discard}</button>`
    + `<button data-act="pile" data-pile="exhaust_pile">exhaust ${cb.exhaust}</button>`;

  scene.endturn.className = s ? "cancel" : "";
  scene.endturn.innerHTML = s ? "Cancel <kbd>Esc</kbd>" : "End turn <kbd>E</kbd>";
  scene.endturn.onclick = s
    ? () => { setSel(null); updateCombat(); }
    : () => void send({ type: "end_turn" });

  syncHand(cb.hand, s);
}

function updateFoe(n: FoeNodes, e: EnemyView, i: number, targetable: boolean) {
  n.root.classList.toggle("dead", !e.alive);
  n.root.classList.toggle("targetable", targetable);

  if (e.alive && e.intent) {
    n.intent.className = "intent " + e.intent.kind;
    n.intent.innerHTML = intentHtml(e.intent);
    n.intent.setAttribute("data-tip", e.intent.name);
    n.intent.setAttribute("data-tip-desc",
      e.intent.note || KIND_TIP[e.intent.kind] || "");
    n.intent.hidden = false;
  } else if (!e.alive) {
    n.intent.className = "intent";
    n.intent.textContent = "slain";
    n.intent.removeAttribute("data-tip");
    n.intent.hidden = false;
  } else {
    n.intent.hidden = true;
  }

  if (n.sprite.dataset.key !== e.key) {
    n.sprite.dataset.key = e.key;
    n.sprite.innerHTML = art.creature(e.key);
  }

  n.name.innerHTML =
    (e.alive ? `<span style="color:var(--gold)">${LETTERS[i]}</span> · ` : "")
    + esc(e.name)
    + (e.block ? `<span class="block-badge">🛡 ${e.block}</span>` : "");
  n.barFill.style.width = Math.max(0, e.hp) / e.max_hp * 100 + "%";
  n.barNum.textContent = `${Math.max(0, e.hp)} / ${e.max_hp}`;
  n.chips.innerHTML = e.statuses.map(statusChip).join("");

  const hp = `${Math.max(0, e.hp)} of ${e.max_hp} hit points`;
  n.root.setAttribute("aria-label", `${e.name}, ${hp}`
    + (e.intent
      ? `, intent ${e.intent.kind}`
        + (e.intent.kind === "attack" ? ` ${e.intent.dmg} damage` : "")
      : ""));
}

/** Keep hand DOM keyed by uid, so a card that stays in hand keeps its node —
 *  and its position — across an update. */
function syncHand(hand: CardView[], s: ReturnType<typeof sel>) {
  if (!scene) return;
  const wanted = new Set(hand.map((c) => c.uid));
  for (const [uid, node] of scene.cards) {
    if (!wanted.has(uid)) { node.remove(); scene.cards.delete(uid); }
  }
  hand.forEach((c, i) => {
    let node = scene!.cards.get(c.uid);
    const opts = {
      combat: true,
      kbd: (i + 1) % 10,
      selected: Boolean(s && s.kind === "card" && s.idx === i),
      pick: Boolean(s && s.mode === "hand" && i !== s.idx),
      onclick: () => clickCard(i),
    };
    if (!node) {
      node = cardEl(c, opts);
      scene!.cards.set(c.uid, node);
    } else {
      // Cheap enough to rebuild the face; the *node* is what has to persist.
      const fresh = cardEl(c, opts);
      node.className = fresh.className;
      node.innerHTML = fresh.innerHTML;
      node.onclick = opts.onclick;
      node.setAttribute("aria-label", fresh.getAttribute("aria-label")!);
    }
    if (scene!.hand.children[i] !== node) {
      scene!.hand.insertBefore(node, scene!.hand.children[i] ?? null);
    }
  });
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
    updateCombat();
    return;
  }
  const target = c.targeted ? alive[0]! : null;
  if (c.needs_hand && cb.hand.length > 1) {
    setSel({ kind: "card", idx: i, mode: "hand", target });
    updateCombat();
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
    updateCombat();
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
    updateCombat();
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

/** Kept so the tooltip helper can still build intent attributes. */
export const intentTip = (it: IntentView) =>
  tipAttrs(it.name, it.note || KIND_TIP[it.kind] || "");
