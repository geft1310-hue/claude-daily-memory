from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from claude_daily_memory import google_drive
from claude_daily_memory.google_drive import (
    GoogleDriveMemory,
    GoogleIntegrationError,
    _read_client_config,
    credentials_from_keyring,
    digest_id,
)


class GoogleDriveTests(unittest.TestCase):
    def test_extracts_only_document_text(self) -> None:
        document = {
            "body": {
                "content": [
                    {"paragraph": {"elements": [{"textRun": {"content": "first"}}]}},
                    {"table": {"not-read": "secret"}},
                    {"paragraph": {"elements": [{"textRun": {"content": " second"}}]}},
                ]
            }
        }
        self.assertEqual(GoogleDriveMemory._document_text(document), "first second")

    def test_digest_id_is_stable_and_keyed(self) -> None:
        first = digest_id(b"a" * 32, "2026-08-12", "safe")
        second = digest_id(b"a" * 32, "2026-08-12", "safe")
        other = digest_id(b"b" * 32, "2026-08-12", "safe")
        self.assertEqual(first, second)
        self.assertNotEqual(first, other)
        self.assertRegex(first, r"^[0-9a-f]{32}$")

    def test_client_config_preserves_quota_project(self) -> None:
        import json
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "client.json"
            path.write_text(
                json.dumps(
                    {
                        "installed": {
                            "client_id": "client-test",
                            "client_secret": "secret-test",
                            "token_uri": "https://oauth2.googleapis.com/token",
                            "quota_project_id": "quota-test",
                        }
                    }
                ),
                encoding="utf-8",
            )
            self.assertEqual(_read_client_config(path)["quota_project_id"], "quota-test")

    def test_credentials_receive_quota_project(self) -> None:
        created: list[dict[str, object]] = []

        class Credentials:
            valid = True

            def __init__(self, **kwargs: object) -> None:
                created.append(kwargs)

            def refresh(self, request: object) -> None:
                pass

            def has_scopes(self, scopes: list[str]) -> bool:
                return True

        keyring = type("Keyring", (), {"get_password": lambda *args: "refresh-test"})()
        config = {
            "client_id": "client-test",
            "client_secret": "secret-test",
            "token_uri": "https://oauth2.googleapis.com/token",
            "quota_project_id": "quota-test",
        }
        with (
            patch.object(google_drive, "_imports", return_value=(keyring, object, Credentials, None, None)),
            patch.object(google_drive, "_read_client_config", return_value=config),
        ):
            credentials_from_keyring(Path("client.json"))

        self.assertEqual(created[0]["quota_project_id"], "quota-test")

    def test_rejects_unexpected_token_endpoint(self) -> None:
        import json
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "client.json"
            path.write_text(
                json.dumps(
                    {
                        "installed": {
                            "client_id": "client-test",
                            "client_secret": "secret-test",
                            "token_uri": "https://example.invalid/token",
                        }
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaises(GoogleIntegrationError):
                _read_client_config(path)


if __name__ == "__main__":
    unittest.main()
