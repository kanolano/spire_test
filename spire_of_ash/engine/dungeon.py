"""Map generation and encounter selection.

A map is a plain `list[list[dict(type, edges)]]` — JSON-serialisable as-is, which
is why it can be handed straight to a browser and straight into a save file.
"""

from .. import balance as B
from .combatant import Enemy

NODE_TYPES = ("monster", "elite", "event", "rest", "shop", "treasure", "boss")


def generate_map(rng, act=1):
    """Build one act's map from its profile.

    A profile (see balance.ACT_PROFILES) decides the act's height, where its
    guaranteed treasure and campfire floors sit, how wide each floor may be, and
    how the per-node roll leans. Every act shares the invariants the run and the
    client rely on: floor 0 is combat, the top floor is a lone boss, and every
    node on a floor is reachable from the one below.
    """
    prof = B.act_profile(act)
    floors_per_act = prof["floors"]
    lo_w, hi_w = prof["width"]
    treasure_floor = prof["treasure_floor"]
    rest_floors = set(prof["rest_floors"])
    floors = []
    last = floors_per_act - 1
    for f in range(floors_per_act):
        if f == last:
            types = ["boss"]
        elif f == 0:
            types = ["monster"] * rng.randint(lo_w, min(lo_w + 1, hi_w))
        elif f == treasure_floor:
            types = ["treasure"] * rng.randint(lo_w, hi_w)
        elif f == last - 1 or f in rest_floors:
            types = ["rest"] * rng.randint(lo_w, min(lo_w + 1, hi_w))
        else:
            types = [_roll_node(rng, f, prof) for _ in range(rng.randint(lo_w, hi_w))]
        floors.append([dict(type=t, edges=[]) for t in types])

    for f in range(floors_per_act - 1):
        _link(rng, floors[f], floors[f + 1])
    return floors


def _roll_node(rng, floor, prof):
    n = prof["node"]
    r = rng.random()
    if floor >= prof["elite_from"] and r < n["elite"]:
        return "elite"
    if floor >= prof["elite_from"] and r < n["rest"]:
        return "rest"
    if r < n["event"]:
        return "event"
    if r < n["shop"]:
        return "shop"
    return "monster"


def _link(rng, cur, nxt):
    """Connect one floor to the next, then make sure every node is reachable."""
    n, m = len(cur), len(nxt)
    base = [round(j * (m - 1) / (n - 1)) if n > 1 else (m - 1) // 2 for j in range(n)]
    for j, node in enumerate(cur):
        targets = {base[j]}
        # A branch used to be clamped to the neighbouring columns' own base, to
        # stop edges crossing. Wherever a floor narrowed, that collapsed several
        # columns onto the same base and forced a single exit — the single
        # biggest source of choiceless steps. Branches are now bounded only by
        # the floor itself; edges may cross, which the map draws legibly.
        if rng.random() < B.MAP_BRANCH_UP:
            targets.add(base[j] + 1)
        if rng.random() < B.MAP_BRANCH_DOWN:
            targets.add(base[j] - 1)
        node["edges"] = sorted(t for t in targets if 0 <= t < m)
    covered = {t for node in cur for t in node["edges"]}
    for t in range(m):
        if t not in covered:
            j = min(range(n), key=lambda x: abs(base[x] - t))
            cur[j]["edges"] = sorted(set(cur[j]["edges"]) | {t})


# An act used to draw from 5 weak and 8 strong groups, so a climb met the same
# handful of fights over and over.
ACT_POOLS = {
    1: dict(
        weak=[["cultist"], ["jaw_worm"], ["louse", "louse"],
              ["small_slime", "small_slime"], ["mad_gremlin", "sneaky_gremlin"],
              ["ash_pup", "ash_pup"], ["cinder_moth"], ["louse", "small_slime"],
              ["ash_pup", "louse"], ["ember_wisp", "ember_wisp"], ["rust_crawler"],
              ["ash_mite", "ash_mite", "ash_mite"], ["ash_mite", "ember_wisp"]],
        strong=[["jaw_worm"], ["cultist", "louse"], ["fungi", "fungi"],
                ["acid_slime"], ["spike_slime", "small_slime"],
                ["louse", "louse", "louse"],
                ["mad_gremlin", "fat_gremlin", "sneaky_gremlin", "shield_gremlin"],
                ["acid_slime", "spike_slime"],
                ["ash_pup", "ash_pup", "ash_pup"], ["slag_golem"],
                ["cinder_moth", "ash_pup"], ["fungi", "louse", "louse"],
                ["cinder_moth", "cinder_moth"], ["slag_golem", "ash_pup"],
                ["rust_crawler", "ember_wisp"], ["ember_wisp", "ember_wisp", "ember_wisp"],
                ["bile_spitter", "ash_mite"], ["rust_crawler", "ash_mite", "ash_mite"]],
        elite=["gremlin_nob", "lagavulin"], boss=["guardian", "slime_boss"]),
    2: dict(
        weak=[["byrd"], ["fungi", "fungi"], ["jaw_worm", "louse"], ["sentry"],
              ["slag_golem"], ["bone_picker"], ["cinder_moth", "cinder_moth"],
              ["molten_sentinel"], ["shriek_bat"], ["bile_spitter", "shriek_bat"]],
        strong=[["chosen"], ["mystic"], ["byrd", "byrd"], ["sentry", "sentry"],
                ["chosen", "cultist"], ["mystic", "byrd"], ["acid_slime", "spike_slime"],
                ["jaw_worm", "jaw_worm"],
                ["bone_picker", "byrd"], ["slag_golem", "cinder_moth"],
                ["sentry", "byrd"], ["mystic", "ash_pup", "ash_pup"],
                ["bone_picker", "bone_picker"], ["molten_sentinel", "cinder_moth"],
                ["molten_sentinel", "slag_golem"], ["shriek_bat", "shriek_bat"],
                ["bile_spitter", "molten_sentinel"]],
        elite=["taskmaster", "gremlin_nob", "forge_warden", "emberfiend"],
        boss=["hexaghost", "champ"]),
    3: dict(
        weak=[["chosen"], ["mystic"], ["sentry", "sentry"], ["byrd", "byrd"],
              ["bone_picker", "bone_picker"], ["slag_golem", "slag_golem"],
              ["cinder_revenant"], ["grave_wraith"]],
        strong=[["chosen", "chosen"], ["sentry", "sentry", "sentry"],
                ["mystic", "chosen"], ["byrd", "byrd", "byrd"],
                ["acid_slime", "acid_slime"], ["chosen", "mystic"],
                ["bone_picker", "chosen"], ["slag_golem", "sentry", "sentry"],
                ["byrd", "byrd", "cinder_moth"], ["bone_picker", "mystic"],
                ["cinder_revenant", "cinder_moth"], ["cinder_revenant", "molten_sentinel"],
                ["grave_wraith", "shriek_bat"], ["grave_wraith", "cinder_revenant"]],
        elite=["book_of_stabbing", "taskmaster", "ash_warden", "ashbound_colossus"],
        boss=["ashen_sovereign", "cinder_warmother"]),
}


def make_encounter(rng, act, kind, floor):
    """Enemies plus a label for one combat node."""
    pool = ACT_POOLS[min(act, B.FINAL_ACT)]
    if kind == "boss":
        return [Enemy(rng.choice(pool["boss"]), act, rng)], "BOSS"
    if kind == "elite":
        elites = pool["elite"]
        prof = B.act_profile(act)
        sef = prof.get("super_elite_from")
        # Deep in an act, elites are drawn from the tougher half of the pool —
        # the entries an act lists last are its nastier ones (e.g. Book of
        # Stabbing, Ash Warden). Early on, any elite is fair game.
        if sef is not None and floor >= sef and len(elites) > 1:
            elites = elites[len(elites) // 2:]
            return [Enemy(rng.choice(elites), act, rng)], "SUPER-ELITE"
        return [Enemy(rng.choice(elites), act, rng)], "ELITE"
    group = rng.choice(pool["weak"] if floor < 3 else pool["strong"])
    return [Enemy(k, act, rng) for k in group], "COMBAT"
