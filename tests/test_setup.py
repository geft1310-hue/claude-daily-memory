from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from claude_daily_memory import setup, setup_google
from claude_daily_memory.notebooklm_integration import MemoryBinding


class SetupTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.config = self.root / "config.json"

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_writes_private_complete_binding_and_registers_stdio_mcp(self) -> None:
        notebooklm = Mock()
        notebooklm.ensure_memory.return_value = MemoryBinding("nb-test", "source-test")

        result = setup.finish_notebooklm_setup(
            config_path=self.config,
            drive_file_id="drive-test",
            notebook_title="Claude Daily Memory",
            profile="memory",
            notebooklm=notebooklm,
            confirm=True,
        )

        self.assertEqual(result, MemoryBinding("nb-test", "source-test"))
        saved = json.loads(self.config.read_text(encoding="utf-8"))
        self.assertEqual(
            saved,
            {
                "drive_file_id": "drive-test",
                "notebooklm_notebook_id": "nb-test",
                "notebooklm_profile": "memory",
                "notebooklm_source_id": "source-test",
            },
        )
        self.assertEqual(self.config.stat().st_mode & 0o777, 0o600)
        notebooklm.check_auth.assert_called_once_with()
        notebooklm.register_claude_mcp.assert_called_once_with()
        notebooklm.refresh_source.assert_called_once_with(MemoryBinding("nb-test", "source-test"))

    def test_preview_does_not_create_or_write(self) -> None:
        notebooklm = Mock()
        notebooklm.ensure_memory.side_effect = setup.NotebookLMConfirmationRequired(
            "Would create notebook and source"
        )

        with self.assertRaises(setup.NotebookLMConfirmationRequired):
            setup.finish_notebooklm_setup(
                config_path=self.config,
                drive_file_id="drive-test",
                notebook_title="Claude Daily Memory",
                profile="default",
                notebooklm=notebooklm,
                confirm=False,
            )

        self.assertFalse(self.config.exists())
        notebooklm.register_claude_mcp.assert_not_called()

    def test_complete_setup_requires_confirmation_before_google_or_login(self) -> None:
        notebooklm = Mock()
        with (
            patch.object(setup, "setup_google_document") as google,
            patch.object(setup, "login_notebooklm") as login,
        ):
            with self.assertRaises(setup.NotebookLMConfirmationRequired):
                setup.complete_setup(
                    client_path=self.root / "google-client.json",
                    config_path=self.config,
                    notebook_title="Claude Daily Memory",
                    profile="default",
                    notebooklm=notebooklm,
                    confirm=False,
                )

        google.assert_not_called()
        login.assert_not_called()

    def test_complete_setup_runs_google_login_notebook_binding_and_enables_timer(self) -> None:
        notebooklm = Mock()
        notebooklm.ensure_memory.return_value = MemoryBinding("nb-test", "source-test")
        client_path = self.root / "google-client.json"
        with (
            patch.object(setup, "setup_google_document", return_value="drive-test") as google,
            patch.object(setup, "login_notebooklm") as login,
            patch.object(setup, "gemini_key_is_ready", return_value=True),
            patch.object(setup, "enable_timer") as enable,
        ):
            result = setup.complete_setup(
                client_path=client_path,
                config_path=self.config,
                notebook_title="Claude Daily Memory",
                profile="memory",
                notebooklm=notebooklm,
                confirm=True,
            )

        self.assertEqual(result, MemoryBinding("nb-test", "source-test"))
        google.assert_called_once_with(
            client_path,
            "Claude Daily Memory",
            config_path=self.config,
        )
        login.assert_called_once_with(notebooklm)
        enable.assert_called_once_with()
        notebooklm.check_auth.assert_called_once_with()

    def test_complete_setup_configures_missing_gemini_key_before_timer(self) -> None:
        notebooklm = Mock()
        notebooklm.ensure_memory.return_value = MemoryBinding("nb-test", "source-test")
        with (
            patch.object(setup, "setup_google_document", return_value="drive-test"),
            patch.object(setup, "login_notebooklm"),
            patch.object(setup, "gemini_key_is_ready", return_value=False),
            patch.object(setup, "configure_gemini_key") as configure,
            patch.object(setup, "enable_timer") as enable,
        ):
            setup.complete_setup(
                client_path=self.root / "google-client.json",
                config_path=self.config,
                notebook_title="Claude Daily Memory",
                profile="default",
                notebooklm=notebooklm,
                confirm=True,
            )

        configure.assert_called_once_with()
        enable.assert_called_once_with()

    def test_gemini_key_uses_hidden_prompt_and_system_keyring(self) -> None:
        keyring = Mock()
        keyring.get_password.return_value = "synthetic-key"
        with (
            patch.object(setup, "_keyring", return_value=keyring),
            patch.object(setup.getpass, "getpass", return_value="synthetic-key") as prompt,
        ):
            setup.configure_gemini_key()

        prompt.assert_called_once_with("Gemini API key (hidden input): ")
        keyring.set_password.assert_called_once_with(
            setup.GEMINI_KEYRING_SERVICE,
            setup.GEMINI_KEYRING_ACCOUNT,
            "synthetic-key",
        )

    def test_empty_gemini_key_fails_closed(self) -> None:
        with (
            patch.object(setup, "_keyring"),
            patch.object(setup.getpass, "getpass", return_value=""),
        ):
            with self.assertRaisesRegex(RuntimeError, "cannot be empty"):
                setup.configure_gemini_key()

    def test_google_setup_reuses_existing_configured_document(self) -> None:
        self.config.write_text(json.dumps({"drive_file_id": "drive-test"}), encoding="utf-8")
        with patch.object(setup_google, "authorize_google") as authorize:
            self.assertEqual(
                setup_google.setup_google_document(
                    self.root / "google-client.json",
                    "Claude Daily Memory",
                    config_path=self.config,
                ),
                "drive-test",
            )
        authorize.assert_not_called()

    def test_complete_setup_persists_drive_id_before_notebook_login(self) -> None:
        notebooklm = Mock()
        with (
            patch.object(setup, "setup_google_document", return_value="drive-test"),
            patch.object(setup, "login_notebooklm", side_effect=RuntimeError("login interrupted")),
        ):
            with self.assertRaisesRegex(RuntimeError, "login interrupted"):
                setup.complete_setup(
                    client_path=self.root / "google-client.json",
                    config_path=self.config,
                    notebook_title="Claude Daily Memory",
                    profile="default",
                    notebooklm=notebooklm,
                    confirm=True,
                )

        self.assertEqual(
            json.loads(self.config.read_text(encoding="utf-8")),
            {"drive_file_id": "drive-test"},
        )
        self.assertEqual(self.config.stat().st_mode & 0o777, 0o600)


if __name__ == "__main__":
    unittest.main()
