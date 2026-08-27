import { gsap } from "gsap";

import { send } from "../actions";
import { mapSky } from "../art/backdrop";
import { NODE_ART, NODE_KINDS, nodeBadge, nodeIcon } from "../art/nodes";
import { reducedMotion } from "../director";
import { el, LETTERS } from "../dom";
import { S } from "../store";

/* Unexplored edges used to be #332c47 at .6 opacity on a near-black
   background — you could not trace where a path went. Every edge now gets a
   dark casing underneath so it reads against the mottled backdrop, and the
   three states are separated by brightness and dash rather than by opacity. */
const EDGE = {
  done: { stroke: "#e6bd6c", width: 3, dash: "", glow: true },
  open: { stroke: "#c0a8f0", width: 2.8, dash: "8 5", glow: true },
  far: { stroke: "#6b5f92", width: 2, dash: "5 5", glow: false },
};

const ROW = 58;

/** Where things are on the last-rendered map, so travel can be animated
 *  without re-deriving the layout the SVG was built from. */
let geo: {
  svg: SVGSVGElement;
  x: (f: number, i: number) => number;
  y: (f: number) => number;
} | null = null;

let traveling = false;

export function renderMap(st: HTMLElement) {
  const m = S().map;
  const W = 640, H = m.floors.length * ROW + 36;
  const x = (f: number, i: number) => 26 + (i + 0.5) * (W - 40) / m.floors[f]!.length;
  const y = (f: number) => H - 28 - f * ROW;
  const isBoss = (f: number) => f === m.floors.length - 1;
  // The bottom of the map is the near future; reveal runs upward from where
  // the player is actually standing rather than from floor 1 every time.
  const delay = (f: number) => Math.min(0.5, Math.abs(f - Math.max(0, m.cur_floor)) * 0.045);

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
      const [x1, y1, x2, y2] = [x(f, i), y(f), x(f + 1, t), y(f + 1)];
      const ends = `x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}"`;
      // Paths draw themselves on from the near end. The dash pattern is the
      // animation's implicit end frame, so a dashed edge grows into its dashes
      // instead of snapping to them when the animation finishes.
      const len = Math.hypot(x2 - x1, y2 - y1).toFixed(1);
      const anim = `class="edge" style="--len:${len};animation-delay:${delay(f).toFixed(2)}s"`;
      svg += `<line ${ends} ${anim} stroke="#0b0812" stroke-width="${e.width + 2.5}"
                stroke-linecap="round" opacity=".85"
                stroke-dasharray="${len} 0"/>`
        + `<line ${ends} ${anim} stroke="${e.stroke}" stroke-width="${e.width}"
                stroke-linecap="round"
                stroke-dasharray="${e.dash || `${len} 0`}"
                ${e.glow ? 'filter="url(#glow)"' : ""}/>`;
    }));
  }

  m.floors.forEach((row, f) => row.forEach((n, i) => {
    const k = NODE_ART[n.type];
    const cur = (f === m.cur_floor && i === m.cur_idx);
    const can = (f === m.cur_floor + 1) && m.reachable.includes(i);
    const seen = m.visited.some((v) => v[0] === f && v[1] === i);
    const r = isBoss(f) ? 23 : 17;
    const fill = cur ? "url(#ncur)" : (seen ? "url(#nseen)" : "url(#ndisc)");
    svg += `<g class="node${can ? " can" : ""}${seen && !cur ? " seen" : ""}"`
      + `${can ? ` data-node="${i}"` : ""} style="animation-delay:${delay(f).toFixed(2)}s">`
      + `<title>${k.title}${can ? " — press " + LETTERS[i] : ""}</title>`
      + (can ? `<circle class="ring" cx="${x(f, i)}" cy="${y(f)}" r="${r + 4}" fill="none"
                    stroke="${k.color}" stroke-width="1.5" filter="url(#glow)" opacity=".6"/>` : "")
      + `<circle class="disc" cx="${x(f, i)}" cy="${y(f)}" r="${r}" fill="${fill}"
              stroke="${cur ? "#f3e2be" : (can ? "#e8c07a" : "#3a3250")}"
              stroke-width="${cur || can ? 2.2 : 1.3}"/>`
      + nodeIcon(n.type, x(f, i), y(f), isBoss(f) ? 1.25 : 0.92)
      + (can ? `<text x="${x(f, i) + r + 7}" y="${y(f) + 5}" font-size="13" fill="#e8c07a"
                    font-family="Georgia,serif">${LETTERS[i]}</text>` : "")
      + `</g>`;
  }));
  svg += `</svg>`;

  st.appendChild(el("h2", "title", "Choose your path"));
  st.appendChild(el("div", "sub", m.cur_floor < 0
    ? "The Spire waits. Pick a starting route."
    : "Click a lit node, or press its letter."));

  // The sky does not scroll with the node list, so it lives outside the
  // scroller and is nudged by it.
  const frame = el("div");
  frame.id = "mapframe";
  frame.innerHTML = mapSky(S().act);

  const wrap = el("div");
  wrap.id = "mapwrap";
  wrap.innerHTML = svg;
  wrap.addEventListener("click", (ev) => {
    const g = (ev.target as Element | null)?.closest("g.node[data-node]");
    if (g) travelTo(Number((g as HTMLElement).dataset.node));
  });
  frame.appendChild(wrap);
  st.appendChild(frame);

  geo = { svg: wrap.querySelector("svg")!, x, y };
  traveling = false;

  const layers = [...frame.querySelectorAll<SVGElement>(".map-sky .par")];
  const depthOf = (l: SVGElement) => Number(l.dataset["depth"] ?? 0);
  // Each layer has to be as tall as the frame *plus* everything it will slide
  // by, or its own bottom edge draws a hard line across the map at full scroll
  // — which is exactly what a fixed 130% height did.
  const layout = () => {
    const travel = Math.max(0, wrap.scrollHeight - wrap.clientHeight);
    layers.forEach((l) => {
      l.style.height = `${Math.ceil(wrap.clientHeight * 1.08 + travel * depthOf(l) + 24)}px`;
    });
  };
  const parallax = () => layers.forEach((l) => {
    l.style.transform = `translateY(${(-wrap.scrollTop * depthOf(l)).toFixed(1)}px)`;
  });
  wrap.addEventListener("scroll", parallax, { passive: true });

  st.appendChild(el("div", "legend", NODE_KINDS.map((kind) =>
    `<span>${nodeBadge(kind)}${NODE_ART[kind].title}</span>`).join("")));

  requestAnimationFrame(() => {
    const target = wrap.scrollHeight - (Math.max(0, m.cur_floor + 1) * ROW) - 280;
    wrap.scrollTop = Math.max(0, target);
    layout();
    parallax();
  });
}

/**
 * Walk there, then ask the server.
 *
 * Choosing a node used to swap the whole screen instantly, so a map with a
 * dozen branches gave no sense of having moved along one of them. The token
 * covers the edge it is taking; the request goes out when it arrives.
 */
function travelTo(idx: number) {
  if (traveling) return;
  const go = () => void send({ type: "map", idx });
  const m = S().map;
  if (!geo || reducedMotion()) { go(); return; }

  const to = { x: geo.x(m.cur_floor + 1, idx), y: geo.y(m.cur_floor + 1) };
  const from = m.cur_floor < 0
    // Before the first choice there is nowhere to walk from: rise into it.
    ? { x: to.x, y: geo.y(0) + ROW }
    : { x: geo.x(m.cur_floor, m.cur_idx), y: geo.y(m.cur_floor) };

  const token = document.createElementNS("http://www.w3.org/2000/svg", "circle");
  token.setAttribute("class", "token");
  token.setAttribute("r", "6");
  token.setAttribute("cx", String(from.x));
  token.setAttribute("cy", String(from.y));
  token.setAttribute("filter", "url(#glow)");
  geo.svg.appendChild(token);

  traveling = true;
  gsap.to(token, {
    attr: { cx: to.x, cy: to.y },
    duration: 0.42,
    ease: "power2.inOut",
    onComplete: go,
  });
}

export function mapKeys(k: string) {
  const i = LETTERS.indexOf(k);
  if (i >= 0 && S().map.reachable.includes(i)) travelTo(i);
}
