"""End-to-end daily digest job: local build, scan, Drive append, then state."""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .audit import append_audit
from .digest import DailyDigestBuilder
from .google_drive import GoogleDriveMemory, credentials_from_keyring, digest_id
from .notebooklm_integration import MemoryBinding, NotebookLMCLI


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("Configuration must be an object")
    return value


def _atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    descriptor = os.open(temporary, os.O_CREAT | os.O_TRUNC | os.O_WRONLY, 0o600)
    try:
        os.write(descriptor, (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8"))
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    os.replace(temporary, path)
    path.chmod(0o600)


def _safe_drive_id(key: bytes, file_id: str) -> str:
    return hmac.new(key, file_id.encode("utf-8"), hashlib.sha256).hexdigest()[:24]


def main() -> int:
    parser = argparse.ArgumentParser(description="Build and upload a safe daily memory digest")
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--projects-root", type=Path, required=True)
    parser.add_argument("--hmac-key", type=Path, required=True)
    parser.add_argument("--google-client", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--day", type=date.fromisoformat)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    audit_path = args.workspace / "events" / "digest_audit.jsonl"
    result = None
    key = b""
    try:
        key = args.hmac_key.read_bytes()
        if len(key) < 32:
            raise ValueError("HMAC key is too short")
        day = args.day or (datetime.now().astimezone().date() - timedelta(days=1))
        result = DailyDigestBuilder(args.workspace, args.projects_root, hmac_key=key).build(day)
        if args.dry_run:
            append_audit(
                audit_path,
                {
                    "day": result.day,
                    "included": result.included,
                    "excluded": result.excluded,
                    "bytes": len(result.text.encode("utf-8")),
                    "rules": result.rules,
                    "excluded_sources": result.excluded_sources,
                    "status": "success",
                    "error_code": "dry-run",
                },
            )
            return 0
        config = _read_json(args.config)
        file_id = config.get("drive_file_id")
        if not isinstance(file_id, str) or not file_id:
            raise ValueError("Missing drive_file_id")
        profile = config.get("notebooklm_profile")
        notebook_id = config.get("notebooklm_notebook_id")
        source_id = config.get("notebooklm_source_id")
        if not all(isinstance(value, str) and value for value in (profile, notebook_id, source_id)):
            raise ValueError("Missing NotebookLM memory binding")
        memory = GoogleDriveMemory(credentials_from_keyring(args.google_client))
        append_result = memory.append_once(file_id, digest_id(key, result.day, result.text), result.text)
        notebooklm_executable = Path(sys.executable).with_name("notebooklm")
        notebooklm = NotebookLMCLI(notebooklm_executable, profile=profile)
        notebooklm.refresh_source(MemoryBinding(notebook_id, source_id))
        _atomic_json(
            args.state,
            {
                "last_successful_day": result.day,
                "last_revision": append_result.revision_id,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        append_audit(
            audit_path,
            {
                "day": result.day,
                "included": result.included,
                "excluded": result.excluded,
                "bytes": len(result.text.encode("utf-8")),
                "rules": result.rules,
                "excluded_sources": result.excluded_sources,
                "status": "success",
                "drive_file": _safe_drive_id(key, file_id),
                "revision": append_result.revision_id,
            },
        )
        return 0
    except Exception as error:
        append_audit(
            audit_path,
            {
                "day": result.day if result else str(args.day or "automatic"),
                "included": result.included if result else 0,
                "excluded": result.excluded if result else 0,
                "bytes": len(result.text.encode("utf-8")) if result else 0,
                "rules": result.rules if result else (),
                "excluded_sources": result.excluded_sources if result else (),
                "status": "failure",
                "error_code": type(error).__name__,
            },
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
