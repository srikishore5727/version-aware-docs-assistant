"""Tests for embeddings, the Chroma store, and hybrid fusion."""

from pathlib import Path

import pytest

from app.config import Settings, get_settings
from app.embeddings import GeminiEmbeddings, HashingEmbeddings, get_embedder
from app.ingest import load_chunks
from app.retriever import _fuse, build_index, hybrid_search
from app.search import SearchResult
from app.vector_store import VectorStore

CORPUS = Path(__file__).resolve().parents[1] / "corpus"


@pytest.fixture(scope="module")
def chunks():
    return load_chunks(CORPUS)


@pytest.fixture()
def store(tmp_path: Path) -> VectorStore:
    return VectorStore(tmp_path / "chroma")


@pytest.fixture()
def settings(tmp_path: Path) -> Settings:
    return Settings(
        gemini_api_key="",
        embedding_model="gemini-embedding-001",
        llm_model="test",
        embeddings_mode="hash",
        corpus_dir=CORPUS,
        db_path=tmp_path / "vada.db",
        chroma_dir=tmp_path / "chroma",
    )


# --- embeddings -----------------------------------------------------------


def test_hashing_embeddings_are_deterministic_and_normalised() -> None:
    embedder = HashingEmbeddings()

    first = embedder.embed_query("cursor pagination")
    second = embedder.embed_query("cursor pagination")

    assert first == second
    assert len(first) == embedder.dimensions
    assert pytest.approx(sum(value * value for value in first), rel=1e-6) == 1.0


def test_gemini_embeddings_require_a_key() -> None:
    with pytest.raises(ValueError):
        GeminiEmbeddings(api_key="")


def test_get_embedder_falls_back_to_hashing_without_a_key() -> None:
    assert get_embedder("gemini", "", "model").name == "hash"
    assert get_embedder("hash", "key", "model").name == "hash"


# --- vector store ---------------------------------------------------------


def test_vector_store_add_and_query(chunks, store: VectorStore) -> None:
    embedder = HashingEmbeddings()
    sample = chunks[:10]

    store.add(
        ids=[chunk.chunk_id for chunk in sample],
        texts=[chunk.text for chunk in sample],
        vectors=embedder.embed_documents([chunk.text for chunk in sample]),
        metadatas=[{"doc_id": chunk.doc_id, "version": chunk.version} for chunk in sample],
    )

    hits = store.query(embedder.embed_query("cursor pagination"), n_results=3)

    assert len(hits) == 3
    assert hits[0]["similarity"] >= hits[-1]["similarity"]
    assert hits[0]["metadata"]["doc_id"]


def test_empty_store_returns_no_hits(store: VectorStore) -> None:
    assert store.query([0.0] * 256, n_results=5) == []


# --- index build ----------------------------------------------------------


def test_build_index_creates_both_indexes(chunks, settings, store) -> None:
    counts = build_index(settings, store=store, embedder=HashingEmbeddings())

    assert counts["chunks"] == len(chunks)
    assert counts["keyword"] == len(chunks)
    assert counts["vectors"] == len(chunks)
    assert settings.db_path.exists()


# --- fusion ---------------------------------------------------------------


def _result(chunk_id: str, score: float = 0.0) -> SearchResult:
    return SearchResult(
        chunk_id=chunk_id,
        doc_id=chunk_id.split("::")[0],
        title="Title",
        doc_type="api-reference",
        version="v3",
        status="current",
        source_url="https://docs.example/x",
        last_updated="2026-10-01",
        section="Section",
        text="text",
        score=score,
    )


def test_fusion_marks_sources() -> None:
    keyword = [_result("a::0"), _result("b::0")]
    vector = [
        {"chunk_id": "b::0", "text": "text", "metadata": {"doc_id": "b", "title": "T", "doc_type": "changelog", "version": "v2", "status": "superseded", "source_url": "u", "last_updated": "d", "section": "s"}, "similarity": 0.9},
        {"chunk_id": "c::0", "text": "text", "metadata": {"doc_id": "c", "title": "T", "doc_type": "changelog", "version": "v2", "status": "superseded", "source_url": "u", "last_updated": "d", "section": "s"}, "similarity": 0.8},
    ]

    fused = _fuse(keyword, vector, limit=5)
    by_id = {item.chunk_id: item for item in fused}

    assert by_id["a::0"].matched_by == "keyword"
    assert by_id["b::0"].matched_by == "both"
    assert by_id["c::0"].matched_by == "vector"


def test_fusion_ranks_agreement_first() -> None:
    keyword = [_result("only-kw"), _result("shared")]
    vector = [
        {"chunk_id": "shared", "text": "t", "metadata": {"doc_id": "d", "title": "T", "doc_type": "x", "version": "v3", "status": "current", "source_url": "u", "last_updated": "d", "section": "s"}, "similarity": 0.9},
        {"chunk_id": "only-vec", "text": "t", "metadata": {"doc_id": "d", "title": "T", "doc_type": "x", "version": "v3", "status": "current", "source_url": "u", "last_updated": "d", "section": "s"}, "similarity": 0.8},
    ]

    assert _fuse(keyword, vector, limit=3)[0].chunk_id == "shared"


def test_fusion_respects_limit() -> None:
    assert len(_fuse([_result("a::0"), _result("b::0")], [], limit=1)) == 1


# --- end to end -----------------------------------------------------------


def test_hybrid_search_returns_cited_results(settings, store) -> None:
    build_index(settings, store=store, embedder=HashingEmbeddings())

    results = hybrid_search(
        "how do I paginate users",
        limit=5,
        settings=settings,
        store=store,
        embedder=HashingEmbeddings(),
    )

    assert results
    assert results[0].version in {"v1", "v2", "v3"}
    assert results[0].source_url.startswith("https://")
    assert results[0].matched_by in {"keyword", "vector", "both"}


def test_hybrid_search_without_vectors_still_works(tmp_path: Path) -> None:
    config = Settings(
        gemini_api_key="",
        embedding_model="",
        llm_model="test",
        embeddings_mode="off",
        corpus_dir=CORPUS,
        db_path=tmp_path / "vada.db",
        chroma_dir=tmp_path / "chroma",
    )
    from app.search import reindex

    reindex(CORPUS, config.db_path)

    results = hybrid_search("cursor", limit=3, settings=config)

    assert results
    assert all(item.matched_by == "keyword" for item in results)


def test_settings_read_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VADA_EMBEDDINGS", "off")
    monkeypatch.setenv("VADA_DB_PATH", "custom/index.db")

    settings = get_settings()

    assert settings.embeddings_mode == "off"
    assert settings.vectors_enabled is False
    assert str(settings.db_path).endswith("index.db")
