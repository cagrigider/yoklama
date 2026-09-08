"""TASK-1.2.2 — POST /api/people/import (ADR-0002 / ADR-0004). Isolated temp DB only."""

from __future__ import annotations

import base64
import io
import json
import sys
import zipfile
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
from app import IMPORT_MSG, fill_gap_meetings, import_people, insert_person, upsert_group_profile
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
CASEY = {
    "id": "90003",
    "name": "Casey Example",
    "position": "Analyst",
    "center": "North",
    "email": "casey@example.net",
}

XLSX_REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
SSML_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
PKG_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"


def _csv_text(rows: list[dict], headers: tuple[str, ...] = ("sicil", "name", "position", "center", "email")) -> str:
    lines = [",".join(headers)]
    for row in rows:
        mapped = {
            "sicil": row.get("sicil", row.get("id", "")),
            "id": row.get("id", row.get("sicil", "")),
            "name": row.get("name", ""),
            "position": row.get("position", ""),
            "center": row.get("center", ""),
            "email": row.get("email", ""),
        }
        lines.append(",".join(mapped[h] for h in headers))
    return "\n".join(lines) + "\n"


def _import_body(filename: str, text: str | None = None, raw: bytes | None = None) -> dict:
    body: dict = {"filename": filename}
    if raw is not None:
        body["contentBase64"] = base64.b64encode(raw).decode("ascii")
    else:
        body["text"] = text if text is not None else ""
    return body


def _minimal_xlsx(header_row: list[str], data_rows: list[list[object]]) -> bytes:
    """Stdlib OOXML zip: first sheet, inline strings, numeric cells as raw <v>."""
    def _inline(ref: str, text: str) -> str:
        return (
            f'<c r="{ref}" t="inlineStr"><is><t>{text}</t></is></c>'
        )

    def _number(ref: str, value: object) -> str:
        return f'<c r="{ref}"><v>{value}</v></c>'

    def _col(index: int) -> str:
        return chr(ord("A") + index)

    def _cell(ref: str, value: object) -> str:
        if isinstance(value, (int, float)):
            return _number(ref, value)
        return _inline(ref, str(value))

    header_xml = "".join(_inline(f"{_col(i)}1", h) for i, h in enumerate(header_row))
    body_xml = []
    for row_i, values in enumerate(data_rows, start=2):
        cells = "".join(_cell(f"{_col(c)}{row_i}", v) for c, v in enumerate(values))
        body_xml.append(f'<row r="{row_i}">{cells}</row>')
    sheet = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<worksheet xmlns="{SSML_NS}"><sheetData>'
        f'<row r="1">{header_xml}</row>'
        f'{"".join(body_xml)}'
        "</sheetData></worksheet>"
    )
    workbook = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<workbook xmlns="{SSML_NS}" xmlns:r="{XLSX_REL_NS}">'
        '<sheets><sheet name="Sheet1" sheetId="1" r:id="rId1"/></sheets>'
        "</workbook>"
    )
    rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<Relationships xmlns="{PKG_REL_NS}">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
        'Target="worksheets/sheet1.xml"/>'
        "</Relationships>"
    )
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_STORED) as zf:
        zf.writestr("xl/workbook.xml", workbook)
        zf.writestr("xl/_rels/workbook.xml.rels", rels)
        zf.writestr("xl/worksheets/sheet1.xml", sheet)
    return buf.getvalue()


class QuietHandler(app.Handler):
    def log_message(self, fmt: str, *args) -> None:
        return


class PeopleImportTest(IsolatedDbTestCase):
    def _by_id(self) -> dict[str, dict]:
        return {p["id"]: p for p in self.people_rows()}

    def test_csv_upserts_by_id_and_keeps_absentees(self) -> None:
        insert_person(self.conn, ALEX)
        insert_person(self.conn, JORDAN)

        code, payload = import_people(
            self.conn,
            _import_body(
                "roster.csv",
                _csv_text(
                    [
                        {
                            "id": "90001",
                            "name": "Alex Updated",
                            "position": "Lead",
                            "center": "North",
                            "email": "alex.updated@example.com",
                        },
                        CASEY,
                    ]
                ),
            ),
        )

        self.assertEqual(code, 200)
        self.assertEqual(payload, {"ok": True, "upserted": 2})
        people = self._by_id()
        self.assertEqual(set(people), {"90001", "90002", "90003"})
        self.assertEqual(people["90001"]["name"], "Alex Updated")
        self.assertEqual(people["90001"]["position"], "Lead")
        self.assertEqual(people["90001"]["center"], "North")
        self.assertEqual(people["90001"]["email"], "alex.updated@example.com")
        self.assertEqual(people["90002"]["name"], "Jordan Example")
        self.assertEqual(people["90002"]["email"], "jordan@example.test")
        self.assertEqual(people["90003"]["name"], "Casey Example")

    def test_json_people_shape_upserts(self) -> None:
        insert_person(self.conn, ALEX)
        roster = [
            {
                "id": "90001",
                "name": "Alex From Json",
                "position": "Engineer",
                "center": "Example",
                "email": "alex@example.com",
            },
            {
                "sicil": "90003",
                "name": "Casey Example",
                "position": "Analyst",
                "yetkinlik": "North",
                "email": "casey@example.net",
            },
        ]

        code, payload = import_people(
            self.conn,
            _import_body("people.json", json.dumps(roster, ensure_ascii=False)),
        )

        self.assertEqual(code, 200)
        self.assertEqual(payload, {"ok": True, "upserted": 2})
        people = self._by_id()
        self.assertEqual(people["90001"]["name"], "Alex From Json")
        self.assertEqual(people["90003"]["id"], "90003")
        self.assertEqual(people["90003"]["center"], "North")
        self.assertEqual(people["90003"]["email"], "casey@example.net")
        self.assertNotIn("90002", people)

    def test_missing_name_or_sicil_rejects_whole_file(self) -> None:
        insert_person(self.conn, ALEX)
        before = self.people_rows()

        missing_name = import_people(
            self.conn,
            _import_body("bad.csv", "sicil,name\n90001,\n90003,Casey Example\n"),
        )
        missing_sicil = import_people(
            self.conn,
            _import_body("bad.csv", "sicil,name\n,Casey Example\n"),
        )
        missing_json_name = import_people(
            self.conn,
            _import_body("people.json", json.dumps([{"id": "90003"}])),
        )

        for code, payload in (missing_name, missing_sicil, missing_json_name):
            self.assertEqual(code, 400)
            self.assertEqual(payload["error"], "missing_id_or_name")
            self.assertEqual(payload["message"], IMPORT_MSG["missing_id_or_name"])
        self.assertEqual(self.people_rows(), before)
        self.assertEqual(self._by_id()["90001"]["name"], "Alex Example")

    def test_duplicate_ids_in_file_last_row_wins(self) -> None:
        # Product (validate_import_rows): duplicate sicil/id is last-row-wins.
        # Later rows overwrite earlier ones in an id-keyed dict. The file is
        # accepted (not 400); upserted is the unique-id count, not the raw
        # row count. PLAN/ADR do not specify this case.
        code, payload = import_people(
            self.conn,
            _import_body(
                "dup.csv",
                _csv_text(
                    [
                        {
                            "id": "90001",
                            "name": "Alex First",
                            "email": "first@example.com",
                        },
                        {
                            "id": "90001",
                            "name": "Alex Last",
                            "position": "Lead",
                            "center": "North",
                            "email": "last@example.com",
                        },
                    ]
                ),
            ),
        )

        self.assertEqual(code, 200)
        self.assertEqual(payload, {"ok": True, "upserted": 1})
        people = self.people_rows()
        self.assertEqual(len(people), 1)
        self.assertEqual(people[0]["id"], "90001")
        self.assertEqual(people[0]["name"], "Alex Last")
        self.assertEqual(people[0]["position"], "Lead")
        self.assertEqual(people[0]["center"], "North")
        self.assertEqual(people[0]["email"], "last@example.com")

    def test_utf8_bom_csv_is_tolerated(self) -> None:
        bom_csv = "\ufeffsicil,name,email\n90003,Casey Example,casey@example.net\n"

        code, payload = import_people(self.conn, _import_body("roster.csv", bom_csv))

        self.assertEqual(code, 200)
        self.assertEqual(payload, {"ok": True, "upserted": 1})
        person = self._by_id()["90003"]
        self.assertEqual(person["name"], "Casey Example")
        self.assertEqual(person["email"], "casey@example.net")

    def test_xlsx_first_sheet_numeric_sicil_strips_trailing_dot_zero(self) -> None:
        raw = _minimal_xlsx(
            ["sicil", "name", "email"],
            [[90001.0, "Alex Example", "alex@example.com"]],
        )
        self.assertTrue(zipfile.is_zipfile(io.BytesIO(raw)))

        code, payload = import_people(
            self.conn, _import_body("roster.xlsx", raw=raw)
        )

        self.assertEqual(code, 200)
        self.assertEqual(payload, {"ok": True, "upserted": 1})
        person = self._by_id()["90001"]
        self.assertEqual(person["id"], "90001")
        self.assertFalse(person["id"].endswith(".0"))
        self.assertEqual(person["name"], "Alex Example")
        self.assertEqual(person["email"], "alex@example.com")

    def test_import_does_not_delete_group_profile_or_meetings(self) -> None:
        fill_gap_meetings(self.conn, date(2026, 9, 9), date(2026, 9, 23), "weekly")
        upsert_group_profile(
            self.conn, "Grup Example", date(2026, 9, 9), date(2026, 9, 23), "weekly"
        )
        self.conn.commit()
        insert_person(self.conn, ALEX)
        insert_person(self.conn, JORDAN)
        before_dates = self.meeting_dates()
        before_profile = dict(self.profile_row())

        ok_code, ok_payload = import_people(
            self.conn,
            _import_body("roster.csv", _csv_text([{"id": "90001", "name": "Alex Updated"}])),
        )
        self.assertEqual(ok_code, 200)
        self.assertEqual(ok_payload["upserted"], 1)
        self.assertEqual(self.meeting_dates(), before_dates)
        self.assertEqual(dict(self.profile_row()), before_profile)
        self.assertEqual(self.profile_count(), 1)
        self.assertIn("90002", self._by_id())

        bad_code, bad_payload = import_people(
            self.conn,
            _import_body("bad.csv", "sicil,name\n10001,\n"),
        )
        self.assertEqual(bad_code, 400)
        self.assertEqual(bad_payload["error"], "missing_id_or_name")
        self.assertEqual(self.meeting_dates(), before_dates)
        self.assertEqual(dict(self.profile_row()), before_profile)
        self.assertEqual(self.profile_count(), 1)
        self.assertEqual(self._by_id()["90001"]["name"], "Alex Updated")
        self.assertEqual(self._by_id()["90002"]["name"], "Jordan Example")


class PeopleImportHttpTest(IsolatedDbTestCase):
    """POST /api/people/import — in-process loopback, ephemeral port."""

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
        self.conn.commit()
        return code, payload

    def _by_id(self) -> dict[str, dict]:
        return {p["id"]: p for p in self.people_rows()}

    def test_post_import_json_text_upserts(self) -> None:
        insert_person(self.conn, ALEX)
        insert_person(self.conn, JORDAN)

        code, payload = self._request(
            "POST",
            "/api/people/import",
            _import_body(
                "roster.csv",
                _csv_text([{"id": "90001", "name": "Alex Via Http"}, CASEY]),
            ),
        )

        self.assertEqual(code, 200)
        self.assertEqual(payload, {"ok": True, "upserted": 2})
        people = self._by_id()
        self.assertEqual(people["90001"]["name"], "Alex Via Http")
        self.assertEqual(people["90002"]["name"], "Jordan Example")
        self.assertEqual(people["90003"]["name"], "Casey Example")

    def test_post_import_json_content_base64(self) -> None:
        raw = json.dumps(
            [{"id": "90003", "name": "Casey Example", "email": "casey@example.net"}]
        ).encode("utf-8")

        code, payload = self._request(
            "POST",
            "/api/people/import",
            _import_body("people.json", raw=raw),
        )

        self.assertEqual(code, 200)
        self.assertEqual(payload, {"ok": True, "upserted": 1})
        self.assertEqual(self._by_id()["90003"]["email"], "casey@example.net")

    def test_post_import_invalid_json_is_400(self) -> None:
        url = f"http://127.0.0.1:{self.port}/api/people/import"
        req = Request(url, data=b"{not json", method="POST")
        req.add_header("Content-Type", "application/json")
        with self.assertRaises(HTTPError) as ctx:
            urlopen(req, timeout=5)
        self.assertEqual(ctx.exception.code, 400)
        payload = json.loads(ctx.exception.read().decode("utf-8"))
        self.assertEqual(payload, {"error": "invalid_json"})
        self.assertEqual(self.people_rows(), [])
