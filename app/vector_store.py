"""Chroma vector store wrapper.

One collection holds every chunk: the text, its embedding, and the citation
metadata. Cosine distance is used so the stored normalised vectors behave as
similarity scores.
"""

from __future__ import annotations

from pathlib import Path

import chromadb

COLLECTION_NAME = "chunks"


class VectorStore:
    """Thin wrapper over a persistent Chroma collection."""

    def __init__(self, path: str | Path, collection: str = COLLECTION_NAME) -> None:
        self._path = str(path)
        self._collection_name = collection
        self._client = chromadb.PersistentClient(path=self._path)
        self._collection = self._client.get_or_create_collection(
            name=collection,
            metadata={"hnsw:space": "cosine"},
        )

    def count(self) -> int:
        return self._collection.count()

    def reset(self) -> None:
        """Drop and recreate the collection."""
        try:
            self._client.delete_collection(self._collection_name)
        except Exception:  # collection may not exist yet
            pass
        self._collection = self._client.get_or_create_collection(
            name=self._collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def add(self, ids: list[str], texts: list[str], vectors: list[list[float]], metadatas: list[dict]) -> None:
        if not ids:
            return
        self._collection.add(
            ids=ids,
            documents=texts,
            embeddings=vectors,
            metadatas=metadatas,
        )

    def query(self, vector: list[float], n_results: int = 10, where: dict | None = None) -> list[dict]:
        """Return nearest chunks, closest first."""
        if self.count() == 0:
            return []

        result = self._collection.query(
            query_embeddings=[vector],
            n_results=min(n_results, self.count()),
            where=where or None,
            include=["documents", "metadatas", "distances"],
        )

        hits: list[dict] = []
        for chunk_id, text, metadata, distance in zip(
            result["ids"][0],
            result["documents"][0],
            result["metadatas"][0],
            result["distances"][0],
        ):
            hits.append(
                {
                    "chunk_id": chunk_id,
                    "text": text,
                    "metadata": metadata,
                    "similarity": 1.0 - float(distance),
                }
            )
        return hits
