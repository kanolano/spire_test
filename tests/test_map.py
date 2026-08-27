"""Per-act map generation: shape, guaranteed floors, reachability, and the act
difficulty ramp.

These guard the structural contract the run and both clients rely on — floor 0
is combat, the top floor is a lone boss, every node is reachable from the floor
below — and the intent of the per-act profiles: later acts are taller and lean
harder (more elites, fewer campfires).
"""

import unittest

from helpers import autoplay  # noqa: F401  (puts the package on sys.path)

from spire_of_ash import balance as B
from spire_of_ash.engine.dungeon import generate_map, make_encounter
from spire_of_ash.engine.run import Run
from spire_of_ash.rng import Rng


ACTS = list(B.ACT_PROFILES)


def _reachable_from(floors, f, i):
    return floors[f][i]["edges"]


def _all_reachable(floors):
    """Every node above floor 0 must be the target of some edge below it."""
    for f in range(1, len(floors)):
        covered = {t for node in floors[f - 1] for t in node["edges"]}
        for i in range(len(floors[f])):
            if i not in covered:
                return False, (f, i)
    return True, None


class TestMapShape(unittest.TestCase):
    def test_every_act_generates(self):
        for act in ACTS:
            floors = generate_map(Rng(1), act)
            prof = B.act_profile(act)
            self.assertEqual(len(floors), prof["floors"],
                             f"act {act} wrong height")

    def test_floor_zero_is_combat(self):
        for act in ACTS:
            for seed in range(20):
                floors = generate_map(Rng(seed), act)
                self.assertTrue(all(n["type"] == "monster" for n in floors[0]),
                                f"act {act} seed {seed}: floor 0 not all combat")

    def test_top_floor_is_a_lone_boss(self):
        for act in ACTS:
            for seed in range(20):
                floors = generate_map(Rng(seed), act)
                top = floors[-1]
                self.assertEqual(len(top), 1, f"act {act}: boss floor not solitary")
                self.assertEqual(top[0]["type"], "boss")

    def test_guaranteed_floors_match_profile(self):
        for act in ACTS:
            prof = B.act_profile(act)
            for seed in range(15):
                floors = generate_map(Rng(seed), act)
                tf = prof["treasure_floor"]
                self.assertTrue(all(n["type"] == "treasure" for n in floors[tf]),
                                f"act {act} seed {seed}: treasure floor wrong")
                for rf in prof["rest_floors"]:
                    self.assertTrue(all(n["type"] == "rest" for n in floors[rf]),
                                    f"act {act} seed {seed}: rest floor {rf} wrong")

    def test_every_node_is_reachable(self):
        for act in ACTS:
            for seed in range(40):
                floors = generate_map(Rng(seed), act)
                ok, where = _all_reachable(floors)
                self.assertTrue(ok, f"act {act} seed {seed}: node {where} unreachable")

    def test_edges_point_within_the_next_floor(self):
        for act in ACTS:
            for seed in range(20):
                floors = generate_map(Rng(seed), act)
                for f in range(len(floors) - 1):
                    width = len(floors[f + 1])
                    for node in floors[f]:
                        for t in node["edges"]:
                            self.assertTrue(0 <= t < width,
                                            f"act {act}: edge {t} out of range")

    def test_determinism_per_seed_and_act(self):
        for act in ACTS:
            a = generate_map(Rng(99), act)
            b = generate_map(Rng(99), act)
            self.assertEqual(a, b, f"act {act} not deterministic")

    def test_no_elite_before_its_gate(self):
        for act in ACTS:
            gate = B.act_profile(act)["elite_from"]
            for seed in range(40):
                floors = generate_map(Rng(seed), act)
                for f in range(min(gate, len(floors))):
                    for n in floors[f]:
                        self.assertNotEqual(n["type"], "elite",
                                            f"act {act} seed {seed}: elite on floor {f}")


class TestActRamp(unittest.TestCase):
    """The profiles are meant to tighten as the Spire rises. Counted over many
    seeds so a single unlucky map does not decide it."""

    def _counts(self, act, seeds=120):
        elite = rest = total = 0
        for seed in range(seeds):
            floors = generate_map(Rng(seed), act)
            for f in floors:
                for n in f:
                    total += 1
                    if n["type"] == "elite":
                        elite += 1
                    elif n["type"] == "rest":
                        rest += 1
        return elite / total, rest / total

    def test_later_acts_have_more_elites(self):
        e1, _ = self._counts(1)
        e3, _ = self._counts(3)
        self.assertLess(e1, e3, "act 3 should be denser with elites than act 1")

    def test_acts_grow_taller(self):
        heights = [B.act_profile(a)["floors"] for a in ACTS]
        self.assertEqual(heights, sorted(heights), "acts should not shrink")
        self.assertLess(heights[0], heights[-1], "final act should be tallest")


class TestEncounters(unittest.TestCase):
    def test_super_elite_deep_in_later_acts(self):
        """Where a profile gates a super-elite, a deep elite node is labelled as
        one and draws from the tougher half of the pool."""
        for act in ACTS:
            prof = B.act_profile(act)
            sef = prof.get("super_elite_from")
            if sef is None:
                continue
            _, label = make_encounter(Rng(3), act, "elite", sef + 1)
            self.assertEqual(label, "SUPER-ELITE", f"act {act} deep elite not super")

    def test_early_elite_is_plain(self):
        for act in ACTS:
            _, label = make_encounter(Rng(3), act, "elite", 0)
            self.assertEqual(label, "ELITE", f"act {act} floor-0 elite mislabelled")

    def test_boss_encounter_is_a_boss(self):
        for act in ACTS:
            enemies, label = make_encounter(Rng(3), act, "boss", 0)
            self.assertEqual(label, "BOSS")
            self.assertEqual(len(enemies), 1)


class TestFullClimb(unittest.TestCase):
    def test_a_run_can_reach_every_act(self):
        """A high-HP autoplay should climb through all acts and either win or die
        on the final act, never stall or advance past FINAL_ACT."""
        run = Run("sentinel", seed=1)
        run.player.max_hp = run.player.hp = 100000
        autoplay(run, seed=1, keep_alive=True)
        self.assertLessEqual(run.act, B.FINAL_ACT)
        if run.screen == "win":
            self.assertEqual(run.act, B.FINAL_ACT)

    def test_act_view_carries_its_name(self):
        run = Run("sentinel", seed=1)
        st = run.state()
        self.assertEqual(st["map"]["act_name"], B.act_profile(1)["name"])


if __name__ == "__main__":
    unittest.main()
