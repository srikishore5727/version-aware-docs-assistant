# PROJECT MEMORY - VADA

> Read this file first. It is the handoff document for any model or developer
> continuing this project. Keep it updated at the end of every working day.

**Last updated:** 28 October 2026 - Day 3 complete

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
├── .github/workflows/ci.yml   CI: install deps and run pytest
├── app/
│   ├── __init__.py            Version constant
│   ├── main.py                FastAPI app: /health, /, /api/search
│   ├── ingest.py              Front-matter parser, corpus loader, chunker
│   └── search.py              FTS5 index build, query building, BM25 search
├── corpus/                    12 sample Markdown docs (api-reference, migration-guide, changelog)
├── data/index/vada.db         Generated search index (gitignored)
├── tests/
│   ├── test_health.py         Tests for the scaffold
│   ├── test_ingest.py         Tests for parsing, loading, and chunking
│   └── test_search.py         Tests for query building, ranking, and the endpoint
├── docs/
│   └── PRD.md                 Product requirements (v1.0)
├── mockups/                   UX mockup, brand guidelines, design system (static, deployed)
├── requirements.txt
├── pytest.ini
├── README.md
└── PROJECT_MEMORY.md          This file
```

Planned additions: `app/answer.py`, `app/static/` (UI), `tests/golden_set.json`.

---

## 5. Ten-day plan

| Day | Feature | Status |
|---|---|---|
| 1 | App scaffold, `/health`, CI | **Done** |
| 2 | Document ingestion and chunking | **Done** |
| 3 | SQLite FTS5 index, `/api/search` | **Done** |
| 4 | Search UI with source cards | Next |
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

## 8. Current state (end of Day 3)

- `corpus/` has 12 sample Markdown docs: 4 api-reference, 4 migration-guide,
  4 changelog, across v1/v2/v3. v3 docs are `current`; v1 and v2 are `superseded`.
- `app/ingest.py` parses YAML front-matter and splits docs into heading-aware
  overlapping chunks. 12 docs produce 60 chunks.
- `app/search.py` builds a SQLite FTS5 index (porter stemming, BM25 with title
  and section boosted) and returns ranked chunks with full citation metadata.
- `POST /api/search` is live: `{"query": str, "limit": 5}` ->
  `{"query", "count", "results": [...]}`. Empty/wordless query -> `400`,
  no matches -> `count: 0` with an empty list.
- The index builds itself on first search, or via `python -m app.search`.
  Generated file: `data/index/vada.db` (gitignored).
- 30 tests pass locally (3 scaffold + 10 ingestion + 17 search) and in CI.
- No UI, no filters, no answer generation yet.

**Search API (stable - build on this next):**

```python
from app.search import search, reindex, ensure_index

reindex("corpus", "data/index/vada.db")          # force rebuild, returns chunk count
results = search("data/index/vada.db", "how do I paginate users", limit=5)
```

- `SearchResult` fields: `chunk_id, doc_id, title, doc_type, version, status,
  source_url, last_updated, section, text, score` (`score` = `-bm25`, higher is better)
- `build_match_query()` lowercases, strips stopwords, quotes every token, and ORs
  them, so user punctuation cannot produce an FTS5 syntax error.
- Raises `QueryError` when a query has no searchable words.
- Every chunk row is stored with its version/type, so Day 6 filters are a
  `WHERE version = ?` addition rather than a re-index.

---

## 9. Next task - Day 4: search UI with source cards

**Goal:** a usable single page that searches the corpus and shows the citation
behind every result.

**Build**

1. `app/static/index.html` (+ `app.css`, `app.js`) served by FastAPI at `/`.
   Reuse the design-system tokens from `mockups/design-system.html`
   (ink `#111318`, indigo `#4F46E5`, neutral greys, 8px spacing scale).
2. Layout: logo mark (`mockups/brand/logo-mark.svg`), one search input with a
   submit button, example-question chips, and a results area.
3. Results: one card per chunk showing title, section, a version badge
   (`v3` current / `v2` superseded), document type, `last_updated`, a short text
   excerpt, and a link to `source_url` opening in a new tab.
4. States: idle (examples), loading (skeleton or spinner), results, no results
   ("No matches in the indexed docs" - refined on Day 8).
5. Wire it to `POST /api/search` with `fetch`, `limit: 5`. Debounce not needed;
   submit on Enter or button click. Do not store the previous query in history.
6. Keep the JSON endpoints intact and add a test that `/` serves HTML containing
   the search form.

**Do not** add LLM answers or filters on Day 4. The answer panel is Day 5.

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
