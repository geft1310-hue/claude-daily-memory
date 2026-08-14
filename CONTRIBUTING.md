# Contributing

Thank you for helping make persistent AI memory safer and easier to use.

## Required workflow

1. Add or update a synthetic test first.
2. Run it and confirm the expected failure.
3. Implement the smallest production change that satisfies the contract.
4. Run the focused tests, then the complete suite twice.
5. Build sdist and wheel, install the wheel in a clean environment, and run `pip check`.
6. Update English and Russian documentation together for every user-visible change.

Do not weaken or delete a safety assertion to make a change pass.

## Development

```bash
python3 -m venv .venv
.venv/bin/pip install -e '.[google,gemini,notebooklm]'
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests
```

## Safety rules

- Never commit real API keys, OAuth files/tokens, email, transcripts, personal digests, notebook/source IDs, NotebookLM cookies, `storage_state.json`, `master_token.json`, or browser profiles.
- Use synthetic examples in tests, issues, and documentation.
- New network destinations require a documented threat-model update.
- Sanitizer and parser uncertainty must fail closed.
- Daily state must not advance after a failed Drive write or NotebookLM refresh.
- Preserve one application environment and local `stdio` MCP; do not introduce remote HTTP NotebookLM transport, cloud cookie transfer, `NOTEBOOKLM_AUTH_JSON`, or master-token setup.
- Keep `notebooklm-py` pinned and review upstream changes before updating it.
- Notebook/source deletion and sharing expansion must retain preview plus explicit confirmation.
- Permanent Gmail deletion remains unsupported.

Good contributions include synthetic scanner cases, installer improvements, NotebookLM command-contract tests, clearer bilingual onboarding, systemd hardening, accessibility, and macOS/Windows scheduling.

Keep pull requests focused and explain their user-visible behavior and security effect.
