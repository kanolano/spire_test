import { send } from "../actions";
import { campfireScene } from "../art/scenes";
import { el, staggerIn } from "../dom";
import { S } from "../store";
import type { Action } from "../types";

export function renderRest(st: HTMLElement) {
  const p = S().player;
  const full = p.hp >= p.max_hp;
  st.appendChild(el("h2", "title", "A campfire"));
  st.appendChild(el("div", "scenewrap", campfireScene()));
  st.appendChild(el("div", "sub", "The embers are warm. You have time for one thing."));
  const heal = Math.min(p.max_hp - p.hp, Math.max(1, Math.floor(p.max_hp * 0.3)));
  const box = el("div", "choices");

  const opt = (
    kbd: number, label: string, note: string, action: Action, disabled?: boolean,
  ) => {
    const b = el("button", "choice",
      `<span class="k">${kbd}</span> <b>${label}</b> — ${note}`);
    // Rest was offered as a live option at full HP, healing nothing.
    if (disabled) { b.disabled = true; b.classList.add("spent"); }
    else b.onclick = () => void send(action);
    box.appendChild(b);
  };

  opt(1, "Rest", full
    ? `you are already at ${p.hp}/${p.max_hp}`
    : `heal ${heal} HP <span class="ghost">(you are at ${p.hp}/${p.max_hp})</span>`,
    { type: "rest" }, full);
  opt(2, "Smith", "upgrade a card", { type: "smith" });
  opt(3, "Purge", "remove a card from your deck", { type: "purge" });
  staggerIn(box.children);
  st.appendChild(box);
}

export function restKeys(k: string) {
  const p = S().player;
  if (k === "1" && p.hp < p.max_hp) void send({ type: "rest" });
  if (k === "2") void send({ type: "smith" });
  if (k === "3") void send({ type: "purge" });
}
