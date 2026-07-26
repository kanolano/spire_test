"""The run leaderboard.

The old version wrote non-atomically and swallowed every `OSError`, so a failed
write lost data silently and a concurrent reader could see a half-written file.
Writes now go through a temp file plus `os.replace`, and the list is truncated in
exactly one place.
"""

import json
import os
import tempfile
import threading

from .. import balance as B

_LOCK = threading.Lock()

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_PATH = os.environ.get("SPIRE_RECORDS") or os.path.join(_PROJECT_ROOT,
                                                               "spire_save.json")


def load_records(path=DEFAULT_PATH):
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []
    return data if isinstance(data, list) else []


def _rank(record):
    return (-record.get("floors", 0), -record.get("act", 1))


def save_record(record, path=DEFAULT_PATH):
    """Add a run to the leaderboard and return the trimmed list.

    Raises OSError if the file cannot be written — callers decide whether that
    is worth surfacing, but it is no longer hidden.
    """
    with _LOCK:
        records = sorted(load_records(path) + [record], key=_rank)[:B.LEADERBOARD_SIZE]
        directory = os.path.dirname(path) or "."
        fd, tmp = tempfile.mkstemp(dir=directory, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(records, f, indent=1)
            os.replace(tmp, path)
        except BaseException:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise
        return records
