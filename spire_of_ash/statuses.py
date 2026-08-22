"""Status effect metadata.

The short label is what fits inside a chip; the name and description are what a
client shows when the player asks what a status actually does. Colour is a
front-end concern and belongs to whichever client is rendering.
"""

from . import balance as B

_VULN_PCT = int(round((B.VULNERABLE_MULT - 1) * 100))
_WEAK_PCT = int(round((1 - B.WEAK_MULT) * 100))
_FRAIL_PCT = int(round((1 - B.FRAIL_MULT) * 100))

# key: (label, name, description). The description is written for a reader who
# can already see the stack count on the chip, so it says "this much" rather
# than repeating the number.
STATUSES = {
    "strength": ("Str", "Strength",
                 "Attacks deal this much extra damage."),
    "dexterity": ("Dex", "Dexterity",
                  "Cards give this much extra Block."),
    "vulnerable": ("Vuln", "Vulnerable",
                   f"Takes {_VULN_PCT}% more damage from attacks. "
                   "Loses 1 stack at the end of its turn."),
    "weak": ("Weak", "Weak",
             f"Attacks deal {_WEAK_PCT}% less damage. "
             "Loses 1 stack at the end of its turn."),
    "frail": ("Frail", "Frail",
              f"Block gained from cards is reduced by {_FRAIL_PCT}%. "
              "Loses 1 stack at the end of its turn."),
    "poison": ("Psn", "Poison",
               "Loses this much HP at the start of its turn, ignoring Block. "
               "Then loses 1 stack."),
    "thorns": ("Thorns", "Thorns",
               "Anything that attacks it takes this much damage back."),
    "ritual": ("Ritual", "Ritual",
               "Gains this much Strength at the start of each of its turns."),
    "metallicize": ("Metal", "Metallicize",
                    "Gain this much Block at the end of your turn."),
    "demonform": ("Demon", "Demon Form",
                  "Gain this much Strength at the start of each turn."),
    "barricade": ("Barri", "Barricade",
                  "Block is no longer lost at the start of your turn."),
    "feelnopain": ("NoPain", "Feel No Pain",
                   "Gain this much Block whenever a card is Exhausted."),
    "rupture": ("Rupt", "Rupture",
                "Gain this much Strength whenever a card costs you HP."),
    "juggernaut": ("Jugg", "Juggernaut",
                   "Deal this much damage to a random enemy whenever you gain "
                   "Block."),
    "venombloom": ("Bloom", "Venom Bloom",
                   "Apply this much Poison to every enemy at the start of your "
                   "turn."),
    "afterimage": ("After", "After Image",
                   "Gain this much Block whenever you play a card."),
    "thousandcuts": ("Cuts", "A Thousand Cuts",
                     "Deal this much damage to every enemy whenever you play a "
                     "card."),
    "envenom": ("Envm", "Envenom",
                "Unblocked attack damage applies this much Poison."),
    "flexloss": ("", "", ""),   # internal bookkeeping, never shown

    # ── The Stormbound ──
    "stormcoil": ("Coil", "Coil",
                  f"At the end of your turn, each Coil strikes a random enemy "
                  f"for {B.COIL_DAMAGE}, plus your Focus."),
    "frostward": ("Frost", "Frost",
                  f"At the end of your turn, each Frost grants "
                  f"{B.FROST_BLOCK} Block, plus your Focus."),
    "focus": ("Focus", "Focus",
              "Every Coil and every Frost is this much stronger."),
    "dynamo": ("Dynamo", "Dynamo",
               "Gain this much Coil at the start of each turn."),
    "conductor": ("Cond", "Conductor",
                  "Gain this much Coil whenever you play a Skill."),
    "lightningrod": ("Rod", "Lightning Rod",
                     "Gain this much Coil whenever you gain Block."),
    "echoform": ("Echo", "Echo Form",
                 "The first card you play each turn is played twice."),

    # ── The Penitent ──
    "wrath": ("Wrath", "Wrath",
              f"Your attacks deal {B.WRATH_MULT}x damage — and so do theirs."),
    "calm": ("Calm", "Calm",
             f"Leaving Calm returns {B.CALM_EXIT_ENERGY} Energy."),
    "divinity": ("Div", "Divinity",
                 f"Your attacks deal {B.DIVINITY_MULT}x damage. "
                 "It ends at the end of your turn."),
    "mantra": ("Mantra", "Mantra",
               f"At {B.MANTRA_FOR_DIVINITY} Mantra you enter Divinity and the "
               "count starts over."),
    "vigour": ("Vig", "Vigour",
               "Your next Attack deals this much extra damage, then it fades."),
    "devotion": ("Devo", "Devotion",
                 "Gain this much Mantra at the start of each turn."),
    "mentalfortress": ("Fort", "Mental Fortress",
                       "Gain this much Block whenever you change stance."),
    "rushdown": ("Rush", "Rushdown",
                 "Draw this many cards whenever you enter Wrath."),
    "fasting": ("Fast", "Fasting",
                "You begin each turn with this much less Energy."),
    "masterreality": ("Real", "Master Reality",
                      "Cards created during combat arrive upgraded."),

    # ── The Gravewright ──
    "soulfire": ("Soul", "Soulfire",
                 "Deal this much damage to ALL enemies whenever a card is "
                 "Exhausted."),
    "ashenembrace": ("Embr", "Ashen Embrace",
                     "Draw this many cards whenever a card is Exhausted."),
    "soulforge": ("Forge", "Soul Forge",
                  "Gain this much Strength whenever a card is Exhausted."),
    "lichcrown": ("Lich", "Lich Crown",
                  "Exhaust this many cards from the top of your draw pile at "
                  "the start of each turn."),
    "phylactery": ("Phyl", "Phylactery",
                   f"The next blow that would kill you leaves you at "
                   f"{B.PHYLACTERY_HP} HP instead, and spends a stack."),

    # ── The Emberbrewer ──
    "volatility": ("Volat", "Volatility",
                   "Deal this much damage to ALL enemies whenever you drink a "
                   "potion."),
    "elixirward": ("Ward", "Elixir Ward",
                   "Gain this much Block whenever you drink a potion."),
    "potency": ("Poten", "Potency",
                "Your potions take effect twice."),
    "philosopher": ("Philo", "Philosopher's Stone",
                    "Gain this much Energy at the start of each turn."),
    "alchemicalheart": ("Heart", "Alchemical Heart",
                        "Brew this many potions at the start of each turn, "
                        "belt space permitting."),
    "brewmaster": ("Brew", "Brewmaster",
                   "Gain this much Strength whenever you brew a potion."),

    # ── The Hexbinder ──
    "hexbloom": ("Hex", "Hexbloom",
                 "Deal this much damage to an enemy whenever you weaken it."),
    "entrenched": ("Grudge", "Long Grudge",
                   "Its debuffs no longer wear off."),
    "dreadaura": ("Dread", "Dread Aura",
                  "Apply this much Weak to ALL enemies at the start of each "
                  "turn."),
    "bindingcircle": ("Circle", "Binding Circle",
                      "Apply this much Weak, Vulnerable and Frail to ALL "
                      "enemies at the start of each turn."),
    "evilwithin": ("Evil", "Evil Within",
                   f"At the start of each turn, deal this much damage to every "
                   f"enemy carrying {B.EVIL_WITHIN_STACKS} or more debuff "
                   "stacks."),
}

STATUS_LABELS = {key: label for key, (label, _, _) in STATUSES.items()}

# statuses that tick down at the end of the owner's turn
DECAYING = ("vulnerable", "weak", "frail")

# what the Hexbinder counts as a debuff, and what Hexbloom answers to
DEBUFFS = ("weak", "vulnerable", "frail")

# only one of these can be held at a time; entering one clears the others
STANCES = ("wrath", "calm", "divinity")


def describe(key):
    """(name, description) for a status key. Unknown keys fall back to the key."""
    label, name, desc = STATUSES.get(key, ("", "", ""))
    return name or label or key, desc


def visible(statuses):
    """(key, label, amount) for each status worth showing."""
    out = []
    for key, amount in statuses.items():
        label = STATUS_LABELS.get(key, "")
        if amount and label:
            out.append((key, label, amount))
    return out
