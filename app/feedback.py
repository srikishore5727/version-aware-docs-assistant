"""Answer feedback capture.

Two buttons, one row, one table. The point is to keep the question next to the
verdict so a wrong answer can be reproduced later; a rating with no question
would be useless.

SQLite on purpose: no service to run, and the file is gitignored.
"""

from __future__ import annotations

import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

VERDICTS = ("helpful", "not_helpful")

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    question TEXT NOT NULL,
    verdict TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT '',
    version TEXT NOT NULL DEFAULT '',
    doc_type TEXT NOT NULL DEFAULT ''
)
"""


class FeedbackStore:
    """Append-only feedback log."""

    def __init__(self, db_path: str | Path) -> None:
        self._path = Path(db_path)

    def _connect(self) -> sqlite3.Connection:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self._path)
        connection.execute(CREATE_TABLE_SQL)
        return connection

    def record(
        self,
        question: str,
        verdict: str,
        status: str = "",
        version: str | None = None,
        doc_type: str | None = None,
    ) -> int:
        if verdict not in VERDICTS:
            raise ValueError(f"unknown verdict: {verdict}")

        with closing(self._connect()) as connection:
            cursor = connection.execute(
                "INSERT INTO feedback (created_at, question, verdict, status, version, doc_type)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (
                    datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    question,
                    verdict,
                    status,
                    version or "",
                    doc_type or "",
                ),
            )
            connection.commit()
            return int(cursor.lastrowid)

    def summary(self) -> dict:
        with closing(self._connect()) as connection:
            rows = dict(
                connection.execute(
                    "SELECT verdict, COUNT(*) FROM feedback GROUP BY verdict"
                ).fetchall()
            )
        helpful = int(rows.get("helpful", 0))
        not_helpful = int(rows.get("not_helpful", 0))
        return {"total": helpful + not_helpful, "helpful": helpful, "not_helpful": not_helpful}

    def recent(self, limit: int = 20) -> list[dict]:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                "SELECT id, created_at, question, verdict, status, version, doc_type"
                " FROM feedback ORDER BY id DESC LIMIT ?",
                (max(1, min(int(limit), 100)),),
            ).fetchall()

        keys = ("id", "created_at", "question", "verdict", "status", "version", "doc_type")
        return [dict(zip(keys, row)) for row in rows]
