"""Relic hooks and content-table integrity.

The integrity tests are cheap insurance: a card key typo'd into a class pool used
to surface as a KeyError mid-run, on a seed you could not reproduce.
"""

import unittest

from helpers import make_combat

from spire_of_ash import balance as B
from spire_of_ash.content.cards import CARDS
from spire_of_ash.content.classes import CLASSES, DEFAULT_CLASS
from spire_of_ash.content.events import EVENTS, preview_of
from spire_of_ash.content.monsters import MONSTERS
from spire_of_ash.content.pools import random_card_keys, roll_relic
from spire_of_ash.content.potions import POTIONS
from spire_of_ash.content.relics import RELIC_POOL, RELICS, STARTER_RELICS
from spire_of_ash.engine.card import Card
from spire_of_ash.engine.combatant import Player
from spire_of_ash.engine.dungeon import ACT_POOLS
from spire_of_ash.rng import Rng
from spire_of_ash.statuses import STATUS_LABELS, STATUSES, describe

HOOKS = {"on_pickup", "on_combat_start", "on_turn_start", "on_turn_end",
         "on_combat_end", "on_attack", "on_card_played", "on_exhaust",
         "on_kill", "draw_bonus"}


class TestRelicHooks(unittest.TestCase):
    def relic_combat(self, relic):
        cb = make_combat()
        cb.player.relics = [relic]
        return cb

    def test_vajra_grants_strength_at_combat_start(self):
        cb = self.relic_combat("vajra")
        cb.start_combat()
        self.assertEqual(cb.player.s("strength"), 1)

    def test_bag_of_marbles_debuffs_every_enemy(self):
        cb = make_combat(("cultist", "jaw_worm"))
        cb.player.relics = ["bag_of_marbles"]
        cb.start_combat()
        self.assertTrue(all(e.s("vulnerable") == 1 for e in cb.enemies))

    def test_anchor_only_blocks_on_the_first_turn(self):
        cb = self.relic_combat("anchor")
        cb.start_combat()
        cb.player_turn_start()
        self.assertGreaterEqual(cb.player.block, B.ANCHOR_BLOCK)
        cb.turn = 1
        cb.player_turn_start()
        self.assertEqual(cb.player.block, 0)

    def test_bag_of_prep_draws_extra_on_turn_one_only(self):
        cb = self.relic_combat("bag_of_prep")
        cb.start_combat()
        cb.player_turn_start()
        self.assertEqual(len(cb.hand), B.BASE_DRAW + B.BAG_OF_PREP_EXTRA)
        # put the hand back so the pile can reshuffle, or the next draw runs dry
        cb.discard.extend(cb.hand)
        cb.hand = []
        cb.turn = 1
        cb.player_turn_start()
        self.assertEqual(len(cb.hand), B.BASE_DRAW)

    def test_pen_nib_doubles_every_tenth_attack(self):
        cb = self.relic_combat("pen_nib")
        cb.start_combat()
        foe = cb.enemies[0]
        foe.max_hp = foe.hp = 10_000
        cb.attacks_total = 9        # the next attack is the 10th
        before = foe.hp
        cb.player_attack(foe, 10)
        self.assertEqual(before - foe.hp, 20)

    def test_pen_nib_leaves_other_attacks_alone(self):
        cb = self.relic_combat("pen_nib")
        cb.start_combat()
        foe = cb.enemies[0]
        foe.max_hp = foe.hp = 10_000
        cb.attacks_total = 0
        before = foe.hp
        cb.player_attack(foe, 10)
        self.assertEqual(before - foe.hp, 10)

    def test_kunai_grants_dexterity_every_third_attack(self):
        cb = self.relic_combat("kunai")
        cb.start_combat()
        foe = cb.enemies[0]
        foe.max_hp = foe.hp = 10_000
        for _ in range(3):
            cb.player_attack(foe, 1)
        self.assertEqual(cb.player.s("dexterity"), 1)

    def test_burning_blood_heals_after_an_elite_or_boss(self):
        for kind in ("elite", "boss"):
            cb = make_combat(kind=kind)
            cb.player.relics = ["burning_blood"]
            cb.player.hp = cb.player.max_hp - 20
            before = cb.player.hp
            cb.end_combat()
            self.assertEqual(cb.player.hp, before + B.BURNING_BLOOD_ELITE_HEAL, kind)

    def test_burning_blood_heals_less_after_trash(self):
        """A flat 6 after every fight made a trash node cost nothing at all."""
        cb = self.relic_combat("burning_blood")
        cb.player.hp = cb.player.max_hp - 20
        before = cb.player.hp
        cb.end_combat()
        self.assertEqual(cb.player.hp, before + B.BURNING_BLOOD_HEAL)
        self.assertLess(B.BURNING_BLOOD_HEAL, B.BURNING_BLOOD_ELITE_HEAL)

    def test_meat_on_bone_only_heals_below_half(self):
        cb = self.relic_combat("meat_on_bone")
        cb.player.hp = cb.player.max_hp - 1
        before = cb.player.hp
        cb.end_combat()
        self.assertEqual(cb.player.hp, before)

        cb.player.hp = cb.player.max_hp // 4
        before = cb.player.hp
        cb.end_combat()
        self.assertEqual(cb.player.hp, before + B.MEAT_ON_BONE_HEAL)

    def test_art_of_war_rewards_an_attackless_turn(self):
        cb = self.relic_combat("art_of_war")
        cb.start_combat()
        cb.player_turn_start()
        cb.attacked_this_turn = False
        cb.player_turn_end()
        self.assertEqual(cb.bonus_energy_next, 1)

    def test_art_of_war_stays_quiet_after_an_attack(self):
        cb = self.relic_combat("art_of_war")
        cb.start_combat()
        cb.player_turn_start()
        cb.attacked_this_turn = True
        cb.player_turn_end()
        self.assertEqual(cb.bonus_energy_next, 0)

    def test_strawberry_raises_max_hp_on_pickup(self):
        p = Player("sentinel")
        before = p.max_hp
        p.add_relic("strawberry")
        self.assertEqual(p.max_hp, before + B.STRAWBERRY_MAX_HP)
        self.assertEqual(p.hp, before + B.STRAWBERRY_MAX_HP)

    def test_happy_flower_gives_energy_every_third_turn(self):
        cb = self.relic_combat("happy_flower")
        cb.start_combat()
        cb.turn = 2                 # (turn + 1) % 3 == 0
        cb.player_turn_start()
        self.assertEqual(cb.energy, cb.player.max_energy + 1)

    def test_every_relic_hook_name_is_recognised(self):
        for key, spec in RELICS.items():
            for field in spec:
                if field in ("name", "desc"):
                    continue
                self.assertIn(field, HOOKS, f"{key} declares unknown hook {field!r}")

    def test_every_relic_can_be_picked_up_and_fires_cleanly(self):
        """A smoke test over the whole table, so a new relic can't crash a run."""
        for key in RELICS:
            cb = make_combat()
            cb.player.relics = []
            cb.player.add_relic(key)
            cb.start_combat()
            cb.player_turn_start()
            cb.player_attack(cb.enemies[0], 1)
            cb.player_turn_end()
            cb.end_combat()


class TestContentIntegrity(unittest.TestCase):
    def test_class_decks_and_pools_reference_real_cards(self):
        for cls, d in CLASSES.items():
            for key in d["deck"] + d["common"] + d["uncommon"] + d["rare"]:
                self.assertIn(key, CARDS, f"{cls} references missing card {key!r}")

    def test_class_relics_exist(self):
        for cls, d in CLASSES.items():
            self.assertIn(d["relic"], RELICS, f"{cls} has a missing relic")

    def test_default_class_exists(self):
        self.assertIn(DEFAULT_CLASS, CLASSES)

    def test_starter_relics_never_drop(self):
        self.assertTrue(STARTER_RELICS)
        self.assertFalse(set(RELIC_POOL) & STARTER_RELICS)

    def test_every_card_can_be_constructed(self):
        for key in CARDS:
            card = Card(key)
            self.assertTrue(card.name)
            self.assertTrue(card.desc)
            self.assertTrue(Card(key, upgraded=True).name.endswith("+"))

    def test_card_types_are_known(self):
        for key, d in CARDS.items():
            self.assertIn(d["type"],
                          ("ATTACK", "SKILL", "POWER", "CURSE", "STATUS"),
                          f"{key} has an odd type")

    def test_act_pools_reference_real_monsters(self):
        for act, pools in ACT_POOLS.items():
            for group in pools["weak"] + pools["strong"]:
                for key in group:
                    self.assertIn(key, MONSTERS, f"act {act} references {key!r}")
            for key in pools["elite"] + pools["boss"]:
                self.assertIn(key, MONSTERS, f"act {act} references {key!r}")

    def test_elites_and_bosses_are_flagged(self):
        for act, pools in ACT_POOLS.items():
            for key in pools["elite"]:
                self.assertTrue(MONSTERS[key].get("elite"), f"{key} is not elite")
            for key in pools["boss"]:
                self.assertTrue(MONSTERS[key].get("boss"), f"{key} is not a boss")

    def test_monster_moves_are_well_formed(self):
        for key, spec in MONSTERS.items():
            self.assertTrue(spec["moves"], f"{key} has no moves")
            self.assertIn("pick", spec, f"{key} has no move picker")
            lo, hi = spec["hp"]
            self.assertLessEqual(lo, hi, f"{key} has a backwards hp range")

    def test_potions_are_well_formed(self):
        for key, spec in POTIONS.items():
            self.assertTrue(spec["name"] and spec["desc"])
            self.assertTrue(callable(spec["fx"]), f"{key} has no effect")

    def test_events_are_well_formed(self):
        for ev in EVENTS:
            self.assertTrue(ev["title"] and ev["text"])
            self.assertTrue(ev["options"], f"{ev['title']} has no options")
            for label, fn in ev["options"]:
                self.assertTrue(label)
                self.assertTrue(callable(fn))

    def test_every_event_option_previews_its_effect(self):
        """A label is flavour; without a preview the player is guessing."""
        for ev in EVENTS:
            for label, fn in ev["options"]:
                self.assertTrue(preview_of(fn),
                                f"{ev['title']} / {label} has no preview")

    def test_statuses_used_by_cards_have_labels(self):
        """Anything shown to the player needs a label to render."""
        for key in ("strength", "dexterity", "vulnerable", "weak", "frail",
                    "poison", "thorns"):
            self.assertTrue(STATUS_LABELS.get(key))

    def test_every_shown_status_explains_itself(self):
        """A four-letter chip is meaningless without the tooltip behind it."""
        for key, (label, name, desc) in STATUSES.items():
            if not label:
                continue          # hidden bookkeeping, never rendered
            self.assertTrue(name, f"{key} has no name")
            self.assertTrue(desc, f"{key} has no description")
            self.assertEqual(describe(key), (name, desc))

    def test_random_card_keys_respects_the_class(self):
        rng = Rng(5)
        pool = set(CLASSES["ashwalker"]["common"] + CLASSES["ashwalker"]["uncommon"]
                   + CLASSES["ashwalker"]["rare"])
        keys = random_card_keys(rng, 3, cls="ashwalker")
        self.assertEqual(len(set(keys)), 3, "keys must be distinct")
        self.assertTrue(set(keys) <= pool)

    def test_roll_relic_avoids_owned_relics(self):
        rng = Rng(5)
        owned = list(RELIC_POOL[:-1])
        self.assertEqual(roll_relic(rng, owned), RELIC_POOL[-1])

    def test_roll_relic_falls_back_when_all_are_owned(self):
        rng = Rng(5)
        self.assertIn(roll_relic(rng, list(RELIC_POOL)), RELIC_POOL)


if __name__ == "__main__":
    unittest.main()


class TestNewRelicHooks(unittest.TestCase):
    """The hooks added once relics were data, not scattered conditionals."""

    def relic_combat(self, relic, enemies=("cultist",)):
        cb = make_combat(enemies)
        cb.player.relics = [relic]
        return cb

    def test_smoulder_stone_burns_every_enemy_each_turn(self):
        cb = self.relic_combat("smoulder_stone", ("cultist", "jaw_worm"))
        cb.start_combat()
        before = [e.hp for e in cb.enemies]
        cb.player_turn_start()
        self.assertTrue(all(e.hp == b - B.SMOULDER_DAMAGE
                            for e, b in zip(cb.enemies, before)))

    def test_grave_ash_fires_only_on_the_first_exhaust(self):
        cb = self.relic_combat("grave_ash")
        cb.start_combat()
        cb.exhaust_card(Card("strike"))
        self.assertEqual(cb.player.s("strength"), B.GRAVE_ASH_STRENGTH)
        cb.exhaust_card(Card("defend"))
        self.assertEqual(cb.player.s("strength"), B.GRAVE_ASH_STRENGTH)

    def test_bone_dice_draws_on_every_fourth_card(self):
        cb = self.relic_combat("bone_dice")
        cb.start_combat()
        cb.hand = []
        for _ in range(B.BONE_DICE_EVERY - 1):
            cb.on_card_played()
        self.assertEqual(len(cb.hand), 0)
        cb.on_card_played()
        self.assertEqual(len(cb.hand), 1)

    def test_oathkeeper_heals_on_a_kill(self):
        cb = self.relic_combat("oathkeeper")
        cb.start_combat()
        cb.player.hp = cb.player.max_hp - 20
        before = cb.player.hp
        cb.kill(cb.enemies[0])
        self.assertEqual(cb.player.hp, before + B.OATHKEEPER_HEAL)

    def test_hollow_lantern_trades_first_turn_energy_for_cards(self):
        cb = self.relic_combat("hollow_lantern")
        cb.start_combat()
        cb.player_turn_start()
        self.assertEqual(cb.energy, cb.player.max_energy - 1)
        self.assertEqual(len(cb.hand), B.BASE_DRAW + 1)

    def test_emberheart_grants_metallicize(self):
        cb = self.relic_combat("emberheart")
        cb.start_combat()
        self.assertEqual(cb.player.s("metallicize"), 3)


class TestEventFollowups(unittest.TestCase):
    def run_with_event(self, title):
        from spire_of_ash.engine.run import Run
        run = Run("sentinel", seed=1)
        idx = next(i for i, e in enumerate(EVENTS) if e["title"] == title)
        run.event = {"index": idx, "title": EVENTS[idx]["title"],
                     "text": EVENTS[idx]["text"],
                     "options": [l for l, _ in EVENTS[idx]["options"]],
                     "result": None, "then": None}
        run.screen = "event"
        return run

    def test_mirror_opens_a_duplicate_picker_and_grows_the_deck(self):
        run = self.run_with_event("THE ASHEN MIRROR")
        before_deck, before_max = len(run.player.deck), run.player.max_hp
        run.apply({"type": "event_choose", "idx": 0})
        self.assertEqual(run.event["then"], "duplicate")
        self.assertLess(run.player.max_hp, before_max)
        run.apply({"type": "event_done"})
        self.assertEqual(run.screen, "choose")
        run.apply({"type": "choose", "idx": 0})
        self.assertEqual(len(run.player.deck), before_deck + 1)

    def test_forge_upgrades_when_you_can_pay(self):
        run = self.run_with_event("THE COLD FORGE")
        run.player.gold = 500
        run.apply({"type": "event_choose", "idx": 0})
        self.assertEqual(run.event["then"], "upgrade")
        self.assertEqual(run.player.gold, 500 - 60)
        run.apply({"type": "event_done"})
        self.assertEqual(run.screen, "choose")
        run.apply({"type": "choose", "idx": 0})
        self.assertTrue(any(k.upgraded for k in run.player.deck))

    def test_forge_refuses_when_you_cannot_pay(self):
        run = self.run_with_event("THE COLD FORGE")
        run.player.gold = 0
        run.apply({"type": "event_choose", "idx": 0})
        self.assertIsNone(run.event["then"])
        run.apply({"type": "event_done"})
        self.assertEqual(run.screen, "map")

    def test_followup_is_skipped_when_no_card_qualifies(self):
        run = self.run_with_event("THE COLD FORGE")
        run.player.gold = 500
        for card in run.player.deck:
            card.upgrade()
        run.apply({"type": "event_choose", "idx": 0})
        run.apply({"type": "event_done"})
        self.assertEqual(run.screen, "map")


class TestSeeds(unittest.TestCase):
    def test_daily_seed_is_stable_for_a_date(self):
        import datetime
        from spire_of_ash.seeds import daily_seed
        day = datetime.date(2026, 7, 25)
        self.assertEqual(daily_seed(day), daily_seed(day))
        self.assertNotEqual(daily_seed(day), daily_seed(datetime.date(2026, 7, 26)))

    def test_daily_runs_match(self):
        from spire_of_ash.engine.run import Run
        from spire_of_ash.seeds import daily_seed
        a, b = Run(seed=1), Run(seed=2)
        a.apply({"type": "new_run", "cls": "sentinel", "daily": True})
        b.apply({"type": "new_run", "cls": "sentinel", "daily": True})
        self.assertEqual(a.state(), b.state())
        self.assertEqual(a.rng.seed, daily_seed())

    def test_explicit_seed_is_honoured(self):
        from spire_of_ash.engine.run import Run
        from spire_of_ash.engine.errors import InvalidAction
        run = Run(seed=1)
        run.apply({"type": "new_run", "cls": "sentinel", "seed": 12345})
        self.assertEqual(run.rng.seed, 12345)
        with self.assertRaises(InvalidAction):
            run.apply({"type": "new_run", "cls": "sentinel", "seed": "abc"})
