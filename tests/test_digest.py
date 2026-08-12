from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from datetime import date, datetime, timezone
from pathlib import Path

from claude_daily_memory.digest import DailyDigestBuilder


SCHEMA = """
CREATE TABLE artifacts (id TEXT PRIMARY KEY, project TEXT);
CREATE TABLE task_artifacts (
    id INTEGER PRIMARY KEY, task_id TEXT, artifact_type TEXT, file_path TEXT,
    created_at TEXT, is_demo INTEGER DEFAULT 0
);
"""


class DigestTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temp.name) / "workspace"
        self.projects = Path(self.temp.name) / "projects"
        self.projects.mkdir()
        (self.workspace / "tasks" / "log" / "task").mkdir(parents=True)
        (self.workspace / "events").mkdir()
        self.db = self.workspace / "tasks" / "routing.db"
        with sqlite3.connect(self.db) as connection:
            connection.executescript(SCHEMA)
        self.builder = DailyDigestBuilder(self.workspace, self.projects, hmac_key=b"a" * 32)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def add_artifact(self, content: str, created_at: str = "2026-08-12T12:00:00+00:00") -> None:
        artifact = self.workspace / "tasks" / "log" / "task" / "decision.md"
        artifact.write_text(content, encoding="utf-8")
        with sqlite3.connect(self.db) as connection:
            connection.execute("INSERT OR IGNORE INTO artifacts VALUES ('task', 'project-one')")
            connection.execute(
                "INSERT INTO task_artifacts VALUES (1, 'task', 'decision', ?, ?, 0)",
                (str(artifact.relative_to(self.workspace)), created_at),
            )

    def test_builds_deterministic_digest(self) -> None:
        self.add_artifact("# Решение\n\nИспользовать безопасное локальное хранение.\n")
        first = self.builder.build(date(2026, 8, 12))
        second = self.builder.build(date(2026, 8, 12))
        self.assertEqual(first.text, second.text)
        self.assertEqual(first.included, 1)
        self.assertIn("Исторические", first.text)
        self.assertEqual(first.path.stat().st_mode & 0o777, 0o600)

    def test_excludes_secret_artifact_without_copying_secret(self) -> None:
        secret = "ghp_abcdefghijklmnopqrstuvwxyzABCDEF123456"
        self.add_artifact(f"Token: {secret}")
        result = self.builder.build(date(2026, 8, 12))
        self.assertEqual(result.included, 0)
        self.assertEqual(result.excluded, 1)
        self.assertNotIn(secret, result.text)
        self.assertIn("github-token", result.rules)

    def test_aggregates_only_safe_event_fields(self) -> None:
        event = {
            "time": datetime(2026, 8, 12, 12, tzinfo=timezone.utc).isoformat(),
            "event": "UserPromptSubmit",
            "session": "abc",
            "project": "project-one",
            "private": "must-not-appear",
        }
        (self.workspace / "events" / "events.jsonl").write_text(json.dumps(event) + "\n", encoding="utf-8")
        result = self.builder.build(date(2026, 8, 12))
        self.assertIn("1 запросов", result.text)
        self.assertNotIn("must-not-appear", result.text)


if __name__ == "__main__":
    unittest.main()
