/**
 * Screen transitions.
 *
 * Two things have gone wrong here in the real client, and both are here:
 * every screen change used to be the same fade so leaving a shop and walking
 * into a fight felt identical, and a screen rebuilt *in place* re-dealt rows
 * that had never left, which read as the whole page flickering.
 */

import { beforeEach, describe, expect, it, vi } from "vitest";

// The leaderboard fetch fires on the two ending screens. `restoreMocks` wipes
// an implementation set inside the factory, so it is set per test instead.
const { getRecords } = vi.hoisted(() => ({ getRecords: vi.fn() }));
vi.mock("./net", async () => {
  const actual = await vi.importActual<typeof import("./net")>("./net");
  return { ...actual, getRecords };
});

import { render } from "./render";
import { setLastScreen, setState } from "./store";
import { fakeState, mountShell } from "./test-harness";

const stage = () => document.querySelector("#stage")!;

/** Put the client on `screen`, having come from `from`. */
function go(screen: string, from: string | null) {
  setLastScreen(from);
  setState(fakeState({ screen }));
  render();
  return stage().className;
}

beforeEach(() => {
  mountShell();
  setLastScreen(null);
  getRecords.mockResolvedValue([]);
});

describe("direction of travel", () => {
  it("settles onto the screens that are not part of a climb", () => {
    expect(go("select", null)).toContain("enter-settle");
    expect(go("gameover", "combat")).toContain("enter-settle");
    expect(go("win", "combat")).toContain("enter-settle");
  });

  it("comes back to the map and goes forward into everything else", () => {
    expect(go("map", "shop")).toContain("enter-back");
    expect(go("shop", "map")).toContain("enter-fwd");
    expect(go("combat", "map")).toContain("enter-fwd");
  });

  it("names the screen it is on, so CSS can target it", () => {
    expect(go("shop", "map")).toContain("screen-shop");
  });
});

describe("the arrive gate", () => {
  it("marks a real screen change as an arrival", () => {
    expect(go("reward", "combat")).toContain("arrive");
  });

  it("does not mark a screen rebuilt in place as one", () => {
    // Taking one of three rewards rebuilds the reward screen from scratch.
    // That is not an arrival, and animating it re-deals the rows that stayed.
    go("reward", "combat");
    setState(fakeState({ screen: "reward" }));
    render();
    expect(stage().className).toContain("screen-reward");
    expect(stage().className).not.toContain("arrive");
  });

  it("clears the arrival marks of the screen before it", () => {
    go("reward", "combat");
    const next = go("map", "reward");
    expect(next).toContain("enter-back");
    expect(next).not.toContain("enter-fwd");
  });
});
