"""VADA - Version-Aware Docs Assistant.

Application entry point.

Days 1-6: scaffold, ingestion, BM25 keyword search, hybrid retrieval, grounded
answer generation with validated citations, and the search UI.
"""

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from pathlib import Path
from typing import Literal
import time

from app import __version__
from app.answer import generate_answer
from app.cache import AnswerCache, cache_key, index_fingerprint
from app.config import get_settings
from app.feedback import FeedbackStore
from app.observability import log_request, metrics
from app.refresh import index_status
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

# Process-local, bounded, and invalidated by an index rebuild (the key holds the
# FTS5 mtime). Set VADA_CACHE_SIZE=0 to turn it off.
answer_cache = AnswerCache(get_settings().cache_size)


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


class FeedbackRequest(BaseModel):
    """Body of a feedback submission."""

    question: str = Field(description="The question the reader asked")
    verdict: Literal["helpful", "not_helpful"] = Field(description="Was the answer useful?")
    status: str = Field(default="", description="Answer status the reader saw")
    version: str | None = Field(default=None, description="Version scope, if any")
    doc_type: str | None = Field(default=None, description="Document-type scope, if any")


@app.get("/health", tags=["system"])
def health() -> dict:
    """Liveness probe used by CI and the platform."""
    return {"status": "ok", "service": "vada", "version": __version__}


@app.middleware("http")
async def observe_api_requests(request, call_next):
    """Time API calls, log one JSON line each, and feed the counters."""
    path = request.url.path
    if not path.startswith("/api"):
        return await call_next(request)

    started = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        elapsed = (time.perf_counter() - started) * 1000
        metrics.record_request(path, 500, elapsed)
        log_request(path, 500, elapsed, method=request.method)
        raise

    elapsed = (time.perf_counter() - started) * 1000
    metrics.record_request(path, response.status_code, elapsed)
    log_request(path, response.status_code, elapsed, method=request.method)
    return response


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
        "metrics": "/api/metrics",
    }


@app.get("/api/metrics", tags=["system"])
def metrics_snapshot() -> dict:
    """Process-local request counters and latency figures."""
    return metrics.snapshot()


@app.get("/api/index/status", tags=["system"])
def index_health() -> dict:
    """Whether the indexes match the corpus on disk."""
    settings = get_settings()
    ensure_ready(settings)
    return index_status(settings)


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
    except QueryError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    key = cache_key(
        payload.question,
        payload.limit,
        scope,
        kind,
        index_fingerprint(settings.db_path),
    )
    cached = answer_cache.get(key)
    if cached is not None:
        metrics.record_cache(hit=True)
        metrics.record_outcome(cached["status"])
        return {**cached, "question": payload.question, "cached": True}

    metrics.record_cache(hit=False)

    try:
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
    metrics.record_outcome(answer.status)

    response = {
        "question": payload.question,
        "version": scope,
        "doc_type": kind,
        "mode": "hybrid" if settings.vectors_enabled else "keyword",
        **answer.to_dict(),
        "cached": False,
    }

    # A transient model failure must not be replayed for the life of the cache.
    if answer.status == "answered" or answer.reason in {
        "no_matches",
        "below_threshold",
        "model_not_found",
    }:
        answer_cache.set(key, response)

    return response


@app.post("/api/feedback", status_code=201, tags=["feedback"])
def submit_feedback(payload: FeedbackRequest) -> dict:
    """Store a reader's verdict next to the question that produced it."""
    if not payload.question.strip():
        raise HTTPException(status_code=400, detail="question must not be empty")

    store = FeedbackStore(get_settings().feedback_db)
    feedback_id = store.record(
        payload.question.strip(),
        payload.verdict,
        status=payload.status,
        version=payload.version,
        doc_type=payload.doc_type,
    )
    return {"recorded": True, "id": feedback_id}


@app.get("/api/feedback", tags=["feedback"])
def feedback_summary() -> dict:
    """Counts and the most recent submissions."""
    store = FeedbackStore(get_settings().feedback_db)
    return {"summary": store.summary(), "recent": store.recent()}


# Mounted last, so every route above wins: /health, /docs, /api still work and
# "/" serves the single-page UI from app/static.
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="ui")
