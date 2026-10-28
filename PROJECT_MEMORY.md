# PROJECT MEMORY - VADA

> Read this file first. It is the handoff document for any model or developer
> continuing this project. Keep it updated at the end of every working day.

**Last updated:** 28 October 2026 - Day 2 complete

---

## 1. What we are building

**VADA (Version-Aware Docs Assistant)** is an internal tool for a software vendor.
A developer asks a question in plain English and receives a short answer that cites
the exact document, section, and product version it came from.

The product exists to solve this problem from the Sprint 2 brief:

> A software vendor maintains API references, migration guides, and changelogs across
> product versions, but developers waste time and make integration errors because no
> system answers version-specific questions with the exact source.

**Primary users:** integration developers.
**Core promise:** every answer is traceable to a source, or the product says "not found".

---

## 2. Locked decisions

These are settled. Do not change them without updating `docs/PRD.md`.

| Decision | Value |
|---|---|
| Retrieval | Keyword search with BM25 (SQLite FTS5). No embeddings in v1. |
| Chunking | Split by heading, about 500 characters, 80-character overlap |
| Answering | LLM receives only retrieved chunks; must cite or return not found |
| Citations | Inline `[1]`, `[2]` plus source cards with type, version, section, date |
| Filters | Version and document type |
| Auth | None in v1 |
| Conversation memory | None in v1 |
| Docs corpus | Markdown with YAML front-matter |
| Sprint length | 10 working days (compressed from the 20-day window) |

---

## 3. Tech stack

| Layer | Choice |
|---|---|
| Language | Python 3.10+ |
| Web framework | FastAPI |
| Server | Uvicorn |
| Storage / index | SQLite with FTS5 |
| Testing | pytest + httpx |
| CI | GitHub Actions |
| Frontend | Single-page HTML, same tokens as the design system |

No database server, no vector store, no build step. Keep it that simple.

---

## 4. Repository map

```
version-aware-docs-assistant/
├── .github/workflows/ci.yml   CI: install deps and run pytest
├── app/
│   ├── __init__.py            Version constant
│   ├── main.py                FastAPI app: /health and /
│   └── ingest.py              Front-matter parser, corpus loader, chunker
├── corpus/                    12 sample Markdown docs (api-reference, migration-guide, changelog)
├── tests/
│   ├── test_health.py         Tests for the scaffold
│   └── test_ingest.py         Tests for parsing, loading, and chunking
├── docs/
│   └── PRD.md                 Product requirements (v1.0)
├── mockups/                   UX mockup, brand guidelines, design system (static, deployed)
├── requirements.txt
├── pytest.ini
├── README.md
└── PROJECT_MEMORY.md          This file
```

Planned additions: `app/search.py`, `app/answer.py`, `app/static/` (UI),
`tests/golden_set.json`.

---

## 5. Ten-day plan

| Day | Feature | Status |
|---|---|---|
| 1 | App scaffold, `/health`, CI | **Done** |
| 2 | Document ingestion and chunking | **Done** |
| 3 | SQLite FTS5 index, `/api/search` | Next |
| 4 | Search UI with source cards | Planned |
| 5 | Grounded answer generation with citations | Planned |
| 6 | Version and document-type filters | Planned |
| 7 | Superseded-document handling | Planned |
| 8 | Not-found and low-confidence path | Planned |
| 9 | Golden-set evaluation in CI | Planned |
| 10 | Polish, docs, v1.0.0 release | Planned |

---

## 6. Conventions

**Branches**

```
feat/03-bm25-search
feat/04-search-ui
fix/<short-description>
docs/<short-description>
```

**Commits** - Conventional Commits:

```
feat: add corpus loader and chunker
fix: correct version filter on search endpoint
docs: update project memory for day 3
test: add golden-set evaluation
```

**Pull requests**

- One feature per PR, merged the same day it is opened.
- Title follows the same convention as commits.
- Body includes: summary, what changed, how to test, acceptance criteria.
- Use **Squash and merge**, then delete the feature branch.
- **Never delete `gh-pages`** - it serves the live mockup site.

---

## 7. How to run and test

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
source .venv/bin/activate       # macOS / Linux
pip install -r requirements.txt

uvicorn app.main:app --reload   # http://127.0.0.1:8000
pytest                          # run tests
```

---

## 8. Current state (end of Day 2)

- FastAPI app starts and serves `/health` and `/`.
- CI workflow runs on every push and pull request to `main`.
- `corpus/` has 12 sample Markdown docs: 4 api-reference, 4 migration-guide,
  4 changelog, across v1/v2/v3. v3 docs are `current`; v1 and v2 are `superseded`.
- `app/ingest.py` parses YAML front-matter, loads documents, and splits them into
  heading-aware overlapping chunks. 12 docs currently produce 60 chunks.
- `pyyaml==6.0.2` added to `requirements.txt`.
- 13 tests pass locally (3 scaffold + 10 ingestion) and in CI.
- No search index, no endpoints beyond `/health` and `/`, no UI, no answering yet.

**Ingestion API (stable - build on this next):**

```python
from app.ingest import load_chunks, load_documents

docs = load_documents("corpus")            # list[Document]
chunks = load_chunks("corpus", size=500, overlap=80)   # list[Chunk]
```

- `Document` fields: `doc_id, title, product, doc_type, version, status,
  source_url, last_updated, body, path`
- `Chunk` fields: `chunk_id ("<doc_id>::<n>"), doc_id, title, doc_type, version,
  status, source_url, last_updated, section, text, position`
- Missing `version` / `doc_type` default to `unknown`; missing `status` defaults to `current`.
- Raises `IngestionError` on unclosed front-matter, missing `doc_id`/`title`, or duplicate `doc_id`.

---

## 9. Next task - Day 3: keyword search with SQLite FTS5

**Goal:** index chunks and return ranked results for a query.

**Build**

1. `app/search.py`
   - `build_index(chunks, db_path)` - create an FTS5 table over `chunk.text`
     plus metadata columns (doc_id, version, doc_type, status, section, source_url)
   - `search(query, db_path, limit=10)` - BM25-ranked (`ORDER BY rank`),
     return chunk text plus citation metadata
   - Escape / quote user input safely for FTS5 (avoid syntax errors on `-`, `"`, etc.)
2. `POST /api/search` (or `GET /api/search?q=`) in `app/main.py`
   - Request: `{"query": str, "limit": int = 10}`
   - Response: `{"query": ..., "results": [{"chunk_id", "text", "score",
     "doc_id", "title", "doc_type", "version", "section", "source_url"}]}`
   - Empty or whitespace query returns `400`
3. Rebuild the index on startup if it is missing (in-memory or `data/index.db`).
4. Tests: index build, ranked ordering, metadata passthrough, no-match returns
   empty list, punctuation-heavy query does not crash.

**Do not** add the answer generator or UI on Day 3. Filters are Day 6.

---

## 10. Guardrails

- v1 is **keyword retrieval only**. Do not introduce embeddings or a vector database.
- Every answer must include a citation or the not-found state. No uncited answers.
- No authentication, no chat memory, no code generation, no mobile app.
- Keep each PR to one feature. If a task grows, split it.
- Update this file at the end of each day: status, current state, next task.

---

## 11. Key links

| Item | Link |
|---|---|
| Repository | https://github.com/srikishore5727/version-aware-docs-assistant |
| Live mockup | https://srikishore5727.github.io/version-aware-docs-assistant/ |
| PRD | `docs/PRD.md` |
| Brand guidelines | https://srikishore5727.github.io/version-aware-docs-assistant/brand-guidelines.html |
| Design system | https://srikishore5727.github.io/version-aware-docs-assistant/design-system.html |

---

## 12. Daily log

| Day | Date | What shipped |
|---|---|---|
| 0 | 26 Oct 2026 | PRD v1.0 merged; UX mockup, brand guidelines, design system deployed |
| 1 | 27 Oct 2026 | FastAPI scaffold, `/health`, tests, CI |
| 2 | 28 Oct 2026 | Sample corpus (12 docs) + ingestion and heading-aware chunking (`app/ingest.py`), 13 tests |
