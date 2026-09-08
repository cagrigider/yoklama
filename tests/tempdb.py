"""Isolated temp SQLite for unit tests. Never opens data/attendance.db."""

from __future__ import annotations

import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import app  # noqa: E402

OPERATOR_DB = PROJECT_ROOT / "data" / "attendance.db"

# Same CREATE TABLE script as init_db — applied only on the temp file.
_SCHEMA = """
CREATE TABLE IF NOT EXISTS people (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    position TEXT NOT NULL DEFAULT '',
    center TEXT NOT NULL DEFAULT '',
    email TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS meetings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    date TEXT NOT NULL,
    kind TEXT NOT NULL DEFAULT 'series',
    notes TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS attendance (
    meeting_id INTEGER NOT NULL,
    person_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'unmarked',
    tags TEXT NOT NULL DEFAULT '[]',
    note TEXT NOT NULL DEFAULT '',
    PRIMARY KEY (meeting_id, person_id),
    FOREIGN KEY (meeting_id) REFERENCES meetings(id) ON DELETE CASCADE,
    FOREIGN KEY (person_id) REFERENCES people(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS group_profile (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    name TEXT NOT NULL DEFAULT '',
    first_date TEXT NOT NULL,
    end_date TEXT,
    repeat_rule TEXT NOT NULL DEFAULT 'none'
);
"""


class IsolatedDbTestCase(unittest.TestCase):
    """Each test gets a private SQLite file; app.DB_PATH is pointed at it."""

    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory(prefix="yoklama-ut-")
        self.db_path = Path(self._tmpdir.name) / "test.db"
        self.assertNotEqual(self.db_path.resolve(), OPERATOR_DB.resolve())
        self._orig_db_path = app.DB_PATH
        self._orig_seed_path = app.SEED_PATH
        app.DB_PATH = self.db_path
        app.SEED_PATH = Path(self._tmpdir.name) / "no-seed.json"
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.executescript(_SCHEMA)
        self.conn.commit()

    def tearDown(self) -> None:
        self.conn.close()
        app.DB_PATH = self._orig_db_path
        app.SEED_PATH = self._orig_seed_path
        self._tmpdir.cleanup()

    def meeting_dates(self) -> list[str]:
        rows = self.conn.execute(
            "SELECT date FROM meetings ORDER BY date ASC, id ASC"
        ).fetchall()
        return [r["date"] for r in rows]

    def meeting_rows(self) -> list[sqlite3.Row]:
        return self.conn.execute(
            "SELECT * FROM meetings ORDER BY date ASC, id ASC"
        ).fetchall()

    def people_rows(self) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM people ORDER BY name COLLATE NOCASE"
        ).fetchall()
        return [app.row_to_person(r) for r in rows]

    def profile_row(self) -> sqlite3.Row | None:
        return app.group_profile_row(self.conn)

    def profile_count(self) -> int:
        return self.conn.execute("SELECT COUNT(*) FROM group_profile").fetchone()[0]
