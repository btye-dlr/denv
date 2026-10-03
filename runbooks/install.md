# Install and update

denv is installed as a symlink to `bin/denv` in one git checkout. There is no
pip, venv, build step, or copied files. The checkout is the single source and
every instance records it as `core_path` in `.denv/local/env.json`.

## Where to clone

Any path works. `~/.local/share/denv` is a reasonable default for a personal
install; a shared path such as `/opt/denv` suits a system install.

```sh
git clone https://github.com/btye-dlr/denv.git ~/.local/share/denv
```

## User install

```sh
~/.local/share/denv/bin/denv install
```

This links `~/.local/bin/denv` to the checkout's launcher. If `~/.local/bin`
is not on `PATH`, the command prints the one line to add to your shell
profile. denv does not edit shell profiles.

## System install

```sh
/opt/denv/bin/denv install --system
```

This targets `/usr/local/bin/denv`. denv never calls `sudo`. When the
directory is not writable it exits non-zero and prints the exact command to
rerun with elevated privileges.

`--bin-dir <path>` overrides either default.

## Rules

- If the link already points at this checkout, `install` reports it and exits 0.
- If the target is a symlink to something else, `install` refuses unless
  `--force`. A regular file is never deleted; remove it yourself.
- Two checkouts (for example a release tag and a working branch) can coexist
  by using different `--bin-dir` values.

## Update

```sh
denv self-update            # fast-forward the current branch
denv self-update --ref v0.2.1   # detach at a tag or branch
```

`self-update` refuses a checkout with uncommitted changes. It prints the
version and SHA before and after. Then, in each instance ROOT:

```sh
denv pin-refresh
denv sync-ops
```

denv keeps no registry of instances, so it does not run these for you.
`doctor` fails when `core_path` is missing, unreadable, or has no `VERSION`.
It prints a `WARN` when an instance's pin differs from its core, and `status`
shows the core version beside the pin, so an update does not fail an idle
instance.

`sync-ops` adds missing templates such as `.denv/specs/INDEX.md`. It never
overwrites an existing `AGENTS.md` or cognition file.

## Rollback

```sh
denv self-update --ref v0.1.0
denv pin-refresh      # in each instance
```

## Uninstall

```sh
denv uninstall            # or --system / --bin-dir
```

Removes the symlink only when it points at this checkout. Instances keep
working through `<core_path>/bin/denv`.

## Out of scope

Windows symlinks and package managers (Homebrew, pipx) are not covered by this
release.
