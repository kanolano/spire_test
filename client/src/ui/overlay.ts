/** The modal: deck, relics, piles, help, and the quit confirmation. */

import { abandon } from "../actions";
import { intentMark, shieldMark } from "../art/marks";
import { $, el, esc } from "../dom";
import { ApiError, getPiles, toast } from "../net";
import { S } from "../store";
import type { CardView } from "../types";
import { cardEl, withUpgrade } from "./card";
import { hideTip } from "./tooltip";

let overlayReturn: HTMLElement | null = null;   // focus goes back where it came from
let overlayConfirm: (() => void) | null = null; // set while asking a yes/no

export const overlayOpen = () => $("#overlay").classList.contains("on");
export const pendingConfirm = () => overlayConfirm;

/**
 * Bumped every time the modal's contents are replaced or it is dismissed.
 * `showPile` fetches, so by the time it can write, the player may have closed
 * the modal or asked it a different question; comparing generations is how a
 * late answer knows it is answering nobody.
 */
let overlayGen = 0;
export const overlayGeneration = () => overlayGen;

export function showOverlay() {
  overlayGen++;
  hideTip();
  overlayReturn = overlayOpen()
    ? overlayReturn
    : (document.activeElement as HTMLElement | null);
  $("#overlay").classList.add("on");
  $("#overlay .close").focus();
}

export function closeOverlay() {
  overlayGen++;
  $("#overlay").classList.remove("on");
  overlayReturn?.focus?.();
  overlayReturn = null;
  overlayConfirm = null;
}

export function openOverlay(
  title: string, cards: CardView[], note?: string, upgrades?: boolean,
) {
  const b = $("#overlay-body");
  b.innerHTML = "";
  b.appendChild(el("h2", "title", esc(title)));
  $("#overlay-title").textContent = title;
  if (note) b.appendChild(el("div", "sub", esc(note)));
  const row = el("div", "row");
  for (const c of cards) {
    const card = cardEl(c, { static: true });
    row.appendChild(upgrades && c.up ? withUpgrade(card, c, null) : card);
  }
  b.appendChild(row);
  showOverlay();
}

export function showDeck() {
  const deck = S().deck;
  const upgradable = deck.filter((c) => c.up).length;
  openOverlay(
    `Your deck — ${deck.length} cards`, deck,
    (upgradable
      ? `${upgradable} can still be upgraded — each is shown with what it becomes. `
      : "") + "Relics: " + S().player.relics.map((r) => r.name).join(", "),
    true,
  );
}

export function showRelics() {
  const b = $("#overlay-body");
  b.innerHTML = "";
  b.appendChild(el("h2", "title", "Your relics"));
  $("#overlay-title").textContent = "Your relics";
  for (const r of S().player.relics) {
    b.appendChild(el("div", "item",
      `<span class="nm">${esc(r.name)}</span><span class="ds">${esc(r.desc)}</span>`));
  }
  showOverlay();
}

const PILE_TITLES: Record<string, string> = {
  draw_pile: "Draw pile", discard_pile: "Discard pile", exhaust_pile: "Exhausted",
};

/** Pile contents are fetched on demand rather than riding along with every
 *  single state response. */
export async function showPile(k: string) {
  const title = PILE_TITLES[k] ?? "Pile";
  openOverlay(title, [], "Loading…");
  const mine = overlayGeneration();
  try {
    const piles = await getPiles();
    if (overlayGeneration() !== mine) return;   // closed, or showing something else
    const pile = (piles as unknown as Record<string, CardView[]>)[k] ?? [];
    openOverlay(`${title} — ${pile.length} cards`, pile,
      k === "draw_pile" ? "Sorted; the real draw order is hidden." : "");
  } catch (e) {
    if (overlayGeneration() !== mine) return;
    toast(e instanceof ApiError ? e.message : "Could not reach the Spire.");
    closeOverlay();
  }
}

export function showHelp() {
  $("#overlay-title").textContent = "How to play";
  $("#overlay-body").innerHTML = `
    <h2 class="title">How to play</h2>
    <div style="max-width:660px;margin:16px auto;line-height:1.8">
      <p>Click a card to play it, or press its number. Cards cost <b>Energy</b> (the orb);
         you get 3 per turn. <kbd>E</kbd> ends the turn — your hand is discarded and the
         enemies act.</p>
      <p><b>Block</b> ${shieldMark()} absorbs damage and disappears at the start of your next turn.
         An enemy's intent shows what it will do: ${intentMark("attack")} is the damage
         you would take,
         already adjusted for your statuses.</p>
      <p>Targeted cards ask you to click an enemy (or press <kbd>a</kbd>–<kbd>d</kbd>).
         Potions are the chips in the top-right: click them or press
         <kbd>q</kbd> <kbd>w</kbd> <kbd>r</kbd>.</p>
      <p>The small chips on you and on each enemy are <b>statuses</b>. Hover one —
         or tap it on a phone — and it will tell you exactly what it does. Relics
         and potions in the top bar work the same way.</p>
      <p class="ghost">Keys: <kbd>1</kbd>–<kbd>9</kbd> cards or options ·
        <kbd>E</kbd> end turn · <kbd>a</kbd>–<kbd>d</kbd> target / path ·
        <kbd>i</kbd> deck · <kbd>Esc</kbd> cancel · <kbd>Enter</kbd> continue</p>
    </div>`;
  showOverlay();
}

export function confirmQuit() {
  const st = S();
  if (st.screen === "select") return;
  const ending = st.screen === "gameover" || st.screen === "win";
  $("#overlay-title").textContent = "Abandon this climb";
  const body = $("#overlay-body");
  body.innerHTML = "";
  body.appendChild(el("h2", "title",
    ending ? "Choose another class" : "Abandon this climb?"));
  body.appendChild(el("div", "sub", ending
    ? "You will go back to the character select."
    : `You are on floor ${st.floor} of act ${st.act}. The run ends here, is not `
      + `recorded, and you go back to the character select.`));
  const box = el("div", "choices");
  const yes = el("button", "choice",
    `<span class="k">1</span> <b>${ending ? "Pick a class" : "Abandon the run"}</b>`);
  yes.onclick = () => { closeOverlay(); void abandon(); };
  const no = el("button", "choice",
    `<span class="k">esc</span> <b>${ending ? "Stay here" : "Keep climbing"}</b>`);
  no.onclick = closeOverlay;
  box.appendChild(yes);
  box.appendChild(no);
  body.appendChild(box);
  overlayConfirm = abandon;
  showOverlay();
}
