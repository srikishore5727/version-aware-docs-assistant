"""Tests for the Day 6 search UI shell."""

from fastapi.testclient import TestClient

from app.main import STATIC_DIR, app

client = TestClient(app)


def test_home_serves_the_search_ui() -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    body = response.text
    assert 'id="search-form"' in body
    assert 'id="query"' in body
    assert 'id="answer"' in body
    assert 'id="cards"' in body
    assert "Every answer has a" in body


def test_script_calls_ask_and_keeps_the_search_fallback() -> None:
    script = client.get("/app.js").text

    assert "/api/ask" in script
    assert "/api/search" in script
    assert "citationText" in script


def test_ui_assets_are_served() -> None:
    css = client.get("/app.css")
    js = client.get("/app.js")

    assert css.status_code == 200
    assert "text/css" in css.headers["content-type"]
    assert "--accent" in css.text

    assert js.status_code == 200
    assert "javascript" in js.headers["content-type"]
    assert "/api/search" in js.text


def test_static_directory_exists() -> None:
    assert STATIC_DIR.is_dir()
    assert (STATIC_DIR / "index.html").exists()


def test_api_routes_are_not_shadowed_by_the_ui() -> None:
    assert client.get("/health").json()["status"] == "ok"
    assert client.get("/api").json()["service"] == "VADA"
    assert client.get("/docs").status_code == 200


def test_unknown_ui_path_still_404s() -> None:
    assert client.get("/no-such-page").status_code == 404
