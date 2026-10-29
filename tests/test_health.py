"""Tests for the Day 1 application scaffold."""

from fastapi.testclient import TestClient

from app import __version__
from app.main import app

client = TestClient(app)


def test_health_returns_ok() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "vada", "version": __version__}


def test_api_lists_service_metadata() -> None:
    response = client.get("/api")

    assert response.status_code == 200
    body = response.json()
    assert body["service"] == "VADA"
    assert body["health"] == "/health"
    assert body["docs"] == "/docs"
    assert body["ui"] == "/"


def test_unknown_route_returns_404() -> None:
    assert client.get("/does-not-exist").status_code == 404
