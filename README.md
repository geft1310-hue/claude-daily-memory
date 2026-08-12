# Claude Daily Memory

**Privacy-first, local-first long-term memory for Claude Code.** Collect safe metadata from every terminal and project, build one daily digest, scan it for secrets, and optionally append it to a Google Doc that can be used as a NotebookLM Drive source.

> Alpha software. Start in local `--dry-run` mode and review the output before enabling Google export.

## Why this project exists

Claude Code sessions are useful but fragmented: several terminals may be open, projects are independent, and raw transcripts can contain passwords, tokens, personal data, tool inputs, or private files. Copying those transcripts into a cloud notebook is unsafe.

Claude Daily Memory takes a different approach:

- records only event type, time, keyed project/session aliases, and allowlisted tool names;
- never reads Claude transcript JSONL files;
- exports only curated Markdown artifacts you intentionally saved;
- scans every artifact and the final digest before any network call;
- fails closed: uncertainty or scanner failure stops the upload;
- keeps Google Drive OAuth separate from Gmail, Gemini, and Claude credentials;
- uses the narrow `drive.file` scope for one app-created Google Doc;
- supports a hardened daily `systemd --user` timer;
- provides deterministic, reversible Gmail cleanup rule logic without permanently deleting mail.

## Data flow

```text
Claude Code terminals
        │ safe lifecycle metadata only
        ▼
local events.jsonl ─┐
                    ├─> deterministic daily digest ─> secret scanner ─> Google Doc
curated Markdown ───┘                                          │
                                                               └─> NotebookLM Drive source
```

Gmail and Gemini are deliberately **outside** this automatic path.

## Quick start

Requirements: Linux, Python 3.11+, and `systemd --user` for scheduling.

```bash
git clone https://github.com/geft1310-hue/claude-daily-memory.git
cd claude-daily-memory
./install.sh
```

The installer creates a private virtual environment, a local HMAC key, and the user timer. Google upload remains off until you explicitly complete OAuth setup.

Build a local digest without networking:

```bash
~/.local/share/claude-daily-memory/venv/bin/claude-daily-memory build \
  --workspace "$HOME/tools/trailmark/workspace" \
  --projects-root "$HOME/projects" \
  --hmac-key "$HOME/.config/claude-daily-memory/hmac.key"
```

## Google Drive and NotebookLM

1. Create a Google Cloud **Desktop app** OAuth client and enable Drive and Docs APIs.
2. Keep the downloaded client JSON outside the repository at:
   `~/.config/claude-daily-memory/google-client.json`.
3. Run the one-time setup command from the installed environment.
4. Sign in to Google in the browser. The app requests only `drive.file`.
5. The setup creates `Claude Daily Memory` in Drive and keeps the refresh token in the operating-system Secret Service.
6. In NotebookLM, add that Google Doc once as a Drive source.

No browser cookies, Playwright automation, consumer NotebookLM private API, or plaintext refresh-token file is used. Consumer NotebookLM may require a manual source refresh; this project does not bypass that limitation.

## Gmail cleanup rules

Gmail is a separate connector. Exact matches may be moved to Trash without asking about each message. Partial matches remain untouched, exclusions win, and Trash is never emptied automatically. See [docs/GMAIL.md](docs/GMAIL.md).

## Gemini bridge

The optional bridge uses Google's official Gen AI SDK with Google Cloud Application Default Credentials. It accepts only text supplied with `--text`; it cannot discover or read Gmail, Drive, project files, Trailmark, or the clipboard. It displays the payload first and sends only when `--confirm` is present.

## Threat model

Protected against:

- accidental transcript export;
- common API keys, tokens, cookies, private keys, `.env` assignments, JWTs, and high-entropy secrets;
- concurrent hook writes and duplicate daily jobs;
- malformed inputs and unavailable scanners;
- accidental permanent email deletion;
- secrets entering the public Git repository.

Not protected against:

- a malicious local user with access to your account;
- an already-compromised operating system or Secret Service;
- unknown secret formats that resemble normal prose;
- Google, Anthropic, or NotebookLM service-side retention policies.

Always review your local dry run before first upload. No secret scanner can promise perfect detection.

## Testing

```bash
PYTHONPATH=src python3 -m unittest discover -s tests
```

The test corpus covers concurrency, project boundaries, transcript-field rejection, common secret formats, personal-data redaction, deterministic output, and exact Gmail cleanup rules.

## Privacy guarantees

Claude Daily Memory does not require telemetry and includes none. It does not ship analytics, tracking pixels, external fonts, or an update daemon. Audit logs contain counts, rule names, status codes, HMAC identifiers, and Google revision IDs—not message bodies or matched secrets.

## Project status and roadmap

- [x] privacy-preserving Claude Code metadata hooks
- [x] local deterministic digest builder
- [x] fail-closed secret sanitizer
- [x] official Google Drive/Docs writer
- [x] hardened systemd timer templates
- [x] reversible Gmail cleanup rule engine
- [x] explicit-text Gemini bridge
- [ ] guided cross-platform installer
- [ ] macOS launchd support
- [ ] pluggable curated-memory adapters
- [ ] independent security audit

Contributions, threat-model reviews, false-positive test cases, and documentation improvements are welcome.

## Security

Do not open a public issue containing a secret or private digest. Follow [SECURITY.md](SECURITY.md) for private vulnerability reporting.

## License

Apache License 2.0. This project is not affiliated with or endorsed by Anthropic, Google, Gmail, Gemini, Google Drive, or NotebookLM. Those names are trademarks of their respective owners.
