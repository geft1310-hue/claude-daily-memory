# Contributing

Thank you for helping make long-term AI memory safer.

## Good first contributions

- add synthetic false-positive and false-negative scanner tests;
- improve plain-language installation documentation;
- review Linux systemd hardening;
- add adapters that consume curated artifacts without transcripts;
- improve accessibility and translations.

## Development

```bash
python3 -m venv .venv
.venv/bin/pip install -e .
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests
```

## Safety rules

- never commit real API keys, OAuth files, email, transcripts, or generated daily digests;
- use synthetic examples in tests and issues;
- new network destinations require a documented threat-model update;
- sanitizer errors must fail closed;
- permanent Gmail deletion must remain unsupported;
- do not introduce unofficial NotebookLM APIs or browser-cookie automation.

Please keep pull requests focused and explain the user-visible security effect.
