"""One encounter.

This class is pure: it never prints and never reads input. Where the old version
blocked on `prompt()` to pick a target or choose a card to exhaust, the choice is
now supplied by the caller alongside the action. `Card.requires` tells a client
which extra choice a card needs before it sends the play.
"""

from .. import balance as B
from ..content.potions import POTIONS
from ..statuses import DEBUFFS, DECAYING, STANCES
from .card import Card
from .combatant import damage_after_modifiers
from .errors import Defeat, InvalidAction


class Combat:
    def __init__(self, player, enemies, rng, label="", kind="monster"):
        self.player = player
        self.enemies = enemies
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
        self.kills = 0
        self.echoed_this_turn = False
        # what was played *before* the card resolving right now — Sanctity asks
        self.last_played_type = None
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
        """
        self.log.append(text)
        self.log = self.log[-B.COMBAT_LOG_LEN:]

    def lock_draw(self):
        self.no_draw = True

    def _relics(self, hook):
        return self.player.relic_hooks(hook)

    # ── damage & healing ──
    def player_attack(self, target, base, times=1, str_mult=1, potion=False):
        for _ in range(times):
            if not target or not target.alive:
                return
            if potion:
                dmg = base
                if target.s("vulnerable"):
                    dmg = int(dmg * B.VULNERABLE_MULT)
            else:
                bonus = self.player.s("vigour")
                if bonus:
                    self.player.st["vigour"] = 0
                dmg = damage_after_modifiers(self.player, base + bonus, target,
                                             str_mult)
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
        p = self.player
        if p.s("phylactery"):
            p.st["phylactery"] -= 1
            p.hp = min(p.max_hp, B.PHYLACTERY_HP)
            self.msg("Your phylactery cracks — the ash spits you back out.")
            return
        p.hp = 0
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
        self.kills += 1
        self.msg(f"{enemy.name} is slain!")
        for hook in self._relics("on_kill"):
            hook(self, enemy)
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
            amount = int(amount * B.FRAIL_MULT)
        amount = max(0, amount)
        who.block += amount
        if who is self.player and who.s("lightningrod"):
            self.channel("stormcoil", who.s("lightningrod"))
        if who is self.player and who.s("juggernaut"):
            targets = self.living()
            if targets:
                self.player_attack(self.rng.choice(targets), who.s("juggernaut"),
                                   potion=True)

    def apply(self, target, key, n):
        if n == 0 or target is None or not target.alive:
            return
        target.st[key] += n
        weakened = key in DEBUFFS if n > 0 else key == "strength"
        if weakened and target is not self.player and self.player.s("hexbloom"):
            self.damage(target, self.player.s("hexbloom"))

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
            self.hand.append(self.draw_pile.pop())

    def add_card_to_pile(self, card, to_draw=False):
        if self.player.s("masterreality"):
            card.upgrade()
        if to_draw:
            self.draw_pile.insert(self.rng.randint(0, len(self.draw_pile)), card)
        else:
            self.discard.append(card)
        self.msg(f"{card.name} added to your {'draw' if to_draw else 'discard'} pile.")

    def add_new_card(self, key, n=1, to_draw=False):
        """Conjure fresh cards into a pile — Wounds, Burns, an Insight.

        Cards are built here rather than in the card table so that
        `content.cards` never has to import the engine back.
        """
        for _ in range(n):
            self.add_card_to_pile(Card(key), to_draw)

    def widen_belt(self, n):
        """More potion slots, for the rest of the run."""
        self.player.max_potions += n
        self.msg(f"Your belt now holds {self.player.max_potions} potions.")

    def exhaust_card(self, card):
        p = self.player
        self.exhausted.append(card)
        self.exhausts_this_combat += 1
        if p.s("feelnopain"):
            self.gain_block(p, p.s("feelnopain"))
        if p.s("soulfire"):
            for e in self.living():
                self.damage(e, p.s("soulfire"))
        if p.s("soulforge"):
            self.apply(p, "strength", p.s("soulforge"))
        if p.s("ashenembrace"):
            self.draw(p.s("ashenembrace"))
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

    def on_card_played(self, card=None):
        """After Image / A Thousand Cuts fire once per card played.

        The card itself arrives so a status can care what type it was; relic
        hooks keep the signature they have always had.
        """
        p = self.player
        self.cards_played += 1
        if p.s("afterimage"):
            self.gain_block(p, p.s("afterimage"))
        if p.s("thousandcuts"):
            for e in self.living():
                self.damage(e, p.s("thousandcuts"))
        if card is not None and card.type == "SKILL" and p.s("conductor"):
            self.channel("stormcoil", p.s("conductor"))
        for hook in self._relics("on_card_played"):
            hook(self)
        if card is not None:
            self.last_played_type = card.type

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

    # ── stances (The Penitent) ──
    def stance(self):
        """The stance the player is in, or None."""
        for key in STANCES:
            if self.player.s(key):
                return key
        return None

    def enter_stance(self, name):
        """Move into a stance — or out of every stance, with `None`.

        Only one stance is ever held, so this is the single place that knows
        what leaving one costs and what entering one pays.
        """
        p = self.player
        current = self.stance()
        if current == name:
            return
        if current == "calm":
            self.gain_energy(B.CALM_EXIT_ENERGY)
            self.msg(f"Leaving Calm returns {B.CALM_EXIT_ENERGY} Energy.")
        for key in STANCES:
            p.st[key] = 0
        if name:
            p.st[name] = 1
            self.msg(f"You enter {name.title()}.")
        else:
            self.msg("You settle out of your stance.")
        if p.s("mentalfortress"):
            self.gain_block(p, p.s("mentalfortress"))
        if name == "divinity":
            self.gain_energy(B.DIVINITY_ENERGY)
        if name == "wrath" and p.s("rushdown"):
            self.draw(p.s("rushdown"))

    def gain_mantra(self, n):
        """Mantra spills into Divinity every tenth stack."""
        p = self.player
        p.st["mantra"] += n
        while p.st["mantra"] >= B.MANTRA_FOR_DIVINITY:
            p.st["mantra"] -= B.MANTRA_FOR_DIVINITY
            self.msg("Mantra overflows.")
            self.enter_stance("divinity")

    def wallop(self, target, dmg):
        """Attack, then keep whatever HP the blow actually took as Block."""
        before = target.hp if target else 0
        self.player_attack(target, dmg)
        if target:
            self.gain_block(self.player, max(0, before - target.hp))

    def lesson_learned(self, target, dmg):
        """A kill teaches something: upgrade a card in the deck itself."""
        self.player_attack(target, dmg)
        if not target or target.alive:
            return
        candidates = [k for k in self.player.deck if k.upgradable and not k.upgraded]
        if candidates:
            card = self.rng.choice(candidates)
            card.upgrade()
            self.msg(f"The lesson holds: {card.name} is upgraded for good.")

    def judgment(self, target, threshold):
        if target and target.alive and target.hp <= threshold:
            self.msg(f"{target.name} is found wanting.")
            self.kill(target)

    # ── coils (The Stormbound) ──
    def channel(self, key, n):
        """Gather Coil or Frost, up to what you can hold."""
        p = self.player
        p.st[key] = min(B.COIL_CAP, p.st[key] + n)

    def fire_coils(self):
        """Every Coil strikes a random enemy at the end of your turn."""
        p = self.player
        per = B.COIL_DAMAGE + p.s("focus")
        for _ in range(p.s("stormcoil")):
            alive = self.living()
            if not alive:
                return
            # potion=True: a Coil is not a swing of yours, so Strength, Envenom
            # and the enemy's Thorns all stay out of it.
            self.player_attack(self.rng.choice(alive), per, potion=True)

    def discharge_frost(self):
        frost = self.player.s("frostward")
        if frost:
            self.gain_block(self.player, frost * (B.FROST_BLOCK + self.player.s("focus")))

    def discharge_coils(self, per, target=None):
        """Spend every Coil at once. Returns how many were spent."""
        p = self.player
        coils = p.s("stormcoil")
        if coils <= 0:
            self.msg("You hold no Coil.")
            return 0
        p.st["stormcoil"] = 0
        dmg = coils * per
        targets = [target] if target is not None else self.living()
        for e in targets:
            self.player_attack(e, dmg, potion=True)
        self.msg(f"{coils} Coil discharge for {dmg}.")
        return coils

    # ── the exhaust pile (The Gravewright) ──
    def mill(self, n):
        """Exhaust the top n cards of the draw pile. Returns how many burned."""
        burned = 0
        for _ in range(n):
            if not self.draw_pile:
                if not self.discard:
                    break
                self.draw_pile = self.discard
                self.discard = []
                self.rng.shuffle(self.draw_pile)
            card = self.draw_pile.pop()
            self.exhaust_card(card)
            burned += 1
            self.msg(f"{card.name} crumbles to ash.")
        return burned

    def reclaim(self, n):
        """Pull cards back out of the exhaust pile, at random."""
        got = 0
        while got < n and self.exhausted and len(self.hand) < B.HAND_LIMIT:
            card = self.exhausted.pop(self.rng.randrange(len(self.exhausted)))
            self.hand.append(card)
            got += 1
            self.msg(f"{card.name} claws its way back.")
        return got

    def wake_the_ash(self):
        """Everything exhausted goes back into the draw pile."""
        n = len(self.exhausted)
        for card in self.exhausted:
            self.draw_pile.insert(self.rng.randint(0, len(self.draw_pile)), card)
        self.exhausted = []
        self.msg(f"{n} card(s) rise from the ash.")
        return n

    def exhaust_hand(self):
        """Exhaust every card in hand. Returns the count.

        The hand is taken away first: Ashen Embrace draws into it while this
        runs, and those fresh cards must not burn as well.
        """
        cards, self.hand = self.hand, []
        for card in cards:
            self.exhaust_card(card)
        return len(cards)

    def exhaust_junk(self):
        """Exhaust every Status and Curse in hand. Returns the count."""
        junk = [k for k in self.hand if k.type in ("STATUS", "CURSE")]
        self.hand = [k for k in self.hand if k.type not in ("STATUS", "CURSE")]
        for card in junk:
            self.exhaust_card(card)
        self.msg(f"{len(junk)} dead card(s) go up.")
        return len(junk)

    def cremate(self, per):
        """Burn the hand, and hit everything for what it was worth."""
        n = self.exhaust_hand()
        for e in self.living():
            self.player_attack(e, per * n)

    def funeral_rites(self, per):
        """Burn the hand for Block, then draw its worth back."""
        n = self.exhaust_hand()
        self.gain_block(self.player, per * n)
        self.draw(n)

    def pyre(self, per):
        """Every dead card in hand is fuel."""
        n = self.exhaust_junk()
        for e in self.living():
            self.player_attack(e, per * n)

    def boneyard(self, n, per):
        self.gain_block(self.player, per * self.mill(n))

    # ── the still (The Emberbrewer) ──
    def brew(self, key=None, n=1, quiet_when_full=False):
        """Mix a potion mid-fight. Returns how many made it into the belt."""
        p = self.player
        made = 0
        for _ in range(n):
            if len(p.potions) >= p.max_potions:
                if not quiet_when_full:
                    self.msg("Your potion belt is full.")
                return made
            chosen = key or self.rng.choice(list(POTIONS))
            p.potions.append(chosen)
            made += 1
            self.msg(f"You brew a {POTIONS[chosen]['name']}.")
            if p.s("brewmaster"):
                self.apply(p, "strength", p.s("brewmaster"))
        return made

    def overdose(self, per):
        """Damage every enemy for what the whole belt is worth."""
        dmg = per * len(self.player.potions)
        for e in self.living():
            self.player_attack(e, dmg, potion=True)

    # ── hexes (The Hexbinder) ──
    def debuff_stacks(self, target):
        """How badly a combatant is cursed, counting drained Strength."""
        if not target:
            return 0
        return (sum(max(0, target.s(key)) for key in DEBUFFS)
                + max(0, -target.s("strength")))

    def cleanse(self, who=None):
        """Shed Weak, Vulnerable and Frail. Returns the stacks removed."""
        who = who or self.player
        gone = sum(max(0, who.s(key)) for key in DEBUFFS)
        for key in DEBUFFS:
            who.st[key] = 0
        return gone

    def scapegoat(self, target):
        """Hang your own debuffs on an enemy instead."""
        p = self.player
        moved = 0
        for key in DEBUFFS:
            n = p.s(key)
            if n > 0:
                p.st[key] = 0
                moved += n
                self.apply(target, key, n)
        self.msg(f"{moved} stack(s) find a new home." if moved
                 else "You carry nothing worth passing on.")
        return moved

    def double_debuffs(self):
        for e in self.living():
            for key in DEBUFFS:
                if e.s(key) > 0:
                    self.apply(e, key, e.s(key))
        self.msg("Every curse doubles back.")

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
        p = self.player
        if not p.s("barricade"):
            p.block = 0
        self.energy = p.max_energy + self.bonus_energy_next
        self.bonus_energy_next = 0
        self.energy = max(0, self.energy - p.s("fasting")) + p.s("philosopher")
        self.no_draw = False
        self.attacks_this_turn = 0
        self.attacked_this_turn = False
        self.echoed_this_turn = False
        for hook in self._relics("on_turn_start"):
            hook(self)
        if p.s("demonform"):
            self.apply(p, "strength", p.s("demonform"))
        if p.s("venombloom"):
            for e in self.living():
                self.apply(e, "poison", p.s("venombloom"))
        if p.s("devotion"):
            self.gain_mantra(p.s("devotion"))
        if p.s("dynamo"):
            self.channel("stormcoil", p.s("dynamo"))
        if p.s("lichcrown"):
            self.mill(p.s("lichcrown"))
        if p.s("alchemicalheart"):
            self.brew(n=p.s("alchemicalheart"), quiet_when_full=True)
        if p.s("dreadaura"):
            for e in self.living():
                self.apply(e, "weak", p.s("dreadaura"))
        if p.s("bindingcircle"):
            for e in self.living():
                for key in DEBUFFS:
                    self.apply(e, key, p.s("bindingcircle"))
        if p.s("evilwithin"):
            for e in self.living():
                if self.debuff_stacks(e) >= B.EVIL_WITHIN_STACKS:
                    self.damage(e, p.s("evilwithin"))
        if p.s("poison"):
            self.lose_hp(p, p.s("poison"))
            p.st["poison"] -= 1
        extra = sum(hook(self) for hook in self._relics("draw_bonus"))
        self.draw(B.BASE_DRAW + extra)

    def player_turn_end(self):
        p = self.player
        if p.s("metallicize"):
            self.gain_block(p, p.s("metallicize"))
        self.discharge_frost()
        self.fire_coils()
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
        if p.s("divinity"):
            self.enter_stance(None)

    def enemy_turns(self):
        # living() is a snapshot: an enemy can die partway through this loop —
        # to Thorns, to another enemy's move, to its own poison tick — and must
        # not go on acting. It used to finish every hit of a multi-hit attack
        # after it was already dead, which read as damage from nowhere.
        for e in self.living():
            if not e.alive:
                continue
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
                    if not e.alive:
                        break
                    self.enemy_attack(e, m["dmg"])
            if m["fn"] and e.alive:
                m["fn"](self, e)
            if not e.alive:
                continue
            self.msg(f"{e.name} uses {e.intent}.")
            e.history.append(e.intent)
            e.turn += 1
            if not e.s("entrenched"):
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
        # The played card leaves hand before its effect runs, so a choice the
        # player made against the pre-play hand has to shift down by one.
        if exhaust is not None and isinstance(exhaust, int) and exhaust > idx:
            exhaust -= 1
        self.pending_exhaust = exhaust
        try:
            card.play(self, target)
            if self.player.s("echoform") and not self.echoed_this_turn:
                self.echoed_this_turn = True
                self.msg(f"Echo Form repeats {card.name}.")
                card.play(self, target)
        finally:
            self.pending_exhaust = None
        self.on_card_played(card)
        self.msg(f"You play {card.name}.")
        if card.exhaust:
            self.exhaust_card(card)
        elif card.type != "POWER":       # powers leave play entirely
            self.discard.append(card)

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
        if p.s("potency"):
            spec["fx"](self, target)
        self.msg(f"You drink the {spec['name']}.")
        if p.s("volatility"):
            for e in self.living():
                self.damage(e, p.s("volatility"))
        if p.s("elixirward"):
            self.gain_block(p, p.s("elixirward"))

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
            "kills": self.kills, "echoed_this_turn": self.echoed_this_turn,
            "last_played_type": self.last_played_type,
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
        cb.kills = d.get("kills", 0)
        cb.echoed_this_turn = d.get("echoed_this_turn", False)
        cb.last_played_type = d.get("last_played_type")
        cb.hand = [Card.from_dict(k) for k in d["hand"]]
        cb.draw_pile = [Card.from_dict(k) for k in d["draw_pile"]]
        cb.discard = [Card.from_dict(k) for k in d["discard"]]
        cb.exhausted = [Card.from_dict(k) for k in d["exhausted"]]
        cb.pending_exhaust = None
        return cb
