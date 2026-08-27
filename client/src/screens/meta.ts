/** Character select, and the two run-ending screens. */

import { abandon, send } from "../actions";
import { heroSvg } from "../art/heroes";
import { endingScene } from "../art/scenes";
import { ctaButton, el, esc, staggerIn } from "../dom";
import { getRecords } from "../net";
import { dailyMode, render, S, setDailyMode } from "../store";

export function renderSelect(st: HTMLElement) {
  st.appendChild(el("h1", "title big", "Choose your climber"));
  st.appendChild(el("div", "sub",
    "Each class brings its own deck, relic and card pool."));

  const row = el("div", "classes");
  (S().classes ?? []).forEach((c, i) => {
    const b = el("button", "cls");
    b.innerHTML =
      // You are choosing a body to climb in; it should be visible before the
      // stat block explains it.
      `<div class="cls-art">${heroSvg(c.key, 96)}</div>`
      + `<div class="cls-name"><span class="k">${i + 1}</span>${esc(c.name)}</div>`
      + `<div class="cls-stats">${c.hp} HP<span>${c.energy} energy</span>`
      + `<span>${c.cards} cards in pool</span></div>`
      + `<div class="cls-blurb">${esc(c.blurb)}</div>`
      + `<div class="cls-line"><b>${esc(c.relic.name)}</b> — ${esc(c.relic.desc)}</div>`
      + `<div class="cls-line">Starting deck: ${esc(c.deck.join(", "))}</div>`;
    b.onclick = () => void send({ type: "new_run", cls: c.key, daily: dailyMode });
    row.appendChild(b);
  });
  staggerIn(row.children, 0.08, 0.06);
  st.appendChild(row);

  const toggle = ctaButton(
    dailyMode
      ? "Daily climb: <b>on</b> — everyone gets the same Spire today"
      : "Daily climb: off — each run is freshly seeded",
    () => { setDailyMode(!dailyMode); render(); });
  toggle.setAttribute("aria-pressed", String(dailyMode));
  st.appendChild(toggle);
}

export function selectKeys(_k: string, num: number) {
  const cs = S().classes ?? [];
  const cls = cs[num];
  if (cls) void send({ type: "new_run", cls: cls.key, daily: dailyMode });
}

export function renderEnd(st: HTMLElement, won: boolean) {
  const s = S();
  st.appendChild(el("h1", "title big",
    won ? "You have ascended the Spire" : "You died"));
  st.appendChild(el("div", "scenewrap", endingScene(won)));
  if (!won) {
    st.appendChild(el("div", "sub",
      `Slain by ${esc(s.killer)} on floor ${s.floor} of act ${s.act}.`));
  }
  st.appendChild(el("div", "center",
    `${esc(s.player.name)} · Act ${s.act} · ${s.floors_cleared} combats won · `
    + `${s.elites_killed} elites slain · ${s.player.deck_size} cards · `
    + `${s.player.gold} gold`));

  const relics = el("div", "chips");
  relics.style.cssText = "justify-content:center;margin:18px 0";
  relics.innerHTML = s.player.relics
    .map((r) => `<span class="chip relic">${esc(r.name)}</span>`).join("");
  st.appendChild(relics);

  // This used to be one button sending new_run with no class, which quietly
  // restarted whatever DEFAULT_CLASS happens to be rather than what you played.
  const again = ctaButton(`Climb again as ${esc(s.player.name)} <kbd>Enter</kbd>`,
    () => void send({ type: "new_run", cls: s.player.cls }));
  again.style.cssText += ";padding:12px 28px;font-size:16px";
  st.appendChild(again);
  st.appendChild(ctaButton("Choose another class <kbd>C</kbd>", () => void abandon()));

  void getRecords().then((recs) => {
    if (!recs || !recs.length) return;
    const d = el("div", "center ghost");
    d.style.marginTop = "26px";
    d.innerHTML = "<b>Best runs</b><br>" + recs.slice(0, 5).map((r) =>
      `act ${r.act} · floor ${r.floors} · `
      + (r.won ? "<span style='color:var(--leaf)'>ascended</span>"
               : "died to " + esc(r.killer))).join("<br>");
    st.appendChild(d);
  }).catch(() => { /* the leaderboard is decoration; its absence is not an error */ });
}

export function endKeys(k: string) {
  if (k === "enter") void send({ type: "new_run", cls: S().player.cls });
  if (k === "c") void abandon();
}
