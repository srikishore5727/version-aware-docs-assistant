"""Document ingestion and chunking for the VADA corpus.

Day 2 scope:
- parse YAML front-matter from Markdown files
- normalise each file into a stable ``Document``
- split documents into heading-aware, overlapping ``Chunk`` objects

Retrieval and answer generation are intentionally not part of this module.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

DEFAULT_CHUNK_SIZE = 500
DEFAULT_OVERLAP = 80
DEFAULT_VERSION = "unknown"
DEFAULT_DOC_TYPE = "unknown"
REQUIRED_FIELDS = ("doc_id", "title")


class IngestionError(ValueError):
    """Raised when a corpus file cannot be parsed."""


@dataclass(frozen=True)
class Document:
    """A single Markdown document with parsed front-matter."""

    doc_id: str
    title: str
    product: str
    doc_type: str
    version: str
    status: str
    source_url: str
    last_updated: str
    body: str
    path: str


@dataclass(frozen=True)
class Chunk:
    """A retrieval-sized slice of a document, carrying its metadata."""

    chunk_id: str
    doc_id: str
    title: str
    doc_type: str
    version: str
    status: str
    source_url: str
    last_updated: str
    section: str
    text: str
    position: int


def parse_front_matter(text: str) -> tuple[dict[str, Any], str]:
    """Split a Markdown file into front-matter metadata and body.

    Files without front-matter return an empty mapping and the original text.
    An opening ``---`` without a closing ``---`` is treated as an error.
    """
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        return {}, text

    closing_index = None
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            closing_index = index
            break

    if closing_index is None:
        raise IngestionError("front-matter opened with '---' but never closed")

    metadata = yaml.safe_load("".join(lines[1:closing_index])) or {}
    if not isinstance(metadata, dict):
        raise IngestionError("front-matter must be a YAML mapping")

    body = "".join(lines[closing_index + 1 :]).strip()
    return metadata, body


def load_document(path: str | Path) -> Document:
    """Load one Markdown file into a :class:`Document`."""
    file_path = Path(path)
    metadata, body = parse_front_matter(file_path.read_text(encoding="utf-8"))

    missing = [field for field in REQUIRED_FIELDS if not str(metadata.get(field, "")).strip()]
    if missing:
        raise IngestionError(
            f"{file_path.name}: missing front-matter field(s): {', '.join(missing)}"
        )

    return Document(
        doc_id=str(metadata["doc_id"]).strip(),
        title=str(metadata["title"]).strip(),
        product=str(metadata.get("product", "")).strip(),
        doc_type=str(metadata.get("doc_type") or DEFAULT_DOC_TYPE).strip(),
        version=str(metadata.get("version") or DEFAULT_VERSION).strip(),
        status=str(metadata.get("status") or "current").strip(),
        source_url=str(metadata.get("source_url", "")).strip(),
        last_updated=str(metadata.get("last_updated", "")).strip(),
        body=body,
        path=file_path.name,
    )


def load_documents(corpus_dir: str | Path) -> list[Document]:
    """Load every Markdown file in a directory, sorted by filename."""
    root = Path(corpus_dir)
    if not root.is_dir():
        raise IngestionError(f"corpus directory not found: {root}")

    documents = [load_document(path) for path in sorted(root.glob("*.md"))]

    seen: set[str] = set()
    for document in documents:
        if document.doc_id in seen:
            raise IngestionError(f"duplicate doc_id: {document.doc_id}")
        seen.add(document.doc_id)

    return documents


def split_sections(body: str) -> list[tuple[str, str]]:
    """Split a Markdown body into ``(section_title, text)`` pairs.

    Text before the first heading is labelled ``Overview``.
    """
    sections: list[tuple[str, str]] = []
    title = "Overview"
    buffer: list[str] = []

    for line in body.splitlines():
        if line.startswith("#"):
            text = "\n".join(buffer).strip()
            if text:
                sections.append((title, text))
            title = line.lstrip("#").strip() or "Overview"
            buffer = []
        else:
            buffer.append(line)

    text = "\n".join(buffer).strip()
    if text:
        sections.append((title, text))

    return sections


def _windows(text: str, size: int, overlap: int) -> list[str]:
    """Slice text into overlapping windows of at most ``size`` characters."""
    if size <= 0:
        raise ValueError("size must be positive")
    if overlap < 0 or overlap >= size:
        raise ValueError("overlap must be >= 0 and smaller than size")

    if len(text) <= size:
        return [text]

    step = size - overlap
    windows: list[str] = []
    start = 0

    while start < len(text):
        end = start + size
        windows.append(text[start:end])
        if end >= len(text):
            break
        start += step

    return windows


def chunk_document(
    document: Document,
    size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_OVERLAP,
) -> list[Chunk]:
    """Split a document into chunks that keep its metadata."""
    chunks: list[Chunk] = []
    position = 0

    for section, text in split_sections(document.body):
        for window in _windows(text, size, overlap):
            window = window.strip()
            if not window:
                continue

            chunks.append(
                Chunk(
                    chunk_id=f"{document.doc_id}::{position}",
                    doc_id=document.doc_id,
                    title=document.title,
                    doc_type=document.doc_type,
                    version=document.version,
                    status=document.status,
                    source_url=document.source_url,
                    last_updated=document.last_updated,
                    section=section,
                    text=window,
                    position=position,
                )
            )
            position += 1

    return chunks


def load_chunks(
    corpus_dir: str | Path,
    size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_OVERLAP,
) -> list[Chunk]:
    """Load and chunk every document in a corpus directory."""
    return [
        chunk
        for document in load_documents(corpus_dir)
        for chunk in chunk_document(document, size=size, overlap=overlap)
    ]
