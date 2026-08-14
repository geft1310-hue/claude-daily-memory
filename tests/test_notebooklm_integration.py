from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

from claude_daily_memory.notebooklm_integration import (
    MemoryBinding,
    NotebookLMCLI,
    NotebookLMConfirmationRequired,
    NotebookLMError,
)


class _Runner:
    def __init__(self, responses: list[tuple[int, object]]) -> None:
        self.responses = list(responses)
        self.commands: list[list[str]] = []

    def __call__(self, command: list[str]) -> subprocess.CompletedProcess[str]:
        self.commands.append(command)
        returncode, payload = self.responses.pop(0)
        stdout = payload if isinstance(payload, str) else json.dumps(payload)
        return subprocess.CompletedProcess(command, returncode, stdout, "failure" if returncode else "")


class NotebookLMIntegrationTests(unittest.TestCase):
    def test_login_uses_same_venv_and_selected_profile(self) -> None:
        runner = _Runner([(0, "authenticated")])
        client = NotebookLMCLI(Path("/app/venv/bin/notebooklm"), profile="memory", runner=runner)

        client.login()

        self.assertEqual(
            runner.commands,
            [["/app/venv/bin/notebooklm", "--profile", "memory", "login"]],
        )

    def test_auth_check_is_real_passive_network_check(self) -> None:
        runner = _Runner([(0, {"status": "ok"})])
        client = NotebookLMCLI(Path("/app/venv/bin/notebooklm"), profile="default", runner=runner)

        client.check_auth()

        self.assertEqual(
            runner.commands,
            [[
                "/app/venv/bin/notebooklm",
                "--profile",
                "default",
                "auth",
                "check",
                "--test",
                "--passive",
                "--json",
            ]],
        )

    def test_existing_notebook_and_source_are_reused(self) -> None:
        runner = _Runner(
            [
                (0, {"notebooks": [{"id": "nb-test", "title": "Claude Daily Memory"}]}),
                (
                    0,
                    {
                        "sources": [
                            {
                                "id": "source-test",
                                "title": "Claude Daily Memory",
                                "url": "https://docs.google.com/document/d/drive-test/edit",
                            }
                        ]
                    },
                ),
            ]
        )
        client = NotebookLMCLI(Path("/app/venv/bin/notebooklm"), runner=runner)

        binding = client.ensure_memory("Claude Daily Memory", "drive-test", confirm=False)

        self.assertEqual(binding, MemoryBinding("nb-test", "source-test"))
        self.assertEqual(len(runner.commands), 2)

    def test_missing_notebook_is_previewed_before_creation(self) -> None:
        runner = _Runner([(0, {"notebooks": []})])
        client = NotebookLMCLI(Path("/app/venv/bin/notebooklm"), runner=runner)

        with self.assertRaisesRegex(NotebookLMConfirmationRequired, "create notebook"):
            client.ensure_memory("Claude Daily Memory", "drive-test", confirm=False)

        self.assertEqual(len(runner.commands), 1)

    def test_confirm_creates_notebook_and_adds_drive_source_once(self) -> None:
        runner = _Runner(
            [
                (0, {"notebooks": []}),
                (0, {"notebook": {"id": "nb-test", "title": "Claude Daily Memory"}}),
                (0, {"sources": []}),
                (
                    0,
                    {
                        "action": "add-drive",
                        "source": {"id": "source-test", "title": "Claude Daily Memory"},
                        "notebook_id": "nb-test",
                    },
                ),
            ]
        )
        client = NotebookLMCLI(Path("/app/venv/bin/notebooklm"), runner=runner)

        binding = client.ensure_memory("Claude Daily Memory", "drive-test", confirm=True)

        self.assertEqual(binding, MemoryBinding("nb-test", "source-test"))
        flattened = [part for command in runner.commands for part in command]
        self.assertEqual(flattened.count("create"), 1)
        self.assertEqual(flattened.count("add-drive"), 1)

    def test_ambiguous_exact_notebook_names_fail_closed(self) -> None:
        runner = _Runner(
            [
                (
                    0,
                    {
                        "notebooks": [
                            {"id": "nb-one", "title": "Claude Daily Memory"},
                            {"id": "nb-two", "title": "Claude Daily Memory"},
                        ]
                    },
                )
            ]
        )
        client = NotebookLMCLI(Path("/app/venv/bin/notebooklm"), runner=runner)

        with self.assertRaisesRegex(NotebookLMError, "multiple notebooks"):
            client.ensure_memory("Claude Daily Memory", "drive-test", confirm=True)

    def test_refresh_targets_configured_notebook_and_source(self) -> None:
        runner = _Runner([(0, {"action": "refresh", "status": "refreshed"})])
        client = NotebookLMCLI(Path("/app/venv/bin/notebooklm"), profile="memory", runner=runner)

        client.refresh_source(MemoryBinding("nb-test", "source-test"))

        self.assertEqual(
            runner.commands[0],
            [
                "/app/venv/bin/notebooklm",
                "--profile",
                "memory",
                "source",
                "refresh",
                "source-test",
                "--notebook",
                "nb-test",
                "--json",
            ],
        )

    def test_registers_same_venv_mcp_without_overwriting_other_servers(self) -> None:
        runner = _Runner([(1, "not found"), (0, "added")])
        client = NotebookLMCLI(Path("/app/venv/bin/notebooklm"), profile="memory", runner=runner)

        client.register_claude_mcp()

        self.assertEqual(runner.commands[0], ["claude", "mcp", "get", "notebooklm"])
        self.assertEqual(
            runner.commands[1],
            [
                "claude",
                "mcp",
                "add",
                "--scope",
                "user",
                "notebooklm",
                "--",
                "/app/venv/bin/notebooklm-mcp",
                "--profile",
                "memory",
                "--transport",
                "stdio",
            ],
        )

    def test_migrates_known_legacy_local_registration_to_same_venv(self) -> None:
        runner = _Runner(
            [
                (0, "Command: /home/test/.local/share/notebooklm-py/venv/bin/notebooklm-mcp"),
                (0, "removed"),
                (0, "added"),
            ]
        )
        client = NotebookLMCLI(Path("/app/venv/bin/notebooklm"), runner=runner)

        client.register_claude_mcp()

        self.assertEqual(
            runner.commands[1],
            ["claude", "mcp", "remove", "notebooklm", "--scope", "user"],
        )
        self.assertEqual(runner.commands[2][0:6], ["claude", "mcp", "add", "--scope", "user", "notebooklm"])

    def test_unknown_existing_mcp_registration_fails_closed(self) -> None:
        runner = _Runner([(0, "Command: /different/custom-mcp")])
        client = NotebookLMCLI(Path("/app/venv/bin/notebooklm"), runner=runner)

        with self.assertRaisesRegex(NotebookLMError, "already exists"):
            client.register_claude_mcp()

        self.assertEqual(len(runner.commands), 1)


if __name__ == "__main__":
    unittest.main()
