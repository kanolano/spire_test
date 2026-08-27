/**
 * One hidden SVG holding every gradient and filter the sprites reference.
 *
 * Per-sprite <defs> would mean 29 copies of the same four filters, and ids
 * that collide the moment two of the same monster are on screen. Referencing
 * document-level ids from many separate <svg> elements is fine, so they live
 * here and get mounted once.
 */

import { RAMPS, type RampName } from "./palette";

export const bodyGrad = (ramp: RampName) => `spire-body-${ramp}`;
export const GLOW_SOFT = "spire-glow-soft";
export const GLOW_HARD = "spire-glow-hard";
export const INNER_SHADE = "spire-inner";

/** Blend two hex colours, so gradient stops stay inside the ramp. */
export function mix(a: string, b: string, t: number): string {
  const hex = (s: string) => [1, 3, 5].map((i) => parseInt(s.slice(i, i + 2), 16));
  const [ar, ag, ab] = hex(a);
  const [br, bg, bb] = hex(b);
  const ch = (x: number, y: number) =>
    Math.round(x + (y - x) * t).toString(16).padStart(2, "0");
  return `#${ch(ar!, br!)}${ch(ag!, bg!)}${ch(ab!, bb!)}`;
}

let mounted = false;

export function mountArtDefs() {
  if (mounted) return;
  mounted = true;

  const grads = (Object.keys(RAMPS) as RampName[]).map((name) => {
    const r = RAMPS[name];
    return `
      <!-- The light falls from the upper left. Only the last fifth reaches
           ink: an earlier version bottomed out at near-black by 60%, which
           left every creature reading as an outline on a dark stage. -->
      <linearGradient id="${bodyGrad(name)}" x1="0.15" y1="0" x2="0.6" y2="1">
        <stop offset="0" stop-color="${r.rim}"/>
        <stop offset="0.28" stop-color="${r.shade}"/>
        <stop offset="0.8" stop-color="${mix(r.shade, r.ink, 0.7)}"/>
        <stop offset="1" stop-color="${r.ink}"/>
      </linearGradient>`;
  }).join("");

  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("aria-hidden", "true");
  svg.setAttribute("width", "0");
  svg.setAttribute("height", "0");
  svg.style.cssText = "position:absolute;width:0;height:0;overflow:hidden";
  svg.innerHTML = `
    <defs>
      ${grads}
      <!-- userSpaceOnUse and a generous region: a percentage filter area is a
           percentage of the bounding box, so a thin shape's glow collapses. -->
      <filter id="${GLOW_SOFT}" filterUnits="userSpaceOnUse"
              x="-20" y="-20" width="140" height="140">
        <feGaussianBlur stdDeviation="2.6" result="b"/>
        <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
      </filter>
      <filter id="${GLOW_HARD}" filterUnits="userSpaceOnUse"
              x="-20" y="-20" width="140" height="140">
        <feGaussianBlur stdDeviation="1.1" result="b"/>
        <feMerge>
          <feMergeNode in="b"/><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/>
        </feMerge>
      </filter>
      <radialGradient id="${INNER_SHADE}" cx="34%" cy="22%">
        <stop offset="0" stop-color="#ffffff" stop-opacity="0.22"/>
        <stop offset="0.5" stop-color="#ffffff" stop-opacity="0.02"/>
        <stop offset="1" stop-color="#000000" stop-opacity="0.18"/>
      </radialGradient>
    </defs>`;
  document.body.appendChild(svg);
}
