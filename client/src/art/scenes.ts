/**
 * The set pieces the non-combat screens stand in.
 *
 * A campfire, a merchant and a chest were each a line of centred text with an
 * emoji or nothing at all, which is why every screen between fights looked
 * like the same form with different words on it. These are drawn in the same
 * 100×100 box as the bestiary, ground at y=88, so a scene and a creature agree
 * about where the floor is.
 *
 * They are deliberately quiet: a scene sits behind a decision the player is
 * making, and must not compete with the buttons.
 */

import { GLOW_HARD, GLOW_SOFT, INNER_SHADE, bodyGrad } from "./defs";
import { body, eyes } from "./kit";
import { RAMPS } from "./palette";

const svg = (cls: string, inner: string, px: number) =>
  `<svg class="scene ${cls}" viewBox="0 0 100 100" height="${px}"
     preserveAspectRatio="xMidYMax meet" aria-hidden="true">${inner}</svg>`
    .replace(/\s+/g, " ");

/* ── the campfire ──────────────────────────────────────────── */

/** Stones, two logs and a flame that actually burns (see .rig-flame). */
export function campfireScene(px = 150): string {
  const a = RAMPS.ash;
  const s = RAMPS.stone;

  const stones = [
    [26, 84, 9, 5], [38, 87, 8.5, 4.6], [50, 88, 9, 4.8],
    [62, 87, 8.5, 4.6], [74, 84, 9, 5],
  ].map(([cx, cy, rx, ry]) =>
    `<ellipse cx="${cx}" cy="${cy}" rx="${rx}" ry="${ry}"
       fill="${s.shade}" stroke="${s.rim}" stroke-opacity=".35"/>`).join("");

  const log = (x1: number, y1: number, x2: number, y2: number) =>
    `<path d="M${x1} ${y1} L${x2} ${y2}" stroke="${RAMPS.flesh.ink}" stroke-width="7"
       stroke-linecap="round"/>`
    + `<path d="M${x1} ${y1} L${x2} ${y2}" stroke="${RAMPS.flesh.shade}" stroke-width="3"
       stroke-linecap="round" opacity=".55"/>`;

  return svg("scene-fire", `
    <ellipse cx="50" cy="84" rx="40" ry="12" fill="${a.glow}" opacity=".10"
      filter="url(#${GLOW_SOFT})"/>
    ${stones}
    ${log(30, 84, 66, 70)}${log(70, 84, 34, 70)}
    <g filter="url(#${GLOW_SOFT})">
      <path class="rig-flame" d="M50 26 q15 18 15 29 a15 15 0 0 1 -30 0
        q0 -8 7 -15 q1 7 5 9 q4 -9 3 -23 z" fill="${a.glow}" opacity=".92"/>
      <path class="rig-flame" d="M51 48 q8 10 8 16 a8 8 0 0 1 -16 0 q0 -6 8 -16 z"
        fill="#ffd9a0" opacity=".95"/>
    </g>
    <g class="rig-ember" filter="url(#${GLOW_SOFT})">
      <circle cx="38" cy="34" r="1.7" fill="${a.glow}"/>
      <circle cx="62" cy="26" r="1.3" fill="${a.glow}" opacity=".8"/>
      <circle cx="56" cy="16" r="1" fill="${a.glow}" opacity=".6"/>
    </g>`, px);
}

/* ── the merchant ──────────────────────────────────────────── */

/** A hooded figure behind a counter, with a lantern and something to sell. */
export function merchantScene(px = 150): string {
  const c = RAMPS.cloth;
  const g = RAMPS.regal;

  return svg("scene-shop", `
    <!-- The figure stands behind the counter, so it is drawn first and cut
         off by it rather than floating above it. -->
    <g transform="translate(0 -22)">
      ${body("draped", "cloth", 40, 46)}
      ${eyes("cloth", { y: 54, spread: 9, r: 2.4 })}
      <path d="M32 56 q18 -22 36 0 q-18 -9 -36 0 z" fill="${c.ink}"
        stroke="${c.rim}" stroke-opacity=".5" stroke-width="1.4"/>
    </g>
    <path d="M14 70 h72 v6 H14 z" fill="${g.ink}" stroke="${g.rim}"
      stroke-opacity=".5" stroke-width="1.2"/>
    <path d="M18 76 h64 l-4 14 H22 z" fill="url(#${bodyGrad("regal")})" opacity=".9"/>
    <path d="M18 76 h64 l-4 14 H22 z" fill="url(#${INNER_SHADE})"/>
    <!-- wares: a flask and a stack of coin -->
    <path d="M60.5 58 h5 v4 l3.5 6 a5.5 5.5 0 0 1 -12 0 l3.5 -6 z"
      fill="#4e9ec4" opacity=".9" stroke="#9fd6ef" stroke-opacity=".5"/>
    <rect x="60" y="55.5" width="6" height="3" rx="1" fill="${c.rim}"/>
    <g fill="${g.glow}" opacity=".9">
      <ellipse cx="34" cy="68" rx="6" ry="2"/><ellipse cx="34" cy="65" rx="5.4" ry="1.9"/>
      <ellipse cx="34" cy="62.2" rx="4.8" ry="1.8"/>
    </g>
    <!-- lantern, hung off the stall post. A lit rectangle on a stick reads as
         a tankard, so it gets a cap, a base and bars. -->
    <path d="M84 16 v6" stroke="${g.rim}" stroke-width="1.4"/>
    <circle cx="84" cy="14.5" r="2.4" fill="none" stroke="${g.rim}" stroke-width="1.4"/>
    <path d="M78 22 h12 l-1.6 4 h-8.8 z" fill="${g.ink}" stroke="${g.rim}"
      stroke-opacity=".5"/>
    <g filter="url(#${GLOW_SOFT})">
      <rect x="79" y="26" width="10" height="13" rx="1.5" fill="${g.glow}" opacity=".9"/>
      <circle cx="84" cy="32" r="11" fill="${g.glow}" opacity=".13"/>
    </g>
    <path d="M82 26 v13 M86 26 v13" stroke="${g.ink}" stroke-width="1" opacity=".5"/>
    <path d="M77.6 39 h12.8 l-1.6 3.4 h-9.6 z" fill="${g.ink}" stroke="${g.rim}"
      stroke-opacity=".5"/>`, px);
}

/* ── the chest ─────────────────────────────────────────────── */

export function chestScene(px = 140): string {
  const g = RAMPS.regal;
  const coin = (x: number, y: number, r: number) =>
    `<ellipse cx="${x}" cy="${y}" rx="${r}" ry="${r * 0.45}" fill="${g.glow}"/>`;

  return svg("scene-chest", `
    <ellipse cx="50" cy="88" rx="34" ry="7" fill="#000" opacity=".4"/>
    <g filter="url(#${GLOW_SOFT})">
      <ellipse cx="50" cy="60" rx="26" ry="16" fill="${g.glow}" opacity=".18"/>
    </g>
    <!-- lid, thrown back -->
    <path d="M26 54 q24 -22 48 0 l0 6 q-24 -18 -48 0 z" fill="url(#${bodyGrad("regal")})"
      stroke="${g.rim}" stroke-opacity=".6" stroke-width="1.4"/>
    <path d="M24 60 h52 v26 H24 z" fill="url(#${bodyGrad("regal")})"
      stroke="${g.rim}" stroke-opacity=".6" stroke-width="1.6"/>
    <path d="M24 60 h52 v26 H24 z" fill="url(#${INNER_SHADE})"/>
    <path d="M24 70 h52" stroke="${g.ink}" stroke-width="3"/>
    <rect x="45" y="66" width="10" height="12" rx="2" fill="${g.rim}"/>
    <circle cx="50" cy="72" r="2" fill="${g.ink}"/>
    <g opacity=".95">${coin(34, 62, 5)}${coin(44, 59, 4.4)}${coin(60, 61, 5)}
      ${coin(68, 63, 4)}</g>`, px);
}

/* ── the unknown ───────────────────────────────────────────── */

/** A watching sigil: the event screen's "?" was doing a lot of work alone. */
export function omenScene(px = 130): string {
  const sp = RAMPS.spectre;
  const runes = Array.from({ length: 12 }, (_, i) => {
    const a = (i / 12) * Math.PI * 2;
    const x = 50 + Math.cos(a) * 32;
    const y = 52 + Math.sin(a) * 32;
    return `<path d="M${x} ${y - 3} v6" stroke="${sp.rim}" stroke-width="2"
      stroke-linecap="round" opacity="${(0.3 + (i % 3) * 0.25).toFixed(2)}"
      transform="rotate(${Math.round((a * 180) / Math.PI) + 90} ${x} ${y})"/>`;
  }).join("");

  return svg("scene-omen", `
    <circle cx="50" cy="52" r="32" fill="none" stroke="${sp.shade}"
      stroke-width="1.2" stroke-dasharray="4 6" opacity=".7"/>
    ${runes}
    <g filter="url(#${GLOW_SOFT})">
      <path d="M22 52 q28 -24 56 0 q-28 24 -56 0 z" fill="${sp.ink}"
        stroke="${sp.rim}" stroke-width="1.8"/>
      <circle cx="50" cy="52" r="9" fill="${sp.shade}"/>
      <circle class="rig-eye" cx="50" cy="52" r="5" fill="${sp.glow}"/>
    </g>`, px);
}

/* ── the two endings ───────────────────────────────────────── */

/** Won: the peak, crowned and lit. Lost: the fire the player was. */
export function endingScene(won: boolean, px = 160): string {
  const g = RAMPS.regal;
  const a = RAMPS.ash;

  if (won) {
    // The crown sits above the peak, not on it: overlapping the tip put gold
    // on gold inside the halo and the crown simply disappeared.
    return svg("scene-win", `
      <g filter="url(#${GLOW_SOFT})">
        <ellipse cx="50" cy="56" rx="28" ry="22" fill="${g.glow}" opacity=".13"/>
      </g>
      <path d="M50 30 L74 88 H26 z" fill="url(#${bodyGrad("regal")})"
        stroke="${g.rim}" stroke-opacity=".55" stroke-width="1.5"/>
      <path d="M50 30 L74 88 H26 z" fill="url(#${INNER_SHADE})"/>
      <path d="M36 70 h28 M40 80 h20" stroke="${g.ink}" stroke-width="2" opacity=".5"/>
      <g filter="url(#${GLOW_HARD})">
        <path d="M38 22 l4 -12 l4 7.5 l4 -13 l4 13 l4 -7.5 l4 12 z" fill="${g.glow}"/>
        <path d="M38 22 h24" stroke="${g.glow}" stroke-width="3" stroke-linecap="round"/>
      </g>`, px);
  }

  return svg("scene-lost", `
    <ellipse cx="50" cy="86" rx="30" ry="8" fill="#000" opacity=".45"/>
    <path d="M24 86 q10 -16 26 -16 q16 0 26 16 z" fill="${a.ink}"
      stroke="${a.rim}" stroke-opacity=".35" stroke-width="1.4"/>
    <path d="M24 86 q10 -16 26 -16 q16 0 26 16 z" fill="url(#${INNER_SHADE})"/>
    <!-- one ember left in the ash, and the smoke off it -->
    <g filter="url(#${GLOW_SOFT})">
      <circle class="rig-eye" cx="50" cy="76" r="3" fill="${a.glow}" opacity=".9"/>
    </g>
    <path d="M50 70 q-7 -10 0 -18 q7 -8 1 -18" stroke="${a.rim}" stroke-width="1.8"
      fill="none" opacity=".55"/>
    <g class="rig-ember" opacity=".5">
      <circle cx="40" cy="60" r="1.2" fill="${a.glow}"/>
      <circle cx="61" cy="52" r="1" fill="${a.glow}"/>
      <circle cx="56" cy="66" r="0.9" fill="${a.glow}"/>
    </g>`, px);
}
