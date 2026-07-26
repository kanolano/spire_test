"""Drawing random content from the class card pools and the relic pool.

The class used to be resolved through the `PLAYER_REF` module global, which meant
card generation depended on hidden state and two runs could not coexist. The
class key and the run's generator are now always passed in explicitly.
"""

from .classes import CLASSES, DEFAULT_CLASS
from .relics import RELIC_POOL


def random_card_keys(rng, n, chances=(0.62, 0.31, 0.07), cls=DEFAULT_CLASS):
    """Pick n distinct card keys from one class's pools, weighted by rarity."""
    d = CLASSES[cls if cls in CLASSES else DEFAULT_CLASS]
    common, uncommon = chances[0], chances[0] + chances[1]
    keys = []
    while len(keys) < n:
        r = rng.random()
        pool = d["common"] if r < common else (
            d["uncommon"] if r < uncommon else d["rare"])
        k = rng.choice(pool)
        if k not in keys:
            keys.append(k)
    return keys


def roll_relic(rng, owned):
    """A relic the player does not already own, if one is left.

    This one-liner appeared verbatim seven times across the engine and the web
    layer.
    """
    pool = [r for r in RELIC_POOL if r not in owned] or RELIC_POOL
    return rng.choice(pool)
