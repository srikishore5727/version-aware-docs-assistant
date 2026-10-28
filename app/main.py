"""VADA - Version-Aware Docs Assistant.

Application entry point.

Days 1-4: scaffold, ingestion, BM25 keyword search, and hybrid retrieval
(embeddings + Chroma fused with BM25). Answer generation arrives on Day 5.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from app import __version__
from app.config import get_settings
from app.retriever import ensure_ready, hybrid_search
from app.search import QueryError

APP_NAME = "VADA"
APP_DESCRIPTION = "Version-aware answers over product documentation, with citations."

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
    """Return the best-matching chunks, fused from vector and keyword search.

    Each result carries its document, version, section, and source URL, plus
    ``matched_by`` so the caller can see which retriever found it.
    """
    if not payload.query.strip():
        raise HTTPException(status_code=400, detail="query must not be empty")

    settings = get_settings()
    ensure_ready(settings)

    try:
        results = hybrid_search(
            payload.query, limit=payload.limit, settings=settings
        )
    except QueryError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return {
        "query": payload.query,
        "mode": "hybrid" if settings.vectors_enabled else "keyword",
        "count": len(results),
        "results": [result.to_dict() for result in results],
    }
