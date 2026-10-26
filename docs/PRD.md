# Product Requirements Document — Version-Aware Docs Assistant

| Field | Value |
|---|---|
| Product | VADA (Version-Aware Docs Assistant) |
| Repository | https://github.com/srikishore5727/version-aware-docs-assistant |
| Author | Sri Kishore S |
| Version | 1.0 |
| Status | Final — Ready for Review |
| Date | 26 October 2026 |
| Reviewer | Mentor — Sprint 2 assignment |

---

## Contents

1. [Business Problem Statement](#1-business-problem-statement)
2. [Stakeholders and Ownership](#2-stakeholders-and-ownership)
3. [Business Impact Justification](#3-business-impact-justification)
4. [Dataset and Data Source Documentation](#4-dataset-and-data-source-documentation)
5. [KPIs and Success Metrics](#5-kpis-and-success-metrics)
6. [User Stories](#6-user-stories)
7. [Feature Scope](#7-feature-scope)
8. [UX and Wireframe](#8-ux-and-wireframe)
9. [Data Workflow Architecture](#9-data-workflow-architecture)
10. [Assumptions](#10-assumptions)
11. [Risks and Mitigation](#11-risks-and-mitigation)
12. [Non-Functional Requirements](#12-non-functional-requirements)
13. [Validation Checklist](#13-validation-checklist)
14. [Approval](#14-approval)

---

## 1. Business Problem Statement

**Problem:** Our 150 integration developers must cross-reference an API reference (4 versions), migration guides, and changelogs to answer a single question. Documentation is spread across three surfaces, and no system lets a developer ask a question and receive a version-specific answer with its source. In 8 developer interviews, all 8 reported manually opening 4 to 6 pages per question (average 2.5 hours per week), and 6 of 8 had shipped a deprecated field at least once.

**Goal:** Reduce weekly documentation-search time by at least 70% and ensure every answer is traceable to an exact document and version.

**Primary users:** 150 integration developers across 3 regions.

**Success criteria:** At least 90% citation accuracy on a 30-question golden set, and at least 70% of 40 pilot developers active weekly within 30 days of launch.

---

## 2. Stakeholders and Ownership

| Type | Who | Role |
|---|---|---|
| Primary users | 150 integration developers | Ask questions daily; their workflow defines the UX |
| Secondary users | 20 support engineers and 8 solutions architects | Occasional use; need version-correct answers for escalations |
| Data owners | Docs team | Owns the corpus; confirms front-matter fields and refresh rate |
| Technical owner | Platform team | Owns hosting, deployment, and CI |
| Approvers | Head of Developer Experience; Engineering Manager, Docs Platform | Business and technical sign-off before launch |

---

## 3. Business Impact Justification

- **Operational impact:** 150 developers × 2.5 hours per week = **375 hours per week** lost to document hunting and cross-referencing.
- **Revenue and cost impact:** 375 hours × ₹3,000 per hour ≈ **₹11.25L per week (₹45L per month)**. In addition, **8 version-mismatch incidents last quarter at ₹6L remediation each = ₹48L per quarter**.
- **User experience impact:** 6 of 8 interviewed developers described document-hunting as "the worst part of integration work."

---

## 4. Dataset and Data Source Documentation

| Item | Detail |
|---|---|
| Source | `docs-platform/content` (Git repository of Markdown files) |
| Volume | 12 documents for the pilot; 300 documents targeted at general availability |
| Key fields | `doc_id`, `title`, `product`, `doc_type`, `version`, `status`, `section`, `body`, `last_updated`, `source_url` |
| Data quality issues | About 3% of files are missing front-matter; some changelog entries have no version tag |
| Refresh rate | Daily sync at 06:00 IST (confirmed with the Docs team on 20 October 2026) |
| Owner | Docs team — confirmed |

No feature in this document depends on a field that the Docs team has not confirmed.

---

## 5. KPIs and Success Metrics

| Metric | Measurement method | Target | Timeline |
|---|---|---|---|
| Citation accuracy | Golden set of 30 question-to-document pairs, scored automatically | At least 90% | Launch + 2 weeks |
| Unsupported-claim rate | Human review of 50 sampled answers | At most 5% | Launch + 2 weeks |
| Retrieval latency (p95) | Server logs | At most 300 ms | Launch |
| Answer latency (p95) | End-to-end request logs | At most 15 s | Launch |
| Weekly active pilot developers | Product analytics | At least 70% of 40 | 30 days |
| Documentation-search time | Pre and post survey | 2.5 h to at most 45 min per week | 60 days |
| Version-mismatch tickets | Support system | 30% reduction | 90 days |

---

## 6. User Stories

- **US-01:** As an integration developer, I want to ask a natural-language question and get an answer that cites the exact document and version, so that I can trust it without opening five pages.
- **US-02:** As a developer migrating from v2 to v3, I want to restrict results to v3, so that I never apply a deprecated field.
- **US-03:** As a support engineer, I want the assistant to say "not found in the indexed docs" when coverage is missing, so that I do not relay a wrong answer to a customer.
- **US-04:** As a documentation maintainer, I want the corpus re-indexed daily, so that new changelog entries are searchable the same day.
- **US-05:** As a developer, I want to see the source passage rather than only a link, so that I can verify the claim in seconds.

---

## 7. Feature Scope

### In scope — v1.0

- Natural-language question box
- Keyword (BM25) retrieval over indexed documents
- Answer with inline citations such as `[1]` and `[2]`
- Source cards showing title, version, section, and passage snippet
- Version filter and document-type filter
- "Not found" low-confidence path
- Daily re-index command
- Golden-set evaluation script

### Out of scope — v1.0

- Embedding or semantic search (keyword retrieval only in v1)
- Code generation or code execution
- Conversation memory or follow-up questions
- Authentication, SSO, and multi-tenant access control
- Real-time streaming ingestion
- Mobile application
- Feedback analytics dashboard
- Localization

---

## 8. UX and Wireframe

```text
+------------------------------------------------------------------+
| Version-Aware Docs Assistant            [ v3 v ]  [ All types v ]|
+------------------------------------------------------------------+
| Ask a question...                                        [ Ask ]  |
+------------------------------------------------------------------+
| ANSWER                                                            |
| In v3, POST /users replaces "user_name" with "display_name" and   |
| returns 201 instead of 200. [1]                                   |
|                                                                   |
| SOURCES                                                           |
| [1] API Reference - v3 - "Create User"                   0.87     |
|     "...display_name (string, required)..."           [ expand ]  |
| [2] Migration Guide - v2 to v3 - "Renaming fields"       0.81     |
+------------------------------------------------------------------+
| No answer?  "This isn't covered in the indexed documentation."    |
+------------------------------------------------------------------+
```

**Behaviour notes**

- Every answer shows at least one source card, or the not-found state.
- Each source card shows the document type, version, section, and relevance score.
- The version filter defaults to the latest stable version.

---

## 9. Data Workflow Architecture

1. **Ingestion** — Docs Git repository synced by a daily job at 06:00 IST.
2. **Cleaning** — Parse front-matter; default a missing `version` to `unknown`; drop empty bodies.
3. **Chunking** — Split by heading into chunks of about 500 characters with 80-character overlap; copy metadata onto every chunk.
4. **Indexing** — SQLite FTS5, which provides BM25 ranking without additional infrastructure.
5. **Retrieval** — Top-5 chunks, filtered by `version` and `doc_type`.
6. **Answering** — The language model receives only the retrieved chunks and a strict instruction to cite or say not found.
7. **Serving** — A single-page UI renders the answer and the source cards.
8. **Evaluation** — A golden set of 30 question-to-document pairs runs in CI on every change.

---

## 10. Assumptions

| # | Assumption | Status |
|---|---|---|
| A1 | The Docs team can supply Markdown with front-matter | Confirmed |
| A2 | 12 pilot documents are representative of the full 300 | Unconfirmed — validate at 50 documents |
| A3 | BM25 is sufficient for developer-style queries | Unconfirmed — test against the golden set |
| A4 | The language model can be constrained to answer only from supplied chunks | Unconfirmed — measure on 50 samples |
| A5 | Internal network hosting is acceptable | Confirmed with the Platform team |

---

## 11. Risks and Mitigation

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| The language model hallucinates API details | Medium | High — incorrect integrations | Strict grounded prompt; not-found path; 5% unsupported-claim KPI |
| Documentation front-matter is missing or inconsistent | Medium | Medium — incorrect version filter | Default to `unknown`; Docs team lint rule; report gaps in the re-index output |
| BM25 misses paraphrased questions | Medium | Medium — poor recall | Add a synonym map; move to embeddings in v2 |
| Corpus growth slows the index | Low | Low | FTS5 comfortably handles 300 documents; measure p95 |
| Stale documentation after a changelog update | Low | High — deprecated guidance | Daily re-index; show `last_updated` on every source card |

---

## 12. Non-Functional Requirements

- Retrieval p95 of at most 300 ms; answer p95 of at most 15 s.
- Uptime of at least 99% during business hours.
- No personally identifiable information in the corpus.
- Every answer renders at least one citation or the not-found state; uncited answers are not permitted.

---

## 13. Validation Checklist

| # | Check | Status |
|---|---|---|
| 1 | Problem is specific and quantified | Pass |
| 2 | Every KPI has a target, method, and timeline | Pass |
| 3 | Stakeholders are named with roles | Pass |
| 4 | Primary user is clearly defined | Pass |
| 5 | Dataset is confirmed with the data team | Pass |
| 6 | User stories follow Role + Action + Benefit | Pass |
| 7 | Scope is bounded with an out-of-scope list | Pass |
| 8 | Data workflow is documented end to end | Pass |
| 9 | Assumptions are documented as risks | Pass |
| 10 | A wireframe is included | Pass |
| 11 | No aspirational language is used | Pass |
| 12 | AI-assisted review is completed | Pass |
| 13 | Naming and formatting are consistent | Pass |
| 14 | Stakeholder alignment review is complete | Pending |
| 15 | A non-technical reader can follow the document | Pass |

---

## 14. Approval

This PRD is submitted to the mentor for approval as part of the Sprint 2 simulation assignment.

| Role | Name | Status |
|---|---|---|
| Author | Sri Kishore S | Signed |
| Mentor / Assignment Reviewer | To be completed by mentor | Pending |
