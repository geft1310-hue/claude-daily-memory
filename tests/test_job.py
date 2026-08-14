from __future__ import annotations

import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from claude_daily_memory import job
from claude_daily_memory.google_drive import AppendResult
from claude_daily_memory.notebooklm_integration import MemoryBinding


class JobIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.workspace = self.root / "workspace"
        (self.workspace / "events").mkdir(parents=True)
        self.projects = self.root / "projects"
        self.projects.mkdir()
        self.key = self.root / "hmac.key"
        self.key.write_bytes(b"k" * 32)
        self.google_client = self.root / "google-client.json"
        self.google_client.write_text("{}", encoding="utf-8")
        self.config = self.root / "config.json"
        self.config.write_text(
            json.dumps(
                {
                    "drive_file_id": "drive-test",
                    "notebooklm_profile": "default",
                    "notebooklm_notebook_id": "nb-test",
                    "notebooklm_source_id": "source-test",
                }
            ),
            encoding="utf-8",
        )
        self.state = self.root / "state.json"
        self.result = types.SimpleNamespace(
            day="2026-08-12",
            text="# Safe memory\n",
            included=1,
            excluded=0,
            rules=(),
            excluded_sources=(),
        )

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _argv(self, *extra: str) -> list[str]:
        return [
            "job",
            "--workspace",
            str(self.workspace),
            "--projects-root",
            str(self.projects),
            "--hmac-key",
            str(self.key),
            "--google-client",
            str(self.google_client),
            "--config",
            str(self.config),
            "--state",
            str(self.state),
            "--day",
            "2026-08-12",
            *extra,
        ]

    def test_refreshes_memory_source_after_drive_append(self) -> None:
        memory = Mock()
        memory.append_once.return_value = AppendResult("drive-test", "rev-test", True)
        notebooklm = Mock()
        with (
            patch.object(sys, "argv", self._argv()),
            patch.object(job.DailyDigestBuilder, "build", return_value=self.result),
            patch.object(job, "credentials_from_keyring", return_value=object()),
            patch.object(job, "GoogleDriveMemory", return_value=memory),
            patch.object(job, "NotebookLMCLI", return_value=notebooklm) as notebooklm_class,
        ):
            self.assertEqual(job.main(), 0)

        notebooklm.refresh_source.assert_called_once_with(MemoryBinding("nb-test", "source-test"))
        executable = notebooklm_class.call_args.args[0]
        self.assertEqual(executable, Path(sys.executable).with_name("notebooklm"))
        state = json.loads(self.state.read_text(encoding="utf-8"))
        self.assertEqual(state["last_successful_day"], "2026-08-12")

    def test_notebooklm_failure_does_not_advance_state(self) -> None:
        memory = Mock()
        memory.append_once.return_value = AppendResult("drive-test", "rev-test", False)
        notebooklm = Mock()
        notebooklm.refresh_source.side_effect = RuntimeError("unavailable")
        with (
            patch.object(sys, "argv", self._argv()),
            patch.object(job.DailyDigestBuilder, "build", return_value=self.result),
            patch.object(job, "credentials_from_keyring", return_value=object()),
            patch.object(job, "GoogleDriveMemory", return_value=memory),
            patch.object(job, "NotebookLMCLI", return_value=notebooklm),
        ):
            self.assertEqual(job.main(), 1)

        self.assertFalse(self.state.exists())
        audit = (self.workspace / "events" / "digest_audit.jsonl").read_text(encoding="utf-8")
        self.assertNotIn("nb-test", audit)
        self.assertNotIn("source-test", audit)

    def test_drive_failure_never_calls_notebooklm(self) -> None:
        memory = Mock()
        memory.append_once.side_effect = RuntimeError("drive failure")
        notebooklm = Mock()
        with (
            patch.object(sys, "argv", self._argv()),
            patch.object(job.DailyDigestBuilder, "build", return_value=self.result),
            patch.object(job, "credentials_from_keyring", return_value=object()),
            patch.object(job, "GoogleDriveMemory", return_value=memory),
            patch.object(job, "NotebookLMCLI", return_value=notebooklm),
        ):
            self.assertEqual(job.main(), 1)

        notebooklm.refresh_source.assert_not_called()

    def test_dry_run_calls_neither_cloud_service(self) -> None:
        with (
            patch.object(sys, "argv", self._argv("--dry-run")),
            patch.object(job.DailyDigestBuilder, "build", return_value=self.result),
            patch.object(job, "GoogleDriveMemory") as drive,
            patch.object(job, "NotebookLMCLI") as notebooklm,
        ):
            self.assertEqual(job.main(), 0)

        drive.assert_not_called()
        notebooklm.assert_not_called()


if __name__ == "__main__":
    unittest.main()
