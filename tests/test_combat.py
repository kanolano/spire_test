"""Combat rules: damage, block, statuses, energy, piles, card requirements."""

import unittest

from helpers import make_combat

from spire_of_ash import balance as B
from spire_of_ash.engine.card import Card
from spire_of_ash.engine.combatant import Enemy, Player, damage_after_modifiers
from spire_of_ash.engine.errors import Defeat, InvalidAction
from spire_of_ash.rng import Rng


class TestDamage(unittest.TestCase):
    def setUp(self):
        self.cb = make_combat()
        self.foe = self.cb.enemies[0]

    def test_block_absorbs_before_hp(self):
        self.foe.block = 5
        self.assertEqual(self.cb.damage(self.foe, 8), 3)
        self.assertEqual(self.foe.block, 0)

    def test_block_can_fully_absorb(self):
        self.foe.block = 20
        before = self.foe.hp
        self.assertEqual(self.cb.damage(self.foe, 8), 0)
        self.assertEqual(self.foe.hp, before)
        self.assertEqual(self.foe.block, 12)

    def test_ignore_block_bypasses_block(self):
        self.foe.block = 20
        before = self.foe.hp
        self.assertEqual(self.cb.damage(self.foe, 7, ignore_block=True), 7)
        self.assertEqual(self.foe.hp, before - 7)
        self.assertEqual(self.foe.block, 20)

    def test_thorns_hurt_the_attacker(self):
        self.foe.st["thorns"] = 3
        before = self.cb.player.hp
        self.cb.player_attack(self.foe, 5)
        self.assertEqual(self.cb.player.hp, before - 3)

    def test_death_raises_defeat_naming_the_killer(self):
        self.cb.player.hp = 1
        with self.assertRaisesRegex(Defeat, "Cultist"):
            self.cb.damage(self.cb.player, 50)

    def test_killing_the_last_enemy_ends_combat(self):
        self.cb.kill(self.foe)
        self.assertTrue(self.cb.over())


class TestModifiers(unittest.TestCase):
    def setUp(self):
        self.player = Player("sentinel")
        self.foe = Enemy("cultist", 1, Rng(1))

    def test_vulnerable_increases_damage_taken(self):
        plain = damage_after_modifiers(self.player, 10, self.foe)
        self.foe.st["vulnerable"] = 1
        self.assertEqual(damage_after_modifiers(self.player, 10, self.foe),
                         int(plain * B.VULNERABLE_MULT))

    def test_weak_reduces_damage_dealt(self):
        plain = damage_after_modifiers(self.player, 10, self.foe)
        self.player.st["weak"] = 1
        self.assertEqual(damage_after_modifiers(self.player, 10, self.foe),
                         int(plain * B.WEAK_MULT))

    def test_strength_adds_flat_damage(self):
        self.player.st["strength"] = 3
        self.assertEqual(damage_after_modifiers(self.player, 10, self.foe), 13)

    def test_damage_never_goes_negative(self):
        self.player.st["strength"] = -50
        self.assertEqual(damage_after_modifiers(self.player, 5, self.foe), 0)


class TestBlockAndStatuses(unittest.TestCase):
    def setUp(self):
        self.cb = make_combat()

    def test_frail_reduces_block(self):
        self.cb.player.st["frail"] = 1
        self.cb.gain_block(self.cb.player, 10)
        self.assertEqual(self.cb.player.block, int(10 * B.FRAIL_MULT))

    def test_dexterity_adds_block(self):
        self.cb.player.st["dexterity"] = 4
        self.cb.gain_block(self.cb.player, 5)
        self.assertEqual(self.cb.player.block, 9)

    def test_poison_damages_and_ticks_down(self):
        foe = self.cb.enemies[0]
        foe.st["poison"] = 3
        before = foe.hp
        self.cb.enemy_turns()
        self.assertEqual(foe.hp, before - 3)
        self.assertEqual(foe.s("poison"), 2)

    def test_decaying_statuses_tick_but_strength_does_not(self):
        self.cb.player.st["vulnerable"] = 2
        self.cb.player.st["strength"] = 2
        self.cb.player_turn_end()
        self.assertEqual(self.cb.player.s("vulnerable"), 1)
        self.assertEqual(self.cb.player.s("strength"), 2)

    def test_block_clears_at_turn_start(self):
        self.cb.player.block = 12
        self.cb.player_turn_start()
        self.assertEqual(self.cb.player.block, 0)

    def test_barricade_keeps_block(self):
        self.cb.player.st["barricade"] = 1
        self.cb.player.block = 12
        self.cb.player_turn_start()
        self.assertGreaterEqual(self.cb.player.block, 12)


class TestPiles(unittest.TestCase):
    def setUp(self):
        self.cb = make_combat()

    def test_hand_limit_is_respected(self):
        self.cb.hand = [Card("strike") for _ in range(B.HAND_LIMIT)]
        self.cb.draw(3)
        self.assertEqual(len(self.cb.hand), B.HAND_LIMIT)

    def test_draw_reshuffles_the_discard_pile(self):
        self.cb.draw_pile = []
        self.cb.discard = [Card("strike"), Card("defend")]
        self.cb.draw(1)
        self.assertEqual(len(self.cb.hand), 1)
        self.assertEqual(len(self.cb.draw_pile) + len(self.cb.discard), 1)

    def test_draw_from_nothing_is_safe(self):
        self.cb.draw_pile = []
        self.cb.discard = []
        self.cb.hand = []
        self.cb.draw(5)
        self.assertEqual(self.cb.hand, [])


class TestPlayingCards(unittest.TestCase):
    def setUp(self):
        self.cb = make_combat()
        self.cb.player_turn_start()

    def test_energy_is_spent(self):
        self.cb.hand = [Card("strike")]
        before = self.cb.energy
        self.cb.play_card(0, target_idx=0)
        self.assertEqual(self.cb.energy, before - 1)

    def test_cannot_play_without_energy(self):
        self.cb.energy = 0
        self.cb.hand = [Card("strike")]
        with self.assertRaisesRegex(InvalidAction, "energy"):
            self.cb.play_card(0, target_idx=0)

    def test_unplayable_card_is_refused(self):
        self.cb.hand = [Card("burn")]
        with self.assertRaises(InvalidAction):
            self.cb.play_card(0)

    def test_out_of_range_index_is_refused(self):
        with self.assertRaises(InvalidAction):
            self.cb.play_card(99)

    def test_non_integer_index_is_refused(self):
        """Previously a TypeError -> HTTP 500 -> a silently frozen UI."""
        self.cb.hand = [Card("strike")]
        with self.assertRaises(InvalidAction):
            self.cb.play_card("1")

    def test_boolean_index_is_refused(self):
        self.cb.hand = [Card("strike")]
        with self.assertRaises(InvalidAction):
            self.cb.play_card(True)

    def test_power_card_leaves_play(self):
        self.cb.energy = 9
        self.cb.hand = [Card("inflame")]
        self.cb.play_card(0)
        self.assertEqual(self.cb.hand, [])
        self.assertTrue(all(k.type != "POWER" for k in self.cb.discard))

    def test_x_cost_consumes_all_energy(self):
        self.cb.energy = 4
        self.cb.hand = [Card("whirlwind")]
        self.cb.play_card(0)
        self.assertEqual(self.cb.energy, 0)
        self.assertEqual(self.cb.x_spent, 4)

    def test_sole_enemy_is_auto_targeted(self):
        self.cb.hand = [Card("strike")]
        self.cb.play_card(0)      # no target supplied

    def test_target_required_when_several_enemies_live(self):
        cb = make_combat(("cultist", "jaw_worm"))
        cb.player_turn_start()
        cb.hand = [Card("strike")]
        with self.assertRaisesRegex(InvalidAction, "target"):
            cb.play_card(0)

    def test_dead_enemy_cannot_be_targeted(self):
        cb = make_combat(("cultist", "jaw_worm"))
        cb.player_turn_start()
        cb.enemies[0].alive = False
        cb.hand = [Card("strike")]
        with self.assertRaises(InvalidAction):
            cb.play_card(0, target_idx=0)


class TestTrueGrit(unittest.TestCase):
    """The pre-declared-choice path, including its off-by-one."""

    def test_upgraded_grit_declares_its_requirement(self):
        self.assertEqual(Card("true_grit", upgraded=True).requires, "exhaust")
        self.assertIsNone(Card("true_grit").requires)

    def test_chosen_card_is_exhausted_after_index_shift(self):
        cb = make_combat()
        cb.player_turn_start()
        cb.energy = 9
        grit = Card("true_grit", upgraded=True)
        keep, doomed = Card("strike"), Card("defend")
        cb.hand = [grit, keep, doomed]
        # index 2 names `doomed` in the hand as the player saw it
        cb.play_card(0, exhaust=2)
        self.assertIn(doomed, cb.exhausted)
        self.assertIn(keep, cb.hand)

    def test_unupgraded_grit_exhausts_something(self):
        cb = make_combat()
        cb.player_turn_start()
        cb.energy = 9
        cb.hand = [Card("true_grit"), Card("strike"), Card("defend")]
        cb.play_card(0)
        self.assertEqual(len(cb.exhausted), 1)


class TestLog(unittest.TestCase):
    def test_log_contains_no_ansi(self):
        """Styling is the client's job; the engine emits plain text."""
        cb = make_combat()
        cb.msg("Pen Nib doubles the blow!")
        cb.kill(cb.enemies[0])
        self.assertTrue(all("\033" not in line for line in cb.log))

    def test_log_is_bounded(self):
        cb = make_combat()
        for i in range(200):
            cb.msg(f"line {i}")
        self.assertLessEqual(len(cb.log), B.COMBAT_LOG_LEN)


if __name__ == "__main__":
    unittest.main()
