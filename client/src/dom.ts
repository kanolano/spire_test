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
