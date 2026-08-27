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

    # A pair of these was landing 30+ in a turn *and* stacking Vulnerable, while
    # Drain compounded their Strength — the damage came down rather than the
    # debuffs, so the fight still plays as a nasty attrition puzzle.
    "chosen": dict(name="Chosen", hp=(50, 58), moves={
        "Hex": mv("debuff", fn=lambda cb, e: cb.add_card_to_pile(Card("regret"), True)),
        "Zap": mv("attack", 12),
        "Debilitate": mv("attack", 7, fn=_debuff("vulnerable", 2)),
        "Drain": mv("debuff", fn=lambda cb, e: (cb.apply(cb.player, "weak", 3),
                                                cb.apply(e, "strength", 2))),
    }, pick=lambda e: "Hex" if e.turn == 0 else weighted_pick(
        [("Zap", 30, 2), ("Debilitate", 40, 2), ("Drain", 30, 1)])(e)),

    "mystic": dict(name="Mystic", hp=(44, 50), moves={
        "Heal": mv("buff", fn=lambda cb, e: [cb.heal(x, 8) for x in cb.living()]),
        "Attack Debuff": mv("attack", 9, fn=_debuff("weak", 2)),
        "Buff": mv("buff", fn=lambda cb, e: [cb.apply(x, "strength", 2) for x in cb.living()]),
    }, pick=weighted_pick([("Heal", 30, 1), ("Attack Debuff", 40, 2), ("Buff", 30, 1)])),

    # Four commons whose job is variety: a pack that rewards sweeping damage, a
    # predictable blocker that rewards reading intents, a chip-damage nuisance
    # that clogs the deck, and a healer-of-itself that punishes slow removal.
    "ash_pup": dict(name="Ash Pup", hp=(13, 17), moves={
        "Nip": mv("attack", 5),
        "Snarl": mv("buff", fn=_grow(2)),
    }, pick=weighted_pick([("Nip", 70, 3), ("Snarl", 30, 1)])),

    "slag_golem": dict(name="Slag Golem", hp=(36, 42), moves={
        "Harden": mv("block", fn=_block(12)),
        "Smash": mv("attack", 13),
    }, pick=cycle_pick(["Harden", "Smash"])),

    "cinder_moth": dict(name="Cinder Moth", hp=(21, 26), moves={
        "Scald": mv("attack", 5, fn=_add_cards("burn", 1)),
        "Dust": mv("debuff", fn=_debuff("weak", 2)),
        "Flit": mv("block", fn=_block(6)),
    }, pick=weighted_pick([("Scald", 45, 2), ("Dust", 30, 1), ("Flit", 25, 2)])),

    "bone_picker": dict(name="Bone Picker", hp=(30, 36), moves={
        "Rend": mv("attack", 4, hits=3),
        "Carrion Feast": mv("buff", fn=lambda cb, e: (cb.heal(e, 8),
                                                      cb.apply(e, "strength", 1))),
    }, pick=weighted_pick([("Rend", 65, 2), ("Carrion Feast", 35, 1)])),

    # ── expansion commons ──
    # A darting chip-attacker (act 1), an armoured turtle that rewards reading
    # its cycle (act 1/2), a heavy that grows Thorns as it defends (act 2), and a
    # self-healing revenant that punishes a slow clock (act 3).
    "ember_wisp": dict(name="Ember Wisp", hp=(12, 16), moves={
        "Singe": mv("attack", 4, fn=_debuff("weak", 1)),
        "Flicker": mv("block", fn=_block(5)),
        "Flare": mv("attack", 7),
    }, pick=weighted_pick([("Singe", 45, 2), ("Flare", 35, 2), ("Flicker", 20, 2)])),

    "rust_crawler": dict(name="Rust Crawler", hp=(34, 40), moves={
        "Plate Up": mv("block", fn=_block(10)),
        "Gore": mv("attack", 11),
        "Corrode": mv("attack", 6, fn=_add_cards("wound", 1)),
    }, pick=cycle_pick(["Plate Up", "Gore", "Corrode"])),

    "molten_sentinel": dict(name="Molten Sentinel", hp=(40, 46), moves={
        "Forge Guard": mv("block", fn=lambda cb, e: (cb.gain_block(e, 10),
                                                     cb.apply(e, "thorns", 2))),
        "Overhead Swing": mv("attack", 14),
        "Slag Spit": mv("attack", 6, fn=_add_cards("burn", 1)),
    }, pick=weighted_pick([("Overhead Swing", 40, 2), ("Slag Spit", 30, 2),
                           ("Forge Guard", 30, 2)])),

    "cinder_revenant": dict(name="Cinder Revenant", hp=(48, 54), moves={
        "Rake": mv("attack", 10, fn=_debuff("vulnerable", 1)),
        "Feast on Ash": mv("buff", fn=lambda cb, e: (cb.heal(e, 10),
                                                     cb.apply(e, "strength", 2))),
        "Cinder Lash": mv("attack", 7, hits=2),
    }, pick=lambda e: "Feast on Ash" if e.turn == 0 else weighted_pick(
        [("Rake", 40, 2), ("Cinder Lash", 40, 2), ("Feast on Ash", 20, 1)])(e)),

    # ── expansion commons, wave 2 ──
    # A frail swarm-mite that clogs the deck (act 1), a spitter that stacks
    # Poison and Frail (act 1/2), a shrieking flyer that softens you with Weak
    # then dives (act 2), and a phase-shifting wraith that hides behind Block on
    # a fixed cycle (act 3).
    "ash_mite": dict(name="Ash Mite", hp=(8, 12), moves={
        "Gnaw": mv("attack", 3, fn=_add_cards("wound", 1)),
        "Skitter": mv("attack", 5),
    }, pick=weighted_pick([("Gnaw", 45, 1), ("Skitter", 55, 3)])),

    "bile_spitter": dict(name="Bile Spitter", hp=(30, 36), moves={
        "Spit": mv("attack", 6, fn=_debuff("frail", 1)),
        "Corrode": mv("attack", 4, fn=lambda cb, e: cb.apply(cb.player, "vulnerable", 1)),
        "Fester": mv("buff", fn=_block(6)),
    }, pick=weighted_pick([("Spit", 45, 2), ("Corrode", 35, 2), ("Fester", 20, 2)])),

    "shriek_bat": dict(name="Shriek Bat", hp=(26, 32), moves={
        "Screech": mv("debuff", fn=_debuff("weak", 2)),
        "Dive": mv("attack", 13),
        "Wingbeat": mv("attack", 3, hits=3),
    }, pick=lambda e: "Screech" if e.turn == 0 else weighted_pick(
        [("Dive", 45, 2), ("Wingbeat", 40, 2), ("Screech", 15, 1)])(e)),

    "grave_wraith": dict(name="Grave Wraith", hp=(52, 60), moves={
        "Phase Guard": mv("block", fn=lambda cb, e: (cb.gain_block(e, 14),
                                                     cb.apply(e, "strength", 1))),
        "Soul Rake": mv("attack", 12, fn=_debuff("frail", 2)),
        "Wail": mv("attack", 8, fn=_add_cards("wound", 1)),
    }, pick=cycle_pick(["Phase Guard", "Soul Rake", "Wail"])),

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

    # ── expansion elites ──
    # An act-2 forge-warden that ramps Strength behind a wall of Thorns, and an
    # act-3 colossus that stacks Metallicize and grinds you with multi-hits.
    "forge_warden": dict(name="Forge Warden", hp=(112, 120), elite=True, moves={
        "Bellows": mv("buff", fn=lambda cb, e: (cb.apply(e, "strength", 3),
                                                cb.gain_block(e, 8))),
        "Molten Cleave": mv("attack", 16, fn=_add_cards("burn", 1)),
        "Ember Ward": mv("block", fn=lambda cb, e: (cb.gain_block(e, 12),
                                                    cb.apply(e, "thorns", 3))),
    }, pick=lambda e: "Bellows" if e.turn == 0 else weighted_pick(
        [("Molten Cleave", 50, 2), ("Ember Ward", 50, 2)])(e)),

    "ashbound_colossus": dict(name="Ashbound Colossus", hp=(160, 172), elite=True, moves={
        "Stone Fist": mv("attack", 10, hits=2),
        "Fortify": mv("block", fn=lambda cb, e: (cb.gain_block(e, 16),
                                                 cb.apply(e, "metallicize", 4))),
        "Crushing Heel": mv("attack", 20, fn=_debuff("frail", 2)),
    }, pick=cycle_pick(["Stone Fist", "Fortify", "Crushing Heel"])),

    "emberfiend": dict(name="Emberfiend", hp=(120, 130), elite=True, moves={
        "Conflagrate": mv("attack", 12, fn=_add_cards("burn", 2, to_draw=True)),
        "Scorching Grasp": mv("attack", 9, fn=_debuff("weak", 2)),
        "Kindle": mv("buff", fn=lambda cb, e: (cb.apply(e, "strength", 2),
                                               cb.apply(e, "ritual", 2))),
    }, pick=lambda e: "Kindle" if e.turn == 0 else weighted_pick(
        [("Conflagrate", 45, 2), ("Scorching Grasp", 55, 2)])(e)),

    # ── bosses ──
    # Act 1 was a wall, and the reason was spike damage rather than length: one
    # unblocked Fierce Bash was 43% of a Sentinel's max HP. The big hits came
    # down and some of the HP went back, so the fight is still long enough to
    # need a plan without being decided by a single unlucky turn.
    "guardian": dict(name="The Guardian", hp=(200, 200), boss=True, moves={
        "Charging Up": mv("block", fn=_block(9)),
        "Fierce Bash": mv("attack", 22),
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

    # Slam landed every third turn for half a Sentinel's max HP.
    "slime_boss": dict(name="Slime Boss", hp=(155, 155), boss=True, moves={
        "Goop Spray": mv("debuff", fn=_add_cards("slimed", 3)),
        "Preparing": mv("block", fn=_block(15)),
        "Slam": mv("attack", 26),
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

    # A second act-3 finale, so the top of the Spire is not always the same
    # fight. Where the Sovereign seals your draw and burns, the Warmother grinds:
    # she armours up, spawns pressure with heavy multi-hits, and heals off her
    # own rage — a race against a wall that hits back.
    "cinder_warmother": dict(name="The Cinder Warmother", hp=(330, 330), boss=True, moves={
        "Molten Bulwark": mv("block", fn=lambda cb, e: (cb.gain_block(e, 24),
                                                        cb.apply(e, "thorns", 4))),
        "Rain of Ash": mv("attack", 7, hits=4),
        "Maternal Fury": mv("buff", fn=lambda cb, e: (cb.apply(e, "strength", 5),
                                                      cb.heal(e, 24))),
        "Ashen Maul": mv("attack", 22, fn=_debuff("frail", 2)),
        "Ember Wave": mv("attack", 10, fn=_add_cards("burn", 2, to_draw=True)),
    }, pick=cycle_pick(["Molten Bulwark", "Rain of Ash", "Maternal Fury",
                        "Ashen Maul", "Ember Wave", "Rain of Ash"])),
}
