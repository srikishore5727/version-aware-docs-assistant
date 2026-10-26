# Version-Aware Docs Assistant

Ask a question about a product's API and get a short answer grounded in the exact document and version it came from.

## Problem

A software vendor maintains API references, migration guides, and changelogs across multiple product versions. Developers waste time cross-referencing pages and still make integration errors, because no system answers a version-specific question with the exact source.

## What this project does

- Answers natural-language questions over a documentation corpus.
- Cites the exact document, section, and product version behind every answer.
- Lets the user restrict answers to a specific version or document type.
- Says "not found" instead of guessing when the documentation does not cover the question.

## Status

Sprint 2, Day 1 — repository initialized and v1.0 PRD published.

## Documentation

- [Product Requirements Document v1.0](docs/PRD.md) — problem, users, KPIs, scope, data workflow, and risks.

## Roadmap

| Day | Deliverable |
|---|---|
| 1 | Repository scaffold and v1.0 PRD |
| 2 | Documentation ingestion and chunking |
| 3 | Keyword (BM25) retrieval |
| 4 | Search endpoint and source cards |
| 5 | Grounded answer generation |
| 6 | Citation highlighting |
| 7 | Version and document-type filters |
| 8 | Superseded-document handling |
| 9 | Not-found / low-confidence path |
| 10 | Golden-set evaluation in CI |
| 11 | Streaming answers and loading states |
| 12 | README, demo, v1.0.0 release |

## Author

Sri Kishore S
