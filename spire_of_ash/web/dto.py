"""Engine state → the JSON the browser client consumes.

Keeping this separate from the engine means view concerns never leak into the
rules. `card_data` used to special-case `card.key == "true_grit"` to decide
whether a card needed an extra choice; cards now declare that themselves via
`Card.requires`.
"""

from ..content.cards import CARDS
from ..content.classes import CLASSES
from ..content.potions import POTIONS
from ..content.relics import RELICS
from ..statuses import describe


def card_data(card, energy=None, idx=None):
    affordable = energy is None or card.cost == "X" or card.cost <= energy
    return {
        "i": idx,
        "key": card.key,
        "name": card.name,
        "type": card.type,
        "cost": card.cost,
        "desc": card.desc,
        "upgraded": card.upgraded,
        "playable": bool(card.playable and affordable),
        "targeted": card.targeted,
        "requires": card.requires,
        # kept for the current client, which still reads this name
        "needs_hand": card.requires == "exhaust",
    }


def cards_data(cards, energy=None):
    return [card_data(k, energy, i) for i, k in enumerate(cards)]


def sorted_cards(cards):
    return sorted((card_data(k) for k in cards), key=lambda d: (d["type"], d["name"]))


def relic_dto(key):
    """The one place a relic becomes {name, desc}. This literal appeared six times."""
    r = RELICS[key]
    return {"key": key, "name": r["name"], "desc": r["desc"]}


def potion_dto(key):
    p = POTIONS[key]
    return {"key": key, "name": p["name"], "desc": p["desc"],
            "targeted": bool(p.get("targeted"))}


def statuses_dto(triples):
    """Chips carry their own explanation so the client can tooltip them."""
    out = []
    for key, label, n in triples:
        name, desc = describe(key)
        out.append({"key": key, "label": label, "value": n,
                    "name": name, "desc": desc})
    return out


def event_option_dto(option):
    """Older saves stored options as bare label strings."""
    if isinstance(option, str):
        return {"label": option, "preview": ""}
    return {"label": option["label"], "preview": option.get("preview", "")}


def _class_roster():
    out = []
    for key, d in CLASSES.items():
        out.append({
            "key": key, "name": d["name"], "hp": d["hp"], "energy": d["energy"],
            "blurb": d["blurb"],
            "deck": sorted({CARDS[k]["name"] for k in d["deck"]}),
            "relic": relic_dto(d["relic"]),
            "cards": len(d["common"]) + len(d["uncommon"]) + len(d["rare"]),
        })
    return out


# Static for the life of the process — it used to be rebuilt and shipped on
# every single response.
CLASS_ROSTER = _class_roster()


def piles_view(run):
    """Pile contents, fetched only when the player opens the overlay."""
    cb = run.combat
    if not cb:
        return {"draw_pile": [], "discard_pile": [], "exhaust_pile": []}
    return {
        # the real draw order stays hidden
        "draw_pile": sorted_cards(cb.draw_pile),
        "discard_pile": [card_data(k) for k in cb.discard],
        "exhaust_pile": [card_data(k) for k in cb.exhausted],
    }


def view(run):
    """The full view model for one run."""
    st = run.state()
    p, cb = run.player, run.combat

    st["player"]["statuses"] = statuses_dto(st["player"]["statuses"])
    st["player"]["relics"] = [relic_dto(k) for k in p.relics]
    st["player"]["potions"] = [potion_dto(k) for k in p.potions]
    st["deck"] = sorted_cards(p.deck)

    # The roster is only read by the character-select screen.
    if run.screen == "select":
        st["classes"] = CLASS_ROSTER

    if cb:
        c = st["combat"]
        for e, src in zip(c["enemies"], cb.enemies):
            e["statuses"] = statuses_dto(e["statuses"])
            if e["intent"] is not None:
                e["intent"] = dict(e["intent"], name=src.intent,
                                   dmg=e["intent"].get("damage"))
        c["hand"] = cards_data(cb.hand, cb.energy)
        # The three pile *contents* used to ship with every single response and
        # were only read when the player opened an overlay. Counts travel here;
        # the cards come from /piles on demand.

    if run.reward:
        r = run.reward
        st["reward"] = {
            "gold": r["gold"], "kind": r["kind"], "log": r["log"],
            "relic": relic_dto(r["relic"]) if r["relic"] else None,
            "potion": potion_dto(r["potion"]) if r["potion"] else None,
            "cards": cards_data(r["cards"]),
            "relic_taken": bool(r.get("relic_taken")),
            "potion_taken": bool(r.get("potion_taken")),
            "card_taken": bool(r.get("card_taken")),
            "potions_full": len(p.potions) >= p.max_potions,
        }
    if run.choose:
        ch = run.choose
        st["choose"] = {"kind": ch["kind"], "title": ch["title"], "back": ch["back"],
                        "allow_skip": ch["allow_skip"], "cards": cards_data(ch["cards"])}
    if run.shop:
        s = run.shop
        st["shop"] = {
            "relic_price": s["relic_price"], "removal_price": s["removal_price"],
            "removed": s["removed"],
            "cards": [dict(d, price=s["prices"][i])
                      for i, d in enumerate(cards_data(s["cards"]))],
            "relic": relic_dto(s["relic"]) if s["relic"] else None,
            "potions": [dict(potion_dto(k), price=s["potion_prices"][i])
                        for i, k in enumerate(s["potions"])],
        }
    if run.treasure:
        t = run.treasure
        st["treasure"] = {"gold": t["gold"], "relic": relic_dto(t["relic"])}
    if run.event:
        e = run.event
        st["event"] = {"title": e["title"], "text": e["text"],
                       "options": [event_option_dto(o) for o in e["options"]],
                       "result": e["result"], "then": e["then"]}
    return st
