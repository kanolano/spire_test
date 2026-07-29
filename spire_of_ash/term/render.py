"""Terminal presentation: ANSI colour, card boxes, the map.

Every escape code in the project lives here. The engine deals in plain text, so
nothing downstream has to strip ANSI back out of a log line the way the old web
layer did.
"""

import shutil
import sys

from ..balance import FLOORS_PER_ACT

ESC = "\033["
RESET = ESC + "0m"
BOLD, DIM = 1, 2
RED, GRN, YEL, BLU, MAG, CYN, WHT, GRY = 31, 32, 33, 34, 35, 36, 37, 90

TYPE_COLOR = {"ATTACK": RED, "SKILL": CYN, "POWER": MAG, "CURSE": GRY, "STATUS": GRY}
STATUS_COLOR = {
    "strength": RED, "dexterity": GRN, "vulnerable": MAG, "weak": BLU,
    "frail": BLU, "poison": GRN, "thorns": YEL, "ritual": RED,
    "metallicize": CYN, "demonform": RED, "barricade": CYN, "feelnopain": CYN,
    "rupture": RED, "juggernaut": YEL, "venombloom": GRN, "afterimage": CYN,
    "thousandcuts": RED, "envenom": GRN,
}
NODE_SYMBOLS = {
    "monster": ("M", RED), "elite": ("E", MAG), "event": ("?", CYN),
    "rest": ("R", GRN), "shop": ("$", YEL), "treasure": ("T", YEL), "boss": ("B", RED),
}
CARD_W = 21


def c(text, *codes):
    return "".join(ESC + str(x) + "m" for x in codes) + str(text) + RESET


def clear():
    sys.stdout.write(ESC + "2J" + ESC + "H")


def term_width():
    return max(60, shutil.get_terminal_size((100, 30)).columns)


def bar(cur, mx, width=14, color=GRN):
    cur = max(0, cur)
    filled = 0 if mx <= 0 else min(width, int(round(width * cur / mx)))
    return c("█" * filled, color) + c("░" * (width - filled), GRY)


def wrap(text, width):
    words, lines, cur = text.split(), [], ""
    for w in words:
        if len(cur) + len(w) + (1 if cur else 0) <= width:
            cur += (" " if cur else "") + w
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def prompt(msg):
    try:
        return input(msg).strip()
    except (EOFError, KeyboardInterrupt):
        print()
        sys.exit(0)


def pause(msg="  [enter] "):
    prompt(c(msg, GRY))


def status_line(statuses):
    """`statuses` is the (key, label, value) list from the engine."""
    return " ".join(c(f"{s['label']} {s['value']}", STATUS_COLOR.get(s["key"], WHT))
                    for s in statuses)


def card_box(card, index=None, energy=None, dim=False):
    """The list of lines making up one rendered card, from a card DTO."""
    inner = CARD_W - 2
    col = TYPE_COLOR.get(card["type"], WHT)
    playable = card["playable"] if energy is None else (
        card["playable"] and (card["cost"] == "X" or card["cost"] <= energy))
    if dim or not playable:
        col = GRY
    cost = str(card["cost"])
    head = (f"{index}." if index is not None else " ") + " " + card["name"]
    head = head[:inner - 4].ljust(inner - 4)
    lines = [c("┌" + "─" * inner + "┐", col),
             c("│", col) + c(head, WHT if playable else GRY) +
             c(f"[{cost}]", YEL if playable else GRY) + c("│", col),
             c("│", col) + c(card["type"].ljust(inner), col) + c("│", col),
             c("├" + "─" * inner + "┤", col)]
    body = wrap(card["desc"], inner - 2)[:4]
    for i in range(4):
        text = body[i] if i < len(body) else ""
        lines.append(c("│", col) + " " + text.ljust(inner - 2) + " " + c("│", col))
    lines.append(c("└" + "─" * inner + "┘", col))
    return lines


def print_cards(cards, energy=None, start=1, numbered=True):
    per_row = max(1, (term_width() - 2) // (CARD_W + 1))
    for i in range(0, len(cards), per_row):
        chunk = cards[i:i + per_row]
        boxes = [card_box(k, (start + i + j) if numbered else None, energy)
                 for j, k in enumerate(chunk)]
        for row in zip(*boxes):
            print(" " + " ".join(row))


def render_map(floors, cur_floor, cur_idx, visited):
    """visited: list of [floor, idx] already taken."""
    width = 44
    visited = {tuple(v) for v in visited}

    def xpos(f, i):
        return int((i + 0.5) * width / len(floors[f]))

    rows = []
    for f in range(len(floors) - 1, -1, -1):
        line = [" "] * (width + 4)
        for i, node in enumerate(floors[f]):
            sym, col = NODE_SYMBOLS[node["type"]]
            x = xpos(f, i)
            reachable = (f == cur_floor + 1 and
                         (cur_floor == -1 or i in floors[cur_floor][cur_idx]["edges"]))
            if (f, i) == (cur_floor, cur_idx):
                cell = c(sym, BOLD, WHT)
            elif (f, i) in visited:
                cell = c(sym, GRY)
            elif reachable:
                cell = c(sym, BOLD, col)
            else:
                cell = c(sym, col)
            line[x] = cell
            if reachable:
                line[min(width + 3, x + 1)] = c(chr(ord("a") + i), YEL)
        rows.append(f"{f + 1:>3} " + "".join(line))
        if f > 0:
            conn = [" "] * (width + 4)
            for i, node in enumerate(floors[f - 1]):
                x0 = xpos(f - 1, i)
                for t in node["edges"]:
                    x1 = xpos(f, t)
                    ch = "|" if x1 == x0 else ("\\" if x1 < x0 else "/")
                    xm = (x0 + x1) // 2
                    if 0 <= xm < len(conn):
                        conn[xm] = c(ch, GRY)
            rows.append("    " + "".join(conn))
    return rows


TITLE = r"""
   ███████╗██████╗ ██╗██████╗ ███████╗
   ██╔════╝██╔══██╗██║██╔══██╗██╔════╝
   ███████╗██████╔╝██║██████╔╝█████╗
   ╚════██║██╔═══╝ ██║██╔══██╗██╔══╝
   ███████║██║     ██║██║  ██║███████╗
   ╚══════╝╚═╝     ╚═╝╚═╝  ╚═╝╚══════╝
"""
