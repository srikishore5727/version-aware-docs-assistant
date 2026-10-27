"""VADA - Version-Aware Docs Assistant.

Application entry point.

Day 1 scope is deliberately small: a health endpoint, service metadata,
and a test suite wired into CI. The documentation pipeline, search, and
answer generation arrive in later days of the 10-day plan.
"""

from fastapi import FastAPI

from app import __version__

APP_NAME = "VADA"
APP_DESCRIPTION = "Version-aware answers over product documentation, with citations."

app = FastAPI(
    title="VADA API",
    description=APP_DESCRIPTION,
    version=__version__,
)


@app.get("/health", tags=["system"])
def health() -> dict:
    """Liveness probe used by CI and the platform."""
    return {"status": "ok", "service": "vada", "version": __version__}


@app.get("/", tags=["system"])
def root() -> dict:
    """Service metadata. Replaced by the UI in a later day."""
    return {
        "service": APP_NAME,
        "version": __version__,
        "docs": "/docs",
        "health": "/health",
    }
