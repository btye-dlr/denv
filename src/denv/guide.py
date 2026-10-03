"""Working loop printed by `denv guide`."""

GUIDE = """\
denv working loop

denv is the CLI. An application repository gets AGENTS.md and .denv/.
The denv checkout stays the CLI.

Before a ROOT exists:

  denv init --mode project --defaults
  denv doctor

Files after init:

  AGENTS.md
  .denv/cognition/          principles, decisions, memory, sessions/CURRENT.md
  .denv/specs/              one spec file per change; INDEX.md is the catalog
  .denv/config.json         tracked config
  .denv/pin.json            core version pin
  .denv/local/              gitignored; holds env, secrets, and core_path

Each ROOT has its own specs and session. Config inherits. When status shows
an umbrella, read that pack first, then the nearest project pack.

Loop:

  denv status
  denv session show
  Read the spec named by the session before editing.
  denv spec new "Title"             draft only
  denv spec status <id> approved    human only; do not approve a spec yourself
  denv session begin --goal "..." --spec <id>
  Do the work against the spec's acceptance criteria.
  Update Completed, Next, Risks, and Durable links in
  .denv/cognition/sessions/CURRENT.md
  denv session end

An idle goal (No active goal.) needs no spec. An active goal must name a spec
whose status is approved or active. doctor enforces this. session begin
accepts only those two statuses and rewrites only the Goal and Spec sections.

Status moves draft -> approved -> active -> done. abandoned is allowed from
draft, approved, or active.

After denv self-update, run denv pin-refresh and denv sync-ops in each instance.
"""


def guide_text() -> str:
    return GUIDE.rstrip("\n")
