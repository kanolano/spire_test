"""Shared test fixtures and a scripted player.

Tests are written against stdlib `unittest` so they run with no dependencies
(`python3 -m unittest discover tests`). pytest collects them too if you have it.
"""

import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from spire_of_ash.engine.combat import Combat            # noqa: E402
from spire_of_ash.engine.combatant import Enemy, Player  # noqa: E402
from spire_of_ash.engine.errors import InvalidAction     # noqa: E402
from spire_of_ash.rng import Rng                         # noqa: E402


def make_combat(enemies=("cultist",), cls="sentinel", seed=1234):
    """A started combat plus its rng, for rules tests."""
    rng = Rng(seed)
    player = Player(cls)
    cb = Combat(player, [Enemy(k, 1, rng) for k in enemies], rng, "TEST")
    cb.start_combat()
    return cb


def autoplay(run, seed=0, max_steps=6000, keep_alive=False):
    """Drive a run with a scripted player until it ends or stalls."""
    pick = random.Random(seed)
    for _ in range(max_steps):
        if run.finished:
            break
        if keep_alive:
            run.player.hp = run.player.max_hp
        st = run.state()
        screen = st["screen"]
        if screen == "map":
            run.apply({"type": "map", "idx": pick.choice(st["map"]["reachable"])})
        elif screen == "combat":
            _combat_step(run, st, pick)
        elif screen == "reward":
            run.apply({"type": "reward", "idx": 0})
        elif screen == "choose":
            run.apply({"type": "choose", "idx": 0})
        elif screen == "rest":
            run.apply({"type": pick.choice(["rest", "smith"])})
        elif screen == "shop":
            try:
                run.apply({"type": "shop_buy", "what": "card", "idx": 0})
            except InvalidAction:
                run.apply({"type": "shop_leave"})
        elif screen == "event":
            if st["event"]["result"] is None:
                run.apply({"type": "event_choose",
                           "idx": pick.randrange(len(st["event"]["options"]))})
            else:
                run.apply({"type": "event_done"})
        elif screen == "treasure":
            run.apply({"type": "treasure_done"})
        elif screen == "select":
            run.apply({"type": "new_run", "cls": "sentinel"})
        else:
            break
    return run


def _combat_step(run, st, pick):
    cb = st["combat"]
    alive = [i for i, e in enumerate(cb["enemies"]) if e["alive"]]
    order = pick.sample(range(len(cb["hand"])), len(cb["hand"]))
    for i in order:
        try:
            run.apply({"type": "play", "idx": i,
                       "target": pick.choice(alive) if alive else None,
                       "exhaust": 0})
            return
        except InvalidAction:
            continue
    run.apply({"type": "end_turn"})
