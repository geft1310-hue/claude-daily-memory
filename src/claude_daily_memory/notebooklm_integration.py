"""Local NotebookLM CLI adapter for the permanent memory notebook."""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


class NotebookLMError(RuntimeError):
    pass


class NotebookLMConfirmationRequired(NotebookLMError):
    pass


@dataclass(frozen=True)
class MemoryBinding:
    notebook_id: str
    source_id: str


Runner = Callable[[list[str]], subprocess.CompletedProcess[str]]


def _run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, text=True, capture_output=True, check=False)


class NotebookLMCLI:
    def __init__(
        self,
        executable: Path,
        *,
        profile: str = "default",
        runner: Runner = _run,
        claude_executable: str = "claude",
    ) -> None:
        if not profile or any(character.isspace() for character in profile):
            raise NotebookLMError("Invalid NotebookLM profile")
        self.executable = executable.expanduser()
        self.profile = profile
        self.runner = runner
        self.claude_executable = claude_executable

    def _command(self, *arguments: str) -> list[str]:
        return [str(self.executable), "--profile", self.profile, *arguments]

    def _json(self, *arguments: str) -> Any:
        completed = self.runner(self._command(*arguments))
        if completed.returncode:
            raise NotebookLMError("NotebookLM command failed")
        try:
            return json.loads(completed.stdout)
        except (json.JSONDecodeError, TypeError) as error:
            raise NotebookLMError("NotebookLM returned invalid JSON") from error

    @staticmethod
    def _items(payload: Any, key: str) -> list[dict[str, Any]]:
        if not isinstance(payload, dict) or not isinstance(payload.get(key), list):
            raise NotebookLMError("NotebookLM response has an unexpected shape")
        items = payload[key]
        if not all(isinstance(item, dict) for item in items):
            raise NotebookLMError("NotebookLM response has an unexpected shape")
        return items

    def login(self) -> None:
        completed = self.runner(self._command("login"))
        if completed.returncode:
            raise NotebookLMError("NotebookLM login did not complete")

    def check_auth(self) -> None:
        payload = self._json("auth", "check", "--test", "--passive", "--json")
        if isinstance(payload, dict) and payload.get("status") in {"error", "failed"}:
            raise NotebookLMError("NotebookLM authentication is not ready")

    def ensure_memory(self, title: str, drive_file_id: str, *, confirm: bool) -> MemoryBinding:
        notebooks = self._items(self._json("list", "--json"), "notebooks")
        matches = [item for item in notebooks if item.get("title") == title]
        if len(matches) > 1:
            raise NotebookLMError("Found multiple notebooks with the exact memory title")
        if not matches:
            if not confirm:
                raise NotebookLMConfirmationRequired(
                    f"Would create notebook '{title}' and connect the daily memory source"
                )
            created = self._json("create", title, "--json")
            notebook = created.get("notebook") if isinstance(created, dict) else None
            notebook_id = notebook.get("id") if isinstance(notebook, dict) else None
        else:
            notebook_id = matches[0].get("id")
        if not isinstance(notebook_id, str) or not notebook_id:
            raise NotebookLMError("NotebookLM did not return a notebook id")

        sources = self._items(
            self._json("source", "list", "--notebook", notebook_id, "--json"),
            "sources",
        )
        source_matches = [
            item for item in sources if self._source_matches_drive_file(item, drive_file_id)
        ]
        if len(source_matches) > 1:
            raise NotebookLMError("Found multiple memory sources for the Google document")
        if not source_matches:
            if not confirm:
                raise NotebookLMConfirmationRequired(
                    f"Would connect the Google document to notebook '{title}'"
                )
            added = self._json(
                "source",
                "add-drive",
                drive_file_id,
                title,
                "--notebook",
                notebook_id,
                "--json",
            )
            source = added.get("source") if isinstance(added, dict) else None
            source_id = source.get("id") if isinstance(source, dict) else None
        else:
            source_id = source_matches[0].get("id")
        if not isinstance(source_id, str) or not source_id:
            raise NotebookLMError("NotebookLM did not return a source id")
        return MemoryBinding(notebook_id, source_id)

    @staticmethod
    def _source_matches_drive_file(source: dict[str, Any], drive_file_id: str) -> bool:
        if source.get("drive_file_id") == drive_file_id:
            return True
        url = source.get("url")
        return isinstance(url, str) and f"/d/{drive_file_id}/" in url

    def refresh_source(self, binding: MemoryBinding) -> None:
        payload = self._json(
            "source",
            "refresh",
            binding.source_id,
            "--notebook",
            binding.notebook_id,
            "--json",
        )
        if not isinstance(payload, dict) or payload.get("status") != "refreshed":
            raise NotebookLMError("NotebookLM did not confirm source refresh")

    def register_claude_mcp(self) -> None:
        mcp_executable = self.executable.with_name("notebooklm-mcp")
        expected = [
            self.claude_executable,
            "mcp",
            "add",
            "--scope",
            "user",
            "notebooklm",
            "--",
            str(mcp_executable),
            "--profile",
            self.profile,
            "--transport",
            "stdio",
        ]
        current = self.runner([self.claude_executable, "mcp", "get", "notebooklm"])
        if current.returncode == 0:
            if str(mcp_executable) in current.stdout and f"--profile {self.profile}" in current.stdout:
                return
            if "/.local/share/notebooklm-py/venv/bin/notebooklm-mcp" in current.stdout:
                removed = self.runner(
                    [
                        self.claude_executable,
                        "mcp",
                        "remove",
                        "notebooklm",
                        "--scope",
                        "user",
                    ]
                )
                if removed.returncode:
                    raise NotebookLMError("Could not migrate the previous NotebookLM MCP")
            else:
                raise NotebookLMError("NotebookLM MCP already exists with a different command")
        added = self.runner(expected)
        if added.returncode:
            raise NotebookLMError("Could not register NotebookLM MCP in Claude Code")
