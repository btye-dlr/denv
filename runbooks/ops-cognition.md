# LLM cognition

The `.denv/cognition/` pack is durable workspace memory, not a chat archive.

## Load sequence

1. Principles: slow-changing constitution.
2. Ways of working: session discipline and anti-drift practices.
3. Decision index and applicable ADRs: durable rationale.
4. Project memory: bounded stable facts and lessons.
5. Current session packet: active goal and restart point.
6. The spec named by that session, then any artifacts it declares.
7. Runtime-private memory: useful but never authoritative over the above.

## Inter-session continuity

At session close, update `.denv/cognition/sessions/CURRENT.md` with:

- active goal and status;
- constraints and governing ADRs;
- verified outcomes;
- ordered next actions;
- risks, blockers, and failed approaches;
- durable links.

Archive the packet when switching to a genuinely new goal. It is a compact
restart record, not a transcript.

## Memory quality

Keep `.denv/cognition/memory/PROJECT.md` compact and actionable. Prefer stable
conventions, environment facts, and validated workarounds. Skip raw logs, task
diaries, temporary paths, and facts obvious from the repository. Consolidate
around 80% of its soft 4,000-character budget.

## Drift controls

- Decisions outrank conversation history until superseded by a new ADR.
- Re-read the pack after context compression or a lengthy detour.
- Record “why” before relying on a model to remember it.
- Reconcile contradictions rather than choosing the most recent statement.
- Keep one active goal in CURRENT.
- Never put secrets in tracked cognition or spec files.

## Specs

Specs are the tracked "what" for a change. They live in `.denv/specs/` unless
`specs_dir` says otherwise.

- `denv spec new` creates one draft file and an index row. It does not approve.
- A light spec is that single file. Declare `artifacts` when it needs companion
  files. Set `rigor: workflow` to require `plan` and `tasks`.
- `denv spec status <id> approved` is the human approval step. `active` and
  `done` follow. `draft`, `done`, and `abandoned` do not satisfy an active
  session.
- Put the spec id under `## Spec` in the session packet. Leave the goal as
  `No active goal.` when nothing is in progress.
