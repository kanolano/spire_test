"""Per-run random number generation.

The old code used the global `random` module, so runs were neither reproducible
nor testable, and two concurrent runs shared one stream. Every `Run` now owns an
`Rng` seeded at creation. `to_dict`/`from_dict` capture the generator's exact
internal state, so a saved run resumes on the same stream it left off on.
"""

import random


class Rng:
    def __init__(self, seed=None):
        if seed is None:
            seed = random.SystemRandom().getrandbits(64)
        self.seed = seed
        self._r = random.Random(seed)

    # ── the surface the engine actually uses ──
    def random(self):
        return self._r.random()

    def randint(self, lo, hi):
        return self._r.randint(lo, hi)

    def randrange(self, n):
        return self._r.randrange(n)

    def choice(self, seq):
        return self._r.choice(seq)

    def sample(self, seq, k):
        return self._r.sample(seq, k)

    def shuffle(self, seq):
        self._r.shuffle(seq)

    # ── persistence ──
    def to_dict(self):
        version, internal, gauss = self._r.getstate()
        return {"seed": self.seed, "version": version,
                "state": list(internal), "gauss": gauss}

    @classmethod
    def from_dict(cls, d):
        rng = cls(d["seed"])
        rng._r.setstate((d["version"], tuple(d["state"]), d["gauss"]))
        return rng
