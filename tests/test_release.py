"""Release checks for the v1.0.0 cut."""

from pathlib import Path

from app import __version__

ROOT = Path(__file__).resolve().parents[1]


def test_the_package_is_at_one_zero() -> None:
    assert __version__ == "1.0.0"


def test_the_changelog_documents_the_current_version() -> None:
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")

    assert f"## [{__version__}]" in changelog
    assert changelog.index(f"## [{__version__}]") < changelog.index("[1.0.0]:")


def test_the_readme_advertises_the_release() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert f"**v{__version__}" in readme
    assert "| 20 | v1.0.0 release | Done |" in readme


def test_the_api_reports_the_release_version() -> None:
    from fastapi.testclient import TestClient

    from app.main import app

    assert TestClient(app).get("/api").json()["version"] == __version__
