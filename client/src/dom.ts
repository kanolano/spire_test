/** Small DOM helpers, carried over from app.js. */

export const $ = <T extends HTMLElement = HTMLElement>(sel: string): T => {
  const node = document.querySelector<T>(sel);
  if (!node) throw new Error(`missing element: ${sel}`);
  return node;
};

export function el<K extends keyof HTMLElementTagNameMap>(
  tag: K, cls?: string, html?: string,
): HTMLElementTagNameMap[K] {
  const d = document.createElement(tag);
  if (cls) d.className = cls;
  if (html != null) d.innerHTML = html;
  return d;
}

// Quotes matter: esc() output is interpolated into double-quoted attributes.
const ESCAPES: Record<string, string> = {
  "<": "&lt;", ">": "&gt;", "&": "&amp;", '"': "&quot;", "'": "&#39;",
};
export const esc = (s: unknown): string =>
  String(s).replace(/[<>&"']/g, (m) => ESCAPES[m]!);

/** Anything carrying these two attributes gets the hover/focus/tap tooltip. */
export const tipAttrs = (name: string, desc?: string): string =>
  ` data-tip="${esc(name)}" data-tip-desc="${esc(desc || "")}"`;

/** The centred continue/skip/leave button, which was copy-pasted six times. */
export function ctaButton(label: string, onclick: () => void, cls?: string) {
  const b = el("button", cls || "tbtn", label);
  b.style.cssText = "display:block;margin:24px auto";
  b.onclick = onclick;
  return b;
}

export const LETTERS = "abcdefgh";

/**
 * Deal a screen's contents in rather than having them all appear at once.
 *
 * The delay is set per node instead of by nth-child rules because the counts
 * are not known here — a shop has as many rows as it has stock. Reduced motion
 * is handled by the same global rule that flattens every other animation, so
 * there is nothing to branch on.
 */
export function staggerIn(
  nodes: Iterable<Element>, step = 0.05, base = 0.03,
): void {
  // Arrivals only. Every non-combat screen is rebuilt from scratch on any
  // state change, so without this an update re-deals contents that were
  // already on screen and unchanged.
  if (!document.querySelector("#stage.arrive")) return;
  [...nodes].forEach((n, i) => {
    n.classList.add("risein");
    (n as HTMLElement).style.animationDelay = `${(base + i * step).toFixed(3)}s`;
  });
}
