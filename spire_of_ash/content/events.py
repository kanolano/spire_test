"""Map events.

Handlers take `(run, player)` and **return** their outcome rather than printing
it. The old handlers printed coloured text straight to stdout, so the web layer
had to run them under `contextlib.redirect_stdout` — swapping a process-global —
and then strip ANSI codes back out of the captured string.

A handler returns `outcome(text, then=...)`. `then` names a follow-up screen the
run must open before the event is finished; only "remove" (card removal) is used
today.
"""

from ..engine.card import Card
from .cards import CARDS
from .pools import random_card_keys, roll_relic
from .potions import POTIONS
from .relics import RELICS

HEAL_FRACTION = 0.25
MAX_HP_GAIN = 8
REMOVE_HP_COST = 8
LIBRARY_HP_COST = 10
POTION_SALE_GOLD = 30


def outcome(text, then=None):
    return {"text": text, "then": then}


def _ev_heal(run, p):
    n = int(p.max_hp * HEAL_FRACTION)
    p.hp = min(p.max_hp, p.hp + n)
    return outcome(f"You heal {n} HP.")


def _ev_maxhp(run, p):
    p.max_hp += MAX_HP_GAIN
    p.hp += MAX_HP_GAIN
    return outcome(f"Max HP +{MAX_HP_GAIN}.")


def _ev_curse_relic(run, p):
    key = roll_relic(run.rng, p.relics)
    p.add_relic(key)
    p.deck.append(Card("regret"))
    return outcome(f"You gain {RELICS[key]['name']} — and a Regret curse.")


def _ev_gold(run, p):
    n = run.rng.randint(50, 90)
    p.gold += n
    return outcome(f"You find {n} gold.")


def _ev_gamble(run, p):
    if run.rng.random() < 0.5:
        n = run.rng.randint(80, 140)
        p.gold += n
        return outcome(f"The bones favour you: +{n} gold.")
    loss = min(p.gold, run.rng.randint(40, 80))
    p.gold -= loss
    return outcome(f"You lose {loss} gold.")


def _ev_upgrade(run, p):
    opts = [k for k in p.deck if k.upgradable and not k.upgraded]
    if not opts:
        return outcome("Nothing here can be improved.")
    k = run.rng.choice(opts)
    k.upgrade()
    return outcome(f"{k.name} glows with new power.")


def _ev_remove(run, p):
    p.hp = max(1, p.hp - REMOVE_HP_COST)
    return outcome(f"The rite costs you {REMOVE_HP_COST} HP.", then="remove")


def _ev_potion(run, p):
    if len(p.potions) < p.max_potions:
        k = run.rng.choice(list(POTIONS))
        p.potions.append(k)
        return outcome(f"You pocket a {POTIONS[k]['name']}.")
    p.gold += POTION_SALE_GOLD
    return outcome(f"No room for potions — you sell it for {POTION_SALE_GOLD} gold.")


def _ev_nothing(run, p):
    return outcome("You walk on. Nothing happens.")


def _ev_hurt_card(run, p):
    p.hp = max(1, p.hp - LIBRARY_HP_COST)
    keys = random_card_keys(run.rng, 1, (0.2, 0.5, 0.3), p.cls)
    p.deck.append(Card(keys[0]))
    return outcome(f"You lose {LIBRARY_HP_COST} HP but learn {CARDS[keys[0]]['name']}.")


EVENTS = [
    dict(title="THE CLERIC", text="A robed figure offers her services to weary travellers, "
                                  "for a price that is not always gold.",
         options=[("Ask for healing", _ev_heal),
                  ("Ask her to purge a card (lose 8 HP)", _ev_remove),
                  ("Leave", _ev_nothing)]),
    dict(title="GOLDEN IDOL", text="A heavy idol sits on a pressure plate. Taking it will "
                                   "surely trigger something.",
         options=[("Take it", _ev_curse_relic), ("Leave it alone", _ev_nothing)]),
    dict(title="BONFIRE SPIRITS", text="Spirits circle a green flame. Offer something to "
                                       "the fire and it may give something back.",
         options=[("Offer a card to the flames", _ev_remove),
                  ("Warm yourself", _ev_heal)]),
    dict(title="DEAD ADVENTURER", text="A corpse in dented armour, still clutching a purse. "
                                       "Something killed him and may still be near.",
         options=[("Search the body", _ev_gold), ("Pay respects and move on", _ev_nothing)]),
    dict(title="THE GAMBLER", text="A grinning stranger rattles a cup of knucklebones. "
                                   "'Double or nothing, friend.'",
         options=[("Roll the bones", _ev_gamble), ("Decline", _ev_nothing)]),
    dict(title="WHETSTONE", text="An old whetstone hums faintly on a stone plinth.",
         options=[("Sharpen a card", _ev_upgrade), ("Leave", _ev_nothing)]),
    dict(title="THE SACRED FOUNTAIN", text="Clear water bubbles up through cracked "
                                           "marble. It smells faintly of iron.",
         options=[("Drink deeply", _ev_maxhp), ("Fill a vial", _ev_potion),
                  ("Move on", _ev_nothing)]),
    dict(title="THE LIBRARY", text="Shelves of half-burnt tomes. One book is still warm, "
                                   "and reading it hurts.",
         options=[("Read the warm book", _ev_hurt_card), ("Take a nap instead", _ev_heal)]),
]
