import { esc, tipAttrs } from "../dom";
import type { StatusView } from "../types";

/** Chips carry their own explanation so they can be tooltipped. */
export const statusChip = (s: StatusView): string =>
  `<span class="chip st" data-k="${esc(s.key)}" tabindex="0"` +
  tipAttrs(s.name || s.label, s.desc) +
  ` aria-label="${esc(s.name || s.label)} ${s.value}: ${esc(s.desc || "")}">` +
  `${esc(s.label)} ${s.value}</span>`;
