"""Brand compliance for the UI stylesheet.

The palette, radii, elevation, type stacks and easing come from
``mockups/brand-guidelines.html``; the component radii and supporting tints come
from ``mockups/design-system.html``. These tests fail if the app drifts from
either file, or if a component introduces a colour that is not a token.
"""

import re
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

ROOT = Path(__file__).resolve().parents[1]
client = TestClient(app)

BRAND = ROOT / "mockups" / "brand-guidelines.html"
DESIGN = ROOT / "mockups" / "design-system.html"

# Values the brand document names, so a reader can trace them by hand.
SUPPORTING = {
    "--accent-line": "#dde4ff",  # design-system.html eyebrow / tag border
    "--accent-line-strong": "#c7d2fe",  # design-system.html .tag-ver
    "--ok-line": "#a7f3d0",  # design-system.html .tag-current
    "--warn-line": "#fde68a",  # design-system.html .notice
    "--notice-ink": "#92400e",  # design-system.html .notice .hint
    "--hover-line": "#d4d4d8",  # design-system.html chip / select hover
    "--code-bg": "#f4f4f5",  # design-system.html code
    "--code-line": "#e4e4e7",  # design-system.html code
}

COMPONENT_RADII = {
    "--r-card": "18px",  # design-system.html .answer / .skel
    "--r-source": "14px",  # design-system.html .source / .notice
    "--r-tag": "6px",
    "--r-cite": "5px",
}


def css() -> str:
    return client.get("/app.css").text.replace("\r\n", "\n")


def _normalise(value: str) -> str:
    """Hex case, 3-digit shorthand and whitespace are not brand decisions."""
    value = re.sub(r"\s+", " ", value.strip().lower().replace(", ", ","))
    value = re.sub(r"rgba?\(([^)]*)\)", lambda m: "rgba(" + m.group(1).replace(" ", "") + ")", value)
    value = re.sub(r"\b0\.(\d+)", r".\1", value)

    def expand(match: re.Match[str]) -> str:
        digits = match.group(1)
        if len(digits) == 3:
            digits = "".join(ch * 2 for ch in digits)
        return "#" + digits

    return re.sub(r"#([0-9a-f]{3,6})\b", expand, value)


def _parse(block: str) -> dict[str, str]:
    return {
        name.strip(): value.strip()
        for name, value in re.findall(r"(--[\w-]+)\s*:\s*([^;]+);", block)
    }


def light_tokens() -> dict[str, str]:
    block = re.search(r":root \{(.*?)\n\}", css(), re.S)
    assert block is not None
    return _parse(block.group(1))


def dark_tokens() -> dict[str, str]:
    """The system-preference dark block."""
    dark = css().split("@media (prefers-color-scheme: dark)", 1)[1]
    block = re.search(r':root:not\(\[data-theme="light"\]\) \{(.*?)\n  \}', dark, re.S)
    assert block is not None
    return _parse(block.group(1))


def theme_dark_tokens() -> dict[str, str]:
    """The explicit `data-theme="dark"` block written by the toggle."""
    block = re.search(r':root\[data-theme="dark"\] \{(.*?)\n\}', css(), re.S)
    assert block is not None
    return _parse(block.group(1))


def brand_tokens() -> dict[str, str]:
    block = re.search(r":root\{(.*?)\}", BRAND.read_text(encoding="utf-8"), re.S)
    assert block is not None
    return _parse(block.group(1))


def test_every_brand_token_is_present_with_the_brand_value() -> None:
    app_tokens = {k: _normalise(v) for k, v in light_tokens().items()}
    brand = {k: _normalise(v) for k, v in brand_tokens().items()}

    assert brand, "brand guidelines should define tokens"
    missing = sorted(set(brand) - set(app_tokens))
    assert missing == []

    wrong = {k: (brand[k], app_tokens[k]) for k in brand if app_tokens[k] != brand[k]}
    assert wrong == {}


def test_supporting_tints_match_the_design_system() -> None:
    tokens = {k: _normalise(v) for k, v in light_tokens().items()}

    for name, value in SUPPORTING.items():
        assert tokens[name] == _normalise(value), name


def test_component_radii_match_the_design_system() -> None:
    tokens = light_tokens()

    for name, value in COMPONENT_RADII.items():
        assert tokens[name] == value, name


def test_no_raw_colour_outside_the_token_blocks() -> None:
    stylesheet = css()
    body = stylesheet.split("\n* {", 1)[1]

    offenders = [
        line.strip()
        for line in body.splitlines()
        if re.search(r"#[0-9a-fA-F]{3,6}\b|rgba?\(", line)
    ]
    assert offenders == []


def test_every_var_reference_is_defined() -> None:
    stylesheet = css()
    defined = set(light_tokens()) | set(dark_tokens()) | set(theme_dark_tokens())
    used = set(re.findall(r"var\((--[\w-]+)\)", stylesheet))

    assert sorted(used - defined) == []


def test_both_dark_paths_define_the_same_tokens() -> None:
    """The system block and the toggle block must never drift apart."""
    assert dark_tokens() == theme_dark_tokens()


def test_the_brand_type_stacks_are_used() -> None:
    tokens = light_tokens()

    assert tokens["--font"] == (
        'ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, '
        '"Helvetica Neue", Arial, sans-serif'
    )
    assert tokens["--mono"] == "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"


def test_motion_uses_the_brand_easing_and_durations() -> None:
    tokens = light_tokens()

    assert tokens["--ease"] == "cubic-bezier(0.2, 0.7, 0.3, 1)"
    assert tokens["--t-fast"] == "120ms"
    assert tokens["--t-mid"] == "180ms"


def test_elevation_uses_the_brand_shadows() -> None:
    tokens = {k: _normalise(v) for k, v in light_tokens().items()}

    assert tokens["--shadow-sm"] == _normalise("0 1px 2px rgba(21,21,24,.05)")
    assert tokens["--shadow"] == _normalise(
        "0 1px 2px rgba(21,21,24,.04),0 18px 40px -22px rgba(21,21,24,.24)"
    )


def test_the_old_off_palette_values_are_gone() -> None:
    stylesheet = css().lower()

    for retired in ("#fef3c7", "#16a34a", "#d97706", "#94a3b8"):
        assert retired not in stylesheet, retired


def test_confidence_and_primary_action_use_semantic_tokens() -> None:
    stylesheet = css()

    assert ".answer__confidence--high .confidence__dot {\n  background: var(--ok);" in stylesheet
    assert ".answer__confidence--medium .confidence__dot {\n  background: var(--warn);" in stylesheet
    assert ".answer__confidence--low .confidence__dot {\n  background: var(--muted);" in stylesheet
    assert "background: var(--accent);\n  color: var(--on-accent);" in stylesheet
    assert ".search button:hover:not(:disabled) {\n  background: var(--accent-2);" in stylesheet


def test_dark_mode_keeps_the_brand_hues() -> None:
    dark = {k: _normalise(v) for k, v in dark_tokens().items()}

    # Indigo 300 is the night accent; the hue is unchanged.
    assert dark["--accent"] == "#a5b4fc"
    assert dark["--accent-ink"] == "#c7d2fe"
