"""Relic definitions.

Relic effects used to be hardcoded `if player.has("...")` branches scattered
across `Combat.start_combat`, `Combat.player_turn_start`, `Combat.player_attack`,
`Player.add_relic` and the post-combat reward path — five sites in two classes,
with the post-combat pair duplicated again in the web layer. Adding a relic meant
editing several unrelated methods.

Now each relic carries its own hooks and a new relic is one entry in this table.

Hooks (all optional):
    on_pickup(player)          — when the relic is acquired
    on_combat_start(combat)    — after statuses are cleared, before intents roll
    on_turn_start(combat)      — start of the player's turn, before drawing
    on_turn_end(combat)        — end of the player's turn
    on_combat_end(combat)      — after the last enemy dies
    on_attack(combat, damage)  — return a new damage value, or None to leave it
    draw_bonus(combat)         — extra cards to draw this turn
"""

from .. import balance as B


def _combat_start_apply(key, amount, to_enemies=False):
    def hook(cb):
        if to_enemies:
            for e in cb.enemies:
                cb.apply(e, key, amount)
        else:
            cb.apply(cb.player, key, amount)
    return hook


def _first_turn_block(cb):
    if cb.turn == 0:
        cb.gain_block(cb.player, B.ANCHOR_BLOCK)


def _first_turn_energy(cb):
    if cb.turn == 0:
        cb.energy += 1


def _happy_flower(cb):
    if (cb.turn + 1) % B.HAPPY_FLOWER_EVERY == 0:
        cb.energy += 1


def _pen_nib(cb, damage):
    if cb.attacks_total % B.PEN_NIB_EVERY == 0:
        cb.msg("Pen Nib doubles the blow!")
        return damage * 2
    return None


def _kunai(cb, damage):
    if cb.attacks_this_turn % B.KUNAI_EVERY == 0:
        cb.apply(cb.player, "dexterity", 1)
    return None


def _art_of_war(cb):
    if not cb.attacked_this_turn:
        cb.bonus_energy_next += 1


def _burning_blood(cb):
    cb.heal(cb.player, B.BURNING_BLOOD_HEAL)


def _meat_on_bone(cb):
    p = cb.player
    if p.hp < p.max_hp // 2:
        cb.heal(p, B.MEAT_ON_BONE_HEAL)


def _strawberry(player):
    player.max_hp += B.STRAWBERRY_MAX_HP
    player.hp += B.STRAWBERRY_MAX_HP


RELICS = {
    "burning_blood": dict(
        name="Burning Blood", desc="Heal 6 HP after each combat.",
        on_combat_end=_burning_blood),
    "bag_of_marbles": dict(
        name="Bag of Marbles", desc="At combat start, apply 1 Vulnerable to ALL enemies.",
        on_combat_start=_combat_start_apply("vulnerable", 1, to_enemies=True)),
    "anchor": dict(
        name="Anchor", desc="Gain 10 Block on the first turn of combat.",
        on_turn_start=_first_turn_block),
    "vajra": dict(
        name="Vajra", desc="Start each combat with 1 Strength.",
        on_combat_start=_combat_start_apply("strength", 1)),
    "oddly_smooth_stone": dict(
        name="Oddly Smooth Stone", desc="Start each combat with 1 Dexterity.",
        on_combat_start=_combat_start_apply("dexterity", 1)),
    "bronze_scales": dict(
        name="Bronze Scales", desc="Start each combat with 3 Thorns.",
        on_combat_start=_combat_start_apply("thorns", B.BRONZE_SCALES_THORNS)),
    "blood_vial": dict(
        name="Blood Vial", desc="At combat start, heal 2 HP.",
        on_combat_start=lambda cb: cb.heal(cb.player, B.BLOOD_VIAL_HEAL)),
    "lantern": dict(
        name="Lantern", desc="Gain 1 Energy on the first turn of combat.",
        on_turn_start=_first_turn_energy),
    "happy_flower": dict(
        name="Happy Flower", desc="Every 3rd turn, gain 1 Energy.",
        on_turn_start=_happy_flower),
    "pen_nib": dict(
        name="Pen Nib", desc="Every 10th Attack you play deals double damage.",
        on_attack=_pen_nib),
    "strawberry": dict(
        name="Strawberry", desc="Raise Max HP by 7.",
        on_pickup=_strawberry),
    "meat_on_bone": dict(
        name="Meat on the Bone",
        desc="If you end a combat below half HP, heal 12 HP.",
        on_combat_end=_meat_on_bone),
    "kunai": dict(
        name="Kunai", desc="Every 3rd Attack in a turn grants 1 Dexterity.",
        on_attack=_kunai),
    "bag_of_prep": dict(
        name="Bag of Preparation", desc="Draw 2 extra cards on turn 1.",
        draw_bonus=lambda cb: B.BAG_OF_PREP_EXTRA if cb.turn == 0 else 0),
    "art_of_war": dict(
        name="Art of War",
        desc="If you play no Attacks in a turn, gain 1 Energy next turn.",
        on_turn_end=_art_of_war),
    "ash_phial": dict(
        name="Ash Phial", desc="At combat start, apply 2 Poison to ALL enemies.",
        on_combat_start=_combat_start_apply("poison", B.ASH_PHIAL_POISON,
                                            to_enemies=True)),
}

# Starting relics are handed out by class and never appear as drops.
from .classes import CLASSES  # noqa: E402  (must follow RELICS)

STARTER_RELICS = {d["relic"] for d in CLASSES.values()}
RELIC_POOL = [k for k in RELICS if k not in STARTER_RELICS]
