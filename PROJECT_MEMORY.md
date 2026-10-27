# PROJECT MEMORY - VADA

> Read this file first. It is the handoff document for any model or developer
> continuing this project. Keep it updated at the end of every working day.

**Last updated:** 27 October 2026 - Day 1 complete

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
│   └── main.py                FastAPI app: /health and /
├── tests/
│   └── test_health.py         Tests for the scaffold
├── docs/
│   └── PRD.md                 Product requirements (v1.0)
├── mockups/                   UX mockup, brand guidelines, design system (static, deployed)
├── requirements.txt
├── pytest.ini
├── README.md
└── PROJECT_MEMORY.md          This file
```

Planned additions: `corpus/` (sample docs), `app/ingest.py`, `app/search.py`,
`app/answer.py`, `app/static/` (UI), `tests/golden_set.json`.

---

## 5. Ten-day plan

| Day | Feature | Status |
|---|---|---|
| 1 | App scaffold, `/health`, CI | **Done** |
| 2 | Document ingestion and chunking | Next |
| 3 | SQLite FTS5 index, `/api/search` | Planned |
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
feat/02-docs-ingestion
feat/03-bm25-search
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

## 8. Current state (end of Day 1)

- FastAPI app starts and serves `/health` and `/`.
- Three tests pass locally and in CI.
- CI workflow runs on every push and pull request to `main`.
- PRD, UX mockup, brand guidelines, and design system are complete and deployed.
- No corpus, no search, no answering code yet. That is intentional.

---

## 9. Next task - Day 2: document ingestion and chunking

**Goal:** turn Markdown files into clean, metadata-carrying chunks.

**Build**

1. `corpus/` with 12 sample Markdown docs:
   - 4 API reference pages, 4 migration guides, 4 changelog entries
   - versions v1, v2, v3 (use `status: current` for v3, `superseded` for older)
2. Front-matter schema on every file:

```yaml
---
doc_id: api-users-create
title: Create user
product: Nimbus API
doc_type: api-reference        # api-reference | migration-guide | changelog
version: v3
status: current                # current | superseded
source_url: https://docs.example.com/v3/users/create
last_updated: 2026-10-12
---
```

3. `app/ingest.py`
   - `load_documents(path) -> list[Document]`
   - `chunk_document(doc, size=500, overlap=80) -> list[Chunk]`
   - Default a missing `version` to `unknown`
   - Skip empty bodies
4. Add `pyyaml` to `requirements.txt`.
5. Tests covering: front-matter parsing, missing version default, chunk overlap,
   every chunk inherits metadata.

**Do not** add search, endpoints, or UI on Day 2.

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
