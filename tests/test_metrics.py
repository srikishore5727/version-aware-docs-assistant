"""Tests for structured logging and process metrics (Day 15)."""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.observability import format_event, metrics

CORPUS = Path(__file__).resolve().parents[1] / "corpus"


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("VADA_CORPUS_DIR", str(CORPUS))
    metrics.reset()
    return TestClient(app)


def test_event_is_one_json_line() -> None:
    line = format_event("/api/ask", 200, 12.3456, method="POST")
    payload = json.loads(line)

    assert "\n" not in line
    assert payload == {
        "event": "request",
        "endpoint": "/api/ask",
        "status": 200,
        "duration_ms": 12.35,
        "method": "POST",
    }


def test_metrics_snapshot_shape() -> None:
    snapshot = metrics.snapshot()

    assert set(snapshot) == {
        "requests",
        "answered",
        "not_found",
        "errors",
        "cache_hits",
        "cache_misses",
        "avg_ms",
        "max_ms",
        "slowest_endpoint",
    }


def test_api_calls_are_counted(client: TestClient) -> None:
    client.get("/api/metrics")
    body = client.get("/api/metrics").json()

    assert body["requests"] >= 1
    assert body["avg_ms"] >= 0
    assert body["slowest_endpoint"] == "/api/metrics"


def test_health_is_not_counted(client: TestClient) -> None:
    client.get("/health")
    body = client.get("/api/metrics").json()

    # The metrics call is recorded after its own response is rendered.
    assert body["requests"] == 0
    assert body["slowest_endpoint"] == ""


def test_answered_outcome_is_counted(client: TestClient) -> None:
    client.post("/api/ask", json={"question": "Which field replaced user_name?"})
    body = client.get("/api/metrics").json()

    assert body["answered"] == 1
    assert body["not_found"] == 0
    assert body["requests"] == 1


def test_not_found_outcome_is_counted(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("app.main.hybrid_search", lambda *args, **kwargs: [])
    client.post("/api/ask", json={"question": "banana smoothie recipe"})
    body = client.get("/api/metrics").json()

    assert body["not_found"] == 1
    assert body["answered"] == 0
    assert body["requests"] == 1


def test_client_errors_are_not_server_errors(client: TestClient) -> None:
    client.post("/api/ask", json={"question": "  "})
    body = client.get("/api/metrics").json()

    assert body["errors"] == 0


def test_reset_clears_every_counter() -> None:
    metrics.record_request("/api/search", 200, 5.0)
    metrics.record_outcome("answered")
    metrics.record_cache(hit=True)
    metrics.reset()

    assert metrics.snapshot()["requests"] == 0
    assert metrics.snapshot()["answered"] == 0
    assert metrics.snapshot()["cache_hits"] == 0
    assert metrics.snapshot()["cache_misses"] == 0
    assert metrics.snapshot()["slowest_endpoint"] == ""
