"""TASK-1.2.3 — people POST/PUT/DELETE helpers (ADR-0004). Isolated temp DB only."""

from __future__ import annotations

import sys
from pathlib import Path

_TESTS = Path(__file__).resolve().parent
_ROOT = _TESTS.parent
for _p in (_ROOT, _TESTS):
    _s = str(_p)
    if _s not in sys.path:
        sys.path.insert(0, _s)

from app import delete_person, insert_person, people_write_id, update_person
from tempdb import IsolatedDbTestCase

# Synthetic roster only (RFC 2606). Never copied from seed/people.json.
ALEX = {
    "id": "90001",
    "name": "Alex Example",
    "position": "Engineer",
    "center": "Example",
    "email": "alex@example.com",
}
JORDAN = {
    "id": "90002",
    "name": "Jordan Example",
    "position": "",
    "center": "",
    "email": "jordan@example.test",
}


class PeopleCrudTest(IsolatedDbTestCase):
    def test_add_person_with_sicil_and_name(self) -> None:
        code, payload = insert_person(self.conn, ALEX)
        self.assertEqual(code, 201)
        self.assertEqual(payload["id"], "90001")
        self.assertEqual(payload["name"], "Alex Example")
        self.assertEqual(payload["position"], "Engineer")
        self.assertEqual(payload["center"], "Example")
        self.assertEqual(payload["email"], "alex@example.com")
        self.assertEqual(self.people_rows(), [payload])

    def test_add_person_accepts_sicil_alias(self) -> None:
        code, payload = insert_person(
            self.conn,
            {"sicil": "90001", "name": "Alex Example", "email": "alex@example.com"},
        )
        self.assertEqual(code, 201)
        self.assertEqual(payload["id"], "90001")

    def test_add_person_requires_sicil_and_name(self) -> None:
        missing_name = insert_person(self.conn, {"id": "90001"})
        missing_id = insert_person(self.conn, {"name": "Alex Example"})
        empty = insert_person(self.conn, {})
        blank = insert_person(self.conn, {"id": "  ", "name": "  "})

        for code, payload in (missing_name, missing_id, empty, blank):
            self.assertEqual(code, 400)
            self.assertEqual(payload, {"error": "missing_id_or_name"})
        self.assertEqual(self.people_rows(), [])

    def test_duplicate_add_returns_409_without_overwrite(self) -> None:
        first_code, first = insert_person(self.conn, ALEX)
        self.assertEqual(first_code, 201)

        code, payload = insert_person(
            self.conn,
            {
                "id": "90001",
                "name": "Other Example",
                "position": "Changed",
                "center": "Elsewhere",
                "email": "other@example.net",
            },
        )
        self.assertEqual(code, 409)
        self.assertEqual(payload, {"error": "duplicate_id"})

        rows = self.people_rows()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["name"], "Alex Example")
        self.assertEqual(rows[0]["position"], "Engineer")
        self.assertEqual(rows[0]["center"], "Example")
        self.assertEqual(rows[0]["email"], "alex@example.com")
        self.assertEqual(rows[0], first)

    def test_put_cannot_change_sicil(self) -> None:
        insert_person(self.conn, ALEX)
        code, payload = update_person(
            self.conn,
            "90001",
            {
                "id": "90099",
                "sicil": "90099",
                "name": "Alex Updated",
                "position": "Lead",
                "center": "North",
                "email": "alex.updated@example.com",
            },
        )
        self.assertEqual(code, 200)
        self.assertEqual(payload["id"], "90001")
        self.assertEqual(payload["name"], "Alex Updated")
        self.assertEqual(payload["position"], "Lead")
        self.assertEqual(payload["center"], "North")
        self.assertEqual(payload["email"], "alex.updated@example.com")
        self.assertIsNone(
            self.conn.execute("SELECT 1 FROM people WHERE id = ?", ("90099",)).fetchone()
        )
        self.assertEqual(len(self.people_rows()), 1)

    def test_delete_cascades_attendance(self) -> None:
        insert_person(self.conn, ALEX)
        insert_person(self.conn, JORDAN)
        meeting = self.conn.execute(
            "INSERT INTO meetings (title, date, kind, notes) VALUES (?, ?, 'extra', '')",
            ("Standup", "2026-09-09"),
        )
        meeting_id = meeting.lastrowid
        self.conn.execute(
            """
            INSERT INTO attendance (meeting_id, person_id, status, tags, note)
            VALUES (?, ?, 'present', '[]', 'keep-until-delete')
            """,
            (meeting_id, "90001"),
        )
        self.conn.execute(
            """
            INSERT INTO attendance (meeting_id, person_id, status, tags, note)
            VALUES (?, ?, 'absent', '[]', 'jordan stays')
            """,
            (meeting_id, "90002"),
        )
        self.conn.commit()

        code, payload = delete_person(self.conn, "90001")
        self.assertEqual(code, 200)
        self.assertEqual(payload, {"ok": True, "id": "90001"})

        self.assertIsNone(
            self.conn.execute("SELECT 1 FROM people WHERE id = ?", ("90001",)).fetchone()
        )
        leftover_alex = self.conn.execute(
            "SELECT 1 FROM attendance WHERE person_id = ?",
            ("90001",),
        ).fetchone()
        self.assertIsNone(leftover_alex)

        meeting_row = self.conn.execute(
            "SELECT 1 FROM meetings WHERE id = ?", (meeting_id,)
        ).fetchone()
        self.assertIsNotNone(meeting_row)
        jordan_mark = self.conn.execute(
            "SELECT status, note FROM attendance WHERE person_id = ?",
            ("90002",),
        ).fetchone()
        self.assertEqual(jordan_mark["status"], "absent")
        self.assertEqual(jordan_mark["note"], "jordan stays")
        self.assertEqual([p["id"] for p in self.people_rows()], ["90002"])

    def test_empty_roster_is_valid(self) -> None:
        self.assertEqual(self.people_rows(), [])
        code, payload = insert_person(self.conn, ALEX)
        self.assertEqual(code, 201)
        delete_person(self.conn, "90001")
        self.assertEqual(self.people_rows(), [])

    def test_unknown_person_update_and_delete_404(self) -> None:
        insert_person(self.conn, ALEX)
        put_code, put_payload = update_person(
            self.conn, "19999", {"name": "Nobody Example"}
        )
        del_code, del_payload = delete_person(self.conn, "19999")
        self.assertEqual(put_code, 404)
        self.assertEqual(put_payload, {"error": "not_found"})
        self.assertEqual(del_code, 404)
        self.assertEqual(del_payload, {"error": "not_found"})
        self.assertEqual([p["id"] for p in self.people_rows()], ["90001"])

    def test_people_write_id_path_only_skips_import(self) -> None:
        self.assertEqual(people_write_id("/api/people/90001"), "90001")
        self.assertIsNone(people_write_id("/api/people"))
        self.assertIsNone(people_write_id("/api/people/import"))
        self.assertIsNone(people_write_id("/api/people/90001/report"))
