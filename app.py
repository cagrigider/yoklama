#!/usr/bin/env python3
"""Local meeting attendance tracker. Binds to 127.0.0.1 only."""

from __future__ import annotations

import base64
import csv
import io
import json
import re
import sqlite3
import zipfile
from datetime import date, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
DB_PATH = DATA_DIR / "attendance.db"
SEED_PATH = ROOT / "seed" / "people.json"
STATIC_DIR = ROOT / "static"

HOST = "127.0.0.1"
PORT = 8765

STATUSES = ("unmarked", "absent", "present", "quiet", "spoke", "strong")
TAGS = ("question", "win", "homework", "camera")
STATUS_TR = {
    "unmarked": "işaretlenmedi",
    "absent": "gelmedi",
    "present": "geldi",
    "quiet": "geldi, sessiz",
    "spoke": "biraz konuştu",
    "strong": "güçlü katkı",
}
TAG_TR = {
    "question": "soru sordu",
    "win": "kazanım paylaştı",
    "homework": "ödev yaptı",
    "camera": "kamera açık",
}
PRESENT = {"present", "quiet", "spoke", "strong"}
REPEAT_RULES = ("none", "weekly", "biweekly", "monthly")
SERIES_TITLE = "Toplantı"
PROFILE_ID = 1
DEFAULT_GROUP_NAME = "Yoklama"
SICIL_FLOAT_RE = re.compile(r"^-?\d+\.0+$")
XLSX_REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
IMPORT_MSG = {
    "missing_id_or_name": (
        "Dosyadaki her satırda sicil (veya id) ve ad olmalı. Hiçbir kişi güncellenmedi."
    ),
    "exotic_xlsx": (
        "Bu Excel dosyası okunamadı (makro, birden fazla başlık satırı veya şifre). "
        "CSV olarak kaydedip tekrar dene."
    ),
    "unsupported_type": "Desteklenen dosyalar: Excel (xlsx), CSV veya people.json.",
    "invalid_file": "Dosya okunamadı. CSV, JSON veya basit bir Excel sayfası dene.",
    "missing_body": "Dosya adı ve içerik (text veya contentBase64) gerekli.",
}
ID_HEADERS = frozenset({"id", "sicil"})
NAME_HEADERS = frozenset({"name", "ad", "isim"})
POSITION_HEADERS = frozenset({"position", "pozisyon"})
CENTER_HEADERS = frozenset({"center", "yetkinlik"})
EMAIL_HEADERS = frozenset({"email", "e-posta", "eposta", "e_posta"})


class SeriesError(ValueError):
    """Invalid series bounds or rule; fill_gap_meetings writes nothing."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class RosterImportError(ValueError):
    """Invalid roster file; import_people writes nothing."""

    def __init__(self, code: str, message: str | None = None) -> None:
        super().__init__(code)
        self.code = code
        self.message = message or IMPORT_MSG.get(code, IMPORT_MSG["invalid_file"])


def db() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    conn = db()
    conn.executescript(
        """
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
    )
    seed_people(conn)
    seed_meetings(conn)
    ensure_default_profile(conn)
    conn.commit()
    conn.close()


def seed_people(conn: sqlite3.Connection) -> None:
    if conn.execute("SELECT COUNT(*) FROM people").fetchone()[0]:
        return
    if not SEED_PATH.is_file():
        return
    people = json.loads(SEED_PATH.read_text(encoding="utf-8"))
    conn.executemany(
        "INSERT INTO people (id, name, position, center, email) VALUES (?, ?, ?, ?, ?)",
        [
            (p["id"], p["name"], p.get("position", ""), p.get("center", ""), p.get("email", ""))
            for p in people
        ],
    )


def seed_meetings(conn: sqlite3.Connection) -> None:
    # New installs start empty. Recurring series belong in setup/settings, not in git.
    return


def _nth_weekday_in_month(year: int, month: int, weekday: int, ordinal: int) -> date | None:
    """Return the ordinal occurrence of weekday in (year, month), or None if absent."""
    first = date(year, month, 1)
    day_num = 1 + (weekday - first.weekday()) % 7 + 7 * (ordinal - 1)
    try:
        found = date(year, month, day_num)
    except ValueError:
        return None
    if found.month != month:
        return None
    return found


def fill_gap_meetings(
    conn: sqlite3.Connection,
    first_date: date,
    end_date: date | None,
    repeat_rule: str,
) -> list[date]:
    """Generate series dates and insert kind=series meetings only where that ISO date is missing.

    Wizard save and Settings save must call this function (calendar ``date`` only).
    Never DELETE/UPDATE meetings or attendance. Does not commit; the caller commits.
    """
    if repeat_rule not in REPEAT_RULES:
        raise SeriesError("invalid_repeat")
    if end_date is not None and end_date < first_date:
        raise SeriesError("end_before_first")
    dates: list[date]
    if repeat_rule == "none":
        dates = [first_date]
    elif end_date is None:
        raise SeriesError("end_required")
    elif repeat_rule == "monthly":
        weekday = first_date.weekday()
        ordinal = (first_date.day - 1) // 7 + 1
        dates = []
        year, month = first_date.year, first_date.month
        end_year, end_month = end_date.year, end_date.month
        while (year, month) <= (end_year, end_month):
            day = _nth_weekday_in_month(year, month, weekday, ordinal)
            if day is not None and first_date <= day <= end_date:
                dates.append(day)
            if month == 12:
                year += 1
                month = 1
            else:
                month += 1
    else:
        step = 7 if repeat_rule == "weekly" else 14
        dates = []
        day = first_date
        while day <= end_date:
            dates.append(day)
            day += timedelta(days=step)
    inserted: list[date] = []
    for day in dates:
        iso = day.isoformat()
        exists = conn.execute(
            "SELECT 1 FROM meetings WHERE date = ? LIMIT 1",
            (iso,),
        ).fetchone()
        if exists:
            continue
        conn.execute(
            "INSERT INTO meetings (title, date, kind, notes) VALUES (?, ?, 'series', '')",
            (SERIES_TITLE, iso),
        )
        inserted.append(day)
    return inserted


def group_profile_row(conn: sqlite3.Connection) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM group_profile WHERE id = ?", (PROFILE_ID,)).fetchone()


def profile_meta(conn: sqlite3.Connection) -> dict:
    """GET /api/meta extras: configured, groupName; optional firstDate, endDate, repeatRule."""
    row = group_profile_row(conn)
    if row is None:
        return {
            "configured": False,
            "groupName": "",
            "firstDate": None,
            "endDate": None,
            "repeatRule": None,
        }
    return {
        "configured": True,
        "groupName": row["name"] or "",
        "firstDate": row["first_date"],
        "endDate": row["end_date"],
        "repeatRule": row["repeat_rule"],
    }


def upsert_group_profile(
    conn: sqlite3.Connection,
    name: str,
    first_date: date,
    end_date: date | None,
    repeat_rule: str,
) -> None:
    """Write the id=1 GroupProfile singleton. Caller commits with fill_gap_meetings."""
    conn.execute(
        """
        INSERT INTO group_profile (id, name, first_date, end_date, repeat_rule)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            name = excluded.name,
            first_date = excluded.first_date,
            end_date = excluded.end_date,
            repeat_rule = excluded.repeat_rule
        """,
        (
            PROFILE_ID,
            name,
            first_date.isoformat(),
            end_date.isoformat() if end_date is not None else None,
            repeat_rule,
        ),
    )


def ensure_default_profile(conn: sqlite3.Connection) -> None:
    """ADR-0001: meetings exist and no profile → default row, no fill_gap_meetings."""
    if group_profile_row(conn) is not None:
        return
    earliest = conn.execute("SELECT MIN(date) FROM meetings").fetchone()[0]
    if earliest is None:
        return
    conn.execute(
        """
        INSERT INTO group_profile (id, name, first_date, end_date, repeat_rule)
        VALUES (?, ?, ?, NULL, 'none')
        """,
        (PROFILE_ID, DEFAULT_GROUP_NAME, earliest),
    )


def row_to_person(r: sqlite3.Row) -> dict:
    return {
        "id": r["id"],
        "name": r["name"],
        "position": r["position"],
        "center": r["center"],
        "email": r["email"],
    }


def row_to_meeting(r: sqlite3.Row, extra: dict | None = None) -> dict:
    item = {
        "id": r["id"],
        "title": r["title"],
        "date": r["date"],
        "kind": r["kind"],
        "notes": r["notes"],
    }
    if extra:
        item.update(extra)
    return item


def parse_tags(raw: str) -> list[str]:
    try:
        tags = json.loads(raw or "[]")
    except json.JSONDecodeError:
        return []
    return [t for t in tags if t in TAGS]


def attendance_payload(r: sqlite3.Row | None, person: sqlite3.Row) -> dict:
    if r is None:
        status, tags, note = "unmarked", [], ""
    else:
        status, tags, note = r["status"], parse_tags(r["tags"]), r["note"]
    return {
        **row_to_person(person),
        "status": status,
        "tags": tags,
        "note": note,
    }


def meeting_counts(conn: sqlite3.Connection, meeting_id: int) -> dict:
    people_n = conn.execute("SELECT COUNT(*) FROM people").fetchone()[0]
    rows = conn.execute(
        "SELECT status FROM attendance WHERE meeting_id = ?",
        (meeting_id,),
    ).fetchall()
    present = sum(1 for r in rows if r["status"] in PRESENT)
    absent = sum(1 for r in rows if r["status"] == "absent")
    unmarked = people_n - present - absent
    return {
        "people": people_n,
        "present": present,
        "absent": absent,
        "unmarked": unmarked,
    }


def person_history(conn: sqlite3.Connection, person_id: str) -> list[dict]:
    meetings = conn.execute(
        "SELECT * FROM meetings ORDER BY date ASC, id ASC"
    ).fetchall()
    att = {
        r["meeting_id"]: r
        for r in conn.execute(
            "SELECT * FROM attendance WHERE person_id = ?",
            (person_id,),
        ).fetchall()
    }
    history = []
    for m in meetings:
        a = att.get(m["id"])
        status = a["status"] if a else "unmarked"
        history.append(
            {
                "meetingId": m["id"],
                "title": m["title"],
                "date": m["date"],
                "kind": m["kind"],
                "status": status,
                "tags": parse_tags(a["tags"]) if a else [],
                "note": a["note"] if a else "",
            }
        )
    return history


def activity_sentence(present_rows: list[dict]) -> str:
    if not present_rows:
        return "Kayıtlı oturumlara katılmadı."
    scores = {"present": 1, "quiet": 1, "spoke": 2, "strong": 3}
    avg = sum(scores[r["status"]] for r in present_rows) / len(present_rows)
    if avg >= 2.4:
        return "Katıldığı oturumlarda aktif katkı verdi."
    if avg >= 1.6:
        return "Katıldığı oturumlarda ara sıra konuştu / katkı verdi."
    return "Katıldığı oturumlarda genellikle dinledi, az konuştu."


def people_overview(conn: sqlite3.Connection) -> list[dict]:
    people = conn.execute("SELECT * FROM people ORDER BY name COLLATE NOCASE").fetchall()
    return [
        {
            **row_to_person(p),
            **{
                k: v
                for k, v in (person_report(conn, p["id"]) or {}).items()
                if k in ("total", "present", "percent", "lastPresent", "summary")
            },
        }
        for p in people
    ]


def person_report(conn: sqlite3.Connection, person_id: str) -> dict | None:
    person = conn.execute("SELECT * FROM people WHERE id = ?", (person_id,)).fetchone()
    if person is None:
        return None
    history = person_history(conn, person_id)
    relevant = [
        h
        for h in history
        if h["date"] <= date.today().isoformat() or h["status"] != "unmarked"
    ]
    present_rows = [h for h in relevant if h["status"] in PRESENT]
    total = len(relevant)
    present_n = len(present_rows)
    pct = round(100 * present_n / total) if total else 0
    last = next((h for h in reversed(history) if h["status"] in PRESENT), None)
    if total == 0:
        summary = f"{person['name']} için henüz sayılacak bir oturum yok."
    else:
        summary = (
            f"{person['name']}, {total} oturumun {present_n} tanesine katıldı. "
            f"{activity_sentence(present_rows)}"
        )
        if last:
            summary += f" Son katılım: {last['date']} ({STATUS_TR[last['status']]})."
    return {
        "person": row_to_person(person),
        "total": total,
        "present": present_n,
        "percent": pct,
        "lastPresent": last,
        "summary": summary,
        "history": history,
    }


def meeting_report(conn: sqlite3.Connection, meeting_id: int) -> dict | None:
    meeting = conn.execute("SELECT * FROM meetings WHERE id = ?", (meeting_id,)).fetchone()
    if meeting is None:
        return None
    roster = meeting_roster(conn, meeting_id)
    present = [p for p in roster if p["status"] in PRESENT]
    absent = [p for p in roster if p["status"] == "absent"]
    unmarked = [p for p in roster if p["status"] == "unmarked"]
    lines = [
        f"{meeting['title']} — {meeting['date']}",
        f"Katılan: {len(present)}/{len(roster)}",
        "",
    ]
    if present:
        lines.append("Katılanlar:")
        for p in present:
            tag_bit = ""
            if p["tags"]:
                tag_bit = " · " + ", ".join(TAG_TR.get(t, t) for t in p["tags"])
            note_bit = f" — {p['note']}" if p["note"] else ""
            lines.append(f"- {p['name']} ({STATUS_TR[p['status']]}{tag_bit}){note_bit}")
        lines.append("")
    if absent:
        lines.append("Gelmedi: " + ", ".join(p["name"] for p in absent))
    if unmarked:
        lines.append("İşaretlenmedi: " + ", ".join(p["name"] for p in unmarked))
    return {
        "meeting": row_to_meeting(meeting, meeting_counts(conn, meeting_id)),
        "present": present,
        "absent": absent,
        "unmarked": unmarked,
        "summary": "\n".join(lines).strip(),
    }


def _roster_rank(p: dict) -> tuple:
    if p["status"] in PRESENT:
        return (0, p["name"].casefold())
    if p["status"] == "absent":
        return (2, p["name"].casefold())
    return (1, p["name"].casefold())


def meeting_roster(conn: sqlite3.Connection, meeting_id: int) -> list[dict]:
    people = conn.execute("SELECT * FROM people ORDER BY name COLLATE NOCASE").fetchall()
    att = {
        r["person_id"]: r
        for r in conn.execute(
            "SELECT * FROM attendance WHERE meeting_id = ?",
            (meeting_id,),
        ).fetchall()
    }
    roster = [attendance_payload(att.get(p["id"]), p) for p in people]
    roster.sort(key=_roster_rank)
    return roster


def read_json(handler: BaseHTTPRequestHandler) -> dict:
    length = int(handler.headers.get("Content-Length") or 0)
    raw = handler.rfile.read(length) if length else b"{}"
    if not raw:
        return {}
    return json.loads(raw.decode("utf-8"))


def people_write_id(path: str) -> str | None:
    """Person id for PUT/DELETE /api/people/{id}. Id is path-only; not /import."""
    parts = path.split("/")
    if len(parts) != 4 or parts[1] != "api" or parts[2] != "people":
        return None
    person_id = parts[3]
    if not person_id or person_id == "import":
        return None
    return person_id


def person_id_from_body(body: dict) -> str:
    raw = body.get("id", body.get("sicil"))
    if raw is None:
        return ""
    return str(raw).strip()


def optional_person_field(body: dict, key: str, fallback: str = "") -> str:
    if key not in body:
        return fallback
    value = body.get(key)
    if value is None:
        return ""
    return str(value).strip()


def insert_person(conn: sqlite3.Connection, body: dict) -> tuple[int, dict]:
    """Insert a person. Returns (status, payload). Duplicate id is 409, not an upsert."""
    person_id = person_id_from_body(body)
    name = optional_person_field(body, "name")
    if not person_id or not name:
        return 400, {"error": "missing_id_or_name"}
    existing = conn.execute("SELECT * FROM people WHERE id = ?", (person_id,)).fetchone()
    if existing is not None:
        return 409, {"error": "duplicate_id"}
    position = optional_person_field(body, "position")
    center = optional_person_field(body, "center")
    email = optional_person_field(body, "email")
    try:
        conn.execute(
            "INSERT INTO people (id, name, position, center, email) VALUES (?, ?, ?, ?, ?)",
            (person_id, name, position, center, email),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.rollback()
        return 409, {"error": "duplicate_id"}
    row = conn.execute("SELECT * FROM people WHERE id = ?", (person_id,)).fetchone()
    return 201, row_to_person(row)


def update_person(conn: sqlite3.Connection, person_id: str, body: dict) -> tuple[int, dict]:
    """Update name/position/center/email. Path id is immutable; body id is ignored."""
    existing = conn.execute("SELECT * FROM people WHERE id = ?", (person_id,)).fetchone()
    if existing is None:
        return 404, {"error": "not_found"}
    name = optional_person_field(body, "name", existing["name"])
    if not name:
        return 400, {"error": "missing_id_or_name"}
    position = optional_person_field(body, "position", existing["position"])
    center = optional_person_field(body, "center", existing["center"])
    email = optional_person_field(body, "email", existing["email"])
    conn.execute(
        "UPDATE people SET name = ?, position = ?, center = ?, email = ? WHERE id = ?",
        (name, position, center, email, person_id),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM people WHERE id = ?", (person_id,)).fetchone()
    return 200, row_to_person(row)


def delete_person(conn: sqlite3.Connection, person_id: str) -> tuple[int, dict]:
    """Delete a person; attendance rows cascade via FK."""
    existing = conn.execute("SELECT id FROM people WHERE id = ?", (person_id,)).fetchone()
    if existing is None:
        return 404, {"error": "not_found"}
    conn.execute("DELETE FROM people WHERE id = ?", (person_id,))
    conn.commit()
    return 200, {"ok": True, "id": person_id}


def coerce_sicil(value: object) -> str:
    """Store numeric xlsx sicil as a string without a trailing .0."""
    text = str(value if value is not None else "").strip()
    if SICIL_FLOAT_RE.fullmatch(text):
        return text.split(".", 1)[0]
    return text


def _norm_header(label: object) -> str:
    return str(label or "").strip().casefold().replace(" ", "_")


def header_field(label: object) -> str | None:
    key = _norm_header(label)
    if key in ID_HEADERS:
        return "id"
    if key in NAME_HEADERS:
        return "name"
    if key in POSITION_HEADERS:
        return "position"
    if key in CENTER_HEADERS:
        return "center"
    if key in EMAIL_HEADERS:
        return "email"
    return None


def _empty_import_row(row: dict) -> bool:
    return not any(str(row.get(k) or "").strip() for k in ("id", "name", "position", "center", "email"))


def validate_import_rows(rows: list[dict]) -> list[dict]:
    """Require sicil/id and name on every non-empty row before any write."""
    cleaned: list[dict] = []
    for row in rows:
        if _empty_import_row(row):
            continue
        person_id = coerce_sicil(row.get("id"))
        name = str(row.get("name") or "").strip()
        if not person_id or not name:
            raise RosterImportError("missing_id_or_name")
        cleaned.append(
            {
                "id": person_id,
                "name": name,
                "position": str(row.get("position") or "").strip(),
                "center": str(row.get("center") or "").strip(),
                "email": str(row.get("email") or "").strip(),
            }
        )
    by_id: dict[str, dict] = {}
    for person in cleaned:
        by_id[person["id"]] = person
    return list(by_id.values())


def upsert_imported_people(conn: sqlite3.Connection, people: list[dict]) -> None:
    """Upsert by people.id. Does not delete absentees. Caller commits."""
    conn.executemany(
        """
        INSERT INTO people (id, name, position, center, email)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            name = excluded.name,
            position = excluded.position,
            center = excluded.center,
            email = excluded.email
        """,
        [
            (p["id"], p["name"], p["position"], p["center"], p["email"])
            for p in people
        ],
    )


def _row_from_mapped(mapped: dict) -> dict:
    values = {"id": "", "name": "", "position": "", "center": "", "email": ""}
    for raw_key, raw_val in mapped.items():
        field = header_field(raw_key)
        if not field:
            continue
        text = str(raw_val or "").strip()
        if field == "id":
            text = coerce_sicil(text)
        if text and not values[field]:
            values[field] = text
    return values


def parse_roster_csv(raw: bytes) -> list[dict]:
    try:
        text = raw.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text))
        if not reader.fieldnames:
            raise RosterImportError("invalid_file")
        if not any(header_field(name) == "id" for name in reader.fieldnames) or not any(
            header_field(name) == "name" for name in reader.fieldnames
        ):
            raise RosterImportError("invalid_file")
        return [_row_from_mapped(row) for row in reader]
    except (UnicodeDecodeError, csv.Error) as err:
        raise RosterImportError("invalid_file") from err


def parse_roster_json(raw: bytes) -> list[dict]:
    try:
        data = json.loads(raw.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as err:
        raise RosterImportError("invalid_file") from err
    if not isinstance(data, list):
        raise RosterImportError("invalid_file")
    rows: list[dict] = []
    for item in data:
        if not isinstance(item, dict):
            raise RosterImportError("invalid_file")
        mapped = dict(item)
        if "sicil" in mapped and "id" not in mapped:
            mapped["id"] = mapped.get("sicil")
        if "yetkinlik" in mapped and "center" not in mapped:
            mapped["center"] = mapped.get("yetkinlik")
        rows.append(_row_from_mapped(mapped))
    return rows


def _xml_local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def _col_index(cell_ref: str) -> int:
    letters = "".join(ch for ch in cell_ref if ch.isalpha())
    index = 0
    for ch in letters.upper():
        index = index * 26 + (ord(ch) - 64)
    return max(index - 1, 0)


def _xlsx_si_text(si: ET.Element) -> str:
    direct = [c for c in list(si) if _xml_local(c.tag) == "t"]
    if direct:
        return "".join((t.text or "") for t in direct)
    parts: list[str] = []
    for child in si:
        loc = _xml_local(child.tag)
        if loc == "r":
            for node in child:
                if _xml_local(node.tag) == "t":
                    parts.append(node.text or "")
        elif loc == "t":
            parts.append(child.text or "")
    return "".join(parts)


def _xlsx_shared_strings(zf: zipfile.ZipFile) -> list[str]:
    try:
        root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
    except KeyError:
        return []
    return [_xlsx_si_text(si) for si in root if _xml_local(si.tag) == "si"]


def _xlsx_cell_text(cell: ET.Element, shared: list[str]) -> str:
    cell_type = cell.get("t")
    if cell_type == "inlineStr":
        return "".join(
            (el.text or "") for el in cell.iter() if _xml_local(el.tag) == "t"
        ).strip()
    value = ""
    for child in cell:
        if _xml_local(child.tag) == "v":
            value = (child.text or "").strip()
            break
    if cell_type == "s":
        try:
            return shared[int(value)].strip()
        except (ValueError, IndexError):
            return value
    return coerce_sicil(value) if value else ""


def _xlsx_first_sheet_xml(zf: zipfile.ZipFile) -> bytes:
    try:
        workbook = ET.fromstring(zf.read("xl/workbook.xml"))
    except KeyError as err:
        raise RosterImportError("exotic_xlsx") from err
    sheets = [el for el in workbook.iter() if _xml_local(el.tag) == "sheet"]
    if not sheets:
        raise RosterImportError("exotic_xlsx")
    rid = sheets[0].get(f"{{{XLSX_REL_NS}}}id") or sheets[0].get("r:id")
    try:
        rels = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
    except KeyError as err:
        raise RosterImportError("exotic_xlsx") from err
    target = None
    for rel in rels.iter():
        if _xml_local(rel.tag) == "Relationship" and rel.get("Id") == rid:
            target = (rel.get("Target") or "").replace("\\", "/")
            break
    if not target:
        raise RosterImportError("exotic_xlsx")
    if target.startswith("/"):
        target = target.lstrip("/")
    elif not target.startswith("xl/"):
        target = f"xl/{target}"
    try:
        return zf.read(target)
    except KeyError as err:
        raise RosterImportError("exotic_xlsx") from err


def parse_roster_xlsx(raw: bytes) -> list[dict]:
    """First worksheet only. Macros, extra header rows, and encrypted books fail closed."""
    try:
        zf = zipfile.ZipFile(io.BytesIO(raw))
    except zipfile.BadZipFile as err:
        raise RosterImportError("exotic_xlsx") from err
    names = zf.namelist()
    if any(name.endswith("EncryptedPackage") or name.endswith("EncryptionInfo") for name in names):
        raise RosterImportError("exotic_xlsx")
    if any(name.endswith("vbaProject.bin") for name in names):
        raise RosterImportError("exotic_xlsx")
    try:
        shared = _xlsx_shared_strings(zf)
        sheet = ET.fromstring(_xlsx_first_sheet_xml(zf))
    except ET.ParseError as err:
        raise RosterImportError("exotic_xlsx") from err
    grid: dict[int, dict[int, str]] = {}
    for row_el in sheet.iter():
        if _xml_local(row_el.tag) != "row":
            continue
        try:
            row_num = int(row_el.get("r") or 0)
        except ValueError:
            continue
        cells: dict[int, str] = {}
        for cell in row_el:
            if _xml_local(cell.tag) != "c":
                continue
            cells[_col_index(cell.get("r") or "")] = _xlsx_cell_text(cell, shared)
        if row_num:
            grid[row_num] = cells
    if not grid:
        return []
    max_col = 0
    for cells in grid.values():
        if cells:
            max_col = max(max_col, max(cells))
    first_r = min(grid)
    headers = [grid[first_r].get(i, "").strip() for i in range(max_col + 1)]
    fields = [header_field(h) for h in headers]
    if "id" not in fields or "name" not in fields:
        raise RosterImportError("exotic_xlsx")
    extra_header = False
    for row_num in sorted(grid):
        if row_num == first_r:
            continue
        later = [grid[row_num].get(i, "").strip() for i in range(max_col + 1)]
        later_fields = [header_field(h) for h in later]
        if "id" in later_fields and "name" in later_fields:
            extra_header = True
            break
    if extra_header:
        raise RosterImportError("exotic_xlsx")
    rows: list[dict] = []
    for row_num in sorted(n for n in grid if n > first_r):
        mapped = {headers[i]: grid[row_num].get(i, "") for i in range(len(headers))}
        rows.append(_row_from_mapped(mapped))
    return rows


def parse_roster(filename: str, raw: bytes) -> list[dict]:
    lower = filename.casefold()
    if lower.endswith(".csv"):
        return parse_roster_csv(raw)
    if lower.endswith(".json"):
        return parse_roster_json(raw)
    if lower.endswith(".xlsx"):
        return parse_roster_xlsx(raw)
    if lower.endswith((".xls", ".xlsm", ".xlsb")):
        raise RosterImportError("exotic_xlsx")
    raise RosterImportError("unsupported_type")


def import_people(conn: sqlite3.Connection, body: dict) -> tuple[int, dict]:
    """POST /api/people/import — JSON {filename, text} or {filename, contentBase64}."""
    filename = str(body.get("filename") or "").strip()
    raw_b64 = body.get("contentBase64")
    raw_text = body.get("text")
    if not filename:
        return 400, {"error": "missing_body", "message": IMPORT_MSG["missing_body"]}
    raw: bytes
    if isinstance(raw_b64, str) and raw_b64.strip():
        try:
            raw = base64.b64decode(raw_b64, validate=False)
        except (ValueError, TypeError):
            return 400, {"error": "invalid_file", "message": IMPORT_MSG["invalid_file"]}
    elif raw_text is not None:
        if not isinstance(raw_text, str):
            return 400, {"error": "invalid_file", "message": IMPORT_MSG["invalid_file"]}
        raw = raw_text.encode("utf-8")
    else:
        return 400, {"error": "missing_body", "message": IMPORT_MSG["missing_body"]}
    try:
        people = validate_import_rows(parse_roster(filename, raw))
    except RosterImportError as err:
        return 400, {"error": err.code, "message": err.message}
    upsert_imported_people(conn, people)
    conn.commit()
    return 200, {"ok": True, "upserted": len(people)}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args) -> None:
        print(f"[{self.log_date_time_string()}] {fmt % args}")

    def _send(self, code: int, body: bytes, content_type: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def json(self, code: int, payload) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self._send(code, body, "application/json; charset=utf-8")

    def not_found(self) -> None:
        self.json(404, {"error": "not_found"})

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        if path.startswith("/api/"):
            self.handle_api_get(path, parse_qs(parsed.query))
            return
        self.serve_static(path)

    def do_POST(self) -> None:
        self.handle_api_write("POST", urlparse(self.path).path)

    def do_PUT(self) -> None:
        self.handle_api_write("PUT", urlparse(self.path).path)

    def do_DELETE(self) -> None:
        self.handle_api_write("DELETE", urlparse(self.path).path)

    def serve_static(self, path: str) -> None:
        rel = path.lstrip("/") or "index.html"
        if path == "/" or not Path(rel).suffix:
            rel = "index.html"
        target = (STATIC_DIR / rel).resolve()
        if not str(target).startswith(str(STATIC_DIR.resolve())) or not target.is_file():
            self._send(404, b"Not found", "text/plain")
            return
        types = {
            ".html": "text/html; charset=utf-8",
            ".css": "text/css; charset=utf-8",
            ".js": "application/javascript; charset=utf-8",
            ".json": "application/json; charset=utf-8",
            ".svg": "image/svg+xml",
            ".ico": "image/x-icon",
        }
        self._send(200, target.read_bytes(), types.get(target.suffix, "application/octet-stream"))

    def _put_profile(self, conn: sqlite3.Connection) -> None:
        """PUT /api/profile — persist group_profile + fill_gap_meetings in one transaction."""
        body = read_json(self)
        if not isinstance(body, dict):
            self.json(400, {"error": "invalid_json"})
            return
        raw_name = body.get("name")
        name = "" if raw_name is None else str(raw_name).strip()
        first_raw = (body.get("firstDate") or "").strip()
        try:
            first = date.fromisoformat(first_raw)
        except ValueError:
            self.json(400, {"error": "invalid_date"})
            return
        end_raw = body.get("endDate")
        end: date | None = None
        if end_raw not in (None, ""):
            try:
                end = date.fromisoformat(str(end_raw).strip())
            except ValueError:
                self.json(400, {"error": "invalid_date"})
                return
        repeat_rule = (body.get("repeatRule") or "").strip()
        try:
            inserted = fill_gap_meetings(conn, first, end, repeat_rule)
            upsert_group_profile(conn, name, first, end, repeat_rule)
        except SeriesError as err:
            conn.rollback()
            self.json(400, {"error": err.code})
            return
        conn.commit()
        self.json(
            200,
            {
                "ok": True,
                "inserted": [d.isoformat() for d in inserted],
                "configured": True,
                "groupName": name,
            },
        )

    def handle_api_get(self, path: str, query: dict) -> None:
        conn = db()
        try:
            if path == "/api/meta":
                # GET /api/meta — existing fields plus configured, groupName (ADR-0004).
                self.json(
                    200,
                    {
                        "today": date.today().isoformat(),
                        "statuses": STATUSES,
                        "tags": TAGS,
                        "statusLabels": STATUS_TR,
                        **profile_meta(conn),
                    },
                )
                return
            if path == "/api/people":
                rows = conn.execute("SELECT * FROM people ORDER BY name COLLATE NOCASE").fetchall()
                self.json(200, [row_to_person(r) for r in rows])
                return
            if path == "/api/overview":
                self.json(200, people_overview(conn))
                return
            if path.startswith("/api/people/") and path.endswith("/report"):
                person_id = path.split("/")[3]
                report = person_report(conn, person_id)
                if report is None:
                    self.not_found()
                    return
                self.json(200, report)
                return
            if path == "/api/meetings":
                rows = conn.execute("SELECT * FROM meetings ORDER BY date ASC, id ASC").fetchall()
                payload = [row_to_meeting(r, meeting_counts(conn, r["id"])) for r in rows]
                self.json(200, payload)
                return
            if path.startswith("/api/meetings/") and path.endswith("/report"):
                meeting_id = int(path.split("/")[3])
                report = meeting_report(conn, meeting_id)
                if report is None:
                    self.not_found()
                    return
                self.json(200, report)
                return
            if path.startswith("/api/meetings/") and path.endswith("/roster"):
                meeting_id = int(path.split("/")[3])
                meeting = conn.execute(
                    "SELECT * FROM meetings WHERE id = ?", (meeting_id,)
                ).fetchone()
                if meeting is None:
                    self.not_found()
                    return
                self.json(
                    200,
                    {
                        "meeting": row_to_meeting(meeting, meeting_counts(conn, meeting_id)),
                        "roster": meeting_roster(conn, meeting_id),
                    },
                )
                return
            if path == "/api/export":
                self.json(200, export_all(conn))
                return
            self.not_found()
        finally:
            conn.close()

    def handle_api_write(self, method: str, path: str) -> None:
        conn = db()
        try:
            # PUT /api/profile — {name, firstDate, endDate|null, repeatRule}.
            # Profile + fill_gap_meetings commit together; import is a later, separate write.
            if method == "PUT" and path == "/api/profile":
                self._put_profile(conn)
                return

            # POST /api/people/import — JSON {filename, text} or {filename, contentBase64}.
            # Not multipart. People writes only; does not touch group_profile or meetings.
            if method == "POST" and path == "/api/people/import":
                body = read_json(self)
                if not isinstance(body, dict):
                    self.json(400, {"error": "invalid_json"})
                    return
                code, payload = import_people(conn, body)
                self.json(code, payload)
                return

            # POST /api/people — add; PUT/DELETE /api/people/{id} — id in path only.
            # Duplicate add is 409 (no silent overwrite). POST /api/people/import is not this family.
            if method == "POST" and path == "/api/people":
                body = read_json(self)
                if not isinstance(body, dict):
                    self.json(400, {"error": "invalid_json"})
                    return
                code, payload = insert_person(conn, body)
                self.json(code, payload)
                return

            person_id = people_write_id(path)
            if person_id and method == "PUT":
                body = read_json(self)
                if not isinstance(body, dict):
                    self.json(400, {"error": "invalid_json"})
                    return
                code, payload = update_person(conn, person_id, body)
                self.json(code, payload)
                return

            if person_id and method == "DELETE":
                code, payload = delete_person(conn, person_id)
                self.json(code, payload)
                return

            if method == "POST" and path == "/api/meetings":
                body = read_json(self)
                title = (body.get("title") or "").strip() or "Toplantı"
                day = (body.get("date") or "").strip()
                notes = (body.get("notes") or "").strip()
                try:
                    date.fromisoformat(day)
                except ValueError:
                    self.json(400, {"error": "invalid_date"})
                    return
                cur = conn.execute(
                    "INSERT INTO meetings (title, date, kind, notes) VALUES (?, ?, 'extra', ?)",
                    (title, day, notes),
                )
                conn.commit()
                row = conn.execute(
                    "SELECT * FROM meetings WHERE id = ?", (cur.lastrowid,)
                ).fetchone()
                self.json(201, row_to_meeting(row, meeting_counts(conn, row["id"])))
                return

            if method == "PUT" and path.startswith("/api/meetings/") and "/attendance/" in path:
                parts = path.split("/")
                meeting_id = int(parts[3])
                person_id = parts[5]
                body = read_json(self)
                meeting = conn.execute(
                    "SELECT id FROM meetings WHERE id = ?", (meeting_id,)
                ).fetchone()
                person = conn.execute(
                    "SELECT * FROM people WHERE id = ?", (person_id,)
                ).fetchone()
                if meeting is None or person is None:
                    self.not_found()
                    return
                existing = conn.execute(
                    "SELECT * FROM attendance WHERE meeting_id = ? AND person_id = ?",
                    (meeting_id, person_id),
                ).fetchone()
                if "status" in body:
                    status = body.get("status") or "unmarked"
                else:
                    status = existing["status"] if existing else "unmarked"
                if status not in STATUSES:
                    self.json(400, {"error": "invalid_status"})
                    return
                if "tags" in body:
                    tags = [t for t in (body.get("tags") or []) if t in TAGS]
                else:
                    tags = parse_tags(existing["tags"]) if existing else []
                if "note" in body:
                    note = (body.get("note") or "").strip()
                else:
                    note = existing["note"] if existing else ""
                conn.execute(
                    """
                    INSERT INTO attendance (meeting_id, person_id, status, tags, note)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(meeting_id, person_id) DO UPDATE SET
                        status = excluded.status,
                        tags = excluded.tags,
                        note = excluded.note
                    """,
                    (meeting_id, person_id, status, json.dumps(tags), note),
                )
                conn.commit()
                saved = conn.execute(
                    "SELECT * FROM attendance WHERE meeting_id = ? AND person_id = ?",
                    (meeting_id, person_id),
                ).fetchone()
                self.json(200, attendance_payload(saved, person))
                return

            if method == "POST" and path.startswith("/api/meetings/") and path.endswith("/close"):
                meeting_id = int(path.split("/")[3])
                meeting = conn.execute(
                    "SELECT id FROM meetings WHERE id = ?", (meeting_id,)
                ).fetchone()
                if meeting is None:
                    self.not_found()
                    return
                people = conn.execute("SELECT id FROM people").fetchall()
                existing = {
                    r["person_id"]
                    for r in conn.execute(
                        "SELECT person_id, status FROM attendance WHERE meeting_id = ?",
                        (meeting_id,),
                    ).fetchall()
                    if r["status"] != "unmarked"
                }
                for p in people:
                    if p["id"] in existing:
                        continue
                    conn.execute(
                        """
                        INSERT INTO attendance (meeting_id, person_id, status, tags, note)
                        VALUES (?, ?, 'absent', '[]', '')
                        ON CONFLICT(meeting_id, person_id) DO UPDATE SET status = 'absent'
                        """,
                        (meeting_id, p["id"]),
                    )
                conn.commit()
                self.json(
                    200,
                    {
                        "meeting": row_to_meeting(
                            conn.execute(
                                "SELECT * FROM meetings WHERE id = ?", (meeting_id,)
                            ).fetchone(),
                            meeting_counts(conn, meeting_id),
                        ),
                        "roster": meeting_roster(conn, meeting_id),
                    },
                )
                return

            if method == "PUT" and path.startswith("/api/meetings/") and path.count("/") == 3:
                meeting_id = int(path.split("/")[3])
                body = read_json(self)
                meeting = conn.execute(
                    "SELECT * FROM meetings WHERE id = ?", (meeting_id,)
                ).fetchone()
                if meeting is None:
                    self.not_found()
                    return
                title = (body.get("title") or meeting["title"]).strip()
                notes = body.get("notes")
                if notes is None:
                    notes = meeting["notes"]
                day = meeting["date"]
                if "date" in body:
                    day = (body.get("date") or "").strip()
                    try:
                        date.fromisoformat(day)
                    except ValueError:
                        self.json(400, {"error": "invalid_date"})
                        return
                conn.execute(
                    "UPDATE meetings SET title = ?, date = ?, notes = ? WHERE id = ?",
                    (title, day, str(notes).strip(), meeting_id),
                )
                conn.commit()
                row = conn.execute(
                    "SELECT * FROM meetings WHERE id = ?", (meeting_id,)
                ).fetchone()
                self.json(200, row_to_meeting(row, meeting_counts(conn, meeting_id)))
                return

            if method == "DELETE" and path.startswith("/api/meetings/") and path.count("/") == 3:
                meeting_id = int(path.split("/")[3])
                meeting = conn.execute(
                    "SELECT * FROM meetings WHERE id = ?", (meeting_id,)
                ).fetchone()
                if meeting is None:
                    self.not_found()
                    return
                conn.execute("DELETE FROM meetings WHERE id = ?", (meeting_id,))
                conn.commit()
                self.json(200, {"ok": True, "id": meeting_id})
                return

            self.not_found()
        except json.JSONDecodeError:
            self.json(400, {"error": "invalid_json"})
        finally:
            conn.close()


def export_all(conn: sqlite3.Connection) -> dict:
    people = [row_to_person(r) for r in conn.execute("SELECT * FROM people").fetchall()]
    meetings = [
        row_to_meeting(r) for r in conn.execute("SELECT * FROM meetings").fetchall()
    ]
    attendance = []
    for r in conn.execute("SELECT * FROM attendance").fetchall():
        attendance.append(
            {
                "meetingId": r["meeting_id"],
                "personId": r["person_id"],
                "status": r["status"],
                "tags": parse_tags(r["tags"]),
                "note": r["note"],
            }
        )
    return {"people": people, "meetings": meetings, "attendance": attendance}


def main() -> None:
    init_db()
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"Yoklama aracı: http://{HOST}:{PORT}")
    print("Veri bu makinede kalır. Durdurmak için Ctrl+C.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nKapatıldı.")
        server.server_close()


if __name__ == "__main__":
    main()
