"""Enemy definitions.

`hp` is a (lo, hi) range rolled at construction. `moves` maps a move name to an
`mv(...)` dict; `pick(enemy)` chooses the next move and may consult `enemy.turn`
and `enemy.history`. `on_death(combat, enemy)` is optional.

Move selection draws from `enemy.rng` — the run's own generator — so encounters
are reproducible from a seed.
"""

from ..engine.card import Card


def mv(kind, dmg=0, hits=1, fn=None, note=""):
    return dict(kind=kind, dmg=dmg, hits=hits, fn=fn, note=note)


def _grow(n):
    return lambda cb, e: cb.apply(e, "strength", n)


def _block(n):
    return lambda cb, e: cb.gain_block(e, n)


def _debuff(key, n):
    return lambda cb, e: cb.apply(cb.player, key, n)


def _add_cards(key, n, to_draw=False):
    def f(cb, e):
        for _ in range(n):
            cb.add_card_to_pile(Card(key), to_draw)
    return f


def cycle_pick(order):
    """Enemy repeats a fixed sequence of moves."""
    return lambda e: order[e.turn % len(order)]


def weighted_pick(options):
    """options: list of (move, weight, max_repeat)."""
    def f(e):
        pool = []
        for name, wt, rep in options:
            if rep and len(e.history) >= rep and all(h == name for h in e.history[-rep:]):
                continue
            pool += [name] * wt
        return e.rng.choice(pool) if pool else options[0][0]
    return f


MONSTERS = {
    "jaw_worm": dict(name="Jaw Worm", hp=(40, 46), moves={
        "Chomp": mv("attack", 11),
        "Thrash": mv("attack", 7, fn=_block(5)),
        "Bellow": mv("buff", fn=lambda cb, e: (cb.apply(e, "strength", 3), cb.gain_block(e, 6))),
    }, pick=lambda e: "Chomp" if e.turn == 0 else weighted_pick(
        [("Bellow", 45, 2), ("Thrash", 30, 3), ("Chomp", 25, 2)])(e)),

    "cultist": dict(name="Cultist", hp=(48, 54), moves={
        "Incantation": mv("buff", fn=lambda cb, e: cb.apply(e, "ritual", 3)),
        "Dark Strike": mv("attack", 6),
    }, pick=lambda e: "Incantation" if e.turn == 0 else "Dark Strike"),

    "louse": dict(name="Red Louse", hp=(11, 16), moves={
        "Bite": mv("attack", 6),
        "Grow": mv("buff", fn=_grow(3)),
    }, pick=weighted_pick([("Bite", 75, 3), ("Grow", 25, 1)])),

    "fungi": dict(name="Fungi Beast", hp=(22, 28), moves={
        "Bite": mv("attack", 6),
        "Grow": mv("buff", fn=_grow(4)),
    }, pick=weighted_pick([("Bite", 60, 2), ("Grow", 40, 1)]),
        on_death=lambda cb, e: cb.apply(cb.player, "vulnerable", 2)),

    "acid_slime": dict(name="Acid Slime", hp=(28, 34), moves={
        "Corrosive Spit": mv("attack", 7, fn=_add_cards("slimed", 1)),
        "Tackle": mv("attack", 10),
        "Lick": mv("debuff", fn=_debuff("weak", 1)),
    }, pick=weighted_pick([("Corrosive Spit", 40, 2), ("Tackle", 35, 2), ("Lick", 25, 1)])),

    "spike_slime": dict(name="Spike Slime", hp=(26, 32), moves={
        "Flame Tackle": mv("attack", 8, fn=_add_cards("slimed", 1)),
        "Frail Lick": mv("debuff", fn=_debuff("frail", 2)),
    }, pick=weighted_pick([("Flame Tackle", 70, 2), ("Frail Lick", 30, 1)])),

    "small_slime": dict(name="Slime Spawn", hp=(9, 13), moves={
        "Tackle": mv("attack", 5),
        "Lick": mv("debuff", fn=_debuff("frail", 1)),
    }, pick=weighted_pick([("Tackle", 80, 3), ("Lick", 20, 1)])),

    "mad_gremlin": dict(name="Mad Gremlin", hp=(18, 22), moves={
        "Scratch": mv("attack", 5),
        "Angry": mv("buff", fn=_grow(1)),
    }, pick=weighted_pick([("Scratch", 80, 4), ("Angry", 20, 1)])),

    "sneaky_gremlin": dict(name="Sneaky Gremlin", hp=(10, 14), moves={
        "Puncture": mv("attack", 9),
    }, pick=lambda e: "Puncture"),

    "fat_gremlin": dict(name="Fat Gremlin", hp=(13, 17), moves={
        "Smash": mv("attack", 5, fn=_debuff("weak", 1)),
    }, pick=lambda e: "Smash"),

    "shield_gremlin": dict(name="Shield Gremlin", hp=(12, 15), moves={
        "Protect": mv("block", fn=lambda cb, e: [cb.gain_block(x, 7)
                                                 for x in cb.living() if x is not e]),
        "Bash": mv("attack", 6),
    }, pick=lambda e: "Protect" if any(x.alive and x is not e for x in e.allies) else "Bash"),

    "sentry": dict(name="Sentry", hp=(36, 40), moves={
        "Beam": mv("attack", 9),
        "Bolt": mv("debuff", fn=_add_cards("wound", 2, to_draw=True)),
    }, pick=cycle_pick(["Bolt", "Beam"])),

    "byrd": dict(name="Byrd", hp=(24, 30), moves={
        "Peck": mv("attack", 2, hits=5),
        "Swoop": mv("attack", 12),
        "Caw": mv("buff", fn=_grow(2)),
    }, pick=weighted_pick([("Peck", 50, 2), ("Swoop", 30, 2), ("Caw", 20, 1)])),

    "chosen": dict(name="Chosen", hp=(50, 58), moves={
        "Hex": mv("debuff", fn=lambda cb, e: cb.add_card_to_pile(Card("regret"), True)),
        "Zap": mv("attack", 18),
        "Debilitate": mv("attack", 10, fn=_debuff("vulnerable", 2)),
        "Drain": mv("debuff", fn=lambda cb, e: (cb.apply(cb.player, "weak", 3),
                                                cb.apply(e, "strength", 3))),
    }, pick=lambda e: "Hex" if e.turn == 0 else weighted_pick(
        [("Zap", 30, 2), ("Debilitate", 40, 2), ("Drain", 30, 1)])(e)),

    "mystic": dict(name="Mystic", hp=(44, 50), moves={
        "Heal": mv("buff", fn=lambda cb, e: [cb.heal(x, 8) for x in cb.living()]),
        "Attack Debuff": mv("attack", 9, fn=_debuff("weak", 2)),
        "Buff": mv("buff", fn=lambda cb, e: [cb.apply(x, "strength", 2) for x in cb.living()]),
    }, pick=weighted_pick([("Heal", 30, 1), ("Attack Debuff", 40, 2), ("Buff", 30, 1)])),

    # ── elites ──
    "gremlin_nob": dict(name="Gremlin Nob", hp=(82, 86), elite=True, moves={
        "Bellow": mv("buff", fn=_grow(3)),
        "Skull Bash": mv("attack", 8, fn=_debuff("vulnerable", 2)),
        "Rush": mv("attack", 16),
    }, pick=lambda e: "Bellow" if e.turn == 0 else weighted_pick(
        [("Rush", 66, 2), ("Skull Bash", 34, 1)])(e)),

    "lagavulin": dict(name="Lagavulin", hp=(105, 112), elite=True, moves={
        "Sleep": mv("block", fn=lambda cb, e: cb.gain_block(e, 8), note="dormant"),
        "Attack": mv("attack", 18),
        "Siphon Soul": mv("debuff", fn=lambda cb, e: (cb.apply(cb.player, "strength", -1),
                                                      cb.apply(cb.player, "dexterity", -1))),
    }, pick=lambda e: "Sleep" if e.turn < 3 else (
        "Siphon Soul" if (e.turn - 3) % 3 == 2 else "Attack")),

    "book_of_stabbing": dict(name="Book of Stabbing", hp=(120, 130), elite=True, moves={
        "Multi-Stab": mv("attack", 6, hits=3, fn=_grow(1)),
        "Single Stab": mv("attack", 21),
    }, pick=weighted_pick([("Multi-Stab", 70, 2), ("Single Stab", 30, 2)])),

    "taskmaster": dict(name="Taskmaster", hp=(90, 98), elite=True, moves={
        "Scouring Wave": mv("attack", 9, fn=_add_cards("wound", 1)),
        "Whip": mv("attack", 14, fn=_debuff("weak", 2)),
        "Rally": mv("buff", fn=lambda cb, e: (cb.apply(e, "strength", 2), cb.gain_block(e, 12))),
    }, pick=weighted_pick([("Scouring Wave", 35, 2), ("Whip", 40, 2), ("Rally", 25, 1)])),

    # ── bosses ──
    # 240 HP against a floor-15 act-1 deck was ~13 turns of chip damage while
    # being hit for 32; almost nobody got through it.
    "guardian": dict(name="The Guardian", hp=(180, 180), boss=True, moves={
        "Charging Up": mv("block", fn=_block(9)),
        "Fierce Bash": mv("attack", 32),
        "Vent Steam": mv("debuff", fn=lambda cb, e: (cb.apply(cb.player, "vulnerable", 2),
                                                     cb.apply(cb.player, "weak", 2))),
        "Whirlwind": mv("attack", 5, hits=4),
        "Twin Slam": mv("attack", 8, hits=2, fn=_grow(2)),
    }, pick=cycle_pick(["Charging Up", "Fierce Bash", "Vent Steam", "Whirlwind", "Twin Slam"])),

    "hexaghost": dict(name="Hexaghost", hp=(250, 250), boss=True, moves={
        "Activate": mv("buff", fn=_block(12)),
        "Divider": mv("attack", 6, hits=6),
        "Sear": mv("attack", 6, fn=_add_cards("burn", 1)),
        "Tackle": mv("attack", 6, hits=2),
        "Inferno": mv("attack", 3, hits=6, fn=_add_cards("burn", 3, to_draw=True)),
    }, pick=lambda e: "Activate" if e.turn == 0 else (
        "Divider" if e.turn == 1 else
        ["Sear", "Tackle", "Sear", "Inferno", "Tackle", "Sear"][(e.turn - 2) % 6])),

    "slime_boss": dict(name="Slime Boss", hp=(140, 140), boss=True, moves={
        "Goop Spray": mv("debuff", fn=_add_cards("slimed", 3)),
        "Preparing": mv("block", fn=_block(15)),
        "Slam": mv("attack", 38),
    }, pick=cycle_pick(["Goop Spray", "Preparing", "Slam"])),

    "champ": dict(name="The Champ", hp=(300, 300), boss=True, moves={
        "Defensive Stance": mv("block", fn=lambda cb, e: (cb.gain_block(e, 18),
                                                          cb.apply(e, "metallicize", 4))),
        "Heavy Slash": mv("attack", 18),
        "Face Slap": mv("attack", 14, fn=lambda cb, e: (cb.apply(cb.player, "frail", 2),
                                                        cb.apply(cb.player, "vulnerable", 2))),
        "Execute": mv("attack", 12, hits=2),
        "Anger": mv("buff", fn=lambda cb, e: (cb.apply(e, "strength", 6), cb.heal(e, 20))),
    }, pick=cycle_pick(["Face Slap", "Heavy Slash", "Defensive Stance", "Execute", "Anger",
                        "Heavy Slash", "Execute"])),

    "ash_warden": dict(name="Ash Warden", hp=(140, 150), elite=True, moves={
        "Cinder Guard": mv("block", fn=lambda cb, e: (cb.gain_block(e, 14),
                                                      cb.apply(e, "thorns", 3))),
        "Halberd": mv("attack", 15, fn=_debuff("frail", 2)),
        "Smother": mv("attack", 7, hits=2, fn=_add_cards("burn", 1)),
    }, pick=weighted_pick([("Halberd", 45, 2), ("Smother", 30, 2),
                           ("Cinder Guard", 25, 1)])),

    # The act-3 finale. It opens by sealing your draw, so the fight is about the
    # hand you are already holding.
    "ashen_sovereign": dict(name="The Ashen Sovereign", hp=(340, 340), boss=True, moves={
        "Sealing Gaze": mv("debuff", fn=lambda cb, e: (cb.lock_draw(),
                                                       cb.apply(cb.player, "weak", 2))),
        "Crown of Cinders": mv("buff", fn=lambda cb, e: (cb.apply(e, "strength", 4),
                                                         cb.gain_block(e, 20))),
        "Sovereign's Reach": mv("attack", 13, hits=2),
        "Immolate": mv("attack", 26, fn=_add_cards("burn", 2)),
        "Ashfall": mv("attack", 9, hits=3, fn=_debuff("vulnerable", 2)),
    }, pick=cycle_pick(["Sealing Gaze", "Sovereign's Reach", "Crown of Cinders",
                        "Ashfall", "Sovereign's Reach", "Immolate"])),
}
