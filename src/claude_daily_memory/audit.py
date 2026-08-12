"""Content-free audit records for daily memory exports."""

from __future__ import annotations

import fcntl
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


def append_audit(path: Path, record: dict[str, Any], *, retention_days: int = 90) -> None:
    """Append a safe record and remove records older than the retention window."""
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    path.parent.chmod(0o700)
    descriptor = os.open(path, os.O_APPEND | os.O_CREAT | os.O_RDWR, 0o600)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        with os.fdopen(os.dup(descriptor), "r", encoding="utf-8") as reader:
            existing = reader.read().splitlines()
        cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
        retained: list[str] = []
        for line in existing:
            try:
                item = json.loads(line)
                timestamp = datetime.fromisoformat(item["time"])
                if timestamp >= cutoff:
                    retained.append(json.dumps(item, ensure_ascii=False, sort_keys=True))
            except (ValueError, TypeError, KeyError, json.JSONDecodeError):
                continue
        safe_record = {
            "time": record.get("time", datetime.now(timezone.utc).isoformat()),
            "day": str(record.get("day", "unknown")),
            "included": int(record.get("included", 0)),
            "excluded": int(record.get("excluded", 0)),
            "bytes": int(record.get("bytes", 0)),
            "rules": sorted({str(item) for item in record.get("rules", [])}),
            "excluded_sources": sorted({str(item) for item in record.get("excluded_sources", [])}),
            "status": "success" if record.get("status") == "success" else "failure",
            "error_code": str(record.get("error_code", ""))[:80],
            "drive_file": str(record.get("drive_file", ""))[:64],
            "revision": str(record.get("revision", ""))[:128],
        }
        retained.append(json.dumps(safe_record, ensure_ascii=False, sort_keys=True))
        os.lseek(descriptor, 0, os.SEEK_SET)
        os.ftruncate(descriptor, 0)
        os.write(descriptor, ("\n".join(retained) + "\n").encode("utf-8"))
        os.fsync(descriptor)
    finally:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
        finally:
            os.close(descriptor)
    path.chmod(0o600)
