/**
 * Visual feedback for what just changed.
 *
 * Phase 0 keeps the original approach — diff the previous snapshot against the
 * current one and pop a number. Phase 1 adds `combat.fx`, an ordered event
 * list from the engine, and this becomes a real timeline that can stage a
 * multi-enemy turn instead of collapsing it into one instant.
 */

import { $, el } from "./dom";
import { foeNode } from "./screens/combat";
import { pendingFx, prev, S, setPendingFx } from "./store";

export function floaters() {
  // Only the render that follows a server response animates; selecting or
  // cancelling a card re-renders against the same prev/S pair and must not
  // replay.
  if (!pendingFx) return;
  setPendingFx(false);

  const before = prev();
  const now = S();
  if (!before?.combat || !now.combat) return;

  const stage = $("#stage");

  const pop = (node: HTMLElement, text: string, cls: string) => {
    const r = node.getBoundingClientRect();
    const s = stage.getBoundingClientRect();
    const f = el("div", "float " + cls, text);
    f.style.left = (r.left - s.left + r.width / 2 - 12) + "px";
    f.style.top = (r.top - s.top + 10) + "px";
    stage.appendChild(f);
    setTimeout(() => f.remove(), 1000);
  };

  now.combat.enemies.forEach((e, i) => {
    const was = before.combat!.enemies[i];
    if (!was) return;
    const d = Math.max(0, was.hp) - Math.max(0, e.hp);
    const node = foeNode(i);
    if (d > 0 && node) pop(node, `-${d}`, "dmg");
  });

  const bar = document.querySelector<HTMLElement>("#playerbar");
  if (!bar) return;

  const dp = before.player.hp - now.player.hp;
  if (dp > 0) {
    pop(bar, `-${dp}`, "dmg");
    bar.classList.add("shake");
    setTimeout(() => bar.classList.remove("shake"), 320);
  }
  if (dp < 0) pop(bar, `+${-dp}`, "heal");

  const db = now.player.block - before.player.block;
  if (db > 0) pop(bar, `+${db} 🛡`, "blk");
}
