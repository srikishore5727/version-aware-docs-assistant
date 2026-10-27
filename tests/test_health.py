"""Tests for the Day 1 application scaffold."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_returns_ok() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "vada", "version": "0.1.0"}


def test_root_lists_service_metadata() -> None:
    response = client.get("/")

    assert response.status_code == 200
    body = response.json()
    assert body["service"] == "VADA"
    assert body["health"] == "/health"
    assert body["docs"] == "/docs"


def test_unknown_route_returns_404() -> None:
    assert client.get("/does-not-exist").status_code == 404
