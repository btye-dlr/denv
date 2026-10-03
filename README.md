# denv

`denv` is a clone-first development environment. The repository you clone is
both a general, unconfigured instance and the core tooling that configures it:

- tracked JSON configuration with umbrella/project inheritance;
- machine-local, gitignored environment and secret stores;
- a small commit-aware pin to the framework checkout;
- a vendor-neutral LLM cognition pack for principles, decisions, project
  memory, and session continuity.

denv is not an agent runtime, package installer, or transcript database.

## Requirements

Python 3.11 or newer. There is no pip, venv, build, or dependency install.
The launcher will use an available `python3.11`–`python3.14` when the default
`python3` is older.

To call `denv` from any directory, run `./bin/denv install` once (or
`--system`). See [runbooks/install.md](runbooks/install.md) for update and
rollback, and [runbooks/daily.md](runbooks/daily.md) for the working loop.

## Clone, then configure

```sh
git clone https://github.com/btye-dlr/denv.git
cd denv
./bin/denv --help
./bin/denv setup
```

After clone, `AGENTS.md`, `.denv/cognition/`, defaults, profiles, and the CLI
already exist. `setup` configures this checkout by writing tracked instance
config and machine-local values. `--help` and `--version` never configure it.

Non-interactive equivalent:

```sh
./bin/denv init \
  --mode umbrella \
  --profile generic \
  --defaults
```

The default ROOT is the current directory. Use `--root` only to configure a
nested project or another explicit path. `--mode project` configures one
project. `--config answers.json` overlays non-secret answers on a profile.
Never put credentials in an answers file.

## Commands

```text
setup             interactive initialization and --reconfigure
init              non-interactive initialization engine
doctor            validate config, pin, cognition, specs, and secret hygiene
status            show nearest ROOT, inheritance chain, pin, and cognition
resolve           show effective config and per-key provenance
config get|set    access nearest tracked config; secret-shaped keys are blocked
sync-ops          add missing cognition and spec templates without overwriting
pin-refresh       refresh the core identity recorded in .denv/pin.json
spec new          draft a single-file spec; does not approve it
spec list         list specs from the index
spec status       move a spec through draft, approved, active, done, abandoned
session show      show the goal and linked spec for the nearest ROOT
session begin     set the goal and link an approved or active spec
session end       return the session packet to idle
install           symlink bin/denv onto PATH (user or --system)
uninstall         remove that symlink when it points at this checkout
self-update       update this checkout with git (ff-only or --ref <tag>)
vendor-refresh    deprecated alias for pin-refresh during transition
migrate-layout    explicitly move a legacy ops/vendor instance
```

## General instance versus configured instance

The clone is already the general instance. Before setup it has no
`.denv/config.json`, pin, secrets, or machine path. Running `setup` or `init`
turns that same checkout into the configured instance.

The cloneable product contains:

```text
denv/
  AGENTS.md                  # thin, cross-tool entry point; created if missing
  bin/denv                   # runnable core tooling
  src/denv/
  defaults.toml
  profiles/
  .denv/
    cognition/
      PRINCIPLES.md
      WAYS_OF_WORKING.md
      decisions/INDEX.md
      memory/PROJECT.md
      sessions/CURRENT.md
    specs/
      INDEX.md                # specs are added with `denv spec new`
    config.json               # added by setup
    pin.json                  # added by setup
    local/                    # added by setup; gitignored
```

denv owns `.denv/`; `AGENTS.md` is the only default root overlay because major
coding agents already discover it there. If `AGENTS.md` exists, denv leaves it
unchanged. It does not create `CLAUDE.md`, `.cursor/`, adapter files, example
ADRs, or a second copied framework tree.

Track `config.json`, `pin.json`, `cognition/`, and `specs/`. `.denv/local/`
contains `env.json`, `secrets.json`, and `USER.md` and stays gitignored.

## Configuration semantics

- Missing key: inherit.
- Empty string or array: explicit override.
- Objects: deep-merge.
- Arrays and scalars: replace.
- Nearest project ROOT wins.
- An umbrella ROOT is included and stops further ascent.

`denv resolve --json` shows both the effective value and its source.

## Specs

Tracked specs live under `.denv/specs/` (`specs_dir` in config). `denv spec new`
drafts one markdown file. An active session goal must name a spec whose status
is `approved` or `active`; `doctor` fails otherwise. An idle goal
(`No active goal.`) does not need a spec.

Reference companion files from frontmatter when one file is no longer enough.
Set `rigor: workflow` and declare `artifacts.plan` and `artifacts.tasks` when
the change needs a plan and a task list. Humans approve a spec with
`denv spec status <id> approved`.

## LLM cognition boundary

denv owns workspace-shared truth under `.denv/cognition/`. Agent runtimes own
chats, transcripts, caches, and search databases. A Hermes or Cursor adapter
consumes the denv pack; it must not create a competing project constitution.

See [runbooks/ops-cognition.md](runbooks/ops-cognition.md) and
[runbooks/adapters.md](runbooks/adapters.md).

## Development

```sh
/opt/homebrew/bin/python3.14 -m unittest discover -s tests -v
```

Any Python 3.11+ interpreter may replace the path above.

Public releases are published at https://github.com/btye-dlr/denv from a
private maintainer `denv-core` repository. Tests and export tooling stay in the
private core; the public repository contains the starter and runtime required
for clone → setup. denv is licensed under the MIT License.
