"""Deterministic, reversible Gmail cleanup rules.

This module decides only whether a message matches an explicit rule. The Gmail
connector remains responsible for moving matches to Trash; permanent deletion
is intentionally unsupported.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable


@dataclass(frozen=True)
class GmailMessage:
    message_id: str
    sender: str
    subject: str
    labels: frozenset[str]
    received_at: datetime


@dataclass(frozen=True)
class CleanupRule:
    name: str
    sender_domains: tuple[str, ...] = ()
    sender_addresses: tuple[str, ...] = ()
    subject_patterns: tuple[str, ...] = ()
    required_labels: tuple[str, ...] = ()
    older_than_days: int | None = None
    exclude_senders: tuple[str, ...] = ()
    exclude_subject_patterns: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("Rule name is required")
        if not any(
            (
                self.sender_domains,
                self.sender_addresses,
                self.subject_patterns,
                self.required_labels,
                self.older_than_days is not None,
            )
        ):
            raise ValueError("A cleanup rule needs at least one positive condition")
        if self.older_than_days is not None and self.older_than_days < 0:
            raise ValueError("older_than_days cannot be negative")
        for pattern in self.subject_patterns + self.exclude_subject_patterns:
            re.compile(pattern)


def matching_rule(
    message: GmailMessage,
    rules: Iterable[CleanupRule],
    *,
    now: datetime | None = None,
) -> str | None:
    """Return one exact matching rule name, otherwise leave the message alone."""
    current = now or datetime.now(timezone.utc)
    sender = message.sender.strip().casefold()
    for rule in rules:
        if sender in {item.casefold() for item in rule.exclude_senders}:
            continue
        if any(re.search(pattern, message.subject, re.IGNORECASE) for pattern in rule.exclude_subject_patterns):
            continue
        checks: list[bool] = []
        if rule.sender_domains:
            checks.append(any(sender.endswith("@" + domain.casefold().lstrip("@")) for domain in rule.sender_domains))
        if rule.sender_addresses:
            checks.append(sender in {item.casefold() for item in rule.sender_addresses})
        if rule.subject_patterns:
            checks.append(any(re.search(pattern, message.subject, re.IGNORECASE) for pattern in rule.subject_patterns))
        if rule.required_labels:
            checks.append(set(rule.required_labels).issubset(message.labels))
        if rule.older_than_days is not None:
            age = current - message.received_at.astimezone(timezone.utc)
            checks.append(age.days >= rule.older_than_days)
        if checks and all(checks):
            return rule.name
    return None


def cleanup_report(matches_by_rule: dict[str, int]) -> str:
    details = ", ".join(f"{name}: {count}" for name, count in sorted(matches_by_rule.items()))
    total = sum(matches_by_rule.values())
    return f"Перемещено в корзину: {total}. {details}" if details else "Ничего не перемещено в корзину."
