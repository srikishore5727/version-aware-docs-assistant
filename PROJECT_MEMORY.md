# PROJECT MEMORY - VADA

> Read this file first. It is the handoff document for any model or developer
> continuing this project. Keep it updated at the end of every working day.

**Last updated:** 29 October 2026 - v1.0.0 released

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
| 10 | Superseded-document handling | **Done** |
| 11 | Not-found and low-confidence path | **Done** |
| 12 | Golden-set evaluation harness | **Done** |
| 13 | Evaluation in CI | **Done** |
| 14 | Confidence and explanation panel | **Done** |
| 15 | Logging and metrics | **Done** |
| 16 | Answer feedback capture | **Done** |
| 17 | Index refresh job | **Done** |
| 18 | Accessibility and dark mode | **Done** |
| 19 | Performance tuning | **Done** |
| 20 | v1.0.0 release | **Done** |

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

## 8. Current state (end of Day 20 - v1.0.0)

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
- **Superseded documents** are demoted, never hidden:
  - `_fuse()` subtracts `SUPERSEDED_PENALTY = 0.0015` from any chunk whose
    `status` is `superseded`, after fusion and before sorting. One RRF rank
    step is ~0.016, so the penalty only breaks near-ties.
  - `superseded_notice(sources)` in `app/answer.py` returns a sentence naming
    every retired version among the *validated* citations, or `""`.
  - `Answer.notice` is exposed in `to_dict()` and rendered as an amber banner
    above the answer body. The model cannot suppress it.
- **Relevance floor** (`MIN_SIMILARITY = 0.60`, `app/retriever.py`):
  - calibrated on 14 in-scope questions (best 0.63-0.86) and 10 out-of-scope
    asks (best 0.52-0.59) with `gemini-embedding-001`
  - vector hits below the floor are dropped before fusion; if the best hit is
    below it, retrieval returns `[]` even when BM25 found an incidental word
  - only applied when `embedder.calibrated` is true (`GeminiEmbeddings` yes,
    `HashingEmbeddings` no); a vector failure skips the gate
- Config from env + `.env`: `GEMINI_API_KEY`, `VADA_EMBEDDING_MODEL`
  (`gemini-embedding-001`), `VADA_LLM_MODEL` (`gemini-3.1-flash-lite-preview`),
  `VADA_EMBEDDINGS` (`gemini` / `hash` / `off`).
- 103 tests pass locally (6 more threshold tests). CI forces
  `VADA_EMBEDDINGS=hash` and a blank key, so the floor is exercised through
  injected fakes, never the hashing numbers.
- **Golden set** (`eval/golden_set.json`, `app/evaluate.py`): 30 questions over
  all 12 docs, scored retrieval-only. Baseline with real Gemini embeddings:
  **recall@5 1.00, MRR 0.91**; hermetic hashing baseline **0.93**.
- **CI gate**: `python -m app.evaluate --min-recall 0.85` runs after pytest,
  exits `1` below target, and uploads `data/eval/report.json` as an artefact.
- **Confidence** is computed, never generated: `Answer.__post_init__` fills
  `confidence` (`high` / `medium` / `low`) and `reasons` from the validated
  sources and the model name. Rules: high = 2+ sources, one version, all
  current; medium = single source, mixed versions, or superseded; low =
  not-found or extractive. Exposed in `to_dict()` and rendered as a quiet row
  under the answer head.
- **Observability** (`app/observability.py`): one JSON line per `/api/*` request
  (`format_event()`), plus process-local counters exposed at `GET /api/metrics`
  (`requests`, `answered`, `not_found`, `errors`, `avg_ms`, `max_ms`,
  `slowest_endpoint`). `/health` and static files are not counted. Middleware
  lives in `app/main.py`; counters reset in tests via `metrics.reset()`.
- **Feedback** (`app/feedback.py`): SQLite `data/feedback.db` (gitignored,
  `VADA_FEEDBACK_DB`), table `feedback(id, created_at, question, verdict,
  status, version, doc_type)`. `POST /api/feedback` returns `201` with the id,
  `422` for an unknown verdict, `400` for an empty question;
  `GET /api/feedback` returns counts plus the 20 most recent rows. Two quiet
  buttons appear under an answered response.
- **Index refresh** (`app/refresh.py`): `index_status()` reports doc/chunk/vector
  counts plus corpus and index timestamps and a `stale` flag; `refresh()` and
  `refresh_if_stale()` rebuild; `python -m app.refresh [--force]` is the CLI.
  `GET /api/index/status` is read-only; there is no unauthenticated rebuild
  endpoint.
- **Accessibility + theme** (`app/static/`): skip link to a `tabindex="-1"`
  results region, `role="status"` live hint, labels on every control, focus
  moved to the answer panel after a response (`focusResult()`), visible
  `:focus-visible` rings, and a full `prefers-color-scheme: dark` token block.
  `prefers-reduced-motion` disables the shimmer and hover lifts. No theme
  toggle; `meta color-scheme` + `color-scheme` handle native controls.
- **Answer cache** (`app/cache.py`): thread-safe LRU of `/api/ask` payloads,
  keyed by question (case/space normalised), limit, version, doc type, and the
  FTS5 mtime. `VADA_CACHE_SIZE` defaults to 128; `0` disables. Hits echo
  `"cached": true`; `generation_failed` answers are never stored. `/api/metrics`
  exposes `cache_hits` / `cache_misses`.
- **Benchmark** (`app/benchmark.py`): `python -m app.benchmark` runs the 30
  golden questions twice with a stubbed citation, so no model call. Latest:
  cold p50 ~1.17 s (Gemini embeddings), warm p50 ~0 ms, 30/60 hits by design.
  Live second ask: 5.66 s -> 98 ms.
- 160 tests pass locally.
- **Release**: `app/__init__.py` is `1.0.0`, `CHANGELOG.md` records the full
  feature set, and the README carries CI/Python badges plus a 20/20 plan table.

**APIs (stable - build on these next):**

```python
from app.retriever import build_index, hybrid_search, normalize_version
from app.answer import generate_answer

chunks = hybrid_search("pagination", limit=5, version="v3", doc_type="migration-guide")
answer = generate_answer("pagination", chunks)
answer.notice  # "" for current-only citations
```

- `SearchResult` fields: `chunk_id, doc_id, title, doc_type, version, status,
  source_url, last_updated, section, text, score, matched_by`
- `Answer` fields: `status, answer, sources, model, reason, notice, confidence,
  reasons`; each source carries `index`, the citation metadata, and its `text`.
- Scores are now rounded to 6 decimals because of the penalty.

---

## 9. After 1.0 - maintenance notes

There is no Day 21 in the plan. If this project continues, the natural next
steps are:

1. Replace the 12-document sample corpus with a real docs pipeline (the ingest
   and citation contract stay the same).
2. Move metrics and the answer cache out of process before running multiple
   workers (Prometheus and Redis are the usual choices).
3. Add a reranker only if the golden set shows a retrieval gap; today recall@5
   is 1.00 with `gemini-embedding-001`.
4. Re-run `python -m app.refresh`, `python -m app.evaluate --min-recall 0.85`,
   and `python -m app.benchmark` after any corpus or model change.

Keep `PROJECT_MEMORY.md` current if the project is handed on.

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
| 10 | 28 Oct 2026 | Superseded handling: RRF demotion penalty, `Answer.notice`, UI amber banner, superseded tests, 97 tests |
| 11 | 29 Oct 2026 | Relevance floor (`MIN_SIMILARITY`, calibrated embeddings only), out-of-scope `not_found`, 6 threshold tests, 103 tests |
| 12 | 29 Oct 2026 | Golden-set harness (`eval/golden_set.json`, `app/evaluate.py`), recall@5 1.00 / MRR 0.91 with Gemini, 6 eval tests, 109 tests |
| 13 | 29 Oct 2026 | Evaluation gates CI (`--min-recall 0.85`, report artefact), threshold test, 110 tests |
| 14 | 29 Oct 2026 | Computed confidence + reasons on `Answer`, quiet UI row, 7 confidence tests, 117 tests |
| 15 | 29 Oct 2026 | JSON request logs, `/api/metrics` counters and latency, 8 metrics tests, 125 tests |
| 16 | 29 Oct 2026 | Feedback capture (`app/feedback.py`, `POST/GET /api/feedback`), UI buttons, 8 feedback tests, 133 tests |
| 17 | 29 Oct 2026 | Index freshness (`app/refresh.py`, `/api/index/status`, CLI `--force`), 6 refresh tests, 139 tests |
| 18 | 29 Oct 2026 | Accessibility and dark mode: skip link, live status, focus management, focus rings, `prefers-color-scheme` token block, reduced motion, 7 a11y tests, 146 tests |
| 19 | 29 Oct 2026 | Answer cache (`app/cache.py`, `VADA_CACHE_SIZE`, mtime invalidation), benchmark (`app/benchmark.py`), cache counters, 14 cache/benchmark tests, 160 tests |
| 20 | 29 Oct 2026 | v1.0.0: version bump, `CHANGELOG.md`, README badges and 1.0 summary, tag `v1.0.0` |
