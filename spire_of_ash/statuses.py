"""Status effect metadata.

Only the short display label lives here — colour is a front-end concern and
belongs to whichever client is rendering.
"""

STATUS_LABELS = {
    "strength": "Str",
    "dexterity": "Dex",
    "vulnerable": "Vuln",
    "weak": "Weak",
    "frail": "Frail",
    "poison": "Psn",
    "thorns": "Thorns",
    "ritual": "Ritual",
    "metallicize": "Metal",
    "demonform": "Demon",
    "barricade": "Barri",
    "feelnopain": "NoPain",
    "rupture": "Rupt",
    "juggernaut": "Jugg",
    "venombloom": "Bloom",
    "afterimage": "After",
    "thousandcuts": "Cuts",
    "envenom": "Envm",
    "flexloss": "",       # internal bookkeeping, never shown
    "asleep": "Asleep",
}

# statuses that tick down at the end of the owner's turn
DECAYING = ("vulnerable", "weak", "frail")
DEBUFFS = ("vulnerable", "weak", "frail", "poison")


def visible(statuses):
    """(key, label, amount) for each status worth showing."""
    out = []
    for key, amount in statuses.items():
        label = STATUS_LABELS.get(key, "")
        if amount and label:
            out.append((key, label, amount))
    return out
