from __future__ import annotations

import json
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from claude_daily_memory.hooks import MetadataLogger


class MetadataLoggerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.projects = self.root / "projects"
        self.first = self.projects / "first"
        self.second = self.projects / "second"
        self.first.mkdir(parents=True)
        self.second.mkdir()
        self.events = self.root / "state" / "events.jsonl"
        self.key = self.root / "config" / "hmac.key"
        self.key.parent.mkdir()
        self.key.write_bytes(b"x" * 32)
        self.logger = MetadataLogger(self.projects, self.events, self.key)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_records_only_allowlisted_metadata(self) -> None:
        secret = "SECRET_TEST_VALUE"
        self.assertTrue(
            self.logger.record(
                {
                    "hook_event_name": "PostToolUse",
                    "cwd": str(self.first),
                    "session_id": "real-id",
                    "transcript_path": secret,
                    "tool_name": "Read",
                    "tool_input": {"password": secret},
                    "tool_response": secret,
                }
            )
        )
        raw = self.events.read_text(encoding="utf-8")
        event = json.loads(raw)
        self.assertNotIn(secret, raw)
        self.assertNotIn("real-id", raw)
        self.assertEqual(event["tool"], "Read")
        self.assertEqual(set(event), {"time", "event", "session", "project", "tool"})

    def test_distinguishes_projects_and_ignores_outside(self) -> None:
        self.assertTrue(self.logger.record({"hook_event_name": "SessionEnd", "cwd": str(self.first), "session_id": "1"}))
        self.assertTrue(self.logger.record({"hook_event_name": "SessionStart", "cwd": str(self.second), "session_id": "2"}))
        self.assertFalse(self.logger.record({"hook_event_name": "SessionStart", "cwd": str(self.root), "session_id": "3"}))
        events = [json.loads(line) for line in self.events.read_text(encoding="utf-8").splitlines()]
        self.assertNotEqual(events[0]["project"], events[1]["project"])

    def test_concurrent_writes_are_valid(self) -> None:
        def write(index: int) -> bool:
            return self.logger.record(
                {"hook_event_name": "UserPromptSubmit", "cwd": str(self.first), "session_id": str(index)}
            )

        with ThreadPoolExecutor(max_workers=8) as executor:
            self.assertTrue(all(executor.map(write, range(50))))
        lines = self.events.read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(lines), 50)
        self.assertEqual(len([json.loads(line) for line in lines]), 50)


if __name__ == "__main__":
    unittest.main()
