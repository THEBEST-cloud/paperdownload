# paperdl package

The executable is `app/.venv/bin/paperdl`; run `app/scripts/setup.sh` first if
it is absent. Resolve both paths from this package directory rather than from
the user's current directory.

Run the executable from a separate user data directory so credentials,
browser state, downloads, and job data are not stored in the installed skill.
See `SKILL.md` and `references/configuration.md` for the supported workflow.
