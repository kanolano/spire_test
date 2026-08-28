/**
 * The animation director.
 *
 * Its one rule is that the server snapshot is authoritative and the timeline
 * is only a way of arriving at it, so every path — reduced motion, a missing
 * scene, an empty stream, a skipped turn — has to end with the scene
 * reconciled against `after`. A dropped beat may make the journey less pretty;
 * it must never leave the display disagreeing with the engine.
 */

import { beforeEach, describe, expect, it, vi } from "vitest";

const { combatScene, updateCombat, setBusy } = vi.hoisted(() => ({
  combatScene: vi.fn(), updateCombat: vi.fn(), setBusy: vi.fn(),
}));
vi.mock("./screens/combat", () => ({ combatScene, updateCombat }));
vi.mock("./net", async () => {
  const actual = await vi.importActual<typeof import("./net")>("./net");
  return { ...actual, setBusy };
});

import { isPlaying, play, reducedMotion, skip } from "./director";
import { fakeState, mountShell, stubMatchMedia } from "./test-harness";

const before = () => fakeState({ screen: "combat" });
const after = () => fakeState({ screen: "combat" });

/** Only the parts of the scene the beats under test actually reach into. */
function fakeScene() {
  return { log: document.createElement("div") } as never;
}

beforeEach(() => {
  // `current` is module state and outlives a single test, so finish whatever
  // the last one left running before counting anything.
  skip();
  mountShell();
  stubMatchMedia(false);
  history.replaceState(null, "", "/");
  combatScene.mockReturnValue(fakeScene());
  updateCombat.mockReset();
  setBusy.mockReset();
});

describe("reducedMotion", () => {
  it("follows the operating system preference", () => {
    stubMatchMedia(true);
    expect(reducedMotion()).toBe(true);
  });

  it("can be forced with ?motion=off, so the path can be driven rather than assumed", () => {
    stubMatchMedia(false);
    history.replaceState(null, "", "/?motion=off");
    expect(reducedMotion()).toBe(true);
  });

  it("animates otherwise", () => {
    expect(reducedMotion()).toBe(false);
  });
});

describe("play always ends at the snapshot", () => {
  const fx = [{ k: "damage", who: 0, amount: 6 }] as never;

  it("reconciles immediately under reduced motion", () => {
    stubMatchMedia(true);
    play(before(), after(), fx);
    expect(updateCombat).toHaveBeenCalledTimes(1);
    expect(isPlaying()).toBe(false);
  });

  it("reconciles when there is no scene to animate in", () => {
    combatScene.mockReturnValue(null);
    play(before(), after(), fx);
    expect(updateCombat).toHaveBeenCalledTimes(1);
    expect(isPlaying()).toBe(false);
  });

  it("reconciles when the stream is empty", () => {
    play(before(), after(), [] as never);
    expect(updateCombat).toHaveBeenCalledTimes(1);
  });

  it("reconciles when there was no previous snapshot to animate from", () => {
    play(null, after(), fx);
    expect(updateCombat).toHaveBeenCalledTimes(1);
  });

  it("reconciles a stream it has no beat for, without going busy", () => {
    // An empty timeline never fires onComplete, so a stream of nothing the
    // director recognises would otherwise leave the client busy forever. It
    // does go busy on the way — that is fine, nothing renders in between —
    // but it has to come back out on its own.
    play(before(), after(), [{ k: "not_a_real_event" }] as never);
    expect(isPlaying()).toBe(false);
    expect(updateCombat).toHaveBeenCalled();
    expect(setBusy).toHaveBeenLastCalledWith(false);
  });
});

describe("skip", () => {
  it("is harmless when nothing is playing", () => {
    expect(isPlaying()).toBe(false);
    expect(() => skip()).not.toThrow();
  });

  it("jumps a running turn to its end and reconciles", () => {
    // A log line is a real beat, so this does start a timeline.
    play(before(), after(), [{ k: "log", text: "You play Strike." }] as never);
    expect(isPlaying()).toBe(true);
    expect(setBusy).toHaveBeenCalledWith(true);

    skip();

    expect(isPlaying()).toBe(false);
    expect(setBusy).toHaveBeenLastCalledWith(false);
    expect(updateCombat).toHaveBeenLastCalledWith(
      expect.objectContaining({ screen: "combat" }),
    );
  });

  it("never lets two turns animate at once", () => {
    play(before(), after(), [{ k: "log", text: "first" }] as never);
    play(before(), after(), [{ k: "log", text: "second" }] as never);
    // The first timeline is forced to its end rather than overlapping.
    expect(isPlaying()).toBe(true);
    skip();
    expect(isPlaying()).toBe(false);
  });
});
