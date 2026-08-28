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
