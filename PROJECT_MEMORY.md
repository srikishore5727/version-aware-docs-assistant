# PROJECT MEMORY - VADA

> Read this file first. It is the handoff document for any model or developer
> continuing this project. Keep it updated at the end of every working day.

**Last updated:** 28 October 2026 - Day 5 complete

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
| 5 | Grounded answer generation, `/api/ask` | **Done** |
| 6 | Search UI with source cards | Next |
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

## 8. Current state (end of Day 5)

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
- `POST /api/search` returns `{"query", "mode", "count", "results"}`.
  `POST /api/ask` returns `{"question", "mode", "status", "answer", "sources",
  "model", "reason"}`.
- Config from env + `.env`: `GEMINI_API_KEY`, `VADA_EMBEDDING_MODEL`
  (`gemini-embedding-001`), `VADA_LLM_MODEL` (`gemini-3.1-flash-lite-preview`),
  `VADA_EMBEDDINGS` (`gemini` / `hash` / `off`).
- 60 tests pass locally (3 scaffold + 10 ingestion + 17 search + 12 hybrid +
  18 answer). CI forces `VADA_EMBEDDINGS=hash` and a blank key, so it never
  calls the network.
- Verified live against Gemini: `display_name` replacement, `page=2` -> 400,
  token expiry 60 minutes, rate-limit question -> `not_found`.
- No UI and no filters yet.

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

## 9. Next task - Day 6: search UI with source cards

**Goal:** a usable single page at `/` that searches the corpus, shows the
grounded answer, and exposes the citation behind it.

**Build**

1. Serve `app/static/` from FastAPI (`StaticFiles`), so `/` is the UI and
   `/docs`, `/health`, `/api/*` keep working. Keep the JSON root metadata at
   `/api` if it would otherwise be shadowed.
2. Reuse the design tokens already approved in `mockups/design-system.html`
   (ink `#111318`, indigo `#4F46E5`, 8px spacing scale) and the logo mark.
   No Tailwind, no build step - plain HTML, CSS, and one `app.js`.
3. Layout: brand row, one question input with submit, example-question chips,
   then an answer panel followed by source cards.
4. Call `POST /api/ask` and render:
   - `answered`: answer text with `[n]` markers turned into links that scroll to
     the matching source card; version badge on every card.
   - `not_found`: a calm "not in the indexed docs" state, not an error toast.
5. States: idle, loading (disable submit), answered, not found, network error.
6. Keep it accessible: labels on inputs, focus rings, `aria-live` on results.
7. Test that `/` returns HTML containing the form and that `/docs` still works.

**Do not** add filters or confidence scoring on Day 6. Those are Days 8 and 14.

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
