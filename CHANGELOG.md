# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-10-29

First release. VADA answers Nimbus API questions from versioned documentation
and cites the exact page and version behind every claim.

### Added

- Sample corpus of 12 Markdown documents (API references, migration guides, and
  changelogs) across v1, v2, and v3, with 60 heading-aware chunks.
- SQLite FTS5 keyword index with BM25 ranking and `/api/search`.
- Gemini embeddings in Chroma, fused with BM25 by Reciprocal Rank Fusion.
- Grounded answers over `POST /api/ask` with code-validated `[n]` citations,
  grouped citations, one retry, and a `not_found` state.
- Search UI with citation links, source cards, and a retrieval-only fallback.
- Version and document-type filters that combine across both retrievers.
- Superseded-document demotion plus a plain-language notice on retired citations.
- Calibrated relevance floor, so out-of-scope questions return no cards.
- Golden set of 30 questions with recall@5 / MRR reporting; CI fails below 0.85.
- Computed confidence (`high` / `medium` / `low`) with human-readable reasons.
- One JSON log line per API request, process metrics at `GET /api/metrics`, and
  answer feedback at `POST` / `GET /api/feedback`.
- Index freshness reporting (`GET /api/index/status`) and a `python -m app.refresh`
  CLI with `--force`.
- Keyboard and screen-reader support (skip link, live status, focus management,
  visible focus rings) and a system dark theme.
- Bounded in-process answer cache (`VADA_CACHE_SIZE`) with index-mtime
  invalidation and `python -m app.benchmark` latency reporting.

### Changed

- Retrieval is hybrid by default; keyword-only mode remains the no-key fallback.
- The JSON service map moved to `/api`; `/` serves the web UI.

### Fixed

- Answers can no longer cite a chunk that was not retrieved.
- Out-of-scope questions no longer return five vaguely related cards.
- A corpus edit is now visible through index status instead of silently
  serving stale text.

### Security

- Secrets are read from environment variables or a gitignored `.env`; no key is
  committed. Feedback and index files are gitignored.

[1.0.0]: https://github.com/srikishore5727/version-aware-docs-assistant/releases/tag/v1.0.0
