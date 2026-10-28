"""Shared test configuration.

Tests must never call the network or depend on a real API key, so embeddings
default to the deterministic hashing provider and generated indexes live in a
temporary directory.
"""

import os
import tempfile
from pathlib import Path

TEST_ROOT = Path(tempfile.mkdtemp(prefix="vada-tests-"))

os.environ.setdefault("VADA_EMBEDDINGS", "hash")
os.environ.setdefault("VADA_DB_PATH", str(TEST_ROOT / "vada.db"))
os.environ.setdefault("VADA_CHROMA_DIR", str(TEST_ROOT / "chroma"))

# Force the offline answer path: tests must never call Gemini.
os.environ["GEMINI_API_KEY"] = ""
