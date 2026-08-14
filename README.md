# Claude Daily Memory

[Русская версия](README-RU.md) · [Website](https://geft1310-hue.github.io/claude-daily-memory/) · [Security](SECURITY.md)

Claude Daily Memory makes **NotebookLM the persistent memory for Claude Code**. It collects selected useful outcomes from your projects, removes unsafe material, appends one daily entry to a growing Google Doc, and automatically refreshes that document in one permanent NotebookLM notebook.

The same installation registers the complete local NotebookLM MCP in Claude Code. Claude can therefore work with **all notebooks in your NotebookLM account**—not only the permanent memory notebook—including their sources, chat, notes, research, Studio artifacts, downloads, and sharing controls.

## One product, one setup

```text
Claude Code work across projects
              ↓
selected, privacy-filtered daily memory
              ↓
one growing Google Doc
              ↓
one permanent NotebookLM memory notebook
(the Drive source is connected and refreshed automatically)
              ↓
Claude can also use every other NotebookLM notebook and artifact
through the same local MCP installation
```

There is no second NotebookLM installer or separate product mode. `./install.sh` creates one virtual environment at `~/.local/share/claude-daily-memory/venv`. It contains Claude Daily Memory, Google Drive/Docs support, Gemini, the pinned NotebookLM client, browser support, and the MCP server.

## What v0.2.0 provides

- One daily memory assembled across multiple Claude Code projects.
- A local Markdown archive before any cloud upload.
- Fail-closed secret and personal-data scanning for every selected item and the final digest.
- Idempotent append to one Google Doc through the official Drive and Docs APIs.
- Automatic refresh of that Drive source in one permanent NotebookLM notebook.
- Full local NotebookLM MCP access across all notebooks, sources, chat, notes, research, Studio artifacts, downloads, and sharing.
- Gemini Developer API access with the API key stored in the operating-system keyring.
- One local installation, one setup command, and one systemd user timer.
- No raw Claude transcript collection, remote NotebookLM server, master token, or plaintext cloud credential file.

## Quick start

### 1. Install

Requirements: Linux, Python 3.11+, Claude Code, Git, systemd user services, and an operating-system Secret Service/keyring.

```bash
git clone https://github.com/geft1310-hue/claude-daily-memory.git
cd claude-daily-memory
./install.sh
```

The installer deliberately leaves the daily timer disabled.

### 2. Prepare Google OAuth once

Create a Google Desktop OAuth client with the Google Drive API and Google Docs API enabled. Save the downloaded JSON as `~/.config/claude-daily-memory/google-client.json` and keep it private (`chmod 600`). Detailed instructions: [docs/GOOGLE.md](docs/GOOGLE.md).

You also need a Gemini Developer API key. Do not put it in a shell command or configuration file: the setup command requests it with hidden input and stores it in the system keyring.

### 3. Preview, then run the unified setup

First review what the command will do:

```bash
~/.local/share/claude-daily-memory/venv/bin/claude-daily-memory-setup \
  --client ~/.config/claude-daily-memory/google-client.json \
  --config ~/.config/claude-daily-memory/config.json
```

Nothing is changed without `--confirm`. When ready, run:

```bash
~/.local/share/claude-daily-memory/venv/bin/claude-daily-memory-setup \
  --client ~/.config/claude-daily-memory/google-client.json \
  --config ~/.config/claude-daily-memory/config.json \
  --confirm
```

The setup performs one complete flow:

1. authorizes the narrow Google `drive.file` scope;
2. creates or reuses the `Claude Daily Memory` Google Doc;
3. opens a local interactive NotebookLM login;
4. verifies the session with a real passive authentication check;
5. creates or reuses the permanent `Claude Daily Memory` notebook and its Drive source without duplicates;
6. saves only required document/notebook/source identifiers in a private `0600` config;
7. registers `notebooklm-mcp` in Claude Code from the same environment using local `stdio` and the selected profile;
8. asks for a missing Gemini key through hidden input and stores it in the system keyring;
9. refreshes the memory source and enables the timer only after every preceding step succeeds.

Use `--notebook-title "Another exact title"` to reuse an existing notebook with that exact title, and `--profile NAME` to select a NotebookLM profile.

### 4. Verify locally

```bash
systemctl --user status claude-daily-memory.timer
claude mcp get notebooklm
```

Build a local memory without calling Drive or NotebookLM:

```bash
~/.local/share/claude-daily-memory/venv/bin/claude-daily-memory build \
  --workspace "$HOME/tools/trailmark/workspace" \
  --projects-root "$HOME/projects" \
  --hmac-key "$HOME/.config/claude-daily-memory/hmac.key"
```

Review the generated Markdown before relying on the scheduled job.

## What Claude can do with NotebookLM

The registered MCP exposes the capabilities of pinned `notebooklm-py` rather than a reduced one-document wrapper. Subject to features available in your Google account, Claude can:

- list, inspect, create, rename, and describe notebooks;
- list, read, add, refresh, and remove sources;
- ask grounded questions and configure chat;
- create and work with notes;
- start and inspect research;
- generate, monitor, rename, and download Studio artifacts;
- inspect and manage sharing.

Deletion and sharing expansion are consequential actions. They must be previewed and require a separate explicit confirmation; setup never performs them.

## Daily behavior and failure recovery

The daily job sanitizes the inputs and final digest, writes local Markdown, appends the day to Google Docs once, refreshes the configured NotebookLM source, and advances `last_successful_day` only after the complete chain succeeds.

If Drive fails, NotebookLM is not called. If Drive succeeds but NotebookLM refresh fails, the day remains pending. The next run safely retries: the Google marker prevents a duplicate daily entry, while the NotebookLM refresh runs again.

## Privacy and security boundaries

The automatic pipeline does **not** read Claude Code transcript JSONL, full prompts, full responses, raw commands, tool inputs/outputs, Gmail, arbitrary project files, or NotebookLM answers. Audit records contain only event codes, counts, and HMAC pseudonyms—not notebook/source identifiers or document contents.

Google refresh tokens and the Gemini API key live in the OS keyring. NotebookLM browser-session state stays locally under `~/.notebooklm/` and must never be committed or copied to a remote service. The supported MCP transport is local `stdio`; the project does not configure an HTTP listener, remote MCP, cloud cookie transfer, or master-token flow.

Consumer NotebookLM automation is provided by the pinned third-party MIT package `notebooklm-py[browser,mcp]==0.8.0`. It uses Google’s internal NotebookLM web RPCs, so a Google change can require a package update or a new local login. This is an implementation disclosure, not a separate product mode. See [SECURITY.md](SECURITY.md) and [THIRD_PARTY.md](THIRD_PARTY.md).

## NotebookLM session recovery

If authentication expires, rerun the unified setup with `--confirm`; the existing Google Doc, notebook, and source are reused. The normal path is local interactive `notebooklm login`. Chrome-cookie import may be used only as a recovery fallback when normal login fails; it can expose a broader browser-cookie surface and must remain local. See [docs/NOTEBOOKLM.md](docs/NOTEBOOKLM.md).

## Development

```bash
python -m unittest discover -s tests
python -m build
```

Tests are synthetic and require no real Google or NotebookLM credentials. Contributions must preserve test-first development, fail-closed behavior, bilingual public documentation, and credential hygiene. See [CONTRIBUTING.md](CONTRIBUTING.md).

## Project status

Version `0.2.0` targets Linux and a systemd user timer. macOS and Windows schedulers are not implemented yet. The project is not affiliated with or endorsed by Anthropic or Google.

Apache-2.0. See [LICENSE](LICENSE).
