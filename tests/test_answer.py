"""Tests for grounded generation and citation validation."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.answer import (
    Answer,
    build_prompt,
    cited_indexes,
    extractive_answer,
    generate_answer,
    has_valid_citations,
    render_context,
    sources_for,
)
from app.config import Settings
from app.main import app
from app.search import SearchResult

CORPUS = Path(__file__).resolve().parents[1] / "corpus"


def _chunk(index: int, version: str = "v3") -> SearchResult:
    return SearchResult(
        chunk_id=f"doc-{index}::0",
        doc_id=f"doc-{index}",
        title=f"Title {index}",
        doc_type="api-reference",
        version=version,
        status="current",
        source_url=f"https://docs.example/{index}",
        last_updated="2026-10-01",
        section="Request body",
        text="Use display_name instead of user_name.",
        score=0.5,
        matched_by="both",
    )


CHUNKS = [_chunk(1), _chunk(2)]


# --- prompt contract ------------------------------------------------------


def test_prompt_contains_the_grounding_rules() -> None:
    messages = build_prompt("Which field replaced user_name?", CHUNKS)

    assert messages[0]["role"] == "system"
    assert "ONLY the numbered context" in messages[0]["content"]
    assert "NOT_FOUND" in messages[0]["content"]
    assert "Cite every factual sentence" in messages[0]["content"]
    assert "Question: Which field replaced user_name?" in messages[1]["content"]


def test_context_numbers_every_chunk() -> None:
    context = render_context(CHUNKS)

    assert context.startswith("[1] Title 1")
    assert "[2] Title 2" in context
    assert "v3" in context


# --- citation validation --------------------------------------------------


def test_cited_indexes_are_deduplicated_in_order() -> None:
    assert cited_indexes("A [2]. B [1]. C [2].") == [2, 1]


def test_grouped_citations_are_parsed() -> None:
    assert cited_indexes("See [1, 3] and [3, 5].") == [1, 3, 5]
    assert has_valid_citations("Grouped [1, 2].", 2)


def test_valid_citations_require_a_real_chunk() -> None:
    assert has_valid_citations("Use display_name [1].", 2)
    assert not has_valid_citations("Use display_name.", 2)
    assert not has_valid_citations("Use display_name [3].", 2)
    assert not has_valid_citations("Mixed [1] and [9].", 2)


def test_sources_only_cover_cited_chunks() -> None:
    sources = sources_for(CHUNKS, [2])

    assert len(sources) == 1
    assert sources[0]["index"] == 2
    assert sources[0]["source_url"] == "https://docs.example/2"
    assert sources[0]["text"] == CHUNKS[1].text


# --- generation -----------------------------------------------------------


def test_answer_with_citations_is_returned() -> None:
    completer = lambda messages: "In v3, use `display_name` instead of `user_name` [1]."

    answer = generate_answer("Which field replaced user_name?", CHUNKS, completer=completer)

    assert answer.status == "answered"
    assert answer.sources[0]["index"] == 1
    assert "[1]" in answer.answer


def test_model_not_found_maps_to_not_found_status() -> None:
    answer = generate_answer("What is the rate limit?", CHUNKS, completer=lambda m: "NOT_FOUND")

    assert answer.status == "not_found"
    assert answer.reason == "model_not_found"
    assert answer.sources == []


def test_uncited_answer_is_retried_once() -> None:
    replies = iter(["Use display_name.", "Use display_name [1]."])
    answer = generate_answer("Which field?", CHUNKS, completer=lambda m: next(replies))

    assert answer.status == "answered"
    assert answer.reason == ""


def test_second_uncited_answer_is_rejected() -> None:
    answer = generate_answer("Which field?", CHUNKS, completer=lambda m: "Trust me, it works.")

    assert answer.status == "not_found"
    assert answer.reason == "invalid_citations"


def test_citation_outside_the_context_is_rejected() -> None:
    answer = generate_answer("Which field?", CHUNKS, completer=lambda m: "It is [7].")

    assert answer.status == "not_found"


def test_generation_failure_falls_back_to_quotes() -> None:
    def boom(messages: list[dict]) -> str:
        raise TimeoutError("upstream timed out")

    answer = generate_answer("Which field?", CHUNKS, completer=boom)

    assert answer.status == "answered"
    assert answer.model == "extractive"
    assert answer.reason.startswith("generation_failed")
    assert "[1]" in answer.answer


def test_extractive_answer_needs_chunks() -> None:
    answer = extractive_answer([])

    assert answer.status == "not_found"
    assert answer.reason == "no_matches"


def test_no_chunks_means_not_found_without_calling_the_model() -> None:
    calls: list[int] = []

    def completer(messages: list[dict]) -> str:
        calls.append(1)
        return "should not run [1]"

    answer = generate_answer("anything", [], completer=completer)

    assert answer.status == "not_found"
    assert calls == []


def test_missing_key_uses_the_extractive_path() -> None:
    settings = Settings(
        gemini_api_key="",
        embedding_model="",
        llm_model="test",
        embeddings_mode="off",
        corpus_dir=CORPUS,
        db_path=Path("unused.db"),
        chroma_dir=Path("unused"),
    )

    answer = generate_answer("Which field?", CHUNKS, settings=settings)

    assert answer.status == "answered"
    assert answer.reason == "no_api_key"


# --- endpoint -------------------------------------------------------------


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("VADA_CORPUS_DIR", str(CORPUS))
    return TestClient(app)


def test_ask_endpoint_returns_answer_and_sources(client: TestClient) -> None:
    response = client.post("/api/ask", json={"question": "Which field replaced user_name?"})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] in {"answered", "not_found"}
    assert body["answer"]
    if body["status"] == "answered":
        assert body["sources"]


def test_ask_endpoint_rejects_empty_question(client: TestClient) -> None:
    assert client.post("/api/ask", json={"question": "  "}).status_code == 400


def test_api_advertises_ask(client: TestClient) -> None:
    assert client.get("/api").json()["ask"] == "/api/ask"
