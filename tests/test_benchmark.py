"""Tests for the latency benchmark (Day 19)."""

from pathlib import Path
from types import SimpleNamespace

from app.benchmark import benchmark, percentile
from app.config import Settings

ROOT = Path(__file__).resolve().parents[1]

CASES = [
    {"id": "a", "question": "q1", "expected_doc_ids": ["api-users-list"]},
    {"id": "b", "question": "q2", "expected_doc_ids": ["api-auth-tokens"]},
]


def settings(tmp_path: Path, cache_size: int = 8) -> Settings:
    return Settings(
        gemini_api_key="",
        embedding_model="",
        llm_model="test",
        embeddings_mode="off",
        corpus_dir=ROOT / "corpus",
        db_path=tmp_path / "vada.db",
        chroma_dir=tmp_path / "chroma",
        cache_size=cache_size,
    )


def _generate(question, chunks, **kwargs):
    return SimpleNamespace(to_dict=lambda: {"status": "not_found"})


def test_percentile_uses_nearest_rank() -> None:
    assert percentile([], 0.5) == 0.0
    assert percentile([10], 0.95) == 10.0
    assert percentile([1, 2, 3, 4], 0.5) == 2.0
    assert percentile([1, 2, 3, 4], 0.95) == 4.0


def test_second_round_hits_the_cache(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("app.benchmark.ensure_ready", lambda *args, **kwargs: None)

    report = benchmark(
        settings=settings(tmp_path),
        rounds=2,
        cases=CASES,
        retrieve=lambda *args, **kwargs: [],
        generate=_generate,
    )

    assert report["cases"] == 2
    assert report["requests"] == 4
    assert report["hits"] == 2
    assert report["hit_rate"] == 0.5
    assert report["cold_p50_ms"] >= 0.0
    assert report["warm_p50_ms"] >= 0.0


def test_disabled_cache_never_hits(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("app.benchmark.ensure_ready", lambda *args, **kwargs: None)

    report = benchmark(
        settings=settings(tmp_path, cache_size=0),
        rounds=2,
        cases=CASES,
        retrieve=lambda *args, **kwargs: [],
        generate=_generate,
    )

    assert report["hits"] == 0
    assert report["hit_rate"] == 0.0
