"""Tests for feedback capture (Day 16)."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.feedback import FeedbackStore
from app.main import app

CORPUS = Path(__file__).resolve().parents[1] / "corpus"


@pytest.fixture()
def store(tmp_path: Path) -> FeedbackStore:
    return FeedbackStore(tmp_path / "feedback.db")


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> TestClient:
    monkeypatch.setenv("VADA_CORPUS_DIR", str(CORPUS))
    monkeypatch.setenv("VADA_FEEDBACK_DB", str(tmp_path / "feedback.db"))
    return TestClient(app)


def test_store_round_trip(store: FeedbackStore) -> None:
    feedback_id = store.record(
        "Which field replaced user_name?",
        "helpful",
        status="answered",
        version="v3",
        doc_type="api-reference",
    )

    assert feedback_id == 1
    recent = store.recent()
    assert recent[0]["question"] == "Which field replaced user_name?"
    assert recent[0]["verdict"] == "helpful"
    assert recent[0]["version"] == "v3"


def test_summary_counts_each_verdict(store: FeedbackStore) -> None:
    store.record("q1", "helpful")
    store.record("q2", "helpful")
    store.record("q3", "not_helpful")

    assert store.summary() == {"total": 3, "helpful": 2, "not_helpful": 1}


def test_empty_summary_is_all_zero(store: FeedbackStore) -> None:
    assert store.summary() == {"total": 0, "helpful": 0, "not_helpful": 0}


def test_unknown_verdict_is_rejected_by_the_store(store: FeedbackStore) -> None:
    with pytest.raises(ValueError):
        store.record("q", "maybe")


def test_endpoint_records_feedback(client: TestClient) -> None:
    response = client.post(
        "/api/feedback",
        json={
            "question": "How do I paginate users?",
            "verdict": "not_helpful",
            "status": "answered",
            "version": "v3",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["recorded"] is True
    assert body["id"] == 1

    summary = client.get("/api/feedback").json()
    assert summary["summary"]["not_helpful"] == 1
    assert summary["recent"][0]["question"] == "How do I paginate users?"


def test_endpoint_rejects_an_unknown_verdict(client: TestClient) -> None:
    response = client.post("/api/feedback", json={"question": "q", "verdict": "maybe"})

    assert response.status_code == 422


def test_endpoint_rejects_an_empty_question(client: TestClient) -> None:
    response = client.post("/api/feedback", json={"question": "  ", "verdict": "helpful"})

    assert response.status_code == 400


def test_ui_renders_the_feedback_controls(client: TestClient) -> None:
    script = client.get("/app.js").text

    assert "/api/feedback" in script
    assert "answer__feedback" in script
    assert "Was this useful?" in script
