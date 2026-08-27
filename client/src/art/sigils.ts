/**
 * Relic sigils, potion vials and card emblems.
 *
 * These sit at 24–29px, so they are drawn as bold single-read glyphs rather
 * than little illustrations: at that size, detail is noise. Like the
 * bestiary, they share a vocabulary — relics are line-drawn objects in old
 * gold, potions are one vial silhouette with different contents, and card
 * emblems are the watermark behind the rules text.
 *
 * Keys are content ids, checked against the Python tables by the build
 * manifest.
 */

const GOLD = "#e0b978";
const DIM = "#a9803c";
const BLOOD = "#c8503f";
const EMBER = "#ff8a3c";
const LEAF = "#77c97c";
const SKY = "#84bce3";
const VIOLET = "#a97bd8";
const BONE = "#d6cbb4";

const svg = (inner: string, stroke = GOLD) =>
  `<svg viewBox="0 0 24 24" width="100%" height="100%" fill="none"
     stroke="${stroke}" stroke-width="1.6" stroke-linecap="round"
     stroke-linejoin="round" aria-hidden="true">${inner}</svg>`.replace(/\s+/g, " ");

/* ── relics ────────────────────────────────────────────────── */

const RELIC: Record<string, string> = {
  burning_blood: svg(`<path d="M12 3 C7 9 5 12 5 15 a7 7 0 0 0 14 0 c0-3-2-6-7-12z"/>
    <path d="M12 12 v5" stroke="${EMBER}"/>`, BLOOD),
  bag_of_marbles: svg(`<path d="M4 14 h16 l-2 6 H6z"/><circle cx="9" cy="8" r="3"/>
    <circle cx="15" cy="10" r="2.4"/>`),
  anchor: svg(`<circle cx="12" cy="5" r="2.2"/><path d="M12 7 v12"/>
    <path d="M6 13 a6 6 0 0 0 12 0"/><path d="M8 10 h8"/>`),
  vajra: svg(`<path d="M12 3 v18"/><path d="M8 6 l4 -3 l4 3"/><path d="M8 18 l4 3 l4 -3"/>
    <path d="M6 12 h12"/>`),
  oddly_smooth_stone: svg(`<ellipse cx="12" cy="13" rx="8" ry="6.5"/>
    <path d="M8 10 a5 4 0 0 1 5 -2" stroke-opacity=".6"/>`),
  bronze_scales: svg(`<path d="M12 4 v14"/><path d="M5 8 h14"/>
    <path d="M5 8 l-2 5 h4z"/><path d="M19 8 l-2 5 h4z"/><path d="M8 20 h8"/>`),
  blood_vial: svg(`<path d="M10 3 h4 v5 l3 8 a5 5 0 0 1 -10 0 l3 -8z"/>
    <path d="M8 15 h8" stroke="${BLOOD}"/>`, BLOOD),
  lantern: svg(`<path d="M9 4 h6"/><path d="M7 8 h10 v9 H7z"/><path d="M10 20 h4"/>
    <circle cx="12" cy="12.5" r="2.4" stroke="${EMBER}"/>`),
  happy_flower: svg(`<circle cx="12" cy="10" r="2.6"/>
    <path d="M12 4 v3 M12 13 v3 M6 10 h3 M15 10 h3 M8 6 l2 2 M16 6 l-2 2 M8 14 l2-2 M16 14 l-2-2"/>
    <path d="M12 16 v5" stroke="${LEAF}"/>`),
  pen_nib: svg(`<path d="M12 3 l5 12 l-5 6 l-5 -6z"/><path d="M12 9 v8"/>
    <circle cx="12" cy="14" r="1.4"/>`),
  strawberry: svg(`<path d="M12 8 c5 0 7 3 7 6 a7 6 0 0 1 -14 0 c0-3 2-6 7-6z"/>
    <path d="M9 6 h6 M12 4 v3"/>`, BLOOD),
  meat_on_bone: svg(`<path d="M7 8 a5 5 0 0 1 8 2 l3 3"/><circle cx="19" cy="14" r="2"/>
    <path d="M6 7 a3 3 0 1 0 1 5"/>`),
  kunai: svg(`<path d="M12 2 l3 7 l-3 9 l-3 -9z"/><path d="M12 18 v4"/>
    <path d="M9 20 h6"/>`),
  bag_of_prep: svg(`<path d="M6 9 h12 l-1.5 11 H7.5z"/><path d="M9 9 a3 3 0 0 1 6 0"/>
    <path d="M8 14 h8" stroke-opacity=".6"/>`),
  art_of_war: svg(`<path d="M6 4 h12 v16 H6z"/><path d="M9 8 h6 M9 12 h6 M9 16 h4"/>`),
  ash_phial: svg(`<path d="M9 3 h6 v4 l2 10 a4 4 0 0 1 -10 0 l2 -10z"/>
    <path d="M9 15 h6" stroke="${EMBER}"/>`, EMBER),
  emberheart: svg(`<path d="M12 20 C5 15 4 10 7 7 a4 4 0 0 1 5 1 a4 4 0 0 1 5 -1 c3 3 2 8 -5 13z"/>
    <path d="M12 9 v5" stroke="${EMBER}"/>`, EMBER),
  ashglass_vial: svg(`<path d="M8 3 h8 l-2 7 l2 11 H8 l2 -11z"/>
    <path d="M10 17 h4" stroke="${EMBER}"/>`),
  smoulder_stone: svg(`<path d="M5 15 l4 -8 l6 -2 l4 7 l-3 6 H7z"/>
    <path d="M11 11 l2 3 l-1 3" stroke="${EMBER}"/>`),
  grave_ash: svg(`<path d="M8 5 h8 l2 15 H6z"/><path d="M12 8 v6 M9 11 h6"/>`),
  bone_dice: svg(`<path d="M5 8 l7 -4 l7 4 v8 l-7 4 l-7 -4z"/>
    <circle cx="12" cy="11" r="1" fill="${BONE}" stroke="none"/>
    <circle cx="9" cy="14" r="1" fill="${BONE}" stroke="none"/>
    <circle cx="15" cy="14" r="1" fill="${BONE}" stroke="none"/>`, BONE),
  oathkeeper: svg(`<path d="M10 20 h4"/><path d="M12 20 v-8"/>
    <path d="M12 12 c-3 -2 -1 -6 0 -8 c1 2 3 6 0 8z" stroke="${EMBER}"/>`),
  hollow_lantern: svg(`<path d="M9 4 h6"/><path d="M7 8 h10 v9 H7z"/><path d="M10 20 h4"/>
    <path d="M10 11 l4 4 M14 11 l-4 4" stroke-opacity=".7"/>`, VIOLET),
  // class starter relics — drawn in the colour of the resource each plays around
  storm_cell: svg(`<path d="M6 6 h12 v12 H6z"/><path d="M13 8 l-4 5 h3 l-2 4 l5 -6 h-3z"
    stroke="${SKY}"/>`, SKY),
  prayer_bead: svg(`<circle cx="12" cy="12" r="7"/><circle cx="12" cy="5" r="1.6"/>
    <circle cx="19" cy="12" r="1.6"/><circle cx="12" cy="19" r="1.6"/>
    <circle cx="5" cy="12" r="1.6"/>`),
  gravebell: svg(`<path d="M7 17 a5 6 0 0 1 10 0z"/><path d="M5 17 h14"/>
    <path d="M12 6 v5"/><circle cx="12" cy="5" r="1.4"/>
    <circle cx="12" cy="19" r="1.2"/>`),
  cracked_alembic: svg(`<path d="M9 3 h6 v4 l3 10 a4 4 0 0 1 -12 0 l3 -10z"/>
    <path d="M10 12 l2 3 l-1 3" stroke="${LEAF}"/>`, LEAF),
  hexing_thread: svg(`<path d="M6 6 q6 4 12 0 q-4 6 0 12 q-6 -4 -12 0 q4 -6 0 -12z"
    stroke="${VIOLET}"/><circle cx="12" cy="12" r="1.4" stroke="${VIOLET}"/>`, VIOLET),
};

/* ── potions ───────────────────────────────────────────────── */

/** One vial silhouette, different contents — so a potion always reads as a
 *  potion before it reads as which potion. */
function vial(fill: string, motif = ""): string {
  return `<svg viewBox="0 0 24 24" width="100%" height="100%" aria-hidden="true">
    <path d="M9.5 3 h5 v5.5 l3.2 8.2 a5.7 5.7 0 0 1 -11.4 0 L9.5 8.5z"
      fill="#0f0b17" stroke="${DIM}" stroke-width="1.5"/>
    <path d="M7.6 14 a5.7 5.7 0 0 0 8.8 3.9 a5.7 5.7 0 0 0 1.4 -1.2 l-1.5 -3.9z"
      fill="${fill}" opacity=".85"/>
    <path d="M8.6 2.4 h6.8" stroke="${GOLD}" stroke-width="1.8" stroke-linecap="round"/>
    ${motif}</svg>`.replace(/\s+/g, " ");
}

const POTION: Record<string, string> = {
  fire: vial(EMBER, `<path d="M12 13 c-1.6 -1.2 -.5 -3.2 0 -4.2 c.5 1 1.6 3 0 4.2z"
    fill="#ffd08a"/>`),
  block: vial(SKY, `<path d="M12 11 l3 1.2 v2.2 c0 1.6 -1.6 2.6 -3 3.1 c-1.4 -.5 -3 -1.5 -3 -3.1
    v-2.2z" fill="#cfeaff" opacity=".9"/>`),
  strength: vial(BLOOD, `<path d="M9.5 15 h5 M12 12.5 v5" stroke="#ffc0b0"
    stroke-width="1.8" stroke-linecap="round"/>`),
  energy: vial(GOLD, `<path d="M12.8 11 l-2.6 4 h2 l-.8 3 l2.8 -4.2 h-2z" fill="#fff0c8"/>`),
  swift: vial(LEAF, `<path d="M8.6 14.4 h5 M9.6 16.4 h4.4 M10.6 18.2 h3"
    stroke="#d8ffe4" stroke-width="1.5" stroke-linecap="round"/>`),
  explosive: vial(EMBER, `<path d="M12 11 l1.2 2.4 l2.4 -.6 l-1.4 2.2 l1.4 2.2 l-2.4 -.6
    l-1.2 2.4 l-1.2 -2.4 l-2.4 .6 l1.4 -2.2 l-1.4 -2.2 l2.4 .6z" fill="#ffd08a"/>`),
  weak: vial(VIOLET, `<path d="M9 15.5 q3 -2.4 6 0 q-3 2.4 -6 0z" fill="#e2c8ff"/>`),
  fear: vial(VIOLET, `<circle cx="10.4" cy="14.6" r="1.1" fill="#f0dcff"/>
    <circle cx="13.6" cy="14.6" r="1.1" fill="#f0dcff"/>
    <path d="M10 17.6 q2 -1.6 4 0" stroke="#f0dcff" stroke-width="1.3" fill="none"/>`),
  blood: vial(BLOOD, `<path d="M12 11.6 c-1.8 2 -2.6 3.2 -2.6 4.2 a2.6 2.6 0 0 0 5.2 0
    c0-1 -.8-2.2 -2.6-4.2z" fill="#ff9c8a"/>`),
};

/* ── card emblems ──────────────────────────────────────────── */

/**
 * The watermark behind a card's rules text.
 *
 * Assigned by what the card *does* rather than one drawing per card: 74 cards
 * share about twenty motifs, and a player learns "this shape means poison"
 * far faster than 74 separate pictures.
 */
const EMBLEM: Record<string, string> = {
  blade: `<path d="M12 2 l3 13 l-3 7 l-3 -7z"/><path d="M8 19 h8"/>`,
  cleave: `<path d="M3 6 q9 4 18 0"/><path d="M3 12 q9 4 18 0"/><path d="M3 18 q9 4 18 0"/>`,
  shield: `<path d="M12 2 l9 4 v7 c0 5 -5 8 -9 9 c-4 -1 -9 -4 -9 -9 V6z"/>`,
  fist: `<path d="M5 11 a4 4 0 0 1 8 0 h4 a3 3 0 0 1 0 6 H8 a3 3 0 0 1 -3 -3z"/>
    <path d="M8 11 V7 a2 2 0 0 1 4 0v4"/>`,
  flame: `<path d="M12 2 C7 9 5 12 5 15 a7 7 0 0 0 14 0 c0-3-2-6-7-13z"/>
    <path d="M12 12 c-2 2 -2 5 0 6 c2-1 2-4 0-6z"/>`,
  venom: `<path d="M12 3 l7 5 v8 l-7 5 l-7 -5 V8z"/><circle cx="12" cy="12" r="2.6"/>
    <path d="M12 6 v2 M12 16 v2"/>`,
  cloak: `<path d="M12 3 l7 6 l-3 12 H8 L5 9z"/><path d="M9 9 q3 3 6 0"/>`,
  bolt: `<path d="M13 2 L5 13 h5 l-2 9 l9 -12 h-5z"/>`,
  eye: `<path d="M2 12 q10 -8 20 0 q-10 8 -20 0z"/><circle cx="12" cy="12" r="3"/>`,
  chain: `<path d="M9 8 a4 4 0 0 1 6 6"/><path d="M15 16 a4 4 0 0 1 -6 -6"/>`,
  skull: `<path d="M12 3 a8 8 0 0 1 8 8 v4 h-4 l-1 4 h-6 l-1 -4 H4 v-4 a8 8 0 0 1 8 -8z"/>
    <circle cx="9" cy="11" r="1.8"/><circle cx="15" cy="11" r="1.8"/>`,
  wings: `<path d="M12 6 q-9 -3 -10 6 q6 1 10 -2z"/><path d="M12 6 q9 -3 10 6 q-6 1 -10 -2z"/>`,
  ash: `<path d="M12 3 v18 M5 8 l14 8 M19 8 L5 16"/><circle cx="12" cy="12" r="2.4"/>`,
  heart: `<path d="M12 21 C4 15 3 9 6.5 6 a4.5 4.5 0 0 1 5.5 1 a4.5 4.5 0 0 1 5.5 -1
    C21 9 20 15 12 21z"/>`,
  bomb: `<circle cx="11" cy="15" r="6"/><path d="M15 9 l3 -3"/><path d="M18 6 l2 -1 l-1 2"/>`,
  curse: `<circle cx="12" cy="12" r="8"/><path d="M7 7 l10 10 M17 7 L7 17"/>`,
};

/** Which motif a card gets. Falls back to its type's default. */
const CARD_EMBLEM: Record<string, keyof typeof EMBLEM> = {
  strike: "blade", bash: "fist", cleave: "cleave", twin_strike: "blade",
  pommel_strike: "fist", iron_wave: "shield", clothesline: "chain",
  body_slam: "shield", uppercut: "fist", heavy_blade: "blade",
  whirlwind: "cleave", bludgeon: "fist", reaper: "skull", crushing_blow: "fist",
  quick_slash: "blade", slice_and_dice: "cleave", blade_dance: "blade",
  dagger_spray: "cleave", flying_knee: "blade", grand_finale: "flame",
  a_thousand_cuts: "cleave", sneak_attack: "cloak", flechettes: "blade",
  bane: "skull", vial_toss: "bomb", bouncing_flask: "bomb",
  toxic_vial: "venom", deadly_poison: "venom", poison_stab: "venom",
  venom_dagger: "venom", crippling_cloud: "venom", nightmare_toxin: "venom",
  envenom: "venom", venom_bloom: "venom", catalyst: "venom", caltrops: "venom",
  defend: "shield", shrug_it_off: "shield", impervious: "shield",
  barricade: "shield", ember_shield: "shield", dodge_roll: "shield",
  backflip: "shield", footwork: "wings", acrobatics: "wings",
  escape_plan: "wings", after_image: "wings", shadowstep: "cloak",
  cloak: "cloak", smoke_bomb: "cloak", well_laid_plans: "eye",
  flex: "fist", inflame: "flame", demon_form: "flame", limit_break: "flame",
  seeing_red: "bolt", battle_trance: "bolt", offering: "heart",
  bloodletting: "heart", true_grit: "heart", second_wind: "wings",
  armaments: "shield", disarm: "chain", shockwave: "bolt",
  metallicize: "shield", feel_no_pain: "shield", juggernaut: "fist",
  rupture: "heart", unyielding: "shield", cinder_dart: "flame",
  wound: "curse", burn: "flame", slimed: "curse", regret: "curse",
};

const TYPE_EMBLEM: Record<string, keyof typeof EMBLEM> = {
  ATTACK: "blade", SKILL: "shield", POWER: "ash", STATUS: "curse", CURSE: "curse",
};

/* ── public ────────────────────────────────────────────────── */

export const relicSigil = (key: string) => RELIC[key] ?? null;
export const potionSigil = (key: string) => POTION[key] ?? null;

export function cardEmblem(key: string, type: string): string {
  const motif = CARD_EMBLEM[key] ?? TYPE_EMBLEM[type] ?? "ash";
  return `<svg class="cemblem" viewBox="0 0 24 24" fill="none" stroke="currentColor"
     stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"
     aria-hidden="true">${EMBLEM[motif]}</svg>`.replace(/\s+/g, " ");
}

export const RELIC_KEYS = Object.keys(RELIC);
export const POTION_KEYS_ART = Object.keys(POTION);
