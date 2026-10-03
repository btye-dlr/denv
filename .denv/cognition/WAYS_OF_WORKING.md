# Ways of working

## Start a session

Read the cognition pack in the order documented by `AGENTS.md`. Run
`denv session show` and read the linked spec. Restate the active goal,
constraints, and evidence needed for completion before changing the workspace.

If the session is idle and new work is needed: draft with `denv spec new`,
wait for a human `denv spec status <id> approved`, then run
`denv session begin --goal "..." --spec <id>`.

## During a session

- Keep one active goal.
- Write durable “why” as an ADR, not only in chat.
- Update project memory only with stable, reusable facts.
- Re-read constraints after context compression or a long detour.
- Stop and reconcile conflicts between chat, code, and recorded decisions.

## Spec before code

An active session goal requires an approved spec. `doctor` fails when the goal
is set and the Spec section does not name a spec in status `approved` or
`active`. An idle goal (`No active goal.`) does not require a spec. Use
`denv session begin` and `denv session end` to change the goal and spec link;
they rewrite only those two sections.

Keep the spec as one file under `.denv/specs/` while it is small. Reference
companion files from frontmatter when it needs them. Set `rigor: workflow` only
when the work needs a plan and a task list; those two artifacts are then
required.

Agents may draft specs with `denv spec new`. Humans approve them with
`denv spec status <id> approved`. Agents must not approve their own specs.

## Close a session

Update `sessions/CURRENT.md` with constraints, completed work, next actions,
risks, and durable links. Run `denv session end` when the goal is finished so
the packet returns to idle. Archive it when work changes to a new goal.
