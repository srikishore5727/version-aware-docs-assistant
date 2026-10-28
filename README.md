# Version-Aware Docs Assistant

Ask a question about a product's API and get a short answer grounded in the exact document and version it came from.

## Problem

A software vendor maintains API references, migration guides, and changelogs across multiple product versions. Developers waste time cross-referencing pages and still make integration errors, because no system answers a version-specific question with the exact source.

## Status

**Sprint 2 · Day 3 of 10 — complete.**

Application scaffold, sample corpus, heading-aware chunking, and BM25 keyword search are in place. `POST /api/search` returns ranked chunks with citation metadata. The UI is next.

## Quick start

Requires Python 3.10 or newer.

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload
```

- Health check: <http://127.0.0.1:8000/health>
- API docs: <http://127.0.0.1:8000/docs>

## Tests

```bash
pytest
```

## Corpus

`corpus/` holds 12 sample Markdown docs: 4 API reference pages, 4 migration
guides, and 4 changelog entries across versions v1, v2, and v3. Each file starts
with YAML front-matter:

```yaml
---
doc_id: api-users-create
title: Create user
product: Nimbus API
doc_type: api-reference        # api-reference | migration-guide | changelog
version: v3
status: current                # current | superseded
source_url: https://docs.nimbus.example/v3/users/create
last_updated: 2026-10-12
---
```

Load and chunk the corpus:

```python
from app.ingest import load_chunks

chunks = load_chunks("corpus")   # 12 docs -> 60 chunks today
```

Each chunk carries its document's version, type, status, source URL, and section
heading, so every later citation can name an exact source.

## Search

Chunks are indexed in SQLite FTS5 and ranked with BM25. The index builds itself
on the first search, or rebuild it explicitly:

```bash
python -m app.search            # 60 chunks -> data/index/vada.db
```

Query it:

```bash
curl -X POST http://127.0.0.1:8000/api/search ^
  -H "Content-Type: application/json" ^
  -d "{\"query\": \"how do I paginate users\", \"limit\": 3}"
```

```json
{
  "query": "how do I paginate users",
  "count": 1,
  "results": [
    {
      "chunk_id": "migration-v2-to-v3-pagination::0",
      "doc_id": "migration-v2-to-v3-pagination",
      "title": "Pagination changes in v3",
      "doc_type": "migration-guide",
      "version": "v3",
      "status": "current",
      "source_url": "https://docs.nimbus.example/migrate/v2-to-v3/pagination",
      "last_updated": "2026-10-08",
      "section": "Pagination changes in v3",
      "text": "v3 replaces page-based pagination with cursor pagination.",
      "score": 2.65
    }
  ]
}
```

- `limit` defaults to 5 and is capped at 20.
- An empty query returns `400`.
- A query with no matches returns `count: 0` and an empty `results` list.

## Ten-day plan

| Day | Feature | Status |
|---|---|---|
| 1 | Application scaffold, health endpoint, CI | Done |
| 2 | Document ingestion and chunking | Done |
| 3 | Keyword search (SQLite FTS5) and `/api/search` | Done |
| 4 | Search UI with source cards | Next |
| 5 | Grounded answer generation with citations | Planned |
| 6 | Version and document-type filters | Planned |
| 7 | Superseded-document handling | Planned |
| 8 | Not-found and low-confidence path | Planned |
| 9 | Golden-set evaluation in CI | Planned |
| 10 | Polish, docs, and v1.0.0 release | Planned |

## Documentation

- [Product requirements](docs/PRD.md)
- [Project memory](PROJECT_MEMORY.md) - read this before continuing the build
- [UX mockup](https://srikishore5727.github.io/version-aware-docs-assistant/ux-mockup.html)
- [Brand guidelines](https://srikishore5727.github.io/version-aware-docs-assistant/brand-guidelines.html)
- [Design system](https://srikishore5727.github.io/version-aware-docs-assistant/design-system.html)

## Author

Sri Kishore S
