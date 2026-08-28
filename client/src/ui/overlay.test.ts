/**
 * The modal, and the reason it has a generation counter.
 *
 * `showPile` fetches. By the time it can write, the player may have closed the
 * modal or asked it a different question, and both of those actually happened:
 * closing the deck view before /piles answered reopened it, and asking for the
 * draw pile then the discard pile showed whichever the server finished last.
 */

import { beforeEach, describe, expect, it, vi } from "vitest";

// vi.mock is hoisted above the file, so the stub has to be hoisted with it.
const { getPiles, toast } = vi.hoisted(() => ({
  getPiles: vi.fn(), toast: vi.fn(),
}));
vi.mock("../net", async () => {
  const actual = await vi.importActual<typeof import("../net")>("../net");
  return { ...actual, getPiles, toast };
});

import {
  closeOverlay, openOverlay, overlayGeneration, overlayOpen, showPile,
} from "./overlay";
import { fakeCard, mountShell } from "../test-harness";

const title = () => document.querySelector("#overlay-title")!.textContent;
/** A promise the test resolves by hand, to hold a response open. */
function deferred<T>() {
  let resolve!: (v: T) => void;
  let reject!: (e: unknown) => void;
  const promise = new Promise<T>((res, rej) => { resolve = res; reject = rej; });
  return { promise, resolve, reject };
}

beforeEach(() => {
  mountShell();
  getPiles.mockReset();
});

describe("the generation counter", () => {
  it("moves whenever the modal's contents are replaced", () => {
    const before = overlayGeneration();
    openOverlay("Your deck", []);
    expect(overlayGeneration()).not.toBe(before);
  });

  it("moves when the modal is dismissed", () => {
    openOverlay("Your deck", []);
    const shown = overlayGeneration();
    closeOverlay();
    expect(overlayGeneration()).not.toBe(shown);
  });
});

describe("showPile", () => {
  it("shows what came back when nothing else happened meanwhile", async () => {
    getPiles.mockResolvedValue({ draw_pile: [fakeCard()] });
    await showPile("draw_pile");
    expect(title()).toBe("Draw pile — 1 cards");
    expect(overlayOpen()).toBe(true);
  });

  it("stays shut if the player closed it before the answer arrived", async () => {
    const piles = deferred<unknown>();
    getPiles.mockReturnValue(piles.promise);
    const pending = showPile("draw_pile");
    expect(overlayOpen()).toBe(true);          // "Loading…"
    closeOverlay();
    piles.resolve({ draw_pile: [fakeCard()] });
    await pending;
    expect(overlayOpen()).toBe(false);
  });

  it("does not let a slow answer overwrite the question asked after it", async () => {
    // The first request answers last, which is exactly what last-writer-wins
    // gets wrong.
    const slow = deferred<unknown>();
    const fast = deferred<unknown>();
    getPiles.mockReturnValueOnce(slow.promise).mockReturnValueOnce(fast.promise);

    const first = showPile("draw_pile");
    const second = showPile("discard_pile");
    fast.resolve({ discard_pile: [fakeCard({ key: "defend", name: "Defend" })] });
    await second;
    expect(title()).toBe("Discard pile — 1 cards");

    slow.resolve({ draw_pile: [fakeCard()] });
    await first;
    expect(title()).toBe("Discard pile — 1 cards");
  });

  it("does not report a failure onto a modal showing something else", async () => {
    const slow = deferred<unknown>();
    getPiles.mockReturnValue(slow.promise);
    const pending = showPile("draw_pile");
    openOverlay("Your relics", []);            // player moved on
    slow.reject(new Error("network down"));
    await pending;
    expect(overlayOpen()).toBe(true);
    expect(title()).toBe("Your relics");
  });
});
