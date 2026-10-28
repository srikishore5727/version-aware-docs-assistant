"""Grounded answer generation.

The model receives only retrieved chunks and a strict contract: cite every
claim with ``[n]``, or reply ``NOT_FOUND``. Citations are validated in code, so
an answer that points at a chunk that was not retrieved is rejected before it
reaches the caller.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable

from app.config import Settings, get_settings
from app.search import SearchResult

NOT_FOUND = "NOT_FOUND"
GEMINI_OPENAI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
MAX_ANSWER_WORDS = 80
TEMPERATURE = 0.2
MAX_TOKENS = 1200
CITATION_RE = re.compile(r"\[([\d,\s]+)\]")
SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")

SYSTEM_PROMPT = """You answer questions about the Nimbus API using ONLY the numbered context below.

Rules:
1. Use only the context. Never use outside knowledge.
2. Cite every factual sentence with the matching [n].
3. If the context does not contain the answer, reply exactly: NOT_FOUND
4. Never invent endpoints, fields, status codes, or versions.
5. State the version you are answering for.
6. Keep answers under 80 words."""

RETRY_PROMPT = """Your previous answer was rejected: every sentence must end with a
citation like [1] that refers to one of the numbered context blocks.
Answer again using only the context, or reply exactly NOT_FOUND."""

Completer = Callable[[list[dict]], str]


@dataclass
class Answer:
    """The result of one question."""

    status: str
    answer: str
    sources: list[dict] = field(default_factory=list)
    model: str = "extractive"
    reason: str = ""

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "answer": self.answer,
            "sources": self.sources,
            "model": self.model,
            "reason": self.reason,
        }


def render_context(chunks: list[SearchResult]) -> str:
    """Number the chunks so the model can cite them by index."""
    blocks = []
    for index, chunk in enumerate(chunks, start=1):
        blocks.append(
            f"[{index}] {chunk.title} | {chunk.doc_type} | {chunk.version} | "
            f"{chunk.status} | section: {chunk.section}\n{chunk.text}"
        )
    return "\n\n".join(blocks)


def build_prompt(question: str, chunks: list[SearchResult]) -> list[dict]:
    """Build the chat messages for one question."""
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Context:\n{render_context(chunks)}\n\nQuestion: {question}"},
    ]


def cited_indexes(answer_text: str) -> list[int]:
    """Return every citation number, in order, without duplicates.

    Handles both single ``[1]`` and grouped ``[1, 3]`` forms.
    """
    seen: list[int] = []
    for group in CITATION_RE.findall(answer_text):
        for part in group.split(","):
            part = part.strip()
            if not part.isdigit():
                continue
            number = int(part)
            if number not in seen:
                seen.append(number)
    return seen


def has_valid_citations(answer_text: str, chunk_count: int) -> bool:
    """True when the answer cites at least one real chunk and nothing else."""
    numbers = cited_indexes(answer_text)
    if not numbers:
        return False
    return all(1 <= number <= chunk_count for number in numbers)


def sources_for(chunks: list[SearchResult], numbers: list[int]) -> list[dict]:
    """Build citation cards for the chunks the answer referenced."""
    sources = []
    for number in numbers:
        if not 1 <= number <= len(chunks):
            continue
        chunk = chunks[number - 1]
        sources.append(
            {
                "index": number,
                "chunk_id": chunk.chunk_id,
                "doc_id": chunk.doc_id,
                "title": chunk.title,
                "doc_type": chunk.doc_type,
                "version": chunk.version,
                "status": chunk.status,
                "section": chunk.section,
                "source_url": chunk.source_url,
                "last_updated": chunk.last_updated,
            }
        )
    return sources


def extractive_answer(chunks: list[SearchResult]) -> Answer:
    """Offline fallback: quote the best chunk verbatim with a citation.

    Used when no API key is configured. It cannot paraphrase, which is exactly
    why it cannot hallucinate.
    """
    if not chunks:
        return Answer(status="not_found", answer="Not found in the indexed docs.", reason="no_matches")

    chunk = chunks[0]
    body = " ".join(chunk.text.split())
    sentences = SENTENCE_RE.split(body)
    excerpt = ""
    for sentence in sentences:
        if len(excerpt) + len(sentence) > 240 and excerpt:
            break
        excerpt = f"{excerpt} {sentence}".strip()

    answer_text = f"{excerpt} [{1}]"
    return Answer(
        status="answered",
        answer=answer_text,
        sources=sources_for(chunks, [1]),
        model="extractive",
        reason="no_api_key",
    )


def make_completer(settings: Settings) -> Completer | None:
    """Build a Gemini completer, or ``None`` when no key is configured."""
    if not settings.has_api_key:
        return None

    from openai import OpenAI

    client = OpenAI(
        api_key=settings.gemini_api_key,
        base_url=GEMINI_OPENAI_BASE_URL,
        timeout=20.0,
        max_retries=1,
    )

    def complete(messages: list[dict]) -> str:
        response = client.chat.completions.create(
            model=settings.llm_model,
            messages=messages,
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
        )
        choice = response.choices[0]
        if choice.finish_reason == "length":
            raise RuntimeError("model output truncated")
        return (choice.message.content or "").strip()

    return complete


def generate_answer(
    question: str,
    chunks: list[SearchResult],
    settings: Settings | None = None,
    completer: Completer | None = None,
) -> Answer:
    """Ask the model to answer from the retrieved chunks, then validate."""
    config = settings or get_settings()

    if not chunks:
        return Answer(status="not_found", answer="Not found in the indexed docs.", reason="no_matches")

    completer = completer or make_completer(config)
    if completer is None:
        return extractive_answer(chunks)

    messages = build_prompt(question, chunks)

    try:
        raw = completer(messages)
    except Exception as exc:  # network, quota, timeout
        fallback = extractive_answer(chunks)
        fallback.reason = f"generation_failed: {type(exc).__name__}"
        return fallback

    if raw.strip().upper().startswith(NOT_FOUND):
        return Answer(
            status="not_found",
            answer="Not found in the indexed docs.",
            model=config.llm_model,
            reason="model_not_found",
        )

    if not has_valid_citations(raw, len(chunks)):
        retry_messages = messages + [
            {"role": "assistant", "content": raw},
            {"role": "user", "content": RETRY_PROMPT},
        ]
        try:
            raw = completer(retry_messages)
        except Exception as exc:
            fallback = extractive_answer(chunks)
            fallback.reason = f"generation_failed: {type(exc).__name__}"
            return fallback

        if raw.strip().upper().startswith(NOT_FOUND):
            return Answer(
                status="not_found",
                answer="Not found in the indexed docs.",
                model=config.llm_model,
                reason="model_not_found",
            )

        if not has_valid_citations(raw, len(chunks)):
            return Answer(
                status="not_found",
                answer="I could not answer that with a verified source.",
                model=config.llm_model,
                reason="invalid_citations",
            )

    return Answer(
        status="answered",
        answer=raw.strip(),
        sources=sources_for(chunks, cited_indexes(raw)),
        model=config.llm_model,
    )
