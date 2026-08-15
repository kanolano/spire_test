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

  // Height is set inline per creature so bosses read bigger; only the shared
  // presentation belongs here.
  const style = document.createElement("style");
  style.textContent =
    "svg.csprite{display:block;width:auto;overflow:visible;"
    + "filter:drop-shadow(0 6px 8px rgba(0,0,0,.55))}";
  document.head.appendChild(style);
}
