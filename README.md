# Version-Aware Docs Assistant

Ask a question about a product's API and get a short answer grounded in the exact document and version it came from.

## Problem

A software vendor maintains API references, migration guides, and changelogs across multiple product versions. Developers waste time cross-referencing pages and still make integration errors, because no system answers a version-specific question with the exact source.

## Status

**Sprint 2 · Day 1 of 10 — complete.**

Application scaffold, health endpoint, and CI are in place. The documentation pipeline starts on Day 2.

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

## Ten-day plan

| Day | Feature | Status |
|---|---|---|
| 1 | Application scaffold, health endpoint, CI | Done |
| 2 | Document ingestion and chunking | Next |
| 3 | Keyword search (SQLite FTS5) and `/api/search` | Planned |
| 4 | Search UI with source cards | Planned |
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
