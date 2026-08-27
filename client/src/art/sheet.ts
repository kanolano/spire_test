/**
 * A contact sheet of every sprite, at /?art=1.
 *
 * Judging a bestiary one monster at a time, by fighting your way to each one,
 * is how a set drifts apart. Seeing all 29 side by side is the only way to
 * tell whether they read as one hand — and it is the loop this art was
 * actually developed against.
 */

import { mountArtDefs } from "./defs";
import { creatureSvg, CREATURE_KEYS } from "./creatures";
import { NODE_KINDS, nodeBadge } from "./nodes";
import {
  campfireScene, chestScene, endingScene, merchantScene, omenScene,
} from "./scenes";
import { RAMP_NAMES, RAMPS } from "./palette";

export const artSheetRequested = () =>
  new URLSearchParams(location.search).get("art") === "1";

export function renderArtSheet() {
  // Order matters: the defs live in a hidden <svg> appended to <body>, so
  // clearing the body after mounting them silently strips every gradient and
  // leaves the whole bestiary rendering as bare outlines.
  document.body.innerHTML = "";
  mountArtDefs();
  document.body.style.cssText =
    "margin:0;padding:28px;background:#0a0810;color:#ece6f5;"
    + "font:14px system-ui,sans-serif;overflow:auto;height:auto";

  const h = document.createElement("h1");
  h.textContent = `Bestiary — ${CREATURE_KEYS.length} creatures`;
  h.style.cssText = "font:600 22px Georgia,serif;color:#e0b978;letter-spacing:.08em";
  document.body.appendChild(h);

  const swatches = document.createElement("div");
  swatches.style.cssText = "display:flex;gap:10px;flex-wrap:wrap;margin:14px 0 26px";
  swatches.innerHTML = RAMP_NAMES.map((n) => {
    const r = RAMPS[n];
    return `<div style="text-align:center">
      <div style="width:76px;height:26px;border-radius:3px;
        background:linear-gradient(90deg,${r.ink},${r.shade},${r.rim});
        box-shadow:inset 0 0 0 1px ${r.glow}55"></div>
      <div style="font-size:11px;color:#9a8fb0;margin-top:3px">${n}</div></div>`;
  }).join("");
  document.body.appendChild(swatches);

  const grid = document.createElement("div");
  grid.style.cssText =
    "display:grid;grid-template-columns:repeat(auto-fill,minmax(140px,1fr));gap:18px";
  grid.innerHTML = CREATURE_KEYS.map((key) => `
    <div style="text-align:center;padding:10px 6px;border:1px solid #372f4a;
                border-radius:4px;background:linear-gradient(#181422,#100d18)">
      <div style="height:158px;display:flex;align-items:flex-end;justify-content:center">
        ${creatureSvg(key) ?? "?"}
      </div>
      <div style="font-size:11.5px;color:#9a8fb0;margin-top:8px">${key}</div>
    </div>`).join("");
  document.body.appendChild(grid);

  // The map icons are drawn at 17px and judged nowhere else, which is how you
  // end up with an elite skull that reads as a goblet. Here they are big.
  const nodes = document.createElement("div");
  nodes.style.cssText = "display:flex;gap:26px;flex-wrap:wrap;margin:34px 0 0";
  nodes.innerHTML = NODE_KINDS.map((kind) => `
    <div style="text-align:center">
      <div style="display:grid;place-items:center;width:110px;height:110px;
                  border:1px solid #372f4a;border-radius:4px;
                  background:radial-gradient(circle at 35% 28%,#3a3052,#15111e)">
        ${nodeBadge(kind, 78)}
      </div>
      <div style="font-size:11.5px;color:#9a8fb0;margin-top:6px">${kind}</div>
      <div style="font-size:11.5px;color:#4a4260">${nodeBadge(kind, 17)}</div>
    </div>`).join("");
  const nh = document.createElement("h2");
  nh.textContent = "Map nodes";
  nh.style.cssText = "font:600 17px Georgia,serif;color:#e0b978;margin:34px 0 0";
  document.body.appendChild(nh);
  document.body.appendChild(nodes);

  // The set pieces, which are otherwise only reachable by playing to them —
  // a campfire is four floors and a fight away from a reload.
  const sh = document.createElement("h2");
  sh.textContent = "Set pieces";
  sh.style.cssText = "font:600 17px Georgia,serif;color:#e0b978;margin:34px 0 0";
  document.body.appendChild(sh);

  const scenes = document.createElement("div");
  scenes.style.cssText = "display:flex;gap:22px;flex-wrap:wrap;margin:16px 0 0";
  scenes.innerHTML = ([
    ["campfire", campfireScene()],
    ["merchant", merchantScene()],
    ["chest", chestScene()],
    ["omen", omenScene()],
    ["ascended", endingScene(true)],
    ["died", endingScene(false)],
  ] as const).map(([name, art]) => `
    <div style="text-align:center">
      <div style="display:grid;place-items:end center;width:200px;height:190px;
                  padding:12px;border:1px solid #372f4a;border-radius:4px;
                  background:linear-gradient(#181422,#100d18)">${art}</div>
      <div style="font-size:11.5px;color:#9a8fb0;margin-top:6px">${name}</div>
    </div>`).join("");
  document.body.appendChild(scenes);

  // Height is set inline per creature so bosses read bigger; only the shared
  // presentation belongs here.
  const style = document.createElement("style");
  style.textContent =
    "svg.csprite{display:block;width:auto;overflow:visible;"
    + "filter:drop-shadow(0 6px 8px rgba(0,0,0,.55))}";
  document.head.appendChild(style);
}
