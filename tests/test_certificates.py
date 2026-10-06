"""Certificate catalog + Academy verify assignment. Isolated temp DB only."""

from __future__ import annotations

import sys
from pathlib import Path

_TESTS = Path(__file__).resolve().parent
_ROOT = _TESTS.parent
for _p in (_ROOT, _TESTS):
    _s = str(_p)
    if _s not in sys.path:
        sys.path.insert(0, _s)

from app import (
    AcademyUnreachable,
    _academy_blocked,
    add_person_certificate,
    delete_certificate,
    delete_person,
    get_certificate,
    insert_certificate,
    insert_person,
    list_certificates,
    names_match,
    normalize_match_text,
    parse_verify_code,
    person_report,
    update_certificate,
)
from tempdb import IsolatedDbTestCase

ALEX = {
    "id": "90001",
    "name": "Çağrı Gider",
    "position": "",
    "center": "",
    "email": "",
}
JORDAN = {
    "id": "90002",
    "name": "Jordan Example",
    "position": "",
    "center": "",
    "email": "",
}
CODE_A = "547e3a740ac9226a1a1bcfebfaa13e8c"
CODE_B = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
COURSE = "Building with the Claude API"


def badge(*, name: str = "Cagri Gider", title: str = COURSE, valid: bool = True) -> dict:
    if not valid:
        return {}
    return {
        "valid": True,
        "certificateName": name,
        "courseTitle": title,
        "issuedAt": "2026-09-15T07:20:32.950154Z",
    }


class NormalizeTest(IsolatedDbTestCase):
    def test_parse_url_and_hex(self) -> None:
        url = f"https://academy.claude.com/verify/{CODE_A}"
        self.assertEqual(parse_verify_code(url), CODE_A)
        self.assertEqual(parse_verify_code(CODE_A.upper()), CODE_A)
        self.assertIsNone(parse_verify_code("not-a-code"))
        self.assertIsNone(parse_verify_code(""))

    def test_turkish_name_fold(self) -> None:
        self.assertEqual(normalize_match_text("Çağrı Gider"), "cagri gider")
        self.assertTrue(names_match("Çağrı Gider", "Cagri Gider"))
        self.assertFalse(names_match("Çağrı Gider", "Jordan Example"))

    def test_cloudflare_block_is_not_an_invalid_badge(self) -> None:
        self.assertTrue(
            _academy_blocked(
                {
                    "error_code": 1010,
                    "status": 403,
                    "cloudflare_error": True,
                    "valid": False,
                }
            )
        )
        self.assertFalse(_academy_blocked({}))
        self.assertFalse(_academy_blocked({"valid": True}))


class CatalogTest(IsolatedDbTestCase):
    def test_add_list_counts(self) -> None:
        insert_person(self.conn, ALEX)
        insert_person(self.conn, JORDAN)
        code, payload = insert_certificate(self.conn, {"name": COURSE, "notes": "API"})
        self.assertEqual(code, 201)
        self.assertEqual(payload["haveCount"], 0)
        self.assertEqual(payload["peopleCount"], 2)
        listed = list_certificates(self.conn)
        self.assertEqual(len(listed), 1)
        self.assertEqual(listed[0]["name"], COURSE)
        self.assertEqual(listed[0]["haveCount"], 0)
        self.assertEqual(listed[0]["peopleCount"], 2)

    def test_duplicate_name_409(self) -> None:
        insert_certificate(self.conn, {"name": COURSE})
        code, payload = insert_certificate(self.conn, {"name": COURSE})
        self.assertEqual(code, 409)
        self.assertEqual(payload, {"error": "duplicate_name"})

    def test_missing_name_400(self) -> None:
        code, payload = insert_certificate(self.conn, {"notes": "x"})
        self.assertEqual(code, 400)
        self.assertEqual(payload, {"error": "missing_name"})

    def test_update_and_detail_lists(self) -> None:
        insert_person(self.conn, ALEX)
        insert_person(self.conn, JORDAN)
        _, created = insert_certificate(self.conn, {"name": "Claude 101"})
        cid = created["id"]
        code, updated = update_certificate(
            self.conn, cid, {"name": "Claude 101", "url": "https://academy.claude.com/courses/claude-101"}
        )
        self.assertEqual(code, 200)
        self.assertEqual(updated["url"], "https://academy.claude.com/courses/claude-101")
        self.assertEqual(len(updated["missing"]), 2)
        self.assertEqual(updated["holders"], [])

    def test_delete_catalog_cascades_assignments(self) -> None:
        insert_person(self.conn, ALEX)
        _, created = insert_certificate(self.conn, {"name": COURSE})
        add_person_certificate(
            self.conn,
            "90001",
            {"verifyCode": CODE_A},
            fetcher=lambda _code: badge(),
        )
        code, payload = delete_certificate(self.conn, created["id"])
        self.assertEqual(code, 200)
        self.assertEqual(payload["ok"], True)
        report = person_report(self.conn, "90001")
        self.assertEqual(report["certificates"], [])


class AssignTest(IsolatedDbTestCase):
    def setUp(self) -> None:
        super().setUp()
        insert_person(self.conn, ALEX)
        insert_person(self.conn, JORDAN)
        _, created = insert_certificate(self.conn, {"name": COURSE})
        self.cid = created["id"]

    def test_happy_path_url(self) -> None:
        url = f"https://academy.claude.com/verify/{CODE_A}"
        code, payload = add_person_certificate(
            self.conn,
            "90001",
            {"url": url},
            fetcher=lambda _code: badge(),
        )
        self.assertEqual(code, 201)
        self.assertEqual(payload["verifyCode"], CODE_A)
        self.assertEqual(payload["name"], COURSE)
        self.assertFalse(payload["forced"])
        listed = list_certificates(self.conn)
        self.assertEqual(listed[0]["haveCount"], 1)
        detail = get_certificate(self.conn, self.cid)
        self.assertEqual([h["id"] for h in detail["holders"]], ["90001"])
        self.assertEqual([m["id"] for m in detail["missing"]], ["90002"])
        report = person_report(self.conn, "90001")
        self.assertEqual(len(report["certificates"]), 1)

    def test_malformed_code_no_fetch(self) -> None:
        called = {"n": 0}

        def boom(_code: str) -> dict:
            called["n"] += 1
            raise AssertionError("must not call Academy")

        code, payload = add_person_certificate(
            self.conn, "90001", {"url": "nope"}, fetcher=boom
        )
        self.assertEqual(code, 422)
        self.assertFalse(payload["forceAllowed"])
        self.assertEqual(payload["fields"][0]["field"], "verifyCode")
        self.assertEqual(payload["fields"][0]["problem"], "geçersiz")
        self.assertEqual(called["n"], 0)

    def test_invalid_badge(self) -> None:
        code, payload = add_person_certificate(
            self.conn,
            "90001",
            {"verifyCode": CODE_A},
            fetcher=lambda _code: badge(valid=False),
        )
        self.assertEqual(code, 422)
        self.assertFalse(payload["forceAllowed"])
        self.assertEqual(payload["fields"][0]["field"], "academy")
        self.assertEqual(payload["fields"][0]["problem"], "not exist")

    def test_name_mismatch_then_force(self) -> None:
        code, payload = add_person_certificate(
            self.conn,
            "90001",
            {"verifyCode": CODE_A},
            fetcher=lambda _code: badge(name="Someone Else"),
        )
        self.assertEqual(code, 422)
        self.assertTrue(payload["forceAllowed"])
        self.assertEqual(payload["fields"][0]["field"], "name")
        self.assertEqual(payload["fields"][0]["expected"], "Çağrı Gider")
        self.assertEqual(payload["fields"][0]["actual"], "Someone Else")
        self.assertEqual(list_certificates(self.conn)[0]["haveCount"], 0)

        code, saved = add_person_certificate(
            self.conn,
            "90001",
            {"verifyCode": CODE_A, "force": True},
            fetcher=lambda _code: badge(name="Someone Else"),
        )
        self.assertEqual(code, 201)
        self.assertTrue(saved["forced"])
        self.assertEqual(saved["forceFields"], ["name"])

    def test_title_not_in_list_force_creates_catalog(self) -> None:
        code, payload = add_person_certificate(
            self.conn,
            "90001",
            {"verifyCode": CODE_A},
            fetcher=lambda _code: badge(title="Claude Code 101"),
        )
        self.assertEqual(code, 422)
        self.assertTrue(payload["forceAllowed"])
        cert_field = payload["fields"][0]
        self.assertEqual(cert_field["field"], "certificate")
        self.assertEqual(cert_field["problem"], "listede yok")
        self.assertEqual(cert_field["actual"], "Claude Code 101")
        self.assertIn(COURSE, cert_field["expected"])

        code, saved = add_person_certificate(
            self.conn,
            "90001",
            {"verifyCode": CODE_A, "force": True},
            fetcher=lambda _code: badge(title="Claude Code 101"),
        )
        self.assertEqual(code, 201)
        self.assertEqual(saved["name"], "Claude Code 101")
        names = [c["name"] for c in list_certificates(self.conn)]
        self.assertIn("Claude Code 101", names)

    def test_force_rejected_for_invalid_or_duplicate(self) -> None:
        add_person_certificate(
            self.conn,
            "90001",
            {"verifyCode": CODE_A},
            fetcher=lambda _code: badge(),
        )
        code, payload = add_person_certificate(
            self.conn,
            "90002",
            {"verifyCode": CODE_A, "force": True},
            fetcher=lambda _code: badge(name="Jordan Example"),
        )
        self.assertEqual(code, 422)
        self.assertFalse(payload["forceAllowed"])
        problems = {f["field"]: f["problem"] for f in payload["fields"]}
        self.assertEqual(problems["verifyCode"], "zaten kayıtlı")

    def test_unreachable(self) -> None:
        def fail(_code: str) -> dict:
            raise AcademyUnreachable("down")

        code, payload = add_person_certificate(
            self.conn, "90001", {"verifyCode": CODE_A}, fetcher=fail
        )
        self.assertEqual(code, 503)
        self.assertEqual(payload["error"], "academy_unreachable")

    def test_delete_person_cascades_assignments(self) -> None:
        add_person_certificate(
            self.conn,
            "90001",
            {"verifyCode": CODE_A},
            fetcher=lambda _code: badge(),
        )
        delete_person(self.conn, "90001")
        listed = list_certificates(self.conn)
        self.assertEqual(listed[0]["haveCount"], 0)
        self.assertEqual(listed[0]["peopleCount"], 1)
