import { send } from "../actions";
import { el, LETTERS } from "../dom";
import { S } from "../store";
import type { NodeKind } from "../types";

export const NODE: Record<NodeKind, { g: string; c: string; t: string }> = {
  monster: { g: "⚔", c: "#c8503f", t: "Combat" },
  elite: { g: "☠", c: "#a874d4", t: "Elite" },
  event: { g: "?", c: "#4e9ec4", t: "Unknown" },
  rest: { g: "♨", c: "#6fbf73", t: "Campfire" },
  shop: { g: "$", c: "#e3b86a", t: "Merchant" },
  treasure: { g: "◈", c: "#e3b86a", t: "Treasure" },
  boss: { g: "♛", c: "#c8503f", t: "Boss" },
};

/* Unexplored edges used to be #332c47 at .6 opacity on a near-black
   background — you could not trace where a path went. Every edge now gets a
   dark casing underneath so it reads against the mottled backdrop, and the
   three states are separated by brightness and dash rather than by opacity. */
const EDGE = {
  done: { stroke: "#e6bd6c", width: 3, dash: "", glow: true },
  open: { stroke: "#c0a8f0", width: 2.8, dash: "8 5", glow: true },
  far: { stroke: "#6b5f92", width: 2, dash: "5 5", glow: false },
};

export function renderMap(st: HTMLElement) {
  const m = S().map;
  const W = 640, ROW = 58, H = m.floors.length * ROW + 36;
  const x = (f: number, i: number) => 26 + (i + 0.5) * (W - 40) / m.floors[f]!.length;
  const y = (f: number) => H - 28 - f * ROW;
  const isBoss = (f: number) => f === m.floors.length - 1;

  let svg = `<svg viewBox="0 0 ${W} ${H}" width="100%" height="${H}">
    <defs>
      <!-- userSpaceOnUse, because a percentage filter region is a percentage of
           the bounding box: a perfectly vertical edge has zero width, so its
           glow region collapsed and the line vanished entirely. -->
      <filter id="glow" filterUnits="userSpaceOnUse"
              x="0" y="0" width="${W}" height="${H}">
        <feGaussianBlur stdDeviation="3.4" result="b"/>
        <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
      </filter>
      <radialGradient id="ndisc" cx="35%" cy="28%">
        <stop offset="0" stop-color="#3a3052"/><stop offset="1" stop-color="#15111e"/>
      </radialGradient>
      <radialGradient id="ncur" cx="35%" cy="28%">
        <stop offset="0" stop-color="#7a63ad"/><stop offset="1" stop-color="#2a2140"/>
      </radialGradient>
      <radialGradient id="nseen" cx="35%" cy="28%">
        <stop offset="0" stop-color="#241f30"/><stop offset="1" stop-color="#120f19"/>
      </radialGradient>
    </defs>`;

  // floor ticks
  m.floors.forEach((_row, f) => {
    svg += `<text x="8" y="${y(f) + 4}" font-size="10" fill="#4a4260"
             font-family="Georgia,serif">${f + 1}</text>`;
  });

  for (let f = 0; f < m.floors.length - 1; f++) {
    m.floors[f]!.forEach((n, i) => n.edges.forEach((t) => {
      const done = m.visited.some((v) => v[0] === f && v[1] === i)
        && m.visited.some((v) => v[0] === f + 1 && v[1] === t);
      const open = f === m.cur_floor && i === m.cur_idx && m.reachable.includes(t);
      const e = EDGE[done ? "done" : (open ? "open" : "far")];
      const ends = `x1="${x(f, i)}" y1="${y(f)}" x2="${x(f + 1, t)}" y2="${y(f + 1)}"`;
      svg += `<line ${ends} stroke="#0b0812" stroke-width="${e.width + 2.5}"
                stroke-linecap="round" opacity=".85"/>`
        + `<line ${ends} stroke="${e.stroke}" stroke-width="${e.width}"
                stroke-linecap="round"
                ${e.dash ? `stroke-dasharray="${e.dash}"` : ""}
                ${e.glow ? 'filter="url(#glow)"' : ""}/>`;
    }));
  }

  m.floors.forEach((row, f) => row.forEach((n, i) => {
    const k = NODE[n.type];
    const cur = (f === m.cur_floor && i === m.cur_idx);
    const can = (f === m.cur_floor + 1) && m.reachable.includes(i);
    const seen = m.visited.some((v) => v[0] === f && v[1] === i);
    const r = isBoss(f) ? 23 : 17;
    const fill = cur ? "url(#ncur)" : (seen ? "url(#nseen)" : "url(#ndisc)");
    svg += `<g class="node${can ? " can" : ""}"${can ? ` data-node="${i}"` : ""}>`
      + `<title>${k.t}${can ? " — press " + LETTERS[i] : ""}</title>`
      + (can ? `<circle class="ring" cx="${x(f, i)}" cy="${y(f)}" r="${r + 4}" fill="none"
                    stroke="${k.c}" stroke-width="1.5" filter="url(#glow)" opacity=".6"/>` : "")
      + `<circle class="disc" cx="${x(f, i)}" cy="${y(f)}" r="${r}" fill="${fill}"
              stroke="${cur ? "#f3e2be" : (can ? "#e8c07a" : "#3a3250")}"
              stroke-width="${cur || can ? 2.2 : 1.3}"/>`
      + `<text x="${x(f, i)}" y="${y(f) + (isBoss(f) ? 7 : 6)}" text-anchor="middle"
              font-size="${isBoss(f) ? 22 : 17}" fill="${seen && !cur ? "#584f6e" : k.c}"
              opacity="${seen || can || cur ? 1 : .85}">${k.g}</text>`
      + (can ? `<text x="${x(f, i) + r + 7}" y="${y(f) + 5}" font-size="13" fill="#e8c07a"
                    font-family="Georgia,serif">${LETTERS[i]}</text>` : "")
      + `</g>`;
  }));
  svg += `</svg>`;

  st.appendChild(el("h2", "title", "Choose your path"));
  st.appendChild(el("div", "sub", m.cur_floor < 0
    ? "The Spire waits. Pick a starting route."
    : "Click a lit node, or press its letter."));

  const wrap = el("div");
  wrap.id = "mapwrap";
  wrap.innerHTML = svg;
  wrap.addEventListener("click", (ev) => {
    const g = (ev.target as Element | null)?.closest("g.node[data-node]");
    if (g) void send({ type: "map", idx: Number((g as HTMLElement).dataset.node) });
  });
  st.appendChild(wrap);

  st.appendChild(el("div", "legend", Object.values(NODE).map((v) =>
    `<span><span style="color:${v.c}">${v.g}</span>&nbsp;${v.t}</span>`).join("")));

  requestAnimationFrame(() => {
    const target = wrap.scrollHeight - (Math.max(0, m.cur_floor + 1) * ROW) - 280;
    wrap.scrollTop = Math.max(0, target);
  });
}

export function mapKeys(k: string) {
  const i = LETTERS.indexOf(k);
  if (i >= 0 && S().map.reachable.includes(i)) void send({ type: "map", idx: i });
}
