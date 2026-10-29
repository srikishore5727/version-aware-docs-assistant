"""Index freshness: is the index older than the corpus?

Editing a Markdown file does not update FTS5 or Chroma, so the assistant would
keep answering from the old text. This module reports that gap and can rebuild
on demand::

    python -m app.refresh            # rebuild only when the corpus changed
    python -m app.refresh --force    # rebuild regardless
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from app.config import Settings, get_settings
from app.ingest import load_chunks
from app.retriever import build_index
from app.vector_store import VectorStore


def corpus_mtime(corpus_dir: str | Path) -> float:
    """Newest modification time among the corpus files."""
    files = list(Path(corpus_dir).glob("*.md"))
    return max((path.stat().st_mtime for path in files), default=0.0)


def _iso(timestamp: float) -> str | None:
    if timestamp <= 0:
        return None
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat(timespec="seconds")


def index_status(settings: Settings | None = None) -> dict:
    """Counts, timestamps, and whether a refresh is needed."""
    config = settings or get_settings()
    chunks = list(load_chunks(config.corpus_dir))
    index_path = Path(config.db_path)
    indexed = index_path.exists()

    newest_source = corpus_mtime(config.corpus_dir)
    newest_index = index_path.stat().st_mtime if indexed else 0.0
    vectors = 0
    if config.vectors_enabled and Path(config.chroma_dir).exists():
        try:
            vectors = VectorStore(config.chroma_dir).count()
        except Exception:  # a corrupt store must not break the status endpoint
            vectors = 0

    return {
        "indexed": indexed,
        "documents": len({chunk.doc_id for chunk in chunks}),
        "chunks": len(chunks),
        "vectors": vectors,
        "corpus_updated": _iso(newest_source),
        "index_updated": _iso(newest_index),
        "stale": (not indexed) or newest_source > newest_index,
    }


def refresh(settings: Settings | None = None) -> dict:
    """Rebuild both indexes, then report the new status."""
    config = settings or get_settings()
    build_index(config)
    return index_status(config)


def refresh_if_stale(settings: Settings | None = None) -> dict:
    """Rebuild only when the corpus is newer than the index."""
    config = settings or get_settings()
    status = index_status(config)
    if status["stale"]:
        return refresh(config)
    return status


def _main() -> None:  # pragma: no cover - CLI
    import argparse

    parser = argparse.ArgumentParser(description="Rebuild the VADA indexes.")
    parser.add_argument("--force", action="store_true", help="rebuild even when fresh")
    args = parser.parse_args()

    status = refresh() if args.force else refresh_if_stale()
    print(json.dumps(status, indent=2))


if __name__ == "__main__":  # pragma: no cover - CLI
    _main()
