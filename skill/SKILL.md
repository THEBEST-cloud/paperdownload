---
name: paperdl
description: >
  Search OpenAlex and download academic paper PDFs by DOI through authorized
  open-access sources or CAS CSTCloud/las.ac.cn institutional subscriptions.
  Use for paper search, setup, account configuration, login, batch download,
  retry/resume, and the paperdl web UI. Do not use for unauthorized sources.
---

# paperdl

Use the bundled CLI in `app/`. Resolve paths relative to this `SKILL.md`; do
not assume the user's current directory is the skill directory.

## Setup and data location

1. If `app/.venv/bin/paperdl` is missing, run `bash <skill-root>/app/scripts/setup.sh`.
2. Run the CLI by absolute path: `<skill-root>/app/.venv/bin/paperdl`.
3. Run CLI commands from a user-chosen data directory. The current directory
   stores `.paperdl.env`, `.profile/`, downloads, results, and web jobs; never
   put user credentials in the installed skill directory.

For install targets, account fields, and first-run commands, read
[`references/configuration.md`](references/configuration.md). For login,
browser, proxy, rate-limit, or retry failures, read
[`references/troubleshooting.md`](references/troubleshooting.md).

## Workflows

- Search without institutional login:
  `paperdl search "keywords" --from 2020 --sort cited -n 25`.
- Download subscribed papers: run `config`, `doctor`, and `login` once, then
  `run <doi-list>`; use `retry` after transient failures or rate-limit cooldown.
- Start the web UI with `serve --host 0.0.0.0 --port 8200`.

Replace `paperdl` above with the absolute bundled CLI path. Keep the default
8–20 second delay and batch limit. Never share `.paperdl.env` or `.profile/`.
Institutional access only covers the institution's subscriptions; direct users
to document delivery for unavailable papers.
