/**
 * Hand-written mirror of `spire_of_ash/web/dto.py:view()`.
 *
 * This is the one place the client's idea of the payload and the server's are
 * reconciled. If a field moves in dto.py, it moves here, and tsc points at
 * every call site that cared.
 */

export type Screen =
  | "select" | "map" | "combat" | "reward" | "choose" | "rest"
  | "shop" | "event" | "treasure" | "gameover" | "win";

export type CardType = "ATTACK" | "SKILL" | "POWER" | "STATUS" | "CURSE";

export interface UpgradePreview {
  name: string;
  cost: number | "X";
  desc: string;
}

export interface CardView {
  /** Hand index, or null outside a hand. */
  i: number | null;
  /** Per-instance id — stable across renders, so a card can be animated
   *  from hand to target to discard. Added in dto.card_data. */
  uid: number;
  key: string;
  name: string;
  type: CardType;
  cost: number | "X";
  desc: string;
  upgraded: boolean;
  playable: boolean;
  targeted: boolean;
  requires: string | null;
  needs_hand: boolean;
  /** Deck view and the upgrade picker only. */
  up?: UpgradePreview | null;
  /** Shop only. */
  price?: number;
}

export interface StatusView {
  key: string;
  label: string;
  value: number;
  name: string;
  desc: string;
}

export interface RelicView { key: string; name: string; desc: string }
export interface PotionView {
  key: string; name: string; desc: string; targeted: boolean; price?: number;
}

export type IntentKind = "attack" | "block" | "buff" | "debuff";

export interface IntentView {
  kind: IntentKind;
  /** The move's own name. */
  name: string;
  note: string;
  /** Attack intents only. Already adjusted for the state the blow lands in
   *  — see Enemy.intent_preview in engine/combatant.py. */
  dmg?: number;
  damage?: number;
  hits?: number;
  extra?: boolean;
}

export interface EnemyView {
  /** Content id (jaw_worm, hexaghost, …). Sprites key off this, not `name`. */
  key: string;
  name: string;
  hp: number;
  max_hp: number;
  block: number;
  alive: boolean;
  statuses: StatusView[];
  intent: IntentView | null;
}

export interface PlayerView {
  name: string;
  cls: string;
  hp: number;
  max_hp: number;
  block: number;
  gold: number;
  deck_size: number;
  statuses: StatusView[];
  relics: RelicView[];
  potions: PotionView[];
  max_potions: number;
  energy: number;
  max_energy: number;
}

export interface CombatView {
  label: string;
  kind: "monster" | "elite" | "boss";
  turn: number;
  energy: number;
  enemies: EnemyView[];
  hand: CardView[];
  draw: number;
  discard: number;
  exhaust: number;
  log: string[];
  /** Ordered effect timeline for the action just applied. Phase 1. */
  fx?: FxEvent[];
}

/* ── the effect stream (engine/combat.py emit()) ───────────── */

/** "player", or an index into combat.enemies. */
export type Who = "player" | number;

export type FxEvent =
  | { k: "log"; text: string }
  | { k: "turn"; phase: "player_start" | "player_end" | "enemy_start" }
  | { k: "act"; who: number; move: string }
  | { k: "act_end"; who: number }
  | { k: "play"; uid: number; key: string; target: number | null }
  | { k: "swing"; src: Who; dst: Who }
  | { k: "damage"; who: Who; amount: number; blocked: number; hp: number }
  | { k: "block"; who: Who; amount: number; total: number }
  | { k: "heal"; who: Who; amount: number }
  | { k: "lose_hp"; who: Who; amount: number }
  | { k: "status"; who: Who; key: string; n: number }
  | { k: "death"; who: number }
  | { k: "draw"; n: number }
  | { k: "discard"; uid: number }
  | { k: "exhaust"; uid: number };

/* ── screen payloads ───────────────────────────────────────── */

export interface MapNode { type: NodeKind; edges: number[] }
export type NodeKind =
  "monster" | "elite" | "event" | "rest" | "shop" | "treasure" | "boss";

export interface MapView {
  floors: MapNode[][];
  cur_floor: number;
  cur_idx: number;
  visited: [number, number][];
  reachable: number[];
}

export interface ClassView {
  key: string; name: string; hp: number; energy: number; blurb: string;
  deck: string[]; relic: RelicView; cards: number;
}

export interface RewardView {
  gold: number;
  kind: "monster" | "elite" | "boss";
  log: string[];
  relic: RelicView | null;
  potion: PotionView | null;
  cards: CardView[];
  relic_taken: boolean;
  potion_taken: boolean;
  card_taken: boolean;
  potions_full: boolean;
}

export interface ChooseView {
  kind: "upgrade" | "remove" | "duplicate";
  title: string;
  back: string;
  allow_skip: boolean;
  cards: CardView[];
}

export interface ShopView {
  relic_price: number;
  removal_price: number;
  removed: boolean;
  cards: CardView[];
  relic: RelicView | null;
  potions: PotionView[];
}

export interface EventOption { label: string; preview: string }

export interface EventView {
  title: string;
  text: string;
  options: EventOption[];
  result: string | null;
  then: string | null;
}

export interface TreasureView { gold: number; relic: RelicView }

export interface State {
  screen: Screen;
  act: number;
  floor: number;
  floors_cleared: number;
  elites_killed: number;
  banner: [string, string] | null;
  killer: string | null;
  pending: { kind: string; [k: string]: unknown } | null;
  seed: number;
  player: PlayerView;
  deck: CardView[];
  map: MapView;
  classes?: ClassView[];
  combat?: CombatView;
  reward?: RewardView;
  choose?: ChooseView;
  shop?: ShopView;
  event?: EventView;
  treasure?: TreasureView;
}

export interface Piles {
  draw_pile: CardView[];
  discard_pile: CardView[];
  exhaust_pile: CardView[];
}

export interface RecordView {
  act: number; floors: number; won: boolean; killer: string;
  deck: number; gold: number; cls: string;
}

/* ── actions the client can send ───────────────────────────── */

export type Action =
  | { type: "new_run"; cls?: string; daily?: boolean; seed?: number }
  | { type: "map"; idx: number }
  | { type: "play"; idx: number; target: number | null; exhaust: number | null }
  | { type: "potion"; idx: number; target: number | null }
  | { type: "end_turn" }
  | { type: "reward"; what: "card" | "relic" | "potion"; idx?: number }
  | { type: "reward_done" }
  | { type: "choose"; idx: number | null }
  | { type: "rest" } | { type: "smith" } | { type: "purge" }
  | { type: "shop_buy"; what: "card" | "relic" | "potion" | "removal"; idx?: number }
  | { type: "shop_leave" }
  | { type: "event_choose"; idx: number }
  | { type: "event_done" }
  | { type: "treasure_done" };
