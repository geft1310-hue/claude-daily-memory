"""Privacy-preserving Claude Code lifecycle metadata hook."""

from __future__ import annotations

import fcntl
import hashlib
import hmac
import json
import os
import secrets
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ALLOWED_EVENTS = {"SessionStart", "UserPromptSubmit", "PostToolUse", "Stop", "SessionEnd"}
ALLOWED_TOOLS = {
    "Agent",
    "AskUserQuestion",
    "Bash",
    "Edit",
    "NotebookEdit",
    "Read",
    "Skill",
    "WebFetch",
    "WebSearch",
    "Write",
}


class MetadataLogger:
    def __init__(self, projects_root: Path, event_file: Path, key_file: Path) -> None:
        self.projects_root = projects_root.expanduser().resolve()
        self.event_file = event_file.expanduser()
        self.key_file = key_file.expanduser()

    def record(self, payload: dict[str, Any]) -> bool:
        cwd_raw = payload.get("cwd")
        if not isinstance(cwd_raw, str) or not cwd_raw:
            return False
        cwd = Path(cwd_raw).expanduser().resolve()
        project = self._project_root(cwd)
        if project is None:
            return False

        event_name = payload.get("hook_event_name")
        if not isinstance(event_name, str) or event_name not in ALLOWED_EVENTS:
            return False

        session_raw = payload.get("session_id")
        session = session_raw if isinstance(session_raw, str) else "unknown"
        event: dict[str, str] = {
            "time": datetime.now(timezone.utc).isoformat(),
            "event": event_name,
            "session": self._digest(session),
            "project": self._digest(str(project)),
        }
        if event_name == "PostToolUse":
            tool_raw = payload.get("tool_name")
            event["tool"] = tool_raw if isinstance(tool_raw, str) and tool_raw in ALLOWED_TOOLS else "other"
        self._append(event)
        return True

    def _project_root(self, cwd: Path) -> Path | None:
        if cwd == self.projects_root or not cwd.is_relative_to(self.projects_root):
            return None
        candidate = self.projects_root / cwd.relative_to(self.projects_root).parts[0]
        try:
            if candidate.is_symlink() or not candidate.is_dir():
                return None
            resolved = candidate.resolve(strict=True)
        except OSError:
            return None
        return resolved if resolved.parent == self.projects_root else None

    def _append(self, event: dict[str, str]) -> None:
        self.event_file.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.event_file.parent.chmod(0o700)
        descriptor = os.open(self.event_file, os.O_APPEND | os.O_CREAT | os.O_WRONLY, 0o600)
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX)
            os.write(descriptor, (json.dumps(event, ensure_ascii=False) + "\n").encode("utf-8"))
            os.fsync(descriptor)
        finally:
            try:
                fcntl.flock(descriptor, fcntl.LOCK_UN)
            finally:
                os.close(descriptor)
        self.event_file.chmod(0o600)

    def _digest(self, value: str) -> str:
        return hmac.new(self._load_key(), value.encode("utf-8"), hashlib.sha256).hexdigest()[:24]

    def _load_key(self) -> bytes:
        if not self.key_file.exists():
            self.key_file.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            self.key_file.write_bytes(secrets.token_bytes(32))
            self.key_file.chmod(0o600)
        key = self.key_file.read_bytes()
        if len(key) < 32:
            raise ValueError("HMAC key is too short")
        return key


def main() -> int:
    """Read one hook payload. Errors intentionally never block Claude Code."""
    try:
        raw = sys.stdin.read(1_048_577)
        if len(raw) > 1_048_576:
            return 0
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            return 0
        home = Path.home()
        logger = MetadataLogger(
            projects_root=Path(os.environ.get("CDM_PROJECTS_ROOT", home / "projects")),
            event_file=Path(os.environ.get("CDM_EVENT_FILE", home / ".local/state/claude-daily-memory/events.jsonl")),
            key_file=Path(os.environ.get("CDM_HMAC_KEY", home / ".config/claude-daily-memory/hmac.key")),
        )
        logger.record(payload)
    except Exception:
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
