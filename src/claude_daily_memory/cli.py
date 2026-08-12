"""Command-line entry points for local daily memory jobs."""

from __future__ import annotations

import argparse
import json
import os
from datetime import date, datetime, timezone
from pathlib import Path

from .audit import append_audit
from .digest import DailyDigestBuilder


def _key(path: Path) -> bytes:
    key = path.expanduser().read_bytes()
    if len(key) < 32:
        raise ValueError("HMAC key must contain at least 32 bytes")
    return key


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Privacy-first daily memory for Claude Code")
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build", help="Build a local sanitized daily digest")
    build.add_argument("--workspace", type=Path, required=True)
    build.add_argument("--projects-root", type=Path, required=True)
    build.add_argument("--hmac-key", type=Path, required=True)
    build.add_argument("--day", type=date.fromisoformat)
    return parser


def main() -> int:
    args = _parser().parse_args()
    if args.command != "build":
        return 2
    audit_path = args.workspace.expanduser() / "events" / "digest_audit.jsonl"
    try:
        result = DailyDigestBuilder(
            args.workspace,
            args.projects_root,
            hmac_key=_key(args.hmac_key),
        ).build(args.day)
        append_audit(
            audit_path,
            {
                "time": datetime.now(timezone.utc).isoformat(),
                "day": result.day,
                "included": result.included,
                "excluded": result.excluded,
                "bytes": len(result.text.encode("utf-8")),
                "rules": result.rules,
                "excluded_sources": result.excluded_sources,
                "status": "success",
                "error_code": "local-only",
            },
        )
        print(json.dumps({"status": "success", "day": result.day, "path": str(result.path)}))
        return 0
    except Exception as error:
        append_audit(
            audit_path,
            {
                "time": datetime.now(timezone.utc).isoformat(),
                "day": str(getattr(args, "day", None) or "automatic"),
                "status": "failure",
                "error_code": type(error).__name__,
            },
        )
        print(json.dumps({"status": "failure", "error_code": type(error).__name__}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
