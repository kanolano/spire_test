"""The terminal client.

This is a *client* of the engine, exactly like the web server is. It renders
`view(run)` and turns keystrokes into `run.apply(...)` actions. It holds no rules
of its own, which is what stops it drifting away from the browser version the way
the old `Game` and `Session` did.
"""

import argparse
import sys

from ..engine.errors import InvalidAction
from ..engine.records import load_records, save_record
from ..engine.run import Run
from ..web.dto import CLASS_ROSTER, view
from .render import (BOLD, CYN, GRN, GRY, MAG, RED, WHT, YEL, TITLE, bar, c,
                     clear, pause, print_cards, prompt, render_map, status_line,
                     term_width, wrap)


def rule(ch="═", color=GRY):
    print(c(ch * min(term_width() - 1, 96), color))


def header(st):
    p = st["player"]
    print(c(f"  {p['name']}   ACT {st['act']}   floor {st['floor']}/15", BOLD, YEL))
    print(f"  {bar(p['hp'], p['max_hp'], 16, GRN)} {p['hp']}/{p['max_hp']}"
          f"   {c('◉ ' + str(p['gold']), YEL)}   deck {p['deck_size']}")
    if p["relics"]:
        print(c("  relics: " + ", ".join(r["name"] for r in p["relics"]), MAG))
    if p["potions"]:
        print(c("  potions: " + "  ".join(f"(p{i + 1}) {q['name']}"
                                          for i, q in enumerate(p["potions"])), CYN))


def show_banner(st):
    if st["banner"]:
        title, body = st["banner"]
        print()
        print(c("  " + title, BOLD, YEL))
        print(c("  " + body, GRY))
        print()


# ── screens ────────────────────────────────────────────────────────────────
def screen_select(run, st):
    clear()
    print(c(TITLE, YEL))
    print(c("   A roguelike deckbuilder. Choose your climber.\n", GRY))
    for i, d in enumerate(CLASS_ROSTER, 1):
        print(c(f"  {i}. {d['name']}", BOLD, WHT) +
              c(f"   {d['hp']} HP   {d['energy']} energy", GRY))
        for line in wrap(d["blurb"], min(term_width() - 8, 86)):
            print(c("     " + line, GRY))
        print(c(f"     relic: {d['relic']['name']} — {d['relic']['desc']}", MAG))
        print()
    ans = prompt(c("  choose 1-%d > " % len(CLASS_ROSTER), YEL))
    if ans.isdigit() and 1 <= int(ans) <= len(CLASS_ROSTER):
        return {"type": "new_run", "cls": CLASS_ROSTER[int(ans) - 1]["key"]}
    return None


def screen_map(run, st):
    clear()
    header(st)
    show_banner(st)
    rule("─")
    m = st["map"]
    for row in render_map(m["floors"], m["cur_floor"], m["cur_idx"], m["visited"]):
        print("  " + row)
    rule("─")
    reach = m["reachable"]
    opts = ", ".join(f"({chr(ord('a') + i)})" for i in reach)
    ans = prompt(c(f"  climb to {opts} / (d)eck / (q)uit > ", YEL)).lower()
    if ans in ("q", "quit"):
        raise SystemExit(0)
    if ans in ("d", "deck"):
        show_deck(st)
        return None
    if ans and ans[0].isalpha():
        idx = ord(ans[0]) - ord("a")
        if idx in reach:
            return {"type": "map", "idx": idx}
    return None


def screen_combat(run, st):
    clear()
    cb = st["combat"]
    p = st["player"]
    rule()
    print(c(f" {cb['label']}  —  turn {cb['turn']} ", BOLD, YEL))
    print()
    for i, e in enumerate(cb["enemies"]):
        tag = chr(ord("a") + i)
        if not e["alive"]:
            print(c(f"  ({tag}) {e['name']:<18} DEAD", GRY))
            continue
        blk = c(f" ⛨{e['block']}", CYN) if e["block"] else ""
        print(f"  ({c(tag, YEL)}) {c(e['name'].ljust(18), WHT)} "
              f"{bar(e['hp'], e['max_hp'], 14, RED)} {e['hp']}/{e['max_hp']:<6}{blk}")
        line = "       intent: " + intent_text(e["intent"])
        st_line = status_line(e["statuses"])
        if st_line:
            line += "   " + st_line
        print(line)
    print()
    rule("─")
    blk = c(f"⛨ {p['block']}", CYN) if p["block"] else c("⛨ 0", GRY)
    print(f"  {c(p['name'], BOLD, GRN)}  {bar(p['hp'], p['max_hp'], 16, GRN)} "
          f"{p['hp']}/{p['max_hp']}   {blk}   "
          f"{c('⚡ ' + str(cb['energy']) + '/' + str(p['max_energy']), YEL)}")
    st_line = status_line(p["statuses"])
    if st_line:
        print("  " + st_line)
    print(c(f"  draw {cb['draw']}   discard {cb['discard']}   "
            f"exhaust {cb['exhaust']}   gold {p['gold']}", GRY))
    if p["potions"]:
        print("  " + "  ".join(f"{c('(p' + str(i + 1) + ')', YEL)} {q['name']}"
                               for i, q in enumerate(p["potions"])))
    print()
    print_cards(cb["hand"], cb["energy"])
    print()
    for line in cb["log"][-3:]:
        print(c("  " + line, GRY))

    ans = prompt(c("  play # / (p#) potion / (e)nd turn / (d)eck / (?)help > ",
                   YEL)).lower()
    if ans in ("e", "end", ""):
        return {"type": "end_turn"}
    if ans in ("?", "h", "help"):
        help_screen()
        return None
    if ans in ("d", "deck"):
        show_piles(st)
        return None
    if ans.startswith("p") and ans[1:].isdigit():
        idx = int(ans[1:]) - 1
        potions = p["potions"]
        target = None
        if 0 <= idx < len(potions) and potions[idx]["targeted"]:
            target = ask_target(cb)
            if target is None:
                return None
        return {"type": "potion", "idx": idx, "target": target}
    if ans.isdigit():
        idx = int(ans) - 1
        hand = cb["hand"]
        if not 0 <= idx < len(hand):
            return None
        card = hand[idx]
        target = ask_target(cb) if card["targeted"] else None
        if card["targeted"] and target is None:
            return None
        exhaust = None
        if card["requires"] == "exhaust":
            exhaust = ask_exhaust(hand)
            if exhaust is None:
                return None
        return {"type": "play", "idx": idx, "target": target, "exhaust": exhaust}
    return None


def intent_text(it):
    if not it:
        return ""
    if it["kind"] == "attack":
        hits = f" x{it['hits']}" if it.get("hits", 1) > 1 else ""
        extra = " +debuff" if it.get("extra") else ""
        return c(f"⚔ {it['dmg']}{hits}{extra}", RED)
    return {"block": c("⛨ defend", CYN), "buff": c("↑ buff", YEL)}.get(
        it["kind"], c("↓ debuff", MAG))


def ask_target(cb):
    """Pick an enemy. Auto-selects when there is only one left."""
    alive = [i for i, e in enumerate(cb["enemies"]) if e["alive"]]
    if len(alive) == 1:
        return alive[0]
    opts = ", ".join(f"({chr(ord('a') + i)}) {cb['enemies'][i]['name']}" for i in alive)
    ans = prompt(c(f"  target — {opts} > ", YEL)).lower()
    if not ans:
        return None
    i = ord(ans[0]) - ord("a")
    return i if i in alive else None


def ask_exhaust(hand):
    print(c("\n  Exhaust which card?", YEL))
    print_cards(hand)
    ans = prompt(c("  > ", YEL))
    if ans.isdigit() and 1 <= int(ans) <= len(hand):
        return int(ans) - 1
    return None


def screen_reward(run, st):
    clear()
    r = st["reward"]
    print(c("\n  VICTORY!\n", BOLD, GRN))
    print(c(f"  You find {r['gold']} gold.", YEL))
    if r["relic"]:
        print(c(f"  Relic obtained: {r['relic']['name']} — {r['relic']['desc']}", MAG))
    if r["potion"]:
        print(c(f"  Potion obtained: {r['potion']['name']}", MAG))
    print()
    print(c("  Choose a card to add to your deck:\n", YEL))
    print_cards(r["cards"])
    ans = prompt(c("\n  card # / (s)kip > ", YEL)).lower()
    if ans.isdigit() and 1 <= int(ans) <= len(r["cards"]):
        return {"type": "reward", "idx": int(ans) - 1}
    return {"type": "reward", "idx": None}


def screen_choose(run, st):
    clear()
    ch = st["choose"]
    print(c(f"\n  {ch['title']}\n", BOLD, YEL))
    print_cards(ch["cards"])
    tail = " / (s)kip" if ch["allow_skip"] else ""
    ans = prompt(c(f"\n  card #{tail} > ", YEL)).lower()
    if ans.isdigit() and 1 <= int(ans) <= len(ch["cards"]):
        return {"type": "choose", "idx": int(ans) - 1}
    return {"type": "choose", "idx": None}


def screen_rest(run, st):
    clear()
    header(st)
    p = st["player"]
    heal = max(1, int(p["max_hp"] * 0.3))
    print(c("\n  A CAMPFIRE\n", BOLD, YEL))
    print(f"  1. Rest — heal {heal} HP")
    print("  2. Smith — upgrade a card")
    ans = prompt(c("\n  > ", YEL))
    if ans == "1":
        return {"type": "rest"}
    if ans == "2":
        return {"type": "smith"}
    return None


def screen_shop(run, st):
    clear()
    header(st)
    s = st["shop"]
    print(c("\n  THE MERCHANT\n", BOLD, YEL))
    print_cards(s["cards"])
    for i, card in enumerate(s["cards"], 1):
        print(c(f"   {i}. {card['name']:<22} {card['price']} gold", WHT))
    n = len(s["cards"])
    if s["relic"]:
        print(c(f"   {n + 1}. {s['relic']['name']:<22} {s['relic_price']} gold"
                f"  — {s['relic']['desc']}", MAG))
    for i, q in enumerate(s["potions"]):
        print(c(f"   {n + 2 + i}. {q['name']:<22} {q['price']} gold", CYN))
    if not s["removed"]:
        print(c(f"   r. Remove a card from your deck   {s['removal_price']} gold", GRY))
    ans = prompt(c("\n  buy # / (r)emove / (l)eave > ", YEL)).lower()
    if ans in ("l", "leave", ""):
        return {"type": "shop_leave"}
    if ans == "r":
        return {"type": "shop_buy", "what": "removal"}
    if ans.isdigit():
        i = int(ans)
        if 1 <= i <= n:
            return {"type": "shop_buy", "what": "card", "idx": i - 1}
        if i == n + 1:
            return {"type": "shop_buy", "what": "relic"}
        if n + 2 <= i <= n + 1 + len(s["potions"]):
            return {"type": "shop_buy", "what": "potion", "idx": i - n - 2}
    return None


def screen_event(run, st):
    clear()
    header(st)
    ev = st["event"]
    print(c(f"\n  {ev['title']}\n", BOLD, YEL))
    for line in wrap(ev["text"], min(term_width() - 6, 86)):
        print("  " + c(line, GRY))
    print()
    if ev["result"] is None:
        for i, label in enumerate(ev["options"], 1):
            print(f"   {i}. {label}")
        ans = prompt(c("\n  > ", YEL))
        if ans.isdigit() and 1 <= int(ans) <= len(ev["options"]):
            return {"type": "event_choose", "idx": int(ans) - 1}
        return None
    print(c("  " + ev["result"], GRN))
    pause()
    return {"type": "event_done"}


def screen_treasure(run, st):
    clear()
    header(st)
    t = st["treasure"]
    print(c("\n  A CHEST\n", BOLD, YEL))
    print(c(f"  {t['gold']} gold.", YEL))
    print(c(f"  {t['relic']['name']} — {t['relic']['desc']}", MAG))
    pause()
    return {"type": "treasure_done"}


def show_deck(st):
    clear()
    print(c(f"\n  YOUR DECK — {len(st['deck'])} cards\n", BOLD, YEL))
    print_cards(st["deck"], numbered=False)
    pause()


def show_piles(st):
    clear()
    cb = st["combat"]
    for title, pile in (("DRAW PILE (order hidden)", cb["draw_pile"]),
                        ("DISCARD PILE", cb["discard_pile"]),
                        ("EXHAUSTED", cb["exhaust_pile"])):
        print(c(f"\n  {title} — {len(pile)} cards", BOLD, YEL))
        if pile:
            print_cards(pile, numbered=False)
    pause()


def help_screen():
    clear()
    print(c("\n  HOW TO PLAY\n", BOLD, YEL))
    for line in [
        "Type a card's number to play it. Cards cost Energy (⚡); you get 3 per turn.",
        "'e' ends your turn: your hand is discarded and the enemies act.",
        "Block (⛨) absorbs damage and vanishes at the start of your next turn.",
        "Enemy intent shows what they will do next — ⚔ is the damage you would take.",
        "",
        c("Vulnerable", MAG) + " — takes 50% more attack damage.",
        c("Weak", 34) + " — deals 25% less attack damage.",
        c("Frail", 34) + " — gains 25% less Block.",
        c("Strength", RED) + " — adds damage to each attack. " +
        c("Dexterity", GRN) + " — adds Block.",
        c("Poison", GRN) + " — lose that much HP each turn; it decreases by 1.",
        c("Thorns", YEL) + " — attackers take damage.",
        "",
        "'d' inspects your draw / discard / exhaust piles. 'p1'..'p3' drink a potion.",
    ]:
        print("   " + line)
    pause()


def screen_end(run, st, won):
    clear()
    p = st["player"]
    if won:
        print(c("\n  THE SPIRE IS YOURS.\n", BOLD, YEL))
    else:
        print(c("\n  YOU DIED.\n", BOLD, RED))
        print(c(f"  Slain by {st['killer']}.", GRY))
    print(c(f"  Act {st['act']} · {st['floors_cleared']} floors cleared · "
            f"{p['deck_size']} cards · {p['gold']} gold\n", GRY))
    try:
        records = save_record(run.summary(won))
    except OSError:
        records = load_records()
        print(c("  (could not write the leaderboard)", RED))
    print(c("  BEST RUNS", BOLD, YEL))
    for r in records[:5]:
        mark = c("WIN ", GRN) if r.get("won") else c("dead", GRY)
        print(c(f"   {mark} act {r.get('act', 1)}  {r.get('floors', 0):>2} floors  "
                f"{r.get('cls', '?')}  — {r.get('killer', '?')}", GRY))
    print()
    return prompt(c("  Climb again? (y/n) > ", YEL)).lower().startswith("y")


SCREENS = {
    "select": screen_select,
    "map": screen_map,
    "combat": screen_combat,
    "reward": screen_reward,
    "choose": screen_choose,
    "rest": screen_rest,
    "shop": screen_shop,
    "event": screen_event,
    "treasure": screen_treasure,
}


def play(seed=None):
    """One climb. Returns True if the player wants another."""
    run = Run(seed=seed)
    while True:
        st = view(run)
        if run.finished:
            return screen_end(run, st, run.screen == "win")
        action = SCREENS[run.screen](run, st)
        if action is None:
            continue
        try:
            run.apply(action)
        except InvalidAction as e:
            print(c(f"  {e}", RED))
            pause()


def main(argv=None):
    parser = argparse.ArgumentParser(prog="spire",
                                     description="Play Spire of Ash in the terminal.")
    parser.add_argument("--seed", type=int, default=None,
                        help="play a reproducible run")
    args = parser.parse_args(argv)
    try:
        while play(args.seed):
            args.seed = None      # only the first run honours an explicit seed
    except SystemExit:
        pass
    clear()
    print(c("\n  The Spire waits.\n", GRY))
    return 0


if __name__ == "__main__":
    sys.exit(main())
