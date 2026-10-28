# PROJECT MEMORY - VADA

> Read this file first. It is the handoff document for any model or developer
> continuing this project. Keep it updated at the end of every working day.

**Last updated:** 28 October 2026 - Day 4 complete

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
| Retrieval | Hybrid: Gemini embeddings + Chroma, fused with BM25 (SQLite FTS5) via Reciprocal Rank Fusion |
| Chunking | Split by heading, about 500 characters, 80-character overlap |
| Answering | Gemini Flash via the OpenAI-compatible endpoint, receiving only retrieved chunks; must cite or return not found |
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
|-- .github/workflows/ci.yml   CI: install deps and run pytest
|-- app/
|   |-- __init__.py            Version constant
|   |-- main.py                FastAPI app: /health, /, /api/search
|   |-- config.py              Settings from env + .env
|   |-- ingest.py              Front-matter parser, corpus loader, chunker
|   |-- search.py              FTS5 index, BM25 keyword search
|   |-- embeddings.py          Gemini embeddings + offline hashing fallback
|   |-- vector_store.py        Chroma collection wrapper
|   `-- retriever.py           Hybrid retrieval (RRF fusion) + index build
|-- corpus/                    12 sample Markdown docs (api-reference, migration-guide, changelog)
|-- data/index/                Generated indexes: vada.db + chroma/ (gitignored)
|-- tests/
|   |-- conftest.py            Forces offline embeddings and temp indexes
|   |-- test_health.py
|   |-- test_ingest.py
|   |-- test_search.py
|   `-- test_hybrid.py
|-- docs/
|   |-- PRD.md                 Product requirements (v1.0)
|   `-- RAG_ARCHITECTURE.md    Pipeline, prompt contract, failure behaviour
|-- mockups/                   UX mockup, brand guidelines, design system (static, deployed)
|-- .env.example               Template for local secrets (real .env is gitignored)
|-- requirements.txt
|-- pytest.ini
|-- README.md
`-- PROJECT_MEMORY.md          This file
```

Planned additions: `app/answer.py`, `app/static/` (UI), `tests/golden_set.json`.

---

## 5. 20-day plan

| Day | Feature | Status |
|---|---|---|
| 1 | App scaffold, `/health`, CI | **Done** |
| 2 | Document ingestion and chunking | **Done** |
| 3 | SQLite FTS5 index, `/api/search` | **Done** |
| 4 | Embeddings, Chroma, hybrid retrieval | **Done** |
| 5 | Grounded answer generation, `/api/ask` | Next |
| 6 | Search UI with source cards | Planned |
| 7 | Answer panel and source cards | Planned |
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

---

## 6. Conventions

**Branches**

```
feat/04-search-ui
feat/05-grounded-answers
fix/<short-description>
docs/<short-description>
```

**Commits** - Conventional Commits:

```
feat: add FTS5 index and search endpoint
fix: correct version filter on search endpoint
docs: update project memory for day 4
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

## 8. Current state (end of Day 4)

- `corpus/` has 12 sample Markdown docs across v1/v2/v3 (v3 `current`, v1/v2
  `superseded`). Ingestion produces 60 chunks with full citation metadata.
- **Two indexes** exist for every chunk:
  - `data/index/vada.db` - SQLite FTS5, BM25 with title/section boosts
  - `data/index/chroma/` - Chroma collection, cosine, Gemini embeddings (768d)
- **Hybrid retrieval** (`app/retriever.py`) queries both and fuses with
  Reciprocal Rank Fusion (K=60). A vector failure silently falls back to BM25.
- `POST /api/search` returns `{"query", "mode", "count", "results"}` where
  `mode` is `hybrid` or `keyword`, and each result has `matched_by`
  (`keyword` / `vector` / `both`).
- Config comes from env + `.env`: `GEMINI_API_KEY`, `VADA_EMBEDDING_MODEL`,
  `VADA_LLM_MODEL`, `VADA_EMBEDDINGS` (`gemini` / `hash` / `off`).
- 42 tests pass locally (3 scaffold + 10 ingestion + 17 search + 12 hybrid).
  Tests force `VADA_EMBEDDINGS=hash`, so CI never calls the network.
- No UI, no filters, no answer generation yet.

**Retrieval API (stable - build on this next):**

```python
from app.retriever import build_index, hybrid_search

build_index()                                   # rebuild both indexes
results = hybrid_search("how do I paginate users", limit=5)
```

- `SearchResult` fields: `chunk_id, doc_id, title, doc_type, version, status,
  source_url, last_updated, section, text, score, matched_by`
- `build_index()` prints/logs `{"chunks", "keyword", "vectors"}` counts.
- Filters are not implemented yet; they arrive on Day 8 by passing `where` to
  Chroma and a `WHERE` clause to FTS5.

---

## 9. Next task - Day 5: grounded answer generation with citations

**Goal:** `POST /api/ask` returns a short answer that cites retrieved chunks, or
`not_found`. This is the RAG generation half.

**Build**

1. `app/answer.py`
   - `build_prompt(question, chunks)` implementing the contract in
     `docs/RAG_ARCHITECTURE.md` §6 (answer only from context, cite `[n]`,
     reply `NOT_FOUND`, state the version, under 80 words).
   - `answer_question(question, ...) -> Answer` with
     `status` (`answered` / `not_found`), `answer`, `sources`, `model`.
   - Gemini through the **OpenAI-compatible** endpoint
     `https://generativelanguage.googleapis.com/v1beta/openai/` using the
     `openai` SDK, model from `VADA_LLM_MODEL`, temperature 0.2, timeout 20 s.
   - Validate citations in code: every `[n]` must map to a retrieved chunk.
     Retry once, then return `not_found`. Never return an uncited answer.
   - No key -> deterministic extractive fallback (top chunk's first sentences
     plus `[1]`), so the demo and tests work offline.
2. `POST /api/ask` in `app/main.py`: `{"question", "version"?, "doc_type"?}`.
   `400` for empty question, `503` if retrieval is unavailable.
3. Tests: prompt contains the rules, citation validation rejects bad markers,
   `NOT_FOUND` maps to the not-found status, endpoint returns sources.

**Do not** build the UI on Day 5. That is Day 6.

---

## 10. Guardrails

- Retrieval is **hybrid**: vector search (Gemini embeddings + Chroma) fused with BM25.
  Both paths must stay working; BM25 is the no-key fallback. See `docs/RAG_ARCHITECTURE.md`.
- No LangChain, no re-rankers, no chat memory. Keep the pipeline readable.
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
| 3 | 28 Oct 2026 | SQLite FTS5 index + BM25 `POST /api/search` (`app/search.py`), 30 tests |
| 4 | 28 Oct 2026 | Gemini embeddings + Chroma + hybrid RRF retrieval (`app/embeddings.py`, `vector_store.py`, `retriever.py`), 42 tests |
