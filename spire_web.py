"""Browser front-end for Spire of Ash.

Runs a stdlib HTTP server that drives the game engine in spire.py and serves
spire_ui.html.  Nothing to install:

    python3 spire_web.py            # then open http://localhost:8765

The terminal version (python3 spire.py) still works and shares the same engine.
"""
import contextlib
import io
import json
import os
import random
import re
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

try:
    import termios
except ImportError:  # windows
    termios = None

import spire

HERE = os.path.dirname(os.path.abspath(__file__))
UI_FILE = os.path.join(HERE, "spire_ui.html")
ANSI = re.compile(r"\x1b\[[0-9;]*m")


def plain(text):
    return ANSI.sub("", text)


# ─────────────────────────────────────────────────────────── engine adapters ──
class WebCombat(spire.Combat):
    """spire.Combat with the terminal prompts replaced by pre-supplied choices."""

    def __init__(self, *a, **kw):
        self.web_target = None
        self.web_exhaust = None
        super().__init__(*a, **kw)

    def choose_target(self, auto_ok=True):
        alive = self.living()
        if not alive:
            return None
        if self.web_target is not None and 0 <= self.web_target < len(self.enemies):
            e = self.enemies[self.web_target]
            if e.alive:
                return e
        return alive[0]

    def grit_exhaust(self, choose):
        if not self.hand:
            return
        idx = self.web_exhaust
        if not (choose and idx is not None and 0 <= idx < len(self.hand)):
            idx = random.randrange(len(self.hand))
        card = self.hand.pop(idx)
        self.exhaust_card(card)
        self.msg(f"Exhausted {card.name}.")

    def msg(self, text):
        self.log.append(plain(text))
        self.log = self.log[-40:]

    def render(self):
        pass


def card_data(card, energy=None, idx=None):
    return {
        "i": idx,
        "name": card.name,
        "type": card.type,
        "cost": "X" if card.cost == "X" else card.cost,
        "desc": card.desc,
        "upgraded": card.upgraded,
        "playable": bool(card.playable and (energy is None or card.cost == "X"
                                            or card.cost <= energy)),
        "targeted": card.targeted,
        "needs_hand": card.key == "true_grit" and card.upgraded,
    }


def status_data(comb):
    out = []
    for k, v in comb.st.items():
        label = spire.STATUS_INFO.get(k, ("", 0))[0]
        if v and label:
            out.append({"key": k, "label": label, "value": v})
    return out


def intent_data(enemy, player):
    if not enemy.intent:
        return None
    m = enemy.moves[enemy.intent]
    d = {"kind": m["kind"], "name": enemy.intent, "hits": m["hits"], "extra": bool(m["fn"])}
    if m["kind"] == "attack":
        d["dmg"] = spire.damage_after_modifiers(enemy, m["dmg"], player)
    return d


def relic_data(player):
    return [{"name": spire.RELICS[r]["name"], "desc": spire.RELICS[r]["desc"]}
            for r in player.relics]


def potion_data(player):
    return [{"name": spire.POTIONS[k]["name"], "desc": spire.POTIONS[k]["desc"],
             "targeted": bool(spire.POTIONS[k].get("targeted"))}
            for k in player.potions]


class EventShim:
    """Stands in for the Game object that spire's event effects poke at."""

    def __init__(self):
        self.needs_removal = False

    def remove_screen(self, free=True):
        self.needs_removal = True
        return True


# ────────────────────────────────────────────────────────────────── session ──
class Session:
    """The whole run as an event-driven state machine (no blocking prompts)."""

    def __init__(self):
        self.new_run()

    # ── lifecycle ──
    def new_run(self):
        self.player = spire.Player()
        spire.PLAYER_REF[0] = self.player
        self.act = 1
        self.floors = spire.generate_map()
        self.cur_floor = -1
        self.cur_idx = 0
        self.visited = []
        self.floors_cleared = 0
        self.elites_killed = 0
        self.combat = None
        self.reward = None
        self.shop = None
        self.event = None
        self.choose = None
        self.treasure = None
        self.banner = None
        self.killer = "—"
        self.screen = "map"

    # ── helpers ──
    def reachable(self):
        if self.cur_floor == -1:
            return list(range(len(self.floors[0])))
        if self.cur_floor >= len(self.floors) - 1:
            return []
        return list(self.floors[self.cur_floor][self.cur_idx]["edges"])

    def to_map(self):
        self.screen = "map"
        self.reward = self.shop = self.event = self.choose = self.treasure = None

    def game_over(self, killer):
        self.killer = killer or "the Spire"
        self.screen = "gameover"
        self.combat = None
        self.save_record(False)

    def win(self):
        self.screen = "win"
        self.combat = None
        self.save_record(True)

    def save_record(self, won):
        spire.save_record(dict(act=self.act, floors=self.floors_cleared, won=won,
                               killer=self.killer, deck=len(self.player.deck),
                               gold=self.player.gold))

    # ── map ──
    def enter_node(self, idx):
        if self.screen != "map" or idx not in self.reachable():
            return
        nf = self.cur_floor + 1
        if nf >= len(self.floors):
            return
        self.visited.append([nf, idx])
        self.cur_floor, self.cur_idx = nf, idx
        kind = self.floors[nf][idx]["type"]
        if kind in ("monster", "elite", "boss"):
            self.start_combat(kind)
        elif kind == "rest":
            self.screen = "rest"
        elif kind == "shop":
            self.open_shop()
        elif kind == "treasure":
            self.open_treasure()
        elif kind == "event":
            self.open_event()

    def next_act(self):
        self.act += 1
        self.floors = spire.generate_map()
        self.cur_floor = -1
        self.cur_idx = 0
        self.visited = []
        p = self.player
        p.max_hp += 8
        p.hp = min(p.max_hp, p.hp + 20)
        self.banner = (f"The stairs spiral upward — ACT {self.act}",
                       f"Max HP +8. You recover some strength: {p.hp}/{p.max_hp}.")

    # ── combat ──
    def start_combat(self, kind):
        enemies, label = spire.make_encounter(self.act, kind, self.cur_floor)
        cb = WebCombat(self.player, enemies, f"{label} — floor {self.cur_floor + 1}")
        cb.kind = kind
        self.combat = cb
        self.screen = "combat"
        try:
            cb.start_combat()
            cb.player_turn_start()
        except spire.Defeat as e:
            self.game_over(str(e))
            return
        if not cb.living():
            self.victory()

    def guard(self, fn):
        """Run a combat step, converting death into the game-over screen."""
        cb = self.combat
        try:
            fn()
        except spire.Defeat as e:
            self.game_over(str(e))
            return False
        if cb is self.combat and not cb.living():
            self.victory()
            return False
        return True

    def play_card(self, idx, target=None, exhaust=None):
        cb = self.combat
        if self.screen != "combat" or not cb or not (0 <= idx < len(cb.hand)):
            return
        cb.web_target = target
        # the played card leaves hand before its effect runs, so shift the choice
        cb.web_exhaust = (exhaust - 1) if (exhaust is not None and exhaust > idx) else exhaust
        self.guard(lambda: cb.play_card(idx))

    def use_potion(self, idx, target=None):
        cb = self.combat
        if self.screen != "combat" or not cb:
            return
        cb.web_target = target
        self.guard(lambda: cb.use_potion(idx))

    def end_turn(self):
        cb = self.combat
        if self.screen != "combat" or not cb:
            return

        def step():
            cb.player_turn_end()
            if not cb.living():
                return
            cb.enemy_turns()
            cb.turn += 1
            if not cb.living():
                return
            cb.player_turn_start()
        self.guard(step)

    def victory(self):
        cb, p = self.combat, self.player
        kind = getattr(cb, "kind", "monster")
        p.block = 0
        p.st.clear()
        self.floors_cleared += 1
        if kind == "elite":
            self.elites_killed += 1
        if p.has("burning_blood"):
            p.hp = min(p.max_hp, p.hp + 6)
        if p.has("meat_on_bone") and p.hp < p.max_hp // 2:
            p.hp = min(p.max_hp, p.hp + 12)
        gold = {"monster": random.randint(10, 20), "elite": random.randint(25, 35),
                "boss": random.randint(80, 100)}[kind]
        p.gold += gold
        rew = {"gold": gold, "relic": None, "potion": None, "kind": kind,
               "log": list(cb.log[-6:])}
        if kind in ("elite", "boss"):
            key = random.choice([r for r in spire.RELIC_POOL if r not in p.relics]
                                or spire.RELIC_POOL)
            p.add_relic(key)
            rew["relic"] = {"name": spire.RELICS[key]["name"],
                            "desc": spire.RELICS[key]["desc"]}
        if random.random() < (0.6 if kind != "monster" else 0.4) and \
                len(p.potions) < p.max_potions:
            pk = random.choice(list(spire.POTIONS))
            p.potions.append(pk)
            rew["potion"] = {"name": spire.POTIONS[pk]["name"],
                             "desc": spire.POTIONS[pk]["desc"]}
        chances = (0.5, 0.38, 0.12) if kind != "monster" else (0.62, 0.31, 0.07)
        cards = [spire.Card(k) for k in spire.random_card_keys(3, chances)]
        if kind == "boss":
            for k in cards:
                k.upgrade()
        self.reward_cards = cards
        rew["cards"] = [card_data(k, idx=i) for i, k in enumerate(cards)]
        self.reward = rew
        self.combat = None
        self.screen = "reward"

    def take_reward(self, idx):
        if self.screen != "reward":
            return
        if idx is not None and 0 <= idx < len(self.reward_cards):
            self.player.deck.append(self.reward_cards[idx])
        kind = self.reward["kind"]
        self.to_map()
        if kind == "boss":
            if self.act >= 3:
                self.win()
            else:
                self.next_act()

    # ── campfire ──
    def rest(self):
        if self.screen != "rest":
            return
        p = self.player
        p.hp = min(p.max_hp, p.hp + max(1, int(p.max_hp * 0.3)))
        self.to_map()

    def smith(self):
        if self.screen != "rest":
            return
        opts = [k for k in self.player.deck if k.upgradable and not k.upgraded]
        if not opts:
            self.rest()
            return
        self.open_choose("upgrade", "Choose a card to upgrade", opts, "map")

    # ── card-picker modal ──
    def open_choose(self, kind, title, cards, back, allow_skip=False):
        self.choose_cards = cards
        self.choose = {"kind": kind, "title": title, "back": back,
                       "allow_skip": allow_skip,
                       "cards": [card_data(k, idx=i) for i, k in enumerate(cards)]}
        self.screen = "choose"

    def resolve_choose(self, idx):
        if self.screen != "choose":
            return
        kind, back = self.choose["kind"], self.choose["back"]
        if idx is not None and 0 <= idx < len(self.choose_cards):
            card = self.choose_cards[idx]
            if kind == "upgrade":
                card.upgrade()
            elif kind == "remove" and card in self.player.deck:
                self.player.deck.remove(card)
                if self.shop and self.pending_removal_price:
                    self.player.gold -= self.pending_removal_price
                    self.shop["removed"] = True
                    self.pending_removal_price = 0
        elif kind == "remove":
            self.pending_removal_price = 0
        self.choose = None
        if back == "shop" and self.shop:
            self.screen = "shop"
        else:
            self.to_map()

    # ── shop ──
    def open_shop(self):
        p = self.player
        self.shop_cards = [spire.Card(k) for k in spire.random_card_keys(5)]
        base = {"common": 50, "uncommon": 75, "rare": 130, "starter": 50}
        self.shop_prices = [base[k.rarity] + random.randint(-8, 8) for k in self.shop_cards]
        relic_key = random.choice([r for r in spire.RELIC_POOL if r not in p.relics]
                                  or spire.RELIC_POOL)
        self.shop_relic = relic_key
        self.shop_potions = random.sample(list(spire.POTIONS), 2)
        self.shop_potion_prices = [random.randint(45, 65) for _ in self.shop_potions]
        self.pending_removal_price = 0
        self.shop = {
            "relic_price": random.randint(140, 190),
            "removal_price": 75,
            "removed": False,
        }
        self.screen = "shop"

    def shop_state(self):
        s = dict(self.shop)
        s["cards"] = [dict(card_data(k, idx=i), price=self.shop_prices[i])
                      for i, k in enumerate(self.shop_cards)]
        s["relic"] = None
        if self.shop_relic:
            s["relic"] = {"name": spire.RELICS[self.shop_relic]["name"],
                          "desc": spire.RELICS[self.shop_relic]["desc"]}
        s["potions"] = [{"name": spire.POTIONS[k]["name"], "desc": spire.POTIONS[k]["desc"],
                         "price": self.shop_potion_prices[i]}
                        for i, k in enumerate(self.shop_potions)]
        return s

    def shop_buy(self, what, idx=0):
        if self.screen != "shop":
            return
        p = self.player
        if what == "card" and 0 <= idx < len(self.shop_cards):
            if p.gold >= self.shop_prices[idx]:
                p.gold -= self.shop_prices[idx]
                p.deck.append(self.shop_cards.pop(idx))
                self.shop_prices.pop(idx)
        elif what == "relic" and self.shop_relic:
            if p.gold >= self.shop["relic_price"]:
                p.gold -= self.shop["relic_price"]
                p.add_relic(self.shop_relic)
                self.shop_relic = None
        elif what == "potion" and 0 <= idx < len(self.shop_potions):
            if len(p.potions) < p.max_potions and p.gold >= self.shop_potion_prices[idx]:
                p.gold -= self.shop_potion_prices[idx]
                p.potions.append(self.shop_potions.pop(idx))
                self.shop_potion_prices.pop(idx)
        elif what == "removal" and not self.shop["removed"]:
            if p.gold >= self.shop["removal_price"] and p.deck:
                self.pending_removal_price = self.shop["removal_price"]
                self.open_choose("remove", "Choose a card to remove", list(p.deck), "shop")

    # ── treasure & events ──
    def open_treasure(self):
        p = self.player
        gold = random.randint(25, 60)
        p.gold += gold
        key = random.choice([r for r in spire.RELIC_POOL if r not in p.relics]
                            or spire.RELIC_POOL)
        p.add_relic(key)
        self.treasure = {"gold": gold, "relic": {"name": spire.RELICS[key]["name"],
                                                 "desc": spire.RELICS[key]["desc"]}}
        self.screen = "treasure"

    def open_event(self):
        ev = random.choice(spire.EVENTS)
        self.event_def = ev
        self.event = {"title": ev["title"], "text": ev["text"],
                      "options": [label for label, _ in ev["options"]], "result": None}
        self.screen = "event"

    def choose_event(self, idx):
        if self.screen != "event" or self.event["result"] is not None:
            return
        opts = self.event_def["options"]
        if not (0 <= idx < len(opts)):
            return
        shim = EventShim()
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            opts[idx][1](shim, self.player)
        self.event["result"] = plain(buf.getvalue()).strip() or "Nothing happens."
        self.event["needs_removal"] = shim.needs_removal

    def finish_event(self):
        if self.screen != "event":
            return
        if self.event.get("needs_removal") and self.player.deck:
            self.pending_removal_price = 0
            self.open_choose("remove", "Choose a card to remove", list(self.player.deck), "map")
        else:
            self.to_map()

    # ── serialisation ──
    def state(self):
        p = self.player
        cb = self.combat
        st = {
            "screen": self.screen,
            "act": self.act,
            "floor": self.cur_floor + 1,
            "floors_cleared": self.floors_cleared,
            "elites_killed": self.elites_killed,
            "banner": self.banner,
            "killer": self.killer,
            "player": {
                "name": p.name, "hp": p.hp, "max_hp": p.max_hp, "block": p.block,
                "gold": p.gold, "deck_size": len(p.deck),
                "statuses": status_data(p),
                "relics": relic_data(p), "potions": potion_data(p),
                "energy": cb.energy if cb else 0,
                "max_energy": p.max_energy,
            },
            "deck": sorted([card_data(k) for k in p.deck],
                           key=lambda d: (d["type"], d["name"])),
            "map": {
                "floors": [[{"type": n["type"], "edges": n["edges"]} for n in f]
                           for f in self.floors],
                "cur_floor": self.cur_floor, "cur_idx": self.cur_idx,
                "visited": self.visited, "reachable": self.reachable(),
            },
        }
        self.banner = None
        if cb:
            st["combat"] = {
                "label": cb.label, "turn": cb.turn + 1,
                "enemies": [{
                    "name": e.name, "hp": max(0, e.hp), "max_hp": e.max_hp,
                    "block": e.block, "alive": e.alive,
                    "statuses": status_data(e),
                    "intent": intent_data(e, p) if e.alive else None,
                } for e in cb.enemies],
                "hand": [card_data(k, cb.energy, i) for i, k in enumerate(cb.hand)],
                "draw": len(cb.draw_pile), "discard": len(cb.discard),
                "exhaust": len(cb.exhausted),
                "draw_pile": sorted([card_data(k) for k in cb.draw_pile],
                                    key=lambda d: (d["type"], d["name"])),
                "discard_pile": [card_data(k) for k in cb.discard],
                "exhaust_pile": [card_data(k) for k in cb.exhausted],
                "log": cb.log[-8:],
            }
        if self.reward:
            st["reward"] = self.reward
        if self.shop:
            st["shop"] = self.shop_state()
        if self.event:
            st["event"] = self.event
        if self.choose:
            st["choose"] = self.choose
        if self.treasure:
            st["treasure"] = self.treasure
        return st

    # ── action dispatch ──
    def act_on(self, a):
        t = a.get("type")
        if t == "new_run":
            self.new_run()
        elif t == "map":
            self.enter_node(a.get("idx", -1))
        elif t == "play":
            self.play_card(a.get("idx", -1), a.get("target"), a.get("exhaust"))
        elif t == "potion":
            self.use_potion(a.get("idx", -1), a.get("target"))
        elif t == "end_turn":
            self.end_turn()
        elif t == "reward":
            self.take_reward(a.get("idx"))
        elif t == "rest":
            self.rest()
        elif t == "smith":
            self.smith()
        elif t == "choose":
            self.resolve_choose(a.get("idx"))
        elif t == "shop_buy":
            self.shop_buy(a.get("what"), a.get("idx", 0))
        elif t == "shop_leave":
            self.to_map()
        elif t == "event_choose":
            self.choose_event(a.get("idx", -1))
        elif t == "event_done":
            self.finish_event()
        elif t == "treasure_done":
            self.to_map()
        return self.state()


# ────────────────────────────────────────────────────────────────── terminal ──
# The game lives in the browser, but the server keeps a terminal in the
# foreground.  If anything switches the terminal's mouse reporting on (a browser
# launcher poking the tty, or a leftover mode from an earlier program), every
# mouse move sends an escape sequence that the tty happily echoes back at us as
# gibberish like "35;80;24M".  Turn reporting off, and keep echo off while we run.
MOUSE_OFF = "".join("\033[?%dl" % m for m in (1000, 1002, 1003, 1004, 1005, 1006, 1015))


def _tty_fd():
    try:
        if sys.stdin.isatty() and sys.stdout.isatty():
            return sys.stdin.fileno()
    except (ValueError, OSError):
        pass
    return None


def _write_tty(text):
    with contextlib.suppress(Exception):
        if sys.stdout.isatty():  # never scribble escapes into a pipe or log file
            sys.stdout.write(text)
            sys.stdout.flush()


@contextlib.contextmanager
def quiet_terminal():
    """Silence mouse-report noise for as long as the server is in the foreground."""
    fd = _tty_fd()
    saved = None
    if fd is not None and termios is not None:
        with contextlib.suppress(termios.error, OSError):
            saved = termios.tcgetattr(fd)
            attrs = list(saved)
            attrs[3] &= ~termios.ECHO  # lflags; ISIG stays on so ctrl-c still works
            termios.tcsetattr(fd, termios.TCSADRAIN, attrs)
    _write_tty(MOUSE_OFF)
    try:
        yield
    finally:
        _write_tty(MOUSE_OFF)  # again: the browser launcher may have re-enabled it
        if saved is not None:
            with contextlib.suppress(termios.error, OSError):
                termios.tcsetattr(fd, termios.TCSADRAIN, saved)
                termios.tcflush(fd, termios.TCIFLUSH)  # drop queued mouse bytes


def open_browser(url):
    """webbrowser.open(), but with the launcher detached from our terminal.

    Popen inherits stdin/stdout/stderr, so `gio open` & friends (or a console
    browser fallback) can write escape sequences straight into our tty.
    """
    with contextlib.suppress(Exception):
        sys.stdout.flush()
        sys.stderr.flush()
        saved = [os.dup(fd) for fd in (0, 1, 2)]
        null = os.open(os.devnull, os.O_RDWR)
        try:
            for fd in (0, 1, 2):
                os.dup2(null, fd)
            webbrowser.open(url)
        finally:
            for fd, old in zip((0, 1, 2), saved):
                os.dup2(old, fd)
                os.close(old)
            os.close(null)


# ─────────────────────────────────────────────────────────────────── server ──
SESSION = Session()
LOCK = threading.Lock()


class Handler(BaseHTTPRequestHandler):
    server_version = "SpireOfAsh"

    def _send(self, code, body, ctype):
        if isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, obj):
        self._send(200, json.dumps(obj), "application/json")

    def do_GET(self):
        path = self.path.split("?")[0]
        if path in ("/", "/index.html"):
            try:
                with open(UI_FILE, encoding="utf-8") as f:
                    self._send(200, f.read(), "text/html; charset=utf-8")
            except OSError:
                self._send(500, f"Missing {UI_FILE}", "text/plain")
        elif path == "/state":
            with LOCK:
                self._json(SESSION.state())
        elif path == "/records":
            self._json(spire.load_records()[:10])
        else:
            self._send(404, "not found", "text/plain")

    def do_POST(self):
        if self.path.split("?")[0] != "/action":
            self._send(404, "not found", "text/plain")
            return
        n = int(self.headers.get("Content-Length") or 0)
        try:
            action = json.loads(self.rfile.read(n) or b"{}")
        except json.JSONDecodeError:
            self._send(400, "bad json", "text/plain")
            return
        with LOCK:
            try:
                self._json(SESSION.act_on(action))
            except Exception:  # never leave the browser hanging on an engine bug
                import traceback
                traceback.print_exc()
                self._send(500, "engine error", "text/plain")

    def log_message(self, *a):
        pass


def main():
    port = 8765
    for arg in sys.argv[1:]:
        if arg.isdigit():
            port = int(arg)
    srv = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    url = f"http://localhost:{port}"
    with quiet_terminal():
        print(f"\n  Spire of Ash — open {url} in your browser")
        print("  (ctrl-c here to stop the server)\n")
        if "--no-open" not in sys.argv:
            open_browser(url)
        try:
            srv.serve_forever()
        except KeyboardInterrupt:
            print("\n  The Spire waits.\n")
        finally:
            srv.server_close()


if __name__ == "__main__":
    main()
