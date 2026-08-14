"""Google OAuth and document setup for Claude Daily Memory."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .google_drive import (
    DRIVE_FILE_SCOPE,
    KEYRING_ACCOUNT,
    KEYRING_SERVICE,
    GoogleDriveMemory,
    GoogleIntegrationError,
    _imports,
    _read_client_config,
)


def authorize_google(client_path: Path) -> Any:
    keyring, _, _, _, _ = _imports()
    _read_client_config(client_path)
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError as error:
        raise GoogleIntegrationError("Install the optional 'google' dependencies") from error

    flow = InstalledAppFlow.from_client_secrets_file(
        str(client_path.expanduser()), [DRIVE_FILE_SCOPE]
    )
    credentials = flow.run_local_server(
        port=0,
        open_browser=True,
        authorization_prompt_message="",
    )
    if not credentials.refresh_token:
        raise GoogleIntegrationError(
            "Google did not return a refresh token; revoke the grant and retry"
        )
    keyring.set_password(KEYRING_SERVICE, KEYRING_ACCOUNT, credentials.refresh_token)
    if keyring.get_password(KEYRING_SERVICE, KEYRING_ACCOUNT) != credentials.refresh_token:
        raise GoogleIntegrationError("Secret Service did not persist the credential")
    return credentials


def _configured_file_id(config_path: Path | None) -> str | None:
    if config_path is None or not config_path.expanduser().is_file():
        return None
    try:
        config = json.loads(config_path.expanduser().read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    file_id = config.get("drive_file_id") if isinstance(config, dict) else None
    return file_id if isinstance(file_id, str) and file_id else None


def setup_google_document(
    client_path: Path,
    title: str = "Claude Daily Memory",
    *,
    config_path: Path | None = None,
) -> str:
    existing = _configured_file_id(config_path)
    if existing:
        return existing
    credentials = authorize_google(client_path)
    return GoogleDriveMemory(credentials).create_document(title)


def main() -> int:
    parser = argparse.ArgumentParser(description="Set up the Claude Daily Memory Google Doc")
    parser.add_argument("--client", type=Path, required=True, help="Google Desktop OAuth client JSON")
    parser.add_argument("--config", type=Path, required=True, help="Non-secret output configuration")
    args = parser.parse_args()

    file_id = setup_google_document(args.client, config_path=args.config)
    args.config.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    args.config.parent.chmod(0o700)
    args.config.write_text(json.dumps({"drive_file_id": file_id}, indent=2) + "\n", encoding="utf-8")
    args.config.chmod(0o600)
    print("Google Doc is ready. Complete NotebookLM setup before enabling the timer.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
