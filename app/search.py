"""Keyword search over the chunked corpus using SQLite FTS5.

- build an FTS5 index over chunks produced by :mod:`app.ingest`
- run BM25-ranked queries and return chunk text with citation metadata
- filter by version (Day 8); document-type filtering arrives on Day 9

Ranking is plain keyword relevance. Embeddings are fused in :mod:`app.retriever`.
"""

from __future__ import annotations

import re
import sqlite3
from contextlib import closing
from dataclasses import asdict, dataclass
from pathlib import Path

from app.ingest import Chunk, load_chunks

DEFAULT_DB_PATH = Path("data/index/vada.db")
DEFAULT_CORPUS_DIR = Path("corpus")
DEFAULT_LIMIT = 5
MAX_LIMIT = 20

# Columns are declared so that FTS5 indexes only the human-readable fields.
# Every other column is stored but not tokenised.
CREATE_TABLE_SQL = """
CREATE VIRTUAL TABLE chunks USING fts5(
    chunk_id UNINDEXED,
    doc_id UNINDEXED,
    title,
    doc_type UNINDEXED,
    version UNINDEXED,
    status UNINDEXED,
    source_url UNINDEXED,
    last_updated UNINDEXED,
    section,
    text,
    tokenize = 'porter unicode61'
)
"""

INSERT_SQL = """
INSERT INTO chunks (
    chunk_id, doc_id, title, doc_type, version,
    status, source_url, last_updated, section, text
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""

# bm25() weights follow the column order above. Title and section are boosted
# so a document whose heading matches the question outranks a passing mention.
SELECT_SQL = """
SELECT
    chunk_id, doc_id, title, doc_type, version, status, source_url,
    last_updated, section, text,
    -bm25(chunks, 0.0, 0.0, 3.0, 0.0, 0.0, 0.0, 0.0, 0.0, 2.0, 1.0) AS score
FROM chunks
WHERE chunks MATCH ?
ORDER BY score DESC
LIMIT ?
"""

# Same query with a version constraint. ``version`` is an UNINDEXED FTS5
# column, so it can still be compared in WHERE.
SELECT_BY_VERSION_SQL = SELECT_SQL.replace(
    "WHERE chunks MATCH ?",
    "WHERE chunks MATCH ?\n  AND version = ?",
)

TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")

# Dropped from the query so "how do I create a user" ranks on "create"/"user".
# Porter stemming in the index already handles plurals and verb endings.
STOPWORDS = frozenset(
    """
    a an and are as at be been by can could do does did for from has have how
    i if in into is it its me my of on or our should so than that the their
    them then there these they this to was we were what when where which who
    why will with would you your
    """.split()
)


class QueryError(ValueError):
    """Raised when a query contains no searchable terms."""


@dataclass(frozen=True)
class SearchResult:
    """One ranked chunk, ready to become a citation card."""

    chunk_id: str
    doc_id: str
    title: str
    doc_type: str
    version: str
    status: str
    source_url: str
    last_updated: str
    section: str
    text: str
    score: float
    matched_by: str = "keyword"

    def to_dict(self) -> dict:
        return asdict(self)


def build_match_query(query: str) -> str:
    """Turn free text into a safe FTS5 MATCH expression.

    Every token is quoted, so punctuation cannot break the query, and tokens
    are OR-ed so a partial match still returns something. BM25 decides order.
    """
    tokens = [token.lower() for token in TOKEN_RE.findall(query or "")]
    if not tokens:
        raise QueryError("query must contain at least one word")

    meaningful = [token for token in tokens if token not in STOPWORDS]
    if not meaningful:
        meaningful = tokens

    seen: list[str] = []
    for token in meaningful:
        if token not in seen:
            seen.append(token)

    return " OR ".join(f'"{token}"' for token in seen)


def reindex(corpus_dir: str | Path = DEFAULT_CORPUS_DIR, db_path: str | Path = DEFAULT_DB_PATH) -> int:
    """Build the index from scratch. Returns the number of chunks indexed."""
    chunks = list(load_chunks(corpus_dir))
    if not chunks:
        raise QueryError(f"no chunks found in {corpus_dir}")

    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.unlink(missing_ok=True)

    with closing(sqlite3.connect(path)) as connection:
        connection.execute(CREATE_TABLE_SQL)
        connection.executemany(
            INSERT_SQL,
            [
                (
                    chunk.chunk_id,
                    chunk.doc_id,
                    chunk.title,
                    chunk.doc_type,
                    chunk.version,
                    chunk.status,
                    chunk.source_url,
                    chunk.last_updated,
                    chunk.section,
                    chunk.text,
                )
                for chunk in chunks
            ],
        )
        connection.commit()

    return len(chunks)


def build_index(chunks: list[Chunk], db_path: str | Path = DEFAULT_DB_PATH) -> int:
    """Build the index from an explicit list of chunks. Used by tests."""
    if not chunks:
        raise QueryError("cannot index an empty chunk list")

    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.unlink(missing_ok=True)

    with closing(sqlite3.connect(path)) as connection:
        connection.execute(CREATE_TABLE_SQL)
        connection.executemany(
            INSERT_SQL,
            [
                (
                    chunk.chunk_id,
                    chunk.doc_id,
                    chunk.title,
                    chunk.doc_type,
                    chunk.version,
                    chunk.status,
                    chunk.source_url,
                    chunk.last_updated,
                    chunk.section,
                    chunk.text,
                )
                for chunk in chunks
            ],
        )
        connection.commit()

    return len(chunks)


def ensure_index(
    corpus_dir: str | Path = DEFAULT_CORPUS_DIR,
    db_path: str | Path = DEFAULT_DB_PATH,
) -> int:
    """Create the index only if it does not exist yet.

    Returns the number of chunks indexed, or ``0`` when the index was already
    present. Called on the first search so a fresh clone works without a
    separate build step.
    """
    if Path(db_path).exists():
        return 0
    return reindex(corpus_dir, db_path)


def search(
    db_path: str | Path,
    query: str,
    limit: int = DEFAULT_LIMIT,
    version: str | None = None,
) -> list[SearchResult]:
    """Return BM25-ranked chunks for a query. Highest score first.

    ``version`` restricts results to one API version when given.
    """
    expression = build_match_query(query)
    bounded_limit = max(1, min(int(limit), MAX_LIMIT))
    path = Path(db_path)

    if not path.exists():
        raise FileNotFoundError(f"search index not found: {path}")

    if version:
        params: tuple = (expression, version, bounded_limit)
        statement = SELECT_BY_VERSION_SQL
    else:
        params = (expression, bounded_limit)
        statement = SELECT_SQL

    with closing(sqlite3.connect(path)) as connection:
        rows = connection.execute(statement, params).fetchall()

    return [SearchResult(*row) for row in rows]


if __name__ == "__main__":  # pragma: no cover - manual helper
    indexed = reindex()
    print(f"indexed {indexed} chunks into {DEFAULT_DB_PATH}")
