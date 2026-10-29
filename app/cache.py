"""Bounded in-process cache for answers.

The same handful of questions gets asked repeatedly ("how do I create a
user?"), and every miss costs an embedding call, a Chroma query, and a model
call. A small LRU removes that cost without adding Redis to a demo app.

The key includes the FTS5 file's mtime. Rebuilding the index therefore makes
old entries unreachable even in a long-running process, which is the one
invalidation case that matters here.
"""

from __future__ import annotations

import threading
from collections import OrderedDict
from pathlib import Path

DEFAULT_MAXSIZE = 128


def index_fingerprint(db_path: str | Path) -> int:
    """Cheap identity for the current index; 0 when it does not exist yet."""
    try:
        return Path(db_path).stat().st_mtime_ns
    except OSError:
        return 0


def cache_key(
    question: str,
    limit: int,
    version: str | None,
    doc_type: str | None,
    fingerprint: int = 0,
) -> tuple:
    """One key per distinct question *and* scope."""
    return (
        " ".join(question.lower().split()),
        int(limit),
        version or "",
        doc_type or "",
        int(fingerprint),
    )


class AnswerCache:
    """A thread-safe LRU of answer payloads."""

    def __init__(self, maxsize: int = DEFAULT_MAXSIZE) -> None:
        self.maxsize = max(0, int(maxsize))
        self._items: OrderedDict[tuple, dict] = OrderedDict()
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0

    @property
    def enabled(self) -> bool:
        return self.maxsize > 0

    def get(self, key: tuple) -> dict | None:
        if not self.enabled:
            return None

        with self._lock:
            value = self._items.get(key)
            if value is None:
                self._misses += 1
                return None
            self._items.move_to_end(key)
            self._hits += 1
            return value

    def set(self, key: tuple, value: dict) -> None:
        if not self.enabled:
            return

        with self._lock:
            self._items[key] = dict(value)
            self._items.move_to_end(key)
            while len(self._items) > self.maxsize:
                self._items.popitem(last=False)

    def clear(self) -> None:
        """Drop every entry and reset the counters."""
        with self._lock:
            self._items.clear()
            self._hits = 0
            self._misses = 0

    def stats(self) -> dict:
        with self._lock:
            lookups = self._hits + self._misses
            return {
                "size": len(self._items),
                "maxsize": self.maxsize,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": round(self._hits / lookups, 4) if lookups else 0.0,
            }
