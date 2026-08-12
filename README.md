# Claude Daily Memory

**English** · [Русский](README-RU.md)

## Turn NotebookLM into long-term memory for Claude Code

Claude Code can do valuable work across dozens of sessions, terminals, and repositories—but the useful context is scattered. Yesterday's decision lives in one terminal. A working plan is buried in another project. The reason behind a technical choice disappears when the session ends.

**Claude Daily Memory turns that fragmented work into a growing NotebookLM knowledge base.** It gathers the useful results of your Claude Code work across projects, creates a clean daily memory, and keeps a Google Doc ready to use as a NotebookLM source.

Instead of starting every session from zero, you get a second brain that grows with your work.

> **Claude Code does the work. Claude Daily Memory preserves the useful results. NotebookLM helps you understand and reuse them.**

> Alpha software. Start with a local dry run and review the result before enabling Google export.

## The problem

AI-assisted work creates a new kind of information loss:

- important decisions are spread across many Claude Code sessions;
- several terminals may work on different projects at the same time;
- plans, findings, trade-offs, and unfinished threads are difficult to recover later;
- raw transcripts are noisy and may contain secrets or personal data;
- manually writing a summary after every session is easy to forget;
- NotebookLM is powerful only when its sources stay useful and up to date.

The result is repeated explanations, duplicated research, forgotten decisions, and an AI assistant that knows less about your work than it should.

## The outcome

Claude Daily Memory creates a continuous knowledge loop:

```text
Work in Claude Code across terminals and projects
                    ↓
Useful plans, decisions, notes, reports, and activity are collected
                    ↓
One clean, structured daily memory is produced
                    ↓
Secrets and unnecessary personal data are blocked before upload
                    ↓
A Google Doc becomes a growing source for NotebookLM
                    ↓
NotebookLM becomes your searchable, reusable project memory
```

Once the memory document is connected to NotebookLM, you can use NotebookLM's own capabilities on the accumulated knowledge, for example:

- ask what was decided about a feature and why;
- compare approaches used across different projects;
- recover unfinished work and open questions;
- prepare a briefing before returning to an old project;
- find recurring problems, assumptions, and dependencies;
- generate summaries, study guides, FAQs, timelines, reports, mind maps, audio overviews, or other artifacts supported by your NotebookLM account;
- build a coherent picture of your work instead of searching through disconnected chats.

Claude Daily Memory is the **memory ingestion and maintenance layer**. NotebookLM remains the place where you search, analyze, connect, and transform that memory.

## Why use it

### One memory across all Claude Code work

Multiple terminals and projects feed one daily knowledge stream. You no longer need to remember which session contained the important answer.

### NotebookLM becomes more useful over time

The source grows from actual work: selected plans, decisions, notes, reports, and high-level activity. The more consistently you use it, the more useful cross-project questions become.

### No end-of-session ritual

You do not have to copy and paste every conversation or remember to write a manual summary each evening. A daily job prepares the memory automatically.

### Signal instead of transcript noise

The system preserves useful outcomes—not every greeting, failed command, intermediate tool result, or repeated explanation.

### Safe enough for real project work

Raw Claude transcripts are never read. Each selected artifact and the final daily digest are checked before any network request. Common keys, tokens, cookies, private keys, `.env` assignments, suspicious secret-like strings, and unnecessary personal details are blocked or redacted.

### Local-first and inspectable

A readable Markdown digest is produced locally first. Google export is optional. There is no telemetry, hidden analytics, or browser-cookie automation.

### Built for concurrency

File locks, keyed project/session aliases, deterministic output, and idempotent Google Doc markers let multiple Claude Code terminals contribute without corrupting the memory or creating duplicate daily entries.

## What gets remembered

Claude Daily Memory is intentionally selective.

**Included:**

- curated plans;
- decisions and their reasoning;
- useful notes;
- reports and verification results;
- safe high-level activity counts;
- project grouping and dates.

**Never used as an automatic source:**

- raw Claude Code transcripts;
- full prompts and full assistant responses;
- shell commands and tool input/output;
- Gmail messages;
- arbitrary files from your projects;
- credentials, cookies, tokens, or `.env` contents.

This distinction is the core of the product: **remember the work, not the sensitive exhaust around the work.**

## How NotebookLM fits

Claude Daily Memory creates and maintains a Google Doc called `Claude Daily Memory`. Add that document once to NotebookLM as a normal Google Drive source.

From then on:

1. Claude Code sessions create useful, curated outcomes.
2. The daily job combines outcomes from all participating projects.
3. The result is sanitized locally.
4. The Google Doc receives an idempotent daily entry.
5. NotebookLM uses the document as a source after its normal source synchronization or refresh.

No unofficial consumer NotebookLM API is used. No Google browser cookies are copied. No Playwright login robot is required. Consumer NotebookLM may require a manual source refresh depending on the account and current product behavior; this project does not bypass that limitation.

## Quick start

Requirements: Linux, Python 3.11+, and `systemd --user` for scheduling.

```bash
git clone https://github.com/geft1310-hue/claude-daily-memory.git
cd claude-daily-memory
./install.sh
```

The installer creates a private Python environment, local state directories, a keyed identity file, and a staged daily timer. The timer stays off until Google OAuth setup is complete.

Build and inspect a local memory without sending anything to Google:

```bash
~/.local/share/claude-daily-memory/venv/bin/claude-daily-memory build \
  --workspace "$HOME/tools/trailmark/workspace" \
  --projects-root "$HOME/projects" \
  --hmac-key "$HOME/.config/claude-daily-memory/hmac.key"
```

## Connect Google Drive and NotebookLM

1. Create a Google Cloud OAuth client of type **Desktop app**.
2. Enable the Google Drive and Google Docs APIs.
3. Keep the downloaded client file outside the repository at:
   `~/.config/claude-daily-memory/google-client.json`.
4. Run the one-time setup command from the installed environment.
5. Sign in in the browser. The background writer requests only `drive.file`.
6. The setup creates the `Claude Daily Memory` Google Doc.
7. Add that Google Doc once to NotebookLM as a Drive source.
8. Enable the timer after the first local and Google test succeeds.

The refresh token is stored in the operating-system Secret Service, not in the repository, `.env`, process arguments, or a plaintext token file.

## Designed to fail safely

The export pipeline is fail-closed:

- a selected artifact is checked before inclusion;
- the complete daily memory is checked again;
- malformed input, unreadable state, scanner failure, missing Secret Service, OAuth failure, and ambiguous secret-like content stop the upload;
- Google state advances only after a confirmed document update;
- audit logs contain counts and rule names—not the secret that triggered a rule.

No scanner can guarantee perfect detection. Review the local dry run before the first cloud upload and use curated artifacts rather than unrestricted text dumps.

## More than memory capture

The repository also contains optional, deliberately separate tools:

- **reversible Gmail cleanup rules** — exact matches can move to Trash without asking about every message; uncertain matches stay untouched and Trash is never emptied automatically;
- **explicit-text Gemini bridge** — only text shown on the command line can be sent, and the bridge cannot discover Gmail, Drive, project files, local memory, or clipboard content.

These are outside the automatic memory pipeline. Gmail content and Gemini responses are not silently added to NotebookLM memory.

## Architecture

```text
Claude Code lifecycle hooks          Curated Trailmark artifacts
(time/event/project/tool only)        (plan/decision/note/report)
                 \                      /
                  \                    /
                   └─ local daily builder
                              ↓
                    per-artifact sanitizer
                              ↓
                    final digest sanitizer
                              ↓
                  local Markdown + safe audit
                              ↓
             official Google Drive / Docs APIs
                     drive.file OAuth scope
                              ↓
                Google Doc → NotebookLM source
```

## Testing

```bash
PYTHONPATH=src python3 -m unittest discover -s tests
```

The test suite covers:

- concurrent terminal writes;
- project boundaries and project identity merging;
- transcript-field rejection;
- common secret formats and high-entropy strings;
- personal-data redaction without damaging ISO dates;
- deterministic daily output;
- Google document idempotency helpers;
- exact and uncertain Gmail cleanup matches;
- systemd timer and sandbox requirements.

## Project status

Available in the current alpha:

- [x] multi-terminal Claude Code metadata aggregation
- [x] curated cross-project daily memory
- [x] fail-closed secret and personal-data filtering
- [x] local Markdown memory and content-free audit
- [x] official Google Drive and Docs writer with `drive.file`
- [x] Google Doc source workflow for NotebookLM
- [x] hardened Linux `systemd --user` timer
- [x] reversible Gmail cleanup rule engine
- [x] explicit-text-only Gemini bridge
- [x] public documentation, CI, security policy, and AI-readable metadata

Roadmap:

- [ ] simpler guided Google setup
- [ ] macOS `launchd` support
- [ ] Windows Task Scheduler support
- [ ] more curated-memory adapters
- [ ] configurable digest templates
- [ ] independent security audit

## Who this is for

Claude Daily Memory is useful for:

- developers running several Claude Code terminals;
- founders and operators managing many AI-assisted projects;
- researchers who want a NotebookLM knowledge base built from ongoing work;
- teams that need continuity without exporting raw AI transcripts;
- anyone tired of repeatedly explaining the same project context to an AI assistant.

## Contributing

The most valuable contributions are:

- new synthetic secret-scanner test cases;
- false-positive reductions;
- macOS and Windows scheduling support;
- clearer one-command onboarding;
- NotebookLM workflow documentation;
- accessibility, translation, and security review.

See [CONTRIBUTING.md](CONTRIBUTING.md). Never include real credentials, email, transcripts, or private memory in an issue or pull request.

## Security

Use GitHub's private vulnerability reporting. Do not place secrets or private digests in a public issue. See [SECURITY.md](SECURITY.md).

## License

Apache License 2.0.

Claude Daily Memory is not affiliated with or endorsed by Anthropic or Google. Claude, Gmail, Gemini, Google Drive, and NotebookLM are trademarks of their respective owners.
