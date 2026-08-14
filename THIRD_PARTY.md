# Third-party components

Claude Daily Memory is Apache-2.0 licensed. Its Python dependencies retain their own licenses.

## notebooklm-py

- Package: `notebooklm-py[browser,mcp]==0.8.0`
- Upstream: <https://github.com/teng-lin/notebooklm-py>
- License: MIT
- Role: local NotebookLM authentication, command-line operations, and the full local MCP server.

This dependency uses internal NotebookLM web RPCs rather than a stable public consumer API. Google changes can break compatibility or require renewed local authentication. Claude Daily Memory pins the reviewed version, wraps setup/daily operations in a small adapter, tests command and JSON contracts synthetically, and exposes the upstream full MCP locally through `stdio`.

Supported setup excludes upstream remote-server and credential-export patterns: no HTTP listener, remote MCP, master-token flow, `NOTEBOOKLM_AUTH_JSON`, or cloud cookie transfer. Browser-session state remains local under `~/.notebooklm/`.

The third-party dependency is part of the single Claude Daily Memory installation; this notice documents implementation and licensing rather than a separate product mode.

For the complete transitive dependency list and exact licenses, inspect the built environment with the appropriate package/license tooling before redistribution.
