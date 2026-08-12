"""One-time official Google OAuth setup for the background Drive writer."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .google_drive import (
    DRIVE_FILE_SCOPE,
    KEYRING_ACCOUNT,
    KEYRING_SERVICE,
    GoogleDriveMemory,
    GoogleIntegrationError,
    _imports,
    _read_client_config,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Set up the Claude Daily Memory Google Doc")
    parser.add_argument("--client", type=Path, required=True, help="Google Desktop OAuth client JSON")
    parser.add_argument("--config", type=Path, required=True, help="Non-secret output configuration")
    args = parser.parse_args()

    keyring, _, _, _, _ = _imports()
    _read_client_config(args.client)
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError as error:
        raise GoogleIntegrationError("Install the optional 'google' dependencies") from error

    flow = InstalledAppFlow.from_client_secrets_file(str(args.client.expanduser()), [DRIVE_FILE_SCOPE])
    credentials = flow.run_local_server(port=0, open_browser=True, authorization_prompt_message="")
    if not credentials.refresh_token:
        raise GoogleIntegrationError("Google did not return a refresh token; revoke the grant and retry")
    keyring.set_password(KEYRING_SERVICE, KEYRING_ACCOUNT, credentials.refresh_token)
    if keyring.get_password(KEYRING_SERVICE, KEYRING_ACCOUNT) != credentials.refresh_token:
        raise GoogleIntegrationError("Secret Service did not persist the credential")

    file_id = GoogleDriveMemory(credentials).create_document()
    args.config.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    args.config.parent.chmod(0o700)
    args.config.write_text(json.dumps({"drive_file_id": file_id}, indent=2) + "\n", encoding="utf-8")
    args.config.chmod(0o600)
    print("Google Doc created successfully. Add it once as a Drive source in NotebookLM.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
