# Agent adapter boundaries

An adapter makes an agent runtime consume denv workspace truth. It does not
move runtime-private state into git.

## Shared by denv

- principles and ways of working;
- accepted and superseded decisions;
- curated project facts;
- current inter-session packet.

## Private to a runtime

- complete conversations and transcripts;
- SQLite/FTS stores;
- caches, embeddings, and provider state;
- credentials and generated runtime configuration.

## Cursor

The seeded root `AGENTS.md` is the entry pointer. It directs Cursor to the
canonical load order. Cursor chat history remains convenience context.

## Hermes

Hermes owns `.hermes/`, `state.db`, session search, and bounded prompt memory.
A future adapter may project a concise subset of denv project memory into
Hermes MEMORY and direct Hermes to denv principles. It must avoid silent
bidirectional synchronization and must not edit NemoClaw-generated config.

When both tools work on a ROOT, `.denv/cognition/sessions/CURRENT.md` and git
are the portable handoff surface. Adapter documentation remains in the denv
framework and is not copied into each instance.
