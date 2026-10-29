"""Tests for the golden-set evaluation harness."""

import json
from pathlib import Path

import pytest

from app.config import Settings
from app.evaluate import check_threshold, evaluate, first_hit_rank, load_golden_set
from app.ingest import load_chunks
from app.search import SearchResult

ROOT = Path(__file__).resolve().parents[1]
GOLDEN = ROOT / "eval" / "golden_set.json"
CORPUS = ROOT / "corpus"


@pytest.fixture()
def settings(tmp_path: Path) -> Settings:
    return Settings(
        gemini_api_key="",
        embedding_model="",
        llm_model="test",
        embeddings_mode="hash",
        corpus_dir=CORPUS,
        db_path=tmp_path / "vada.db",
        chroma_dir=tmp_path / "chroma",
    )


def _result(doc_id: str) -> SearchResult:
    return SearchResult(
        chunk_id=f"{doc_id}::0",
        doc_id=doc_id,
        title="T",
        doc_type="api-reference",
        version="v3",
        status="current",
        source_url="u",
        last_updated="d",
        section="s",
        text="t",
        score=1.0,
    )


def test_golden_set_has_thirty_unique_cases() -> None:
    cases = load_golden_set(GOLDEN)

    assert len(cases) == 30
    assert len({case["id"] for case in cases}) == 30
    assert all(case["question"].strip() for case in cases)


def test_every_expected_document_exists_in_the_corpus() -> None:
    known = {chunk.doc_id for chunk in load_chunks(CORPUS)}
    expected = {doc for case in load_golden_set(GOLDEN) for doc in case["expected_doc_ids"]}

    assert expected - known == set()


def test_duplicate_ids_are_rejected(tmp_path: Path) -> None:
    path = tmp_path / "bad.json"
    path.write_text(
        json.dumps(
            {
                "cases": [
                    {"id": "a", "question": "q", "expected_doc_ids": ["x"]},
                    {"id": "a", "question": "q", "expected_doc_ids": ["x"]},
                ]
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError):
        load_golden_set(path)


def test_first_hit_rank_uses_the_earliest_expected_document() -> None:
    results = [_result("other"), _result("b"), _result("a")]

    assert first_hit_rank(results, ["a", "b"]) == 2
    assert first_hit_rank(results, ["missing"]) is None


def test_a_perfect_retriever_scores_one(settings: Settings) -> None:
    cases = [
        {"id": "one", "question": "q1", "expected_doc_ids": ["api-users-list"]},
        {"id": "two", "question": "q2", "expected_doc_ids": ["api-auth-tokens"]},
    ]

    def perfect(question, **kwargs):
        expected = next(case["expected_doc_ids"] for case in cases if case["question"] == question)
        return [_result(expected[0])]

    report = evaluate(settings, cases=cases, retrieve=perfect)

    assert report["recall"] == 1.0
    assert report["mrr"] == 1.0
    assert report["misses"] == []


def test_real_retrieval_clears_the_recall_target(settings: Settings) -> None:
    report = evaluate(settings)

    assert report["recall"] >= 0.85, report["misses"]


def test_threshold_helper_accepts_a_pass_and_rejects_a_miss() -> None:
    assert check_threshold({"recall": 0.9}, 0.85) is True
    assert check_threshold({"recall": 0.85}, 0.85) is True
    assert check_threshold({"recall": 0.84}, 0.85) is False
    assert check_threshold({}, 0.85) is False
