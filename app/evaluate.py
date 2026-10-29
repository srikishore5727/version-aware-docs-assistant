"""Golden-set evaluation for retrieval.

Thirty question -> expected-document pairs, scored with recall@k and MRR. No
model call, so this runs offline in CI and costs nothing.

A case counts as a hit when a retrieved chunk's ``doc_id`` is in
``expected_doc_ids``. The first such rank feeds MRR. Expected lists may name
more than one document: a question about a field rename is answered by both the
API reference and the migration guide.

Run it with::

    python -m app.evaluate
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

from app.config import Settings, get_settings
from app.retriever import ensure_ready, hybrid_search
from app.search import SearchResult

DEFAULT_GOLDEN_SET = Path("eval/golden_set.json")
DEFAULT_REPORT = Path("data/eval/report.json")
DEFAULT_LIMIT = 5

# CI fails below this. The real Gemini baseline is 1.00; the hashing baseline
# used in CI is lower, so leave a margin rather than pinning the exact number.
MIN_RECALL_TARGET = 0.85

Retriever = Callable[..., list[SearchResult]]


def load_golden_set(path: str | Path = DEFAULT_GOLDEN_SET) -> list[dict]:
    """Read and validate the golden set."""
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    cases = payload["cases"] if isinstance(payload, dict) else payload

    seen: set[str] = set()
    for case in cases:
        missing = {"id", "question", "expected_doc_ids"} - set(case)
        if missing:
            raise ValueError(f"golden case {case.get('id', '?')} is missing {sorted(missing)}")
        if case["id"] in seen:
            raise ValueError(f"duplicate golden case id: {case['id']}")
        seen.add(case["id"])
        if not case["expected_doc_ids"]:
            raise ValueError(f"golden case {case['id']} has no expected documents")

    return cases


def first_hit_rank(results: list[SearchResult], expected: list[str]) -> int | None:
    """1-based rank of the first result from an expected document."""
    for rank, result in enumerate(results, start=1):
        if result.doc_id in expected:
            return rank
    return None


def evaluate(
    settings: Settings | None = None,
    cases: list[dict] | None = None,
    limit: int = DEFAULT_LIMIT,
    retrieve: Retriever = hybrid_search,
) -> dict:
    """Score the retriever against the golden set."""
    config = settings or get_settings()
    golden = cases if cases is not None else load_golden_set()
    ensure_ready(config)

    rows: list[dict] = []
    hits = 0
    reciprocal_rank = 0.0

    for case in golden:
        results = retrieve(
            case["question"],
            limit=limit,
            settings=config,
            version=case.get("version"),
            doc_type=case.get("doc_type"),
        )
        rank = first_hit_rank(results, case["expected_doc_ids"])
        if rank is not None:
            hits += 1
            reciprocal_rank += 1.0 / rank

        rows.append(
            {
                "id": case["id"],
                "question": case["question"],
                "rank": rank,
                "expected": case["expected_doc_ids"],
                "got": [result.doc_id for result in results],
            }
        )

    total = len(golden) or 1
    return {
        "cases": len(golden),
        "limit": limit,
        "recall": round(hits / total, 4),
        "mrr": round(reciprocal_rank / total, 4),
        "misses": [row for row in rows if row["rank"] is None],
        "results": rows,
    }


def write_report(report: dict, path: str | Path = DEFAULT_REPORT) -> Path:
    """Persist a report for CI artefacts."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return target


def check_threshold(report: dict, minimum: float = MIN_RECALL_TARGET) -> bool:
    """True when retrieval clears the recall target."""
    return float(report.get("recall", 0.0)) >= minimum


def _main() -> None:  # pragma: no cover - CLI
    import argparse

    parser = argparse.ArgumentParser(description="Score retrieval against the golden set.")
    parser.add_argument(
        "--min-recall",
        type=float,
        default=None,
        help="exit 1 when recall is below this value (e.g. 0.85)",
    )
    args = parser.parse_args()

    report = evaluate()
    print(
        f"cases: {report['cases']}  recall@{report['limit']}: {report['recall']:.2f}  "
        f"mrr: {report['mrr']:.2f}"
    )
    for miss in report["misses"]:
        print(f"  MISS {miss['id']}: {miss['question']}")
        print(f"       expected {miss['expected']} got {miss['got']}")
    print(f"report: {write_report(report)}")

    if args.min_recall is not None and not check_threshold(report, args.min_recall):
        raise SystemExit(
            f"FAIL: recall {report['recall']:.2f} is below the {args.min_recall:.2f} target"
        )


if __name__ == "__main__":  # pragma: no cover - CLI
    _main()
