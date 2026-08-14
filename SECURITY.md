# Security Policy

## Supported versions

Security fixes are applied to the latest release and current `main` branch.

## Reporting a vulnerability

Do not include secrets, private email, OAuth credentials, NotebookLM browser state, real notebook/source identifiers, transcripts, or personal digests in a public issue.

Use GitHub **Private vulnerability reporting**. Include the affected version, a minimal synthetic reproduction, expected and observed behavior, impact, and a suggested mitigation if known. If private reporting is unavailable, open a content-free public request for a private channel.

## Security boundaries

The daily pipeline:

- never reads raw Claude Code transcript JSONL;
- does not automatically collect full prompts/responses, raw commands, tool data, Gmail, arbitrary project files, or NotebookLM answers;
- scans each selected artifact and the final digest before networking;
- fails closed on malformed input, scanner uncertainty, missing credentials, or cloud failure;
- uses official Google Drive/Docs APIs with `drive.file`;
- advances daily state only after Drive append and NotebookLM source refresh both succeed;
- keeps audit data content-free and excludes notebook/source identifiers.

Google refresh tokens and the Gemini API key are stored in the operating-system keyring. The private config is mode `0600` and stores only identifiers needed for idempotent operation.

## NotebookLM threat model

Consumer NotebookLM integration is provided by pinned `notebooklm-py[browser,mcp]==0.8.0`, an MIT-licensed third-party package that uses internal Google web RPCs. These interfaces can change without notice. The project supports local interactive browser authentication and local `stdio` MCP only.

NotebookLM session state under `~/.notebooklm/` is credential material. Never commit or share `storage_state.json`, browser profiles, cookie exports, or `master_token.json`. The supported setup does not use a remote/HTTP server, `NOTEBOOKLM_AUTH_JSON`, a master-token flow, or cloud cookie transfer.

Chrome-cookie import is documented only as a local recovery fallback because it may expose a broader cookie surface. Normal isolated login is preferred.

Notebook/source deletion and any expansion of sharing require a preview and separate explicit confirmation. Initial setup does not delete user data or modify other notebooks.

No scanner or unofficial web-client compatibility layer can guarantee perfect protection or availability. Review local output before first upload, keep dependencies current through reviewed releases, and revoke access promptly if credentials may have been exposed.
