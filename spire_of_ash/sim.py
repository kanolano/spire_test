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

from .content.cards import CARDS
from .content.pools import CLASSES
from .engine.errors import InvalidAction
from .engine.run import Run

# 90 of the 94 attacks state their damage in the card text, and 43 skills state
# their Block. Reading it back out is crude, but the alternative is a second
# copy of every card's numbers that would drift from the fx lambdas.
_DAMAGE = re.compile(r"Deal (\d+) damage")
_BLOCK = re.compile(r"Gain (\d+) Block")

MAX_STEPS = 20000          # a full act-3 run is ~2-4k actions; this is a stall guard


def _desc(key, upgraded):
    c = CARDS.get(key) or {}
    return (c.get("udesc") if upgraded else None) or c.get("desc") or ""


def _stat(pattern, key, upgraded):
    m = pattern.search(_desc(key, upgraded))
    return int(m.group(1)) if m else 0


class Result:
    """One finished run, flattened to the numbers a report cares about."""

    __slots__ = ("cls", "seed", "won", "act", "floor", "floors_cleared",
                 "elites_killed", "killer", "deck", "gold", "steps", "stalled")

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
                dmg = _stat(_DAMAGE, key, up)
                lethal = [i for i in alive
                          if dmg and dmg >= cb["enemies"][i]["hp"] + cb["enemies"][i]["block"]]
                if lethal:
                    # Kill the one that was about to hit hardest.
                    kill = max(lethal, key=lambda i: cb["enemies"][i]["intent"].get("damage", 0))
                    out.append((1000 + dmg, idx, kill if info.get("targeted") else None))
                    continue
                score = (dmg or 6) * 10 / per
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

def simulate(cls, seed, policy_cls=GreedyPolicy, max_steps=MAX_STEPS):
    run = Run(cls, seed=seed)
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
    return Result(cls=cls, seed=seed, won=run.screen == "win", act=st["act"],
                  floor=st["floor"], floors_cleared=st["floors_cleared"],
                  elites_killed=st["elites_killed"], killer=st["killer"],
                  deck=st["player"]["deck_size"], gold=st["player"]["gold"],
                  steps=steps, stalled=stalled)


def batch(classes, runs, policy_cls, seed0=0, progress=None):
    out = []
    for cls in classes:
        for i in range(runs):
            out.append(simulate(cls, seed0 + i, policy_cls))
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


def print_report(rows, policy_name, elapsed, out=None):
    # Bound at call time, not at import: a default of sys.stdout is
    # captured when the module loads, which makes the report immune to
    # redirect_stdout and anything else that swaps the stream later.
    out = out or sys.stdout
    total = sum(r["runs"] for r in rows)
    print(f"\n  {total} runs · policy: {policy_name} · {elapsed:.1f}s\n", file=out)
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
    results = batch(classes, args.runs, POLICIES[args.policy], args.seed, progress)
    elapsed = time.time() - started
    if not args.quiet:
        print("\r" + " " * 40 + "\r", end="", file=sys.stderr)

    rows = summarise(results)
    print_report(rows, args.policy, elapsed)

    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump({"policy": args.policy, "runs_per_class": args.runs,
                       "seed": args.seed, "summary": rows,
                       "runs": [r.as_dict() for r in results]}, f, indent=1)
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
