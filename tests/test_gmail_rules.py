from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from claude_daily_memory.gmail_rules import CleanupRule, GmailMessage, matching_rule


class GmailRuleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.now = datetime(2026, 8, 12, tzinfo=timezone.utc)
        self.rule = CleanupRule(
            name="old-promotions",
            sender_domains=("news.example",),
            required_labels=("CATEGORY_PROMOTIONS",),
            older_than_days=30,
            exclude_subject_patterns=("receipt|security",),
        )

    def message(self, *, subject: str = "Weekly sale", age: int = 45) -> GmailMessage:
        return GmailMessage(
            message_id="message-id",
            sender="offers@news.example",
            subject=subject,
            labels=frozenset({"CATEGORY_PROMOTIONS"}),
            received_at=self.now - timedelta(days=age),
        )

    def test_exact_match_can_be_trashed_without_confirmation(self) -> None:
        self.assertEqual(matching_rule(self.message(), [self.rule], now=self.now), "old-promotions")

    def test_partial_or_excluded_match_stays(self) -> None:
        self.assertIsNone(matching_rule(self.message(age=2), [self.rule], now=self.now))
        self.assertIsNone(matching_rule(self.message(subject="Your receipt"), [self.rule], now=self.now))

    def test_rule_cannot_be_unbounded(self) -> None:
        with self.assertRaises(ValueError):
            CleanupRule(name="delete everything")


if __name__ == "__main__":
    unittest.main()
