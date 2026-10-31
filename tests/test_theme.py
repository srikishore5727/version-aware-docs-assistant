"""Theme switching and native-control contrast.

The page follows the system preference until the reader clicks the theme
toggle; that choice is stored and applied through ``data-theme``. These tests
cover the markup, the two dark paths in the stylesheet, the script that keeps
the button honest, and the dropdown contrast bug that made dark-mode select
options unreadable.
"""

import re
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

ROOT = Path(__file__).resolve().parents[1]
client = TestClient(app)


def page() -> str:
    return client.get("/").text


def stylesheet() -> str:
    return client.get("/app.css").text.replace("\r\n", "\n")


def script() -> str:
    return client.get("/app.js").text


def _tokens(block: str) -> dict[str, str]:
    return {
        name.strip(): value.strip()
        for name, value in re.findall(r"(--[\w-]+)\s*:\s*([^;]+);", block)
    }


def light_tokens() -> dict[str, str]:
    match = re.search(r":root \{(.*?)\n\}", stylesheet(), re.S)
    assert match is not None
    return _tokens(match.group(1))


def dark_tokens() -> dict[str, str]:
    match = re.search(r':root\[data-theme="dark"\] \{(.*?)\n\}', stylesheet(), re.S)
    assert match is not None
    return _tokens(match.group(1))


def _resolve(name: str, tokens: dict[str, str], seen: int = 0) -> str:
    value = tokens[name].strip()
    alias = re.fullmatch(r"var\((--[\w-]+)\)", value)
    if alias and seen < 5:
        return _resolve(alias.group(1), tokens, seen + 1)
    return value


def _luminance(colour: str) -> float:
    digits = colour.lstrip("#")
    if len(digits) == 3:
        digits = "".join(ch * 2 for ch in digits)
    channels = [int(digits[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    linear = [
        c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in channels
    ]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast(tokens: dict[str, str], foreground: str, background: str) -> float:
    lighter = max(_luminance(_resolve(foreground, tokens)), _luminance(_resolve(background, tokens)))
    darker = min(_luminance(_resolve(foreground, tokens)), _luminance(_resolve(background, tokens)))
    return (lighter + 0.05) / (darker + 0.05)


def test_the_head_resolves_the_theme_before_the_stylesheet() -> None:
    body = page()

    assert 'localStorage.getItem("vada-theme")' in body
    assert 'setAttribute("data-theme"' in body
    assert body.index('setAttribute("data-theme"') < body.index('rel="stylesheet"')


def test_the_toggle_is_a_labelled_button_with_both_icons() -> None:
    body = page()

    assert 'id="theme-toggle"' in body
    assert 'aria-pressed="false"' in body
    assert 'aria-label="Switch to dark theme"' in body
    assert "theme-toggle__icon--moon" in body
    assert "theme-toggle__icon--sun" in body
    # Decorative SVGs must not be announced twice.
    for icon in re.findall(r'<svg class="theme-toggle__icon[^>]*>', body):
        assert 'aria-hidden="true"' in icon


def test_the_stylesheet_supports_system_and_explicit_dark() -> None:
    css = stylesheet()

    assert '@media (prefers-color-scheme: dark)' in css
    # An explicit light choice must win over a dark OS.
    assert ':root:not([data-theme="light"]) {' in css
    assert ':root[data-theme="dark"] {' in css


def test_the_icon_shows_the_theme_it_switches_to() -> None:
    css = stylesheet()

    assert ".theme-toggle__icon--sun {\n  display: none;\n}" in css
    assert ':root[data-theme="dark"] .theme-toggle__icon--sun {\n  display: block;\n}' in css
    assert ':root[data-theme="dark"] .theme-toggle__icon--moon {\n  display: none;\n}' in css


def test_the_toggle_has_a_focus_ring() -> None:
    assert ".theme-toggle:focus-visible" in stylesheet()


def test_theme_body_text_passes_aa_in_both_schemes() -> None:
    assert contrast(light_tokens(), "--ink", "--surface") >= 4.5
    assert contrast(dark_tokens(), "--ink", "--surface") >= 4.5
    assert contrast(dark_tokens(), "--ink-2", "--surface") >= 4.5


def test_dropdown_options_use_theme_tokens() -> None:
    """The popup is OS-drawn; without explicit colours its text inherits page
    ink on a white sheet, which is unreadable in dark mode."""
    block = re.search(r"\.search select option \{(.*?)\n\}", stylesheet(), re.S)
    assert block is not None

    rule = block.group(1)
    assert "background: var(--surface);" in rule
    assert "color: var(--ink);" in rule


def test_dropdown_text_is_readable_against_its_own_background() -> None:
    for tokens in (light_tokens(), dark_tokens()):
        assert contrast(tokens, "--ink", "--surface") >= 4.5


def test_the_script_keeps_the_button_and_storage_in_sync() -> None:
    js = script()

    assert 'var THEME_KEY = "vada-theme";' in js
    assert 'localStorage.setItem(THEME_KEY, next)' in js
    assert 'setAttribute("aria-pressed"' in js
    assert 'addEventListener("change"' in js
    # A stored choice must survive a system preference flip.
    assert "if (!storedTheme()) applyTheme(systemTheme());" in js


def test_the_readme_documents_the_toggle() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "theme toggle" in readme.lower()
