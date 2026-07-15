"""SQLite persistence for reproducible recommendations and later learning labels."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path

from trading_agent.domain.analysis import WorkflowResult


class SqliteRecommendationRepository:
    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)

    def initialize(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self._path) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS recommendations (
                    id INTEGER PRIMARY KEY,
                    run_at TEXT NOT NULL,
                    code TEXT NOT NULL,
                    name TEXT NOT NULL,
                    total_score REAL NOT NULL,
                    verdict TEXT NOT NULL,
                    vetoed INTEGER NOT NULL,
                    reasons_json TEXT NOT NULL,
                    risks_json TEXT NOT NULL
                )
                """
            )

    def save(self, result: WorkflowResult, run_at: datetime | None = None) -> None:
        self.initialize()
        timestamp = (run_at or datetime.now().astimezone()).isoformat()
        records = (*result.recommendations, *result.vetoed)
        with sqlite3.connect(self._path) as connection:
            connection.executemany(
                """
                INSERT INTO recommendations
                (run_at, code, name, total_score, verdict, vetoed, reasons_json, risks_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        timestamp,
                        item.code,
                        item.name,
                        item.total_score,
                        item.verdict,
                        int(item.vetoed),
                        json.dumps(item.reasons, ensure_ascii=False),
                        json.dumps(item.risks, ensure_ascii=False),
                    )
                    for item in records
                ],
            )
