"""Latency benchmark for retrieval plus answer assembly.

Runs the 30 golden questions twice: the first pass fills the answer cache, the
second should hit it. Generation is stubbed with a valid ``[1]`` citation, so
this measures retrieval, citation validation, and cache overhead without
spending model quota or requiring a network connection.

Run it with::

    python -m app.benchmark
    python -m app.benchmark --rounds 5 --limit 3
"""

from __future__ import annotations

import json
import math
import time

from app.answer import generate_answer
from app.cache import AnswerCache, cache_key, index_fingerprint
from app.config import Settings, get_settings
from app.evaluate import load_golden_set
from app.retriever import ensure_ready, hybrid_search, normalize_doc_type, normalize_version

STUB_ANSWER = "According to the retrieved documentation, see [1]."
DEFAULT_ROUNDS = 2


def percentile(values: list[float], fraction: float) -> float:
    """Nearest-rank percentile, 0.0 for an empty sample."""
    if not values:
        return 0.0
    fraction = min(max(fraction, 0.0), 1.0)
    ordered = sorted(values)
    rank = max(0, math.ceil(fraction * len(ordered)) - 1)
    return round(ordered[min(rank, len(ordered) - 1)], 2)


def _stub(messages: list[dict]) -> str:
    return STUB_ANSWER


def benchmark(
    settings: Settings | None = None,
    rounds: int = DEFAULT_ROUNDS,
    limit: int = 5,
    retrieve=hybrid_search,
    generate=generate_answer,
    cases: list[dict] | None = None,
) -> dict:
    """Score retrieval and cache behaviour over the golden set."""
    config = settings or get_settings()
    ensure_ready(config)

    cases = cases if cases is not None else load_golden_set()
    rounds = max(1, int(rounds))
    fingerprint = index_fingerprint(config.db_path)
    cache = AnswerCache(config.cache_size)

    cold: list[float] = []
    warm: list[float] = []
    samples: list[float] = []
    hits = 0

    for round_index in range(rounds):
        for case in cases:
            version = normalize_version(case.get("version"))
            kind = normalize_doc_type(case.get("doc_type"))
            key = cache_key(case["question"], limit, version, kind, fingerprint)

            started = time.perf_counter()
            value = cache.get(key)
            if value is None:
                chunks = retrieve(
                    case["question"],
                    limit=limit,
                    settings=config,
                    version=version,
                    doc_type=kind,
                )
                answer = generate(
                    case["question"],
                    chunks,
                    settings=config,
                    completer=_stub,
                )
                cache.set(key, answer.to_dict())
            else:
                hits += 1
            elapsed = (time.perf_counter() - started) * 1000

            samples.append(elapsed)
            (cold if round_index == 0 else warm).append(elapsed)

    requests = rounds * len(cases)
    return {
        "cases": len(cases),
        "rounds": rounds,
        "requests": requests,
        "hits": hits,
        "hit_rate": round(hits / requests, 4) if requests else 0.0,
        "cold_p50_ms": percentile(cold, 0.50),
        "cold_p95_ms": percentile(cold, 0.95),
        "warm_p50_ms": percentile(warm, 0.50),
        "warm_p95_ms": percentile(warm, 0.95),
        "p50_ms": percentile(samples, 0.50),
        "p95_ms": percentile(samples, 0.95),
        "generation": "stub (no model call)",
    }


def _main() -> None:  # pragma: no cover - CLI
    import argparse

    parser = argparse.ArgumentParser(description="Benchmark retrieval and the answer cache.")
    parser.add_argument("--rounds", type=int, default=DEFAULT_ROUNDS, help="passes over the golden set")
    parser.add_argument("--limit", type=int, default=5, help="chunks retrieved per question")
    args = parser.parse_args()

    report = benchmark(rounds=args.rounds, limit=args.limit)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":  # pragma: no cover - CLI
    _main()
