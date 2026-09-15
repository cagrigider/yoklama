"""Meeting Excel export — GET /api/reports/meetings.xlsx (stdlib xlsx)."""

from __future__ import annotations

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
from xml.etree import ElementTree as ET

_TESTS = Path(__file__).resolve().parent
_ROOT = _TESTS.parent
for _p in (_ROOT, _TESTS):
    _s = str(_p)
    if _s not in sys.path:
        sys.path.insert(0, _s)

import app
from app import (
    MEETING_EXPORT_HEADERS,
    PRESENT,
    SSML_NS,
    build_meetings_export_xlsx,
    build_simple_xlsx,
    format_export_date,
    meetings_export_rows,
    parse_export_range,
    upsert_group_profile,
)
from tempdb import IsolatedDbTestCase


class QuietHandler(app.Handler):
    def log_message(self, fmt: str, *args) -> None:
        return


def _sheet_rows(xlsx_bytes: bytes) -> list[list[str | int]]:
    """Read first-sheet cells from a stdlib-built workbook (inlineStr + numbers)."""
    with zipfile.ZipFile(io.BytesIO(xlsx_bytes)) as zf:
        root = ET.fromstring(zf.read("xl/worksheets/sheet1.xml"))
    ns = {"m": SSML_NS}
    out: list[list[str | int]] = []
    for row in root.findall("m:sheetData/m:row", ns):
        values: list[str | int] = []
        for cell in row.findall("m:c", ns):
            if cell.get("t") == "inlineStr":
                t = cell.find("m:is/m:t", ns)
                values.append("" if t is None or t.text is None else t.text)
            else:
                v = cell.find("m:v", ns)
                text = "" if v is None or v.text is None else v.text
                values.append(int(text) if text.isdigit() else text)
        out.append(values)
    return out


class MeetingsExportHelperTest(IsolatedDbTestCase):
    def _seed(self) -> None:
        upsert_group_profile(self.conn, "Grup 8", date(2026, 9, 9), None, "none")
        self.conn.execute(
            "INSERT INTO people (id, name, position, center, email) VALUES (?, ?, '', '', '')",
            ("10001", "Ayşe Örnek"),
        )
        self.conn.execute(
            "INSERT INTO people (id, name, position, center, email) VALUES (?, ?, '', '', '')",
            ("10002", "Berk Deneme"),
        )
        self.conn.executemany(
            "INSERT INTO meetings (title, date, kind, notes) VALUES (?, ?, 'series', '')",
            [
                ("AI Awareness", "2026-09-09"),
                ("AI Awareness", "2026-09-23"),
                ("AI Awareness", "2026-10-07"),
            ],
        )
        # Meeting 1: both present. Meeting 2: one present, one absent. Meeting 3: unmarked.
        self.conn.execute(
            "INSERT INTO attendance (meeting_id, person_id, status, tags, note) VALUES (1, '10001', 'present', '[]', '')"
        )
        self.conn.execute(
            "INSERT INTO attendance (meeting_id, person_id, status, tags, note) VALUES (1, '10002', 'spoke', '[]', '')"
        )
        self.conn.execute(
            "INSERT INTO attendance (meeting_id, person_id, status, tags, note) VALUES (2, '10001', 'quiet', '[]', '')"
        )
        self.conn.execute(
            "INSERT INTO attendance (meeting_id, person_id, status, tags, note) VALUES (2, '10002', 'absent', '[]', '')"
        )
        self.conn.commit()

    def test_format_export_date(self) -> None:
        self.assertEqual(format_export_date("2026-09-09"), "09/09/2026")
        self.assertEqual(format_export_date("2026-10-07"), "07/10/2026")

    def test_september_range_excludes_october(self) -> None:
        self._seed()
        rows = meetings_export_rows(self.conn, date(2026, 9, 1), date(2026, 9, 30))
        self.assertEqual(
            rows,
            [
                ["09/09/2026", "Grup 8", 2],
                ["23/09/2026", "Grup 8", 1],
            ],
        )
        dates = [r[0] for r in rows]
        self.assertNotIn("07/10/2026", dates)

    def test_custom_range_spans_months(self) -> None:
        self._seed()
        rows = meetings_export_rows(self.conn, date(2026, 9, 20), date(2026, 10, 31))
        self.assertEqual(
            rows,
            [
                ["23/09/2026", "Grup 8", 1],
                ["07/10/2026", "Grup 8", 0],
            ],
        )

    def test_attendee_count_is_present_only(self) -> None:
        self._seed()
        rows = meetings_export_rows(self.conn, date(2026, 9, 23), date(2026, 9, 23))
        self.assertEqual(rows[0][2], 1)
        self.assertTrue("absent" not in PRESENT)

    def test_empty_range_headers_only(self) -> None:
        upsert_group_profile(self.conn, "Grup Empty", date(2026, 9, 9), None, "none")
        self.conn.commit()
        raw = build_meetings_export_xlsx(self.conn, date(2026, 1, 1), date(2026, 1, 31))
        sheet = _sheet_rows(raw)
        self.assertEqual(sheet, [list(MEETING_EXPORT_HEADERS)])

    def test_group_falls_back_to_yoklama(self) -> None:
        self.conn.execute(
            "INSERT INTO meetings (title, date, kind, notes) VALUES ('X', '2026-09-09', 'extra', '')"
        )
        self.conn.commit()
        rows = meetings_export_rows(self.conn, date(2026, 9, 1), date(2026, 9, 30))
        self.assertEqual(rows[0][1], "Yoklama")

    def test_parse_export_range_errors(self) -> None:
        self.assertEqual(parse_export_range({}), (None, "invalid_date"))
        self.assertEqual(
            parse_export_range({"from": ["2026-09-09"], "to": ["2026-09-01"]}),
            (None, "end_before_first"),
        )
        start, end = parse_export_range(
            {"from": ["2026-09-01"], "to": ["2026-09-30"]}
        )
        self.assertEqual(start, date(2026, 9, 1))
        self.assertEqual(end, date(2026, 9, 30))

    def test_build_simple_xlsx_round_trip(self) -> None:
        raw = build_simple_xlsx(("A", "B"), [["x", 3]])
        self.assertEqual(_sheet_rows(raw), [["A", "B"], ["x", 3]])


class MeetingsExportHttpTest(IsolatedDbTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.conn.commit()
        self._httpd = ThreadingHTTPServer(("127.0.0.1", 0), QuietHandler)
        self._thread = Thread(target=self._httpd.serve_forever, daemon=True)
        self._thread.start()
        self.port = self._httpd.server_address[1]

    def tearDown(self) -> None:
        self._httpd.shutdown()
        self._httpd.server_close()
        self._thread.join(timeout=5)
        super().tearDown()

    def _get(self, path: str) -> tuple[int, bytes, dict[str, str]]:
        url = f"http://127.0.0.1:{self.port}{path}"
        req = Request(url, method="GET")
        try:
            with urlopen(req, timeout=5) as resp:
                headers = {k.lower(): v for k, v in resp.headers.items()}
                return resp.status, resp.read(), headers
        except HTTPError as err:
            return err.code, err.read(), {k.lower(): v for k, v in err.headers.items()}

    def test_http_september_export(self) -> None:
        upsert_group_profile(self.conn, "Grup 8", date(2026, 9, 9), None, "none")
        self.conn.executemany(
            "INSERT INTO meetings (title, date, kind, notes) VALUES (?, ?, 'series', '')",
            [
                ("AI Awareness", "2026-09-09"),
                ("AI Awareness", "2026-10-07"),
            ],
        )
        self.conn.commit()
        code, body, headers = self._get(
            "/api/reports/meetings.xlsx?from=2026-09-01&to=2026-09-30"
        )
        self.assertEqual(code, 200)
        self.assertIn("spreadsheetml.sheet", headers.get("content-type", ""))
        self.assertIn("yoklama-2026-09.xlsx", headers.get("content-disposition", ""))
        sheet = _sheet_rows(body)
        self.assertEqual(sheet[0], list(MEETING_EXPORT_HEADERS))
        self.assertEqual(len(sheet), 2)
        self.assertEqual(sheet[1][0], "09/09/2026")
        self.assertEqual(sheet[1][1], "Grup 8")

    def test_http_inverted_range_is_400(self) -> None:
        code, body, _headers = self._get(
            "/api/reports/meetings.xlsx?from=2026-09-09&to=2026-09-01"
        )
        self.assertEqual(code, 400)
        self.assertEqual(json.loads(body.decode("utf-8")), {"error": "end_before_first"})

    def test_http_missing_query_is_400(self) -> None:
        code, body, _headers = self._get("/api/reports/meetings.xlsx")
        self.assertEqual(code, 400)
        self.assertEqual(json.loads(body.decode("utf-8")), {"error": "invalid_date"})
