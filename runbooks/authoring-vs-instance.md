# Private core versus public instance

## Public clone

The public `denv` clone is a general instance plus its runnable CLI, defaults,
profiles, and cognition starter. `denv setup` configures that checkout in
place; it does not create a second product tree.

## Private core (later)

The private `btye-dlr/denv-core` repository holds maintainer tests and export
automation. It publishes the cloneable starter and runtime to public
`btye-dlr/denv`.

## Maintainer loop before the split

1. Change this combined working tree.
2. Run unit tests.
3. Copy it to a disposable clone-equivalent directory.
4. Run `./bin/denv init` from that clone without `--root`.
5. Delete it.

Do not configure this authoring checkout during tests; `.denv/config.json`
must remain absent until it is deliberately used as an instance.
