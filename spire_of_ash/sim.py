"""Headless balance simulation.

Seven classes, 256 cards, 41 monsters and 28 relics is well past the point
where a designer can hold the win rate in their head, and the suite in tests/
deliberately says nothing about balance: it asks whether the rules are obeyed,
not whether the Hexbinder can actually finish act 3. This module answers the
second question the only way it can be answered cheaply — by playing the game
several thousand times and counting.

It is a measuring instrument, not a player. `GreedyPolicy` is a decent floor,
not a good human: it reads damage and Block off the card text and never plans a
turn ahead. So the absolute win rate it reports is not "the" win rate. What it
is good for is *comparison* — between classes, between acts, and between two
commits — because the same crude player meets all of them.

    python3 -m spire_of_ash.sim                      # 60 runs per class
    python3 -m spire_of_ash.sim --runs 500           # tighter numbers
    python3 -m spire_of_ash.sim --classes hexbinder  # one climber
    python3 -m spire_of_ash.sim --policy random      # the old scripted flailer
    python3 -m spire_of_ash.sim --json out.json      # for CI, or a diff

Every run is seeded from `--seed` plus the run index, so a report is
reproducible and two reports are comparable run for run.
"""

from __future__ import annotations

import argparse
import json
import random
import re
import sys
import time
from collections import Counter

from . import balance as B
from .content.cards import CARDS
from .content.pools import CLASSES
from .engine.errors import InvalidAction
from .engine.run import Run

# 90 of the 94 attacks state their damage in the card text, and 43 skills state
# their Block. Reading it back out is crude, but the alternative is a second
# copy of every card's numbers that would drift from the fx lambdas.
_DAMAGE = re.compile(r"Deal (\d+) damage")
_BLOCK = re.compile(r"Gain (\d+) Block")
# "Deal 4 damage three times" is 12, not 4. Reading only the first number made
# the policy undervalue every multi-hit and AoE attack in the game — the card
# telemetry found it: Blade Dance had the best damage per energy in the pool
# and one of the worst play rates, which is the fingerprint of a card the
# player cannot see the value of.
_TIMES = re.compile(r"(\d+) times")
_WORD_TIMES = (("three times", 3), ("thrice", 3), ("twice", 2), ("four times", 4))

MAX_STEPS = 20000          # a full act-3 run is ~2-4k actions; this is a stall guard


def _desc(key, upgraded):
    c = CARDS.get(key) or {}
    return (c.get("udesc") if upgraded else None) or c.get("desc") or ""


def _stat(pattern, key, upgraded):
    m = pattern.search(_desc(key, upgraded))
    return int(m.group(1)) if m else 0


def _attack_damage(key, upgraded, alive):
    """(damage one enemy takes, total damage the card puts out).

    The two differ for anything that hits everything: a 3-damage sweep against
    four enemies is 12 output but still only 3 towards killing any one of them,
    and confusing the two is how a policy talks itself into a sweep that kills
    nobody.
    """
    text = _desc(key, upgraded)
    m = _DAMAGE.search(text)
    if not m:
        return 0, 0
    dmg = int(m.group(1))
    hits = 1
    mt = _TIMES.search(text)
    if mt:
        hits = int(mt.group(1))
    else:
        for word, n in _WORD_TIMES:
            if word in text:
                hits = n
                break
    per_target = dmg * hits
    everyone = "ALL enemies" in text
    return per_target, per_target * (max(alive, 1) if everyone else 1)


class Result:
    """One finished run, flattened to the numbers a report cares about."""

    __slots__ = ("cls", "seed", "ascension", "won", "act", "floor",
                 "floors_cleared", "elites_killed", "killer", "deck", "gold",
                 "steps", "stalled")

    def __init__(self, **kw):
        for k in self.__slots__:
            setattr(self, k, kw.get(k))

    def as_dict(self):
        return {k: getattr(self, k) for k in self.__slots__}


# ── policies ────────────────────────────────────────────────────────────────

class Policy:
    """Turns a state into exactly one action.

    One call, one `run.apply`, so the caller can count steps and break a stall.
    Screens the subclasses do not care about are handled here, identically for
    every policy, so a comparison between policies is a comparison of the parts
    that differ.
    """

    name = "policy"

    def __init__(self, seed=0):
        self.rng = random.Random(seed)

    def act(self, run, st):
        fn = getattr(self, "on_" + st["screen"], None)
        if fn is None:
            return False
        fn(run, st)
        return True

    # Rewards are never worth skipping, and the engine ends the screen for us
    # once everything on it has been claimed.
    def on_reward(self, run, st):
        p = st["pending"]
        if p["relic"]:
            run.apply({"type": "reward", "what": "relic"})
        elif p["potion"]:
            run.apply({"type": "reward", "what": "potion"})
        elif p["card"]:
            run.apply({"type": "reward", "what": "card", "idx": 0})
        else:
            run.apply({"type": "reward_done"})

    def on_choose(self, run, st):
        run.apply({"type": "choose", "idx": 0})

    def on_event(self, run, st):
        if st["event"]["result"] is None:
            run.apply({"type": "event_choose",
                       "idx": self.rng.randrange(len(st["event"]["options"]))})
        else:
            run.apply({"type": "event_done"})

    def on_treasure(self, run, st):
        run.apply({"type": "treasure_done"})

    def on_shop(self, run, st):
        try:
            run.apply({"type": "shop_buy", "what": "card", "idx": 0})
        except InvalidAction:
            run.apply({"type": "shop_leave"})

    def on_select(self, run, st):
        run.apply({"type": "new_run", "cls": st["player"]["cls"]})


class RandomPolicy(Policy):
    """The scripted flailer the tests already use: legal, and nothing more.

    Kept because it is the floor. If a change to the rules makes the random
    player do better, that is worth knowing.
    """

    name = "random"

    def on_map(self, run, st):
        run.apply({"type": "map", "idx": self.rng.choice(st["map"]["reachable"])})

    def on_rest(self, run, st):
        run.apply({"type": self.rng.choice(["rest", "smith"])})

    def on_combat(self, run, st):
        cb = st["combat"]
        alive = [i for i, e in enumerate(cb["enemies"]) if e["alive"]]
        for i in self.rng.sample(range(len(cb["hand"])), len(cb["hand"])):
            try:
                run.apply({"type": "play", "idx": i,
                           "target": self.rng.choice(alive) if alive else None,
                           "exhaust": 0})
                return
            except InvalidAction:
                continue
        run.apply({"type": "end_turn"})


class GreedyPolicy(Policy):
    """Plays for the current turn only: kill what it can, block what it can't.

    Deliberately shallow. It does not sequence a combo, hold a card for next
    turn, or read a relic. Anything it beats is beatable without thinking,
    which is the property that makes it a useful yardstick.
    """

    name = "greedy"

    # How much a node is worth walking onto, before health talks us out of it.
    NODE_VALUE = {"rest": 4, "treasure": 5, "shop": 3, "elite": 4,
                  "event": 2, "monster": 2, "boss": 1}

    def on_map(self, run, st):
        p = st["player"]
        hurt = p["hp"] / max(p["max_hp"], 1)
        floors = st["map"]["floors"]
        nxt = st["map"]["cur_floor"] + 1
        best, best_score = None, -1e9
        for idx in st["map"]["reachable"]:
            kind = floors[nxt][idx]["type"] if nxt < len(floors) else "boss"
            score = self.NODE_VALUE.get(kind, 1)
            # An elite is a good deal at full health and a way to die at a
            # third of it; a campfire is the reverse.
            if kind == "elite":
                score += 6 * (hurt - 0.7)
            if kind == "rest":
                score += 6 * (0.7 - hurt)
            if kind == "shop" and p["gold"] < 120:
                score -= 2
            if score > best_score:
                best, best_score = idx, score
        run.apply({"type": "map", "idx": best})

    def on_rest(self, run, st):
        p = st["player"]
        # Upgrades compound over the rest of the run, so only spend the fire on
        # healing when the next fight is the thing likely to end it.
        low = p["hp"] / max(p["max_hp"], 1) < 0.6
        try:
            run.apply({"type": "rest" if low else "smith"})
        except InvalidAction:
            run.apply({"type": "rest" if not low else "smith"})

    # ── combat ──

    def on_combat(self, run, st):
        cb, p = st["combat"], st["player"]
        alive = [i for i, e in enumerate(cb["enemies"]) if e["alive"]]
        if not alive:
            run.apply({"type": "end_turn"})
            return

        incoming = sum(e["intent"].get("damage", 0) * max(e["intent"].get("hits", 1), 1)
                       for e in cb["enemies"]
                       if e["alive"] and e["intent"].get("kind") == "attack")
        unblocked = max(incoming - p["block"], 0)

        if self._maybe_potion(run, st, alive, unblocked):
            return

        plays = sorted(self._score_hand(cb, alive, unblocked, p["hp"]),
                       key=lambda c: -c[0])
        for _score, idx, target in plays:
            try:
                run.apply({"type": "play", "idx": idx, "target": target,
                           "exhaust": 0})
                return
            except InvalidAction:
                continue      # unplayable for a reason the card text did not say
        run.apply({"type": "end_turn"})

    def _score_hand(self, cb, alive, unblocked, hp):
        """(score, hand index, target) for everything worth playing."""
        out = []
        energy = cb["energy"]
        # Focus fire: the enemy nearest death is the one whose intent we can
        # actually delete this turn.
        weakest = min(alive, key=lambda i: cb["enemies"][i]["hp"] + cb["enemies"][i]["block"])
        biggest = max(alive, key=lambda i: cb["enemies"][i]["intent"].get("damage", 0)
                      * max(cb["enemies"][i]["intent"].get("hits", 1), 1))

        for idx, card in enumerate(cb["hand"]):
            key, up = card["key"], card["upgraded"]
            info = CARDS.get(key) or {}
            kind = info.get("type")
            cost = info.get("cost")
            if not isinstance(cost, int) or cost < 0:
                cost = 1                      # X-cost and oddities: assume one
            if cost > energy or kind in ("CURSE", "STATUS"):
                continue
            per = max(cost, 1)                # a free card is not infinitely good
            target = weakest if info.get("targeted") else None

            if kind == "ATTACK":
                # Lethality is judged per target; value is judged on total
                # output, so a sweep gets credit for the whole room.
                dmg, output = _attack_damage(key, up, len(alive))
                lethal = [i for i in alive
                          if dmg and dmg >= cb["enemies"][i]["hp"] + cb["enemies"][i]["block"]]
                if lethal:
                    # Kill the one that was about to hit hardest.
                    kill = max(lethal, key=lambda i: cb["enemies"][i]["intent"].get("damage", 0))
                    out.append((1000 + output, idx, kill if info.get("targeted") else None))
                    continue
                score = (output or 6) * 10 / per
                out.append((score, idx, target))
            elif kind == "SKILL":
                blk = _stat(_BLOCK, key, up)
                if blk:
                    # Block past what is actually coming is wasted, and block
                    # that stops a hit is worth roughly its damage — except
                    # when the hit would take a large slice of what is left,
                    # which is the situation the act bosses create and the one
                    # a flat weight kept losing to. Measured at 200 runs a
                    # class: Guardian kills fell by a quarter.
                    useful = min(blk, unblocked)
                    if unblocked >= hp * 0.5:
                        weight = 40
                    elif unblocked >= hp * 0.25:
                        weight = 22
                    else:
                        weight = 11
                    out.append((useful * weight / per, idx, target))
                else:
                    # Draw, debuffs, exhaust fuel: unreadable from the text, but
                    # a hand full of never-played skills is not a real player.
                    out.append((28 / per, idx, target if info.get("targeted") else None))
            elif kind == "POWER":
                # Powers pay off over the fight, so they are worth most early.
                out.append(((90 if cb["turn"] <= 2 else 45) / per, idx, target))
        return out

    def _maybe_potion(self, run, st, alive, unblocked):
        """Drink when the belt would otherwise overflow, or when a hit lands hard."""
        p = st["player"]
        potions = p["potions"]
        if not potions:
            return False
        desperate = unblocked >= p["hp"] or p["hp"] / max(p["max_hp"], 1) < 0.3
        # The Emberbrewer brews faster than it drinks; a full belt throws the
        # next brew away, which would read as the class being weak.
        overflowing = len(potions) >= p["max_potions"]
        if not (desperate or overflowing):
            return False
        for i in range(len(potions)):
            try:
                run.apply({"type": "potion", "idx": i, "target": alive[0] if alive else None})
                return True
            except InvalidAction:
                continue
        return False


POLICIES = {"greedy": GreedyPolicy, "random": RandomPolicy}


# ── driving one run ─────────────────────────────────────────────────────────

# ── card telemetry ──────────────────────────────────────────────────────────

class Telemetry:
    """Per-card counters, gathered by watching the game rather than changing it.

    Everything here is derived from the state the engine already publishes: a
    card's damage is the enemy HP that disappeared while it resolved, and a
    dead card is one that sat in hand when the turn ended. Nothing reaches into
    combat internals, so the engine stays a pure state machine and these
    numbers cannot drift from what a client would see.

    The blind spots are worth stating. Damage that lands on a corpse's overkill
    is not counted, block and debuffs are not valued at all, and a card that
    wins the fight by setting up the next card gets none of the credit. So this
    finds cards that are never played or never do anything — not cards that are
    subtly weak.
    """

    def __init__(self):
        self.drawn = Counter()      # times the card arrived in hand
        self.played = Counter()
        self.held = Counter()       # still in hand when the turn ended
        self.damage = Counter()
        self.energy = Counter()

    def drew(self, key, n=1):
        self.drawn[key] += n

    def saw_hand_at_turn_end(self, hand):
        for c in hand:
            self.held[c["key"]] += 1

    def saw_play(self, key, cost, damage):
        self.played[key] += 1
        self.energy[key] += cost
        self.damage[key] += max(damage, 0)

    def rows(self, min_draws=1):
        out = []
        for key in sorted(self.drawn):
            drawn = self.drawn[key]
            if drawn < min_draws:
                continue
            played = self.played[key]
            info = CARDS.get(key) or {}
            spent = self.energy[key]
            out.append({
                "key": key,
                "name": info.get("name", key),
                "type": info.get("type", "?"),
                "cost": info.get("cost"),
                "drawn": drawn,
                "played": played,
                "play_rate": played / drawn if drawn else 0.0,
                "dead_rate": self.held[key] / drawn if drawn else 0.0,
                "damage": self.damage[key],
                "dmg_per_play": self.damage[key] / played if played else 0.0,
                # Undefined rather than zero for a free card: dividing its
                # damage by no energy at all once ranked Cinder Dart and Spill
                # last in a table they belong at the top of.
                "dmg_per_energy": (self.damage[key] / spent) if spent else None,
            })
        return out


class _Watched:
    """A Run with a tap on it, so the simulator can see what a card did.

    The policy talks to this exactly as it would to a Run. Only `play` is
    treated specially: the enemy HP before and after the action is the damage
    the card actually dealt, which is the one number the state does not report
    directly.
    """

    def __init__(self, run, tel):
        self._run = run
        self._tel = tel
        self._combat = None
        self._hand = Counter()

    def __getattr__(self, name):
        return getattr(self._run, name)

    @staticmethod
    def _enemy_hp(run):
        cb = run.combat
        return sum(e.hp for e in cb.enemies) if cb else 0

    def state(self):
        st = self._run.state()
        # Count a draw whenever a card *arrives* in hand, rather than sampling
        # the opening hand each turn. Cards drawn mid-turn are playable, and
        # counting them as played but never drawn produced play rates above
        # 100% for anything a draw effect fetched.
        if st["screen"] == "combat":
            combat = id(self._run.combat)
            if combat != self._combat:
                self._combat, self._hand = combat, Counter()
            self._observe([c["key"] for c in st["combat"]["hand"]])
        return st

    def _observe(self, keys):
        """Count everything that arrived in hand since the last look."""
        now = Counter(keys)
        for key, n in now.items():
            gained = n - self._hand.get(key, 0)
            if gained > 0:
                self._tel.drew(key, gained)
        self._hand = now

    def apply(self, action):
        kind = action.get("type")
        if kind == "end_turn" and self._run.combat is not None:
            self._tel.saw_hand_at_turn_end(
                [c.to_dict() for c in self._run.combat.hand])
            return self._run.apply(action)
        if kind != "play" or self._run.combat is None:
            return self._run.apply(action)

        hand = self._run.combat.hand
        idx = action.get("idx")
        card = hand[idx] if isinstance(idx, int) and 0 <= idx < len(hand) else None
        before = self._enemy_hp(self._run)
        out = self._run.apply(action)
        if card is not None:
            key = card.key
            info = CARDS.get(key) or {}
            cost = info.get("cost")
            cost = cost if isinstance(cost, int) and cost >= 0 else 1
            self._tel.saw_play(key, cost, before - self._enemy_hp(self._run))
        if self._run.combat is not None:
            # A card that draws cards puts them in hand before we look again;
            # folding them into the baseline instead of counting them is what
            # let Heavy Blade report a 104% play rate.
            self._observe([c.key for c in self._run.combat.hand])
        return out


def simulate(cls, seed, policy_cls=GreedyPolicy, max_steps=MAX_STEPS,
             telemetry=None, ascension=0):
    run = Run(cls, seed=seed, ascension=ascension)
    if telemetry is not None:
        run = _Watched(run, telemetry)
    policy = policy_cls(seed=seed)
    steps = 0
    stalled = False
    while not run.finished:
        if steps >= max_steps:
            stalled = True
            break
        st = run.state()
        try:
            if not policy.act(run, st):
                stalled = True
                break
        except InvalidAction:
            # The policy proposed something illegal and had no fallback left.
            # Ending the turn is always legal in combat; anywhere else, stop.
            try:
                run.apply({"type": "end_turn"})
            except InvalidAction:
                stalled = True
                break
        steps += 1

    st = run.state()
    return Result(cls=cls, seed=seed, ascension=ascension,
                  won=run.screen == "win", act=st["act"],
                  floor=st["floor"], floors_cleared=st["floors_cleared"],
                  elites_killed=st["elites_killed"], killer=st["killer"],
                  deck=st["player"]["deck_size"], gold=st["player"]["gold"],
                  steps=steps, stalled=stalled)


def batch(classes, runs, policy_cls, seed0=0, progress=None, telemetry=None,
          ascension=0):
    out = []
    for cls in classes:
        for i in range(runs):
            out.append(simulate(cls, seed0 + i, policy_cls, telemetry=telemetry,
                                ascension=ascension))
            if progress:
                progress(cls, i + 1, runs)
    return out


# ── reporting ───────────────────────────────────────────────────────────────

def _mean(xs):
    xs = list(xs)
    return sum(xs) / len(xs) if xs else 0.0


def summarise(results):
    by = {}
    for r in results:
        by.setdefault(r.cls, []).append(r)
    rows = []
    for cls, rs in by.items():
        rows.append({
            "cls": cls,
            "runs": len(rs),
            "wins": sum(1 for r in rs if r.won),
            "win_rate": sum(1 for r in rs if r.won) / len(rs),
            "mean_floors": _mean(r.floors_cleared for r in rs),
            "mean_act": _mean(r.act for r in rs),
            "mean_elites": _mean(r.elites_killed for r in rs),
            "mean_deck": _mean(r.deck for r in rs),
            "stalled": sum(1 for r in rs if r.stalled),
            "killers": Counter(r.killer for r in rs if not r.won).most_common(3),
        })
    rows.sort(key=lambda r: -r["win_rate"])
    return rows


def print_report(rows, policy_name, elapsed, out=None, ascension=0):
    # Bound at call time, not at import: a default of sys.stdout is
    # captured when the module loads, which makes the report immune to
    # redirect_stdout and anything else that swaps the stream later.
    out = out or sys.stdout
    total = sum(r["runs"] for r in rows)
    rung = f" · ascension {ascension}" if ascension else ""
    print(f"\n  {total} runs · policy: {policy_name}{rung} · {elapsed:.1f}s\n",
          file=out)
    print(f"  {'class':<14}{'win':>7}{'floors':>9}{'act':>7}"
          f"{'elites':>8}{'deck':>7}   most often killed by", file=out)
    print("  " + "─" * 78, file=out)
    for r in rows:
        killer = r["killers"][0][0] if r["killers"] else "—"
        n = r["killers"][0][1] if r["killers"] else 0
        print(f"  {r['cls']:<14}{r['win_rate']*100:>6.1f}%{r['mean_floors']:>9.1f}"
              f"{r['mean_act']:>7.2f}{r['mean_elites']:>8.2f}{r['mean_deck']:>7.1f}"
              f"   {killer} ({n})", file=out)
    spread = (max(r["win_rate"] for r in rows) - min(r["win_rate"] for r in rows)) if rows else 0
    print(f"\n  spread between best and worst class: {spread*100:.1f} points", file=out)
    stalled = sum(r["stalled"] for r in rows)
    if stalled:
        print(f"  WARNING: {stalled} runs hit the step cap without finishing", file=out)


def print_cards(rows, out=None, top=12, min_draws=30):
    """The two ends of the pool: what never gets played, and what pays best."""
    out = out or sys.stdout
    rows = [r for r in rows if r["drawn"] >= min_draws]
    if not rows:
        print("\n  (not enough draws to say anything about individual cards)", file=out)
        return

    print(f"\n  Card telemetry — {len(rows)} cards drawn at least {min_draws} times\n",
          file=out)

    # Curses and statuses are unplayable on purpose; listing them as the cards
    # nobody plays is true and useless.
    playable = [r for r in rows if r["type"] not in ("CURSE", "STATUS")]

    # Raw play rate measures the player, not the card, in two ways that both
    # have to be divided out.
    #
    # Cost: across 231 cards the play rate slides 95% -> 59% -> 32% -> 22% from
    # cost 0 to cost 3, which is a fact about having three energy a turn.
    #
    # Type: even at equal cost, attacks run +14 points and skills -12, because
    # GreedyPolicy scores an attack by the damage it can read off the card and
    # falls back to a flat guess for a skill whose text it cannot parse. That
    # is the policy's blind spot, not the card's fault.
    #
    # So a card is compared only with cards that cost the same *and* do the
    # same kind of thing. What is left is the closest thing to a quality signal
    # this tool can honestly produce — and it is still only a hint.
    peers = {}
    for r in playable:
        peers.setdefault((str(r["cost"]), r["type"]), []).append(r["play_rate"])
    norm = {k: sum(v) / len(v) for k, v in peers.items()}
    for r in playable:
        r["vs_peers"] = r["play_rate"] - norm[(str(r["cost"]), r["type"])]

    dead = sorted(playable, key=lambda r: (r["vs_peers"], -r["drawn"]))[:top]
    print(f"  Least played vs same cost+type{'':<2}{'cost':>5}{'type':>8}"
          f"{'drawn':>7}{'play %':>9}{'vs peers':>10}", file=out)
    print("  " + "─" * 72, file=out)
    for r in dead:
        print(f"  {r['name'][:28]:<30}{str(r['cost']):>5}{r['type'][:6]:>8}"
              f"{r['drawn']:>7}{r['play_rate']*100:>8.1f}%"
              f"{r['vs_peers']*100:>9.1f}", file=out)

    free = [r for r in playable
            if r["cost"] == 0 and r["type"] == "ATTACK" and r["played"] >= 20]
    if free:
        print(f"\n  Free attacks (damage per energy is undefined, not zero)"
              f"{'':<3}{'played':>7}{'dmg/play':>10}", file=out)
        print("  " + "─" * 62, file=out)
        for r in sorted(free, key=lambda r: -r["dmg_per_play"]):
            print(f"  {r['name'][:28]:<30}{'':>8}{r['played']:>8}"
                  f"{r['dmg_per_play']:>10.1f}", file=out)

    attacks = [r for r in rows if r["type"] == "ATTACK" and r["played"] >= 20
               and r["dmg_per_energy"] is not None]
    if attacks:
        best = sorted(attacks, key=lambda r: -r["dmg_per_energy"])
        print(f"\n  Damage per energy{'':<13}{'played':>8}{'dmg/play':>10}"
              f"{'dmg/energy':>12}", file=out)
        print("  " + "─" * 62, file=out)
        for r in best[:top // 2]:
            print(f"  {r['name'][:28]:<30}{r['played']:>8}{r['dmg_per_play']:>10.1f}"
                  f"{r['dmg_per_energy']:>12.1f}", file=out)
        print("  " + " " * 30 + "…", file=out)
        for r in best[-(top // 2):]:
            print(f"  {r['name'][:28]:<30}{r['played']:>8}{r['dmg_per_play']:>10.1f}"
                  f"{r['dmg_per_energy']:>12.1f}", file=out)


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="spire-sim", description="Play the game thousands of times and count.")
    ap.add_argument("--runs", type=int, default=60, help="runs per class (default 60)")
    ap.add_argument("--classes", default="all",
                    help="comma-separated class keys, or 'all'")
    ap.add_argument("--policy", default="greedy", choices=sorted(POLICIES))
    ap.add_argument("--seed", type=int, default=0, help="first seed; runs use seed+i")
    ap.add_argument("--json", metavar="PATH", help="also write the raw rows here")
    ap.add_argument("--quiet", action="store_true", help="no progress line")
    ap.add_argument("--ascension", type=int, default=0,
                    metavar="N", help=f"difficulty rung 0-{B.MAX_ASCENSION}")
    ap.add_argument("--cards", action="store_true",
                    help="also report per-card play rates and damage per energy")
    ap.add_argument("--fail-outside", metavar="LO,HI",
                    help="exit 1 if any class's win rate falls outside this "
                         "percentage band, e.g. 25,65 — for CI")
    args = ap.parse_args(argv)

    classes = sorted(CLASSES) if args.classes == "all" else \
        [c.strip() for c in args.classes.split(",") if c.strip()]
    unknown = [c for c in classes if c not in CLASSES]
    if unknown:
        ap.error(f"unknown class(es): {', '.join(unknown)}. "
                 f"known: {', '.join(sorted(CLASSES))}")

    def progress(cls, i, n):
        if not args.quiet:
            print(f"\r  {cls:<14} {i}/{n}", end="", file=sys.stderr, flush=True)

    started = time.time()
    tel = Telemetry() if args.cards else None
    results = batch(classes, args.runs, POLICIES[args.policy], args.seed,
                    progress, telemetry=tel, ascension=args.ascension)
    elapsed = time.time() - started
    if not args.quiet:
        print("\r" + " " * 40 + "\r", end="", file=sys.stderr)

    rows = summarise(results)
    print_report(rows, args.policy, elapsed, ascension=args.ascension)
    if tel is not None:
        print_cards(tel.rows())

    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            payload = {"policy": args.policy, "runs_per_class": args.runs,
                       "seed": args.seed, "ascension": args.ascension,
                       "summary": rows,
                       "runs": [r.as_dict() for r in results]}
            if tel is not None:
                payload["cards"] = tel.rows()
            json.dump(payload, f, indent=1)
        print(f"  wrote {args.json}")

    if args.fail_outside:
        lo, hi = (float(x) / 100 for x in args.fail_outside.split(","))
        bad = [r for r in rows if not lo <= r["win_rate"] <= hi]
        if bad:
            print(f"\n  FAIL: {len(bad)} class(es) outside the "
                  f"{lo*100:.0f}–{hi*100:.0f}% band:", file=sys.stderr)
            for r in bad:
                print(f"    {r['cls']}: {r['win_rate']*100:.1f}%", file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
