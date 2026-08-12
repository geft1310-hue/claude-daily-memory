from __future__ import annotations

import unittest

from claude_daily_memory.sanitize import sanitize_text


class SanitizeTests(unittest.TestCase):
    def test_blocks_known_secret_shapes(self) -> None:
        samples = {
            "private": "-----BEGIN PRIVATE KEY-----\nnot-real\n-----END PRIVATE KEY-----",
            "github": "ghp_abcdefghijklmnopqrstuvwxyzABCDEF123456",
            "google": "AIzaSyDUMMYDUMMYDUMMYDUMMYDUMMYDUMMY1",
            "jwt": "eyJabcdefghijk.abcdefghijklmnop.abcdefghijklmnop",
            "env": "SERVICE_API_KEY=ThisIsNotARealSecretButMustBeBlocked123",
            "cookie": "Cookie: SID=not-a-real-cookie",
            "transcript": '"tool_response": "private"',
        }
        for name, sample in samples.items():
            with self.subTest(name=name):
                result = sanitize_text(sample)
                self.assertFalse(result.allowed)
                self.assertEqual(result.text, "")

    def test_redacts_personal_data(self) -> None:
        result = sanitize_text("Write to person@example.com or +1 (555) 123-4567 in /home/alice/project")
        self.assertTrue(result.allowed)
        self.assertNotIn("person@example.com", result.text)
        self.assertNotIn("555", result.text)
        self.assertNotIn("alice", result.text)

    def test_allows_normal_markdown_and_hashes(self) -> None:
        result = sanitize_text(
            "# Decision\n\nUse local storage for task abc-123.\n"
            "Commit: 0123456789abcdef0123456789abcdef01234567\n"
        )
        self.assertTrue(result.allowed)
        self.assertIn("local storage", result.text)


if __name__ == "__main__":
    unittest.main()
