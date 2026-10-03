# Setup and reconfiguration

`setup` is the interactive wrapper. `init` is the deterministic engine used by
automation and tests.

## Interactive

```sh
git clone https://github.com/btye-dlr/denv.git
cd denv
./bin/denv setup
```

The default ROOT is the current clone. The questionnaire records instance,
git, stack, and non-sensitive environment answers. Environment answers and the
local core path go to `.denv/local/env.json`.

Use `setup --reconfigure` to revisit answers. Unknown tracked config keys,
unknown local environment keys, and existing `secrets.json` content are
preserved. Cognition files with user content and an existing root `AGENTS.md`
are never replaced.

## Non-interactive

```sh
./bin/denv init --mode project --profile python --defaults
```

An optional JSON answers file deep-merges over defaults and profile. Secret-
shaped keys are rejected. Put credentials directly into the gitignored
`.denv/local/secrets.json`, using the security controls appropriate to the
host.

Use `--root <path>` only for a nested project or another explicitly chosen
ROOT.

## v0.1 layout migration

If `status`, `doctor`, or `sync-ops` reports a legacy root `ops/`, inspect it,
then migrate explicitly:

```sh
./bin/denv migrate-layout --root <root>
```

The command moves `ops/` to `.denv/cognition/`, removes the generated vendor
snapshot, writes `pin.json`, updates legacy config keys, and rewrites
`AGENTS.md` only when it exactly matches the old stock template. It also adds
a missing `.denv/specs/INDEX.md` without overwriting existing files.
