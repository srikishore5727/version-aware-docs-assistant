"""Embedding providers.

Two implementations behind one small interface:

- :class:`GeminiEmbeddings` calls Gemini's ``batchEmbedContents`` endpoint.
- :class:`HashingEmbeddings` is deterministic and offline, used by tests and by
  CI when no API key is configured.

Vectors are L2-normalised so cosine similarity is a dot product.
"""

from __future__ import annotations

import hashlib
import math
import re
from typing import Protocol

import httpx

GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
EMBEDDING_DIM = 768
BATCH_SIZE = 20
TOKEN_RE = re.compile(r"[a-z0-9_]+")


class EmbeddingProvider(Protocol):
    """Minimal interface the retriever depends on."""

    name: str
    dimensions: int

    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...

    def embed_query(self, text: str) -> list[float]: ...


def _normalise(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return vector
    return [value / norm for value in vector]


class GeminiEmbeddings:
    """Gemini embedding model over its REST API."""

    name = "gemini"
    dimensions = EMBEDDING_DIM

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-embedding-001",
        timeout: float = 30.0,
    ) -> None:
        if not api_key:
            raise ValueError("GEMINI_API_KEY is required for Gemini embeddings")
        self._api_key = api_key
        self._model = model
        self._timeout = timeout

    def _embed(self, texts: list[str], task_type: str) -> list[list[float]]:
        vectors: list[list[float]] = []

        for start in range(0, len(texts), BATCH_SIZE):
            batch = texts[start : start + BATCH_SIZE]
            payload = {
                "requests": [
                    {
                        "model": f"models/{self._model}",
                        "content": {"parts": [{"text": text}]},
                        "taskType": task_type,
                        "outputDimensionality": self.dimensions,
                    }
                    for text in batch
                ]
            }

            response = httpx.post(
                f"{GEMINI_BASE_URL}/models/{self._model}:batchEmbedContents",
                headers={"x-goog-api-key": self._api_key},
                json=payload,
                timeout=self._timeout,
            )
            response.raise_for_status()
            vectors.extend(
                _normalise(item["values"]) for item in response.json()["embeddings"]
            )

        return vectors

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._embed(texts, task_type="RETRIEVAL_DOCUMENT")

    def embed_query(self, text: str) -> list[float]:
        return self._embed([text], task_type="RETRIEVAL_QUERY")[0]


class HashingEmbeddings:
    """Deterministic offline embeddings for tests and CI.

    A hashed bag of words: enough to exercise the vector path without a network
    call or an API key. It is not a semantic model and is never used in
    production.
    """

    name = "hash"
    dimensions = 256

    def _vector(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions

        for token in TOKEN_RE.findall(text.lower()):
            digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
            bucket = int.from_bytes(digest[:4], "big") % self.dimensions
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[bucket] += sign

        return _normalise(vector)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._vector(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._vector(text)


def get_embedder(mode: str, api_key: str, model: str) -> EmbeddingProvider:
    """Build the embedder for a mode: ``gemini``, ``hash``, or ``off``."""
    if mode == "gemini" and api_key:
        return GeminiEmbeddings(api_key=api_key, model=model)
    return HashingEmbeddings()
