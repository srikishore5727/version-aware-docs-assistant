"""Hybrid retrieval: vector search fused with BM25.

Both retrievers return their own ranked list. Reciprocal Rank Fusion combines
them without needing to normalise cosine similarity against BM25 scores:

    score = sum(1 / (K + rank))   with K = 60

The merged list keeps the citation metadata from the chunks, so callers cannot
tell which retriever produced a result apart from ``matched_by``.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from app.config import Settings, get_settings
from app.embeddings import EmbeddingProvider, get_embedder
from app.ingest import load_chunks
from app.search import QueryError, SearchResult, reindex, search
from app.vector_store import VectorStore

RRF_K = 60
TOP_K_PER_RETRIEVER = 10

# Demotion applied to a retired document after fusion. Small enough that a
# strongly relevant v2 page still wins a v2 question, large enough to break
# ties in favour of the version we still support.
SUPERSEDED_PENALTY = 0.0015

# Versions present in ``corpus/``. Explicit so an unknown filter is a 400 rather
# than a silent empty result. The index refresh (Day 17) revisits this.
SUPPORTED_VERSIONS = ("v1", "v2", "v3")

# Document types present in ``corpus/``.
SUPPORTED_DOC_TYPES = ("api-reference", "migration-guide", "changelog")


def normalize_version(version: str | None) -> str | None:
    """Validate and canonicalise a version filter.

    ``None`` and blank strings mean "all versions". Anything else must be one
    of :data:`SUPPORTED_VERSIONS`; the check is case-insensitive.
    """
    if version is None:
        return None

    cleaned = version.strip().lower()
    if not cleaned:
        return None

    if cleaned not in SUPPORTED_VERSIONS:
        allowed = ", ".join(SUPPORTED_VERSIONS)
        raise QueryError(f"unknown version '{version}'. Use one of: {allowed}")

    return cleaned


def normalize_doc_type(doc_type: str | None) -> str | None:
    """Validate and canonicalise a document-type filter.

    Spaces and underscores are accepted so ``"API Reference"`` and
    ``"migration_guide"`` resolve to the indexed values.
    """
    if doc_type is None:
        return None

    cleaned = doc_type.strip().lower().replace("_", "-").replace(" ", "-")
    if not cleaned:
        return None

    if cleaned not in SUPPORTED_DOC_TYPES:
        allowed = ", ".join(SUPPORTED_DOC_TYPES)
        raise QueryError(f"unknown doc_type '{doc_type}'. Use one of: {allowed}")

    return cleaned


def _metadata_for(chunk) -> dict:
    return {
        "doc_id": chunk.doc_id,
        "title": chunk.title,
        "doc_type": chunk.doc_type,
        "version": chunk.version,
        "status": chunk.status,
        "source_url": chunk.source_url,
        "last_updated": chunk.last_updated,
        "section": chunk.section,
    }


def build_index(
    settings: Settings | None = None,
    store: VectorStore | None = None,
    embedder: EmbeddingProvider | None = None,
) -> dict:
    """Rebuild the keyword index and, when enabled, the vector index."""
    config = settings or get_settings()
    chunks = load_chunks(config.corpus_dir)

    keyword_count = reindex(config.corpus_dir, config.db_path)
    vector_count = 0

    if config.vectors_enabled:
        store = store or VectorStore(config.chroma_dir)
        embedder = embedder or get_embedder(
            config.embeddings_mode, config.gemini_api_key, config.embedding_model
        )
        vectors = embedder.embed_documents([chunk.text for chunk in chunks])
        store.reset()
        store.add(
            ids=[chunk.chunk_id for chunk in chunks],
            texts=[chunk.text for chunk in chunks],
            vectors=vectors,
            metadatas=[_metadata_for(chunk) for chunk in chunks],
        )
        vector_count = store.count()

    return {"chunks": len(chunks), "keyword": keyword_count, "vectors": vector_count}


def ensure_ready(settings: Settings | None = None) -> None:
    """Build whichever index is missing. Cheap no-op once everything exists."""
    config = settings or get_settings()

    if not Path(config.db_path).exists():
        reindex(config.corpus_dir, config.db_path)

    if config.vectors_enabled and VectorStore(config.chroma_dir).count() == 0:
        build_index(config)


def hybrid_search(
    query: str,
    limit: int = 5,
    settings: Settings | None = None,
    store: VectorStore | None = None,
    embedder: EmbeddingProvider | None = None,
    version: str | None = None,
    doc_type: str | None = None,
) -> list[SearchResult]:
    """Return the best chunks from both retrievers, fused by rank.

    ``version`` and ``doc_type`` restrict both retrievers.
    """
    config = settings or get_settings()
    scope = normalize_version(version)
    kind = normalize_doc_type(doc_type)

    keyword_hits = search(
        config.db_path,
        query,
        limit=TOP_K_PER_RETRIEVER,
        version=scope,
        doc_type=kind,
    )
    vector_hits: list[dict] = []

    if config.vectors_enabled:
        try:
            store = store or VectorStore(config.chroma_dir)
            embedder = embedder or get_embedder(
                config.embeddings_mode, config.gemini_api_key, config.embedding_model
            )
            conditions = {}
            if scope:
                conditions["version"] = scope
            if kind:
                conditions["doc_type"] = kind

            where = None
            if len(conditions) == 1:
                where = conditions
            elif conditions:
                where = {"$and": [{key: value} for key, value in conditions.items()]}

            vector_hits = store.query(
                embedder.embed_query(query),
                n_results=TOP_K_PER_RETRIEVER,
                where=where,
            )
        except Exception:
            # A vector failure must never break search; BM25 still answers.
            vector_hits = []

    return _fuse(keyword_hits, vector_hits, limit=limit)


def _fuse(
    keyword_hits: list[SearchResult], vector_hits: list[dict], limit: int
) -> list[SearchResult]:
    """Reciprocal Rank Fusion of two ranked lists."""
    scores: dict[str, float] = {}
    sources: dict[str, set[str]] = {}
    results: dict[str, SearchResult] = {}

    for rank, hit in enumerate(keyword_hits):
        scores[hit.chunk_id] = scores.get(hit.chunk_id, 0.0) + 1.0 / (RRF_K + rank + 1)
        sources.setdefault(hit.chunk_id, set()).add("keyword")
        results[hit.chunk_id] = hit

    for rank, hit in enumerate(vector_hits):
        metadata = hit["metadata"]
        chunk_id = hit["chunk_id"]
        scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (RRF_K + rank + 1)
        sources.setdefault(chunk_id, set()).add("vector")
        results.setdefault(
            chunk_id,
            SearchResult(
                chunk_id=chunk_id,
                doc_id=metadata.get("doc_id", ""),
                title=metadata.get("title", ""),
                doc_type=metadata.get("doc_type", ""),
                version=metadata.get("version", ""),
                status=metadata.get("status", ""),
                source_url=metadata.get("source_url", ""),
                last_updated=metadata.get("last_updated", ""),
                section=metadata.get("section", ""),
                text=hit["text"],
                score=0.0,
            ),
        )

    fused = [
        replace(
            results[chunk_id],
            score=round(
                scores[chunk_id]
                - (SUPERSEDED_PENALTY if results[chunk_id].status == "superseded" else 0.0),
                6,
            ),
            matched_by="both" if len(sources[chunk_id]) == 2 else next(iter(sources[chunk_id])),
        )
        for chunk_id in scores
    ]
    fused.sort(key=lambda item: item.score, reverse=True)
    return fused[: max(1, min(limit, 20))]


if __name__ == "__main__":  # pragma: no cover - manual helper
    counts = build_index()
    print(
        f"indexed {counts['chunks']} chunks | keyword: {counts['keyword']} | vectors: {counts['vectors']}"
    )
