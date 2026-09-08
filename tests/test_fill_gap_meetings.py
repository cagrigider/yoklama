"""TASK-1.1.1 — fill_gap_meetings (ADR-0003). Isolated temp DB only."""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

_TESTS = Path(__file__).resolve().parent
_ROOT = _TESTS.parent
for _p in (_ROOT, _TESTS):
    _s = str(_p)
    if _s not in sys.path:
        sys.path.insert(0, _s)

from app import SeriesError, fill_gap_meetings
from tempdb import IsolatedDbTestCase


class FillGapMeetingsTest(IsolatedDbTestCase):
    def test_none_inserts_first_date_only(self) -> None:
        inserted = fill_gap_meetings(self.conn, date(2026, 9, 9), None, "none")
        self.conn.commit()

        self.assertEqual(inserted, [date(2026, 9, 9)])
        self.assertEqual(self.meeting_dates(), ["2026-09-09"])

        inserted_again = fill_gap_meetings(
            self.conn, date(2026, 9, 9), date(2026, 10, 7), "none"
        )
        self.conn.commit()
        self.assertEqual(inserted_again, [])
        self.assertEqual(self.meeting_dates(), ["2026-09-09"])

    def test_weekly_inserts_seven_day_steps(self) -> None:
        inserted = fill_gap_meetings(
            self.conn, date(2026, 9, 9), date(2026, 9, 23), "weekly"
        )
        self.conn.commit()

        self.assertEqual(
            inserted,
            [date(2026, 9, 9), date(2026, 9, 16), date(2026, 9, 23)],
        )
        self.assertEqual(
            self.meeting_dates(),
            ["2026-09-09", "2026-09-16", "2026-09-23"],
        )

    def test_biweekly_inserts_fourteen_day_steps(self) -> None:
        # ADR-0003 / PLAN example: 2026-09-09 … 2026-10-07 every 2 weeks.
        inserted = fill_gap_meetings(
            self.conn, date(2026, 9, 9), date(2026, 10, 7), "biweekly"
        )
        self.conn.commit()

        self.assertEqual(
            inserted,
            [date(2026, 9, 9), date(2026, 9, 23), date(2026, 10, 7)],
        )
        self.assertEqual(
            self.meeting_dates(),
            ["2026-09-09", "2026-09-23", "2026-10-07"],
        )
        self.assertNotIn("2026-09-16", self.meeting_dates())

    def test_monthly_same_weekday_and_week_ordinal(self) -> None:
        # 2026-09-09 is 2nd Wednesday: (9-1)//7+1 = 2.
        inserted = fill_gap_meetings(
            self.conn, date(2026, 9, 9), date(2026, 11, 11), "monthly"
        )
        self.conn.commit()

        self.assertEqual(
            inserted,
            [date(2026, 9, 9), date(2026, 10, 14), date(2026, 11, 11)],
        )
        dates = self.meeting_dates()
        self.assertEqual(dates, ["2026-09-09", "2026-10-14", "2026-11-11"])
        self.assertNotIn("2026-10-09", dates)
        self.assertNotIn("2026-09-16", dates)

    def test_monthly_skips_month_without_nth_weekday(self) -> None:
        # 2026-09-30 is 5th Wednesday; Oct/Nov 2026 have no fifth Wednesday.
        inserted = fill_gap_meetings(
            self.conn, date(2026, 9, 30), date(2026, 12, 31), "monthly"
        )
        self.conn.commit()

        self.assertEqual(inserted, [date(2026, 9, 30), date(2026, 12, 30)])
        self.assertEqual(self.meeting_dates(), ["2026-09-30", "2026-12-30"])

    def test_existing_date_not_duplicated_missing_dates_inserted(self) -> None:
        cur = self.conn.execute(
            "INSERT INTO meetings (title, date, kind, notes) VALUES (?, ?, 'extra', ?)",
            ("Extra 23", "2026-09-23", "operator note"),
        )
        extra_id = cur.lastrowid
        self.conn.execute(
            "INSERT INTO people (id, name, position, center, email) VALUES (?, ?, ?, ?, ?)",
            ("90001", "Alex Example", "Engineer", "Example", "alex@example.com"),
        )
        self.conn.execute(
            """
            INSERT INTO attendance (meeting_id, person_id, status, tags, note)
            VALUES (?, ?, 'present', '[]', 'kept')
            """,
            (extra_id, "90001"),
        )
        self.conn.commit()

        inserted = fill_gap_meetings(
            self.conn, date(2026, 9, 9), date(2026, 10, 7), "biweekly"
        )
        self.conn.commit()

        self.assertEqual(inserted, [date(2026, 9, 9), date(2026, 10, 7)])
        same_date_rows = self.conn.execute(
            "SELECT id, title, kind, notes FROM meetings WHERE date = ?",
            ("2026-09-23",),
        ).fetchall()
        self.assertEqual(len(same_date_rows), 1)
        self.assertEqual(same_date_rows[0]["id"], extra_id)
        self.assertEqual(same_date_rows[0]["title"], "Extra 23")
        self.assertEqual(same_date_rows[0]["kind"], "extra")
        self.assertEqual(same_date_rows[0]["notes"], "operator note")

        mark = self.conn.execute(
            "SELECT status, note FROM attendance WHERE meeting_id = ? AND person_id = ?",
            (extra_id, "90001"),
        ).fetchone()
        self.assertEqual(mark["status"], "present")
        self.assertEqual(mark["note"], "kept")
        self.assertEqual(
            self.meeting_dates(),
            ["2026-09-09", "2026-09-23", "2026-10-07"],
        )

    def test_shortening_end_date_never_deletes(self) -> None:
        fill_gap_meetings(self.conn, date(2026, 9, 9), date(2026, 10, 7), "weekly")
        extra = self.conn.execute(
            "INSERT INTO meetings (title, date, kind, notes) VALUES (?, ?, 'extra', '')",
            ("Extra A", "2026-09-10"),
        )
        extra_id = extra.lastrowid
        snapshot = [
            (r["id"], r["date"], r["kind"], r["title"]) for r in self.meeting_rows()
        ]
        self.conn.execute(
            "INSERT INTO people (id, name, email) VALUES (?, ?, ?)",
            ("90002", "Jordan Example", "jordan@example.test"),
        )
        self.conn.execute(
            "INSERT INTO attendance (meeting_id, person_id, status) VALUES (?, ?, 'present')",
            (extra_id, "90002"),
        )
        self.conn.commit()

        before_count = self.conn.execute("SELECT COUNT(*) FROM meetings").fetchone()[0]
        inserted = fill_gap_meetings(
            self.conn, date(2026, 9, 9), date(2026, 9, 9), "weekly"
        )
        self.conn.commit()

        self.assertEqual(inserted, [])
        after = [(r["id"], r["date"], r["kind"], r["title"]) for r in self.meeting_rows()]
        self.assertEqual(after, snapshot)
        self.assertEqual(
            self.conn.execute("SELECT COUNT(*) FROM meetings").fetchone()[0],
            before_count,
        )
        mark = self.conn.execute(
            "SELECT status FROM attendance WHERE meeting_id = ? AND person_id = ?",
            (extra_id, "90002"),
        ).fetchone()
        self.assertEqual(mark["status"], "present")

    def test_end_date_before_first_rejected_no_writes(self) -> None:
        self.conn.execute(
            "INSERT INTO meetings (title, date, kind, notes) VALUES (?, ?, 'extra', '')",
            ("Keep me", "2026-08-01"),
        )
        self.conn.commit()
        before = [dict(r) for r in self.meeting_rows()]

        with self.assertRaises(SeriesError) as ctx:
            fill_gap_meetings(self.conn, date(2026, 9, 9), date(2026, 9, 1), "weekly")
        self.assertEqual(ctx.exception.code, "end_before_first")
        self.conn.commit()

        after = [dict(r) for r in self.meeting_rows()]
        self.assertEqual(after, before)
        self.assertEqual(self.meeting_dates(), ["2026-08-01"])

    def test_generated_meetings_have_kind_series(self) -> None:
        fill_gap_meetings(self.conn, date(2026, 9, 9), None, "none")
        self.conn.execute(
            "INSERT INTO meetings (title, date, kind, notes) VALUES (?, ?, 'extra', '')",
            ("User extra", "2026-09-10"),
        )
        self.conn.commit()

        rows = {r["date"]: r["kind"] for r in self.meeting_rows()}
        self.assertEqual(rows["2026-09-09"], "series")
        self.assertEqual(rows["2026-09-10"], "extra")

    def test_unique_date_constraint_not_added(self) -> None:
        fill_gap_meetings(self.conn, date(2026, 9, 9), None, "none")
        self.conn.commit()
        self.conn.execute(
            "INSERT INTO meetings (title, date, kind, notes) VALUES (?, ?, 'extra', '')",
            ("Same-day extra", "2026-09-09"),
        )
        self.conn.commit()
        same_day = self.conn.execute(
            "SELECT kind FROM meetings WHERE date = ? ORDER BY id",
            ("2026-09-09",),
        ).fetchall()
        self.assertEqual([r["kind"] for r in same_day], ["series", "extra"])
        indexes = self.conn.execute("PRAGMA index_list('meetings')").fetchall()
        for idx in indexes:
            info = self.conn.execute(f"PRAGMA index_info('{idx['name']}')").fetchall()
            cols = [c["name"] for c in info]
            if cols == ["date"] and idx["unique"]:
                self.fail("UNIQUE(date) must not be added on meetings")
