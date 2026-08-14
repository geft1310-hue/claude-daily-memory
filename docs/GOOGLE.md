# Google and Gemini setup

[Русская версия](GOOGLE-RU.md)

Claude Daily Memory uses one unified setup command. Google Drive/Docs provide the growing source document, Gemini is installed in the same application environment, and NotebookLM connection is completed in the same flow.

## 1. Create a Google Cloud project

1. Open <https://console.cloud.google.com/>.
2. Create or select a project.
3. Enable **Google Drive API** and **Google Docs API**.
4. Configure the OAuth consent screen. For personal use, testing mode with your account as a test user is sufficient.
5. Create an OAuth client of type **Desktop app** and download its JSON file.

## 2. Store the OAuth client privately

```bash
mkdir -p ~/.config/claude-daily-memory
mv ~/Downloads/client_secret_*.json ~/.config/claude-daily-memory/google-client.json
chmod 600 ~/.config/claude-daily-memory/google-client.json
```

Never commit this file.

## 3. Prepare a Gemini Developer API key

Create a Gemini API key in Google AI Studio. Do not paste it into a command, `.env`, issue, or repository file. The unified setup requests it with hidden input and saves it in the operating-system keyring under service `claude-daily-memory` and account `gemini-api-key`.

Vertex AI is not the default. It is used by the separate explicit-text bridge only when `--project` is deliberately supplied.

## 4. Run the unified setup

Preview first (no changes):

```bash
~/.local/share/claude-daily-memory/venv/bin/claude-daily-memory-setup \
  --client ~/.config/claude-daily-memory/google-client.json \
  --config ~/.config/claude-daily-memory/config.json
```

Then confirm:

```bash
~/.local/share/claude-daily-memory/venv/bin/claude-daily-memory-setup \
  --client ~/.config/claude-daily-memory/google-client.json \
  --config ~/.config/claude-daily-memory/config.json \
  --confirm
```

The browser requests only `drive.file`. The refresh token is stored in the OS keyring. Setup creates or reuses the Google Doc, completes local NotebookLM login and binding, registers local stdio MCP, requests a missing Gemini key, refreshes the NotebookLM source, and only then enables the timer.

The private config contains identifiers required for reliable retries; it contains no OAuth refresh token, Gemini key, NotebookLM cookies, or master token.

## 5. Verify

```bash
systemctl --user status claude-daily-memory.timer
claude mcp get notebooklm
```

See [NOTEBOOKLM.md](NOTEBOOKLM.md) for login recovery and MCP details.

## Revoke or disable

```bash
systemctl --user disable --now claude-daily-memory.timer
```

Revoke the application in your Google Account security settings. Remove the Gemini key from your system password manager if desired. NotebookLM logout/session removal must remain local; never upload its browser state for support.
