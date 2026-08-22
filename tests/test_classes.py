"""The five classes added after the Sentinel and the Ashwalker.

The smoke test is the important one: it plays every card in every class pool,
upgraded and not, against a live enemy. A typo inside a card's `fx` lambda is
invisible until someone draws that card on a seed nobody can reproduce, and the
content tables only ever checked that the key existed.
"""

import unittest

from helpers import make_combat

from spire_of_ash import balance as B
from spire_of_ash.content.cards import CARDS
from spire_of_ash.content.classes import CLASSES
from spire_of_ash.engine.card import Card
from spire_of_ash.engine.combatant import Player, damage_after_modifiers

NEW_CLASSES = ("stormbound", "penitent", "gravewright", "emberbrewer", "hexbinder")


def combat_for(cls, enemies=("cultist", "jaw_worm")):
    cb = make_combat(enemies, cls=cls)
    cb.player_turn_start()
    return cb


class TestClassRoster(unittest.TestCase):
    def test_the_new_classes_are_playable(self):
        for cls in NEW_CLASSES:
            p = Player(cls)
            self.assertEqual(p.cls, cls)
            self.assertTrue(p.deck and p.relics)

    def test_every_pool_card_matches_the_rarity_of_its_slot(self):
        """Shop prices and reward rolls both read `rarity`, not the pool."""
        for cls, d in CLASSES.items():
            for rarity in ("common", "uncommon", "rare"):
                for key in d[rarity]:
                    self.assertEqual(CARDS[key].get("rarity", "common"), rarity,
                                     f"{cls}: {key} sits in the {rarity} pool")

    def test_starter_cards_are_not_also_in_the_pools(self):
        for cls, d in CLASSES.items():
            pool = set(d["common"] + d["uncommon"] + d["rare"])
            self.assertFalse(pool & set(d["deck"]), f"{cls} offers its own starters")

    def test_every_card_of_every_class_can_be_played(self):
        for cls, d in CLASSES.items():
            keys = set(d["deck"] + d["common"] + d["uncommon"] + d["rare"])
            for key in sorted(keys):
                for upgraded in (False, True):
                    with self.subTest(cls=cls, card=key, upgraded=upgraded):
                        self.play_once(cls, key, upgraded)

    def play_once(self, cls, key, upgraded):
        cb = combat_for(cls)
        card = Card(key, upgraded)
        cb.hand.append(card)
        cb.energy = 9
        # Cards that scale off things the fight has not produced yet still have
        # to survive being played into an empty combat, so seed a little of
        # everything they might read.
        cb.player.potions = ["fire"]
        cb.exhausted.append(Card("strike"))
        cb.apply(cb.enemies[0], "weak", 2)
        cb.play_card(len(cb.hand) - 1, target_idx=0,
                     exhaust=0 if card.requires == "exhaust" else None)
        cb.player_turn_end()


class TestStances(unittest.TestCase):
    def test_entering_wrath_doubles_damage_both_ways(self):
        cb = combat_for("penitent")
        foe = cb.enemies[0]
        cb.enter_stance("wrath")
        self.assertEqual(damage_after_modifiers(cb.player, 10, foe), 10 * B.WRATH_MULT)
        self.assertEqual(damage_after_modifiers(foe, 10, cb.player), 10 * B.WRATH_MULT)

    def test_only_one_stance_is_held_at_a_time(self):
        cb = combat_for("penitent")
        cb.enter_stance("wrath")
        cb.enter_stance("calm")
        self.assertEqual(cb.stance(), "calm")
        self.assertEqual(cb.player.s("wrath"), 0)

    def test_leaving_calm_hands_the_energy_back(self):
        cb = combat_for("penitent")
        cb.enter_stance("calm")
        before = cb.energy
        cb.enter_stance("wrath")
        self.assertEqual(cb.energy, before + B.CALM_EXIT_ENERGY)

    def test_mantra_spills_into_divinity(self):
        cb = combat_for("penitent")
        cb.player.st["mantra"] = 0          # the Prayer Bead has already given 3
        cb.gain_mantra(B.MANTRA_FOR_DIVINITY + 2)
        self.assertEqual(cb.stance(), "divinity")
        self.assertEqual(cb.player.s("mantra"), 2)

    def test_divinity_lasts_one_turn(self):
        cb = combat_for("penitent")
        cb.enter_stance("divinity")
        cb.player_turn_end()
        self.assertIsNone(cb.stance())

    def test_vigour_rides_the_next_attack_only(self):
        cb = combat_for("penitent", ("cultist",))
        foe = cb.enemies[0]
        foe.max_hp = foe.hp = 500
        cb.apply(cb.player, "vigour", 5)
        before = foe.hp
        cb.player_attack(foe, 10)
        self.assertEqual(before - foe.hp, 15)
        before = foe.hp
        cb.player_attack(foe, 10)
        self.assertEqual(before - foe.hp, 10)


class TestCoils(unittest.TestCase):
    def test_coils_strike_at_the_end_of_the_turn(self):
        cb = combat_for("stormbound", ("cultist",))
        foe = cb.enemies[0]
        foe.max_hp = foe.hp = 500
        cb.player.st["stormcoil"] = 2
        before = foe.hp
        cb.player_turn_end()
        self.assertEqual(before - foe.hp, 2 * B.COIL_DAMAGE)

    def test_focus_makes_every_coil_and_frost_bigger(self):
        cb = combat_for("stormbound", ("cultist",))
        foe = cb.enemies[0]
        foe.max_hp = foe.hp = 500
        cb.player.st["stormcoil"] = 1
        cb.player.st["frostward"] = 1
        cb.player.st["focus"] = 2
        before = foe.hp
        cb.player_turn_end()
        self.assertEqual(before - foe.hp, B.COIL_DAMAGE + 2)
        self.assertEqual(cb.player.block, B.FROST_BLOCK + 2)

    def test_you_can_only_hold_so_many(self):
        cb = combat_for("stormbound")
        cb.channel("stormcoil", B.COIL_CAP + 5)
        self.assertEqual(cb.player.s("stormcoil"), B.COIL_CAP)

    def test_overload_spends_the_whole_bank(self):
        cb = combat_for("stormbound", ("cultist",))
        foe = cb.enemies[0]
        foe.max_hp = foe.hp = 500
        cb.player.st["stormcoil"] = 3
        before = foe.hp
        cb.discharge_coils(5, foe)
        self.assertEqual(before - foe.hp, 15)
        self.assertEqual(cb.player.s("stormcoil"), 0)

    def test_echo_form_repeats_only_the_first_card_of_a_turn(self):
        cb = combat_for("stormbound", ("cultist",))
        foe = cb.enemies[0]
        foe.max_hp = foe.hp = 500
        cb.player.st["echoform"] = 1
        cb.hand = [Card("strike"), Card("strike")]
        cb.energy = 9
        before = foe.hp
        cb.play_card(0, target_idx=0)
        self.assertEqual(before - foe.hp, 12)
        before = foe.hp
        cb.play_card(0, target_idx=0)
        self.assertEqual(before - foe.hp, 6)


class TestTheGrave(unittest.TestCase):
    def test_soulfire_answers_every_exhaust(self):
        cb = combat_for("gravewright", ("cultist", "jaw_worm"))
        cb.player.st["soulfire"] = 3
        before = [e.hp for e in cb.enemies]
        cb.exhaust_card(Card("strike"))
        self.assertTrue(all(e.hp == b - 3 for e, b in zip(cb.enemies, before)))

    def test_ashen_embrace_draws_on_an_exhaust(self):
        cb = combat_for("gravewright")
        cb.player.st["ashenembrace"] = 1
        before = len(cb.hand)
        cb.exhaust_card(Card("strike"))
        self.assertEqual(len(cb.hand), before + 1)

    def test_exhausting_the_hand_does_not_burn_what_it_draws(self):
        """Ashen Embrace refills the hand while Cremation is still burning it."""
        cb = combat_for("gravewright")
        cb.player.st["ashenembrace"] = 1
        cb.hand = [Card("strike"), Card("defend")]
        self.assertEqual(cb.exhaust_hand(), 2)
        self.assertEqual(len(cb.hand), 2)          # the two it drew are still there

    def test_milling_feeds_the_exhaust_pile(self):
        cb = combat_for("gravewright")
        burned = cb.mill(2)
        self.assertEqual(burned, 2)
        self.assertEqual(len(cb.exhausted), 2)

    def test_reclaim_pulls_a_card_back(self):
        cb = combat_for("gravewright")
        cb.exhausted = [Card("strike")]
        cb.hand = []
        self.assertEqual(cb.reclaim(2), 1)
        self.assertEqual(len(cb.hand), 1)

    def test_the_phylactery_catches_a_killing_blow(self):
        cb = combat_for("gravewright", ("cultist",))
        cb.player.st["phylactery"] = 1
        cb.player.hp = 5
        cb.damage(cb.player, 999)
        self.assertEqual(cb.player.hp, min(cb.player.max_hp, B.PHYLACTERY_HP))
        self.assertEqual(cb.player.s("phylactery"), 0)

    def test_the_phylactery_only_works_once_per_stack(self):
        from spire_of_ash.engine.errors import Defeat
        cb = combat_for("gravewright", ("cultist",))
        cb.player.st["phylactery"] = 1
        cb.damage(cb.player, 999)
        with self.assertRaises(Defeat):
            cb.damage(cb.player, 999)


class TestBrewing(unittest.TestCase):
    def test_the_brewer_carries_a_deeper_belt(self):
        self.assertGreater(Player("emberbrewer").max_potions, Player("sentinel").max_potions)

    def test_brewing_fills_the_belt_and_then_stops(self):
        cb = combat_for("emberbrewer")
        cb.player.potions = []
        made = cb.brew(n=cb.player.max_potions + 3)
        self.assertEqual(made, cb.player.max_potions)
        self.assertEqual(len(cb.player.potions), cb.player.max_potions)

    def test_a_named_potion_is_the_one_you_get(self):
        cb = combat_for("emberbrewer")
        cb.player.potions = []
        cb.brew("fire")
        self.assertEqual(cb.player.potions, ["fire"])

    def test_potency_runs_a_potion_twice(self):
        cb = combat_for("emberbrewer", ("cultist",))
        foe = cb.enemies[0]
        foe.max_hp = foe.hp = 500
        cb.player.potions = ["fire", "fire"]
        cb.use_potion(0, target_idx=0)
        plain = 500 - foe.hp
        cb.player.st["potency"] = 1
        before = foe.hp
        cb.use_potion(0, target_idx=0)
        self.assertEqual(before - foe.hp, plain * 2)

    def test_volatility_fires_when_you_drink(self):
        cb = combat_for("emberbrewer", ("cultist", "jaw_worm"))
        cb.player.potions = ["block"]
        cb.player.st["volatility"] = 4
        before = [e.hp for e in cb.enemies]
        cb.use_potion(0)
        self.assertTrue(all(e.hp == b - 4 for e, b in zip(cb.enemies, before)))


class TestHexes(unittest.TestCase):
    def test_hexbloom_bites_when_a_debuff_lands(self):
        cb = combat_for("hexbinder", ("cultist",))
        foe = cb.enemies[0]
        foe.max_hp = foe.hp = 500
        cb.player.st["hexbloom"] = 3
        cb.apply(foe, "weak", 1)
        self.assertEqual(foe.hp, 497)

    def test_hexbloom_ignores_buffs_and_your_own_debuffs(self):
        cb = combat_for("hexbinder", ("cultist",))
        foe = cb.enemies[0]
        foe.max_hp = foe.hp = 500
        cb.player.st["hexbloom"] = 3
        cb.apply(foe, "strength", 2)
        cb.apply(cb.player, "weak", 2)
        self.assertEqual(foe.hp, 500)

    def test_draining_strength_counts_as_weakening(self):
        cb = combat_for("hexbinder", ("cultist",))
        foe = cb.enemies[0]
        foe.max_hp = foe.hp = 500
        cb.player.st["hexbloom"] = 3
        cb.apply(foe, "strength", -1)
        self.assertEqual(foe.hp, 497)

    def test_debuff_stacks_count_drained_strength_too(self):
        cb = combat_for("hexbinder", ("cultist",))
        foe = cb.enemies[0]
        cb.apply(foe, "weak", 2)
        cb.apply(foe, "frail", 1)
        cb.apply(foe, "strength", -2)
        self.assertEqual(cb.debuff_stacks(foe), 5)

    def test_frail_now_bites_enemies(self):
        """Frail did nothing to an enemy, which made half the pool a dead card."""
        cb = combat_for("hexbinder", ("cultist",))
        foe = cb.enemies[0]
        cb.gain_block(foe, 10)
        plain = foe.block
        foe.block = 0
        cb.apply(foe, "frail", 1)
        cb.gain_block(foe, 10)
        self.assertLess(foe.block, plain)

    def test_long_grudge_stops_debuffs_wearing_off(self):
        cb = combat_for("hexbinder", ("cultist",))
        foe = cb.enemies[0]
        cb.apply(foe, "weak", 3)
        cb.apply(foe, "entrenched", 1)
        cb.enemy_turns()
        self.assertEqual(foe.s("weak"), 3)

    def test_scapegoat_moves_your_debuffs_along(self):
        cb = combat_for("hexbinder", ("cultist",))
        foe = cb.enemies[0]
        cb.apply(cb.player, "weak", 2)
        cb.apply(cb.player, "vulnerable", 1)
        self.assertEqual(cb.scapegoat(foe), 3)
        self.assertEqual(cb.player.s("weak"), 0)
        self.assertEqual(foe.s("weak"), 2)
        self.assertEqual(foe.s("vulnerable"), 1)


if __name__ == "__main__":
    unittest.main()
