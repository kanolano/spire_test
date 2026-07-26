"""Saving and resuming a run, and the leaderboard."""

import json
import os
import tempfile
import unittest

from helpers import autoplay, make_combat

from spire_of_ash.engine import records
from spire_of_ash.engine.card import Card
from spire_of_ash.engine.combatant import Player
from spire_of_ash.engine.run import Run
from spire_of_ash.rng import Rng


class TestRoundTrip(unittest.TestCase):
    def test_card(self):
        card = Card("strike", upgraded=True)
        clone = Card.from_dict(card.to_dict())
        self.assertEqual((clone.key, clone.upgraded, clone.name),
                         (card.key, card.upgraded, card.name))

    def test_player(self):
        p = Player("ashwalker")
        p.gold = 250
        p.add_relic("kunai")
        p.potions.append("fire")
        p.st["strength"] = 3
        clone = Player.from_dict(p.to_dict())
        self.assertEqual(clone.to_dict(), p.to_dict())

    def test_rng_resumes_the_same_stream(self):
        rng = Rng(42)
        [rng.random() for _ in range(10)]
        clone = Rng.from_dict(rng.to_dict())
        self.assertEqual([rng.random() for _ in range(5)],
                         [clone.random() for _ in range(5)])

    def test_run_on_the_map(self):
        run = Run("sentinel", seed=17)
        clone = Run.from_dict(json.loads(json.dumps(run.to_dict())))
        self.assertEqual(clone.state(), run.state())

    def test_run_mid_combat(self):
        run = Run("ashwalker", seed=99)
        run.apply({"type": "map", "idx": run.reachable()[0]})
        self.assertEqual(run.screen, "combat")
        clone = Run.from_dict(json.loads(json.dumps(run.to_dict())))
        self.assertEqual(clone.state(), run.state())

    def test_resumed_run_stays_in_lockstep(self):
        """The property that makes resume trustworthy."""
        run = Run("ashwalker", seed=99)
        run.apply({"type": "map", "idx": run.reachable()[0]})
        clone = Run.from_dict(json.loads(json.dumps(run.to_dict())))
        for _ in range(6):
            if run.screen == "combat":
                run.apply({"type": "end_turn"})
            if clone.screen == "combat":
                clone.apply({"type": "end_turn"})
        self.assertEqual(clone.state(), run.state())

    def test_every_screen_survives_a_round_trip(self):
        seen = set()
        for seed in range(25):
            run = Run("sentinel", seed=seed)
            for _ in range(120):
                if run.finished:
                    break
                seen.add(run.screen)
                clone = Run.from_dict(json.loads(json.dumps(run.to_dict())))
                self.assertEqual(clone.state(), run.state(),
                                 f"round trip broke on screen {run.screen}")
                autoplay(run, seed=seed, max_steps=1, keep_alive=True)
        for screen in ("map", "combat", "reward"):
            self.assertIn(screen, seen)

    def test_save_is_json_clean_and_small(self):
        run = Run("sentinel", seed=1)
        run.apply({"type": "map", "idx": run.reachable()[0]})
        blob = json.dumps(run.to_dict())
        self.assertLess(len(blob), 200_000)


class TestRecords(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.path = os.path.join(self.dir, "records.json")

    def test_missing_file_reads_as_empty(self):
        self.assertEqual(records.load_records(self.path), [])

    def test_corrupt_file_reads_as_empty(self):
        with open(self.path, "w") as f:
            f.write("{not json")
        self.assertEqual(records.load_records(self.path), [])

    def test_records_are_ranked_and_truncated(self):
        for floors in range(20):
            records.save_record({"act": 1, "floors": floors, "won": False},
                                self.path)
        saved = records.load_records(self.path)
        self.assertEqual(len(saved), 10)
        self.assertEqual([r["floors"] for r in saved], sorted(
            [r["floors"] for r in saved], reverse=True))

    def test_write_is_atomic_and_leaves_no_temp_files(self):
        records.save_record({"act": 1, "floors": 3, "won": False}, self.path)
        leftovers = [f for f in os.listdir(self.dir) if f.endswith(".tmp")]
        self.assertEqual(leftovers, [])

    def test_write_failure_is_not_swallowed(self):
        """The old save_record hid every OSError behind `pass`."""
        bad = os.path.join(self.dir, "no-such-dir", "records.json")
        with self.assertRaises(OSError):
            records.save_record({"act": 1, "floors": 1, "won": False}, bad)


if __name__ == "__main__":
    unittest.main()
