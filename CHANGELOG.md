# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed

- The UI stylesheet now matches `mockups/brand-guidelines.html` and
  `mockups/design-system.html` exactly: missing `--accent-2`, `--faint`,
  `--line-2`, `--r-sm`/`--r-md`/`--r-lg`/`--r-xl`, `--shadow-sm` and `--ease`
  tokens restored; off-palette amber `#fef3c7`, confidence greens/oranges
  `#16a34a`/`#d97706`/`#94a3b8` and translucent chip backgrounds removed.
- Primary button is indigo 600 and hovers to indigo 700, per the brand's
  "indigo means action" rule, instead of ink with an indigo hover.
- Body type is 15 px / 1.6; heading, meta and card type sizes follow the design
  system scale, and the type stacks include `Helvetica Neue` and drop `SF Mono`.
- Motion uses the brand easing with 120 ms / 180 ms durations, elevation uses the
  brand shadows, and every radius comes from the token scale.
- Focus rings are a 2 px indigo ring on every control, including inputs that
  previously set `outline: none`.
- The not-found panel uses the reserved amber surface with `--notice-ink` copy,
  so amber appears only on misses and data-quality notices.
- Dark mode keeps the brand hues (indigo 300 as the night accent) and exposes
  `--surface`, which also fixes washed-out chips against dark backgrounds.

### Added

- `tests/test_brand.py`: 11 tests that parse both mockup files and fail on
  missing tokens, drifted values, raw colours outside the token block,
  undefined `var()` references, off-palette legacy colours, or a dark theme that
  stops using the brand hues.
- README section `Brand and design tokens` documenting the token groups and the
  rules the stylesheet follows.

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

[Unreleased]: https://github.com/srikishore5727/version-aware-docs-assistant/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/srikishore5727/version-aware-docs-assistant/releases/tag/v1.0.0
