"""Seed helpers.

Runs are reproducible from a seed, which makes a shared daily challenge almost
free: everyone who plays on the same UTC date climbs the same Spire.
"""

import datetime
import hashlib

DAILY_SALT = "spire-of-ash-daily"


def daily_seed(day=None):
    """A stable 64-bit seed for one UTC date."""
    day = day or datetime.datetime.now(datetime.timezone.utc).date()
    digest = hashlib.sha256(f"{DAILY_SALT}:{day.isoformat()}".encode()).digest()
    return int.from_bytes(digest[:8], "big")


def daily_label(day=None):
    day = day or datetime.datetime.now(datetime.timezone.utc).date()
    return day.isoformat()
