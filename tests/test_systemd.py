from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class SystemdTests(unittest.TestCase):
    def test_service_has_security_boundaries(self) -> None:
        text = (ROOT / "systemd" / "claude-daily-memory.service").read_text(encoding="utf-8")
        for setting in (
            "Type=oneshot",
            "UMask=0077",
            "NoNewPrivileges=true",
            "ProtectSystem=strict",
            "ProtectHome=read-only",
            "PrivateDevices=true",
            "RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6",
        ):
            self.assertIn(setting, text)
        self.assertIn("ReadOnlyPaths=%h/.config/claude-daily-memory", text)
        self.assertIn("%h/.notebooklm", text)
        self.assertNotIn(".claude/projects", text)
        self.assertNotIn("gmail", text.casefold())

    def test_timer_catches_up_and_runs_daily(self) -> None:
        text = (ROOT / "systemd" / "claude-daily-memory.timer").read_text(encoding="utf-8")
        self.assertIn("OnCalendar=*-*-*", text)
        self.assertIn("Persistent=true", text)
        self.assertIn("RandomizedDelaySec=", text)


if __name__ == "__main__":
    unittest.main()
