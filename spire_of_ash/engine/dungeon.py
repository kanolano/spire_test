"""Map generation and encounter selection.

A map is a plain `list[list[dict(type, edges)]]` — JSON-serialisable as-is, which
is why it can be handed straight to a browser and straight into a save file.
"""

from .. import balance as B
from .combatant import Enemy

NODE_TYPES = ("monster", "elite", "event", "rest", "shop", "treasure", "boss")


def generate_map(rng, floors_per_act=B.FLOORS_PER_ACT):
    """Build one act's map: a column of nodes per floor, linked by edges."""
    floors = []
    last = floors_per_act - 1
    for f in range(floors_per_act):
        if f == last:
            types = ["boss"]
        elif f == 0:
            types = ["monster"] * rng.randint(2, 3)
        elif f == B.TREASURE_FLOOR:
            types = ["treasure"] * rng.randint(2, 4)
        elif f == last - 1:
            types = ["rest"] * rng.randint(2, 3)
        else:
            types = [_roll_node(rng, f) for _ in range(rng.randint(2, 4))]
        floors.append([dict(type=t, edges=[]) for t in types])

    for f in range(floors_per_act - 1):
        _link(rng, floors[f], floors[f + 1])
    return floors


def _roll_node(rng, floor):
    r = rng.random()
    if floor >= 5 and r < B.NODE_ELITE:
        return "elite"
    if floor >= 5 and r < B.NODE_REST:
        return "rest"
    if r < B.NODE_EVENT:
        return "event"
    if r < B.NODE_SHOP:
        return "shop"
    return "monster"


def _link(rng, cur, nxt):
    """Connect one floor to the next, then make sure every node is reachable."""
    n, m = len(cur), len(nxt)
    base = [round(j * (m - 1) / (n - 1)) if n > 1 else (m - 1) // 2 for j in range(n)]
    for j, node in enumerate(cur):
        targets = {base[j]}
        hi = base[j + 1] if j + 1 < n else m - 1
        lo = base[j - 1] if j > 0 else 0
        if rng.random() < 0.5 and base[j] + 1 <= hi:
            targets.add(base[j] + 1)
        if rng.random() < 0.35 and base[j] - 1 >= lo:
            targets.add(base[j] - 1)
        node["edges"] = sorted(t for t in targets if 0 <= t < m)
    covered = {t for node in cur for t in node["edges"]}
    for t in range(m):
        if t not in covered:
            j = min(range(n), key=lambda x: abs(base[x] - t))
            cur[j]["edges"] = sorted(set(cur[j]["edges"]) | {t})


ACT_POOLS = {
    1: dict(
        weak=[["cultist"], ["jaw_worm"], ["louse", "louse"],
              ["small_slime", "small_slime"], ["mad_gremlin", "sneaky_gremlin"]],
        strong=[["jaw_worm"], ["cultist", "louse"], ["fungi", "fungi"],
                ["acid_slime"], ["spike_slime", "small_slime"],
                ["louse", "louse", "louse"],
                ["mad_gremlin", "fat_gremlin", "sneaky_gremlin", "shield_gremlin"],
                ["acid_slime", "spike_slime"]],
        elite=["gremlin_nob", "lagavulin"], boss=["guardian", "slime_boss"]),
    2: dict(
        weak=[["byrd"], ["fungi", "fungi"], ["jaw_worm", "louse"], ["sentry"]],
        strong=[["chosen"], ["mystic"], ["byrd", "byrd"], ["sentry", "sentry"],
                ["chosen", "cultist"], ["mystic", "byrd"], ["acid_slime", "spike_slime"],
                ["jaw_worm", "jaw_worm"]],
        elite=["taskmaster", "gremlin_nob"], boss=["hexaghost", "champ"]),
    3: dict(
        weak=[["chosen"], ["mystic"], ["sentry", "sentry"], ["byrd", "byrd"]],
        strong=[["chosen", "chosen"], ["sentry", "sentry", "sentry"],
                ["mystic", "chosen"], ["byrd", "byrd", "byrd"],
                ["acid_slime", "acid_slime"], ["chosen", "mystic"]],
        elite=["book_of_stabbing", "taskmaster"], boss=["champ", "hexaghost"]),
}


def make_encounter(rng, act, kind, floor):
    """Enemies plus a label for one combat node."""
    pool = ACT_POOLS[min(act, B.FINAL_ACT)]
    if kind == "boss":
        return [Enemy(rng.choice(pool["boss"]), act, rng)], "BOSS"
    if kind == "elite":
        return [Enemy(rng.choice(pool["elite"]), act, rng)], "ELITE"
    group = rng.choice(pool["weak"] if floor < 3 else pool["strong"])
    return [Enemy(k, act, rng) for k in group], "COMBAT"
