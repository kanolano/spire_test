# Spire of Ash

A roguelike deckbuilder in the spirit of Slay the Spire. Pure Python standard
library — nothing to install, no build step, no JavaScript framework.

## Running

Browser (recommended):

```sh
python3 spire_web.py            # serves http://localhost:8765 and opens it
python3 spire_web.py 9000       # pick a port
python3 spire_web.py --no-open  # don't launch a browser
```

Terminal:

```sh
python3 spire.py
```

Requires Python 3.10+.

## How it plays

Pick a class, climb a 15-floor map per act, and fight your way to the act boss.
Combat is turn-based: spend energy to play cards from your hand, block what the
enemy telegraphs, and end your turn. Campfires heal or upgrade, shops sell cards,
relics and card removal, and `?` in-game lists every key binding.

The browser UI is fully keyboard-driven — number keys play cards, `a`–`d` pick
targets and map nodes, `e` ends the turn, `i` opens your deck.

## Layout

| File | Purpose |
| --- | --- |
| `spire.py` | Game engine plus the terminal UI |
| `spire_web.py` | HTTP server exposing the engine as JSON |
| `spire_ui.html` | Self-contained browser client |
| `spire_save.json` | Top-10 leaderboard (generated, git-ignored) |

## Status

This is the consolidated baseline. A refactor is underway to separate the engine
from terminal I/O, split the flat modules into a `spire_of_ash` package, support
multiple concurrent players with resumable runs, and add a test suite. See the
project plan for details.
