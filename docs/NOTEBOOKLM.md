# NotebookLM persistent memory and full local MCP

[Русская версия](NOTEBOOKLM-RU.md)

NotebookLM is a core part of Claude Daily Memory. One permanent notebook receives the privacy-filtered daily memory, while the same local MCP lets Claude work with all other notebooks and materials in the account.

## Supported architecture

- One application virtual environment: `~/.local/share/claude-daily-memory/venv`.
- Pinned dependency: `notebooklm-py[browser,mcp]==0.8.0`.
- Local browser authentication under `~/.notebooklm/profiles/<profile>/`.
- Local MCP transport: `stdio` only.
- No HTTP listener, remote MCP, master token, `NOTEBOOKLM_AUTH_JSON`, or cloud cookie transfer.

## Initial setup

Use the unified setup command documented in the main README. It runs local interactive login, checks authentication with a passive live test, creates or reuses the exact memory notebook, connects the Google Doc once without duplicates, registers MCP from the same environment, and refreshes the source.

The default notebook and source title is `Claude Daily Memory`. An exact existing title can be selected with `--notebook-title`; if multiple exact matches exist, setup stops rather than guessing.

## Full account capabilities

The MCP is not restricted to the memory notebook. Depending on upstream and account support, Claude can use notebooks, sources, grounded chat, notes, research, Studio artifacts, downloads, and sharing. Removal and sharing expansion require a preview and separate explicit confirmation.

## Authentication recovery

If the MCP reports an expired or invalid session:

1. rerun the unified setup with the same `--profile` and `--confirm`;
2. complete the local browser login;
3. verify with `claude mcp get notebooklm`.

Existing Google Doc, notebook, and source bindings are reused. The timer should not be considered healthy until the passive auth check and source refresh succeed.

### Chrome-cookie fallback

Use Chrome-cookie import only when ordinary local login cannot be completed. This fallback may expose a broader set of browser cookies to the local importer than the normal isolated login. Close Chrome first if instructed by the upstream CLI, inspect the requested profile, and never copy the resulting state to a server, issue, chat, or repository.

## Logout and revocation

Disable the timer before removing a session:

```bash
systemctl --user disable --now claude-daily-memory.timer
```

Use the local upstream logout/profile command appropriate to the pinned CLI, or remove the selected local profile only after confirming the path. Revoking the Google account session may also invalidate NotebookLM access. A later setup can authenticate again without duplicating the memory notebook or source.

## Implementation disclosure

`notebooklm-py` is an MIT-licensed third-party client that uses internal NotebookLM web RPCs. Google does not publish these as a stable consumer API, so they may change without notice. The dependency is pinned and covered by synthetic command-contract tests, but a future Google change can still require a project update. See [../THIRD_PARTY.md](../THIRD_PARTY.md) and [../SECURITY.md](../SECURITY.md).
