"""Fail-closed filtering for text that may leave the local machine."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass

MAX_EXPORT_BYTES = 512_000
MAX_LINE_LENGTH = 8_000

_DENY_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("private-key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |PGP )?PRIVATE KEY-----")),
    ("authorization-header", re.compile(r"(?im)^\s*(?:authorization|proxy-authorization)\s*:\s*\S+")),
    ("cookie", re.compile(r"(?im)^\s*(?:cookie|set-cookie)\s*:\s*\S+")),
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b")),
    ("aws-access-key", re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b")),
    ("github-token", re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{50,})\b")),
    ("google-api-key", re.compile(r"\bAIza[0-9A-Za-z_-]{30,50}\b")),
    ("slack-token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b")),
    ("generic-secret-assignment", re.compile(
        r"(?im)^\s*(?:export\s+)?[A-Z0-9_]*(?:PASSWORD|PASSWD|SECRET|TOKEN|API_KEY|ACCESS_KEY|PRIVATE_KEY|CLIENT_SECRET|COOKIE)[A-Z0-9_]*\s*[=:]\s*\S+"
    )),
    ("raw-transcript-field", re.compile(
        r"(?im)^\s*[\"']?(?:tool_input|tool_response|transcript_path|last_assistant_message|raw_prompt|raw_response)[\"']?\s*[:=]"
    )),
)

_EMAIL_RE = re.compile(r"(?<![\w.+-])[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}(?![\w.-])", re.IGNORECASE)
_PHONE_RE = re.compile(r"(?<!\w)(?:\+?\d[\d ()-]{8,}\d)(?!\w)")
_HOME_PATH_RE = re.compile(r"(?<!\w)/home/[^/\s]+")
_CANDIDATE_SECRET_RE = re.compile(r"(?<![A-Za-z0-9])[A-Za-z0-9_+\-/=]{40,}(?![A-Za-z0-9])")
_SAFE_LONG_RE = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64}|[0-9a-f]{128})$", re.IGNORECASE)


@dataclass(frozen=True)
class SanitizeResult:
    allowed: bool
    text: str
    rules: tuple[str, ...]


def _entropy(value: str) -> float:
    if not value:
        return 0.0
    counts: dict[str, int] = {}
    for character in value:
        counts[character] = counts.get(character, 0) + 1
    length = len(value)
    return -sum((count / length) * math.log2(count / length) for count in counts.values())


def sanitize_text(text: str, *, max_bytes: int = MAX_EXPORT_BYTES) -> SanitizeResult:
    """Return sanitized text or deny the entire value when it may contain a secret."""
    try:
        if not isinstance(text, str):
            return SanitizeResult(False, "", ("invalid-type",))
        encoded = text.encode("utf-8", errors="strict")
        if len(encoded) > max_bytes:
            return SanitizeResult(False, "", ("oversize",))
        if "\x00" in text or any(len(line) > MAX_LINE_LENGTH for line in text.splitlines()):
            return SanitizeResult(False, "", ("invalid-markdown",))

        matched = tuple(name for name, pattern in _DENY_PATTERNS if pattern.search(text))
        if matched:
            return SanitizeResult(False, "", matched)

        for candidate in _CANDIDATE_SECRET_RE.findall(text):
            stripped = candidate.rstrip("=")
            if _SAFE_LONG_RE.fullmatch(stripped):
                continue
            character_classes = sum(
                bool(re.search(pattern, stripped))
                for pattern in (r"[a-z]", r"[A-Z]", r"\d", r"[_+\-/=]")
            )
            if character_classes >= 3 and _entropy(stripped) >= 4.3:
                return SanitizeResult(False, "", ("high-entropy-secret",))

        cleaned = _EMAIL_RE.sub("[email]", text)
        cleaned = _PHONE_RE.sub("[phone]", cleaned)
        cleaned = _HOME_PATH_RE.sub("/home/[user]", cleaned)
        redactions: list[str] = []
        if cleaned != text:
            if _EMAIL_RE.search(text):
                redactions.append("email-redacted")
            if _PHONE_RE.search(text):
                redactions.append("phone-redacted")
            if _HOME_PATH_RE.search(text):
                redactions.append("home-path-redacted")
        return SanitizeResult(True, cleaned, tuple(redactions))
    except Exception:
        return SanitizeResult(False, "", ("sanitizer-error",))
