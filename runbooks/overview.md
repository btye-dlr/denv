# denv operator overview

1. Clone public `denv` and enter the clone.
2. Verify `./bin/denv --help`; this does not configure anything.
3. Run `./bin/denv setup` or `init --mode … --defaults` without `--root`.
4. Review `.denv/config.json`, `.denv/cognition/`, and the thin `AGENTS.md`.
5. Keep `.denv/local/` gitignored.
6. Run `doctor`. An active session goal must name an approved spec. Then use
   `status` and `resolve` when diagnosing discovery.
7. Use `sync-ops` after framework updates; it only adds missing templates.
8. Use `self-update` in the checkout, then `pin-refresh` and `sync-ops` in each
   instance. `doctor` warns when the pin no longer matches the core.

The instance creates no root `ops/`, copied core tree, adapter files, or example
ADRs. Existing root `AGENTS.md` content is never overwritten.

See the focused runbooks for [install](install.md), [daily use](daily.md),
setup, inheritance, cognition, and adapters.
