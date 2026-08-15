/**
 * Plays the engine's effect stream as a timeline.
 *
 * The rule that keeps this honest: **the server snapshot is authoritative and
 * the timeline is only a way of arriving at it.** Every run ends by
 * reconciling the scene against the real state, so a dropped beat, an
 * unhandled event kind or a mid-flight error can never leave the display
 * disagreeing with the engine — it can only make the journey less pretty.
 *
 * Reduced motion is the same code path with every duration at zero, rather
 * than a second rendering path that could drift.
 */

import { gsap } from "gsap";

import { sfx } from "./audio";

import { $, el } from "./dom";
import { setBusy } from "./net";
import { motes, sparks } from "./particles";
import { combatScene, updateCombat } from "./screens/combat";
import type { FxEvent, State, Who } from "./types";

/** An enemy turn must land in about this long however many enemies act, so a
 *  five-enemy board compresses instead of queueing up seven seconds. */
const TURN_BUDGET = 1.6;

const BEAT = {
  play: 0.26,
  swing: 0.22,
  damage: 0.20,
  block: 0.16,
  status: 0.14,
  death: 0.55,
  draw: 0.05,
  gap: 0.10,
} as const;

export const reducedMotion = () =>
  window.matchMedia("(prefers-reduced-motion: reduce)").matches
  || new URLSearchParams(location.search).get("motion") === "off";

let current: gsap.core.Timeline | null = null;

export const isPlaying = () => Boolean(current);

/** Any click or keypress jumps to the end. Nobody should have to sit through
 *  a five-enemy turn twice. */
export function skip() {
  if (current) current.progress(1);
}

/**
 * Animate from `before` to `after`, then reconcile.
 * Resolves once the scene matches `after`.
 */
export function play(before: State | null, after: State, fx: FxEvent[]): void {
  current?.progress(1);            // never overlap two turns
  current = null;

  const scene = combatScene();
  const usable = scene && before?.combat && after.combat && fx.length;
  if (!usable || reducedMotion()) {
    updateCombat(after);
    return;
  }

  // Start from what the player was looking at, not from the outcome.
  updateCombat(before!);

  const scale = pacing(fx);
  const tl = gsap.timeline({
    onComplete: () => { current = null; setBusy(false); updateCombat(after); },
  });
  current = tl;
  setBusy(true);

  for (const ev of fx) beat(tl, ev, after, scale);

  // An empty timeline never fires onComplete, and a stream of only log lines
  // is a real possibility.
  if (tl.getChildren().length === 0) {
    tl.kill();
    current = null;
    setBusy(false);
    updateCombat(after);
  }
}

/** Squeeze the per-beat durations so a busy turn still fits the budget. */
function pacing(fx: FxEvent[]): number {
  let cost = 0;
  for (const ev of fx) {
    cost += (BEAT as Record<string, number>)[ev.k] ?? 0;
  }
  return cost > TURN_BUDGET ? TURN_BUDGET / cost : 1;
}

/* ── the beats ─────────────────────────────────────────────── */

function beat(tl: gsap.core.Timeline, ev: FxEvent, after: State, scale: number) {
  const scene = combatScene();
  if (!scene) return;
  const d = (base: number) => base * scale;

  switch (ev.k) {
    case "log":
      tl.call(() => pushLog(ev.text));
      break;

    case "play": {
      // The played card is still in the hand we rendered from `before`, at the
      // index the engine reports, so it can be flown out of it.
      const card = scene.hand.children[ev.idx] as HTMLElement | undefined;
      if (!card) break;
      card.style.zIndex = "90";     // over its neighbours while it travels
      // An untargeted card (a Defend, a Power) resolves on the player.
      const target = ev.target == null ? scene.hero : scene.foes[ev.target]?.root;
      const from = card.getBoundingClientRect();
      const to = (target ?? scene.hero).getBoundingClientRect();
      tl.call(() => { sfx.card(); if (ev.cost > 0) { pulseOrb(); sfx.spend(); } });
      tl.to(card, {
        duration: d(BEAT.play) * 0.4, y: -34, scale: 1.06, ease: "power2.out",
      }).to(card, {
        duration: d(BEAT.play) * 0.6,
        x: to.left + to.width / 2 - (from.left + from.width / 2),
        y: to.top + to.height / 2 - (from.top + from.height / 2),
        scale: 0.35, opacity: 0, rotate: 8, ease: "power2.in",
      }).call(() => card.remove());
      break;
    }

    case "act": {
      const foe = scene.foes[ev.who];
      if (!foe) break;
      tl.to(foe.root, {
        duration: d(BEAT.gap), scale: 1.04, ease: "power2.out",
      }).to(foe.root, { duration: d(BEAT.gap), scale: 1 });
      break;
    }

    case "swing": {
      const from = node(ev.src);
      const to = node(ev.dst);
      if (!from) break;
      // Lunge a short way toward the target and snap back. The wind-up pulls
      // *away* first, which is what makes the strike read as a strike.
      const dx = to ? Math.sign(centre(to) - centre(from)) * 26 : 0;
      const dy = to ? 0 : -14;
      tl.to(from, {
        duration: d(BEAT.swing) * 0.35, x: dx * -0.35, y: dy * 0.4,
        ease: "power2.in",
      }).to(from, {
        duration: d(BEAT.swing) * 0.25, x: dx, y: dy, ease: "power4.out",
      }).to(from, {
        duration: d(BEAT.swing) * 0.4, x: 0, y: 0, ease: "power2.out",
      });
      // Rigged parts, if this creature has them. The director never needs to
      // know which creature it is holding.
      rig(from, ".rig-jaw", tl, d(BEAT.swing), { rotate: 12, y: 3 });
      rig(from, ".rig-wing", tl, d(BEAT.swing), { scaleY: 0.7 });
      break;
    }

    case "damage": {
      const target = hitTarget(ev.who);
      if (!target) break;
      const shown = ev.amount > 0 ? `-${ev.amount}` : `${ev.blocked} blocked`;
      tl.call(() => {
        float(target.box, shown, ev.amount > 0 ? "dmg" : "blk");
        setHp(ev.who, ev.hp, after);
        setBlock(ev.who, ev.block, after);
        if (ev.amount > 0) {
          const max = ev.who === "player"
            ? after.player.max_hp : (after.combat?.enemies[ev.who]?.max_hp ?? 30);
          const power = Math.min(1.6, 0.6 + (ev.amount / max) * 3);
          sfx.hit(power);
          sparks(target.body, power);
        } else {
          sfx.blocked();
          sparks(target.body, 0.4, true);
        }
      });
      tl.to(target.body, {
        duration: d(BEAT.damage) * 0.3,
        x: "+=9", filter: "brightness(2.4)", ease: "power3.out",
      }).to(target.body, {
        duration: d(BEAT.damage) * 0.7,
        x: "-=9", filter: "brightness(1)", ease: "elastic.out(1, 0.45)",
      });
      if (ev.amount > 0) rig(target.body, ".rig-eye", tl, d(BEAT.damage), { scale: 1.5 });
      // Block that absorbed a blow and then ran out is worth showing breaking,
      // not silently disappearing.
      if (ev.blocked > 0 && ev.block === 0) {
        const badge = target.box.querySelector(".block-badge");
        if (badge) {
          tl.to(badge, {
            duration: d(BEAT.block), scale: 1.3, opacity: 0, rotate: -12,
            ease: "power2.in",
          }, "<");
        }
      }
      if (ev.who === "player" && ev.amount > 0) {
        const hurt = ev.amount / Math.max(1, after.player.max_hp);
        tl.to($("#stage"), {
          duration: d(0.16), x: 0,
          keyframes: [
            { x: -8 * Math.min(2, 1 + hurt * 6) },
            { x: 6 * Math.min(2, 1 + hurt * 6) },
            { x: 0 },
          ],
        }, "<");
      }
      break;
    }

    case "lose_hp":
    case "heal": {
      const target = hitTarget(ev.who);
      if (!target) break;
      const heal = ev.k === "heal";
      tl.call(() => {
        float(target.box, `${heal ? "+" : "-"}${ev.amount}`, heal ? "heal" : "dmg");
        setHp(ev.who, ev.hp, after);
        if (heal) sfx.heal(); else sfx.hit(0.7);
      });
      tl.to(target.body, {
        duration: d(BEAT.status), filter: heal ? "brightness(1.5)" : "brightness(0.7)",
        yoyo: true, repeat: 1,
      });
      break;
    }

    case "block": {
      const target = hitTarget(ev.who);
      if (!target) break;
      tl.call(() => {
        float(target.box, `+${ev.amount} 🛡`, "blk");
        setBlock(ev.who, ev.total, after);
        sfx.guard();
      });
      tl.to(target.box, {
        duration: d(BEAT.block), scale: 1.03, yoyo: true, repeat: 1,
        ease: "power2.out",
      });
      break;
    }

    case "status": {
      const target = hitTarget(ev.who);
      if (!target) break;
      tl.call(() => sfx.hex());
      tl.to(target.body, {
        duration: d(BEAT.status), scale: 1.06, yoyo: true, repeat: 1,
        ease: "power2.out",
      });
      break;
    }

    case "death": {
      const foe = combatScene()?.foes[ev.who];
      if (!foe) break;
      tl.call(() => { setHp(ev.who, 0, after); sfx.death(); motes(foe.body); });
      tl.to(foe.body, {
        duration: d(BEAT.death) * 0.25, scale: 1.12,
        filter: "brightness(3)", ease: "power2.out",
      }).to(foe.body, {
        duration: d(BEAT.death) * 0.75, scale: 0.82, opacity: 0,
        y: 14, filter: "brightness(0.2)", ease: "power2.in",
      }).call(() => { foe.root.classList.add("dead"); })
        .to(foe.body, { duration: d(0.2), opacity: 1, scale: 1, y: 0, filter: "none" });
      break;
    }

    case "draw":
      // The hand itself is reconciled at the end; this only paces the deal.
      tl.call(() => sfx.deal(0));
      tl.to({}, { duration: d(BEAT.draw) });
      break;

    case "turn":
      tl.to({}, { duration: d(BEAT.gap) });
      break;

    default:
      break;
  }
}

/* ── helpers ───────────────────────────────────────────────── */

/** The element that moves when a combatant swings or is hit. */
function node(who: Who): HTMLElement | null {
  const scene = combatScene();
  if (!scene) return null;
  return who === "player" ? scene.heroBody : (scene.foes[who]?.body ?? null);
}

function hitTarget(who: Who): { body: HTMLElement; box: HTMLElement } | null {
  const scene = combatScene();
  if (!scene) return null;
  if (who === "player") return { body: scene.heroBody, box: scene.hero };
  const foe = scene.foes[who];
  return foe ? { body: foe.body, box: foe.root } : null;
}

const centre = (n: HTMLElement) => {
  const r = n.getBoundingClientRect();
  return r.left + r.width / 2;
};

/**
 * Animate a rigged part of whatever sprite is in `host`, if it has one.
 *
 * Creatures are composed from a shared kit, so a jaw is always `.rig-jaw` and
 * eyes are always `.rig-eye`. That is the whole point of the rig: the director
 * asks for "the jaw" and gets it on the creatures that have one, and nothing
 * on the ones that do not.
 */
function rig(
  host: HTMLElement, part: string, tl: gsap.core.Timeline,
  duration: number, to: gsap.TweenVars,
) {
  const nodes = host.querySelectorAll(part);
  if (!nodes.length) return;
  tl.to(nodes, {
    duration: duration * 0.4, ...to,
    transformOrigin: "50% 50%", ease: "power2.out",
  }, "<").to(nodes, {
    duration: duration * 0.6, rotate: 0, y: 0, scale: 1, scaleY: 1,
    ease: "power2.inOut",
  });
}

/** Patch one combatant's HP mid-timeline. The event carries the absolute
 *  value, so this never has to reason about deltas. */
function setHp(who: Who, hp: number, after: State) {
  const scene = combatScene();
  if (!scene) return;
  if (who === "player") {
    const max = after.player.max_hp;
    scene.hpFill.style.width = Math.max(0, hp) / max * 100 + "%";
    scene.hpText.textContent = `${Math.max(0, hp)} / ${max}`;
    return;
  }
  const foe = scene.foes[who];
  const max = after.combat?.enemies[who]?.max_hp;
  if (!foe || !max) return;
  foe.barFill.style.width = Math.max(0, hp) / max * 100 + "%";
  foe.barNum.textContent = `${Math.max(0, hp)} / ${max}`;
}

function setBlock(who: Who, block: number, after: State) {
  const scene = combatScene();
  if (!scene) return;
  const badge = block ? `<span class="block-badge">🛡 ${block}</span>` : "";
  if (who === "player") {
    scene.pname.innerHTML = escapeName(after.player.name) + badge;
    return;
  }
  const foe = scene.foes[who];
  const e = after.combat?.enemies[who];
  if (!foe || !e) return;
  foe.name.innerHTML =
    (e.alive ? `<span style="color:var(--gold)">${"abcdefgh"[who]}</span> · ` : "")
    + escapeName(e.name) + badge;
}

const escapeName = (s: string) =>
  s.replace(/[<>&"']/g, (m) => (
    { "<": "&lt;", ">": "&gt;", "&": "&amp;", '"': "&quot;", "'": "&#39;" }[m]!));

/** The orb is where energy is spent, so spending should be visible there. */
function pulseOrb() {
  const orb = combatScene()?.orb;
  if (!orb) return;
  gsap.fromTo(orb,
    { scale: 1.14, filter: "brightness(1.7)" },
    { duration: 0.32, scale: 1, filter: "brightness(1)", ease: "power2.out" });
}

function pushLog(text: string) {
  const scene = combatScene();
  if (!scene) return;
  scene.log.appendChild(el("div", undefined, escapeName(text)));
  while (scene.log.children.length > 3) scene.log.firstElementChild!.remove();
}

function float(anchor: HTMLElement, text: string, cls: string) {
  const stage = $("#stage");
  const r = anchor.getBoundingClientRect();
  const s = stage.getBoundingClientRect();
  const f = el("div", "float " + cls, escapeName(text));
  f.style.left = (r.left - s.left + r.width / 2 - 12) + "px";
  f.style.top = (r.top - s.top + 10) + "px";
  stage.appendChild(f);
  setTimeout(() => f.remove(), 1000);
}
