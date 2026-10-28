"""Tests for the Day 8 version filter."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.embeddings import HashingEmbeddings
from app.main import app
from app.retriever import build_index, hybrid_search, normalize_version
from app.search import QueryError, reindex
from app.search import search as keyword_search
from app.vector_store import VectorStore

CORPUS = Path(__file__).resolve().parents[1] / "corpus"


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


@pytest.fixture()
def store(tmp_path: Path) -> VectorStore:
    return VectorStore(tmp_path / "chroma")


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("VADA_CORPUS_DIR", str(CORPUS))
    return TestClient(app)


# --- validation -----------------------------------------------------------


def test_blank_version_means_all_versions() -> None:
    assert normalize_version(None) is None
    assert normalize_version("") is None
    assert normalize_version("   ") is None


def test_version_is_case_insensitive() -> None:
    assert normalize_version("V3") == "v3"


def test_unknown_version_is_rejected() -> None:
    with pytest.raises(QueryError) as error:
        normalize_version("v9")

    assert "unknown version" in str(error.value)
    assert "v3" in str(error.value)


# --- keyword retriever ----------------------------------------------------


def test_keyword_search_filters_by_version(settings: Settings) -> None:
    reindex(settings.corpus_dir, settings.db_path)

    results = keyword_search(settings.db_path, "users", limit=20, version="v2")

    assert results
    assert {result.version for result in results} == {"v2"}


def test_keyword_search_without_version_is_unfiltered(settings: Settings) -> None:
    reindex(settings.corpus_dir, settings.db_path)

    results = keyword_search(settings.db_path, "users", limit=20)

    assert len({result.version for result in results}) > 1


# --- hybrid retriever -----------------------------------------------------


def test_hybrid_search_filters_both_retrievers(settings: Settings, store: VectorStore) -> None:
    build_index(settings, store=store, embedder=HashingEmbeddings())

    results = hybrid_search(
        "pagination",
        limit=10,
        settings=settings,
        store=store,
        embedder=HashingEmbeddings(),
        version="v3",
    )

    assert results
    assert all(result.version == "v3" for result in results)


def test_hybrid_search_rejects_unknown_version(settings: Settings) -> None:
    with pytest.raises(QueryError):
        hybrid_search("pagination", settings=settings, version="v0")


# --- endpoint -------------------------------------------------------------


def test_search_endpoint_filters_and_echoes_version(client: TestClient) -> None:
    response = client.post("/api/search", json={"query": "users", "version": "v2", "limit": 10})

    assert response.status_code == 200
    body = response.json()
    assert body["version"] == "v2"
    assert body["count"] == len(body["results"]) > 0
    assert {item["version"] for item in body["results"]} == {"v2"}


def test_search_endpoint_rejects_unknown_version(client: TestClient) -> None:
    response = client.post("/api/search", json={"query": "users", "version": "v9"})

    assert response.status_code == 400
    assert "unknown version" in response.json()["detail"]


def test_ask_endpoint_rejects_unknown_version(client: TestClient) -> None:
    response = client.post("/api/ask", json={"question": "users", "version": "v9"})

    assert response.status_code == 400


def test_ask_endpoint_accepts_a_version_scope(client: TestClient) -> None:
    response = client.post("/api/ask", json={"question": "Which field replaced user_name?", "version": "v3"})

    assert response.status_code == 200
    assert response.json()["version"] == "v3"


# --- UI -------------------------------------------------------------------


def test_ui_exposes_the_version_select(client: TestClient) -> None:
    body = client.get("/").text

    assert 'id="version"' in body
    assert '<option value="v3">' in body
    assert "All versions" in body
