/** Everything that talks to the server and then redraws. */

import {
  ApiError, getState, isBusy, isOffline, postAbandon, postAction,
  setBusy, setOffline, toast,
} from "./net";
import {
  render, resetForNewRun, setPendingFx, setSel, setState,
} from "./store";
import type { Action } from "./types";

export async function send(action: Action) {
  if (isBusy() || isOffline()) return;
  setBusy(true);
  try {
    const next = await postAction(action);
    setState(next);
    setSel(null);
    setPendingFx(true);
    setOffline(false);
    render();
  } catch (e) {
    if (e instanceof ApiError) {
      // The engine refused the action and said why — show it and stay put.
      toast(e.message);
      setSel(null);
      render();
    } else {
      setOffline(true, "Lost contact with the Spire.");
    }
  } finally {
    setBusy(false);
  }
}

/**
 * Throwing a run away had a server route and no way at all to reach it, so
 * changing class meant dying first — and even then "Climb again" silently
 * restarted the class you had just finished with.
 */
export async function abandon() {
  if (isBusy() || isOffline()) return;
  setBusy(true);
  try {
    const next = await postAbandon();
    resetForNewRun();
    setState(next, true);
    setOffline(false);
    render();
  } catch (e) {
    if (e instanceof ApiError) toast(e.message);
    else setOffline(true, "Lost contact with the Spire.");
  } finally {
    setBusy(false);
  }
}

export async function boot() {
  setBusy(true);
  try {
    setState(await getState());
    setOffline(false);
    render();
  } catch (e) {
    setOffline(true, e instanceof ApiError
      ? "The Spire could not start a run."
      : "Could not reach the Spire. Is the server running?");
  } finally {
    setBusy(false);
  }
}

export async function reconnect() {
  setOffline(false);
  await boot();
}
