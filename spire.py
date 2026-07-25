"""Spire of Ash — a Slay the Spire-like deckbuilding roguelike for the terminal.

Stdlib only. Run with:  python3 spire.py
"""
import json
import os
import random
import shutil
import sys
from collections import defaultdict

SAVE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "spire_save.json")

# ─────────────────────────────────────────────────────────────── presentation ──
ESC = "\033["
RESET = ESC + "0m"
BOLD, DIM = 1, 2


def c(text, *codes):
    return "".join(ESC + str(x) + "m" for x in codes) + str(text) + RESET


RED, GRN, YEL, BLU, MAG, CYN, WHT, GRY = 31, 32, 33, 34, 35, 36, 37, 90

TYPE_COLOR = {"ATTACK": RED, "SKILL": CYN, "POWER": MAG, "CURSE": GRY, "STATUS": GRY}


def clear():
    sys.stdout.write(ESC + "2J" + ESC + "H")


def term_width():
    return max(60, shutil.get_terminal_size((100, 30)).columns)


def bar(cur, mx, width=14, color=GRN):
    cur = max(0, cur)
    filled = 0 if mx <= 0 else int(round(width * cur / mx))
    filled = min(width, filled)
    return c("█" * filled, color) + c("░" * (width - filled), GRY)


def wrap(text, width):
    words, lines, cur = text.split(), [], ""
    for w in words:
        if len(cur) + len(w) + (1 if cur else 0) <= width:
            cur += (" " if cur else "") + w
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def prompt(msg):
    try:
        return input(msg).strip()
    except (EOFError, KeyboardInterrupt):
        print()
        sys.exit(0)


def pause(msg="  [enter] "):
    prompt(c(msg, GRY))


# ────────────────────────────────────────────────────────────────── statuses ──
STATUS_INFO = {
    "strength": ("Str", RED),
    "dexterity": ("Dex", GRN),
    "vulnerable": ("Vuln", MAG),
    "weak": ("Weak", BLU),
    "frail": ("Frail", BLU),
    "poison": ("Psn", GRN),
    "thorns": ("Thorns", YEL),
    "ritual": ("Ritual", RED),
    "metallicize": ("Metal", CYN),
    "demonform": ("Demon", RED),
    "barricade": ("Barri", CYN),
    "feelnopain": ("NoPain", CYN),
    "rupture": ("Rupt", RED),
    "juggernaut": ("Jugg", YEL),
    "flexloss": ("", 0),
    "asleep": ("Asleep", GRY),
}
# statuses that tick down at the end of the owner's turn
DECAYING = ("vulnerable", "weak", "frail")
DEBUFFS = ("vulnerable", "weak", "frail", "poison")


class Combatant:
    def __init__(self, name, hp):
        self.name = name
        self.max_hp = hp
        self.hp = hp
        self.block = 0
        self.st = defaultdict(int)
        self.alive = True

    def s(self, key):
        return self.st[key]

    def status_line(self):
        parts = []
        for k, v in self.st.items():
            if v == 0 or not STATUS_INFO.get(k, ("", 0))[0]:
                continue
            label, col = STATUS_INFO[k]
            parts.append(c(f"{label} {v}", col))
        return " ".join(parts)


# ───────────────────────────────────────────────────────────────────── cards ──
class Card:
    def __init__(self, key):
        d = CARDS[key]
        self.key = key
        self.base_name = d["name"]
        self.type = d["type"]
        self.base_cost = d["cost"]
        self.ucost = d.get("ucost")
        self.rarity = d.get("rarity", "common")
        self.exhaust = d.get("exhaust", False)
        self.targeted = d.get("targeted", False)
        self.playable = d.get("playable", True)
        self.d = d["desc"]
        self.ud = d.get("udesc", d["desc"])
        self.upgradable = d.get("upgradable", True)
        self.upgraded = False

    @property
    def name(self):
        return self.base_name + ("+" if self.upgraded else "")

    @property
    def cost(self):
        if self.upgraded and self.ucost is not None:
            return self.ucost
        return self.base_cost

    @property
    def desc(self):
        return self.ud if self.upgraded else self.d

    def v(self, base, up):
        return up if self.upgraded else base

    def upgrade(self):
        if self.upgradable and not self.upgraded:
            self.upgraded = True
            return True
        return False

    def copy(self):
        n = Card(self.key)
        n.upgraded = self.upgraded
        return n

    def colored_name(self):
        return c(self.name, TYPE_COLOR.get(self.type, WHT))


# Effects receive (cb, card, target) where cb is the Combat object.
CARDS = {
    # ── starter ──
    "strike": dict(name="Strike", type="ATTACK", cost=1, targeted=True, rarity="starter",
                   desc="Deal 6 damage.", udesc="Deal 9 damage.",
                   fx=lambda cb, k, t: cb.player_attack(t, k.v(6, 9))),
    "defend": dict(name="Defend", type="SKILL", cost=1, rarity="starter",
                   desc="Gain 5 Block.", udesc="Gain 8 Block.",
                   fx=lambda cb, k, t: cb.gain_block(cb.player, k.v(5, 8))),
    "bash": dict(name="Bash", type="ATTACK", cost=2, targeted=True, rarity="starter",
                 desc="Deal 8 damage. Apply 2 Vulnerable.",
                 udesc="Deal 10 damage. Apply 3 Vulnerable.",
                 fx=lambda cb, k, t: (cb.player_attack(t, k.v(8, 10)),
                                      cb.apply(t, "vulnerable", k.v(2, 3)))),
    # ── common ──
    "cleave": dict(name="Cleave", type="ATTACK", cost=1,
                   desc="Deal 8 damage to ALL enemies.", udesc="Deal 11 damage to ALL enemies.",
                   fx=lambda cb, k, t: [cb.player_attack(e, k.v(8, 11)) for e in cb.living()]),
    "twin_strike": dict(name="Twin Strike", type="ATTACK", cost=1, targeted=True,
                        desc="Deal 5 damage twice.", udesc="Deal 7 damage twice.",
                        fx=lambda cb, k, t: cb.player_attack(t, k.v(5, 7), times=2)),
    "pommel_strike": dict(name="Pommel Strike", type="ATTACK", cost=1, targeted=True,
                          desc="Deal 9 damage. Draw 1 card.",
                          udesc="Deal 10 damage. Draw 2 cards.",
                          fx=lambda cb, k, t: (cb.player_attack(t, k.v(9, 10)),
                                               cb.draw(k.v(1, 2)))),
    "iron_wave": dict(name="Iron Wave", type="ATTACK", cost=1, targeted=True,
                      desc="Gain 5 Block. Deal 5 damage.", udesc="Gain 7 Block. Deal 7 damage.",
                      fx=lambda cb, k, t: (cb.gain_block(cb.player, k.v(5, 7)),
                                           cb.player_attack(t, k.v(5, 7)))),
    "clothesline": dict(name="Clothesline", type="ATTACK", cost=2, targeted=True,
                        desc="Deal 12 damage. Apply 2 Weak.",
                        udesc="Deal 14 damage. Apply 3 Weak.",
                        fx=lambda cb, k, t: (cb.player_attack(t, k.v(12, 14)),
                                             cb.apply(t, "weak", k.v(2, 3)))),
    "body_slam": dict(name="Body Slam", type="ATTACK", cost=1, ucost=0, targeted=True,
                      desc="Deal damage equal to your Block.",
                      udesc="Deal damage equal to your Block.",
                      fx=lambda cb, k, t: cb.player_attack(t, cb.player.block)),
    "shrug_it_off": dict(name="Shrug It Off", type="SKILL", cost=1,
                         desc="Gain 8 Block. Draw 1 card.", udesc="Gain 11 Block. Draw 1 card.",
                         fx=lambda cb, k, t: (cb.gain_block(cb.player, k.v(8, 11)), cb.draw(1))),
    "flex": dict(name="Flex", type="SKILL", cost=0,
                 desc="Gain 2 Strength. Lose it at end of turn.",
                 udesc="Gain 4 Strength. Lose it at end of turn.",
                 fx=lambda cb, k, t: (cb.apply(cb.player, "strength", k.v(2, 4)),
                                      cb.apply(cb.player, "flexloss", k.v(2, 4)))),
    "true_grit": dict(name="True Grit", type="SKILL", cost=1,
                      desc="Gain 7 Block. Exhaust a random card in hand.",
                      udesc="Gain 9 Block. Exhaust a card of your choice.",
                      fx=lambda cb, k, t: (cb.gain_block(cb.player, k.v(7, 9)),
                                           cb.grit_exhaust(k.upgraded))),
    "bloodletting": dict(name="Bloodletting", type="SKILL", cost=0,
                         desc="Lose 3 HP. Gain 2 Energy.", udesc="Lose 3 HP. Gain 3 Energy.",
                         fx=lambda cb, k, t: (cb.lose_hp(cb.player, 3, from_card=True),
                                              cb.gain_energy(k.v(2, 3)))),
    "armaments": dict(name="Armaments", type="SKILL", cost=1,
                      desc="Gain 5 Block. Upgrade a random card in hand.",
                      udesc="Gain 5 Block. Upgrade ALL cards in hand.",
                      fx=lambda cb, k, t: (cb.gain_block(cb.player, 5),
                                           cb.armaments(k.upgraded))),
    # ── uncommon ──
    "uppercut": dict(name="Uppercut", type="ATTACK", cost=2, targeted=True, rarity="uncommon",
                     desc="Deal 13 damage. Apply 1 Weak. Apply 1 Vulnerable.",
                     udesc="Deal 13 damage. Apply 2 Weak. Apply 2 Vulnerable.",
                     fx=lambda cb, k, t: (cb.player_attack(t, 13),
                                          cb.apply(t, "weak", k.v(1, 2)),
                                          cb.apply(t, "vulnerable", k.v(1, 2)))),
    "heavy_blade": dict(name="Heavy Blade", type="ATTACK", cost=2, targeted=True, rarity="uncommon",
                        desc="Deal 14 damage. Strength affects it 3 times.",
                        udesc="Deal 14 damage. Strength affects it 5 times.",
                        fx=lambda cb, k, t: cb.player_attack(t, 14, str_mult=k.v(3, 5))),
    "whirlwind": dict(name="Whirlwind", type="ATTACK", cost="X", targeted=False, rarity="uncommon",
                      desc="Deal 5 damage to ALL enemies X times.",
                      udesc="Deal 8 damage to ALL enemies X times.",
                      fx=lambda cb, k, t: [cb.player_attack(e, k.v(5, 8))
                                           for _ in range(cb.x_spent) for e in cb.living()]),
    "seeing_red": dict(name="Seeing Red", type="SKILL", cost=1, ucost=0, rarity="uncommon",
                       exhaust=True, desc="Gain 2 Energy. Exhaust.",
                       udesc="Gain 2 Energy. Exhaust.",
                       fx=lambda cb, k, t: cb.gain_energy(2)),
    "offering": dict(name="Offering", type="SKILL", cost=0, rarity="uncommon", exhaust=True,
                     desc="Lose 6 HP. Gain 2 Energy. Draw 3 cards. Exhaust.",
                     udesc="Lose 6 HP. Gain 2 Energy. Draw 5 cards. Exhaust.",
                     fx=lambda cb, k, t: (cb.lose_hp(cb.player, 6, from_card=True),
                                          cb.gain_energy(2), cb.draw(k.v(3, 5)))),
    "second_wind": dict(name="Second Wind", type="SKILL", cost=1, rarity="uncommon",
                        desc="Exhaust all non-Attack cards in hand. Gain 5 Block for each.",
                        udesc="Exhaust all non-Attack cards in hand. Gain 7 Block for each.",
                        fx=lambda cb, k, t: cb.second_wind(k.v(5, 7))),
    "inflame": dict(name="Inflame", type="POWER", cost=1, rarity="uncommon",
                    desc="Gain 2 Strength.", udesc="Gain 3 Strength.",
                    fx=lambda cb, k, t: cb.apply(cb.player, "strength", k.v(2, 3))),
    "metallicize": dict(name="Metallicize", type="POWER", cost=1, rarity="uncommon",
                        desc="At the end of your turn, gain 3 Block.",
                        udesc="At the end of your turn, gain 4 Block.",
                        fx=lambda cb, k, t: cb.apply(cb.player, "metallicize", k.v(3, 4))),
    "feel_no_pain": dict(name="Feel No Pain", type="POWER", cost=1, rarity="uncommon",
                         desc="Whenever a card is Exhausted, gain 3 Block.",
                         udesc="Whenever a card is Exhausted, gain 4 Block.",
                         fx=lambda cb, k, t: cb.apply(cb.player, "feelnopain", k.v(3, 4))),
    "rupture": dict(name="Rupture", type="POWER", cost=1, rarity="uncommon",
                    desc="Whenever you lose HP from a card, gain 1 Strength.",
                    udesc="Whenever you lose HP from a card, gain 2 Strength.",
                    fx=lambda cb, k, t: cb.apply(cb.player, "rupture", k.v(1, 2))),
    "disarm": dict(name="Disarm", type="SKILL", cost=1, targeted=True, rarity="uncommon",
                   exhaust=True, desc="Enemy loses 2 Strength. Exhaust.",
                   udesc="Enemy loses 3 Strength. Exhaust.",
                   fx=lambda cb, k, t: cb.apply(t, "strength", -k.v(2, 3))),
    "shockwave": dict(name="Shockwave", type="SKILL", cost=2, rarity="uncommon", exhaust=True,
                      desc="Apply 3 Weak and 3 Vulnerable to ALL enemies. Exhaust.",
                      udesc="Apply 5 Weak and 5 Vulnerable to ALL enemies. Exhaust.",
                      fx=lambda cb, k, t: [(cb.apply(e, "weak", k.v(3, 5)),
                                            cb.apply(e, "vulnerable", k.v(3, 5)))
                                           for e in cb.living()]),
    "poison_stab": dict(name="Poisoned Stab", type="ATTACK", cost=1, targeted=True,
                        rarity="uncommon", desc="Deal 6 damage. Apply 3 Poison.",
                        udesc="Deal 8 damage. Apply 4 Poison.",
                        fx=lambda cb, k, t: (cb.player_attack(t, k.v(6, 8)),
                                             cb.apply(t, "poison", k.v(3, 4)))),
    "battle_trance": dict(name="Battle Trance", type="SKILL", cost=0, rarity="uncommon",
                          desc="Draw 3 cards. You cannot draw more cards this turn.",
                          udesc="Draw 4 cards. You cannot draw more cards this turn.",
                          fx=lambda cb, k, t: (cb.draw(k.v(3, 4)), cb.lock_draw())),
    # ── rare ──
    "bludgeon": dict(name="Bludgeon", type="ATTACK", cost=3, targeted=True, rarity="rare",
                     desc="Deal 32 damage.", udesc="Deal 42 damage.",
                     fx=lambda cb, k, t: cb.player_attack(t, k.v(32, 42))),
    "reaper": dict(name="Reaper", type="ATTACK", cost=2, rarity="rare", exhaust=True,
                   desc="Deal 4 damage to ALL enemies. Heal HP equal to damage dealt. Exhaust.",
                   udesc="Deal 5 damage to ALL enemies. Heal HP equal to damage dealt. Exhaust.",
                   fx=lambda cb, k, t: cb.reaper(k.v(4, 5))),
    "impervious": dict(name="Impervious", type="SKILL", cost=2, rarity="rare", exhaust=True,
                       desc="Gain 30 Block. Exhaust.", udesc="Gain 40 Block. Exhaust.",
                       fx=lambda cb, k, t: cb.gain_block(cb.player, k.v(30, 40))),
    "demon_form": dict(name="Demon Form", type="POWER", cost=3, rarity="rare",
                       desc="At the start of each turn, gain 2 Strength.",
                       udesc="At the start of each turn, gain 3 Strength.",
                       fx=lambda cb, k, t: cb.apply(cb.player, "demonform", k.v(2, 3))),
    "barricade": dict(name="Barricade", type="POWER", cost=3, ucost=2, rarity="rare",
                      desc="Block is no longer removed at the start of your turn.",
                      udesc="Block is no longer removed at the start of your turn.",
                      fx=lambda cb, k, t: cb.apply(cb.player, "barricade", 1)),
    "juggernaut": dict(name="Juggernaut", type="POWER", cost=2, rarity="rare",
                       desc="Whenever you gain Block, deal 5 damage to a random enemy.",
                       udesc="Whenever you gain Block, deal 7 damage to a random enemy.",
                       fx=lambda cb, k, t: cb.apply(cb.player, "juggernaut", k.v(5, 7))),
    "limit_break": dict(name="Limit Break", type="SKILL", cost=1, rarity="rare", exhaust=True,
                        desc="Double your Strength. Exhaust.", udesc="Double your Strength.",
                        fx=lambda cb, k, t: cb.apply(cb.player, "strength",
                                                     cb.player.s("strength"))),
    # ── statuses & curses ──
    "wound": dict(name="Wound", type="STATUS", cost=0, playable=False, upgradable=False,
                  rarity="none", desc="Unplayable."),
    "burn": dict(name="Burn", type="STATUS", cost=0, playable=False, upgradable=False,
                 rarity="none", desc="Unplayable. At the end of your turn, take 2 damage."),
    "slimed": dict(name="Slimed", type="STATUS", cost=1, upgradable=False, rarity="none",
                   exhaust=True, desc="Exhaust.", fx=lambda cb, k, t: None),
    "regret": dict(name="Regret", type="CURSE", cost=0, playable=False, upgradable=False,
                   rarity="none", desc="Unplayable. At the end of your turn, lose 1 HP "
                                       "per card in your hand."),
}

COMMON_POOL = ["cleave", "twin_strike", "pommel_strike", "iron_wave", "clothesline",
               "body_slam", "shrug_it_off", "flex", "true_grit", "bloodletting", "armaments"]
UNCOMMON_POOL = ["uppercut", "heavy_blade", "whirlwind", "seeing_red", "offering",
                 "second_wind", "inflame", "metallicize", "feel_no_pain", "rupture",
                 "disarm", "shockwave", "poison_stab", "battle_trance"]
RARE_POOL = ["bludgeon", "reaper", "impervious", "demon_form", "barricade", "juggernaut",
             "limit_break"]


def random_card_keys(n, chances=(0.62, 0.31, 0.07)):
    """Pick n distinct card keys weighted by rarity."""
    keys = []
    while len(keys) < n:
        r = random.random()
        pool = COMMON_POOL if r < chances[0] else (
            UNCOMMON_POOL if r < chances[0] + chances[1] else RARE_POOL)
        k = random.choice(pool)
        if k not in keys:
            keys.append(k)
    return keys


# ───────────────────────────────────────────────────────────────── card boxes ──
CARD_W = 21


def card_box(card, index=None, energy=None, dim=False):
    """Return the list of lines making up one rendered card."""
    inner = CARD_W - 2
    col = TYPE_COLOR.get(card.type, WHT)
    playable = card.playable and (energy is None or card.cost == "X" or card.cost <= energy)
    if dim or not playable:
        col = GRY
    cost = "X" if card.cost == "X" else str(card.cost)
    head = (f"{index}." if index is not None else " ") + " " + card.name
    head = head[:inner - 4].ljust(inner - 4)
    lines = [c("┌" + "─" * inner + "┐", col),
             c("│", col) + c(head, WHT if playable else GRY) +
             c(f"[{cost}]", YEL if playable else GRY) + c("│", col),
             c("│", col) + c(card.type.ljust(inner), col) + c("│", col),
             c("├" + "─" * inner + "┤", col)]
    body = wrap(card.desc, inner - 2)[:4]
    for i in range(4):
        text = body[i] if i < len(body) else ""
        lines.append(c("│", col) + " " + text.ljust(inner - 2) + " " + c("│", col))
    lines.append(c("└" + "─" * inner + "┘", col))
    return lines


def print_cards(cards, energy=None, start=1, numbered=True):
    per_row = max(1, (term_width() - 2) // (CARD_W + 1))
    for i in range(0, len(cards), per_row):
        chunk = cards[i:i + per_row]
        boxes = [card_box(k, (start + i + j) if numbered else None, energy)
                 for j, k in enumerate(chunk)]
        for row in zip(*boxes):
            print(" " + " ".join(row))


# ─────────────────────────────────────────────────────────────────── monsters ──
def mv(kind, dmg=0, hits=1, fn=None, note=""):
    return dict(kind=kind, dmg=dmg, hits=hits, fn=fn, note=note)


def _grow(n):
    return lambda cb, e: cb.apply(e, "strength", n)


def _block(n):
    return lambda cb, e: cb.gain_block(e, n)


def _debuff(key, n):
    return lambda cb, e: cb.apply(cb.player, key, n)


def _add_cards(key, n, to_draw=False):
    def f(cb, e):
        for _ in range(n):
            cb.add_card_to_pile(Card(key), to_draw)
    return f


def cycle_pick(order):
    """Enemy repeats a fixed sequence of moves."""
    return lambda e: order[e.turn % len(order)]


def weighted_pick(options):
    """options: list of (move, weight, max_repeat)."""
    def f(e):
        pool = []
        for name, wt, rep in options:
            if rep and len(e.history) >= rep and all(h == name for h in e.history[-rep:]):
                continue
            pool += [name] * wt
        return random.choice(pool) if pool else options[0][0]
    return f


MONSTERS = {
    "jaw_worm": dict(name="Jaw Worm", hp=(40, 46), moves={
        "Chomp": mv("attack", 11),
        "Thrash": mv("attack", 7, fn=_block(5)),
        "Bellow": mv("buff", fn=lambda cb, e: (cb.apply(e, "strength", 3), cb.gain_block(e, 6))),
    }, pick=lambda e: "Chomp" if e.turn == 0 else weighted_pick(
        [("Bellow", 45, 2), ("Thrash", 30, 3), ("Chomp", 25, 2)])(e)),

    "cultist": dict(name="Cultist", hp=(48, 54), moves={
        "Incantation": mv("buff", fn=lambda cb, e: cb.apply(e, "ritual", 3)),
        "Dark Strike": mv("attack", 6),
    }, pick=lambda e: "Incantation" if e.turn == 0 else "Dark Strike"),

    "louse": dict(name="Red Louse", hp=(11, 16), moves={
        "Bite": mv("attack", 6),
        "Grow": mv("buff", fn=_grow(3)),
    }, pick=weighted_pick([("Bite", 75, 3), ("Grow", 25, 1)])),

    "fungi": dict(name="Fungi Beast", hp=(22, 28), moves={
        "Bite": mv("attack", 6),
        "Grow": mv("buff", fn=_grow(4)),
    }, pick=weighted_pick([("Bite", 60, 2), ("Grow", 40, 1)]),
        on_death=lambda cb, e: cb.apply(cb.player, "vulnerable", 2)),

    "acid_slime": dict(name="Acid Slime", hp=(28, 34), moves={
        "Corrosive Spit": mv("attack", 7, fn=_add_cards("slimed", 1)),
        "Tackle": mv("attack", 10),
        "Lick": mv("debuff", fn=_debuff("weak", 1)),
    }, pick=weighted_pick([("Corrosive Spit", 40, 2), ("Tackle", 35, 2), ("Lick", 25, 1)])),

    "spike_slime": dict(name="Spike Slime", hp=(26, 32), moves={
        "Flame Tackle": mv("attack", 8, fn=_add_cards("slimed", 1)),
        "Frail Lick": mv("debuff", fn=_debuff("frail", 2)),
    }, pick=weighted_pick([("Flame Tackle", 70, 2), ("Frail Lick", 30, 1)])),

    "small_slime": dict(name="Slime Spawn", hp=(9, 13), moves={
        "Tackle": mv("attack", 5),
        "Lick": mv("debuff", fn=_debuff("frail", 1)),
    }, pick=weighted_pick([("Tackle", 80, 3), ("Lick", 20, 1)])),

    "mad_gremlin": dict(name="Mad Gremlin", hp=(18, 22), moves={
        "Scratch": mv("attack", 5),
        "Angry": mv("buff", fn=_grow(1)),
    }, pick=weighted_pick([("Scratch", 80, 4), ("Angry", 20, 1)])),

    "sneaky_gremlin": dict(name="Sneaky Gremlin", hp=(10, 14), moves={
        "Puncture": mv("attack", 9),
    }, pick=lambda e: "Puncture"),

    "fat_gremlin": dict(name="Fat Gremlin", hp=(13, 17), moves={
        "Smash": mv("attack", 5, fn=_debuff("weak", 1)),
    }, pick=lambda e: "Smash"),

    "shield_gremlin": dict(name="Shield Gremlin", hp=(12, 15), moves={
        "Protect": mv("block", fn=lambda cb, e: [cb.gain_block(x, 7)
                                                 for x in cb.living() if x is not e]),
        "Bash": mv("attack", 6),
    }, pick=lambda e: "Protect" if any(x.alive and x is not e for x in e.allies) else "Bash"),

    "sentry": dict(name="Sentry", hp=(36, 40), moves={
        "Beam": mv("attack", 9),
        "Bolt": mv("debuff", fn=_add_cards("wound", 2, to_draw=True)),
    }, pick=cycle_pick(["Bolt", "Beam"])),

    "byrd": dict(name="Byrd", hp=(24, 30), moves={
        "Peck": mv("attack", 2, hits=5),
        "Swoop": mv("attack", 12),
        "Caw": mv("buff", fn=_grow(2)),
    }, pick=weighted_pick([("Peck", 50, 2), ("Swoop", 30, 2), ("Caw", 20, 1)])),

    "chosen": dict(name="Chosen", hp=(50, 58), moves={
        "Hex": mv("debuff", fn=lambda cb, e: cb.add_card_to_pile(Card("regret"), True)),
        "Zap": mv("attack", 18),
        "Debilitate": mv("attack", 10, fn=_debuff("vulnerable", 2)),
        "Drain": mv("debuff", fn=lambda cb, e: (cb.apply(cb.player, "weak", 3),
                                                cb.apply(e, "strength", 3))),
    }, pick=lambda e: "Hex" if e.turn == 0 else weighted_pick(
        [("Zap", 30, 2), ("Debilitate", 40, 2), ("Drain", 30, 1)])(e)),

    "mystic": dict(name="Mystic", hp=(44, 50), moves={
        "Heal": mv("buff", fn=lambda cb, e: [cb.heal(x, 8) for x in cb.living()]),
        "Attack Debuff": mv("attack", 9, fn=_debuff("weak", 2)),
        "Buff": mv("buff", fn=lambda cb, e: [cb.apply(x, "strength", 2) for x in cb.living()]),
    }, pick=weighted_pick([("Heal", 30, 1), ("Attack Debuff", 40, 2), ("Buff", 30, 1)])),

    # ── elites ──
    "gremlin_nob": dict(name="Gremlin Nob", hp=(82, 86), elite=True, moves={
        "Bellow": mv("buff", fn=_grow(3)),
        "Skull Bash": mv("attack", 8, fn=_debuff("vulnerable", 2)),
        "Rush": mv("attack", 16),
    }, pick=lambda e: "Bellow" if e.turn == 0 else weighted_pick(
        [("Rush", 66, 2), ("Skull Bash", 34, 1)])(e)),

    "lagavulin": dict(name="Lagavulin", hp=(105, 112), elite=True, moves={
        "Sleep": mv("block", fn=lambda cb, e: cb.gain_block(e, 8), note="dormant"),
        "Attack": mv("attack", 18),
        "Siphon Soul": mv("debuff", fn=lambda cb, e: (cb.apply(cb.player, "strength", -1),
                                                      cb.apply(cb.player, "dexterity", -1))),
    }, pick=lambda e: "Sleep" if e.turn < 3 else (
        "Siphon Soul" if (e.turn - 3) % 3 == 2 else "Attack")),

    "book_of_stabbing": dict(name="Book of Stabbing", hp=(120, 130), elite=True, moves={
        "Multi-Stab": mv("attack", 6, hits=3, fn=_grow(1)),
        "Single Stab": mv("attack", 21),
    }, pick=weighted_pick([("Multi-Stab", 70, 2), ("Single Stab", 30, 2)])),

    "taskmaster": dict(name="Taskmaster", hp=(90, 98), elite=True, moves={
        "Scouring Wave": mv("attack", 9, fn=_add_cards("wound", 1)),
        "Whip": mv("attack", 14, fn=_debuff("weak", 2)),
        "Rally": mv("buff", fn=lambda cb, e: (cb.apply(e, "strength", 2), cb.gain_block(e, 12))),
    }, pick=weighted_pick([("Scouring Wave", 35, 2), ("Whip", 40, 2), ("Rally", 25, 1)])),

    # ── bosses ──
    "guardian": dict(name="The Guardian", hp=(240, 240), boss=True, moves={
        "Charging Up": mv("block", fn=_block(9)),
        "Fierce Bash": mv("attack", 32),
        "Vent Steam": mv("debuff", fn=lambda cb, e: (cb.apply(cb.player, "vulnerable", 2),
                                                     cb.apply(cb.player, "weak", 2))),
        "Whirlwind": mv("attack", 5, hits=4),
        "Twin Slam": mv("attack", 8, hits=2, fn=_grow(2)),
    }, pick=cycle_pick(["Charging Up", "Fierce Bash", "Vent Steam", "Whirlwind", "Twin Slam"])),

    "hexaghost": dict(name="Hexaghost", hp=(250, 250), boss=True, moves={
        "Activate": mv("buff", fn=_block(12)),
        "Divider": mv("attack", 6, hits=6),
        "Sear": mv("attack", 6, fn=_add_cards("burn", 1)),
        "Tackle": mv("attack", 6, hits=2),
        "Inferno": mv("attack", 3, hits=6, fn=_add_cards("burn", 3, to_draw=True)),
    }, pick=lambda e: "Activate" if e.turn == 0 else (
        "Divider" if e.turn == 1 else
        ["Sear", "Tackle", "Sear", "Inferno", "Tackle", "Sear"][(e.turn - 2) % 6])),

    "slime_boss": dict(name="Slime Boss", hp=(160, 160), boss=True, moves={
        "Goop Spray": mv("debuff", fn=_add_cards("slimed", 3)),
        "Preparing": mv("block", fn=_block(15)),
        "Slam": mv("attack", 38),
    }, pick=cycle_pick(["Goop Spray", "Preparing", "Slam"])),

    "champ": dict(name="The Champ", hp=(300, 300), boss=True, moves={
        "Defensive Stance": mv("block", fn=lambda cb, e: (cb.gain_block(e, 18),
                                                          cb.apply(e, "metallicize", 4))),
        "Heavy Slash": mv("attack", 18),
        "Face Slap": mv("attack", 14, fn=lambda cb, e: (cb.apply(cb.player, "frail", 2),
                                                        cb.apply(cb.player, "vulnerable", 2))),
        "Execute": mv("attack", 12, hits=2),
        "Anger": mv("buff", fn=lambda cb, e: (cb.apply(e, "strength", 6), cb.heal(e, 20))),
    }, pick=cycle_pick(["Face Slap", "Heavy Slash", "Defensive Stance", "Execute", "Anger",
                        "Heavy Slash", "Execute"])),
}


class Enemy(Combatant):
    def __init__(self, key, act=1):
        spec = MONSTERS[key]
        lo, hi = spec["hp"]
        hp = random.randint(lo, hi)
        hp = int(hp * (1 + 0.18 * (act - 1)))
        super().__init__(spec["name"], hp)
        self.key = key
        self.spec = spec
        self.moves = spec["moves"]
        self.turn = 0
        self.history = []
        self.intent = None
        self.allies = [self]
        self.elite = spec.get("elite", False)
        self.boss = spec.get("boss", False)
        if act >= 3:
            self.st["strength"] += 1

    def roll_intent(self):
        self.intent = self.spec["pick"](self)

    def intent_text(self):
        if not self.intent:
            return ""
        m = self.moves[self.intent]
        if m["kind"] == "attack":
            dmg = damage_after_modifiers(self, m["dmg"], PLAYER_REF[0])
            hits = f" x{m['hits']}" if m["hits"] > 1 else ""
            extra = " +debuff" if m["fn"] else ""
            return c(f"⚔ {dmg}{hits}{extra}", RED)
        if m["kind"] == "block":
            return c("⛨ defend", CYN)
        if m["kind"] == "buff":
            return c("↑ buff", YEL)
        return c("↓ debuff", MAG)


PLAYER_REF = [None]  # set at run start so intents can preview vulnerability


def damage_after_modifiers(attacker, base, target, str_mult=1):
    dmg = base + attacker.s("strength") * str_mult
    if attacker.s("weak"):
        dmg = int(dmg * 0.75)
    if target and target.s("vulnerable"):
        dmg = int(dmg * 1.5)
    return max(0, dmg)


# ────────────────────────────────────────────────────────────────────── relics ──
RELICS = {
    "burning_blood": dict(name="Burning Blood", desc="Heal 6 HP after each combat."),
    "bag_of_marbles": dict(name="Bag of Marbles", desc="At combat start, apply 1 Vulnerable "
                                                       "to ALL enemies."),
    "anchor": dict(name="Anchor", desc="Gain 10 Block on the first turn of combat."),
    "vajra": dict(name="Vajra", desc="Start each combat with 1 Strength."),
    "oddly_smooth_stone": dict(name="Oddly Smooth Stone", desc="Start each combat with "
                                                               "1 Dexterity."),
    "bronze_scales": dict(name="Bronze Scales", desc="Start each combat with 3 Thorns."),
    "blood_vial": dict(name="Blood Vial", desc="At combat start, heal 2 HP."),
    "lantern": dict(name="Lantern", desc="Gain 1 Energy on the first turn of combat."),
    "happy_flower": dict(name="Happy Flower", desc="Every 3rd turn, gain 1 Energy."),
    "pen_nib": dict(name="Pen Nib", desc="Every 10th Attack you play deals double damage."),
    "strawberry": dict(name="Strawberry", desc="Raise Max HP by 7."),
    "meat_on_bone": dict(name="Meat on the Bone", desc="If you end a combat below half HP, "
                                                       "heal 12 HP."),
    "kunai": dict(name="Kunai", desc="Every 3rd Attack in a turn grants 1 Dexterity."),
    "bag_of_prep": dict(name="Bag of Preparation", desc="Draw 2 extra cards on turn 1."),
    "art_of_war": dict(name="Art of War", desc="If you play no Attacks in a turn, "
                                               "gain 1 Energy next turn."),
}
RELIC_POOL = [k for k in RELICS if k != "burning_blood"]


# ───────────────────────────────────────────────────────────────────── potions ──
POTIONS = {
    "fire": dict(name="Fire Potion", desc="Deal 20 damage to an enemy.", targeted=True,
                 fx=lambda cb, t: cb.player_attack(t, 20, potion=True)),
    "block": dict(name="Block Potion", desc="Gain 12 Block.",
                  fx=lambda cb, t: cb.gain_block(cb.player, 12)),
    "strength": dict(name="Strength Potion", desc="Gain 2 Strength.",
                     fx=lambda cb, t: cb.apply(cb.player, "strength", 2)),
    "energy": dict(name="Energy Potion", desc="Gain 2 Energy.",
                   fx=lambda cb, t: cb.gain_energy(2)),
    "swift": dict(name="Swift Potion", desc="Draw 3 cards.", fx=lambda cb, t: cb.draw(3)),
    "explosive": dict(name="Explosive Potion", desc="Deal 10 damage to ALL enemies.",
                      fx=lambda cb, t: [cb.player_attack(e, 10, potion=True)
                                        for e in cb.living()]),
    "weak": dict(name="Weak Potion", desc="Apply 3 Weak to an enemy.", targeted=True,
                 fx=lambda cb, t: cb.apply(t, "weak", 3)),
    "fear": dict(name="Fear Potion", desc="Apply 3 Vulnerable to an enemy.", targeted=True,
                 fx=lambda cb, t: cb.apply(t, "vulnerable", 3)),
    "blood": dict(name="Blood Potion", desc="Heal 12 HP.", fx=lambda cb, t: cb.heal(cb.player, 12)),
}


# ────────────────────────────────────────────────────────────────────── player ──
class Player(Combatant):
    def __init__(self):
        super().__init__("The Sentinel", 75)
        self.gold = 99
        self.max_energy = 3
        self.deck = [Card("strike") for _ in range(5)] + \
                    [Card("defend") for _ in range(4)] + [Card("bash")]
        self.relics = ["burning_blood"]
        self.potions = []
        self.max_potions = 3

    def has(self, relic):
        return relic in self.relics

    def add_relic(self, key):
        self.relics.append(key)
        if key == "strawberry":
            self.max_hp += 7
            self.hp += 7


# ────────────────────────────────────────────────────────────────────── combat ──
class Defeat(Exception):
    pass


class Combat:
    def __init__(self, player, enemies, label=""):
        self.player = player
        self.enemies = enemies
        for e in enemies:
            e.allies = enemies
        self.label = label
        self.draw_pile = [k.copy() for k in player.deck]
        random.shuffle(self.draw_pile)
        self.hand = []
        self.discard = []
        self.exhausted = []
        self.energy = 0
        self.x_spent = 0
        self.turn = 0
        self.log = []
        self.no_draw = False
        self.attacks_this_turn = 0
        self.attacks_total = 0
        self.attacked_this_turn = False
        self.bonus_energy_next = 0

    # ── helpers ──
    def living(self):
        return [e for e in self.enemies if e.alive]

    def msg(self, text):
        self.log.append(text)
        self.log = self.log[-6:]

    def lock_draw(self):
        self.no_draw = True

    # ── damage & healing ──
    def player_attack(self, target, base, times=1, str_mult=1, potion=False):
        for _ in range(times):
            if not target or not target.alive:
                return
            if potion:
                dmg = base
                if target.s("vulnerable"):
                    dmg = int(dmg * 1.5)
            else:
                dmg = damage_after_modifiers(self.player, base, target, str_mult)
                self.attacks_total += 1
                self.attacks_this_turn += 1
                self.attacked_this_turn = True
                if self.player.has("pen_nib") and self.attacks_total % 10 == 0:
                    dmg *= 2
                    self.msg(c("Pen Nib doubles the blow!", YEL))
                if self.player.has("kunai") and self.attacks_this_turn % 3 == 0:
                    self.apply(self.player, "dexterity", 1)
            self.damage(target, dmg)
            if target.s("thorns") and not potion:
                self.lose_hp(self.player, target.s("thorns"))

    def enemy_attack(self, enemy, base):
        dmg = damage_after_modifiers(enemy, base, self.player)
        self.damage(self.player, dmg)
        if self.player.s("thorns") and enemy.alive:
            self.damage(enemy, self.player.s("thorns"), ignore_block=True)

    def damage(self, target, dmg, ignore_block=False):
        """Apply damage through Block. Returns HP actually lost."""
        if dmg <= 0:
            return 0
        if not ignore_block:
            absorbed = min(target.block, dmg)
            target.block -= absorbed
            dmg -= absorbed
        if dmg <= 0:
            return 0
        target.hp -= dmg
        if target is self.player and target.hp <= 0:
            self.die()
        if target is not self.player and target.hp <= 0:
            self.kill(target)
        return dmg

    def die(self):
        self.player.hp = 0
        raise Defeat(", ".join(e.name for e in self.living()) or "the Spire")

    def lose_hp(self, target, n, from_card=False):
        target.hp -= n
        if from_card and target is self.player and self.player.s("rupture"):
            self.apply(self.player, "strength", self.player.s("rupture"))
        if target is self.player and target.hp <= 0:
            self.die()
        if target is not self.player and target.hp <= 0:
            self.kill(target)

    def kill(self, enemy):
        enemy.hp = 0
        enemy.alive = False
        self.msg(c(f"{enemy.name} is slain!", GRN))
        od = enemy.spec.get("on_death")
        if od:
            od(self, enemy)

    def heal(self, target, n):
        target.hp = min(target.max_hp, target.hp + n)

    # ── block & statuses ──
    def gain_block(self, who, amount):
        if amount <= 0:
            return
        if who is self.player:
            amount += who.s("dexterity")
            if who.s("frail"):
                amount = int(amount * 0.75)
        amount = max(0, amount)
        who.block += amount
        if who is self.player and who.s("juggernaut"):
            targets = self.living()
            if targets:
                self.player_attack(random.choice(targets), who.s("juggernaut"), potion=True)

    def apply(self, target, key, n):
        if n == 0 or target is None or not target.alive:
            return
        target.st[key] += n
        if key in DEBUFFS and n > 0 and target is not self.player:
            pass

    # ── piles ──
    def draw(self, n):
        if self.no_draw:
            return
        for _ in range(n):
            if len(self.hand) >= 10:
                self.msg(c("Hand is full.", GRY))
                return
            if not self.draw_pile:
                if not self.discard:
                    return
                self.draw_pile = self.discard
                self.discard = []
                random.shuffle(self.draw_pile)
            self.hand.append(self.draw_pile.pop())

    def add_card_to_pile(self, card, to_draw=False):
        if to_draw:
            self.draw_pile.insert(random.randint(0, len(self.draw_pile)), card)
        else:
            self.discard.append(card)
        self.msg(c(f"{card.name} added to your {'draw' if to_draw else 'discard'} pile.", GRY))

    def exhaust_card(self, card):
        self.exhausted.append(card)
        if self.player.s("feelnopain"):
            self.gain_block(self.player, self.player.s("feelnopain"))

    def gain_energy(self, n):
        self.energy += n

    # ── special card behaviours ──
    def grit_exhaust(self, choose):
        if not self.hand:
            return
        if choose:
            self.render()
            print(c("  Exhaust which card?", YEL))
            print_cards(self.hand)
            idx = read_index(len(self.hand))
            if idx is None:
                idx = random.randrange(len(self.hand))
        else:
            idx = random.randrange(len(self.hand))
        card = self.hand.pop(idx)
        self.exhaust_card(card)
        self.msg(f"Exhausted {card.name}.")

    def armaments(self, all_cards):
        candidates = [k for k in self.hand if k.upgradable and not k.upgraded]
        if not candidates:
            return
        if all_cards:
            for k in candidates:
                k.upgrade()
            self.msg(c("Armaments upgrades your hand!", YEL))
        else:
            k = random.choice(candidates)
            k.upgrade()
            self.msg(c(f"Armaments upgrades {k.name}.", YEL))

    def second_wind(self, per):
        keep = []
        n = 0
        for k in self.hand:
            if k.type != "ATTACK":
                self.exhaust_card(k)
                n += 1
                self.gain_block(self.player, per)
            else:
                keep.append(k)
        self.hand = keep
        self.msg(f"Second Wind exhausts {n} card(s).")

    def reaper(self, base):
        total = 0
        for e in self.living():
            before = e.hp
            self.player_attack(e, base)
            total += max(0, before - e.hp)
        if total:
            self.heal(self.player, total)
            self.msg(c(f"Reaper heals {total} HP.", GRN))

    # ── rendering ──
    def render(self):
        clear()
        p = self.player
        w = term_width()
        print(c("═" * min(w - 1, 96), GRY))
        title = f" {self.label}  —  turn {self.turn + 1} "
        print(c(title, BOLD, YEL))
        print()
        for i, e in enumerate(self.enemies):
            tag = chr(ord("a") + i)
            if not e.alive:
                print(c(f"  ({tag}) {e.name:<18} DEAD", GRY))
                continue
            hp = f"{e.hp}/{e.max_hp}"
            blk = c(f" ⛨{e.block}", CYN) if e.block else ""
            print(f"  ({c(tag, YEL)}) {c(e.name.ljust(18), WHT)} "
                  f"{bar(e.hp, e.max_hp, 14, RED)} {hp:<9}{blk}")
            line = f"       intent: {e.intent_text()}"
            st = e.status_line()
            if st:
                line += "   " + st
            print(line)
        print()
        print(c("─" * min(w - 1, 96), GRY))
        blk = c(f"⛨ {p.block}", CYN) if p.block else c("⛨ 0", GRY)
        print(f"  {c(p.name, BOLD, GRN)}  {bar(p.hp, p.max_hp, 16, GRN)} "
              f"{p.hp}/{p.max_hp}   {blk}   "
              f"{c('⚡ ' + str(self.energy) + '/' + str(p.max_energy), YEL)}")
        st = p.status_line()
        if st:
            print("  " + st)
        print(c(f"  draw {len(self.draw_pile)}   discard {len(self.discard)}   "
                f"exhaust {len(self.exhausted)}   gold {p.gold}", GRY))
        if p.potions:
            pots = "  ".join(f"{c('(p'+str(i+1)+')', YEL)} {POTIONS[k]['name']}"
                             for i, k in enumerate(p.potions))
            print("  " + pots)
        print()
        print_cards(self.hand, self.energy)
        print()
        for line in self.log[-3:]:
            print("  " + c(line, GRY) if not line.startswith(ESC) else "  " + line)

    # ── turn flow ──
    def start_combat(self):
        p = self.player
        p.block = 0
        p.st.clear()
        if p.has("bag_of_marbles"):
            for e in self.enemies:
                self.apply(e, "vulnerable", 1)
        if p.has("vajra"):
            self.apply(p, "strength", 1)
        if p.has("oddly_smooth_stone"):
            self.apply(p, "dexterity", 1)
        if p.has("bronze_scales"):
            self.apply(p, "thorns", 3)
        if p.has("blood_vial"):
            self.heal(p, 2)
        for e in self.enemies:
            e.roll_intent()

    def player_turn_start(self):
        p = self.player
        if not p.s("barricade"):
            p.block = 0
        self.energy = p.max_energy + self.bonus_energy_next
        self.bonus_energy_next = 0
        self.no_draw = False
        self.attacks_this_turn = 0
        self.attacked_this_turn = False
        if self.turn == 0 and p.has("anchor"):
            self.gain_block(p, 10)
        if self.turn == 0 and p.has("lantern"):
            self.energy += 1
        if p.has("happy_flower") and (self.turn + 1) % 3 == 0:
            self.energy += 1
        if p.s("demonform"):
            self.apply(p, "strength", p.s("demonform"))
        if p.s("poison"):
            self.lose_hp(p, p.s("poison"))
            p.st["poison"] -= 1
        n = 5 + (2 if (self.turn == 0 and p.has("bag_of_prep")) else 0)
        self.draw(n)

    def player_turn_end(self):
        p = self.player
        if p.s("metallicize"):
            self.gain_block(p, p.s("metallicize"))
        if p.s("flexloss"):
            self.apply(p, "strength", -p.s("flexloss"))
            p.st["flexloss"] = 0
        burns = [k for k in self.hand if k.key == "burn"]
        for _ in burns:
            self.lose_hp(p, 2)
        if any(k.key == "regret" for k in self.hand):
            self.lose_hp(p, len(self.hand))
        if p.has("art_of_war") and not self.attacked_this_turn:
            self.bonus_energy_next += 1
        for k in list(self.hand):
            self.discard.append(k)
        self.hand = []
        for key in DECAYING:
            if p.st[key] > 0:
                p.st[key] -= 1

    def enemy_turns(self):
        for e in self.living():
            if e.s("poison"):
                self.lose_hp(e, e.s("poison"))
                e.st["poison"] -= 1
                if not e.alive:
                    continue
            e.block = 0
            if e.s("ritual"):
                self.apply(e, "strength", e.s("ritual"))
            m = e.moves[e.intent]
            if m["kind"] == "attack":
                for _ in range(m["hits"]):
                    self.enemy_attack(e, m["dmg"])
            if m["fn"]:
                m["fn"](self, e)
            self.msg(f"{e.name} uses {e.intent}.")
            e.history.append(e.intent)
            e.turn += 1
            for key in DECAYING:
                if e.st[key] > 0:
                    e.st[key] -= 1
            if e.alive:
                e.roll_intent()

    # ── main loop ──
    def run(self):
        """Returns True on victory; raises Defeat if the player dies."""
        self.start_combat()
        while True:
            self.player_turn_start()
            if not self.living():
                return True
            while True:
                self.render()
                cmd = prompt(c("  play # / (p#) potion / (e)nd turn / (d)eck / (?)help > ", YEL))
                cmd = cmd.lower()
                if cmd in ("e", "end", ""):
                    break
                if cmd in ("?", "h", "help"):
                    self.help_screen()
                    continue
                if cmd in ("d", "deck"):
                    self.pile_screen()
                    continue
                if cmd.startswith("p") and cmd[1:].isdigit():
                    self.use_potion(int(cmd[1:]) - 1)
                    if not self.living():
                        return True
                    continue
                if cmd.isdigit():
                    self.play_card(int(cmd) - 1)
                    if not self.living():
                        return True
                    continue
                self.msg("Unknown command. Press ? for help.")
            self.player_turn_end()
            if not self.living():
                return True
            self.enemy_turns()
            self.turn += 1

    def choose_target(self, auto_ok=True):
        alive = self.living()
        if len(alive) == 1 and auto_ok:
            return alive[0]
        self.render()
        opts = ", ".join(f"({chr(ord('a') + self.enemies.index(e))}) {e.name}" for e in alive)
        ans = prompt(c(f"  target — {opts} > ", YEL)).lower()
        if not ans:
            return None
        i = ord(ans[0]) - ord("a")
        if 0 <= i < len(self.enemies) and self.enemies[i].alive:
            return self.enemies[i]
        return None

    def play_card(self, idx):
        if not (0 <= idx < len(self.hand)):
            self.msg("No such card.")
            return
        card = self.hand[idx]
        if not card.playable:
            self.msg(f"{card.name} is unplayable.")
            return
        if card.cost == "X":
            if self.energy <= 0:
                self.msg("Not enough energy.")
                return
            self.x_spent = self.energy
            cost = self.energy
        else:
            cost = card.cost
            if cost > self.energy:
                self.msg("Not enough energy.")
                return
        target = None
        if card.targeted:
            target = self.choose_target()
            if target is None:
                self.msg("Cancelled.")
                return
        self.energy -= cost
        self.hand.pop(idx)
        CARDS[card.key].get("fx", lambda *a: None)(self, card, target)
        self.msg(f"You play {card.name}.")
        if card.exhaust:
            self.exhaust_card(card)
        elif card.type == "POWER":
            pass  # powers leave play
        else:
            self.discard.append(card)

    def use_potion(self, idx):
        p = self.player
        if not (0 <= idx < len(p.potions)):
            self.msg("No such potion.")
            return
        key = p.potions[idx]
        spec = POTIONS[key]
        target = self.choose_target() if spec.get("targeted") else None
        if spec.get("targeted") and target is None:
            self.msg("Cancelled.")
            return
        p.potions.pop(idx)
        spec["fx"](self, target)
        self.msg(c(f"You drink the {spec['name']}.", MAG))

    def pile_screen(self):
        clear()
        for title, pile in (("DRAW PILE (order hidden)", sorted(
                self.draw_pile, key=lambda k: k.name)),
                ("DISCARD PILE", self.discard), ("EXHAUSTED", self.exhausted)):
            print(c(f"\n  {title} — {len(pile)} cards", BOLD, YEL))
            if pile:
                print_cards(pile, numbered=False)
        pause()

    def help_screen(self):
        clear()
        print(c("\n  HOW TO PLAY\n", BOLD, YEL))
        for line in [
            "Type a card's number to play it. Cards cost Energy (⚡); you get 3 per turn.",
            "'e' ends your turn: your hand is discarded and the enemies act.",
            "Block (⛨) absorbs damage and vanishes at the start of your next turn.",
            "Enemy intent shows what they will do next — ⚔ is the damage you would take.",
            "",
            c("Vulnerable", MAG) + " — takes 50% more attack damage.",
            c("Weak", BLU) + " — deals 25% less attack damage.",
            c("Frail", BLU) + " — gains 25% less Block.",
            c("Strength", RED) + " — adds damage to each attack. " +
            c("Dexterity", GRN) + " — adds Block.",
            c("Poison", GRN) + " — lose that much HP each turn; it decreases by 1.",
            c("Thorns", YEL) + " — attackers take damage.",
            "",
            "'d' inspects your draw / discard / exhaust piles. 'p1'..'p3' drink a potion.",
        ]:
            print("   " + line)
        pause()


def read_index(n):
    ans = prompt(c("  > ", YEL))
    if ans.isdigit() and 1 <= int(ans) <= n:
        return int(ans) - 1
    return None


# ──────────────────────────────────────────────────────────────────────── map ──
NODE_SYMBOLS = {
    "monster": ("M", RED), "elite": ("E", MAG), "event": ("?", CYN),
    "rest": ("R", GRN), "shop": ("$", YEL), "treasure": ("T", YEL), "boss": ("B", RED),
}
FLOORS = 15


def generate_map():
    floors = []
    for f in range(FLOORS):
        if f == FLOORS - 1:
            types = ["boss"]
        elif f == 0:
            types = ["monster"] * random.randint(2, 3)
        elif f == 8:
            types = ["treasure"] * random.randint(2, 4)
        elif f == FLOORS - 2:
            types = ["rest"] * random.randint(2, 3)
        else:
            n = random.randint(2, 4)
            types = []
            for _ in range(n):
                r = random.random()
                if f >= 5 and r < 0.16:
                    types.append("elite")
                elif f >= 5 and r < 0.28:
                    types.append("rest")
                elif r < 0.34:
                    types.append("event")
                elif r < 0.40:
                    types.append("shop")
                else:
                    types.append("monster")
        floors.append([dict(type=t, edges=[]) for t in types])

    for f in range(FLOORS - 1):
        cur, nxt = floors[f], floors[f + 1]
        n, m = len(cur), len(nxt)
        base = [round(j * (m - 1) / (n - 1)) if n > 1 else (m - 1) // 2 for j in range(n)]
        for j, node in enumerate(cur):
            targets = {base[j]}
            hi = base[j + 1] if j + 1 < n else m - 1
            lo = base[j - 1] if j > 0 else 0
            if random.random() < 0.5 and base[j] + 1 <= hi:
                targets.add(base[j] + 1)
            if random.random() < 0.35 and base[j] - 1 >= lo:
                targets.add(base[j] - 1)
            node["edges"] = sorted(t for t in targets if 0 <= t < m)
        covered = {t for node in cur for t in node["edges"]}
        for t in range(m):
            if t not in covered:
                j = min(range(n), key=lambda x: abs(base[x] - t))
                cur[j]["edges"] = sorted(set(cur[j]["edges"]) | {t})
    return floors


def render_map(floors, cur_floor, cur_idx, visited):
    """visited: list of (floor, idx) already taken."""
    width = 44
    def xpos(f, i):
        n = len(floors[f])
        return int((i + 0.5) * width / n)

    rows = []
    for f in range(FLOORS - 1, -1, -1):
        line = [" "] * (width + 4)
        for i, node in enumerate(floors[f]):
            sym, col = NODE_SYMBOLS[node["type"]]
            x = xpos(f, i)
            reachable = (cur_floor is not None and f == cur_floor + 1 and
                         (cur_floor == -1 or i in floors[cur_floor][cur_idx]["edges"]))
            if cur_floor == -1 and f == 0:
                reachable = True
            if (f, i) == (cur_floor, cur_idx):
                cell = c(sym, BOLD, WHT)
            elif (f, i) in visited:
                cell = c(sym, GRY)
            elif reachable:
                cell = c(sym, BOLD, col)
            else:
                cell = c(sym, col)
            label = chr(ord("a") + i) if reachable else " "
            line[x] = cell
            if reachable:
                line[min(width + 3, x + 1)] = c(label, YEL)
        rows.append(f"{f + 1:>3} " + "".join(line))
        if f > 0:
            conn = [" "] * (width + 4)
            for i, node in enumerate(floors[f - 1]):
                x0 = xpos(f - 1, i)
                for t in node["edges"]:
                    x1 = xpos(f, t)
                    ch = "|" if x1 == x0 else ("\\" if x1 < x0 else "/")
                    xm = (x0 + x1) // 2
                    if 0 <= xm < len(conn):
                        conn[xm] = c(ch, GRY)
            rows.append("    " + "".join(conn))
    return rows


# ─────────────────────────────────────────────────────────────────── encounters ──
# Hand-built encounter groups: weak monsters come in packs, strong ones come alone.
ACT_POOLS = {
    1: dict(
        weak=[["cultist"], ["jaw_worm"], ["louse", "louse"],
              ["small_slime", "small_slime"], ["mad_gremlin", "sneaky_gremlin"]],
        strong=[["jaw_worm"], ["cultist", "louse"], ["fungi", "fungi"],
                ["acid_slime"], ["spike_slime", "small_slime"],
                ["louse", "louse", "louse"],
                ["mad_gremlin", "fat_gremlin", "sneaky_gremlin", "shield_gremlin"],
                ["acid_slime", "spike_slime"]],
        elite=["gremlin_nob", "lagavulin"], boss=["guardian", "slime_boss"]),
    2: dict(
        weak=[["byrd"], ["fungi", "fungi"], ["jaw_worm", "louse"], ["sentry"]],
        strong=[["chosen"], ["mystic"], ["byrd", "byrd"], ["sentry", "sentry"],
                ["chosen", "cultist"], ["mystic", "byrd"], ["acid_slime", "spike_slime"],
                ["jaw_worm", "jaw_worm"]],
        elite=["taskmaster", "gremlin_nob"], boss=["hexaghost", "champ"]),
    3: dict(
        weak=[["chosen"], ["mystic"], ["sentry", "sentry"], ["byrd", "byrd"]],
        strong=[["chosen", "chosen"], ["sentry", "sentry", "sentry"],
                ["mystic", "chosen"], ["byrd", "byrd", "byrd"],
                ["acid_slime", "acid_slime"], ["chosen", "mystic"]],
        elite=["book_of_stabbing", "taskmaster"], boss=["champ", "hexaghost"]),
}


def make_encounter(act, kind, floor):
    pool = ACT_POOLS[min(act, 3)]
    if kind == "boss":
        return [Enemy(random.choice(pool["boss"]), act)], "BOSS"
    if kind == "elite":
        return [Enemy(random.choice(pool["elite"]), act)], "ELITE"
    group = random.choice(pool["weak"] if floor < 3 else pool["strong"])
    return [Enemy(k, act) for k in group], "COMBAT"


# ──────────────────────────────────────────────────────────────────────── game ──
class Game:
    def __init__(self):
        self.player = Player()
        PLAYER_REF[0] = self.player
        self.act = 1
        self.floors = generate_map()
        self.cur_floor = -1
        self.cur_idx = 0
        self.visited = []
        self.elites_killed = 0
        self.floors_cleared = 0

    # ── screens ──
    def header(self):
        p = self.player
        print(c(f"  Act {self.act}   ", BOLD, YEL) +
              c(f"HP {p.hp}/{p.max_hp}", GRN) + "   " +
              c(f"Gold {p.gold}", YEL) + "   " +
              c(f"Deck {len(p.deck)}", CYN) + "   " +
              c("Relics: " + ", ".join(RELICS[r]["name"] for r in p.relics), MAG))
        if p.potions:
            print(c("  Potions: " + ", ".join(POTIONS[k]["name"] for k in p.potions), MAG))

    def map_screen(self):
        while True:
            clear()
            print()
            self.header()
            print()
            for line in render_map(self.floors, self.cur_floor, self.cur_idx, self.visited):
                print("  " + line)
            print()
            print(c("   M combat   E elite   ? event   R rest   $ shop   T treasure   B boss",
                    GRY))
            ans = prompt(c("\n  choose a path (letter) / (i)nspect deck / (q)uit > ",
                           YEL)).lower()
            if ans in ("i", "inspect", "deck"):
                self.deck_screen()
                continue
            if ans in ("q", "quit"):
                if prompt(c("  Abandon the run? (y/N) ", RED)).lower().startswith("y"):
                    raise SystemExit(0)
                continue
            if not ans:
                continue
            i = ord(ans[0]) - ord("a")
            nf = self.cur_floor + 1
            if nf >= FLOORS:
                return None
            valid = (range(len(self.floors[0])) if self.cur_floor == -1
                     else self.floors[self.cur_floor][self.cur_idx]["edges"])
            if i in valid:
                self.visited.append((nf, i))
                self.cur_floor, self.cur_idx = nf, i
                return self.floors[nf][i]["type"]

    def deck_screen(self):
        clear()
        p = self.player
        print(c("\n  RELICS\n", BOLD, MAG))
        for r in p.relics:
            print(f"   {c(RELICS[r]['name'].ljust(20), MAG)} {RELICS[r]['desc']}")
        if p.potions:
            print(c("\n  POTIONS\n", BOLD, MAG))
            for k in p.potions:
                print(f"   {c(POTIONS[k]['name'].ljust(20), MAG)} {POTIONS[k]['desc']}")
        deck = sorted(p.deck, key=lambda k: (k.type, k.name))
        print(c(f"\n  YOUR DECK — {len(deck)} cards\n", BOLD, YEL))
        print_cards(deck, numbered=False)
        pause()

    # ── node handlers ──
    def do_combat(self, kind):
        enemies, label = make_encounter(self.act, kind, self.cur_floor)
        cb = Combat(self.player, enemies, f"{label}  (floor {self.cur_floor + 1})")
        cb.run()
        self.player.block = 0
        self.player.st.clear()
        self.floors_cleared += 1
        if kind == "elite":
            self.elites_killed += 1
        if self.player.has("burning_blood"):
            self.player.hp = min(self.player.max_hp, self.player.hp + 6)
        if self.player.has("meat_on_bone") and self.player.hp < self.player.max_hp // 2:
            self.player.hp = min(self.player.max_hp, self.player.hp + 12)
        self.rewards(kind)

    def rewards(self, kind):
        p = self.player
        gold = {"monster": random.randint(10, 20), "elite": random.randint(25, 35),
                "boss": random.randint(80, 100)}[kind if kind in
                                                 ("monster", "elite", "boss") else "monster"]
        p.gold += gold
        clear()
        print(c("\n  VICTORY!\n", BOLD, GRN))
        print(c(f"  You find {gold} gold.", YEL))
        if kind == "elite" or (kind == "boss"):
            key = random.choice([r for r in RELIC_POOL if r not in p.relics] or RELIC_POOL)
            p.add_relic(key)
            print(c(f"  Relic obtained: {RELICS[key]['name']} — {RELICS[key]['desc']}", MAG))
        if random.random() < (0.6 if kind != "monster" else 0.4) and len(p.potions) < p.max_potions:
            pk = random.choice(list(POTIONS))
            p.potions.append(pk)
            print(c(f"  Potion obtained: {POTIONS[pk]['name']}", MAG))
        print()
        chances = (0.5, 0.38, 0.12) if kind != "monster" else (0.62, 0.31, 0.07)
        choices = [Card(k) for k in random_card_keys(3, chances)]
        if kind == "boss":
            for k in choices:
                k.upgrade()
        print(c("  Choose a card to add to your deck:\n", YEL))
        print_cards(choices)
        ans = prompt(c("\n  card # / (s)kip > ", YEL)).lower()
        if ans.isdigit() and 1 <= int(ans) <= 3:
            p.deck.append(choices[int(ans) - 1])
            print(c(f"  {choices[int(ans) - 1].name} added to your deck.", GRN))
            pause()

    def do_rest(self):
        p = self.player
        clear()
        print(c("\n  A CAMPFIRE\n", BOLD, YEL))
        heal = max(1, int(p.max_hp * 0.3))
        print(f"   1. Rest — heal {heal} HP  (you are at {p.hp}/{p.max_hp})")
        print("   2. Smith — upgrade a card")
        ans = prompt(c("\n  > ", YEL))
        if ans == "2":
            self.upgrade_screen()
        else:
            p.hp = min(p.max_hp, p.hp + heal)
            print(c(f"  You rest. HP {p.hp}/{p.max_hp}.", GRN))
            pause()

    def upgrade_screen(self):
        p = self.player
        opts = [k for k in p.deck if k.upgradable and not k.upgraded]
        if not opts:
            print(c("  Nothing left to upgrade.", GRY))
            pause()
            return
        clear()
        print(c("\n  UPGRADE A CARD\n", BOLD, YEL))
        print_cards(opts)
        idx = read_index(len(opts))
        if idx is not None:
            opts[idx].upgrade()
            print(c(f"  {opts[idx].name} sharpened.", GRN))
            pause()

    def remove_screen(self, free=True):
        p = self.player
        clear()
        print(c("\n  REMOVE A CARD\n", BOLD, YEL))
        print_cards(p.deck)
        idx = read_index(len(p.deck))
        if idx is not None:
            card = p.deck.pop(idx)
            print(c(f"  {card.name} removed.", GRN))
            pause()
            return True
        return False

    def do_treasure(self):
        p = self.player
        clear()
        print(c("\n  A CHEST\n", BOLD, YEL))
        gold = random.randint(25, 60)
        p.gold += gold
        print(c(f"  {gold} gold spills out.", YEL))
        key = random.choice([r for r in RELIC_POOL if r not in p.relics] or RELIC_POOL)
        p.add_relic(key)
        print(c(f"  Relic obtained: {RELICS[key]['name']} — {RELICS[key]['desc']}", MAG))
        pause()

    def do_shop(self):
        p = self.player
        stock_cards = [Card(k) for k in random_card_keys(5)]
        prices = [{"common": 50, "uncommon": 75, "rare": 130, "starter": 50}[k.rarity]
                  + random.randint(-8, 8) for k in stock_cards]
        relic_key = random.choice([r for r in RELIC_POOL if r not in p.relics] or RELIC_POOL)
        relic_price = random.randint(140, 190)
        potion_keys = random.sample(list(POTIONS), 2)
        potion_prices = [random.randint(45, 65) for _ in potion_keys]
        removal_price = 75
        removed = False
        while True:
            clear()
            print(c("\n  THE MERCHANT\n", BOLD, YEL))
            print(c(f"  Your gold: {p.gold}\n", YEL))
            print_cards(stock_cards)
            print("  " + "   ".join(c(f"[{i+1}] {pr}g", YEL) for i, pr in enumerate(prices)))
            print()
            if relic_key:
                print(f"   6. {c(RELICS[relic_key]['name'], MAG)} — {RELICS[relic_key]['desc']} "
                      f"{c(str(relic_price) + 'g', YEL)}")
            for i, pk in enumerate(potion_keys):
                print(f"   {7+i}. {c(POTIONS[pk]['name'], MAG)} — {POTIONS[pk]['desc']} "
                      f"{c(str(potion_prices[i]) + 'g', YEL)}")
            if not removed:
                print(f"   9. {c('Card removal service', CYN)} "
                      f"{c(str(removal_price) + 'g', YEL)}")
            ans = prompt(c("\n  buy # / (l)eave > ", YEL)).lower()
            if ans in ("l", "leave", "", "q"):
                return
            if ans.isdigit():
                n = int(ans)
                if 1 <= n <= len(stock_cards):
                    if p.gold >= prices[n - 1]:
                        p.gold -= prices[n - 1]
                        p.deck.append(stock_cards.pop(n - 1))
                        prices.pop(n - 1)
                    else:
                        self.too_poor()
                elif n == 6 and relic_key:
                    if p.gold >= relic_price:
                        p.gold -= relic_price
                        p.add_relic(relic_key)
                        relic_key = None
                    else:
                        self.too_poor()
                elif n in (7, 8) and n - 7 < len(potion_keys):
                    i = n - 7
                    if len(p.potions) >= p.max_potions:
                        print(c("  No potion slots free.", GRY))
                        pause()
                    elif p.gold >= potion_prices[i]:
                        p.gold -= potion_prices[i]
                        p.potions.append(potion_keys.pop(i))
                        potion_prices.pop(i)
                    else:
                        self.too_poor()
                elif n == 9 and not removed:
                    if p.gold >= removal_price:
                        if self.remove_screen():
                            p.gold -= removal_price
                            removed = True
                    else:
                        self.too_poor()

    def too_poor(self):
        print(c("  You cannot afford that.", RED))
        pause()

    def do_event(self):
        p = self.player
        event = random.choice(EVENTS)
        clear()
        print(c(f"\n  {event['title']}\n", BOLD, CYN))
        for line in wrap(event["text"], 78):
            print("   " + line)
        print()
        opts = event["options"]
        for i, (label, _) in enumerate(opts):
            print(f"   {i + 1}. {label}")
        ans = prompt(c("\n  > ", YEL))
        idx = int(ans) - 1 if ans.isdigit() and 1 <= int(ans) <= len(opts) else 0
        print()
        opts[idx][1](self, p)
        pause()

    # ── run loop ──
    def play(self):
        while True:
            kind = self.map_screen()
            if kind is None:
                break
            if kind in ("monster", "elite", "boss"):
                self.do_combat(kind)
                if kind == "boss":
                    if self.act >= 3:
                        return "win"
                    self.next_act()
            elif kind == "rest":
                self.do_rest()
            elif kind == "shop":
                self.do_shop()
            elif kind == "treasure":
                self.do_treasure()
            elif kind == "event":
                self.do_event()
        return "win"

    def next_act(self):
        self.act += 1
        self.floors = generate_map()
        self.cur_floor = -1
        self.cur_idx = 0
        self.visited = []
        p = self.player
        p.max_hp += 8
        p.hp = min(p.max_hp, p.hp + 20)
        clear()
        print(c(f"\n  The stairs spiral upward...  ACT {self.act}\n", BOLD, YEL))
        print(c(f"  Max HP +8, you recover some strength. HP {p.hp}/{p.max_hp}", GRN))
        pause()


# ──────────────────────────────────────────────────────────────────────── events ──
def _ev_heal(g, p):
    n = int(p.max_hp * 0.25)
    p.hp = min(p.max_hp, p.hp + n)
    print(c(f"  You heal {n} HP.", GRN))


def _ev_maxhp(g, p):
    p.max_hp += 8
    p.hp += 8
    print(c("  Max HP +8.", GRN))


def _ev_curse_relic(g, p):
    key = random.choice([r for r in RELIC_POOL if r not in p.relics] or RELIC_POOL)
    p.add_relic(key)
    p.deck.append(Card("regret"))
    print(c(f"  You gain {RELICS[key]['name']} — and a Regret curse.", MAG))


def _ev_gold(g, p):
    n = random.randint(50, 90)
    p.gold += n
    print(c(f"  You find {n} gold.", YEL))


def _ev_gamble(g, p):
    if random.random() < 0.5:
        n = random.randint(80, 140)
        p.gold += n
        print(c(f"  The bones favour you: +{n} gold.", GRN))
    else:
        loss = min(p.gold, random.randint(40, 80))
        p.gold -= loss
        print(c(f"  You lose {loss} gold.", RED))


def _ev_upgrade(g, p):
    opts = [k for k in p.deck if k.upgradable and not k.upgraded]
    if opts:
        k = random.choice(opts)
        k.upgrade()
        print(c(f"  {k.name} glows with new power.", GRN))
    else:
        print(c("  Nothing here can be improved.", GRY))


def _ev_remove(g, p):
    loss = 8
    p.hp = max(1, p.hp - loss)
    print(c(f"  The rite costs you {loss} HP.", RED))
    g.remove_screen()


def _ev_potion(g, p):
    if len(p.potions) < p.max_potions:
        k = random.choice(list(POTIONS))
        p.potions.append(k)
        print(c(f"  You pocket a {POTIONS[k]['name']}.", MAG))
    else:
        p.gold += 30
        print(c("  No room for potions — you sell it for 30 gold.", YEL))


def _ev_nothing(g, p):
    print(c("  You walk on. Nothing happens.", GRY))


def _ev_hurt_card(g, p):
    p.hp = max(1, p.hp - 10)
    keys = random_card_keys(1, (0.2, 0.5, 0.3))
    p.deck.append(Card(keys[0]))
    print(c(f"  You lose 10 HP but learn {CARDS[keys[0]]['name']}.", MAG))


EVENTS = [
    dict(title="THE CLERIC", text="A robed figure offers her services to weary travellers, "
                                  "for a price that is not always gold.",
         options=[("Ask for healing", _ev_heal),
                  ("Ask her to purge a card (lose 8 HP)", _ev_remove),
                  ("Leave", _ev_nothing)]),
    dict(title="GOLDEN IDOL", text="A heavy idol sits on a pressure plate. Taking it will "
                                   "surely trigger something.",
         options=[("Take it", _ev_curse_relic), ("Leave it alone", _ev_nothing)]),
    dict(title="BONFIRE SPIRITS", text="Spirits circle a green flame. Offer something to "
                                       "the fire and it may give something back.",
         options=[("Offer a card to the flames", _ev_remove),
                  ("Warm yourself", _ev_heal)]),
    dict(title="DEAD ADVENTURER", text="A corpse in dented armour, still clutching a purse. "
                                       "Something killed him and may still be near.",
         options=[("Search the body", _ev_gold), ("Pay respects and move on", _ev_nothing)]),
    dict(title="THE GAMBLER", text="A grinning stranger rattles a cup of knucklebones. "
                                   "'Double or nothing, friend.'",
         options=[("Roll the bones", _ev_gamble), ("Decline", _ev_nothing)]),
    dict(title="WHETSTONE", text="An old whetstone hums faintly on a stone plinth.",
         options=[("Sharpen a card", _ev_upgrade), ("Leave", _ev_nothing)]),
    dict(title="THE SACRED FOUNTAIN", text="Clear water bubbles up through cracked "
                                           "marble. It smells faintly of iron.",
         options=[("Drink deeply", _ev_maxhp), ("Fill a vial", _ev_potion),
                  ("Move on", _ev_nothing)]),
    dict(title="THE LIBRARY", text="Shelves of half-burnt tomes. One book is still warm, "
                                   "and reading it hurts.",
         options=[("Read the warm book", _ev_hurt_card), ("Take a nap instead", _ev_heal)]),
]


# ─────────────────────────────────────────────────────────────────────── records ──
def load_records():
    try:
        with open(SAVE_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_record(rec):
    recs = load_records()
    recs.append(rec)
    recs = sorted(recs, key=lambda r: (-r["floors"], -r.get("act", 1)))[:10]
    try:
        with open(SAVE_FILE, "w") as f:
            json.dump(recs, f, indent=1)
    except OSError:
        pass
    return recs


# ────────────────────────────────────────────────────────────────────────── main ──
TITLE = r"""
   ███████╗██████╗ ██╗██████╗ ███████╗     ██████╗ ███████╗     █████╗ ███████╗██╗  ██╗
   ██╔════╝██╔══██╗██║██╔══██╗██╔════╝    ██╔═══██╗██╔════╝    ██╔══██╗██╔════╝██║  ██║
   ███████╗██████╔╝██║██████╔╝█████╗      ██║   ██║█████╗      ███████║███████╗███████║
   ╚════██║██╔═══╝ ██║██╔══██╗██╔══╝      ██║   ██║██╔══╝      ██╔══██║╚════██║██╔══██║
   ███████║██║     ██║██║  ██║███████╗    ╚██████╔╝██║         ██║  ██║███████║██║  ██║
   ╚══════╝╚═╝     ╚═╝╚═╝  ╚═╝╚══════╝     ╚═════╝ ╚═╝         ╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝
"""


def title_screen():
    clear()
    print(c(TITLE, RED))
    print(c("        A deckbuilding climb. Three acts. One deck. Do not die.\n", GRY))
    recs = load_records()
    if recs:
        print(c("        BEST RUNS", BOLD, YEL))
        for r in recs[:5]:
            outcome = c("ASCENDED", GRN) if r.get("won") else c("died", GRY)
            print(f"          act {r.get('act', 1)}  floor {r['floors']:<3} "
                  f"{outcome}  killed by {r.get('killer', '?')}")
        print()
    prompt(c("        [enter] to climb  ", YEL))


def main():
    random.seed()
    while True:
        title_screen()
        g = Game()
        killer = "—"
        try:
            result = g.play()
        except Defeat as e:
            killer = str(e) or "the Spire"
            result = "dead"
        clear()
        won = result == "win"
        if won:
            print(c("\n\n   YOU HAVE ASCENDED THE SPIRE.\n", BOLD, YEL))
        else:
            print(c("\n\n   YOU DIED.\n", BOLD, RED))
            print(c(f"   Slain by {killer} on floor {g.cur_floor + 1} of act {g.act}.\n", GRY))
        p = g.player
        print(c(f"   Act {g.act}   floors cleared {g.floors_cleared}   "
                f"elites slain {g.elites_killed}", WHT))
        print(c(f"   Final deck: {len(p.deck)} cards   gold {p.gold}", CYN))
        print(c("   Relics: " + ", ".join(RELICS[r]["name"] for r in p.relics), MAG))
        print()
        save_record(dict(act=g.act, floors=g.floors_cleared, won=won, killer=killer,
                         deck=len(p.deck), gold=p.gold))
        if not prompt(c("   Climb again? (y/N) ", YEL)).lower().startswith("y"):
            return


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(RESET + "\n  The Spire waits.\n")
