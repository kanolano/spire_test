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
import { heroSvg } from "../art/heroes";
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

/** A hand card: the slot holds its place in the fan, the card is the face. */
export interface HeldCard { slot: HTMLElement; card: HTMLElement }

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
  cards: Map<number, HeldCard>;
  /** The player's body on the field — what the director lunges and shakes. */
  hero: HTMLElement;
  heroBody: HTMLElement;
  heroPlate: HTMLElement;
  heroChips: HTMLElement;
}

let scene: Scene | null = null;

export const combatScene = () => scene;
export const foeNode = (i: number) => scene?.foes[i]?.root ?? null;
export const cardNode = (uid: number) => scene?.cards.get(uid)?.card ?? null;

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

  // The player used to be a status bar being attacked by a row of monsters.
  // Putting a body on the field opposite them is what makes a swing legible as
  // one thing hitting another.
  const field = el("div");
  field.id = "field";
  const hero = el("div", "hero-side");
  const heroBody = el("div", "foe-body");
  const heroPose = el("div", "foe-pose");
  const heroSprite = el("div", "sprite");
  heroSprite.innerHTML = heroSvg(state.player.cls);
  heroPose.appendChild(heroSprite);
  heroBody.appendChild(heroPose);
  const heroPlate = el("div", "hero-plate");
  const heroChips = el("div", "chips foe-chips");
  hero.append(heroBody, el("div", "shadow"), heroPlate, heroChips);
  field.appendChild(hero);

  const foesWrap = el("div");
  foesWrap.id = "enemies";
  const foes: FoeNodes[] = cb.enemies.map((_e, i) => {
    const root = el("div", "foe");
    root.dataset.foe = String(i);
    const intent = el("div", "intent");
    // Three layers, because three things move the sprite and a CSS animation
    // beats a plain declaration while an inline style beats both:
    //   .foe-body  directed motion — the director tweens this inline
    //   .foe-pose  the intent telegraph, plain CSS
    //   .sprite    the idle bob, a running keyframe animation
    const body = el("div", "foe-body");
    const pose = el("div", "foe-pose");
    const sprite = el("div", "sprite");
    pose.appendChild(sprite);
    body.appendChild(pose);
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
  field.appendChild(foesWrap);
  stage.appendChild(field);

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
    hero, heroBody, heroPlate, heroChips,
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

  // The player's own block and statuses belong next to the player's body, not
  // buried in the stats bar.
  scene.heroPlate.innerHTML = p.block
    ? `<span class="block-badge">🛡 ${p.block}</span>` : "";
  scene.heroChips.innerHTML = p.statuses.map(statusChip).join("");
  scene.hero.dataset.low = String(p.hp / p.max_hp < 0.35);

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

  // Only redraw the sprite when it is genuinely a different creature —
  // replacing the SVG would throw away whatever the director is mid-tween on.
  if (n.sprite.dataset.key !== e.key) {
    n.sprite.dataset.key = e.key;
    n.sprite.innerHTML = art.creature(e.key);
  }
  // Posture keyed to what it is about to do: attacks coil forward, blocks
  // hunker down, buffs swell. The CSS owns what each one looks like.
  n.root.dataset.telegraph = e.alive && e.intent ? e.intent.kind : "";

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

/**
 * Keep hand DOM keyed by uid, so a card that stays in hand keeps its node —
 * and its position — across an update.
 *
 * Each card lives in a slot. The slot carries the fan transform and the card
 * carries hover and selection, because one element cannot hold both: the
 * hover rule would overwrite the arc and cards would snap flat under the
 * cursor.
 */
function syncHand(hand: CardView[], s: ReturnType<typeof sel>) {
  if (!scene) return;
  const wanted = new Set(hand.map((c) => c.uid));
  for (const [uid, held] of scene.cards) {
    if (!wanted.has(uid)) { held.slot.remove(); scene.cards.delete(uid); }
  }
  hand.forEach((c, i) => {
    let held = scene!.cards.get(c.uid);
    const opts = {
      combat: true,
      kbd: (i + 1) % 10,
      selected: Boolean(s && s.kind === "card" && s.idx === i),
      pick: Boolean(s && s.mode === "hand" && i !== s.idx),
      onclick: () => clickCard(i),
    };
    if (!held) {
      const card = cardEl(c, opts);
      const slot = el("div", "slot");
      slot.appendChild(card);
      held = { slot, card };
      scene!.cards.set(c.uid, held);
    } else {
      // Cheap enough to rebuild the face; the *node* is what has to persist.
      const fresh = cardEl(c, opts);
      held.card.className = fresh.className;
      held.card.innerHTML = fresh.innerHTML;
      held.card.onclick = opts.onclick;
      held.card.setAttribute("aria-label", fresh.getAttribute("aria-label")!);
    }
    held.slot.dataset.idx = String(i);
    held.card.dataset.idx = String(i);
    if (scene!.hand.children[i] !== held.slot) {
      scene!.hand.insertBefore(held.slot, scene!.hand.children[i] ?? null);
    }
  });
  fanHand(hand.length);
}

/**
 * Lay the hand out as an arc rather than a flat row.
 *
 * Done in JS because it depends on how many cards there are: a hand of two
 * should be almost flat and a hand of nine should curve hard, which a static
 * stylesheet cannot express.
 */
function fanHand(n: number) {
  if (!scene) return;
  const mid = (n - 1) / 2;
  // Tighten the spread as the hand grows, or ten cards fan off the screen.
  const step = Math.min(4.2, 26 / Math.max(1, n));
  [...scene.cards.values()].forEach((held) => {
    const i = Number(held.slot.dataset.idx);
    const off = i - mid;
    const rot = off * step;
    const lift = Math.abs(off) ** 2 * (n > 3 ? 2.6 : 0);
    held.slot.style.transform = `rotate(${rot.toFixed(2)}deg) translateY(${lift.toFixed(1)}px)`;
    // Later cards overlap earlier ones, and a hovered card must win.
    held.slot.style.zIndex = String(10 + i);
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
