"""Tests for accessibility and dark mode (Day 18)."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_skip_link_targets_a_focusable_results_region() -> None:
    body = client.get("/").text

    assert 'class="skip" href="#results"' in body
    assert 'id="results"' in body
    assert 'tabindex="-1"' in body
    assert 'aria-labelledby="results-heading"' in body


def test_the_status_line_is_a_live_region() -> None:
    body = client.get("/").text

    assert 'id="hint" role="status" aria-live="polite"' in body
    assert 'id="answer" class="answer" tabindex="-1"' in body


def test_every_form_control_has_a_label() -> None:
    body = client.get("/").text

    for control in ("query", "version", "doc-type"):
        assert f'for="{control}"' in body
    assert 'id="chips" role="group" aria-label="Example questions"' in body


def test_the_page_declares_both_colour_schemes() -> None:
    body = client.get("/").text

    assert '<meta name="color-scheme" content="light dark">' in body


def test_css_ships_a_dark_theme_and_focus_rings() -> None:
    css = client.get("/app.css").text

    assert "@media (prefers-color-scheme: dark)" in css
    assert "color-scheme: dark" in css
    assert ":focus-visible" in css
    assert "@media (prefers-reduced-motion: reduce)" in css


def test_the_dark_theme_redefines_surfaces_and_ink() -> None:
    css = client.get("/app.css").text
    dark = css.split("@media (prefers-color-scheme: dark)", 1)[1]

    assert "--paper: #101014" in dark
    assert "--ink: #f4f4f5" in dark
    assert "--surface: #18181d" in dark
    assert "--btn-bg: #e4e4e7" in dark


def test_the_script_moves_focus_to_the_result() -> None:
    script = client.get("/app.js").text

    assert "function focusResult()" in script
    assert "answerBox.focus()" in script
    assert "results.focus()" in script
