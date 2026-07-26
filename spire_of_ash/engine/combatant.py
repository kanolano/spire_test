"""Combatants: the shared base, the player, and enemies.

`Enemy.intent_text` used to read the current player out of the `PLAYER_REF`
module global in order to preview Vulnerable. The player is now passed in, which
is what allows two runs to exist in one process.
"""

from collections import defaultdict

from .. import balance as B
from ..content.classes import CLASSES, DEFAULT_CLASS
from ..content.monsters import MONSTERS
from ..content.relics import RELICS
from ..statuses import visible
from .card import Card


class Combatant:
    def __init__(self, name, hp):
        self.name = name
        self.max_hp = hp
        self.hp = hp
        self.block = 0
        self.st = defaultdict(int)
        self.alive = True

    def s(self, key):
        """Amount of a status, 0 if absent."""
        return self.st[key]

    def statuses(self):
        """(key, label, amount) triples worth displaying."""
        return visible(self.st)

    def _base_dict(self):
        return {"name": self.name, "max_hp": self.max_hp, "hp": self.hp,
                "block": self.block, "st": dict(self.st), "alive": self.alive}

    def _load_base(self, d):
        self.name = d["name"]
        self.max_hp = d["max_hp"]
        self.hp = d["hp"]
        self.block = d["block"]
        self.st = defaultdict(int, d["st"])
        self.alive = d["alive"]


def damage_after_modifiers(attacker, base, target, str_mult=1):
    """Strength, Weak and Vulnerable applied to a raw attack value."""
    dmg = base + attacker.s("strength") * str_mult
    if attacker.s("weak"):
        dmg = int(dmg * B.WEAK_MULT)
    if target and target.s("vulnerable"):
        dmg = int(dmg * B.VULNERABLE_MULT)
    return max(0, dmg)


class Enemy(Combatant):
    def __init__(self, key, act=1, rng=None, hp=None):
        spec = MONSTERS[key]
        if hp is None:
            lo, hi = spec["hp"]
            hp = int(rng.randint(lo, hi) * (1 + B.ACT_HP_SCALING * (act - 1)))
        super().__init__(spec["name"], hp)
        self.key = key
        self.rng = rng
        self.turn = 0
        self.history = []
        self.intent = None
        self.allies = [self]
        if act >= B.FINAL_ACT:
            self.st["strength"] += B.ACT3_ENEMY_STRENGTH

    @property
    def spec(self):
        return MONSTERS[self.key]

    @property
    def moves(self):
        return self.spec["moves"]

    @property
    def elite(self):
        return self.spec.get("elite", False)

    @property
    def boss(self):
        return self.spec.get("boss", False)

    def roll_intent(self):
        self.intent = self.spec["pick"](self)

    def intent_preview(self, player):
        """Structured intent for a client to render. None when nothing is set."""
        if not self.intent:
            return None
        m = self.moves[self.intent]
        kind = m["kind"]
        if kind == "attack":
            return {"kind": "attack",
                    "damage": damage_after_modifiers(self, m["dmg"], player),
                    "hits": m["hits"],
                    "extra": bool(m["fn"])}
        return {"kind": kind}

    # ── persistence ──
    def to_dict(self):
        d = self._base_dict()
        d.update(key=self.key, turn=self.turn, history=list(self.history),
                 intent=self.intent)
        return d

    @classmethod
    def from_dict(cls, d, rng):
        e = cls(d["key"], act=1, rng=rng, hp=d["hp"])
        e._load_base(d)
        e.turn = d["turn"]
        e.history = list(d["history"])
        e.intent = d["intent"]
        return e


class Player(Combatant):
    def __init__(self, cls=DEFAULT_CLASS):
        self.cls = cls if cls in CLASSES else DEFAULT_CLASS
        d = CLASSES[self.cls]
        super().__init__(d["name"], d["hp"])
        self.gold = B.STARTING_GOLD
        self.max_energy = d["energy"]
        self.deck = [Card(k) for k in d["deck"]]
        self.relics = [d["relic"]]
        self.potions = []
        self.max_potions = B.MAX_POTIONS

    def has(self, relic):
        return relic in self.relics

    def add_relic(self, key):
        self.relics.append(key)
        hook = RELICS[key].get("on_pickup")
        if hook:
            hook(self)

    def relic_hooks(self, name):
        """Every hook of the given name across the relics the player owns."""
        for key in self.relics:
            hook = RELICS[key].get(name)
            if hook:
                yield hook

    # ── persistence ──
    def to_dict(self):
        d = self._base_dict()
        d.update(cls=self.cls, gold=self.gold, max_energy=self.max_energy,
                 deck=[k.to_dict() for k in self.deck],
                 relics=list(self.relics), potions=list(self.potions),
                 max_potions=self.max_potions)
        return d

    @classmethod
    def from_dict(cls, d):
        p = cls(d["cls"])
        p._load_base(d)
        p.gold = d["gold"]
        p.max_energy = d["max_energy"]
        p.deck = [Card.from_dict(k) for k in d["deck"]]
        p.relics = list(d["relics"])
        p.potions = list(d["potions"])
        p.max_potions = d["max_potions"]
        return p
