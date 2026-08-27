/**
 * Drag a card onto an enemy to play it.
 *
 * Purely additive: every key binding still works, and a plain click still
 * plays a card the way it always did. A drag only starts once the pointer has
 * moved past a threshold, so a click that wobbles by a pixel is still a click.
 *
 * The arc drawn while dragging is the same affordance the keyboard gets from
 * the "targetable" outline — it says what will be hit if you let go now.
 */

import { send } from "./actions";
import { isPlaying } from "./director";
import { $ } from "./dom";
import { isBusy, isOffline } from "./net";
import { combatScene, updateCombat } from "./screens/combat";
import { S, sel, setSel } from "./store";

const THRESHOLD = 6;   // px before a click becomes a drag

interface Drag {
  idx: number;
  card: HTMLElement;
  slot: HTMLElement;
  startX: number;
  startY: number;
  active: boolean;
  hover: number | null;
}

let drag: Drag | null = null;
let arc: SVGSVGElement | null = null;

export function wireDrag() {
  document.addEventListener("pointerdown", onDown);
  document.addEventListener("pointermove", onMove);
  document.addEventListener("pointerup", onUp);
  document.addEventListener("pointercancel", cancel);
  // While a card-drag is pending or live, stop the browser selecting the
  // card's name and rules text under the pointer. Scoped to `drag`, so it
  // never interferes with selecting text anywhere else, and — unlike
  // preventDefault on pointerdown — it cannot suppress the click that plays a
  // card when the pointer barely moves.
  document.addEventListener("selectstart", (ev) => {
    if (drag) ev.preventDefault();
  });
}

function onDown(ev: PointerEvent) {
  if (ev.button !== 0) return;
  if (isBusy() || isOffline() || isPlaying()) return;
  const state = S();
  if (state.screen !== "combat" || sel()) return;

  const card = (ev.target as Element | null)?.closest<HTMLElement>("#hand .card");
  const slot = card?.parentElement;
  if (!card || !slot) return;
  const idx = Number(card.dataset.idx);
  const c = state.combat?.hand[idx];
  if (!c?.playable) return;

  drag = { idx, card, slot, startX: ev.clientX, startY: ev.clientY, active: false, hover: null };
}

function onMove(ev: PointerEvent) {
  if (!drag) return;
  const dx = ev.clientX - drag.startX;
  const dy = ev.clientY - drag.startY;
  if (!drag.active) {
    if (Math.hypot(dx, dy) < THRESHOLD) return;
    begin();
  }
  // The card stays lifted in the hand rather than following the pointer: a
  // card carried under the cursor sits on top of the enemy you are aiming at
  // and hides it. The arc does the pointing. It does lean toward the pointer,
  // so the drag still feels attached to the hand.
  const lean = Math.max(-14, Math.min(14, dx * 0.05));
  drag.card.style.transform =
    `translateY(-38px) rotate(${lean.toFixed(1)}deg) scale(1.04)`;

  const targeted = S().combat?.hand[drag.idx]?.targeted ?? false;
  const foe = foeUnder(ev.clientX, ev.clientY);
  drag.hover = targeted ? foe : null;
  paintTargets(drag.hover, targeted);
  drawArc(ev.clientX, ev.clientY, targeted);
}

function begin() {
  if (!drag) return;
  drag.active = true;
  document.body.classList.add("dragging");
  drag.slot.classList.add("held");
  drag.card.style.transition = "none";
}

function onUp(ev: PointerEvent) {
  if (!drag) return;
  const d = drag;
  if (!d.active) { drag = null; return; }   // it was a click; let click handle it

  const state = S();
  const c = state.combat?.hand[d.idx];
  const dropped = c?.targeted ? foeUnder(ev.clientX, ev.clientY) : releasedOnField(ev);
  finish();

  if (c && dropped !== null && dropped !== undefined) {
    if (c.needs_hand && state.combat!.hand.length > 1) {
      // Still needs a second choice; fall back to the existing picker.
      setSel({ kind: "card", idx: d.idx, mode: "hand",
               target: c.targeted ? (dropped as number) : null });
      updateCombat();
      return;
    }
    void send({
      type: "play", idx: d.idx,
      target: c.targeted ? (dropped as number) : null, exhaust: null,
    });
  } else {
    updateCombat();     // snap the card home
  }
}

function cancel() {
  if (!drag) return;
  finish();
  updateCombat();
}

function finish() {
  if (drag) {
    drag.card.style.transition = "";
    drag.card.style.transform = "";
    drag.slot.classList.remove("held");
  }
  document.body.classList.remove("dragging");
  paintTargets(null, false);
  clearArc();
  drag = null;
}

/** An untargeted card just has to be let go somewhere over the play area. */
function releasedOnField(ev: PointerEvent): number | null {
  const scene = combatScene();
  if (!scene) return null;
  const r = scene.stage.getBoundingClientRect();
  const hand = scene.hand.getBoundingClientRect();
  const inStage = ev.clientY > r.top && ev.clientY < hand.top;
  return inStage ? 0 : null;
}

function foeUnder(x: number, y: number): number | null {
  const scene = combatScene();
  if (!scene) return null;
  for (const [i, foe] of scene.foes.entries()) {
    if (!S().combat?.enemies[i]?.alive) continue;
    const r = foe.root.getBoundingClientRect();
    // A generous box: dropping near a creature should hit it.
    if (x >= r.left - 12 && x <= r.right + 12 && y >= r.top - 30 && y <= r.bottom + 12) {
      return i;
    }
  }
  return null;
}

function paintTargets(hover: number | null, targeted: boolean) {
  const scene = combatScene();
  if (!scene) return;
  scene.foes.forEach((foe, i) => {
    foe.root.classList.toggle("targetable", targeted && drag !== null
      && Boolean(S().combat?.enemies[i]?.alive));
    foe.root.classList.toggle("droptarget", hover === i);
  });
}

/* ── the drawn arc ─────────────────────────────────────────── */

function drawArc(x: number, y: number, targeted: boolean) {
  const scene = combatScene();
  if (!scene || !drag) return;
  if (!arc) {
    arc = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    arc.setAttribute("id", "dragarc");
    arc.setAttribute("aria-hidden", "true");
    arc.innerHTML = `<path fill="none" stroke-width="3" stroke-linecap="round"/>`;
    $("#stage").appendChild(arc);
  }
  const stage = $("#stage").getBoundingClientRect();
  const from = drag.slot.getBoundingClientRect();
  const x0 = from.left + from.width / 2 - stage.left;
  const y0 = from.top - stage.top;
  const x1 = x - stage.left;
  const y1 = y - stage.top;
  // Bow the line upward so it arcs over the board rather than cutting through.
  const cx = (x0 + x1) / 2;
  const cy = Math.min(y0, y1) - 70;
  const path = arc.firstElementChild as SVGPathElement;
  path.setAttribute("d", `M${x0} ${y0} Q${cx} ${cy} ${x1} ${y1}`);
  path.setAttribute("stroke", !targeted || drag.hover !== null ? "#e0b978" : "#6b5f92");
  arc.classList.toggle("live", !targeted || drag.hover !== null);
}

function clearArc() {
  arc?.remove();
  arc = null;
}
