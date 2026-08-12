# Security Policy

## Supported versions

Claude Daily Memory is currently alpha software. Security fixes are applied to the latest version on the `main` branch.

## Reporting a vulnerability

Do not include secrets, private email, OAuth credentials, real transcripts, or personal digests in a public GitHub issue.

Use GitHub's **Private vulnerability reporting** feature in the repository's Security tab. Include:

- affected version or commit;
- minimal reproduction using synthetic data;
- expected and observed behavior;
- impact and suggested mitigation, if known.

If private reporting is unavailable, open a public issue containing no exploit details or private data and ask the maintainer to provide a private channel.

## Security promises and limits

The project is designed to avoid reading raw Claude transcripts, reject common secret formats before upload, use `drive.file`, and store refresh tokens in an operating-system Secret Service. These controls reduce risk but cannot guarantee detection of every secret. Use local dry-run mode before enabling cloud export.
