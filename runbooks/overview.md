# denv operator overview

1. Clone public `denv` and enter the clone.
2. Verify `./bin/denv --help`; this does not configure anything.
3. Run `./bin/denv setup` or `init --mode … --defaults` without `--root`.
4. Review `.denv/config.json`, `.denv/cognition/`, and the thin `AGENTS.md`.
5. Keep `.denv/local/` gitignored.
6. Run `doctor`, then use `status` and `resolve` when diagnosing discovery.
7. Use `sync-ops` after framework updates; it only adds missing templates.
8. Use `pin-refresh` after updating the clone to refresh `.denv/pin.json`.

The instance creates no root `ops/`, copied core tree, adapter files, or example
ADRs. Existing root `AGENTS.md` content is never overwritten.

See the focused runbooks for setup, inheritance, cognition, and adapters.
