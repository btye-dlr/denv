# Daily use

denv is CLI tooling plus a markdown constitution. An application repository
gets only the instance footprint (`AGENTS.md` and `.denv/`). The denv checkout
stays the CLI; `init` records it in `.denv/local/env.json` as `core_path`.

Specs are not inherited. Each ROOT has its own `.denv/specs/` and its own
session packet. Config inherits as described in
[inheritance.md](inheritance.md). `doctor` checks every ROOT in the chain, so
an idle umbrella needs no spec while a nested project with an active goal does.

## 1. Tooling once

Clone denv anywhere and install it on PATH (see [install.md](install.md)).
Leave that checkout unconfigured. The absolute `<checkout>/bin/denv` path keeps
working when PATH is not set. Do not copy `bin/denv` into an app repo: the
launcher treats its parent directory as the core.

## 2. Empty single-level repo

```sh
mkdir app && cd app && git init
denv init --mode project --defaults
denv doctor
```

Result: `AGENTS.md`, `.denv/cognition/`, `.denv/specs/INDEX.md`,
`.denv/config.json`, `.denv/pin.json`, and gitignored `.denv/local/`.
`doctor` passes because the goal is `No active goal.`

## 3. Add a level later

```sh
denv init --mode umbrella --defaults            # at the repo root
denv init --root services/api --mode project --defaults
```

Each level has its own cognition, specs, and session. Read the umbrella pack
first, then the nearest project pack.

## 4. Start work

```sh
denv spec new "Short title"                     # agent or human; status draft
denv spec status 0001 approved                  # human only
```

## 5. Link the session

```sh
denv session begin --goal "One-line goal" --spec 0001
denv doctor
```

`begin` refuses a draft, done, or abandoned spec with the same reason `doctor`
would report. Implement against the spec's acceptance criteria.

## 6. Grow the spec

Keep the single file while it is small. Add `artifacts` in frontmatter when it
needs companion files. Set `rigor: workflow` and declare `plan` and `tasks`
only when that structure is needed; `doctor` then requires both files.

## 7. Close

Update Completed, Next, Risks and blockers, and Durable links in
`.denv/cognition/sessions/CURRENT.md`. Then:

```sh
denv spec status 0001 done
denv session end
denv doctor
```

The index keeps the finished spec.

## 8. Next change at the same level

`denv spec new` allocates the next id. Only the session link changes.

## 9. Restart

Read `AGENTS.md`, run `denv status`, then `denv session show`, then the linked
spec. Nothing else is authoritative over that order. `denv guide` prints this
loop when the repository does not yet have `AGENTS.md`.

## Nested ROOTs

`session begin` and `session end` affect only the ROOT they are aimed at. Use
`--root services/api` from the umbrella, or run from inside the project.

## Existing instances

`sync-ops` never overwrites an existing `AGENTS.md`. Instances created before
the working loop was added need the new entry-point text copied by hand.
New `init` runs pick it up.
