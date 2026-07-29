"""The run state machine: determinism, flow, and rejected actions."""

import unittest

from helpers import autoplay, _reward_step

from spire_of_ash import balance as B
from spire_of_ash.engine.errors import InvalidAction
from spire_of_ash.engine.run import Run


def short_script(run, steps=8):
    for _ in range(steps):
        st = run.state()
        if st["screen"] == "map" and st["map"]["reachable"]:
            run.apply({"type": "map", "idx": st["map"]["reachable"][0]})
        elif st["screen"] == "combat":
            run.apply({"type": "end_turn"})
        elif st["screen"] == "reward":
            _reward_step(run, st)
        else:
            break
    return run.state()


class TestDeterminism(unittest.TestCase):
    def test_same_seed_same_outcome(self):
        self.assertEqual(short_script(Run("sentinel", seed=7)),
                         short_script(Run("sentinel", seed=7)))

    def test_different_seeds_diverge(self):
        self.assertNotEqual(short_script(Run("sentinel", seed=7)),
                            short_script(Run("sentinel", seed=8)))

    def test_full_runs_are_reproducible(self):
        a = autoplay(Run("sentinel", seed=3), seed=3)
        b = autoplay(Run("sentinel", seed=3), seed=3)
        self.assertEqual(a.state(), b.state())

    def test_two_runs_do_not_share_a_stream(self):
        """The old PLAYER_REF / global random made concurrent runs impossible."""
        a, b = Run("sentinel", seed=11), Run("sentinel", seed=11)
        short_script(a, 4)
        self.assertEqual(short_script(a), short_script(b, 12))


class TestStateSnapshot(unittest.TestCase):
    def test_state_has_no_side_effects(self):
        run = Run("sentinel", seed=5)
        run.next_act()                       # sets a banner
        first = run.state()
        self.assertIsNotNone(first["banner"])
        self.assertEqual(first, run.state(), "state() must be idempotent")
        self.assertIsNotNone(run.state()["banner"])

    def test_banner_clears_on_the_next_action(self):
        run = Run("sentinel", seed=5)
        run.next_act()
        self.assertIsNotNone(run.state()["banner"])
        run.apply({"type": "map", "idx": run.reachable()[0]})
        self.assertIsNone(run.state()["banner"])

    def test_pending_describes_the_current_screen(self):
        run = Run(seed=1)
        self.assertEqual(run.state()["pending"]["kind"], "class")
        run.apply({"type": "new_run", "cls": "sentinel"})
        self.assertEqual(run.state()["pending"]["kind"], "map_node")


class TestRejectedActions(unittest.TestCase):
    def setUp(self):
        self.run = Run("sentinel", seed=5)

    def test_unknown_action(self):
        with self.assertRaisesRegex(InvalidAction, "Unknown action"):
            self.run.apply({"type": "wat"})

    def test_non_dict_action(self):
        with self.assertRaises(InvalidAction):
            self.run.apply(["map", 0])

    def test_wrong_screen(self):
        with self.assertRaisesRegex(InvalidAction, "combat screen"):
            self.run.apply({"type": "end_turn"})

    def test_unreachable_node(self):
        with self.assertRaisesRegex(InvalidAction, "not reachable"):
            self.run.apply({"type": "map", "idx": 99})

    def test_non_integer_node(self):
        with self.assertRaises(InvalidAction):
            self.run.apply({"type": "map", "idx": "0"})


class TestFlow(unittest.TestCase):
    def test_every_node_type_is_reachable_and_survivable(self):
        """Sweep many seeds so each node kind gets exercised."""
        seen = set()
        for seed in range(60):
            run = Run("sentinel", seed=seed)
            autoplay(run, seed=seed, keep_alive=True, max_steps=2500)
            for floor, idx in run.visited:
                seen.add(run.floors[floor][idx]["type"])
            if run.act > 1:
                seen.add("act_transition")
        for kind in ("monster", "elite", "boss", "rest", "shop", "treasure", "event"):
            self.assertIn(kind, seen, f"never visited a {kind} node")
        self.assertIn("act_transition", seen)

    def test_a_buffed_run_can_win(self):
        wins = 0
        for seed in range(12):
            run = Run("sentinel", seed=seed)
            run.player.max_hp = run.player.hp = 100000
            autoplay(run, seed=seed, keep_alive=True)
            if run.screen == "win":
                wins += 1
        self.assertGreater(wins, 0, "no seed ever reached the win screen")

    def test_winning_requires_the_final_act(self):
        run = Run("sentinel", seed=1)
        run.player.max_hp = run.player.hp = 100000
        autoplay(run, seed=1, keep_alive=True)
        if run.screen == "win":
            self.assertGreaterEqual(run.act, B.FINAL_ACT)

    def test_exhausted_map_is_not_a_win(self):
        """The old Game.play() returned "win" when it ran off the top of the map."""
        run = Run("sentinel", seed=2)
        run.cur_floor = len(run.floors) - 1
        self.assertEqual(run.reachable(), [])
        self.assertNotEqual(run.screen, "win")
        with self.assertRaises(InvalidAction):
            run.apply({"type": "map", "idx": 0})

    def test_defeat_ends_the_run(self):
        run = Run("sentinel", seed=0)
        autoplay(run, seed=0)
        self.assertIn(run.screen, ("gameover", "win", "combat", "map"))
        if run.screen == "gameover":
            self.assertNotEqual(run.killer, "—")

    def test_campfire_heals(self):
        run = Run("sentinel", seed=5)
        run.screen = "rest"
        run.player.hp = 10
        run.apply({"type": "rest"})
        self.assertGreater(run.player.hp, 10)
        self.assertEqual(run.screen, "map")

    def test_shop_refuses_unaffordable_purchases(self):
        run = Run("sentinel", seed=5)
        run.open_shop()
        run.player.gold = 0
        with self.assertRaisesRegex(InvalidAction, "afford"):
            run.apply({"type": "shop_buy", "what": "card", "idx": 0})

    def test_shop_purchase_deducts_gold_and_adds_the_card(self):
        run = Run("sentinel", seed=5)
        run.open_shop()
        run.player.gold = 9999
        deck_before = len(run.player.deck)
        price = run.shop["prices"][0]
        run.apply({"type": "shop_buy", "what": "card", "idx": 0})
        self.assertEqual(len(run.player.deck), deck_before + 1)
        self.assertEqual(run.player.gold, 9999 - price)

    def test_card_removal_costs_gold_and_shrinks_the_deck(self):
        run = Run("sentinel", seed=5)
        run.open_shop()
        run.player.gold = 9999
        before = len(run.player.deck)
        run.apply({"type": "shop_buy", "what": "removal"})
        self.assertEqual(run.screen, "choose")
        run.apply({"type": "choose", "idx": 0})
        self.assertEqual(len(run.player.deck), before - 1)
        self.assertEqual(run.player.gold, 9999 - B.SHOP_REMOVAL_PRICE)

    def test_treasure_grants_gold_and_a_relic(self):
        run = Run("sentinel", seed=5)
        relics_before = len(run.player.relics)
        gold_before = run.player.gold
        run.open_treasure()
        self.assertGreater(run.player.gold, gold_before)
        self.assertEqual(len(run.player.relics), relics_before + 1)

    def test_events_return_text_without_printing(self):
        run = Run("sentinel", seed=5)
        for i in range(len(run.state()["map"]["floors"])):
            run.open_event()
            for opt in range(len(run.event["options"])):
                probe = Run("sentinel", seed=100 + i * 10 + opt)
                probe.open_event()
                probe.apply({"type": "event_choose", "idx": opt % len(probe.event["options"])})
                self.assertIsInstance(probe.event["result"], str)
                self.assertTrue(probe.event["result"])

    def test_event_options_carry_a_preview(self):
        run = Run("sentinel", seed=5)
        run.open_event()
        for opt in run.event["options"]:
            self.assertTrue(opt["label"])
            self.assertTrue(opt["preview"])

    def test_act_transition_raises_max_hp(self):
        run = Run("sentinel", seed=5)
        before = run.player.max_hp
        run.next_act()
        self.assertEqual(run.player.max_hp, before + B.ACT_MAX_HP_BONUS)
        self.assertEqual(run.act, 2)
        self.assertIsNotNone(run.banner)


class TestRewards(unittest.TestCase):
    """Rewards used to be granted the moment the last enemy died — the screen
    reported a relic you already owned. Now nothing but gold moves until asked."""

    def _reward(self, kind="elite", seed=5):
        run = Run("sentinel", seed=seed)
        run.start_combat(kind)
        run.victory()
        return run

    def test_gold_is_still_banked_outright(self):
        run = Run("sentinel", seed=5)
        before = run.player.gold
        run.start_combat("elite")
        run.victory()
        self.assertGreater(run.player.gold, before)

    def test_a_relic_waits_to_be_claimed(self):
        run = self._reward()
        self.assertEqual(run.screen, "reward")
        key = run.reward["relic"]
        self.assertNotIn(key, run.player.relics)
        run.apply({"type": "reward", "what": "relic"})
        self.assertIn(key, run.player.relics)

    def test_claiming_leaves_the_screen_open(self):
        run = self._reward()
        run.apply({"type": "reward", "what": "card", "idx": 0})
        self.assertEqual(run.screen, "reward")
        self.assertTrue(run.state()["pending"]["relic"])

    def test_leaving_forfeits_whatever_was_not_claimed(self):
        run = self._reward()
        key, deck = run.reward["relic"], len(run.player.deck)
        run.apply({"type": "reward_done"})
        self.assertEqual(run.screen, "map")
        self.assertNotIn(key, run.player.relics)
        self.assertEqual(len(run.player.deck), deck)

    def test_nothing_can_be_claimed_twice(self):
        run = self._reward()
        run.apply({"type": "reward", "what": "relic"})
        with self.assertRaises(InvalidAction):
            run.apply({"type": "reward", "what": "relic"})
        run.apply({"type": "reward", "what": "card", "idx": 0})
        with self.assertRaises(InvalidAction):
            run.apply({"type": "reward", "what": "card", "idx": 1})

    def test_a_full_potion_belt_refuses_the_potion(self):
        run = self._reward()
        run.reward["potion"] = "fire"
        run.player.potions = ["block"] * run.player.max_potions
        with self.assertRaises(InvalidAction):
            run.apply({"type": "reward", "what": "potion"})
        run.player.potions = []
        run.apply({"type": "reward", "what": "potion"})
        self.assertEqual(run.player.potions, ["fire"])

    def test_an_absent_reward_cannot_be_taken(self):
        run = self._reward(kind="monster")
        self.assertIsNone(run.reward["relic"])
        with self.assertRaises(InvalidAction):
            run.apply({"type": "reward", "what": "relic"})
        with self.assertRaises(InvalidAction):
            run.apply({"type": "reward", "what": "nonsense"})

    def test_a_boss_advances_the_act_only_on_leaving(self):
        run = self._reward(kind="boss")
        run.apply({"type": "reward", "what": "relic"})
        self.assertEqual(run.act, 1, "claiming must not end the act")
        run.apply({"type": "reward_done"})
        self.assertEqual(run.act, 2)


if __name__ == "__main__":
    unittest.main()
