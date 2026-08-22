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
    on_card_played(combat)     — after each card resolves
    on_exhaust(combat, card)   — whenever a card is exhausted
    on_kill(combat, enemy)     — whenever an enemy dies
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
    # A flat 6 after *every* fight out-healed a whole trash encounter, so half
    # of all combats left the player better off than they started. Dropping it
    # entirely went too far the other way: this is the Sentinel's only starter
    # effect, and without it the class bled out in Act 1. Small always, real
    # after the fights that actually cost something.
    cb.heal(cb.player, B.BURNING_BLOOD_ELITE_HEAL
            if cb.kind in ("elite", "boss") else B.BURNING_BLOOD_HEAL)


def _meat_on_bone(cb):
    p = cb.player
    if p.hp < p.max_hp // 2:
        cb.heal(p, B.MEAT_ON_BONE_HEAL)


def _strawberry(player):
    player.max_hp += B.STRAWBERRY_MAX_HP
    player.hp += B.STRAWBERRY_MAX_HP


def _smoulder_stone(cb):
    for e in cb.living():
        cb.damage(e, B.SMOULDER_DAMAGE, ignore_block=True)


def _grave_ash(cb, card):
    if cb.exhausts_this_combat == 1:      # only the first exhaust of the combat
        cb.apply(cb.player, "strength", B.GRAVE_ASH_STRENGTH)
        cb.msg("Grave Ash drinks the cinders.")


def _bone_dice(cb):
    if cb.cards_played % B.BONE_DICE_EVERY == 0:
        cb.draw(1)


def _oathkeeper(cb, enemy):
    cb.heal(cb.player, B.OATHKEEPER_HEAL)


def _hollow_lantern(cb):
    """More cards every turn, but the first turn is a step behind."""
    if cb.turn == 0:
        cb.energy = max(0, cb.energy - 1)


RELICS = {
    "burning_blood": dict(
        name="Burning Blood", desc="Heal 3 HP after a combat, 10 after an elite or boss.",
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

    # ── added once relics became data; each of these is one entry, where the
    # old design would have needed edits in two classes and several methods ──
    "emberheart": dict(
        name="Emberheart", desc="At combat start, gain 3 Metallicize.",
        on_combat_start=_combat_start_apply("metallicize", 3)),
    "ashglass_vial": dict(
        name="Ashglass Vial", desc="At combat start, apply 1 Weak to ALL enemies.",
        on_combat_start=_combat_start_apply("weak", 1, to_enemies=True)),
    "smoulder_stone": dict(
        name="Smoulder Stone",
        desc="At the start of each turn, deal 1 damage to ALL enemies.",
        on_turn_start=_smoulder_stone),
    "grave_ash": dict(
        name="Grave Ash",
        desc="The first card you exhaust each combat grants 2 Strength.",
        on_exhaust=_grave_ash),
    "bone_dice": dict(
        name="Bone Dice", desc="Every 4th card you play, draw 1 card.",
        on_card_played=_bone_dice),
    "oathkeeper": dict(
        name="Oathkeeper", desc="Heal 3 HP whenever an enemy dies.",
        on_kill=_oathkeeper),
    "hollow_lantern": dict(
        name="Hollow Lantern",
        desc="Draw 1 extra card each turn, but start combat with 1 less Energy.",
        draw_bonus=lambda cb: 1,
        on_turn_start=_hollow_lantern),

    # ── the five later climbers; each is a starting relic, so none of them
    #    turns up as a drop ──
    "storm_cell": dict(
        name="Storm Cell", desc="At the start of each combat, gain 1 Coil.",
        on_combat_start=lambda cb: cb.channel("stormcoil", B.STORM_CELL_COILS)),
    "prayer_bead": dict(
        name="Prayer Bead", desc="At the start of each combat, gain 3 Mantra.",
        on_combat_start=lambda cb: cb.gain_mantra(B.PRAYER_BEAD_MANTRA)),
    "gravebell": dict(
        name="Gravebell",
        desc="At the start of each combat, gain 1 Soulfire.",
        on_combat_start=_combat_start_apply("soulfire", B.GRAVEBELL_SOULFIRE)),
    "cracked_alembic": dict(
        name="Cracked Alembic", desc="At the start of each combat, brew a random potion.",
        on_combat_start=lambda cb: cb.brew(quiet_when_full=True)),
    "hexing_thread": dict(
        name="Hexing Thread", desc="At the start of each combat, gain 1 Hexbloom.",
        on_combat_start=_combat_start_apply("hexbloom", B.HEXING_THREAD_HEXBLOOM)),
}

# Starting relics are handed out by class and never appear as drops.
from .classes import CLASSES  # noqa: E402  (must follow RELICS)

STARTER_RELICS = {d["relic"] for d in CLASSES.values()}
RELIC_POOL = [k for k in RELICS if k not in STARTER_RELICS]
