# PROJECT MEMORY - VADA

> Read this file first. It is the handoff document for any model or developer
> continuing this project. Keep it updated at the end of every working day.

**Last updated:** 28 October 2026 - Day 6 complete

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

## 8. Current state (end of Day 6)

- `corpus/` has 12 sample Markdown docs across v1/v2/v3 (v3 `current`, v1/v2
  `superseded`). Ingestion produces 60 chunks with full citation metadata.
- **Two indexes** exist for every chunk:
  - `data/index/vada.db` - SQLite FTS5, BM25 with title/section boosts
  - `data/index/chroma/` - Chroma collection, cosine, Gemini embeddings (768d)
- **Hybrid retrieval** (`app/retriever.py`): Reciprocal Rank Fusion (K=60) of
  both lists. A vector failure silently falls back to BM25.
- **Grounded generation** (`app/answer.py`) is live behind `POST /api/ask`.
  Gemini answers only from the numbered context; citations are validated in
  code (`[1]` and grouped `[1, 3]`); one retry, then `not_found`.
- **Search UI** at `/` (`app/static/`): plain HTML/CSS/JS, brand tokens, card
  per chunk with version/status/type/section/date/excerpt/source link. Calls
  `POST /api/search` with `limit: 5`. States: idle, loading, results, empty,
  error. `StaticFiles` is mounted **last** so API routes win; JSON metadata
  moved to `/api`.
- `POST /api/search` returns `{"query", "mode", "count", "results"}`.
  `POST /api/ask` returns `{"question", "mode", "status", "answer", "sources",
  "model", "reason"}`.
- Config from env + `.env`: `GEMINI_API_KEY`, `VADA_EMBEDDING_MODEL`
  (`gemini-embedding-001`), `VADA_LLM_MODEL` (`gemini-3.1-flash-lite-preview`),
  `VADA_EMBEDDINGS` (`gemini` / `hash` / `off`).
- 65 tests pass locally (3 scaffold + 10 ingestion + 17 search + 12 hybrid +
  18 answer + 5 UI). CI forces `VADA_EMBEDDINGS=hash` and a blank key.
- **Known gap:** vector search always returns `limit` neighbours, so a nonsense
  query still shows cards. The UI's empty state only triggers in keyword mode
  today; Day 11 adds the relevance floor that makes `not_found` reachable.

**APIs (stable - build on these next):**

```python
from app.retriever import build_index, hybrid_search
from app.answer import generate_answer

build_index()                                   # rebuild both indexes
chunks = hybrid_search("how do I paginate users", limit=5)
answer = generate_answer("how do I paginate users", chunks)   # Answer
```

- `SearchResult` fields: `chunk_id, doc_id, title, doc_type, version, status,
  source_url, last_updated, section, text, score, matched_by`
- `Answer` fields: `status, answer, sources, model, reason`; `sources` are
  citation cards carrying `index` and the chunk metadata.
- Filters are not implemented yet; Day 8 adds them to `hybrid_search`.

---

## 9. Next task - Day 7: answer panel with citation links

**Goal:** put the grounded answer above the source cards, and make every `[n]`
marker in the answer jump to the card it cites.

**Build**

1. In `app/static/index.html`, add an answer panel inside `#results` (before the
   card list) with: a status line ("Answered for v3"), the answer body, and a
   model/mode footnote.
2. `app.js`: call `POST /api/ask` instead of `/api/search` (same query, same
   limit). Render `status: answered` -> answer text + `sources` cards;
   `status: not_found` -> calm empty state with the reason, not an error.
3. Turn `[1]` and `[1, 3]` in the answer into `<a href="#source-1">` links.
   Build them with DOM nodes (text split on `/(\[\d+(?:\s*,\s*\d+)*\])/`), never
   `innerHTML`, and give each source card `id="source-n"` plus a
   `:target` highlight style.
4. Keep `/api/search` and the existing cards reachable: if the answer fails to
   load, still show retrieval results rather than nothing.
5. Keep the loading skeleton, `aria-busy`, and `aria-live` behaviour.
6. Tests: `/` HTML contains `id="answer"`; a unit test for the citation-split
   helper if it moves into Python; endpoint contract stays covered.

**Do not** add filters, tone controls, or confidence scores on Day 7.

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
