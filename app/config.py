"""Runtime configuration, read from environment variables and ``.env``.

Secrets never live in the repository. ``.env`` is gitignored; CI supplies the
same variables through GitHub Actions secrets or leaves them unset, in which
case the app runs in offline keyword mode.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    """Resolved settings for one process."""

    gemini_api_key: str
    embedding_model: str
    llm_model: str
    embeddings_mode: str
    corpus_dir: Path
    db_path: Path
    chroma_dir: Path
    feedback_db: Path = Path("data/feedback.db")

    @property
    def has_api_key(self) -> bool:
        return bool(self.gemini_api_key)

    @property
    def vectors_enabled(self) -> bool:
        return self.embeddings_mode != "off"


def get_settings() -> Settings:
    """Read settings fresh, so tests can change the environment."""
    mode = os.getenv("VADA_EMBEDDINGS", "").strip().lower()
    if not mode:
        mode = "gemini" if os.getenv("GEMINI_API_KEY", "").strip() else "off"

    return Settings(
        gemini_api_key=os.getenv("GEMINI_API_KEY", "").strip(),
        embedding_model=os.getenv("VADA_EMBEDDING_MODEL", "gemini-embedding-001"),
        llm_model=os.getenv("VADA_LLM_MODEL", "gemini-3.1-flash-lite-preview"),
        embeddings_mode=mode,
        corpus_dir=Path(os.getenv("VADA_CORPUS_DIR", "corpus")),
        db_path=Path(os.getenv("VADA_DB_PATH", "data/index/vada.db")),
        chroma_dir=Path(os.getenv("VADA_CHROMA_DIR", "data/index/chroma")),
        feedback_db=Path(os.getenv("VADA_FEEDBACK_DB", "data/feedback.db")),
    )
