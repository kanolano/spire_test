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

## Balance

The suite says whether the rules are obeyed. It says nothing about whether the
game is *fair*, and seven classes across 256 cards is well past what anyone can
hold in their head. So there is a simulator:

```sh
python3 -m spire_of_ash.sim                      # 60 runs per class
python3 -m spire_of_ash.sim --runs 500           # tighter numbers
python3 -m spire_of_ash.sim --classes hexbinder  # one climber
python3 -m spire_of_ash.sim --json out.json      # raw rows, for a diff
```

It plays the real engine through the same `apply`/`state` machine both clients
use, so it cannot drift from the game. Every run is seeded from `--seed` plus
the run index, which makes a report reproducible and two reports comparable run
for run.

`GreedyPolicy` is a **floor, not a ceiling**: it reads damage and Block off the
card text, kills what it can reach and blocks what it cannot, and never plans a
turn ahead. Its absolute win rate is therefore not "the" win rate. What it is
good for is comparison — between classes, between acts, and between two commits
— because the same crude player meets all of them. `--policy random` is the
scripted flailer the tests use, kept as the true floor.

`--fail-outside 25,65` exits non-zero if any class's win rate leaves that band,
so a content change that quietly guts a climber can fail CI rather than ship.

Numbers move when the game or the policy changes, so treat any figure here as a
timestamp rather than a fact. What the first 2,100-run report found:

- **The act-1 boss is where runs end.** 57% of runs finish in act 1, and the
  two act-1 bosses account for 37% of all deaths.
- **The two act-1 bosses are not interchangeable.** The draw is a clean 50/50,
  but The Guardian kills 554 runs to the Slime Boss's 231 — so which boss the
  seed hands you matters more than anything you do about it.
- **More cards is better here**, which is the opposite of the genre's usual
  advice. Capping the deck at 22 cards cost the Emberbrewer two thirds of its
  win rate, so card rewards are not the trap they are in the games this one is
  in the spirit of.

## How it plays

Pick a class, climb a 15-floor map per act, and fight your way to the act boss.
Combat is turn-based: spend energy to play cards from your hand, block what the
enemy telegraphs, and end your turn. Campfires heal, upgrade or purge, shops sell cards,
relics and card removal, and `?` in-game lists every key binding.

The browser UI is fully keyboard-driven — number keys play cards, `a`–`d` pick
targets and map nodes, `e` ends the turn, `i` opens your deck.

## The climbers

Seven classes, each with its own deck, starting relic and card pools. What
separates them is the resource they play around:

| Class | HP | Plays around |
| --- | --- | --- |
| The Sentinel | 75 | Strength and Block, and brute arithmetic |
| The Ashwalker | 68 | Poison, Weak and a great many small cuts |
| The Stormbound | 70 | Coil and Frost, banked and spent at end of turn, scaled by Focus |
| The Penitent | 72 | Stances — Wrath doubles damage dealt *and* taken, Calm refunds the energy you spend leaving it, ten Mantra spills into Divinity |
| The Gravewright | 68 | The exhaust pile, as fuel rather than a graveyard |
| The Emberbrewer | 66 | Potions brewed mid-fight, into a belt of its own size |
| The Hexbinder | 66 | Weak, Vulnerable and Frail as the whole win condition |

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

Two query flags exist for working on the look, in dev and in the built client
alike:

| Flag | What it does |
|---|---|
| `?art=1` | The contact sheet: every creature, map icon and set piece side by side. Judging art one screen at a time, by playing to it, is how a set drifts apart |
| `?motion=off` | Takes the same branch `prefers-reduced-motion` takes, so the reduced path can be driven and tested rather than assumed |

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

A class is one row in `content/classes.py` — HP, energy, starting deck, starting
relic and three card pools, plus an optional `potions` if it wants a belt of its
own size. Nothing outside that table is class-aware, so the clients pick up a new
climber with no change at all. A class that wants a mechanic the engine cannot
express yet needs one more thing: a status in `statuses.py` and whichever hook
fires it, which is how stances, Coil and the exhaust triggers arrived.

`tests/test_content.py` walks every table, so a card key typo'd into a class pool
fails the suite instead of crashing a run on a seed you cannot reproduce, and
`tests/test_classes.py` goes further and plays every card in every pool, upgraded
and not, against a live enemy — a typo inside an `fx` lambda is otherwise
invisible until someone draws that card.

Runs are seeded and serialisable, so they are reproducible, resumable across a
server restart, and testable.
