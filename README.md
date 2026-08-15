# Spire of Ash

A roguelike deckbuilder in the spirit of Slay the Spire. The engine and server
are pure Python standard library — **playing it needs nothing but Python 3.10+**.

## Running

Browser:

```sh
python3 -m spire_of_ash.web             # serves http://localhost:8765 and opens it
python3 -m spire_of_ash.web 9000        # pick a port
python3 -m spire_of_ash.web --no-open   # don't launch a browser
```

Terminal:

```sh
python3 -m spire_of_ash.term
python3 -m spire_of_ash.term --seed 42  # replay a reproducible run
python3 -m spire_of_ash.term --daily    # today's shared seed
```

Runs are seeded, so a seed is a shareable challenge. The browser client has a
**Daily climb** toggle on the character-select screen; everyone who plays on the
same UTC date gets the same Spire.

Requires Python 3.10+. Installing the package (`pip install -e .`) also gives you
`spire` and `spire-web` commands.

## Tests

```sh
python3 -m unittest discover -s tests
```

No dependencies needed. `pytest` works too if you have it.

## How it plays

Pick a class, climb a 15-floor map per act, and fight your way to the act boss.
Combat is turn-based: spend energy to play cards from your hand, block what the
enemy telegraphs, and end your turn. Campfires heal, upgrade or purge, shops sell cards,
relics and card removal, and `?` in-game lists every key binding.

The browser UI is fully keyboard-driven — number keys play cards, `a`–`d` pick
targets and map nodes, `e` ends the turn, `i` opens your deck.

## Architecture

The engine is pure: it never reads stdin and never prints. Both front-ends are
clients of the same state machine, which is what keeps them from drifting apart.

```
run.state()        a snapshot of engine state — no side effects
run.apply(action)  advance the machine; raises InvalidAction if refused
run.pending        what the run is waiting for right now
```

| Path | Purpose |
| --- | --- |
| `spire_of_ash/engine/` | Rules: cards, combatants, combat, the `Run` state machine, map generation |
| `spire_of_ash/content/` | Data tables: cards, monsters, relics, potions, events, classes |
| `spire_of_ash/balance.py` | Every tuning number, in one place |
| `spire_of_ash/web/` | HTTP server, per-session runs, view model, built client |
| `spire_of_ash/term/` | Terminal client and all ANSI rendering |
| `client/` | Browser client source (TypeScript). Only needed to *change* the UI |
| `tests/` | Rules, flow, persistence, content integrity and HTTP tests |

## Working on the browser client

`spire_of_ash/web/static/` is build output and is committed, which is why
running the game needs no toolchain. Editing the UI does:

```sh
cd client
npm install
npm run dev      # http://localhost:5173, hot reload, proxies the API to 8765
npm run build    # typecheck, then rebuild spire_of_ash/web/static
```

Run `python3 -m spire_of_ash.web` alongside `npm run dev` — the dev server
proxies `/state`, `/action` and friends to it. **Commit the rebuilt `static/`
along with your source change**, or players get the previous UI.

The build also emits `static/art-manifest.json`, listing every sprite the
client can draw. `tests/test_content.py` checks it against the content tables,
so a monster added without art fails the suite rather than quietly rendering as
a generic blob.

Where a card needs a choice the player has to make (True Grit+ picking a card to
exhaust), the client sends that choice with the action — `Card.requires` says
which. The engine never blocks waiting for input.

## Adding content

Everything is a table entry. A relic is one row plus whichever hooks it wants:

```python
"oathkeeper": dict(
    name="Oathkeeper", desc="Heal 3 HP whenever an enemy dies.",
    on_kill=lambda cb, enemy: cb.heal(cb.player, 3)),
```

Hooks: `on_pickup`, `on_combat_start`, `on_turn_start`, `on_turn_end`,
`on_combat_end`, `on_attack`, `on_card_played`, `on_exhaust`, `on_kill`,
`draw_bonus`. Cards carry an `fx(combat, card, target)`; events return their text
and may ask for a follow-up picker (`remove`, `upgrade`, `duplicate`).

An event handler also needs a `@preview("…")` line saying what the option costs
and grants — the label is flavour, and a handler cannot be dry-run to find out,
since it mutates the player and draws from `run.rng` in the same pass. Statuses
declare their own `(label, name, description)` in `spire_of_ash/statuses.py`, and
both clients show the description on hover.

`tests/test_content.py` walks every table, so a card key typo'd into a class pool
fails the suite instead of crashing a run on a seed you cannot reproduce.

Runs are seeded and serialisable, so they are reproducible, resumable across a
server restart, and testable.
