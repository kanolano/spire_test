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


class TestEnemyTurnGuards(unittest.TestCase):
    """An enemy that dies partway through the enemy phase must stop acting.

    A multi-hit attacker killed by Thorns used to finish every remaining hit
    after it was dead, so the player took damage from an enemy the screen was
    already drawing as slain.
    """

    def test_a_dead_enemy_stops_mid_attack(self):
        cb = make_combat(("guardian",))
        cb.start_combat()
        foe = cb.enemies[0]
        foe.intent = "Whirlwind"            # 5 damage, four hits
        cb.player.st["thorns"] = 9999       # the first hit kills it
        cb.player.block = 0
        before = cb.player.hp
        cb.enemy_turns()
        self.assertFalse(foe.alive)
        self.assertEqual(before - cb.player.hp, 5, "only the first hit lands")

    def test_a_dead_enemy_does_not_fire_its_move_effect(self):
        cb = make_combat(("guardian",))
        cb.start_combat()
        foe = cb.enemies[0]
        foe.intent = "Twin Slam"            # 8 x2, and grants itself Strength
        cb.player.st["thorns"] = 9999
        cb.enemy_turns()
        self.assertFalse(foe.alive)
        self.assertEqual(foe.s("strength"), 0, "a corpse does not buff itself")

    def test_an_enemy_killed_by_another_does_not_take_its_turn(self):
        cb = make_combat(("cultist", "cultist"))
        cb.start_combat()
        first, second = cb.enemies
        for e in cb.enemies:
            e.intent = "Dark Strike" if "Dark Strike" in e.moves else list(e.moves)[0]
        # the first one's turn kills the second outright
        cb.kill(second)
        before = cb.player.hp
        cb.enemy_turns()
        self.assertLessEqual(cb.player.hp, before)
        self.assertFalse(second.alive)


class TestUnattributedDamage(unittest.TestCase):
    """HP that vanishes at end of turn needs a line in the log to explain it."""

    def test_burn_says_so(self):
        cb = make_combat()
        cb.start_combat()
        cb.hand = [Card("burn")]
        cb.player_turn_end()
        self.assertTrue(any("Burn" in line for line in cb.log), cb.log)

    def test_regret_says_so(self):
        cb = make_combat()
        cb.start_combat()
        cb.hand = [Card("regret"), Card("strike")]
        cb.player_turn_end()
        self.assertTrue(any("Regret" in line for line in cb.log), cb.log)


class TestIntentPreview(unittest.TestCase):
    """The intent number is what the player blocks against, so it has to equal
    the damage that actually lands — not the damage as of the instant it is
    drawn. Ritual fired before the enemy swung and was never counted, so a
    Cultist hit for its Ritual value more than advertised, every turn."""

    def assertPredicts(self, setup, enemies=("cultist",), move="Dark Strike"):
        cb = make_combat(enemies)
        cb.start_combat()
        cb.player_turn_start()
        foe = cb.enemies[0]
        foe.intent = move
        setup(cb, foe)
        preview = foe.intent_preview(cb.player)
        shown = preview["damage"] * preview["hits"]
        cb.player.block = 0
        before = cb.player.hp
        cb.player_turn_end()
        cb.enemy_turns()
        self.assertEqual(shown, before - cb.player.hp)

    def test_plain_attack(self):
        self.assertPredicts(lambda cb, e: None)

    def test_ritual_strength_lands_before_the_blow(self):
        self.assertPredicts(lambda cb, e: e.st.__setitem__("ritual", 3))

    def test_a_last_stack_of_vulnerable_has_already_worn_off(self):
        """It decays at the end of the player's turn, before any enemy acts."""
        self.assertPredicts(lambda cb, e: cb.player.st.__setitem__("vulnerable", 1))

    def test_vulnerable_that_survives_the_tick_still_counts(self):
        self.assertPredicts(lambda cb, e: cb.player.st.__setitem__("vulnerable", 2))

    def test_ritual_and_vulnerable_together(self):
        self.assertPredicts(lambda cb, e: (e.st.__setitem__("ritual", 3),
                                           cb.player.st.__setitem__("vulnerable", 2)))

    def test_weak_on_the_attacker_still_applies(self):
        """The enemy's own debuffs decay after it acts, so they do count."""
        self.assertPredicts(lambda cb, e: e.st.__setitem__("weak", 2))

    def test_strength(self):
        self.assertPredicts(lambda cb, e: e.st.__setitem__("strength", 4))

    def test_multi_hit(self):
        self.assertPredicts(lambda cb, e: None, ("guardian",), "Whirlwind")

    def test_multi_hit_against_a_vulnerable_player(self):
        self.assertPredicts(lambda cb, e: cb.player.st.__setitem__("vulnerable", 2),
                            ("guardian",), "Whirlwind")

    def test_preview_does_not_mutate_anything(self):
        cb = make_combat(("cultist",))
        cb.start_combat()
        foe = cb.enemies[0]
        foe.intent = "Dark Strike"
        foe.st["ritual"] = 3
        cb.player.st["vulnerable"] = 2
        for _ in range(3):
            foe.intent_preview(cb.player)
        self.assertEqual(foe.s("strength"), 0)
        self.assertEqual(foe.s("ritual"), 3)
        self.assertEqual(cb.player.s("vulnerable"), 2)


class TestEffectStream(unittest.TestCase):
    """The ordered record of what happened, which the browser client animates.

    These assert *order and attribution*, not presentation. A client that shows
    a lunge before the damage it caused, or credits a blow to the wrong enemy,
    is reading this stream — so the stream is what has to be right.
    """

    def kinds(self, cb):
        return [e["k"] for e in cb.fx]

    def only(self, cb, k):
        return [e for e in cb.fx if e["k"] == k]

    def test_a_blow_is_reported_with_what_block_ate(self):
        cb = make_combat()
        foe = cb.enemies[0]
        foe.block = 4
        cb.fx.clear()
        cb.damage(foe, 10)
        hit, = self.only(cb, "damage")
        self.assertEqual(hit["who"], 0)
        self.assertEqual(hit["blocked"], 4)
        self.assertEqual(hit["amount"], 6)
        self.assertEqual(hit["hp"], foe.hp)

    def test_a_fully_blocked_blow_still_reports(self):
        """Block shattering is worth showing; it used to be indistinguishable
        from nothing happening."""
        cb = make_combat()
        foe = cb.enemies[0]
        foe.block = 20
        cb.fx.clear()
        cb.damage(foe, 5)
        hit, = self.only(cb, "damage")
        self.assertEqual((hit["amount"], hit["blocked"]), (0, 5))

    def test_the_swing_comes_before_the_damage_it_causes(self):
        cb = make_combat()
        cb.fx.clear()
        cb.player_attack(cb.enemies[0], 6)
        kinds = self.kinds(cb)
        self.assertLess(kinds.index("swing"), kinds.index("damage"))

    def test_every_hit_of_a_multi_hit_attack_is_its_own_swing(self):
        cb = make_combat(("cultist",))
        cb.enemies[0].hp = 500
        cb.fx.clear()
        cb.player_attack(cb.enemies[0], 3, times=4)
        self.assertEqual(len(self.only(cb, "swing")), 4)
        self.assertEqual(len(self.only(cb, "damage")), 4)

    def test_a_dead_enemy_stops_swinging_mid_attack(self):
        """The engine already stopped resolving hits after a kill; the stream
        must not claim they landed."""
        cb = make_combat(("cultist",))
        cb.enemies[0].hp = 4
        cb.fx.clear()
        cb.player_attack(cb.enemies[0], 4, times=5)
        self.assertEqual(len(self.only(cb, "swing")), 1)
        self.assertEqual(len(self.only(cb, "death")), 1)

    def test_death_is_reported_before_the_line_that_announces_it(self):
        cb = make_combat(("cultist",))
        cb.enemies[0].hp = 3
        cb.fx.clear()
        cb.player_attack(cb.enemies[0], 20)
        kinds = self.kinds(cb)
        self.assertLess(kinds.index("death"), kinds.index("log"))

    def test_each_enemy_turn_is_bracketed(self):
        cb = make_combat(("cultist", "jaw_worm"))
        cb.player_turn_start()
        cb.fx.clear()
        cb.enemy_turns()
        acts = self.only(cb, "act")
        ends = self.only(cb, "act_end")
        self.assertEqual([a["who"] for a in acts], [0, 1])
        self.assertEqual([a["who"] for a in ends], [0, 1])

    def test_the_bracket_closes_even_when_the_enemy_dies_inside_it(self):
        cb = make_combat(("cultist",))
        foe = cb.enemies[0]
        cb.player.st["thorns"] = 999
        foe.hp = 1
        foe.intent = next(m for m, spec in foe.moves.items()
                          if spec["kind"] == "attack")
        cb.fx.clear()
        cb.enemy_turns()
        self.assertEqual(len(self.only(cb, "act")), 1)
        self.assertEqual(len(self.only(cb, "act_end")), 1)

    def test_the_bracket_closes_even_when_the_player_dies_inside_it(self):
        cb = make_combat(("jaw_worm",))
        cb.player.hp = 1
        foe = cb.enemies[0]
        foe.intent = next(m for m, spec in foe.moves.items()
                          if spec["kind"] == "attack")
        cb.fx.clear()
        with self.assertRaises(Defeat):
            cb.enemy_turns()
        self.assertEqual(len(self.only(cb, "act_end")), 1)

    def test_the_killing_blow_is_recorded_before_defeat_unwinds(self):
        cb = make_combat()
        cb.player.hp = 2
        cb.fx.clear()
        with self.assertRaises(Defeat):
            cb.damage(cb.player, 50)
        hit, = self.only(cb, "damage")
        self.assertEqual((hit["who"], hit["hp"]), ("player", 0))

    def test_playing_a_card_reports_the_play_before_its_effect(self):
        cb = make_combat()
        cb.player_turn_start()
        cb.hand = [Card("strike")]
        cb.energy = 3
        cb.fx.clear()
        cb.play_card(0, 0)
        kinds = self.kinds(cb)
        self.assertLess(kinds.index("play"), kinds.index("damage"))
        play, = self.only(cb, "play")
        self.assertEqual((play["key"], play["target"]), ("strike", 0))

    def test_a_played_card_reaches_the_discard_in_the_stream(self):
        cb = make_combat()
        cb.player_turn_start()
        cb.hand = [Card("strike")]
        cb.energy = 3
        cb.fx.clear()
        cb.play_card(0, 0)
        self.assertEqual([d["key"] for d in self.only(cb, "discard")], ["strike"])

    def test_drawing_reports_one_event_per_card(self):
        cb = make_combat()
        cb.fx.clear()
        cb.player_turn_start()
        self.assertEqual(len(self.only(cb, "draw")), B.BASE_DRAW)
        self.assertEqual(self.kinds(cb)[0], "turn")

    def test_block_and_statuses_carry_their_running_total(self):
        cb = make_combat()
        cb.fx.clear()
        cb.gain_block(cb.player, 5)
        cb.gain_block(cb.player, 3)
        self.assertEqual([b["total"] for b in self.only(cb, "block")], [5, 8])
        cb.fx.clear()
        cb.apply(cb.enemies[0], "vulnerable", 2)
        vuln, = self.only(cb, "status")
        self.assertEqual((vuln["key"], vuln["n"], vuln["total"]), ("vulnerable", 2, 2))

    def test_the_log_is_interleaved_rather_than_appended_at_the_end(self):
        """A log line is an event in its own right, so the combat log can
        scroll in step with the action instead of arriving all at once."""
        cb = make_combat(("cultist",))
        cb.enemies[0].hp = 2
        cb.fx.clear()
        cb.player_attack(cb.enemies[0], 50)
        self.assertEqual([e["text"] for e in self.only(cb, "log")],
                         ["Cultist is slain!"])
