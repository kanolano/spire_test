"""One run through the Spire, as an explicit state machine.

This replaces two parallel implementations: the terminal `Game`, which blocked on
`input()` at every choice, and the web `Session`, which re-implemented the same
node handlers without prompts. They had already drifted apart.

Clients drive a `Run` through exactly three things:

    run.state()          a snapshot of engine state — no side effects
    run.apply(action)    advance the machine; raises InvalidAction if refused
    run.pending          what the run is waiting for right now

Nothing here prints or reads input, so the terminal client and the HTTP server
share one implementation of the rules.
"""

from .. import balance as B
from ..content.classes import CLASSES, DEFAULT_CLASS
from ..content.events import EVENTS, preview_of
from ..content.pools import random_card_keys, roll_relic
from ..content.potions import POTIONS
from .card import Card
from .combat import Combat
from .combatant import Player
from .dungeon import generate_map, make_encounter
from .errors import Defeat, InvalidAction
from ..rng import Rng
from ..seeds import daily_seed


class Run:
    def __init__(self, cls=None, seed=None, rng=None):
        self.rng = rng if rng is not None else Rng(seed)
        self.new_run(cls)

    # ── lifecycle ──
    def new_run(self, cls=None, seed=None):
        """With no class chosen yet the run parks on the select screen."""
        if seed is not None:
            self.rng = Rng(seed)
        self.player = Player(cls or DEFAULT_CLASS)
        self.act = 1
        self.floors = generate_map(self.rng)
        self.cur_floor = -1
        self.cur_idx = 0
        self.visited = []
        self.floors_cleared = 0
        self.elites_killed = 0
        self.combat = None
        self.reward = None
        self.shop = None
        self.event = None
        self.choose = None
        self.treasure = None
        self.banner = None
        self.killer = "—"
        self.screen = "map" if cls else "select"

    @property
    def finished(self):
        return self.screen in ("gameover", "win")

    @property
    def pending(self):
        """What the run is waiting for, as data a client can act on."""
        if self.screen == "select":
            return {"kind": "class", "options": list(CLASSES)}
        if self.screen == "combat":
            return {"kind": "combat_turn"}
        if self.screen == "reward":
            r = self.reward
            return {"kind": "card_reward", "count": len(r["cards"]),
                    "skippable": True,
                    "card": not r.get("card_taken"),
                    "relic": bool(r["relic"]) and not r.get("relic_taken"),
                    "potion": bool(r["potion"]) and not r.get("potion_taken")}
        if self.screen == "choose":
            return {"kind": self.choose["kind"], "count": len(self.choose["cards"]),
                    "skippable": self.choose["allow_skip"]}
        if self.screen == "rest":
            return {"kind": "campfire"}
        if self.screen == "shop":
            return {"kind": "shop"}
        if self.screen == "event":
            return {"kind": "event",
                    "resolved": self.event["result"] is not None,
                    "count": len(self.event["options"])}
        if self.screen == "treasure":
            return {"kind": "acknowledge"}
        if self.screen == "map":
            return {"kind": "map_node", "options": self.reachable()}
        return None

    # ── map helpers ──
    def reachable(self):
        if self.cur_floor == -1:
            return list(range(len(self.floors[0])))
        if self.cur_floor >= len(self.floors) - 1:
            return []
        return list(self.floors[self.cur_floor][self.cur_idx]["edges"])

    def to_map(self):
        self.screen = "map"
        self.reward = self.shop = self.event = self.choose = self.treasure = None

    def game_over(self, killer):
        self.killer = killer or "the Spire"
        self.screen = "gameover"
        self.combat = None

    def win(self):
        self.screen = "win"
        self.combat = None

    def summary(self, won):
        """The leaderboard row for this run."""
        return dict(act=self.act, floors=self.floors_cleared, won=won,
                    killer=self.killer, deck=len(self.player.deck),
                    gold=self.player.gold, cls=self.player.name)

    # ── action dispatch ──
    def apply(self, action):
        if not isinstance(action, dict):
            raise InvalidAction("Action must be an object.")
        kind = action.get("type")
        handler = _HANDLERS.get(kind)
        if handler is None:
            raise InvalidAction(f"Unknown action {kind!r}.")
        # A banner survives any number of state() reads and clears once the
        # player does something. state() itself must stay side-effect free.
        self.banner = None
        handler(self, action)
        return self.state()

    def _need(self, screen):
        if self.screen != screen:
            raise InvalidAction(f"Not on the {screen} screen.")

    @staticmethod
    def _index(action, key="idx", allow_none=False):
        value = action.get(key)
        if value is None and allow_none:
            return None
        if not isinstance(value, int) or isinstance(value, bool):
            raise InvalidAction(f"{key!r} must be a number.")
        return value

    # ── class select ──
    def _do_new_run(self, action):
        cls = action.get("cls")
        if cls is not None and not isinstance(cls, str):
            raise InvalidAction("Class must be a name.")
        seed = action.get("seed")
        if action.get("daily"):
            seed = daily_seed()
        elif seed is not None and (not isinstance(seed, int) or isinstance(seed, bool)):
            raise InvalidAction("Seed must be a number.")
        self.new_run(cls if cls in CLASSES else DEFAULT_CLASS, seed)

    # ── map ──
    def _do_map(self, action):
        self._need("map")
        idx = self._index(action)
        if idx not in self.reachable():
            raise InvalidAction("That node is not reachable from here.")
        nf = self.cur_floor + 1
        if nf >= len(self.floors):
            raise InvalidAction("There is nothing above you.")
        self.visited.append([nf, idx])
        self.cur_floor, self.cur_idx = nf, idx
        kind = self.floors[nf][idx]["type"]
        if kind in ("monster", "elite", "boss"):
            self.start_combat(kind)
        elif kind == "rest":
            self.screen = "rest"
        elif kind == "shop":
            self.open_shop()
        elif kind == "treasure":
            self.open_treasure()
        elif kind == "event":
            self.open_event()

    def next_act(self):
        self.act += 1
        self.floors = generate_map(self.rng)
        self.cur_floor = -1
        self.cur_idx = 0
        self.visited = []
        p = self.player
        p.max_hp += B.ACT_MAX_HP_BONUS
        p.hp = min(p.max_hp, p.hp + B.ACT_HEAL)
        self.banner = (f"The stairs spiral upward — ACT {self.act}",
                       f"Max HP +{B.ACT_MAX_HP_BONUS}. You recover some strength: "
                       f"{p.hp}/{p.max_hp}.")

    # ── combat ──
    def start_combat(self, kind):
        enemies, label = make_encounter(self.rng, self.act, kind, self.cur_floor)
        cb = Combat(self.player, enemies, self.rng,
                    f"{label} — floor {self.cur_floor + 1}", kind)
        self.combat = cb
        self.screen = "combat"
        try:
            cb.start_combat()
            cb.player_turn_start()
        except Defeat as e:
            self.game_over(str(e))
            return
        if cb.over():
            self.victory()

    def guard(self, fn):
        """Run a combat step, turning death or a clear board into a screen change."""
        cb = self.combat
        try:
            fn()
        except Defeat as e:
            self.game_over(str(e))
            return False
        if cb is self.combat and cb.over():
            self.victory()
            return False
        return True

    def _do_play(self, action):
        self._need("combat")
        idx = self._index(action)
        target = self._index(action, "target", allow_none=True)
        exhaust = self._index(action, "exhaust", allow_none=True)
        self.guard(lambda: self.combat.play_card(idx, target, exhaust))

    def _do_potion(self, action):
        self._need("combat")
        idx = self._index(action)
        target = self._index(action, "target", allow_none=True)
        self.guard(lambda: self.combat.use_potion(idx, target))

    def _do_end_turn(self, action):
        self._need("combat")
        cb = self.combat

        def step():
            cb.player_turn_end()
            if cb.over():
                return
            cb.enemy_turns()
            cb.turn += 1
            if cb.over():
                return
            cb.player_turn_start()
        self.guard(step)

    def victory(self):
        cb, p = self.combat, self.player
        kind = cb.kind
        p.block = 0
        p.st.clear()
        self.floors_cleared += 1
        if kind == "elite":
            self.elites_killed += 1
        cb.end_combat()

        lo, hi = B.GOLD_REWARD[kind]
        gold = self.rng.randint(lo, hi)
        p.gold += gold
        # Gold is banked outright; everything else waits to be claimed, so the
        # player can look at a relic before it is bolted to them.
        rew = {"gold": gold, "kind": kind, "relic": None, "potion": None,
               "relic_taken": False, "potion_taken": False, "card_taken": False,
               "log": list(cb.log[-B.REWARD_LOG_LINES:])}
        if kind in ("elite", "boss"):
            rew["relic"] = roll_relic(self.rng, p.relics)
        chance = B.POTION_DROP_CHANCE["monster" if kind == "monster" else "other"]
        if self.rng.random() < chance and len(p.potions) < p.max_potions:
            rew["potion"] = self.rng.choice(list(POTIONS))
        chances = B.CARD_RARITY_CHANCES["monster" if kind == "monster" else "other"]
        cards = [Card(k) for k in
                 random_card_keys(self.rng, B.REWARD_CARD_COUNT, chances, p.cls)]
        if kind == "boss":
            for k in cards:
                k.upgrade()
        rew["cards"] = cards
        self.reward = rew
        self.combat = None
        self.screen = "reward"

    def _claim_relic(self):
        r = self.reward
        if not r["relic"]:
            raise InvalidAction("There is no relic to take.")
        if r.get("relic_taken"):
            raise InvalidAction("You have already taken it.")
        self.player.add_relic(r["relic"])
        r["relic_taken"] = True

    def _claim_potion(self):
        r, p = self.reward, self.player
        if not r["potion"]:
            raise InvalidAction("There is no potion to take.")
        if r.get("potion_taken"):
            raise InvalidAction("You have already taken it.")
        if len(p.potions) >= p.max_potions:
            raise InvalidAction("Your potion slots are full.")
        p.potions.append(r["potion"])
        r["potion_taken"] = True

    def _claim_card(self, action):
        r = self.reward
        idx = self._index(action, allow_none=True)
        if idx is None:
            return
        if r.get("card_taken"):
            raise InvalidAction("You have already taken a card.")
        cards = r["cards"]
        if not 0 <= idx < len(cards):
            raise InvalidAction("No such reward card.")
        self.player.deck.append(cards[idx])
        r["card_taken"] = True

    def _do_reward(self, action):
        """Claim one item. The screen stays open until `reward_done`."""
        self._need("reward")
        what = action.get("what", "card")
        if what == "relic":
            self._claim_relic()
        elif what == "potion":
            self._claim_potion()
        elif what == "card":
            self._claim_card(action)
        else:
            raise InvalidAction(f"Cannot take {what!r}.")

    def _do_reward_done(self, action):
        self._need("reward")
        kind = self.reward["kind"]
        self.to_map()
        if kind == "boss":
            if self.act >= B.FINAL_ACT:
                self.win()
            else:
                self.next_act()

    # ── campfire ──
    def _do_rest(self, action):
        self._need("rest")
        p = self.player
        p.hp = min(p.max_hp, p.hp + max(1, int(p.max_hp * B.REST_HEAL_FRACTION)))
        self.to_map()

    def _do_smith(self, action):
        self._need("rest")
        opts = [k for k in self.player.deck if k.upgradable and not k.upgraded]
        if not opts:
            self._do_rest(action)
            return
        self.open_choose("upgrade", "Choose a card to upgrade", opts, "map")

    # ── card picker ──
    def open_choose(self, kind, title, cards, back, allow_skip=False):
        self.choose = {"kind": kind, "title": title, "back": back,
                       "allow_skip": allow_skip, "cards": cards, "price": 0}
        self.screen = "choose"

    def _do_choose(self, action):
        self._need("choose")
        idx = self._index(action, allow_none=True)
        kind, back = self.choose["kind"], self.choose["back"]
        cards = self.choose["cards"]
        if idx is not None:
            if not 0 <= idx < len(cards):
                raise InvalidAction("No such card.")
            card = cards[idx]
            if kind == "upgrade":
                card.upgrade()
            elif kind == "duplicate":
                self.player.deck.append(card.copy())
            elif kind == "remove" and card in self.player.deck:
                self.player.deck.remove(card)
                price = self.choose["price"]
                if self.shop and price:
                    self.player.gold -= price
                    self.shop["removed"] = True
        self.choose = None
        if back == "shop" and self.shop:
            self.screen = "shop"
        else:
            self.to_map()

    # ── shop ──
    def open_shop(self):
        p = self.player
        cards = [Card(k) for k in
                 random_card_keys(self.rng, B.SHOP_CARD_COUNT, cls=p.cls)]
        jitter = B.SHOP_PRICE_JITTER
        potions = self.rng.sample(list(POTIONS), B.SHOP_POTION_COUNT)
        self.shop = {
            "cards": cards,
            "prices": [B.SHOP_CARD_PRICES[k.rarity] + self.rng.randint(-jitter, jitter)
                       for k in cards],
            "relic": roll_relic(self.rng, p.relics),
            "relic_price": self.rng.randint(*B.SHOP_RELIC_PRICE),
            "potions": potions,
            "potion_prices": [self.rng.randint(*B.SHOP_POTION_PRICE) for _ in potions],
            "removal_price": B.SHOP_REMOVAL_PRICE,
            "removed": False,
        }
        self.screen = "shop"

    def _do_shop_buy(self, action):
        self._need("shop")
        what = action.get("what")
        idx = self._index(action, allow_none=True) or 0
        p, shop = self.player, self.shop
        if what == "card":
            if not 0 <= idx < len(shop["cards"]):
                raise InvalidAction("No such card for sale.")
            price = shop["prices"][idx]
            if p.gold < price:
                raise InvalidAction("You cannot afford that.")
            p.gold -= price
            p.deck.append(shop["cards"].pop(idx))
            shop["prices"].pop(idx)
        elif what == "relic":
            if not shop["relic"]:
                raise InvalidAction("The relic is already sold.")
            if p.gold < shop["relic_price"]:
                raise InvalidAction("You cannot afford that.")
            p.gold -= shop["relic_price"]
            p.add_relic(shop["relic"])
            shop["relic"] = None
        elif what == "potion":
            if not 0 <= idx < len(shop["potions"]):
                raise InvalidAction("No such potion for sale.")
            if len(p.potions) >= p.max_potions:
                raise InvalidAction("You have no room for another potion.")
            price = shop["potion_prices"][idx]
            if p.gold < price:
                raise InvalidAction("You cannot afford that.")
            p.gold -= price
            p.potions.append(shop["potions"].pop(idx))
            shop["potion_prices"].pop(idx)
        elif what == "removal":
            if shop["removed"]:
                raise InvalidAction("You have already used the removal service.")
            if p.gold < shop["removal_price"]:
                raise InvalidAction("You cannot afford that.")
            if not p.deck:
                raise InvalidAction("Your deck is empty.")
            self.open_choose("remove", "Choose a card to remove", list(p.deck), "shop")
            self.choose["price"] = shop["removal_price"]
        else:
            raise InvalidAction(f"Cannot buy {what!r}.")

    def _do_shop_leave(self, action):
        self._need("shop")
        self.to_map()

    # ── treasure ──
    def open_treasure(self):
        p = self.player
        gold = self.rng.randint(*B.TREASURE_GOLD)
        p.gold += gold
        key = roll_relic(self.rng, p.relics)
        p.add_relic(key)
        self.treasure = {"gold": gold, "relic": key}
        self.screen = "treasure"

    def _do_treasure_done(self, action):
        self._need("treasure")
        self.to_map()

    # ── events ──
    def open_event(self):
        idx = self.rng.randrange(len(EVENTS))
        ev = EVENTS[idx]
        self.event = {"index": idx, "title": ev["title"], "text": ev["text"],
                      "options": [{"label": label, "preview": preview_of(fn)}
                                  for label, fn in ev["options"]],
                      "result": None, "then": None}
        self.screen = "event"

    def _do_event_choose(self, action):
        self._need("event")
        if self.event["result"] is not None:
            raise InvalidAction("You have already chosen.")
        idx = self._index(action)
        options = EVENTS[self.event["index"]]["options"]
        if not 0 <= idx < len(options):
            raise InvalidAction("No such option.")
        result = options[idx][1](self, self.player)
        self.event["result"] = result["text"] or "Nothing happens."
        self.event["then"] = result.get("then")

    # Follow-up card pickers an event can ask for.
    FOLLOWUPS = {
        "remove": ("Choose a card to remove", lambda p: list(p.deck)),
        "duplicate": ("Choose a card to duplicate", lambda p: list(p.deck)),
        "upgrade": ("Choose a card to upgrade",
                    lambda p: [k for k in p.deck if k.upgradable and not k.upgraded]),
    }

    def _do_event_done(self, action):
        self._need("event")
        followup = self.FOLLOWUPS.get(self.event["then"])
        if followup:
            title, pick = followup
            cards = pick(self.player)
            if cards:
                self.open_choose(self.event["then"], title, cards, "map")
                return
        self.to_map()

    # ── snapshot ──
    def state(self):
        """Engine state as plain data. Never mutates the run."""
        p = self.player
        cb = self.combat
        st = {
            "screen": self.screen,
            "act": self.act,
            "floor": self.cur_floor + 1,
            "floors_cleared": self.floors_cleared,
            "elites_killed": self.elites_killed,
            "banner": self.banner,
            "killer": self.killer,
            "pending": self.pending,
            "seed": self.rng.seed,
            "player": {
                "name": p.name, "cls": p.cls, "hp": p.hp, "max_hp": p.max_hp,
                "block": p.block, "gold": p.gold, "deck_size": len(p.deck),
                "statuses": p.statuses(), "relics": list(p.relics),
                "potions": list(p.potions), "max_potions": p.max_potions,
                "energy": cb.energy if cb else 0, "max_energy": p.max_energy,
            },
            "deck": [k.to_dict() for k in p.deck],
            "map": {
                "floors": [[{"type": n["type"], "edges": n["edges"]} for n in f]
                           for f in self.floors],
                "cur_floor": self.cur_floor, "cur_idx": self.cur_idx,
                "visited": self.visited, "reachable": self.reachable(),
            },
        }
        if cb:
            st["combat"] = {
                "label": cb.label, "kind": cb.kind, "turn": cb.turn + 1,
                "energy": cb.energy,
                "enemies": [{
                    "name": e.name, "hp": max(0, e.hp), "max_hp": e.max_hp,
                    "block": e.block, "alive": e.alive, "statuses": e.statuses(),
                    "intent": e.intent_preview(p) if e.alive else None,
                } for e in cb.enemies],
                "hand": [k.to_dict() for k in cb.hand],
                "draw": len(cb.draw_pile), "discard": len(cb.discard),
                "exhaust": len(cb.exhausted),
                "log": cb.log[-8:],
            }
        # These payloads hold live Card objects; a snapshot must be plain data.
        for name in ("reward", "shop", "choose"):
            payload = getattr(self, name)
            if payload is not None:
                st[name] = _cards_out(payload, "cards")
        for name in ("event", "treasure"):
            payload = getattr(self, name)
            if payload is not None:
                st[name] = dict(payload)
        return st

    # ── persistence ──
    def to_dict(self):
        d = {
            "version": 1,
            "rng": self.rng.to_dict(),
            "player": self.player.to_dict(),
            "act": self.act, "floors": self.floors,
            "cur_floor": self.cur_floor, "cur_idx": self.cur_idx,
            "visited": self.visited, "floors_cleared": self.floors_cleared,
            "elites_killed": self.elites_killed, "screen": self.screen,
            "killer": self.killer, "banner": self.banner,
            "combat": self.combat.to_dict() if self.combat else None,
            "treasure": self.treasure,
            "event": self.event,
            "reward": _cards_out(self.reward, "cards"),
            "choose": _cards_out(self.choose, "cards"),
            "shop": _cards_out(self.shop, "cards"),
        }
        return d

    @classmethod
    def from_dict(cls, d):
        run = cls.__new__(cls)
        run.rng = Rng.from_dict(d["rng"])
        run.player = Player.from_dict(d["player"])
        run.act = d["act"]
        run.floors = d["floors"]
        run.cur_floor = d["cur_floor"]
        run.cur_idx = d["cur_idx"]
        run.visited = d["visited"]
        run.floors_cleared = d["floors_cleared"]
        run.elites_killed = d["elites_killed"]
        run.screen = d["screen"]
        run.killer = d["killer"]
        run.banner = tuple(d["banner"]) if d["banner"] else None
        run.combat = (Combat.from_dict(d["combat"], run.player, run.rng)
                      if d["combat"] else None)
        run.treasure = d["treasure"]
        run.event = d["event"]
        run.reward = _cards_in(d["reward"], "cards")
        run.choose = _cards_in(d["choose"], "cards")
        run.shop = _cards_in(d["shop"], "cards")
        return run


def _cards_out(payload, key):
    """Serialise a screen payload, converting its Card list to plain dicts."""
    if payload is None:
        return None
    out = dict(payload)
    out[key] = [k.to_dict() for k in payload[key]]
    return out


def _cards_in(payload, key):
    if payload is None:
        return None
    out = dict(payload)
    out[key] = [Card.from_dict(k) for k in payload[key]]
    return out


_HANDLERS = {
    "new_run": Run._do_new_run,
    "map": Run._do_map,
    "play": Run._do_play,
    "potion": Run._do_potion,
    "end_turn": Run._do_end_turn,
    "reward": Run._do_reward,
    "reward_done": Run._do_reward_done,
    "rest": Run._do_rest,
    "smith": Run._do_smith,
    "choose": Run._do_choose,
    "shop_buy": Run._do_shop_buy,
    "shop_leave": Run._do_shop_leave,
    "event_choose": Run._do_event_choose,
    "event_done": Run._do_event_done,
    "treasure_done": Run._do_treasure_done,
}
