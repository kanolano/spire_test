"""Map events.

Handlers take `(run, player)` and **return** their outcome rather than printing
it. The old handlers printed coloured text straight to stdout, so the web layer
had to run them under `contextlib.redirect_stdout` — swapping a process-global —
and then strip ANSI codes back out of the captured string.

A handler returns `outcome(text, then=...)`. `then` names a follow-up card picker
the run opens before the event finishes — "remove", "upgrade" or "duplicate".

A handler also carries a `@preview` line: the up-front summary of what taking
that option does. The flavour text on an option label is deliberately vague, so
without this the player is guessing — and a handler cannot be dry-run to find
out, because it mutates the player and draws from `run.rng` in the same pass.
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
FOUND_GOLD = (50, 90)
GAMBLE_WIN_GOLD = (80, 140)
GAMBLE_LOSS_GOLD = (40, 80)


def outcome(text, then=None):
    return {"text": text, "then": then}


def preview(text):
    """Attach the player-facing summary of what an option costs and grants."""
    def deco(fn):
        fn.preview = text
        return fn
    return deco


def preview_of(fn):
    return getattr(fn, "preview", "")


@preview(f"Heal {int(HEAL_FRACTION * 100)}% of your Max HP.")
def _ev_heal(run, p):
    n = int(p.max_hp * HEAL_FRACTION)
    p.hp = min(p.max_hp, p.hp + n)
    return outcome(f"You heal {n} HP.")


@preview(f"Gain {MAX_HP_GAIN} Max HP, and {MAX_HP_GAIN} HP with it.")
def _ev_maxhp(run, p):
    p.max_hp += MAX_HP_GAIN
    p.hp += MAX_HP_GAIN
    return outcome(f"Max HP +{MAX_HP_GAIN}.")


@preview("Gain a random relic, and add a Regret curse to your deck.")
def _ev_curse_relic(run, p):
    key = roll_relic(run.rng, p.relics)
    p.add_relic(key)
    p.deck.append(Card("regret"))
    return outcome(f"You gain {RELICS[key]['name']} — and a Regret curse.")


@preview(f"Gain {FOUND_GOLD[0]}–{FOUND_GOLD[1]} gold.")
def _ev_gold(run, p):
    n = run.rng.randint(*FOUND_GOLD)
    p.gold += n
    return outcome(f"You find {n} gold.")


@preview(f"An even chance of winning {GAMBLE_WIN_GOLD[0]}–{GAMBLE_WIN_GOLD[1]} gold "
         f"or losing {GAMBLE_LOSS_GOLD[0]}–{GAMBLE_LOSS_GOLD[1]}.")
def _ev_gamble(run, p):
    if run.rng.random() < 0.5:
        n = run.rng.randint(*GAMBLE_WIN_GOLD)
        p.gold += n
        return outcome(f"The bones favour you: +{n} gold.")
    loss = min(p.gold, run.rng.randint(*GAMBLE_LOSS_GOLD))
    p.gold -= loss
    return outcome(f"You lose {loss} gold.")


@preview("Upgrade a random card in your deck. You do not choose which.")
def _ev_upgrade(run, p):
    opts = [k for k in p.deck if k.upgradable and not k.upgraded]
    if not opts:
        return outcome("Nothing here can be improved.")
    k = run.rng.choice(opts)
    k.upgrade()
    return outcome(f"{k.name} glows with new power.")


@preview(f"Lose {REMOVE_HP_COST} HP, then remove a card of your choice from your deck.")
def _ev_remove(run, p):
    p.hp = max(1, p.hp - REMOVE_HP_COST)
    return outcome(f"The rite costs you {REMOVE_HP_COST} HP.", then="remove")


@preview(f"Gain a random potion — or {POTION_SALE_GOLD} gold instead if your potion "
         "slots are full.")
def _ev_potion(run, p):
    if len(p.potions) < p.max_potions:
        k = run.rng.choice(list(POTIONS))
        p.potions.append(k)
        return outcome(f"You pocket a {POTIONS[k]['name']}.")
    p.gold += POTION_SALE_GOLD
    return outcome(f"No room for potions — you sell it for {POTION_SALE_GOLD} gold.")


@preview("Nothing gained, nothing lost.")
def _ev_nothing(run, p):
    return outcome("You walk on. Nothing happens.")


@preview(f"Lose {LIBRARY_HP_COST} HP, and add a random card to your deck.")
def _ev_hurt_card(run, p):
    p.hp = max(1, p.hp - LIBRARY_HP_COST)
    keys = random_card_keys(run.rng, 1, (0.2, 0.5, 0.3), p.cls)
    p.deck.append(Card(keys[0]))
    return outcome(f"You lose {LIBRARY_HP_COST} HP but learn {CARDS[keys[0]]['name']}.")


MIRROR_MAX_HP_COST = 6
FORGE_PRICE = 60
CROW_HP_COST = 6
CROW_GOLD = (60, 110)
CROW_SALE_GOLD = 40
STAIR_HEAL = 12
STAIR_GOLD = (40, 75)


@preview(f"Lose {MIRROR_MAX_HP_COST} Max HP, then add a copy of a card of your choice.")
def _ev_duplicate(run, p):
    p.max_hp = max(1, p.max_hp - MIRROR_MAX_HP_COST)
    p.hp = min(p.hp, p.max_hp)
    return outcome(f"The glass drinks {MIRROR_MAX_HP_COST} Max HP and offers a twin.",
                   then="duplicate")


@preview(f"Pay {FORGE_PRICE} gold, then upgrade a card of your choice. "
         "Nothing happens if you cannot pay.")
def _ev_forge(run, p):
    if p.gold < FORGE_PRICE:
        return outcome("You cannot cover the smith's price. He turns away.")
    p.gold -= FORGE_PRICE
    return outcome(f"You pay {FORGE_PRICE} gold and the smith takes up his hammer.",
                   then="upgrade")


@preview(f"Lose {CROW_HP_COST} HP, gain {CROW_GOLD[0]}–{CROW_GOLD[1]} gold.")
def _ev_crow_gold(run, p):
    p.hp = max(1, p.hp - CROW_HP_COST)
    n = run.rng.randint(*CROW_GOLD)
    p.gold += n
    return outcome(f"The beak finds your arm — {CROW_HP_COST} HP — but it leads you "
                   f"to {n} gold.")


@preview(f"Gain a random potion — or {CROW_SALE_GOLD} gold instead if your potion "
         "slots are full.")
def _ev_crow_feed(run, p):
    if len(p.potions) < p.max_potions:
        k = run.rng.choice(list(POTIONS))
        p.potions.append(k)
        return outcome(f"The crow drops a {POTIONS[k]['name']} at your feet.")
    p.gold += CROW_SALE_GOLD
    return outcome(f"Your satchel is full, so the crow leaves {CROW_SALE_GOLD} gold "
                   "instead.")


@preview(f"Heal up to {STAIR_HEAL} HP.")
def _ev_stair_climb(run, p):
    healed = min(STAIR_HEAL, p.max_hp - p.hp)
    p.hp += healed
    return outcome(f"You pick your way up in silence and catch your breath. +{healed} HP.")


@preview(f"Gain {STAIR_GOLD[0]}–{STAIR_GOLD[1]} gold, and add a Slimed curse to your deck.")
def _ev_stair_search(run, p):
    n = run.rng.randint(*STAIR_GOLD)
    p.gold += n
    p.deck.append(Card("slimed"))
    return outcome(f"You dig out {n} gold, and something wet clings to your pack.")


EVENTS = [
    dict(title="THE CLERIC", text="A robed figure offers her services to weary travellers, "
                                  "for a price that is not always gold.",
         options=[("Ask for healing", _ev_heal),
                  ("Ask her to purge a card", _ev_remove),
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
    dict(title="THE ASHEN MIRROR", text="A pane of black glass, unbroken in all this ruin. "
                                        "Your reflection is a half-step behind you, and it "
                                        "is holding one of your cards.",
         options=[("Reach through the glass", _ev_duplicate),
                  ("Look away", _ev_nothing)]),
    dict(title="THE COLD FORGE", text="A smith works a forge that gives no heat. He does not "
                                      "look up. 'Sixty,' he says, 'and I'll sharpen "
                                      "something for you.'",
         options=[("Pay the smith", _ev_forge), ("Keep your coin", _ev_nothing)]),
    dict(title="THE STARVING CROW", text="An enormous crow blocks the stair, head cocked. "
                                         "It is plainly hungry, and plainly clever.",
         options=[("Let it take a bite", _ev_crow_gold),
                  ("Share your rations", _ev_crow_feed),
                  ("Drive it off", _ev_nothing)]),
    dict(title="THE COLLAPSED STAIR", text="Half the stairwell has fallen away. There is a "
                                           "quiet path around it, and a heap of rubble that "
                                           "glitters where the torchlight catches.",
         options=[("Take the quiet path", _ev_stair_climb),
                  ("Search the rubble", _ev_stair_search)]),
]
