"""Playable classes.

Each class owns its starting HP, energy, deck, relic and its own three card
pools, and may set `potions` to carry a belt of its own size. Nothing else in
the game is class-aware, so adding a class is a data-only change.
"""

CLASSES = {
    "sentinel": dict(
        name="The Sentinel", hp=75, energy=3, relic="burning_blood",
        blurb="Ash-caked plate and a heavy blade. Strength, Block and brute arithmetic.",
        deck=["strike"] * 5 + ["defend"] * 4 + ["bash"],
        common=["cleave", "twin_strike", "pommel_strike", "iron_wave", "clothesline",
                "body_slam", "shrug_it_off", "flex", "true_grit", "bloodletting", "armaments",
                "ember_shield"],
        uncommon=["uppercut", "heavy_blade", "whirlwind", "seeing_red", "offering",
                  "second_wind", "inflame", "metallicize", "feel_no_pain", "rupture",
                  "disarm", "shockwave", "poison_stab", "battle_trance", "crushing_blow"],
        rare=["bludgeon", "reaper", "impervious", "demon_form", "barricade", "juggernaut",
              "limit_break", "unyielding"],
    ),
    "ashwalker": dict(
        name="The Ashwalker", hp=68, energy=3, relic="ash_phial",
        blurb="Cinder-smoke and a thin knife. Poison, Weak and a great many small cuts.",
        deck=["strike"] * 5 + ["defend"] * 4 + ["cinder_dart"],
        common=["quick_slash", "venom_dagger", "flechettes", "sneak_attack", "slice_and_dice",
                "dodge_roll", "cloak", "backflip", "acrobatics", "smoke_bomb", "toxic_vial",
                "caltrops"],
        uncommon=["deadly_poison", "blade_dance", "footwork", "crippling_cloud",
                  "well_laid_plans", "catalyst", "dagger_spray", "escape_plan", "bane",
                  "nightmare_toxin", "flying_knee", "vial_toss"],
        rare=["bouncing_flask", "venom_bloom", "after_image", "a_thousand_cuts", "envenom",
              "grand_finale", "shadowstep"],
    ),
    "stormbound": dict(
        name="The Stormbound", hp=70, energy=3, relic="storm_cell",
        blurb="A body wired for weather. Gather Coil and Frost, then let the storm "
              "off its leash at the end of the turn.",
        deck=["strike"] * 5 + ["defend"] * 4 + ["static_lash"],
        common=["charge_bolt", "rimeshard", "coil_up", "lightning_lance", "hailstone",
                "spark_shower", "overclock", "capacitor", "arc_weld", "cold_snap",
                "recharge", "hull_plating"],
        uncommon=["focus_lens", "thunderstrike", "blizzard", "overload", "chain_lightning",
                  "glacier", "reroute", "storm_engine", "sleet_volley", "conductor",
                  "metallicize", "seeing_red"],
        rare=["echo_form", "tempest_crown", "cataclysm", "rime_bastion", "feedback_loop",
              "singularity", "lightning_rod"],
    ),
    "penitent": dict(
        name="The Penitent", hp=72, energy=3, relic="prayer_bead",
        blurb="Bare hands and a vow. Step into Wrath to hit twice as hard and be hit "
              "twice as hard; step into Calm to buy the energy back.",
        deck=["strike"] * 4 + ["defend"] * 4 + ["ember_kata", "still_flame"],
        common=["crescendo", "tranquility", "empty_fist", "empty_body", "flurry_of_ash",
                "prostrate", "evaluate", "halt", "sash_whip", "cut_through_fate",
                "crush_joints", "third_eye"],
        uncommon=["wreath_of_flame", "battle_hymn", "fear_no_evil", "mental_fortress",
                  "rushdown", "wallop", "windmill_strike", "fasting", "inner_peace",
                  "sanctity", "worship", "pray"],
        rare=["blasphemy", "abiding_flame", "lesson_learned", "ragnarok", "spirit_shield",
              "judgment", "master_reality"],
    ),
    "gravewright": dict(
        name="The Gravewright", hp=68, energy=3, relic="gravebell",
        blurb="Thin, grey and patient. Every card you burn is fuel, and the exhaust "
              "pile is a resource rather than a graveyard.",
        deck=["strike"] * 5 + ["defend"] * 4 + ["grave_touch"],
        common=["pyre", "sever_ties", "ash_scatter", "grave_dust", "reclaim", "dead_weight",
                "soul_tap", "mourning_veil", "necrotic_slash", "hollow_call", "cairn_guard",
                "ember_shield"],
        uncommon=["ashen_embrace", "soulfire_rite", "corpse_harvest", "boneyard",
                  "grim_bargain", "exhume", "deathknell", "funeral_rites", "feel_no_pain",
                  "offering", "disarm", "metallicize"],
        rare=["soul_forge", "cremation", "lich_crown", "phylactery", "grave_tide",
              "wake_the_ash", "reaper"],
    ),
    "emberbrewer": dict(
        name="The Emberbrewer", hp=66, energy=3, relic="cracked_alembic", potions=5,
        blurb="A deeper belt and a lit burner. Brew potions mid-fight, then find the "
              "cards that make drinking them a spell in itself.",
        deck=["strike"] * 5 + ["defend"] * 4 + ["quick_brew"],
        common=["firebomb", "bitter_draught", "beaker_shield", "acid_flask", "emberglass",
                "decant", "distil", "spill", "tonic", "sample", "dodge_roll",
                "bloodletting"],
        uncommon=["volatile_mix", "elixir_ward", "alchemize", "fire_oil",
                  "unstable_compound", "panacea", "flash_powder", "siphon", "potion_belt",
                  "double_brew", "footwork", "escape_plan"],
        rare=["grand_elixir", "philosophers_stone", "firestorm", "potency",
              "alchemical_heart", "overdose", "elixir_of_ash"],
    ),
    "hexbinder": dict(
        name="The Hexbinder", hp=66, energy=3, relic="hexing_thread",
        blurb="Knows everything's true name and says them all out loud. Weak, "
              "Vulnerable and Frail are the whole win condition.",
        deck=["strike"] * 5 + ["defend"] * 4 + ["binding_word"],
        common=["hex_bolt", "curse_of_frailty", "wither", "warding_sigil", "unravel",
                "sap_will", "evil_eye", "bad_omen", "spite", "blight_touch", "chain_word",
                "smoke_bomb"],
        uncommon=["hexbloom", "long_grudge", "mass_hysteria", "feed_on_fear",
                  "wracking_pain", "voodoo_pin", "dread_aura", "sigil_ward", "malediction",
                  "borrowed_time", "disarm", "shockwave"],
        rare=["litany_of_names", "evil_within", "unmaking", "scapegoat", "grim_tally",
              "binding_circle", "witching_hour"],
    ),
}

DEFAULT_CLASS = "sentinel"
