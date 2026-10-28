# Version-Aware Docs Assistant

Ask a question about a product's API and get a short answer grounded in the exact document and version it came from.

## Problem

A software vendor maintains API references, migration guides, and changelogs across multiple product versions. Developers waste time cross-referencing pages and still make integration errors, because no system answers a version-specific question with the exact source.

## Status

**Sprint 2 · Day 6 of 20 — complete.**

Scaffold, corpus, chunking, hybrid retrieval, grounded answers with validated
citations, and the search UI are working. The answer panel is next.

## Quick start

Requires Python 3.10 or newer.

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env       # add GEMINI_API_KEY for hybrid mode
uvicorn app.main:app --reload
```

- Health check: <http://127.0.0.1:8000/health>
- Search UI: <http://127.0.0.1:8000/>
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

Chunks are indexed twice: a SQLite FTS5 keyword index and a Chroma vector
index built from Gemini embeddings. Queries hit both and are merged with
Reciprocal Rank Fusion, so paraphrases and exact identifiers both work.

```bash
python -m app.retriever          # rebuild both indexes (60 chunks)
```

Without an API key the app runs in keyword-only mode; with `GEMINI_API_KEY`
set it returns `"mode": "hybrid"`. Each result includes `matched_by`
(`keyword`, `vector`, or `both`).

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

## Ask

`POST /api/ask` retrieves chunks, asks Gemini to answer using only those chunks,
then validates every citation in code.

```bash
curl -X POST http://127.0.0.1:8000/api/ask ^
  -H "Content-Type: application/json" ^
  -d "{\"question\": \"Which field replaced user_name in v3?\"}"
```

```json
{
  "question": "Which field replaced user_name in v3?",
  "status": "answered",
  "answer": "In v3, the `display_name` field replaced `user_name` [3].",
  "sources": [
    {
      "index": 3,
      "title": "Create user",
      "doc_type": "api-reference",
      "version": "v3",
      "section": "Request body",
      "source_url": "https://docs.nimbus.example/v3/users/create"
    }
  ],
  "model": "gemini-3.1-flash-lite-preview",
  "reason": "",
  "mode": "hybrid"
}
```

Behaviour:

- `status: not_found` when no chunk matches, the model refuses, or citations
  cannot be verified. A failed answer is never returned.
- Citations are checked in code: `[n]` must refer to a retrieved chunk, and
  grouped forms like `[1, 3]` are supported.
- Without an API key the endpoint returns a verbatim quote from the top chunk
  plus `[1]`, with `"model": "extractive"`.

## Interface

Open <http://127.0.0.1:8000/> for the search UI. It is plain HTML, CSS, and one
JavaScript file served from `app/static/`, styled with the approved brand
tokens - no build step.

- One question box, example chips, and one card per retrieved chunk.
- Every card shows the version, whether it is `current` or `superseded`, the
  document type, the section, the last-updated date, an excerpt, and a link to
  the exact source page.
- The card footer names how the chunk was found (`keyword`, `vector`, or both).
- States: idle, loading, results, no matches, and a network error.
- The JSON service map moved to `/api`; `/health`, `/docs`, and `/api/*` are
  unchanged.

## 20-day plan

| Day | Feature | Status |
|---|---|---|
| 1 | Application scaffold, health endpoint, CI | Done |
| 2 | Document ingestion and chunking | Done |
| 3 | Keyword search (SQLite FTS5) and `/api/search` | Done |
| 4 | Embeddings, Chroma, hybrid retrieval | Done |
| 5 | Grounded answer generation with citations | Done |
| 6 | Search UI with source cards | Done |
| 7 | Answer panel and citation links | Next |
| 8 | Version filter | Planned |
| 9 | Document-type filter | Planned |
| 10 | Superseded-document handling | Planned |
| 11 | Not-found and low-confidence path | Planned |
| 12 | Golden-set evaluation harness | Planned |
| 13 | Evaluation in CI | Planned |
| 14 | Confidence and explanation panel | Planned |
| 15 | Logging and metrics | Planned |
| 16 | Answer feedback capture | Planned |
| 17 | Index refresh job | Planned |
| 18 | Accessibility and dark mode | Planned |
| 19 | Performance tuning | Planned |
| 20 | v1.0.0 release | Planned |

## Documentation

- [Product requirements](docs/PRD.md)
- [RAG architecture](docs/RAG_ARCHITECTURE.md) - pipeline, prompt contract, failure behaviour
- [Project memory](PROJECT_MEMORY.md) - read this before continuing the build
- [UX mockup](https://srikishore5727.github.io/version-aware-docs-assistant/ux-mockup.html)
- [Brand guidelines](https://srikishore5727.github.io/version-aware-docs-assistant/brand-guidelines.html)
- [Design system](https://srikishore5727.github.io/version-aware-docs-assistant/design-system.html)

## Author

Sri Kishore S
