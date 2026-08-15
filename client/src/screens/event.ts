import { send } from "../actions";
import { chestScene, omenScene } from "../art/scenes";
import { ctaButton, el, esc, staggerIn } from "../dom";
import { S } from "../store";

export function renderEvent(st: HTMLElement) {
  const ev = S().event!;
  st.appendChild(el("h2", "title", esc(ev.title)));
  st.appendChild(el("div", "scenewrap", omenScene()));
  st.appendChild(el("div", "narrative", esc(ev.text)));
  if (ev.result === null) {
    const box = el("div", "choices");
    ev.options.forEach((o, i) => {
      // the label is flavour; the preview is what the choice actually costs
      const b = el("button", "choice",
        `<span class="k">${i + 1}</span> ${esc(o.label)}`
        + (o.preview ? `<span class="preview">${esc(o.preview)}</span>` : ""));
      b.onclick = () => void send({ type: "event_choose", idx: i });
      box.appendChild(b);
    });
    staggerIn(box.children);
    st.appendChild(box);
  } else {
    st.appendChild(el("div", "result", esc(ev.result)));
    st.appendChild(ctaButton("Continue <kbd>Enter</kbd>",
      () => void send({ type: "event_done" })));
  }
}

export function eventKeys(k: string, num: number) {
  const ev = S().event!;
  if (ev.result !== null) {
    if (k === "enter") void send({ type: "event_done" });
    return;
  }
  if (num >= 0 && num < ev.options.length) void send({ type: "event_choose", idx: num });
}

export function renderTreasure(st: HTMLElement) {
  const t = S().treasure!;
  st.appendChild(el("h2", "title", "A chest"));
  st.appendChild(el("div", "scenewrap", chestScene()));
  st.appendChild(el("div", "sub", `${t.gold} gold spills out.`));
  const item = el("div", "item",
    `<span class="nm">${esc(t.relic.name)}</span>`
    + `<span class="ds">${esc(t.relic.desc)}</span>`);
  staggerIn([item], 0, 0.2);
  st.appendChild(item);
  st.appendChild(ctaButton("Continue <kbd>Enter</kbd>",
    () => void send({ type: "treasure_done" })));
}

export function treasureKeys(k: string) {
  if (k === "enter") void send({ type: "treasure_done" });
}
