#!/usr/bin/env python3
"""Local meeting attendance tracker. Binds to 127.0.0.1 only."""

from __future__ import annotations

import json
import sqlite3
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

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
        """
    )
    seed_people(conn)
    seed_meetings(conn)
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

    def handle_api_get(self, path: str, query: dict) -> None:
        conn = db()
        try:
            if path == "/api/meta":
                self.json(
                    200,
                    {
                        "today": date.today().isoformat(),
                        "statuses": STATUSES,
                        "tags": TAGS,
                        "statusLabels": STATUS_TR,
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
