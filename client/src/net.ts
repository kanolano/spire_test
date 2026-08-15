/**
 * Transport, and the connection state the UI shows for it.
 *
 * The original UI reported nothing: a failed request went to console.error, a
 * failed boot left a permanently blank stage, and a dead server looked exactly
 * like a working one.
 */

import { $, el, esc } from "./dom";
import type { Action, Piles, RecordView, State } from "./types";

export class ApiError extends Error {
  constructor(message: string, readonly status: number) {
    super(message);
  }
}

export async function api<T>(path: string, options?: RequestInit): Promise<T> {
  const r = await fetch(path, options);   // throws only on network failure
  const text = await r.text();
  let body: unknown = null;
  if (text) {
    try { body = JSON.parse(text); } catch { body = null; }
  }
  if (!r.ok) {
    const msg = (body as { error?: string } | null)?.error
      ?? `Request failed (${r.status})`;
    throw new ApiError(msg, r.status);
  }
  return body as T;
}

const post = <T>(path: string, body: unknown) => api<T>(path, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});

export const getState = () => api<State>("/state");
export const getPiles = () => api<Piles>("/piles");
export const getRecords = () => api<RecordView[]>("/records");
export const postAction = (action: Action) => post<State>("/action", action);
export const postAbandon = () => post<State>("/abandon", {});

/* ── busy / offline / toasts ───────────────────────────────── */

export function toast(message: string, kind?: string) {
  const box = $("#toasts");
  const node = el("div", "toast" + (kind ? " " + kind : ""), esc(message));
  box.appendChild(node);
  setTimeout(() => node.remove(), 4200);
}

let busyDepth = 0;
let offline = false;

export const isBusy = () => busyDepth > 0;
export const isOffline = () => offline;

/**
 * Counted, not a flag. A request and the animation of its result overlap: the
 * request releases the lock in its `finally`, which lands while the timeline
 * is still playing. As a boolean that unlocked input mid-turn.
 */
export function setBusy(on: boolean) {
  busyDepth = Math.max(0, busyDepth + (on ? 1 : -1));
  document.body.classList.toggle("busy", busyDepth > 0);
}

export function setOffline(on: boolean, message?: string) {
  offline = on;
  const curtain = $("#curtain");
  if (message) $("#curtain-msg").textContent = message;
  curtain.hidden = !on;
}
