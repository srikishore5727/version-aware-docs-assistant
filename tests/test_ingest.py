"""Tests for corpus ingestion and chunking."""

from pathlib import Path

import pytest

from app.ingest import (
    IngestionError,
    chunk_document,
    load_chunks,
    load_document,
    load_documents,
    parse_front_matter,
    split_sections,
)

CORPUS = Path(__file__).resolve().parents[1] / "corpus"


def test_corpus_has_twelve_documents() -> None:
    assert len(load_documents(CORPUS)) == 12


def test_all_corpus_documents_have_required_metadata() -> None:
    documents = load_documents(CORPUS)

    assert {doc.doc_type for doc in documents} == {
        "api-reference",
        "migration-guide",
        "changelog",
    }
    assert {doc.version for doc in documents} == {"v1", "v2", "v3"}

    for document in documents:
        assert document.title
        assert document.body
        assert document.source_url.startswith("https://")
        assert document.status in {"current", "superseded"}


def test_parse_front_matter_returns_metadata_and_body() -> None:
    metadata, body = parse_front_matter(
        "---\ndoc_id: sample\ntitle: Sample\n---\n\n# Heading\n\nBody\n"
    )

    assert metadata == {"doc_id": "sample", "title": "Sample"}
    assert body.startswith("# Heading")


def test_missing_version_defaults_to_unknown(tmp_path: Path) -> None:
    path = tmp_path / "doc.md"
    path.write_text("---\ndoc_id: sample\ntitle: Sample\n---\nBody\n", encoding="utf-8")

    document = load_document(path)

    assert document.version == "unknown"
    assert document.doc_type == "unknown"


def test_missing_required_field_raises(tmp_path: Path) -> None:
    path = tmp_path / "doc.md"
    path.write_text("---\ntitle: Sample\n---\nBody\n", encoding="utf-8")

    with pytest.raises(IngestionError):
        load_document(path)


def test_unclosed_front_matter_raises() -> None:
    with pytest.raises(IngestionError):
        parse_front_matter("---\ndoc_id: sample\ntitle: Sample\n")


def test_split_sections_uses_headings() -> None:
    sections = split_sections("Intro text\n\n# One\n\nA\n\n## Two\n\nB\n")

    assert sections == [("Overview", "Intro text"), ("One", "A"), ("Two", "B")]


def test_chunks_inherit_document_metadata() -> None:
    document = load_document(CORPUS / "api-users-create.md")

    chunks = chunk_document(document, size=200, overlap=40)

    assert chunks
    for chunk in chunks:
        assert chunk.doc_id == document.doc_id
        assert chunk.version == "v3"
        assert chunk.doc_type == "api-reference"
        assert chunk.source_url == document.source_url
        assert chunk.section
        assert chunk.text


def test_long_section_produces_overlapping_chunks() -> None:
    document = load_document(CORPUS / "migration-v2-to-v3.md")

    chunks = chunk_document(document, size=120, overlap=30)

    assert len(chunks) > 1
    assert all(len(chunk.text) <= 120 for chunk in chunks)


def test_chunk_ids_are_unique_across_the_corpus() -> None:
    chunks = load_chunks(CORPUS)
    chunk_ids = [chunk.chunk_id for chunk in chunks]

    assert len(chunks) > len(load_documents(CORPUS))
    assert len(chunk_ids) == len(set(chunk_ids))
