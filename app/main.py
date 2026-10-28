"""VADA - Version-Aware Docs Assistant.

Application entry point.

Days 1-6: scaffold, ingestion, BM25 keyword search, hybrid retrieval, grounded
answer generation with validated citations, and the search UI.
"""

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from pathlib import Path

from app import __version__
from app.answer import generate_answer
from app.config import get_settings
from app.retriever import (
    ensure_ready,
    hybrid_search,
    normalize_doc_type,
    normalize_version,
)
from app.search import QueryError

APP_NAME = "VADA"
APP_DESCRIPTION = "Version-aware answers over product documentation, with citations."
STATIC_DIR = Path(__file__).resolve().parent / "static"

app = FastAPI(
    title="VADA API",
    description=APP_DESCRIPTION,
    version=__version__,
)


class SearchRequest(BaseModel):
    """Body of a search request."""

    query: str = Field(description="Natural-language question or keywords")
    limit: int = Field(default=5, ge=1, le=20, description="Number of chunks to return")
    version: str | None = Field(
        default=None, description="Restrict results to one API version (v1, v2, v3)"
    )
    doc_type: str | None = Field(
        default=None,
        description="Restrict results to one document type (api-reference, migration-guide, changelog)",
    )


class AskRequest(BaseModel):
    """Body of a question."""

    question: str = Field(description="Natural-language question")
    limit: int = Field(default=5, ge=1, le=10, description="Chunks given to the model")
    version: str | None = Field(
        default=None, description="Restrict retrieval to one API version (v1, v2, v3)"
    )
    doc_type: str | None = Field(
        default=None,
        description="Restrict retrieval to one document type (api-reference, migration-guide, changelog)",
    )


@app.get("/health", tags=["system"])
def health() -> dict:
    """Liveness probe used by CI and the platform."""
    return {"status": "ok", "service": "vada", "version": __version__}


@app.get("/api", tags=["system"])
def metadata() -> dict:
    """Service metadata and endpoint map. ``/`` serves the UI."""
    return {
        "service": APP_NAME,
        "version": __version__,
        "ui": "/",
        "docs": "/docs",
        "health": "/health",
        "search": "/api/search",
        "ask": "/api/ask",
    }


@app.post("/api/search", tags=["search"])
def search_chunks(payload: SearchRequest) -> dict:
    """Return the best-matching chunks, fused from vector and keyword search."""
    if not payload.query.strip():
        raise HTTPException(status_code=400, detail="query must not be empty")

    settings = get_settings()
    ensure_ready(settings)

    try:
        scope = normalize_version(payload.version)
        kind = normalize_doc_type(payload.doc_type)
        results = hybrid_search(
            payload.query,
            limit=payload.limit,
            settings=settings,
            version=scope,
            doc_type=kind,
        )
    except QueryError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return {
        "query": payload.query,
        "version": scope,
        "doc_type": kind,
        "mode": "hybrid" if settings.vectors_enabled else "keyword",
        "count": len(results),
        "results": [result.to_dict() for result in results],
    }


@app.post("/api/ask", tags=["answer"])
def ask(payload: AskRequest) -> dict:
    """Answer a question using only retrieved chunks, with validated citations.

    Returns ``status: answered`` with source cards, or ``status: not_found``.
    An answer that cites a chunk that was not retrieved is never returned.
    """
    if not payload.question.strip():
        raise HTTPException(status_code=400, detail="question must not be empty")

    settings = get_settings()
    ensure_ready(settings)

    try:
        scope = normalize_version(payload.version)
        kind = normalize_doc_type(payload.doc_type)
        chunks = hybrid_search(
            payload.question,
            limit=payload.limit,
            settings=settings,
            version=scope,
            doc_type=kind,
        )
    except QueryError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    answer = generate_answer(payload.question, chunks, settings=settings)

    return {
        "question": payload.question,
        "version": scope,
        "doc_type": kind,
        "mode": "hybrid" if settings.vectors_enabled else "keyword",
        **answer.to_dict(),
    }


# Mounted last, so every route above wins: /health, /docs, /api still work and
# "/" serves the single-page UI from app/static.
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="ui")
