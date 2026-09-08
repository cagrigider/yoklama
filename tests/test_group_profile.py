"""TASK-1.1.2 — group profile gate and wizard persistence (ADR-0001/0004). Isolated temp DB only."""

from __future__ import annotations

import json
import sqlite3
import sys
from datetime import date
from http.server import ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from urllib.error import HTTPError
from urllib.request import Request, urlopen

_TESTS = Path(__file__).resolve().parent
_ROOT = _TESTS.parent
for _p in (_ROOT, _TESTS):
    _s = str(_p)
    if _s not in sys.path:
        sys.path.insert(0, _s)

import app
from app import (
    DEFAULT_GROUP_NAME,
    HOST,
    SeriesError,
    ensure_default_profile,
    fill_gap_meetings,
    profile_meta,
    seed_people,
    upsert_group_profile,
)
from tempdb import IsolatedDbTestCase

# Synthetic roster only (RFC 2606). Never copied from seed/people.json.
ALEX = {
    "id": "90001",
    "name": "Alex Example",
    "position": "Engineer",
    "center": "Example",
    "email": "alex@example.com",
}


class QuietHandler(app.Handler):
    def log_message(self, fmt: str, *args) -> None:
        return


class GroupProfileGateTest(IsolatedDbTestCase):
    def test_fresh_db_has_no_profile_configured_false(self) -> None:
        self.assertEqual(self.people_rows(), [])
        self.assertEqual(self.meeting_dates(), [])
        self.assertIsNone(self.profile_row())
        self.assertEqual(self.profile_count(), 0)

        meta = profile_meta(self.conn)
        self.assertEqual(meta["configured"], False)
        self.assertEqual(meta["groupName"], "")
        self.assertIsNone(meta["firstDate"])
        self.assertIsNone(meta["endDate"])
        self.assertIsNone(meta["repeatRule"])

        seed_people(self.conn)
        ensure_default_profile(self.conn)
        self.conn.commit()

        self.assertIsNone(self.profile_row())
        self.assertEqual(profile_meta(self.conn)["configured"], False)

    def test_ensure_default_profile_inserts_without_extra_meetings(self) -> None:
        self.conn.execute(
            "INSERT INTO meetings (title, date, kind, notes) VALUES (?, ?, 'extra', '')",
            ("Existing extra", "2026-08-15"),
        )
        self.conn.execute(
            "INSERT INTO meetings (title, date, kind, notes) VALUES (?, ?, 'series', '')",
            ("Existing series", "2026-08-01"),
        )
        self.conn.commit()
        before_dates = self.meeting_dates()
        before_rows = [
            (r["id"], r["date"], r["kind"], r["title"]) for r in self.meeting_rows()
        ]

        ensure_default_profile(self.conn)
        self.conn.commit()

        row = self.profile_row()
        self.assertIsNotNone(row)
        self.assertEqual(row["id"], 1)
        self.assertEqual(row["name"], DEFAULT_GROUP_NAME)
        self.assertEqual(row["first_date"], "2026-08-01")
        self.assertIsNone(row["end_date"])
        self.assertEqual(row["repeat_rule"], "none")
        self.assertEqual(self.meeting_dates(), before_dates)
        self.assertEqual(
            [(r["id"], r["date"], r["kind"], r["title"]) for r in self.meeting_rows()],
            before_rows,
        )
        meta = profile_meta(self.conn)
        self.assertEqual(meta["configured"], True)
        self.assertEqual(meta["groupName"], DEFAULT_GROUP_NAME)

        ensure_default_profile(self.conn)
        self.conn.commit()
        self.assertEqual(self.profile_count(), 1)
        self.assertEqual(self.meeting_dates(), before_dates)

    def test_seed_people_does_not_create_profile(self) -> None:
        seed = Path(self._tmpdir.name) / "people.json"
        seed.write_text(json.dumps([ALEX]), encoding="utf-8")
        app.SEED_PATH = seed

        seed_people(self.conn)
        self.conn.commit()

        self.assertEqual([p["id"] for p in self.people_rows()], ["90001"])
        self.assertIsNone(self.profile_row())
        self.assertEqual(profile_meta(self.conn)["configured"], False)
        self.assertEqual(self.meeting_dates(), [])

    def test_end_date_before_first_raises_no_profile(self) -> None:
        with self.assertRaises(SeriesError) as ctx:
            fill_gap_meetings(
                self.conn, date(2026, 9, 9), date(2026, 9, 1), "weekly"
            )
        self.assertEqual(ctx.exception.code, "end_before_first")
        self.assertIsNone(self.profile_row())
        self.assertEqual(self.meeting_dates(), [])
        self.assertEqual(self.profile_count(), 0)

    def test_upsert_dont_repeat_persists_singleton_and_first_date(self) -> None:
        inserted = fill_gap_meetings(self.conn, date(2026, 9, 9), None, "none")
        upsert_group_profile(
            self.conn, "Grup Example", date(2026, 9, 9), None, "none"
        )
        self.conn.commit()

        self.assertEqual(inserted, [date(2026, 9, 9)])
        self.assertEqual(self.meeting_dates(), ["2026-09-09"])
        self.assertEqual(self.profile_count(), 1)
        row = self.profile_row()
        self.assertEqual(row["id"], 1)
        self.assertEqual(row["name"], "Grup Example")
        self.assertEqual(row["first_date"], "2026-09-09")
        self.assertIsNone(row["end_date"])
        self.assertEqual(row["repeat_rule"], "none")
        meta = profile_meta(self.conn)
        self.assertEqual(meta["configured"], True)
        self.assertEqual(meta["groupName"], "Grup Example")
        self.assertEqual(meta["firstDate"], "2026-09-09")
        self.assertIsNone(meta["endDate"])
        self.assertEqual(meta["repeatRule"], "none")
        self.assertEqual(self.people_rows(), [])

        upsert_group_profile(
            self.conn, "Grup Example", date(2026, 9, 9), None, "none"
        )
        self.conn.commit()
        self.assertEqual(self.profile_count(), 1)

    def test_upsert_weekly_and_biweekly_fill_gaps(self) -> None:
        fill_gap_meetings(
            self.conn, date(2026, 9, 9), date(2026, 9, 23), "weekly"
        )
        upsert_group_profile(
            self.conn,
            "Grup Weekly",
            date(2026, 9, 9),
            date(2026, 9, 23),
            "weekly",
        )
        self.conn.commit()
        self.assertEqual(
            self.meeting_dates(),
            ["2026-09-09", "2026-09-16", "2026-09-23"],
        )
        self.assertEqual(self.profile_row()["repeat_rule"], "weekly")

        fill_gap_meetings(
            self.conn, date(2026, 9, 9), date(2026, 10, 7), "biweekly"
        )
        upsert_group_profile(
            self.conn,
            "Grup Biweekly",
            date(2026, 9, 9),
            date(2026, 10, 7),
            "biweekly",
        )
        self.conn.commit()
        self.assertEqual(
            self.meeting_dates(),
            ["2026-09-09", "2026-09-16", "2026-09-23", "2026-10-07"],
        )
        self.assertNotIn("2026-09-30", self.meeting_dates())
        self.assertEqual(self.profile_count(), 1)
        self.assertEqual(self.profile_row()["repeat_rule"], "biweekly")
        self.assertEqual(self.profile_row()["name"], "Grup Biweekly")

    def test_group_profile_is_sqlite_singleton(self) -> None:
        upsert_group_profile(
            self.conn, "Grup Example", date(2026, 9, 9), None, "none"
        )
        self.conn.commit()
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute(
                """
                INSERT INTO group_profile (id, name, first_date, end_date, repeat_rule)
                VALUES (2, 'Other', '2026-09-10', NULL, 'none')
                """
            )
        self.conn.rollback()
        self.assertEqual(self.profile_count(), 1)
        self.assertEqual(self.profile_row()["id"], 1)

    def test_host_is_loopback(self) -> None:
        self.assertEqual(HOST, "127.0.0.1")


class GroupProfileHttpTest(IsolatedDbTestCase):
    """PUT /api/profile and GET /api/meta — in-process loopback, ephemeral port."""

    def setUp(self) -> None:
        super().setUp()
        self.conn.commit()
        self._httpd = ThreadingHTTPServer(("127.0.0.1", 0), QuietHandler)
        self._thread = Thread(target=self._httpd.serve_forever, daemon=True)
        self._thread.start()
        self.port = self._httpd.server_address[1]
        ready_code, _ready = self._request("GET", "/api/meta")
        self.assertEqual(ready_code, 200)

    def tearDown(self) -> None:
        self._httpd.shutdown()
        self._httpd.server_close()
        self._thread.join(timeout=5)
        super().tearDown()

    def _request(self, method: str, path: str, body: dict | None = None) -> tuple[int, dict]:
        url = f"http://127.0.0.1:{self.port}{path}"
        data = None if body is None else json.dumps(body).encode("utf-8")
        req = Request(url, data=data, method=method)
        if data is not None:
            req.add_header("Content-Type", "application/json")
        try:
            with urlopen(req, timeout=5) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
                code = resp.status
        except HTTPError as err:
            payload = json.loads(err.read().decode("utf-8"))
            code = err.code
        # Handler commits on another connection; drop any read snapshot.
        self.conn.commit()
        return code, payload

    def test_get_meta_includes_configured_and_group_name(self) -> None:
        code, meta = self._request("GET", "/api/meta")
        self.assertEqual(code, 200)
        self.assertIn("today", meta)
        self.assertIn("statuses", meta)
        self.assertIn("tags", meta)
        self.assertIn("statusLabels", meta)
        self.assertEqual(meta["configured"], False)
        self.assertEqual(meta["groupName"], "")

        upsert_group_profile(
            self.conn, "Grup Example", date(2026, 9, 9), None, "none"
        )
        self.conn.commit()

        code, meta = self._request("GET", "/api/meta")
        self.assertEqual(code, 200)
        self.assertEqual(meta["configured"], True)
        self.assertEqual(meta["groupName"], "Grup Example")
        self.assertEqual(meta["firstDate"], "2026-09-09")
        self.assertIsNone(meta["endDate"])
        self.assertEqual(meta["repeatRule"], "none")
        self.assertEqual(meta["statuses"], list(app.STATUSES))

    def test_put_dont_repeat_configures_and_inserts_first_date(self) -> None:
        code, payload = self._request(
            "PUT",
            "/api/profile",
            {
                "name": "Grup Example",
                "firstDate": "2026-09-09",
                "endDate": None,
                "repeatRule": "none",
            },
        )
        self.assertEqual(code, 200)
        self.assertEqual(payload["ok"], True)
        self.assertEqual(payload["configured"], True)
        self.assertEqual(payload["groupName"], "Grup Example")
        self.assertEqual(payload["inserted"], ["2026-09-09"])

        meta_code, meta = self._request("GET", "/api/meta")
        self.assertEqual(meta_code, 200)
        self.assertEqual(meta["configured"], True)
        self.assertEqual(meta["groupName"], "Grup Example")
        self.assertEqual(meta["repeatRule"], "none")

        self.assertEqual(self.meeting_dates(), ["2026-09-09"])
        self.assertEqual(self.profile_count(), 1)
        self.assertEqual(self.people_rows(), [])

    def test_put_end_before_first_is_400_without_profile(self) -> None:
        code, payload = self._request(
            "PUT",
            "/api/profile",
            {
                "name": "Grup Example",
                "firstDate": "2026-09-09",
                "endDate": "2026-09-01",
                "repeatRule": "weekly",
            },
        )
        self.assertEqual(code, 400)
        self.assertEqual(payload, {"error": "end_before_first"})
        self.assertIsNone(self.profile_row())
        self.assertEqual(self.meeting_dates(), [])
        self.assertEqual(self.profile_count(), 0)

        meta_code, meta = self._request("GET", "/api/meta")
        self.assertEqual(meta_code, 200)
        self.assertEqual(meta["configured"], False)

    def test_put_weekly_and_biweekly_fill_gaps(self) -> None:
        weekly_code, weekly = self._request(
            "PUT",
            "/api/profile",
            {
                "name": "Grup Weekly",
                "firstDate": "2026-09-09",
                "endDate": "2026-09-23",
                "repeatRule": "weekly",
            },
        )
        self.assertEqual(weekly_code, 200)
        self.assertEqual(weekly["configured"], True)
        self.assertEqual(
            weekly["inserted"],
            ["2026-09-09", "2026-09-16", "2026-09-23"],
        )
        self.assertEqual(
            self.meeting_dates(),
            ["2026-09-09", "2026-09-16", "2026-09-23"],
        )

        biweekly_code, biweekly = self._request(
            "PUT",
            "/api/profile",
            {
                "name": "Grup Biweekly",
                "firstDate": "2026-09-09",
                "endDate": "2026-10-07",
                "repeatRule": "biweekly",
            },
        )
        self.assertEqual(biweekly_code, 200)
        self.assertEqual(biweekly["configured"], True)
        self.assertEqual(biweekly["groupName"], "Grup Biweekly")
        self.assertEqual(biweekly["inserted"], ["2026-10-07"])
        self.assertEqual(
            self.meeting_dates(),
            ["2026-09-09", "2026-09-16", "2026-09-23", "2026-10-07"],
        )
        self.assertEqual(self.profile_count(), 1)
        self.assertEqual(self.profile_row()["repeat_rule"], "biweekly")
        self.assertEqual(self.profile_row()["name"], "Grup Biweekly")
        self.assertEqual(self.profile_row()["end_date"], "2026-10-07")
