"""Every tuning number in the game, in one place.

These used to be scattered as literals across the engine and duplicated again in
the web layer, so a balance change had to be made twice and the two copies
drifted. Nothing here should be repeated elsewhere.
"""

# ── combat ──
HAND_LIMIT = 10
BASE_DRAW = 5
BAG_OF_PREP_EXTRA = 2
VULNERABLE_MULT = 1.5
WEAK_MULT = 0.75
FRAIL_MULT = 0.75
COMBAT_LOG_LEN = 40

# ── enemies ──
ACT_HP_SCALING = 0.18          # +18% enemy HP per act beyond the first
ACT3_ENEMY_STRENGTH = 1

# ── player ──
STARTING_GOLD = 99
MAX_POTIONS = 3
STRAWBERRY_MAX_HP = 7

# ── relics ──
PEN_NIB_EVERY = 10
KUNAI_EVERY = 3
HAPPY_FLOWER_EVERY = 3
ANCHOR_BLOCK = 10
BURNING_BLOOD_HEAL = 3
BURNING_BLOOD_ELITE_HEAL = 10  # after an elite or boss — see _burning_blood
MEAT_ON_BONE_HEAL = 12
BLOOD_VIAL_HEAL = 2
BRONZE_SCALES_THORNS = 3
ASH_PHIAL_POISON = 2
SMOULDER_DAMAGE = 1
GRAVE_ASH_STRENGTH = 2
BONE_DICE_EVERY = 4
OATHKEEPER_HEAL = 3

# ── map ──
FLOORS_PER_ACT = 15
TREASURE_FLOOR = 8
REST_FLOOR = 13
MID_REST_FLOOR = 6             # a second guaranteed campfire, mid-act
# Chance a node links to the neighbour above/below its own column. At 0.5/0.35
# the average node had ~1.5 exits, so half of all steps offered no choice at
# all on a screen titled "Choose your path".
MAP_BRANCH_UP = 0.75
MAP_BRANCH_DOWN = 0.7
FINAL_ACT = 3
# Cumulative cutoffs used when rolling a node type. Monsters were 53% of every
# map, and a trash fight cost a median of 1 HP — half the game was a free click.
NODE_ELITE = 0.16
NODE_REST = 0.28
NODE_EVENT = 0.40
NODE_SHOP = 0.48

# ── rewards ──
GOLD_REWARD = {"monster": (10, 20), "elite": (25, 35), "boss": (80, 100)}
POTION_DROP_CHANCE = {"monster": 0.4, "other": 0.6}
CARD_RARITY_CHANCES = {"monster": (0.62, 0.31, 0.07), "other": (0.5, 0.38, 0.12)}
REWARD_CARD_COUNT = 3
REWARD_LOG_LINES = 3            # tail of the fight shown on the results screen

# ── campfire ──
REST_HEAL_FRACTION = 0.3
MIN_DECK_SIZE = 5              # a campfire purge will not thin past this

# ── shop ──
SHOP_CARD_PRICES = {"common": 50, "uncommon": 75, "rare": 130, "starter": 50}
SHOP_PRICE_JITTER = 8
SHOP_RELIC_PRICE = (140, 190)
SHOP_POTION_PRICE = (45, 65)
SHOP_REMOVAL_PRICE = 55
SHOP_CARD_COUNT = 5
SHOP_POTION_COUNT = 2

# ── treasure ──
TREASURE_GOLD = (25, 60)

# ── act transition ──
ACT_MAX_HP_BONUS = 8
ACT_HEAL = 20

# ── records ──
LEADERBOARD_SIZE = 10
