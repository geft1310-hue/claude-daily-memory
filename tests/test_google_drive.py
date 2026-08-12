from __future__ import annotations

import unittest

from claude_daily_memory.google_drive import GoogleDriveMemory, digest_id


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


if __name__ == "__main__":
    unittest.main()
