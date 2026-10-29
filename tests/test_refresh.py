"""Tests for index freshness and refresh (Day 17)."""

import os
import shutil
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import app
from app.refresh import index_status, refresh, refresh_if_stale

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "corpus"


@pytest.fixture()
def settings(tmp_path: Path) -> Settings:
    corpus = tmp_path / "corpus"
    shutil.copytree(CORPUS, corpus)
    return Settings(
        gemini_api_key="",
        embedding_model="",
        llm_model="test",
        embeddings_mode="hash",
        corpus_dir=corpus,
        db_path=tmp_path / "index" / "vada.db",
        chroma_dir=tmp_path / "index" / "chroma",
    )


def test_status_counts_before_anything_is_built(settings: Settings) -> None:
    status = index_status(settings)

    assert status["indexed"] is False
    assert status["stale"] is True
    assert status["documents"] == 12
    assert status["chunks"] == 60
    assert status["index_updated"] is None


def test_refresh_builds_and_reports_fresh(settings: Settings) -> None:
    status = refresh(settings)

    assert status["indexed"] is True
    assert status["stale"] is False
    assert status["documents"] == 12
    assert status["chunks"] == 60
    assert status["vectors"] == 60
    assert status["index_updated"] is not None


def test_a_touched_document_makes_the_index_stale(settings: Settings) -> None:
    refresh(settings)
    time.sleep(0.05)
    target = settings.corpus_dir / "api-users-list.md"
    now = time.time()
    os.utime(target, (now, now))

    assert index_status(settings)["stale"] is True


def test_refresh_if_stale_is_a_noop_when_fresh(settings: Settings) -> None:
    refresh(settings)
    before = Path(settings.db_path).stat().st_mtime

    status = refresh_if_stale(settings)

    assert status["stale"] is False
    assert Path(settings.db_path).stat().st_mtime == before


def test_refresh_if_stale_rebuilds_when_needed(settings: Settings) -> None:
    refresh(settings)
    time.sleep(0.05)
    before = Path(settings.db_path).stat().st_mtime
    target = settings.corpus_dir / "api-users-list.md"
    now = time.time()
    os.utime(target, (now, now))

    status = refresh_if_stale(settings)

    assert status["stale"] is False
    assert Path(settings.db_path).stat().st_mtime >= before


def test_endpoint_exposes_the_status(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VADA_CORPUS_DIR", str(CORPUS))
    response = TestClient(app).get("/api/index/status")

    assert response.status_code == 200
    body = response.json()
    assert body["documents"] == 12
    assert body["chunks"] == 60
    assert "stale" in body
