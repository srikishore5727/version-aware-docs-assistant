"""Tests for the answer cache and its endpoint wiring (Day 19)."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.cache import AnswerCache, cache_key, index_fingerprint
from app.main import app
from app.observability import metrics

CORPUS = Path(__file__).resolve().parents[1] / "corpus"


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("VADA_CORPUS_DIR", str(CORPUS))
    metrics.reset()
    return TestClient(app)


def test_a_stored_value_is_returned_and_counted() -> None:
    cache = AnswerCache(2)
    key = cache_key("How do I create a user?", 5, None, None)

    assert cache.get(key) is None
    cache.set(key, {"status": "answered"})

    assert cache.get(key) == {"status": "answered"}
    assert cache.stats() == {
        "size": 1,
        "maxsize": 2,
        "hits": 1,
        "misses": 1,
        "hit_rate": 0.5,
    }


def test_least_recently_used_entry_is_evicted() -> None:
    cache = AnswerCache(2)
    first = cache_key("first", 5, None, None)
    second = cache_key("second", 5, None, None)
    third = cache_key("third", 5, None, None)

    cache.set(first, {"n": 1})
    cache.set(second, {"n": 2})
    cache.get(first)  # first becomes the most recent
    cache.set(third, {"n": 3})

    assert cache.get(second) is None
    assert cache.get(first) == {"n": 1}
    assert cache.get(third) == {"n": 3}


def test_scope_is_part_of_the_key() -> None:
    question = "How do I paginate users?"

    assert cache_key(question, 5, "v3", None) != cache_key(question, 5, "v2", None)
    assert cache_key(question, 5, None, "changelog") != cache_key(question, 5, None, None)
    assert cache_key(question, 5, None, None) != cache_key(question, 3, None, None)


def test_question_case_and_spacing_are_normalised() -> None:
    assert cache_key("  How  do I paginate? ", 5, None, None) == cache_key(
        "how do i paginate?", 5, None, None
    )


def test_index_fingerprint_separates_rebuilds() -> None:
    base = cache_key("q", 5, None, None, 1)
    rebuilt = cache_key("q", 5, None, None, 2)

    assert base != rebuilt
    assert index_fingerprint("does/not/exist.db") == 0


def test_a_disabled_cache_never_stores() -> None:
    cache = AnswerCache(0)
    key = cache_key("q", 5, None, None)

    cache.set(key, {"status": "answered"})

    assert cache.get(key) is None
    assert cache.stats()["hit_rate"] == 0.0


def test_second_identical_ask_is_served_from_cache(client: TestClient) -> None:
    payload = {"question": "Which field replaced user_name?"}

    first = client.post("/api/ask", json=payload).json()
    second = client.post("/api/ask", json=payload).json()

    assert first["cached"] is False
    assert second["cached"] is True
    assert second["answer"] == first["answer"]
    assert second["question"] == payload["question"]


def test_filters_are_cached_separately(client: TestClient) -> None:
    question = "How do I create a user?"

    first = client.post("/api/ask", json={"question": question, "version": "v3"}).json()
    second = client.post("/api/ask", json={"question": question, "version": "v2"}).json()

    assert first["cached"] is False
    assert second["cached"] is False
    assert first["version"] == "v3"
    assert second["version"] == "v2"


def test_disabled_cache_answers_every_time(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("app.main.answer_cache", AnswerCache(0))
    payload = {"question": "How long do access tokens last?"}

    first = client.post("/api/ask", json=payload).json()
    second = client.post("/api/ask", json=payload).json()

    assert first["cached"] is False
    assert second["cached"] is False


def test_transient_generation_failure_is_not_cached(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.answer import Answer

    def fail(*args, **kwargs):
        return Answer(
            status="not_found",
            answer="The language model was unavailable.",
            reason="generation_failed: TimeoutError",
        )

    monkeypatch.setattr("app.main.generate_answer", fail)
    payload = {"question": "How do I create a user?"}

    assert client.post("/api/ask", json=payload).json()["cached"] is False
    assert client.post("/api/ask", json=payload).json()["cached"] is False


def test_metrics_count_hits_and_misses(client: TestClient) -> None:
    payload = {"question": "How do I paginate users?"}

    client.post("/api/ask", json=payload)
    client.post("/api/ask", json=payload)
    body = client.get("/api/metrics").json()

    assert body["cache_misses"] == 1
    assert body["cache_hits"] == 1
    assert body["answered"] == 2
