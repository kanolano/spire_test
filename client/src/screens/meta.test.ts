/**
 * Character select and the two ending screens.
 *
 * The ending screens fetch the leaderboard. `#stage` is one long-lived element
 * that every render wipes and refills, so appending on arrival dropped "Best
 * runs" onto whichever screen was showing by then — climb again before
 * /records answers and it landed on the map.
 */

import { beforeEach, describe, expect, it, vi } from "vitest";

const { getRecords, send } = vi.hoisted(() => ({
  getRecords: vi.fn(), send: vi.fn(),
}));
vi.mock("../net", async () => {
  const actual = await vi.importActual<typeof import("../net")>("../net");
  return { ...actual, getRecords };
});
vi.mock("../actions", () => ({ send, abandon: vi.fn() }));

import { renderEnd, renderSelect } from "./meta";
import { setAscension, setState } from "../store";
import { fakeState, mountShell } from "../test-harness";

const stage = () => document.querySelector("#stage") as HTMLElement;
function deferred<T>() {
  let resolve!: (v: T) => void;
  const promise = new Promise<T>((res) => { resolve = res; });
  return { promise, resolve };
}

const ROSTER = [{
  key: "sentinel", name: "The Sentinel", hp: 75, energy: 3, cards: 40,
  blurb: "Ash-caked plate.", deck: ["Strike"],
  relic: { key: "burning_blood", name: "Burning Blood", desc: "Heal 3." },
}];

const LADDER = [
  { level: 1, desc: "Enemies have more HP." },
  { level: 2, desc: "Elites and bosses have more HP." },
  { level: 3, desc: "You begin the climb wounded." },
];

beforeEach(() => {
  mountShell();
  getRecords.mockResolvedValue([]);
  send.mockReset();
  setAscension(0);
});

describe("the leaderboard", () => {
  it("shows the best runs once they arrive", async () => {
    getRecords.mockResolvedValue([
      { act: 3, floors: 24, won: false, killer: "Byrd" },
      { act: 4, floors: 30, won: true, killer: "—" },
    ]);
    setState(fakeState({ screen: "gameover" }));
    renderEnd(stage(), false);
    await vi.waitFor(() => expect(stage().textContent).toContain("Best runs"));
    expect(stage().textContent).toContain("died to Byrd");
    expect(stage().textContent).toContain("ascended");
  });

  it("never lands on a screen the player has already moved to", async () => {
    const records = deferred<unknown>();
    getRecords.mockReturnValue(records.promise);
    setState(fakeState({ screen: "gameover" }));
    renderEnd(stage(), false);

    // The player climbs again; the stage is wiped and refilled by the next
    // screen before the fetch answers.
    stage().innerHTML = "";
    stage().appendChild(document.createElement("main"));

    records.resolve([{ act: 3, floors: 24, won: false, killer: "Byrd" }]);
    await records.promise;
    await Promise.resolve();
    expect(stage().textContent).not.toContain("Best runs");
  });

  it("says nothing at all when there are no records", async () => {
    getRecords.mockResolvedValue([]);
    setState(fakeState({ screen: "gameover" }));
    renderEnd(stage(), false);
    await Promise.resolve();
    expect(stage().textContent).not.toContain("Best runs");
  });

  it("survives the leaderboard being unreachable", async () => {
    getRecords.mockRejectedValue(new Error("offline"));
    setState(fakeState({ screen: "gameover" }));
    expect(() => renderEnd(stage(), false)).not.toThrow();
    await Promise.resolve();
    expect(stage().textContent).toContain("You died");
  });
});

describe("the ascension picker", () => {
  const level = () => stage().querySelector(".asc-level")!.textContent;
  const step = (label: string) =>
    [...stage().querySelectorAll<HTMLButtonElement>(".asc-step")]
      .find((b) => b.textContent!.trim() === label)!;

  function select() {
    setState(fakeState({
      screen: "select", ascension_ladder: LADDER, classes: ROSTER,
    }));
    stage().innerHTML = "";
    renderSelect(stage());
  }

  it("starts on the plain climb and cannot go below it", () => {
    select();
    expect(level()).toContain("Ascension 0");
    expect(step("−").disabled).toBe(true);
  });

  it("lists every rung it is turning on, not just the last", () => {
    select();
    step("+").click();
    step("+").click();
    select();
    expect(stage().querySelectorAll(".asc-rung")).toHaveLength(2);
    expect(stage().textContent).toContain("Enemies have more HP.");
    expect(stage().textContent).toContain("Elites and bosses have more HP.");
  });

  it("stops at the top of the ladder the server described", () => {
    select();
    for (let i = 0; i < 10; i++) {
      const up = step("+");
      if (up.disabled) break;
      up.click();
      select();
    }
    expect(level()).toContain(`Ascension ${LADDER.length}`);
    expect(step("+").disabled).toBe(true);
  });

  it("sends the chosen rung with the run", () => {
    select();
    step("+").click();
    step("+").click();
    select();
    stage().querySelector<HTMLButtonElement>("button.cls")!.click();
    expect(send).toHaveBeenCalledWith(
      expect.objectContaining({ type: "new_run", cls: "sentinel", ascension: 2 }),
    );
  });

  it("sends ascension 0 when the player left it alone", () => {
    select();
    stage().querySelector<HTMLButtonElement>("button.cls")!.click();
    expect(send).toHaveBeenCalledWith(
      expect.objectContaining({ type: "new_run", ascension: 0 }),
    );
  });

  it("shows nothing when the server sent no ladder", () => {
    setState(fakeState({ screen: "select", ascension_ladder: [] }));
    stage().innerHTML = "";
    renderSelect(stage());
    expect(stage().querySelectorAll(".asc-step")).toHaveLength(0);
  });
});
