import { beforeEach, describe, expect, it } from "vitest";

import {
  ascension, dailyMode, lastScreen, maybeS, pendingFx, prev, resetForNewRun, S,
  sel, setAscension, setDailyMode, setLastScreen, setPendingFx, setSel, setState,
} from "./store";
import { fakeState } from "./test-harness";

beforeEach(() => {
  resetForNewRun();
  setDailyMode(false);
  setAscension(0);
});

describe("the snapshot pair", () => {
  it("keeps the previous snapshot so the director can diff against it", () => {
    const first = fakeState({ floor: 1 });
    const second = fakeState({ floor: 2 });
    setState(first);
    setState(second);
    expect(S()).toBe(second);
    expect(prev()).toBe(first);
  });

  it("can hold the previous snapshot still across a re-render", () => {
    // Selecting or cancelling a card re-renders without a server response, and
    // must not consume the snapshot the animation still needs.
    const first = fakeState({ floor: 1 });
    setState(first);
    setState(fakeState({ floor: 2 }));
    setState(fakeState({ floor: 3 }), true);
    expect(prev()).toBe(first);
  });

  it("maybeS is the honest read before boot", () => {
    expect(maybeS()).not.toBeNull();
  });
});

describe("client-only choices", () => {
  it("remembers the daily toggle and the ascension rung", () => {
    setDailyMode(true);
    setAscension(5);
    expect(dailyMode).toBe(true);
    expect(ascension).toBe(5);
  });

  it("keeps them across a new run, since they choose the next one", () => {
    setDailyMode(true);
    setAscension(4);
    resetForNewRun();
    expect(dailyMode).toBe(true);
    expect(ascension).toBe(4);
  });
});

describe("resetForNewRun", () => {
  it("drops everything that belonged to the finished run", () => {
    setState(fakeState());
    setState(fakeState());
    setSel({ kind: "card", idx: 2, mode: "target" });
    setPendingFx(true);
    setLastScreen("combat");

    resetForNewRun();

    expect(prev()).toBeNull();
    expect(sel()).toBeNull();
    expect(pendingFx).toBe(false);
    expect(lastScreen).toBeNull();
  });
});
