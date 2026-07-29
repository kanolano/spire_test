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
    "asleep": ("Asleep", "Asleep",
               "Dormant. It will not act until something rouses it."),
    "flexloss": ("", "", ""),   # internal bookkeeping, never shown
}

STATUS_LABELS = {key: label for key, (label, _, _) in STATUSES.items()}

# statuses that tick down at the end of the owner's turn
DECAYING = ("vulnerable", "weak", "frail")
DEBUFFS = ("vulnerable", "weak", "frail", "poison")


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
