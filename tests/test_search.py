"""Tests for BM25 keyword search and the /api/search endpoint."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.ingest import load_chunks
from app.main import app
from app.search import (
    QueryError,
    build_index,
    build_match_query,
    ensure_index,
    search,
)

CORPUS = Path(__file__).resolve().parents[1] / "corpus"


@pytest.fixture(scope="module")
def index_db(tmp_path_factory: pytest.TempPathFactory) -> Path:
    db_path = tmp_path_factory.mktemp("index") / "vada.db"
    build_index(load_chunks(CORPUS), db_path)
    return db_path


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("VADA_CORPUS_DIR", str(CORPUS))
    return TestClient(app)


# --- query building -------------------------------------------------------


def test_match_query_drops_stopwords() -> None:
    assert build_match_query("how do I create a user") == '"create" OR "user"'


def test_match_query_quotes_punctuation() -> None:
    expression = build_match_query('user_name OR "display-; DROP TABLE')

    assert "user_name" in expression
    assert '"' in expression
    assert expression.count('"') % 2 == 0


def test_match_query_keeps_stopwords_when_nothing_else_remains() -> None:
    assert build_match_query("how to") == '"how" OR "to"'


def test_match_query_rejects_empty_input() -> None:
    with pytest.raises(QueryError):
        build_match_query("   ")
    with pytest.raises(QueryError):
        build_match_query("...")


# --- ranking and metadata -------------------------------------------------


def test_search_returns_ranked_chunks(index_db: Path) -> None:
    results = search(index_db, "create user", limit=5)

    assert results
    assert results[0].doc_id in {"api-users-create", "api-users-create-v2"}
    assert results[0].score > 0


def test_search_finds_the_exact_field_name(index_db: Path) -> None:
    results = search(index_db, "user_name", limit=5)

    assert results
    assert "api-users-create" in {result.doc_id for result in results}


def test_pagination_question_prefers_the_pagination_guide(index_db: Path) -> None:
    results = search(index_db, "how do I paginate with a cursor", limit=5)

    assert results[0].doc_id == "migration-v2-to-v3-pagination"


def test_results_carry_citation_metadata(index_db: Path) -> None:
    result = search(index_db, "bearer token", limit=1)[0]

    assert result.chunk_id.startswith(result.doc_id + "::")
    assert result.title
    assert result.section
    assert result.version in {"v1", "v2", "v3"}
    assert result.doc_type in {"api-reference", "migration-guide", "changelog"}
    assert result.status in {"current", "superseded"}
    assert result.source_url.startswith("https://")
    assert result.text


def test_search_respects_the_limit(index_db: Path) -> None:
    assert len(search(index_db, "user", limit=2)) <= 2


def test_unmatched_query_returns_no_results(index_db: Path) -> None:
    assert search(index_db, "kubernetes helm chart", limit=5) == []


def test_punctuation_only_query_raises_a_clean_error(index_db: Path) -> None:
    # A clean QueryError (mapped to HTTP 400) rather than an sqlite error.
    with pytest.raises(QueryError):
        search(index_db, "!!! ??? ---", limit=5)


# --- index lifecycle ------------------------------------------------------


def test_ensure_index_builds_once(tmp_path: Path) -> None:
    db_path = tmp_path / "nested" / "vada.db"

    assert ensure_index(CORPUS, db_path) > 0
    assert db_path.exists()
    assert ensure_index(CORPUS, db_path) == 0


# --- endpoint -------------------------------------------------------------


def test_endpoint_returns_results(client: TestClient) -> None:
    response = client.post("/api/search", json={"query": "cursor pagination"})

    assert response.status_code == 200
    body = response.json()
    assert body["query"] == "cursor pagination"
    assert body["mode"] in {"hybrid", "keyword"}
    assert body["count"] == len(body["results"]) > 0
    assert body["results"][0]["source_url"].startswith("https://")


def test_endpoint_honours_limit(client: TestClient) -> None:
    response = client.post("/api/search", json={"query": "user", "limit": 2})

    assert response.status_code == 200
    assert len(response.json()["results"]) <= 2


def test_endpoint_rejects_empty_query(client: TestClient) -> None:
    assert client.post("/api/search", json={"query": ""}).status_code == 400
    assert client.post("/api/search", json={"query": "   "}).status_code == 400


def test_endpoint_rejects_invalid_limit(client: TestClient) -> None:
    assert client.post("/api/search", json={"query": "user", "limit": 0}).status_code == 422


def test_api_advertises_search(client: TestClient) -> None:
    assert client.get("/api").json()["search"] == "/api/search"
