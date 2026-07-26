# Umbrella and project inheritance

An umbrella ROOT establishes shared defaults for projects below it. A project
ROOT adds or replaces only what it needs.

Resolution walks upward from the requested path, gathers configured ROOTs, and
stops after including the first `mode = "umbrella"` ROOT. Core
`defaults.toml` is the outermost fallback.

Merge behavior is deterministic:

- absent keys inherit;
- objects recursively merge;
- arrays replace rather than concatenate;
- empty strings and empty arrays are intentional overrides;
- scalars replace.

Use:

```sh
denv resolve --root <path> --json
```

The `provenance` object identifies the file that supplied every effective leaf
value.

Cognition content is document-based rather than mechanically merged. Read the
parent umbrella `.denv/cognition/` principles first and then the nearest
project pack. A project ADR must explicitly supersede a parent convention when
they conflict.
