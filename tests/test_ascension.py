"""The difficulty ladder.

The property that matters is not that any particular rung is hard, but that a
rung is always harder than the one below it and that a seed still produces the
same climb — otherwise "the same run on a higher ascension" means nothing and
the ladder is just a different game. `python3 -m spire_of_ash.sim --ascension N`
measures the first claim over thousands of runs; these tests hold the machinery
that claim rests on.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from spire_of_ash import balance as B                     # noqa: E402
from spire_of_ash.engine.dungeon import make_encounter    # noqa: E402
from spire_of_ash.engine.errors import InvalidAction      # noqa: E402
from spire_of_ash.engine.run import Run                   # noqa: E402
from spire_of_ash.rng import Rng                          # noqa: E402


class TestLadder(unittest.TestCase):
    def test_level_zero_changes_nothing(self):
        self.assertTrue(all(v == 0 for v in B.ascension_mods(0).values()))

    def test_rungs_accumulate(self):
        one, two = B.ascension_mods(1), B.ascension_mods(2)
        self.assertEqual(one["enemy_hp"], 0.10)
        self.assertEqual(two["enemy_hp"], 0.10, "rung 2 adds tough HP, not more general HP")
        self.assertGreater(two["tough_hp"], one["tough_hp"])

    def test_levels_are_clamped_at_both_ends(self):
        self.assertEqual(B.ascension_mods(-5), B.ascension_mods(0))
        self.assertEqual(B.ascension_mods(999), B.ascension_mods(B.MAX_ASCENSION))

    def test_nothing_on_the_ladder_makes_the_game_easier(self):
        """Every rung moves difficulty one way or stays put."""
        harder = {"enemy_hp": 1, "tough_hp": 1, "elite_chance": 1,
                  "boss_strength": 1, "start_hp": -1, "rest_heal": -1}
        prev = B.ascension_mods(0)
        for level in range(1, B.MAX_ASCENSION + 1):
            cur = B.ascension_mods(level)
            for key, direction in harder.items():
                with self.subTest(level=level, key=key):
                    self.assertGreaterEqual((cur[key] - prev[key]) * direction, 0)
            self.assertNotEqual(cur, prev, f"rung {level} does nothing")
            prev = cur

    def test_every_rung_says_what_it_does(self):
        ladder = B.ascension_ladder()
        self.assertEqual(len(ladder), B.MAX_ASCENSION)
        self.assertEqual([lvl for lvl, _ in ladder],
                         list(range(1, B.MAX_ASCENSION + 1)))
        for _lvl, desc in ladder:
            self.assertTrue(desc.strip() and desc.endswith("."))


class TestRunsAtAscension(unittest.TestCase):
    def test_a_seed_meets_the_same_monsters_at_any_level(self):
        """Only their size changes, so two levels are comparable run for run."""
        def opening_fight(level):
            run = Run("sentinel", seed=4, ascension=level)
            run.apply({"type": "map", "idx": run.state()["map"]["reachable"][0]})
            return [e["name"] for e in run.state()["combat"]["enemies"]]
        self.assertEqual(opening_fight(0), opening_fight(6))

    def test_enemies_are_tougher_higher_up(self):
        def hp(level):
            run = Run("sentinel", seed=4, ascension=level)
            run.apply({"type": "map", "idx": run.state()["map"]["reachable"][0]})
            return sum(e["max_hp"] for e in run.state()["combat"]["enemies"])
        self.assertGreater(hp(5), hp(0))

    def test_you_start_the_climb_wounded(self):
        low, high = Run("sentinel", seed=1, ascension=0), Run("sentinel", seed=1, ascension=8)
        self.assertEqual(low.player.hp, low.player.max_hp)
        self.assertLess(high.player.hp, high.player.max_hp)
        self.assertEqual(high.player.max_hp, low.player.max_hp,
                         "the ladder takes health off the top, not off max HP")
        self.assertGreater(high.player.hp, 0)

    def test_campfires_give_back_less(self):
        def healed(level):
            run = Run("sentinel", seed=1, ascension=level)
            run.screen = "rest"
            run.player.hp = 10
            run.apply({"type": "rest"})
            return run.player.hp - 10
        self.assertLess(healed(B.MAX_ASCENSION), healed(0))
        self.assertGreater(healed(B.MAX_ASCENSION), 0, "a campfire always does something")

    def test_bosses_gain_strength_near_the_top(self):
        def boss_strength(level):
            enemies, _ = make_encounter(Rng(3), 1, "boss", 14, level)
            return enemies[0].s("strength")
        self.assertEqual(boss_strength(0), 0)
        self.assertGreater(boss_strength(B.MAX_ASCENSION), 0)

    def test_elites_are_tougher_than_ordinary_enemies_at_the_same_level(self):
        level = B.MAX_ASCENSION
        mods = B.ascension_mods(level)
        self.assertGreater(mods["enemy_hp"] + mods["tough_hp"], mods["enemy_hp"])


class TestAscensionTravels(unittest.TestCase):
    def test_it_survives_a_save_and_load(self):
        run = Run("sentinel", seed=2, ascension=6)
        self.assertEqual(Run.from_dict(run.to_dict()).ascension, 6)

    def test_a_save_written_before_the_ladder_loads_as_level_zero(self):
        d = Run("sentinel", seed=2, ascension=6).to_dict()
        del d["ascension"]
        self.assertEqual(Run.from_dict(d).ascension, 0)

    def test_the_state_reports_it(self):
        self.assertEqual(Run("sentinel", seed=1, ascension=3).state()["ascension"], 3)

    def test_the_leaderboard_row_records_it(self):
        run = Run("sentinel", seed=1, ascension=5)
        self.assertEqual(run.summary(False)["ascension"], 5)

    def test_climbing_again_keeps_the_difficulty(self):
        run = Run("sentinel", seed=1, ascension=4)
        run.apply({"type": "new_run", "cls": "ashwalker"})
        self.assertEqual(run.ascension, 4, "climbing again must not drop you to 0")

    def test_a_new_run_can_change_the_difficulty(self):
        run = Run("sentinel", seed=1, ascension=4)
        run.apply({"type": "new_run", "cls": "sentinel", "ascension": 7})
        self.assertEqual(run.ascension, 7)

    def test_a_nonsense_level_is_refused(self):
        run = Run("sentinel", seed=1)
        with self.assertRaises(InvalidAction):
            run.apply({"type": "new_run", "cls": "sentinel", "ascension": "high"})

    def test_an_out_of_range_level_is_clamped_rather_than_refused(self):
        run = Run("sentinel", seed=1)
        run.apply({"type": "new_run", "cls": "sentinel", "ascension": 99})
        self.assertEqual(run.ascension, B.MAX_ASCENSION)


if __name__ == "__main__":
    unittest.main()
