"""VADA - Version-Aware Docs Assistant.

Application entry point.

Day 3 scope: the Day 1 scaffold plus keyword search. ``POST /api/search``
returns BM25-ranked chunks with their citation metadata. Answer generation and
the UI arrive later in the 10-day plan.
"""

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from app import __version__
from app.search import QueryError, ensure_index, search

APP_NAME = "VADA"
APP_DESCRIPTION = "Version-aware answers over product documentation, with citations."

INDEX_PATH = Path(os.getenv("VADA_DB_PATH", "data/index/vada.db"))
CORPUS_DIR = Path(os.getenv("VADA_CORPUS_DIR", "corpus"))

app = FastAPI(
    title="VADA API",
    description=APP_DESCRIPTION,
    version=__version__,
)


class SearchRequest(BaseModel):
    """Body of a search request."""

    query: str = Field(description="Natural-language question or keywords")
    limit: int = Field(default=5, ge=1, le=20, description="Number of chunks to return")


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
        "search": "/api/search",
    }


@app.post("/api/search", tags=["search"])
def search_chunks(payload: SearchRequest) -> dict:
    """Return the best-matching documentation chunks for a query.

    Each result carries its document, version, section, and source URL so the
    caller can render a citation without a second lookup.
    """
    if not payload.query.strip():
        raise HTTPException(status_code=400, detail="query must not be empty")

    ensure_index(CORPUS_DIR, INDEX_PATH)

    try:
        results = search(INDEX_PATH, payload.query, limit=payload.limit)
    except QueryError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return {
        "query": payload.query,
        "count": len(results),
        "results": [result.to_dict() for result in results],
    }
