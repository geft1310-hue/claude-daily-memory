from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class InstallerContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.text = (ROOT / "install.sh").read_text(encoding="utf-8")

    def test_installs_one_complete_application_environment(self) -> None:
        self.assertIn('"${PROJECT_DIR}[google,gemini,notebooklm]"', self.text)
        self.assertIn('"${APP_DIR}/venv/bin/playwright" install chromium', self.text)
        self.assertNotIn("notebooklm-py/venv", self.text)
        self.assertFalse((ROOT / "install-notebooklm.sh").exists())

    def test_timer_remains_disabled_until_complete_setup(self) -> None:
        disable = "systemctl --user disable --now claude-daily-memory.timer"
        self.assertIn(disable, self.text)
        self.assertNotIn("systemctl --user enable --now", self.text)

    def test_supported_path_has_no_remote_or_master_token_mode(self) -> None:
        forbidden = (
            "NOTEBOOKLM_AUTH_JSON",
            "--master-token",
            "--transport http",
            "notebooklm-server",
        )
        for value in forbidden:
            self.assertNotIn(value, self.text)

    def test_installer_is_idempotent_in_isolated_home_without_cloud_login(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            home = root / "home"
            fake_bin = root / "bin"
            log = root / "commands.log"
            home.mkdir()
            fake_bin.mkdir()

            python = fake_bin / "python3"
            python.write_text(
                "#!/bin/sh\n"
                "if [ \"$1\" = \"-c\" ]; then exit 0; fi\n"
                "if [ \"$1\" = \"-m\" ] && [ \"$2\" = \"venv\" ]; then\n"
                "  mkdir -p \"$3/bin\"\n"
                "  cp \"$0\" \"$3/bin/python\"\n"
                "  printf '#!/bin/sh\\nprintf x' > \"$3/bin/playwright\"\n"
                "  chmod +x \"$3/bin/playwright\"\n"
                "  exit 0\n"
                "fi\n"
                f"printf '%s\\n' \"python:$*\" >> '{log}'\n",
                encoding="utf-8",
            )
            python.chmod(0o755)

            systemctl = fake_bin / "systemctl"
            systemctl.write_text(
                "#!/bin/sh\n" f"printf '%s\\n' \"systemctl:$*\" >> '{log}'\n",
                encoding="utf-8",
            )
            systemctl.chmod(0o755)

            environment = os.environ.copy()
            environment["HOME"] = str(home)
            environment["PATH"] = f"{fake_bin}:{environment['PATH']}"
            for _ in range(2):
                subprocess.run(
                    ["bash", str(ROOT / "install.sh")],
                    cwd=ROOT,
                    env=environment,
                    check=True,
                    text=True,
                    capture_output=True,
                )

            commands = log.read_text(encoding="utf-8")
            self.assertNotIn("systemctl:--user enable", commands)
            self.assertEqual(commands.count("systemctl:--user daemon-reload"), 2)
            self.assertTrue(
                (home / ".local/share/claude-daily-memory/venv").is_dir()
            )
            key = home / ".config/claude-daily-memory/hmac.key"
            self.assertTrue(key.is_file())
            self.assertEqual(key.stat().st_mode & 0o777, 0o600)


if __name__ == "__main__":
    unittest.main()
