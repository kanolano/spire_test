/**
 * The whole client, booted against a scripted server.
 *
 * The unit tests each hold one module still. This one runs the real boot path
 * and walks a run through the screens it actually visits, because the failures
 * worth catching here are the ones that only appear when the pieces are wired
 * together: a screen that throws on a shape the server really sends, a render
 * that leaves the stage empty, a transition that loses the run.
 */

import { beforeEach, describe, expect, it, vi } from "vitest";

import { boot, send } from "./actions";
import { render } from "./render";
import { onRender, S } from "./store";
import { fakeCard, fakeState, mountShell, stubMatchMedia } from "./test-harness";

const stage = () => document.querySelector("#stage") as HTMLElement;

/** The next snapshot every /state and /action call will answer with. */
let next: unknown;
const seen: string[] = [];

function serve(state: unknown) { next = state; }

beforeEach(() => {
  mountShell();
  stubMatchMedia(false);
  onRender(render);
  seen.length = 0;
  vi.stubGlobal("fetch", vi.fn(async (path: string) => {
    seen.push(path);
    const body = path === "/records" ? [] : path === "/piles" ? {} : next;
    return {
      ok: true, status: 200,
      text: async () => JSON.stringify(body),
    } as Response;
  }));
});

describe("booting", () => {
  it("draws the class-select screen from the server's first answer", async () => {
    serve(fakeState({
      screen: "select",
      classes: [{
        key: "sentinel", name: "The Sentinel", hp: 75, energy: 3, cards: 40,
        blurb: "Ash-caked plate.", deck: ["Strike"],
        relic: { key: "burning_blood", name: "Burning Blood", desc: "Heal 3." },
      }],
      ascension_ladder: [{ level: 1, desc: "Enemies have more HP." }],
    }));
    await boot();
    expect(seen).toContain("/state");
    expect(stage().textContent).toContain("Choose your climber");
    expect(stage().textContent).toContain("The Sentinel");
  });

  it("says so rather than sitting blank when the Spire cannot be reached", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => { throw new TypeError("network"); }));
    await boot();
    expect(document.body.textContent).toMatch(/reach the Spire/i);
  });
});

describe("walking a run through its screens", () => {
  async function arriveAt(screen: string, over: Record<string, unknown> = {}) {
    serve(fakeState({ screen, ...over }));
    await send({ type: "map", idx: 0 } as never);
  }

  beforeEach(async () => {
    serve(fakeState({ screen: "map" }));
    await boot();
  });

  it("starts on the map", () => {
    expect(stage().textContent).toContain("Choose your path");
    expect(S().screen).toBe("map");
  });

  it("renders a fight", async () => {
    await arriveAt("combat");
    expect(stage().textContent).toContain("Jaw Worm");
    expect(stage().querySelector("#field")).not.toBeNull();
  });

  it("renders the reward screen after it", async () => {
    await arriveAt("combat");
    await arriveAt("reward", {
      reward: {
        gold: 12, kind: "monster", log: ["Jaw Worm is slain!"],
        relic: null, potion: null, cards: [fakeCard()],
        relic_taken: false, potion_taken: false, card_taken: false,
        potions_full: false,
      },
    });
    expect(stage().textContent).toContain("Strike");
    expect(stage().textContent).toContain("12");
  });

  it("comes back to the map without losing the run", async () => {
    await arriveAt("combat");
    await arriveAt("map");
    expect(stage().textContent).toContain("Choose your path");
    expect(stage().className).toContain("enter-back");
  });

  it("ends on the death screen, and asks the leaderboard exactly once", async () => {
    await arriveAt("gameover", { killer: "Jaw Worm" });
    expect(stage().textContent).toContain("You died");
    expect(stage().textContent).toContain("Jaw Worm");
    expect(seen.filter((p) => p === "/records")).toHaveLength(1);
  });

  it("leaves no screen blank", async () => {
    for (const screen of ["map", "combat", "gameover"]) {
      await arriveAt(screen);
      expect(stage().textContent!.trim().length).toBeGreaterThan(0);
    }
  });
});
