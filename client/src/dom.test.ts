import { beforeEach, describe, expect, it } from "vitest";

import { ctaButton, esc, staggerIn } from "./dom";
import { mountShell } from "./test-harness";

beforeEach(mountShell);

describe("esc", () => {
  it("escapes the characters that would break out of an attribute", () => {
    expect(esc(`<b>"x"&'y'`)).toBe("&lt;b&gt;&quot;x&quot;&amp;&#39;y&#39;");
  });

  it("stringifies whatever it is given", () => {
    expect(esc(7)).toBe("7");
    expect(esc(null)).toBe("null");
  });
});

describe("staggerIn", () => {
  const rows = () => {
    const stage = document.querySelector("#stage")!;
    stage.innerHTML = "<i></i><i></i><i></i>";
    return [...stage.children];
  };

  it("deals nodes in on arrival at a screen", () => {
    document.querySelector("#stage")!.className = "arrive";
    const nodes = rows();
    staggerIn(nodes);
    expect(nodes.map((n) => n.classList.contains("risein"))).toEqual([true, true, true]);
    expect(nodes.map((n) => (n as HTMLElement).style.animationDelay))
      .toEqual(["0.030s", "0.080s", "0.130s"]);
  });

  it("does nothing when the screen was rebuilt in place", () => {
    // The bug this guards: every non-combat screen is rebuilt from scratch on
    // any state change, so taking one of three rewards re-dealt the two rows
    // that had never left, and the whole page read as a flicker.
    document.querySelector("#stage")!.className = "";
    const nodes = rows();
    staggerIn(nodes);
    expect(nodes.some((n) => n.classList.contains("risein"))).toBe(false);
    expect(nodes.every((n) => !(n as HTMLElement).style.animationDelay)).toBe(true);
  });

  it("honours a custom step and base", () => {
    document.querySelector("#stage")!.className = "arrive";
    const nodes = rows();
    staggerIn(nodes, 0.1, 0.2);
    expect((nodes[1] as HTMLElement).style.animationDelay).toBe("0.300s");
  });
});

describe("ctaButton", () => {
  it("wires the click through", () => {
    let hits = 0;
    const b = ctaButton("Leave", () => { hits += 1; });
    b.click();
    expect(hits).toBe(1);
    expect(b.textContent).toBe("Leave");
  });
});
