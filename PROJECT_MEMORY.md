# PROJECT MEMORY - VADA

> Read this file first. It is the handoff document for any model or developer
> continuing this project. Keep it updated at the end of every working day.

**Last updated:** 28 October 2026 - Day 9 complete

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
|   |-- main.py                FastAPI app: API routes + UI mount
|   |-- config.py              Settings from env + .env
|   |-- ingest.py              Front-matter parser, corpus loader, chunker
|   |-- search.py              FTS5 index, BM25 keyword search
|   |-- embeddings.py          Gemini embeddings + offline hashing fallback
|   |-- vector_store.py        Chroma collection wrapper
|   |-- retriever.py           Hybrid retrieval (RRF fusion) + index build
|   |-- answer.py              Prompt contract, citation checks, Gemini call
|   `-- static/                Search UI: index.html, app.css, app.js
|-- corpus/                    12 sample Markdown docs (api-reference, migration-guide, changelog)
|-- data/index/                Generated indexes: vada.db + chroma/ (gitignored)
|-- tests/
|   |-- conftest.py            Forces offline embeddings and temp indexes
|   |-- test_health.py
|   |-- test_ingest.py
|   |-- test_search.py
|   |-- test_hybrid.py
|   |-- test_answer.py
|   `-- test_ui.py
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

Planned additions: `tests/golden_set.json`, `app/metrics.py`.

---

## 5. 20-day plan

| Day | Feature | Status |
|---|---|---|
| 1 | App scaffold, `/health`, CI | **Done** |
| 2 | Document ingestion and chunking | **Done** |
| 3 | SQLite FTS5 index, `/api/search` | **Done** |
| 4 | Embeddings, Chroma, hybrid retrieval | **Done** |
| 5 | Grounded answer generation, `/api/ask` | **Done** |
| 6 | Search UI with source cards | **Done** |
| 7 | Answer panel and citation links | **Done** |
| 8 | Version filter | **Done** |
| 9 | Document-type filter | **Done** |
| 10 | Superseded-document handling | Next |
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

## 8. Current state (end of Day 9)

- `corpus/` has 12 sample Markdown docs across v1/v2/v3 (v3 `current`, v1/v2
  `superseded`). Ingestion produces 60 chunks with full citation metadata.
- **Two indexes** exist for every chunk:
  - `data/index/vada.db` - SQLite FTS5, BM25 with title/section boosts
  - `data/index/chroma/` - Chroma collection, cosine, Gemini embeddings (768d)
- **Hybrid retrieval** (`app/retriever.py`): Reciprocal Rank Fusion (K=60) of
  both lists. A vector failure silently falls back to BM25.
- **Filters** work end to end and combine:
  - `normalize_version()` -> `SUPPORTED_VERSIONS` (`v1`, `v2`, `v3`)
  - `normalize_doc_type()` -> `SUPPORTED_DOC_TYPES` (`api-reference`,
    `migration-guide`, `changelog`), accepts spaces/underscores and any case
  - FTS5 gets parameterised `AND column = ?` clauses built from a filter list;
    Chroma gets a single condition or `{"$and": [...]}`
  - API responses echo `version` and `doc_type`
- **Grounded generation** (`app/answer.py`) is live behind `POST /api/ask`.
  Gemini answers only from the numbered context; citations are validated in
  code (`[1]` and grouped `[1, 3]`); one retry, then `not_found`.
- **Answer UI** at `/`: calls `POST /api/ask`, renders an answer panel with
  `[n]` links, then one source card per citation (`id="source-n"`, `:target`
  outline). `not_found` is a calm panel. A failed ask falls back to
  `/api/search`. Version and document-type `<select>`s scope the request and
  are named in the result line.
- Config from env + `.env`: `GEMINI_API_KEY`, `VADA_EMBEDDING_MODEL`
  (`gemini-embedding-001`), `VADA_LLM_MODEL` (`gemini-3.1-flash-lite-preview`),
  `VADA_EMBEDDINGS` (`gemini` / `hash` / `off`).
- 90 tests pass locally (12 more filter tests). CI forces `VADA_EMBEDDINGS=hash`
  and a blank key.
- **Known gap:** vector search always returns `limit` neighbours, so a nonsense
  query still retrieves cards. Day 11 adds the similarity floor.

**APIs (stable - build on these next):**

```python
from app.retriever import build_index, hybrid_search, normalize_version
from app.answer import generate_answer

chunks = hybrid_search("pagination", limit=5, version="v3", doc_type="migration-guide")
answer = generate_answer("pagination", chunks)
```

- `SearchResult` fields: `chunk_id, doc_id, title, doc_type, version, status,
  source_url, last_updated, section, text, score, matched_by`
- `Answer` fields: `status, answer, sources, model, reason`; each source
  carries `index`, the citation metadata, and its `text`.
- Every chunk already has `status` (`current` / `superseded`), which is what
  Day 10 needs.

---

## 9. Next task - Day 10: superseded-document handling

**Goal:** when an answer leans on a retired version, say so - and never let a
superseded chunk quietly outrank a current one.

**Build**

1. `app/retriever.py`: in `_fuse`, apply a small, documented penalty to chunks
   whose `status` is `superseded` (e.g. `SUPERSEDED_PENALTY = 0.0015`) so
   near-ties favour `current`. Do not filter retired docs out - they are often
   the right answer for a v2 question.
2. `app/answer.py`: add `notice: str = ""` to `Answer` and `to_dict()`. When any
   cited source is `superseded`, set a sentence naming the version(s), e.g.
   "This answer cites v2, which is superseded. See v3 for the current API."
   Keep it out of the model's text; the model already states the version.
3. Prompt: add one rule - prefer `current` documents when both answer the
   question, and say which version you used.
4. UI: render `notice` as a small amber banner above the answer body; the
   existing `superseded` badge stays on the card.
5. Tests: penalty flips a near-tie, current still wins normally, notice set for
   superseded citations only, empty when all sources are current.
6. Document the behaviour in `docs/RAG_ARCHITECTURE.md`.

**Do not** add the relevance threshold (Day 11) or confidence scoring (Day 14).

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
| 5 | 28 Oct 2026 | Grounded answer generation with validated citations (`app/answer.py`, `POST /api/ask`), 60 tests |
| 6 | 28 Oct 2026 | Search UI with source cards (`app/static/`, `StaticFiles`, `/api` metadata), 65 tests |
| 7 | 28 Oct 2026 | Answer panel with linked citations (`/api/ask` in the UI, `:target` source cards, retrieval fallback), 66 tests |
| 8 | 28 Oct 2026 | Version filter across FTS5, Chroma and the UI (`normalize_version`, scoped `/api/search` + `/api/ask`), 78 tests |
| 9 | 28 Oct 2026 | Document-type filter plus combined scopes (`normalize_doc_type`, parameterised FTS filters, second UI selector), 90 tests |
