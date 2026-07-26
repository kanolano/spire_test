"""Playable classes.

Each class owns its starting HP, energy, deck, relic and its own three card
pools. Nothing else in the game is class-aware, so adding a class is a data-only
change.
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
}

DEFAULT_CLASS = "sentinel"
