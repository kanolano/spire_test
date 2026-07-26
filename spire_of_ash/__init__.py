"""Spire of Ash — a roguelike deckbuilder.

The engine (`spire_of_ash.engine`) is pure: it never reads stdin or writes to
stdout. Both front-ends drive the same `Run` state machine — the terminal client
in `spire_of_ash.term` and the HTTP server in `spire_of_ash.web`.
"""

__version__ = "0.2.0"
