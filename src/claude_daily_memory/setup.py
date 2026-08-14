"""Complete setup for Google Drive and the permanent NotebookLM memory."""

from __future__ import annotations

import argparse
import getpass
import json
import os
from pathlib import Path
import subprocess

from .notebooklm_integration import (
    MemoryBinding,
    NotebookLMCLI,
    NotebookLMConfirmationRequired,
)
from .setup_google import setup_google_document
from .gemini_bridge import GEMINI_KEYRING_ACCOUNT, GEMINI_KEYRING_SERVICE


def _atomic_json(path: Path, value: dict[str, str]) -> None:
    path = path.expanduser()
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    path.parent.chmod(0o700)
    temporary = path.with_suffix(path.suffix + ".tmp")
    descriptor = os.open(temporary, os.O_CREAT | os.O_TRUNC | os.O_WRONLY, 0o600)
    try:
        os.write(descriptor, (json.dumps(value, indent=2, sort_keys=True) + "\n").encode())
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    os.replace(temporary, path)
    path.chmod(0o600)


def finish_notebooklm_setup(
    *,
    config_path: Path,
    drive_file_id: str,
    notebook_title: str,
    profile: str,
    notebooklm: NotebookLMCLI,
    confirm: bool,
) -> MemoryBinding:
    notebooklm.check_auth()
    binding = notebooklm.ensure_memory(notebook_title, drive_file_id, confirm=confirm)
    notebooklm.register_claude_mcp()
    notebooklm.refresh_source(binding)
    _atomic_json(
        config_path,
        {
            "drive_file_id": drive_file_id,
            "notebooklm_notebook_id": binding.notebook_id,
            "notebooklm_profile": profile,
            "notebooklm_source_id": binding.source_id,
        },
    )
    return binding


def login_notebooklm(notebooklm: NotebookLMCLI) -> None:
    notebooklm.login()


def _keyring():
    try:
        import keyring
    except ImportError as error:
        raise RuntimeError("System password storage support is not installed") from error
    backend = keyring.get_keyring()
    priority = getattr(backend, "priority", 0)
    if priority is None or priority <= 0 or "fail" in backend.__class__.__name__.lower():
        raise RuntimeError("A working system password storage is required")
    return keyring


def gemini_key_is_ready() -> bool:
    try:
        keyring = _keyring()
    except RuntimeError:
        return False
    return bool(keyring.get_password(GEMINI_KEYRING_SERVICE, GEMINI_KEYRING_ACCOUNT))


def configure_gemini_key() -> None:
    value = getpass.getpass("Gemini API key (hidden input): ").strip()
    if not value:
        raise RuntimeError("Gemini API key cannot be empty")
    keyring = _keyring()
    keyring.set_password(GEMINI_KEYRING_SERVICE, GEMINI_KEYRING_ACCOUNT, value)
    if keyring.get_password(GEMINI_KEYRING_SERVICE, GEMINI_KEYRING_ACCOUNT) != value:
        raise RuntimeError("System password storage did not persist the Gemini API key")


def enable_timer() -> None:
    completed = subprocess.run(
        ["systemctl", "--user", "enable", "--now", "claude-daily-memory.timer"],
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode:
        raise RuntimeError("Could not enable the Claude Daily Memory timer")


def complete_setup(
    *,
    client_path: Path,
    config_path: Path,
    notebook_title: str,
    profile: str,
    notebooklm: NotebookLMCLI,
    confirm: bool,
) -> MemoryBinding:
    if not confirm:
        raise NotebookLMConfirmationRequired(
            "Would authorize Google, open NotebookLM login, connect the permanent memory, register MCP, and enable the timer"
        )
    drive_file_id = setup_google_document(
        client_path,
        notebook_title,
        config_path=config_path,
    )
    _atomic_json(config_path, {"drive_file_id": drive_file_id})
    login_notebooklm(notebooklm)
    binding = finish_notebooklm_setup(
        config_path=config_path,
        drive_file_id=drive_file_id,
        notebook_title=notebook_title,
        profile=profile,
        notebooklm=notebooklm,
        confirm=True,
    )
    if not gemini_key_is_ready():
        configure_gemini_key()
    enable_timer()
    return binding


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Set up Google and the permanent NotebookLM memory in one flow"
    )
    parser.add_argument("--client", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--notebook-title", default="Claude Daily Memory")
    parser.add_argument("--profile", default="default")
    parser.add_argument(
        "--notebooklm",
        type=Path,
        default=Path.home() / ".local/share/claude-daily-memory/venv/bin/notebooklm",
    )
    parser.add_argument("--confirm", action="store_true")
    args = parser.parse_args()
    client = NotebookLMCLI(args.notebooklm, profile=args.profile)
    try:
        complete_setup(
            client_path=args.client,
            config_path=args.config,
            notebook_title=args.notebook_title,
            profile=args.profile,
            notebooklm=client,
            confirm=args.confirm,
        )
    except NotebookLMConfirmationRequired as error:
        print(str(error))
        print("Nothing was changed. Repeat with --confirm after reviewing the action.")
        return 2
    print("Claude Daily Memory and NotebookLM are connected.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
