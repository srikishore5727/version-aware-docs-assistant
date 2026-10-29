"""Structured request logging and in-process metrics.

One JSON object per API request, plus a small counter that `/api/metrics`
exposes. Deliberately dependency-free: no Prometheus client, no log shipper.

Metrics are per process. With multiple workers each has its own counters; that
is fine for a single-instance demo and documented rather than hidden.
"""

from __future__ import annotations

import json
import logging
import threading
from dataclasses import dataclass, field

LOGGER_NAME = "vada"

_logger = logging.getLogger(LOGGER_NAME)
if not _logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("%(message)s"))
    _logger.addHandler(_handler)
    _logger.setLevel(logging.INFO)
    _logger.propagate = False


def format_event(endpoint: str, status: int, duration_ms: float, **extra) -> str:
    """Serialise one request event as a single JSON line."""
    payload = {
        "event": "request",
        "endpoint": endpoint,
        "status": status,
        "duration_ms": round(duration_ms, 2),
        **extra,
    }
    return json.dumps(payload, sort_keys=True)


def log_request(endpoint: str, status: int, duration_ms: float, **extra) -> None:
    _logger.info(format_event(endpoint, status, duration_ms, **extra))


@dataclass
class Metrics:
    """Counters for one process."""

    requests: int = 0
    answered: int = 0
    not_found: int = 0
    errors: int = 0
    total_ms: float = 0.0
    max_ms: float = 0.0
    slowest_endpoint: str = ""
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def record_request(self, endpoint: str, status: int, duration_ms: float) -> None:
        with self._lock:
            self.requests += 1
            self.total_ms += duration_ms
            if duration_ms > self.max_ms:
                self.max_ms = duration_ms
                self.slowest_endpoint = endpoint
            if status >= 500:
                self.errors += 1

    def record_outcome(self, status: str) -> None:
        with self._lock:
            if status == "answered":
                self.answered += 1
            elif status == "not_found":
                self.not_found += 1

    def snapshot(self) -> dict:
        with self._lock:
            average = self.total_ms / self.requests if self.requests else 0.0
            return {
                "requests": self.requests,
                "answered": self.answered,
                "not_found": self.not_found,
                "errors": self.errors,
                "avg_ms": round(average, 2),
                "max_ms": round(self.max_ms, 2),
                "slowest_endpoint": self.slowest_endpoint,
            }

    def reset(self) -> None:
        with self._lock:
            self.requests = 0
            self.answered = 0
            self.not_found = 0
            self.errors = 0
            self.total_ms = 0.0
            self.max_ms = 0.0
            self.slowest_endpoint = ""


metrics = Metrics()
