"""The Card runtime object.

A card is fully described by its key plus whether it has been upgraded, which is
what makes saving a deck cheap.
"""

from ..content.cards import CARDS


class Card:
    """One card instance. Look up rules text and effects via `spec`."""

    def __init__(self, key, upgraded=False):
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
        self.upgraded = upgraded

    @property
    def spec(self):
        return CARDS[self.key]

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

    @property
    def requires(self):
        """Extra choice the client must supply when playing this card, if any."""
        fn = self.spec.get("requires")
        return fn(self) if fn else None

    def v(self, base, up):
        """Pick the base or upgraded value."""
        return up if self.upgraded else base

    def play(self, combat, target):
        self.spec.get("fx", lambda *a: None)(combat, self, target)

    def upgrade(self):
        if self.upgradable and not self.upgraded:
            self.upgraded = True
            return True
        return False

    def copy(self):
        return Card(self.key, self.upgraded)

    # ── persistence ──
    def to_dict(self):
        return {"key": self.key, "upgraded": self.upgraded}

    @classmethod
    def from_dict(cls, d):
        return cls(d["key"], d.get("upgraded", False))

    def __repr__(self):
        return f"<Card {self.name}>"
