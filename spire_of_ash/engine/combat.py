"""One encounter.

This class is pure: it never prints and never reads input. Where the old version
blocked on `prompt()` to pick a target or choose a card to exhaust, the choice is
now supplied by the caller alongside the action. `Card.requires` tells a client
which extra choice a card needs before it sends the play.
"""

from .. import balance as B
from ..content.potions import POTIONS
from ..statuses import DECAYING
from .card import Card
from .combatant import damage_after_modifiers
from .errors import Defeat, InvalidAction


class Combat:
    def __init__(self, player, enemies, rng, label="", kind="monster", fx=None):
        self.player = player
        self.enemies = enemies
        # Ordered record of what happened, for a client that wants to play the
        # turn out rather than cut to the result. The Run owns the list and
        # clears it per action — see Run.apply — because a killing blow has to
        # outlive `self.combat = None`.
        self.fx = [] if fx is None else fx
        for e in enemies:
            e.allies = enemies
        self.rng = rng
        self.label = label
        self.kind = kind
        self.draw_pile = [k.copy() for k in player.deck]
        rng.shuffle(self.draw_pile)
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
        self.cards_played = 0
        self.exhausts_this_combat = 0
        # set for the duration of one card's effect when the client pre-declared
        # a choice the effect will consume
        self.pending_exhaust = None

    # ── helpers ──
    def living(self):
        return [e for e in self.enemies if e.alive]

    def over(self):
        return not self.living()

    def msg(self, text):
        """Append a plain-text line to the combat log.

        The old engine baked ANSI colour codes in here, so the web layer had to
        strip them back out with a regex. Styling is the client's job.

        Every line is also an fx event, which is what lets a client scroll the
        log in step with the action instead of dumping it all at the end.
        """
        self.log.append(text)
        self.log = self.log[-B.COMBAT_LOG_LEN:]
        self.emit("log", text=text)

    # ── the effect stream ──
    def emit(self, k, **data):
        """Record one thing that happened, in the order it happened.

        This is data, not presentation: it says an enemy took 7 damage through
        3 block, not that anything should flash red. What a client does with
        it — stage it over a second, or ignore it entirely, as the terminal
        does — is the client's business.
        """
        self.fx.append(dict(k=k, **data))

    def who(self, combatant):
        """Identify a combatant the way the view model does: "player", or an
        index into `enemies`."""
        if combatant is self.player:
            return "player"
        for i, e in enumerate(self.enemies):
            if e is combatant:
                return i
        return None

    def lock_draw(self):
        self.no_draw = True

    def _relics(self, hook):
        return self.player.relic_hooks(hook)

    # ── damage & healing ──
    def player_attack(self, target, base, times=1, str_mult=1, potion=False):
        for _ in range(times):
            if not target or not target.alive:
                return
            self.emit("swing", src="player", dst=self.who(target))
            if potion:
                dmg = base
                if target.s("vulnerable"):
                    dmg = int(dmg * B.VULNERABLE_MULT)
            else:
                dmg = damage_after_modifiers(self.player, base, target, str_mult)
                self.attacks_total += 1
                self.attacks_this_turn += 1
                self.attacked_this_turn = True
                for hook in self._relics("on_attack"):
                    changed = hook(self, dmg)
                    if changed is not None:
                        dmg = changed
            lost = self.damage(target, dmg)
            if lost > 0 and not potion and self.player.s("envenom"):
                self.apply(target, "poison", self.player.s("envenom"))
            if target.s("thorns") and not potion:
                self.lose_hp(self.player, target.s("thorns"))

    def enemy_attack(self, enemy, base):
        dmg = damage_after_modifiers(enemy, base, self.player)
        self.emit("swing", src=self.who(enemy), dst="player")
        self.damage(self.player, dmg)
        if self.player.s("thorns") and enemy.alive:
            self.damage(enemy, self.player.s("thorns"), ignore_block=True)

    def damage(self, target, dmg, ignore_block=False):
        """Apply damage through Block. Returns HP actually lost."""
        if dmg <= 0:
            return 0
        absorbed = 0
        if not ignore_block:
            absorbed = min(target.block, dmg)
            target.block -= absorbed
            dmg -= absorbed
        if dmg > 0:
            target.hp -= dmg
        # Emitted before die(), which raises: the blow that kills you is the
        # one most worth showing.
        self.emit("damage", who=self.who(target), amount=dmg, blocked=absorbed,
                  hp=max(0, target.hp), block=target.block)
        if dmg <= 0:
            return 0
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
        self.emit("lose_hp", who=self.who(target), amount=n,
                  hp=max(0, target.hp))
        if from_card and target is self.player and self.player.s("rupture"):
            self.apply(self.player, "strength", self.player.s("rupture"))
        if target is self.player and target.hp <= 0:
            self.die()
        if target is not self.player and target.hp <= 0:
            self.kill(target)

    def kill(self, enemy):
        enemy.hp = 0
        enemy.alive = False
        self.emit("death", who=self.who(enemy))
        self.msg(f"{enemy.name} is slain!")
        for hook in self._relics("on_kill"):
            hook(self, enemy)
        od = enemy.spec.get("on_death")
        if od:
            od(self, enemy)

    def heal(self, target, n):
        before = target.hp
        target.hp = min(target.max_hp, target.hp + n)
        if target.hp != before:
            self.emit("heal", who=self.who(target), amount=target.hp - before,
                      hp=target.hp)

    # ── block & statuses ──
    def gain_block(self, who, amount):
        if amount <= 0:
            return
        if who is self.player:
            amount += who.s("dexterity")
            if who.s("frail"):
                amount = int(amount * B.FRAIL_MULT)
        amount = max(0, amount)
        who.block += amount
        if amount:
            self.emit("block", who=self.who(who), amount=amount, total=who.block)
        if who is self.player and who.s("juggernaut"):
            targets = self.living()
            if targets:
                self.player_attack(self.rng.choice(targets), who.s("juggernaut"),
                                   potion=True)

    def apply(self, target, key, n):
        if n == 0 or target is None or not target.alive:
            return
        target.st[key] += n
        self.emit("status", who=self.who(target), key=key, n=n,
                  total=target.st[key])

    # ── piles ──
    def draw(self, n):
        if self.no_draw:
            return
        for _ in range(n):
            if len(self.hand) >= B.HAND_LIMIT:
                self.msg("Hand is full.")
                return
            if not self.draw_pile:
                if not self.discard:
                    return
                self.draw_pile = self.discard
                self.discard = []
                self.rng.shuffle(self.draw_pile)
                self.emit("shuffle", n=len(self.draw_pile))
            card = self.draw_pile.pop()
            self.hand.append(card)
            self.emit("draw", key=card.key)

    def add_card_to_pile(self, card, to_draw=False):
        if to_draw:
            self.draw_pile.insert(self.rng.randint(0, len(self.draw_pile)), card)
        else:
            self.discard.append(card)
        self.msg(f"{card.name} added to your {'draw' if to_draw else 'discard'} pile.")

    def exhaust_card(self, card):
        self.exhausted.append(card)
        self.exhausts_this_combat += 1
        self.emit("exhaust", key=card.key)
        if self.player.s("feelnopain"):
            self.gain_block(self.player, self.player.s("feelnopain"))
        for hook in self._relics("on_exhaust"):
            hook(self, card)

    def gain_energy(self, n):
        self.energy += n

    # ── special card behaviours ──
    def grit_exhaust(self, choose):
        """Exhaust a card from hand — the player's pick if the card lets them."""
        if not self.hand:
            return
        idx = None
        if choose and self.pending_exhaust is not None:
            idx = self.pending_exhaust
            if not 0 <= idx < len(self.hand):
                idx = None
        if idx is None:
            idx = self.rng.randrange(len(self.hand))
        card = self.hand.pop(idx)
        self.exhaust_card(card)
        self.msg(f"Exhausted {card.name}.")

    def discard_random(self, n):
        for _ in range(n):
            if not self.hand:
                return
            card = self.hand.pop(self.rng.randrange(len(self.hand)))
            self.discard.append(card)
            self.emit("discard", key=card.key)
            self.msg(f"Discarded {card.name}.")

    def multiply_poison(self, target, mult):
        if not target or not target.alive:
            return
        cur = target.s("poison")
        if cur <= 0:
            self.msg(f"{target.name} carries no Poison.")
            return
        self.apply(target, "poison", cur * (mult - 1))
        self.msg(f"The venom in {target.name} blooms to {target.s('poison')}.")

    def bounce_poison(self, amount, times):
        for _ in range(times):
            alive = self.living()
            if not alive:
                return
            self.apply(self.rng.choice(alive), "poison", amount)

    def bane(self, target, dmg):
        if not target:
            return
        poisoned = target.s("poison") > 0
        self.player_attack(target, dmg)
        if poisoned:
            self.player_attack(target, dmg)

    def energy_next_turn(self, n):
        self.bonus_energy_next += n

    def on_card_played(self):
        """After Image / A Thousand Cuts fire once per card played."""
        p = self.player
        self.cards_played += 1
        if p.s("afterimage"):
            self.gain_block(p, p.s("afterimage"))
        if p.s("thousandcuts"):
            for e in self.living():
                self.damage(e, p.s("thousandcuts"))
        for hook in self._relics("on_card_played"):
            hook(self)

    def armaments(self, all_cards):
        candidates = [k for k in self.hand if k.upgradable and not k.upgraded]
        if not candidates:
            return
        if all_cards:
            for k in candidates:
                k.upgrade()
            self.msg("Armaments upgrades your hand!")
        else:
            k = self.rng.choice(candidates)
            k.upgrade()
            self.msg(f"Armaments upgrades {k.name}.")

    def second_wind(self, per):
        keep, n = [], 0
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
            self.msg(f"Reaper heals {total} HP.")

    # ── turn flow ──
    def start_combat(self):
        p = self.player
        p.block = 0
        p.st.clear()
        for hook in self._relics("on_combat_start"):
            hook(self)
        for e in self.enemies:
            e.roll_intent()

    def player_turn_start(self):
        self.emit("turn", phase="player_start")
        p = self.player
        if not p.s("barricade"):
            p.block = 0
        self.energy = p.max_energy + self.bonus_energy_next
        self.bonus_energy_next = 0
        self.no_draw = False
        self.attacks_this_turn = 0
        self.attacked_this_turn = False
        for hook in self._relics("on_turn_start"):
            hook(self)
        if p.s("demonform"):
            self.apply(p, "strength", p.s("demonform"))
        if p.s("venombloom"):
            for e in self.living():
                self.apply(e, "poison", p.s("venombloom"))
        if p.s("poison"):
            self.lose_hp(p, p.s("poison"))
            p.st["poison"] -= 1
        extra = sum(hook(self) for hook in self._relics("draw_bonus"))
        self.draw(B.BASE_DRAW + extra)

    def player_turn_end(self):
        self.emit("turn", phase="player_end")
        p = self.player
        if p.s("metallicize"):
            self.gain_block(p, p.s("metallicize"))
        if p.s("flexloss"):
            self.apply(p, "strength", -p.s("flexloss"))
            p.st["flexloss"] = 0
        # These two say nothing to the player on their own: the HP simply went
        # away at end of turn, with no attack anywhere on screen to blame.
        burns = [k for k in self.hand if k.key == "burn"]
        if burns:
            self.msg(f"Burn sears you for {2 * len(burns)}.")
        for _ in burns:
            self.lose_hp(p, 2)
        if any(k.key == "regret" for k in self.hand):
            self.msg(f"Regret costs you {len(self.hand)} HP.")
            self.lose_hp(p, len(self.hand))
        for hook in self._relics("on_turn_end"):
            hook(self)
        self.discard.extend(self.hand)
        self.hand = []
        for key in DECAYING:
            if p.st[key] > 0:
                p.st[key] -= 1

    def enemy_turns(self):
        self.emit("turn", phase="enemy_start")
        # living() is a snapshot: an enemy can die partway through this loop —
        # to Thorns, to another enemy's move, to its own poison tick — and must
        # not go on acting. It used to finish every hit of a multi-hit attack
        # after it was already dead, which read as damage from nowhere.
        for e in self.living():
            if not e.alive:
                continue
            # Brackets one enemy's whole turn, so a client can give each of
            # them its own beat rather than resolving five at once. The finally
            # matters: the enemy may die inside, and the player may die inside,
            # which leaves by raising Defeat.
            self.emit("act", who=self.who(e), move=e.intent)
            try:
                self._enemy_turn(e)
            finally:
                self.emit("act_end", who=self.who(e))

    def _enemy_turn(self, e):
        if e.s("poison"):
            self.lose_hp(e, e.s("poison"))
            e.st["poison"] -= 1
            if not e.alive:
                return
        e.block = 0
        if e.s("ritual"):
            self.apply(e, "strength", e.s("ritual"))
        m = e.moves[e.intent]
        if m["kind"] == "attack":
            for _ in range(m["hits"]):
                if not e.alive:
                    break
                self.enemy_attack(e, m["dmg"])
        if m["fn"] and e.alive:
            m["fn"](self, e)
        if not e.alive:
            return
        self.msg(f"{e.name} uses {e.intent}.")
        e.history.append(e.intent)
        e.turn += 1
        for key in DECAYING:
            if e.st[key] > 0:
                e.st[key] -= 1
        if e.alive:
            e.roll_intent()

    def end_combat(self):
        """Fire post-combat relics. Called once, after the last enemy dies."""
        for hook in self._relics("on_combat_end"):
            hook(self)

    # ── player actions ──
    def resolve_target(self, target_idx):
        """Turn a client-supplied enemy index into an Enemy."""
        alive = self.living()
        if target_idx is None:
            if len(alive) == 1:
                return alive[0]
            raise InvalidAction("This card needs a target.")
        if not isinstance(target_idx, int) or isinstance(target_idx, bool):
            raise InvalidAction("Target must be an enemy index.")
        if not (0 <= target_idx < len(self.enemies)) or not self.enemies[target_idx].alive:
            raise InvalidAction("No living enemy there.")
        return self.enemies[target_idx]

    def play_card(self, idx, target_idx=None, exhaust=None):
        if not isinstance(idx, int) or isinstance(idx, bool):
            raise InvalidAction("Card index must be a number.")
        if not (0 <= idx < len(self.hand)):
            raise InvalidAction("No such card in hand.")
        card = self.hand[idx]
        if not card.playable:
            raise InvalidAction(f"{card.name} is unplayable.")
        if card.cost == "X":
            if self.energy <= 0:
                raise InvalidAction("Not enough energy.")
            self.x_spent = cost = self.energy
        else:
            cost = card.cost
            if cost > self.energy:
                raise InvalidAction("Not enough energy.")
        target = self.resolve_target(target_idx) if card.targeted else None

        self.energy -= cost
        self.hand.pop(idx)
        # Emitted before the effect runs, so a client can fly the card at its
        # target and land the damage on arrival rather than before it.
        self.emit("play", idx=idx, key=card.key, cost=cost,
                  target=self.who(target) if target else None)
        # The played card leaves hand before its effect runs, so a choice the
        # player made against the pre-play hand has to shift down by one.
        if exhaust is not None and isinstance(exhaust, int) and exhaust > idx:
            exhaust -= 1
        self.pending_exhaust = exhaust
        try:
            card.play(self, target)
        finally:
            self.pending_exhaust = None
        self.on_card_played()
        self.msg(f"You play {card.name}.")
        if card.exhaust:
            self.exhaust_card(card)
        elif card.type != "POWER":       # powers leave play entirely
            self.discard.append(card)
            self.emit("discard", key=card.key)

    def use_potion(self, idx, target_idx=None):
        p = self.player
        if not isinstance(idx, int) or isinstance(idx, bool):
            raise InvalidAction("Potion index must be a number.")
        if not (0 <= idx < len(p.potions)):
            raise InvalidAction("No such potion.")
        spec = POTIONS[p.potions[idx]]
        target = self.resolve_target(target_idx) if spec.get("targeted") else None
        p.potions.pop(idx)
        spec["fx"](self, target)
        self.msg(f"You drink the {spec['name']}.")

    # ── persistence ──
    def to_dict(self):
        return {
            "label": self.label, "kind": self.kind, "turn": self.turn,
            "energy": self.energy, "x_spent": self.x_spent, "log": list(self.log),
            "no_draw": self.no_draw, "attacks_this_turn": self.attacks_this_turn,
            "attacks_total": self.attacks_total,
            "attacked_this_turn": self.attacked_this_turn,
            "bonus_energy_next": self.bonus_energy_next,
            "cards_played": self.cards_played,
            "exhausts_this_combat": self.exhausts_this_combat,
            "enemies": [e.to_dict() for e in self.enemies],
            "hand": [k.to_dict() for k in self.hand],
            "draw_pile": [k.to_dict() for k in self.draw_pile],
            "discard": [k.to_dict() for k in self.discard],
            "exhausted": [k.to_dict() for k in self.exhausted],
        }

    @classmethod
    def from_dict(cls, d, player, rng):
        from .combatant import Enemy
        enemies = [Enemy.from_dict(e, rng) for e in d["enemies"]]
        cb = cls.__new__(cls)
        cb.player = player
        cb.enemies = enemies
        for e in enemies:
            e.allies = enemies
        cb.rng = rng
        cb.label = d["label"]
        cb.kind = d["kind"]
        cb.turn = d["turn"]
        cb.energy = d["energy"]
        cb.x_spent = d["x_spent"]
        cb.log = list(d["log"])
        cb.no_draw = d["no_draw"]
        cb.attacks_this_turn = d["attacks_this_turn"]
        cb.attacks_total = d["attacks_total"]
        cb.attacked_this_turn = d["attacked_this_turn"]
        cb.bonus_energy_next = d["bonus_energy_next"]
        cb.cards_played = d.get("cards_played", 0)
        cb.exhausts_this_combat = d.get("exhausts_this_combat", 0)
        cb.hand = [Card.from_dict(k) for k in d["hand"]]
        cb.draw_pile = [Card.from_dict(k) for k in d["draw_pile"]]
        cb.discard = [Card.from_dict(k) for k in d["discard"]]
        cb.exhausted = [Card.from_dict(k) for k in d["exhausted"]]
        cb.pending_exhaust = None
        # Transient: an effect stream describes one action, so a restored
        # combat starts with nothing to replay. Run.apply rebinds this.
        cb.fx = []
        return cb
