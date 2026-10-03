# Agent entry point

This workspace uses denv. Before work, read in order:

1. `.denv/cognition/PRINCIPLES.md`
2. `.denv/cognition/WAYS_OF_WORKING.md`
3. `.denv/cognition/decisions/INDEX.md` and relevant active decisions
4. `.denv/cognition/memory/PROJECT.md`
5. `.denv/cognition/sessions/CURRENT.md`
6. The spec named by that session, under `.denv/specs/`

Working loop:

- Use `denv` from PATH. If it is missing, use `<core_path>/bin/denv`, where
  `core_path` is recorded in `.denv/local/env.json`.
- Run `denv status` to see the nearest ROOT and its chain. When the chain has
  an umbrella, read its cognition first, then this ROOT's pack.
- Run `denv session show`, then read the linked spec before editing.
- Draft new work with `denv spec new "Title"`. Stop and wait for a human to run
  `denv spec status <id> approved`. Do not approve a spec yourself.
- Start with `denv session begin --goal "..." --spec <id>`.
- Before finishing, update Completed, Next, Risks, and Durable links in
  `sessions/CURRENT.md`, then run `denv session end`.

Decisions override chat history until explicitly superseded. Never place
secrets in tracked cognition or spec files.
