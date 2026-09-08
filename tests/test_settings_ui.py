"""TASK-1.2.1 — Settings UI host and hash-route markers in the SPA (no Python behavior)."""

from __future__ import annotations

import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_APP_JS = _ROOT / "static" / "js" / "app.js"
_INDEX = _ROOT / "static" / "index.html"


class SettingsUiHostTest(unittest.TestCase):
    def test_settings_import_host_and_hash_route_are_present(self) -> None:
        app_js = _APP_JS.read_text(encoding="utf-8")
        index_html = _INDEX.read_text(encoding="utf-8")

        self.assertIn('id="settings-import"', app_js)
        self.assertIn("#/settings", index_html)
