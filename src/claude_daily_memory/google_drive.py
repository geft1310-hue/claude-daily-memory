"""Official Google Drive/Docs export with per-file OAuth and Secret Service storage."""

from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DRIVE_FILE_SCOPE = "https://www.googleapis.com/auth/drive.file"
KEYRING_SERVICE = "claude-daily-memory"
KEYRING_ACCOUNT = "google-drive-refresh-token"
DOC_MIME_TYPE = "application/vnd.google-apps.document"
MARKER_PREFIX = "<!-- claude-daily-memory:"


class GoogleIntegrationError(RuntimeError):
    pass


@dataclass(frozen=True)
class AppendResult:
    file_id: str
    revision_id: str
    changed: bool


def _imports() -> tuple[Any, Any, Any, Any, Any]:
    try:
        import keyring
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
        from googleapiclient.errors import HttpError
    except ImportError as error:
        raise GoogleIntegrationError("Install the optional 'google' dependencies") from error
    backend = keyring.get_keyring()
    priority = getattr(backend, "priority", 0)
    if priority is None or priority <= 0 or "fail" in backend.__class__.__name__.lower():
        raise GoogleIntegrationError("A working system Secret Service is required")
    return keyring, Request, Credentials, build, HttpError


def _read_client_config(path: Path) -> dict[str, Any]:
    try:
        config = json.loads(path.expanduser().read_text(encoding="utf-8"))
        installed = config["installed"]
        client_id = installed["client_id"]
        client_secret = installed["client_secret"]
        token_uri = installed.get("token_uri", "https://oauth2.googleapis.com/token")
    except (OSError, UnicodeError, json.JSONDecodeError, KeyError, TypeError) as error:
        raise GoogleIntegrationError("Invalid Google Desktop OAuth client file") from error
    if token_uri != "https://oauth2.googleapis.com/token":
        raise GoogleIntegrationError("Unexpected OAuth token endpoint")
    return {"client_id": client_id, "client_secret": client_secret, "token_uri": token_uri}


def credentials_from_keyring(client_file: Path) -> Any:
    keyring, Request, Credentials, _, _ = _imports()
    config = _read_client_config(client_file)
    refresh_token = keyring.get_password(KEYRING_SERVICE, KEYRING_ACCOUNT)
    if not refresh_token:
        raise GoogleIntegrationError("Google Drive is not set up")
    credentials = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri=config["token_uri"],
        client_id=config["client_id"],
        client_secret=config["client_secret"],
        scopes=[DRIVE_FILE_SCOPE],
    )
    credentials.refresh(Request())
    if not credentials.valid or not credentials.has_scopes([DRIVE_FILE_SCOPE]):
        raise GoogleIntegrationError("OAuth credential does not have drive.file")
    return credentials


class GoogleDriveMemory:
    def __init__(self, credentials: Any) -> None:
        _, _, _, build, HttpError = _imports()
        self._http_error = HttpError
        self.drive = build("drive", "v3", credentials=credentials, cache_discovery=False)
        self.docs = build("docs", "v1", credentials=credentials, cache_discovery=False)

    def create_document(self, title: str = "Claude Daily Memory") -> str:
        result = self.drive.files().create(
            body={"name": title, "mimeType": DOC_MIME_TYPE}, fields="id"
        ).execute()
        file_id = result.get("id")
        if not isinstance(file_id, str) or not file_id:
            raise GoogleIntegrationError("Google Drive did not return a document id")
        return file_id

    def append_once(self, file_id: str, digest_id: str, text: str, *, retries: int = 2) -> AppendResult:
        marker = f"{MARKER_PREFIX}{digest_id} -->"
        for attempt in range(retries + 1):
            document = self.docs.documents().get(documentId=file_id).execute()
            revision = document.get("revisionId")
            if not isinstance(revision, str) or not revision:
                raise GoogleIntegrationError("Google Docs did not return a revision id")
            current_text = self._document_text(document)
            if marker in current_text:
                return AppendResult(file_id, revision, False)
            body = {
                "requests": [
                    {
                        "insertText": {
                            "endOfSegmentLocation": {},
                            "text": f"\n{marker}\n{text.rstrip()}\n",
                        }
                    }
                ],
                "writeControl": {"requiredRevisionId": revision},
            }
            try:
                response = self.docs.documents().batchUpdate(documentId=file_id, body=body).execute()
                updated = response.get("writeControl", {}).get("requiredRevisionId")
                return AppendResult(file_id, str(updated or revision), True)
            except self._http_error as error:
                status = getattr(getattr(error, "resp", None), "status", None)
                if status != 400 or attempt >= retries:
                    raise GoogleIntegrationError("Google Docs update failed") from error
        raise GoogleIntegrationError("Google Docs update conflict")

    @staticmethod
    def _document_text(document: dict[str, Any]) -> str:
        fragments: list[str] = []
        for block in document.get("body", {}).get("content", []):
            paragraph = block.get("paragraph", {})
            for element in paragraph.get("elements", []):
                run = element.get("textRun", {})
                content = run.get("content")
                if isinstance(content, str):
                    fragments.append(content)
        return "".join(fragments)


def digest_id(key: bytes, day: str, text: str) -> str:
    value = f"{day}\0{text}".encode("utf-8")
    return hmac.new(key, value, hashlib.sha256).hexdigest()[:32]
