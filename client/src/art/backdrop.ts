/**
 * The room the fight happens in.
 *
 * Combat floated on the same flat gradient whether it was the first Jaw Worm
 * of act 1 or the Ashen Sovereign, so nothing about the screen said where you
 * were or how much trouble you were in. Each act gets its own palette and
 * silhouette, and elites and bosses darken and close in.
 *
 * Deliberately low contrast: this is the room, not the subject. If a backdrop
 * competes with a creature for attention it is wrong.
 */

const ACT = {
  1: { sky: ["#241d33", "#140f1e"], far: "#1d1830", near: "#171227", haze: "#3a2a4a" },
  2: { sky: ["#2a1d24", "#170f16"], far: "#241722", near: "#1c1119", haze: "#4a2a34" },
  3: { sky: ["#2c2118", "#160f0c"], far: "#271a12", near: "#1d130d", haze: "#5a3520" },
} as const;

type Kind = "monster" | "elite" | "boss";

/** Jagged ridge line — the Spire's broken masonry, at a given height. */
function ridge(y: number, seed: number, fill: string, opacity: number): string {
  const pts: string[] = [`0,100`];
  let x = 0;
  let r = seed;
  const rand = () => (r = (r * 1103515245 + 12345) % 2147483648) / 2147483648;
  while (x < 100) {
    const w = 4 + rand() * 9;
    const h = y + (rand() - 0.5) * 9;
    pts.push(`${x.toFixed(1)},${h.toFixed(1)}`);
    x += w;
    pts.push(`${Math.min(100, x).toFixed(1)},${h.toFixed(1)}`);
  }
  pts.push("100,100");
  return `<polygon points="${pts.join(" ")}" fill="${fill}" opacity="${opacity}"/>`;
}

export function backdropSvg(act: number, kind: Kind): string {
  const a = ACT[(Math.min(3, Math.max(1, act)) as 1 | 2 | 3)];
  const heavy = kind !== "monster";

  return `<svg class="backdrop" viewBox="0 0 100 100" preserveAspectRatio="none"
      aria-hidden="true">
    <defs>
      <linearGradient id="bd-sky" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" stop-color="${a.sky[0]}"/>
        <stop offset="1" stop-color="${a.sky[1]}"/>
      </linearGradient>
      <radialGradient id="bd-haze" cx="50%" cy="86%" r="60%">
        <stop offset="0" stop-color="${a.haze}" stop-opacity="${heavy ? 0.5 : 0.32}"/>
        <stop offset="1" stop-color="${a.haze}" stop-opacity="0"/>
      </radialGradient>
    </defs>
    <rect width="100" height="100" fill="url(#bd-sky)"/>
    ${ridge(52, act * 7919 + 13, a.far, 0.95)}
    ${ridge(72, act * 104729 + 7, a.near, 1)}
    <rect width="100" height="100" fill="url(#bd-haze)"/>
    ${heavy ? `<rect width="100" height="100" fill="#000" opacity="${kind === "boss" ? 0.3 : 0.18}"/>` : ""}
  </svg>`.replace(/\s+/g, " ");
}
