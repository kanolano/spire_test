"""The simulator is a measuring instrument, so what matters is that it measures.

These tests do not assert a win rate — that is the number the tool exists to
discover, and pinning it here would mean editing the test every time the game
is balanced. They assert the properties a report has to have before its numbers
mean anything: runs finish, seeds reproduce, and every class is playable by
both policies.
"""

import contextlib
import io
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from spire_of_ash import sim                              # noqa: E402
from spire_of_ash.content.cards import CARDS              # noqa: E402
from spire_of_ash.content.pools import CLASSES            # noqa: E402


class TestSimulate(unittest.TestCase):
    def test_every_class_finishes_under_both_policies(self):
        for cls in CLASSES:
            for policy in (sim.GreedyPolicy, sim.RandomPolicy):
                with self.subTest(cls=cls, policy=policy.name):
                    r = sim.simulate(cls, seed=3, policy_cls=policy)
                    self.assertFalse(r.stalled, f"{cls}/{policy.name} hit the step cap")
                    self.assertEqual(r.cls, cls)
                    self.assertGreater(r.steps, 0)
                    # A run that ended is either a win or has something to blame.
                    self.assertTrue(r.won or r.killer)

    def test_same_seed_gives_the_same_run(self):
        a = sim.simulate("sentinel", seed=11)
        b = sim.simulate("sentinel", seed=11)
        self.assertEqual(a.as_dict(), b.as_dict())

    def test_different_seeds_diverge(self):
        # Not a law of the universe, but 20 identical runs would mean the seed
        # is not reaching the policy or the map.
        got = {sim.simulate("sentinel", seed=s).as_dict()["floors_cleared"]
               for s in range(20)}
        self.assertGreater(len(got), 1)

    def test_a_result_reports_the_act_it_died_in(self):
        r = sim.simulate("sentinel", seed=1)
        self.assertIn(r.act, (1, 2, 3))
        self.assertGreaterEqual(r.floors_cleared, 0)

    def test_step_cap_is_honoured(self):
        r = sim.simulate("sentinel", seed=1, max_steps=5)
        self.assertTrue(r.stalled)
        self.assertLessEqual(r.steps, 5)


class TestReporting(unittest.TestCase):
    def test_summarise_groups_by_class_and_ranks_by_win_rate(self):
        results = sim.batch(["sentinel", "ashwalker"], 3, sim.GreedyPolicy)
        rows = sim.summarise(results)
        self.assertEqual({r["cls"] for r in rows}, {"sentinel", "ashwalker"})
        self.assertEqual([r["runs"] for r in rows], [3, 3])
        self.assertGreaterEqual(rows[0]["win_rate"], rows[-1]["win_rate"])
        for r in rows:
            self.assertEqual(r["wins"], round(r["win_rate"] * r["runs"]))

    def test_batch_uses_seed0_so_two_reports_are_comparable(self):
        a = sim.batch(["sentinel"], 4, sim.GreedyPolicy, seed0=100)
        b = sim.batch(["sentinel"], 4, sim.GreedyPolicy, seed0=100)
        self.assertEqual([r.as_dict() for r in a], [r.as_dict() for r in b])
        self.assertEqual([r.seed for r in a], [100, 101, 102, 103])


class TestCli(unittest.TestCase):
    """The report goes to stdout, which the suite should not have to read."""

    def run_cli(self, argv):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(io.StringIO()):
            code = sim.main(argv)
        return code, buf.getvalue()

    def test_runs_and_reports(self):
        code, out = self.run_cli(["--runs", "1", "--classes", "sentinel", "--quiet"])
        self.assertEqual(code, 0)
        self.assertIn("sentinel", out)
        self.assertIn("policy: greedy", out)

    def test_unknown_class_is_refused(self):
        with self.assertRaises(SystemExit):
            self.run_cli(["--classes", "not_a_climber", "--quiet"])

    def test_fail_outside_flags_a_class_out_of_band(self):
        # Nothing wins 90% of the time, so this band must fail.
        code, _ = self.run_cli(["--runs", "2", "--classes", "sentinel", "--quiet",
                                "--fail-outside", "90,100"])
        self.assertEqual(code, 1)

    def test_fail_outside_passes_a_band_that_contains_everything(self):
        code, _ = self.run_cli(["--runs", "2", "--classes", "sentinel", "--quiet",
                                "--fail-outside", "0,100"])
        self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main()


class TestAttackParsing(unittest.TestCase):
    """The policy reads damage off the card text, so the reading has to be right.

    Undercounting multi-hit and AoE attacks did not cost much win rate, but it
    badly distorted the card telemetry: Blade Dance had the best damage per
    energy in the pool and one of the worst play rates, because the policy
    scored "Deal 4 damage three times" as four.
    """

    def test_multi_hit_damage_is_multiplied(self):
        # Blade Dance: "Deal 4 damage three times."
        per_target, output = sim._attack_damage("blade_dance", False, 1)
        self.assertEqual(per_target, 12)
        self.assertEqual(output, 12)

    def test_sweeps_count_every_enemy_towards_output_but_not_towards_lethal(self):
        # Spark Shower: "Deal 3 damage to ALL enemies twice."
        per_target, output = sim._attack_damage("spark_shower", False, 4)
        self.assertEqual(per_target, 6, "each enemy still only takes 6")
        self.assertEqual(output, 24, "but the card puts out 24 across the room")

    def test_a_plain_attack_is_unchanged(self):
        self.assertEqual(sim._attack_damage("strike", False, 3), (6, 6))

    def test_upgrades_are_read_from_the_upgraded_text(self):
        plain = sim._attack_damage("strike", False, 1)[0]
        upped = sim._attack_damage("strike", True, 1)[0]
        self.assertGreater(upped, plain)

    def test_a_card_with_no_damage_line_reports_nothing(self):
        self.assertEqual(sim._attack_damage("defend", False, 1), (0, 0))


class TestTelemetry(unittest.TestCase):
    def _gather(self, runs=2):
        tel = sim.Telemetry()
        sim.batch(["sentinel"], runs, sim.GreedyPolicy, telemetry=tel)
        return tel

    def test_it_sees_the_starting_deck(self):
        tel = self._gather()
        self.assertGreater(tel.drawn["strike"], 0)
        self.assertGreater(tel.played["strike"], 0)

    def test_no_card_is_played_more_often_than_it_is_drawn(self):
        """A play rate over 100% means draws are being missed, not that a card
        is unusually good — cards fetched mid-turn used to escape the count."""
        tel = self._gather(runs=4)
        for row in tel.rows():
            self.assertLessEqual(
                row["play_rate"], 1.0,
                f"{row['name']} played {row['played']} times but drawn "
                f"{row['drawn']}")

    def test_damage_per_energy_is_undefined_for_a_free_card(self):
        """Not zero: dividing by no energy once ranked the best cards last."""
        tel = sim.Telemetry()
        tel.drew("cinder_dart")
        tel.saw_play("cinder_dart", 0, 4)
        row = next(r for r in tel.rows() if r["key"] == "cinder_dart")
        self.assertIsNone(row["dmg_per_energy"])
        self.assertEqual(row["dmg_per_play"], 4)

    def test_damage_per_energy_divides_by_energy_actually_spent(self):
        tel = sim.Telemetry()
        tel.drew("bash", 2)
        tel.saw_play("bash", 2, 8)
        tel.saw_play("bash", 2, 12)
        row = next(r for r in tel.rows() if r["key"] == "bash")
        self.assertEqual(row["dmg_per_energy"], 5.0)     # 20 damage / 4 energy
        self.assertEqual(row["dmg_per_play"], 10.0)

    def test_rows_carry_the_cost_so_a_report_can_normalise_by_it(self):
        tel = self._gather()
        for row in tel.rows():
            self.assertEqual(row["cost"], (CARDS.get(row["key"]) or {}).get("cost"))

    def test_telemetry_does_not_change_the_run(self):
        """The tap is a wrapper; it must not perturb what it measures."""
        plain = sim.simulate("sentinel", seed=5)
        watched = sim.simulate("sentinel", seed=5, telemetry=sim.Telemetry())
        self.assertEqual(plain.as_dict(), watched.as_dict())

