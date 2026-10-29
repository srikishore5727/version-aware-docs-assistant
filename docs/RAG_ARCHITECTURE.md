# RAG Architecture — VADA

**Version 1.0 · 28 October 2026**
**Author:** Sri Kishore S
**Status:** Pending mentor approval (Phase 3 gate)

---

## 1. Purpose

This document defines how VADA turns product documentation into cited answers.
It covers retrieval, generation, the prompt contract, and how the system fails.

**Scope:** a user asks a question, receives a short answer with sources, or is told
the answer is not in the indexed docs.

**Not in scope:** authentication, chat history, code generation, multi-product support.

---

## 2. Pipeline

```
corpus/*.md
   │
   ├─ 1. Load      parse YAML front-matter, drop empty bodies
   ├─ 2. Chunk     split at headings, 500 chars / 80 overlap, metadata copied
   ├─ 3. Embed     Gemini gemini-embedding-001 → 768-dim vectors
   ├─ 4. Index     Chroma (vectors) + SQLite FTS5 (keywords)
   │
question
   │
   ├─ 5. Retrieve  vector top-10 + BM25 top-10 → fuse → best 5
   ├─ 6. Prompt    retrieved chunks + strict grounding rules
   ├─ 7. Generate  Gemini Flash, temperature 0.2
   └─ 8. Serve     answer with [1][2] citations + source cards
```

Every stage has one job and one failure mode (§9).

---

## 3. Stack

| Required tool | Our choice | Why |
|---|---|---|
| Python | Python 3.10, FastAPI | Already built and tested |
| OpenAI-compatible API | Gemini Flash via Google's OpenAI-compatible endpoint | One key, standard SDK, no custom client |
| Embeddings | Gemini `gemini-embedding-001` (768 dims) | Free tier, same key, no local model or PyTorch |
| Vector database | Chroma, embedded and persistent | No server, survives restarts, 60–300 docs is trivial for it |
| RAG pipeline | Our own code (`app/ingest.py`, `embeddings.py`, `retriever.py`, `answer.py`) | LangChain is optional; ~200 lines is easier to explain and debug |
| UI | Single-page HTML served by FastAPI | Preserves the brand design system; no build step |

**Supporting:** SQLite FTS5 for keyword search (BM25), pytest, GitHub Actions.

**UI deviation (explicit):** the brief lists Next.js or Streamlit. We keep a
hand-built page because the design system, logo, and brand guidelines already
exist and a generic Streamlit app would discard them. The capability required —
a UI that streams the answer and renders source cards — is fully met.

---

## 4. Stages

| # | Stage | Module | Status |
|---|---|---|---|
| 1 | Load and parse front-matter | `app/ingest.py` | Built (Day 2) |
| 2 | Heading-aware chunking | `app/ingest.py` | Built (Day 2) |
| 3 | Embedding generation | `app/embeddings.py` | Planned (Day 4) |
| 4 | Vector index | `app/vector_store.py` | Planned (Day 4) |
| 4 | Keyword index | `app/search.py` | Built (Day 3) |
| 5 | Hybrid retrieval | `app/retriever.py` | Planned (Day 4) |
| 6 | Prompt assembly | `app/answer.py` | Planned (Day 5) |
| 7 | Generation | `app/answer.py` | Planned (Day 5) |
| 8 | UI and citations | `app/static/` | Planned (Day 6) |
| 9 | Evaluation | `tests/test_golden.py` | Planned (Day 9) |

---

## 5. Retrieval — hybrid, on purpose

Two retrievers run on every query:

| Retriever | Good at | Weak at |
|---|---|---|
| Vector (Chroma, cosine) | paraphrases: "paginate results" → "cursor" | exact identifiers: `user_name`, `v3.1.0` |
| Keyword (FTS5, BM25) | exact identifiers and error codes | worded differently from the docs |

Results are merged with **Reciprocal Rank Fusion**: `score = Σ 1 / (60 + rank)`.
RRF needs no score normalisation between cosine and BM25, which keeps the merge
to a few lines and avoids tuning weights.

**Final:** top 5 chunks, each carrying `doc_id`, `title`, `doc_type`, `version`,
`status`, `section`, `source_url`, `last_updated`, and `matched_by`.

---

## 6. Prompt contract

The model receives **only** the retrieved chunks and these rules:

```
You answer questions about the Nimbus API using ONLY the numbered context below.

Rules:
1. Use only the context. Never use outside knowledge.
2. Cite every factual sentence with the matching [n].
3. If the context does not contain the answer, reply exactly: NOT_FOUND
4. Never invent endpoints, fields, status codes, or versions.
5. State the version you are answering for.
6. Keep answers under 80 words.
```

**Generation settings:** temperature `0.2`, max 400 output tokens, 20 s timeout,
one retry on timeout.

**Post-check (code, not the model):** every `[n]` must map to a retrieved chunk.
If it does not, retry once with a stricter instruction; if it still fails, return
the not-found state. An uncited answer is never shown.

---

## 7. Citation and version rules

| Rule | Behaviour |
|---|---|
| Minimum sources | One source card per answer, or not-found |
| Source card | Title · doc type · version · section · last updated · link |
| Superseded sources | Shown, but flagged "superseded by v3" |
| Filter default | Latest stable version (v3) |
| Missing version | Treated as `unknown`, never silently matched to a real version |
| Mixed versions | Answer states which version each claim applies to |
| Confidence | Computed in code from the validated citations: high = 2+ sources, one version, all current; medium = single source, mixed versions, or superseded; low = not-found or extractive fallback |

### 7.1 Superseded documents

A retired version is not deleted, because "what did v2 do?" is a legitimate
question. Two mechanisms keep it honest:

- **Ranking.** After Reciprocal Rank Fusion, every chunk whose `status` is
  `superseded` loses a small fixed penalty (`SUPERSEDED_PENALTY = 0.0015`).
  The penalty never filters; it only breaks near-ties in favour of `current`.
  A v2 page that is clearly the best match for a v2 question still wins,
  because one rank step in an RRF list is worth `1 / (K + rank)` ≈ 0.016.
- **Disclosure.** The prompt asks the model to prefer `current` documents and
  to name the version it used. Independently of the model, `superseded_notice()`
  inspects the *validated* sources and sets `Answer.notice`, e.g. "This answer
  cites v2, which is superseded. Check the current documentation before you
  ship." The UI renders it as an amber banner above the answer body.

The notice is computed from citation metadata, not from model text, so it
cannot be hallucinated away.

---

## 8. API

| Endpoint | Purpose | Status |
|---|---|---|
| `POST /api/search` | Ranked chunks, no generation | Built |
| `POST /api/ask` | Answer + citations + sources | Built |
| `GET /api/metrics` | Process request counters and latency | Built |
| `GET /health` | Liveness | Built |

`POST /api/ask` request: `{"question": str, "version": str?, "doc_type": str?}`
Response: `{"status": "answered"|"not_found", "answer": str, "sources": [...]}`
Errors: `400` empty question, `503` retrieval unavailable.

---

## 9. Failure behaviour

| Failure | Behaviour |
|---|---|
| No API key | Hybrid degrades to BM25 only; UI says "keyword mode" |
| Embedding call fails | Fall back to BM25, log a warning |
| Vector store missing | Rebuild from corpus; if that fails, BM25 only |
| No chunks retrieved | `not_found`, no model call |
| Query is out of scope | Best similarity below `MIN_SIMILARITY` -> no results, `not_found` |
| Model returns `NOT_FOUND` | `not_found` state with the closest sources shown read-only |
| Model times out twice | `not_found` with a retry hint, never a partial answer |
| Citation fails validation | Retry once, then `not_found` |

The system degrades; it never invents an answer.

### 9.1 Relevance floor

Chroma always returns its *nearest* neighbours, however far away they are, so
without a cut-off a question about pizza still produced five confident-looking
cards. The floor is measured, not guessed: on `gemini-embedding-001` (768d,
cosine), 14 in-scope questions scored a best similarity of 0.63-0.86 and 10
out-of-scope asks scored 0.52-0.59. `MIN_SIMILARITY = 0.60` sits in that empty
band.

- Vector hits below the floor are dropped before fusion.
- If the *best* hit is below the floor, retrieval returns nothing, even when
  BM25 found an incidental word match ("write me a poem" matches "write").
- The floor only applies to calibrated embeddings. `HashingEmbeddings` is a
  test/offline fallback whose values mean nothing, so thresholding it would
  break keyword mode. A vector failure also skips the gate and BM25 answers.

---

## 10. Evaluation

- Golden set: 30 question → expected-document pairs (`eval/golden_set.json`),
  covering all 12 docs.
- **Retrieval recall@5 ≥ 0.85** — measured without any model call, so CI is
  deterministic. Baseline with `gemini-embedding-001`: recall@5 1.00, MRR 0.91.
- **Citation accuracy ≥ 90%** — scored against the golden set when a key is set;
  skipped otherwise.
- **Not-found correctness** — unanswerable questions must return `not_found`
  (the Day 11 floor covers this).
- The harness is `app/evaluate.py`; `python -m app.evaluate` prints a summary and
  writes `data/eval/report.json`.
- A CI gate that fails the build below target lands on Day 13.

---

## 11. Out of scope for v1

Authentication · chat memory · streaming · re-ranking models · multi-product
support · document upload · fine-tuning.

---

## 12. Build plan

| Day | Work |
|---|---|
| 2 | Ingestion and chunking — done |
| 3 | BM25 keyword search — done |
| 4 | Embeddings, Chroma, hybrid retrieval |
| 5 | Prompt contract and `/api/ask` generation |
| 6 | Version and doc-type filters, search UI |
| 7 | Superseded handling |
| 8 | Not-found and low-confidence path |
| 9 | Golden-set evaluation in CI |
| 10 | Polish and v1.0.0 release |

---

## 13. Approval

| Role | Name | Decision | Date |
|---|---|---|---|
| Author | Sri Kishore S | Submitted | 28 Oct 2026 |
| Mentor | _pending_ | _pending_ | |

_Target turnaround: 2 working days._
