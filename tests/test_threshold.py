"""Tests for the relevance floor (Day 11).

The floor only applies to calibrated embeddings, so these tests inject a fake
embedder and store with known similarities instead of relying on the hashing
fallback's arbitrary numbers.
"""

from pathlib import Path

import pytest

from app.config import Settings
from app.embeddings import HashingEmbeddings
from app.retriever import MIN_SIMILARITY, hybrid_search
from app.search import reindex

CORPUS = Path(__file__).resolve().parents[1] / "corpus"


class FakeGemini:
    """Calibrated embedder with a fixed query vector."""

    name = "gemini"
    dimensions = 768
    calibrated = True

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [[0.0] * self.dimensions for _ in texts]

    def embed_query(self, text: str) -> list[float]:
        return [0.0] * self.dimensions


class FakeStore:
    """Vector store that returns a prepared list of hits."""

    def __init__(self, similarities: list[float]) -> None:
        self._hits = [
            {
                "chunk_id": f"doc-{index}::0",
                "text": "text",
                "metadata": {
                    "doc_id": f"doc-{index}",
                    "title": f"Title {index}",
                    "doc_type": "api-reference",
                    "version": "v3",
                    "status": "current",
                    "source_url": "https://docs.example/x",
                    "last_updated": "2026-10-01",
                    "section": "Section",
                },
                "similarity": similarity,
            }
            for index, similarity in enumerate(similarities)
        ]

    def count(self) -> int:
        return len(self._hits)

    def query(self, vector, n_results: int = 10, where=None) -> list[dict]:
        return self._hits[:n_results]


@pytest.fixture()
def settings(tmp_path: Path) -> Settings:
    config = Settings(
        gemini_api_key="",
        embedding_model="gemini-embedding-001",
        llm_model="test",
        embeddings_mode="gemini",
        corpus_dir=CORPUS,
        db_path=tmp_path / "vada.db",
        chroma_dir=tmp_path / "chroma",
    )
    reindex(CORPUS, config.db_path)
    return config


def test_the_floor_sits_between_the_two_measured_groups() -> None:
    assert 0.59 < MIN_SIMILARITY < 0.63


def test_an_out_of_scope_question_returns_nothing(settings: Settings) -> None:
    results = hybrid_search(
        "banana smoothie recipe",
        settings=settings,
        store=FakeStore([0.55, 0.53, 0.51]),
        embedder=FakeGemini(),
    )

    assert results == []


def test_a_stray_keyword_hit_cannot_rescue_an_out_of_scope_question(settings: Settings) -> None:
    # "write" appears in the corpus, so BM25 would happily return chunks.
    results = hybrid_search(
        "write me a poem about the sea",
        settings=settings,
        store=FakeStore([0.55, 0.54, 0.52]),
        embedder=FakeGemini(),
    )

    assert results == []


def test_weak_vector_neighbours_are_dropped_but_strong_ones_survive(settings: Settings) -> None:
    results = hybrid_search(
        "pagination",
        settings=settings,
        store=FakeStore([0.74, 0.61, 0.58]),
        embedder=FakeGemini(),
    )

    ids = {item.chunk_id for item in results}
    assert "doc-0::0" in ids
    assert "doc-1::0" in ids
    assert "doc-2::0" not in ids


def test_the_floor_does_not_apply_to_uncalibrated_embeddings(settings: Settings) -> None:
    results = hybrid_search(
        "pagination",
        settings=settings,
        store=FakeStore([0.27, 0.24, 0.20]),
        embedder=HashingEmbeddings(),
    )

    assert results
    assert any(item.matched_by in {"vector", "both"} for item in results)


def test_a_vector_failure_still_returns_keyword_results(settings: Settings) -> None:
    class BrokenStore(FakeStore):
        def query(self, vector, n_results: int = 10, where=None):
            raise RuntimeError("chroma is down")

    results = hybrid_search(
        "pagination",
        settings=settings,
        store=BrokenStore([]),
        embedder=FakeGemini(),
    )

    assert results
    assert all(item.matched_by == "keyword" for item in results)
