from __future__ import annotations

import os
from pathlib import Path
import re
import subprocess

from .paths import CORE_ROOT


class InstallError(RuntimeError):
    pass


USER_BIN = Path("~/.local/bin")
SYSTEM_BIN = Path("/usr/local/bin")
LINK_NAME = "denv"
REF_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]*$")


def launcher_path(core: Path = CORE_ROOT) -> Path:
    return core / "bin" / LINK_NAME


def resolve_bin_dir(system: bool, bin_dir: str | None) -> Path:
    if bin_dir:
        return Path(bin_dir).expanduser().resolve()
    return (SYSTEM_BIN if system else USER_BIN).expanduser().resolve()


def install(
    system: bool = False,
    bin_dir: str | None = None,
    force: bool = False,
    core: Path = CORE_ROOT,
) -> list[str]:
    """Symlink bin/denv into a bin directory. Never escalates privileges."""
    target_dir = resolve_bin_dir(system, bin_dir)
    launcher = launcher_path(core)
    if not launcher.is_file():
        raise InstallError(f"launcher not found: {launcher}")
    link = target_dir / LINK_NAME
    messages: list[str] = []

    if _points_at(link, launcher):
        messages.append(f"Already installed: {link} -> {launcher}")
        messages.extend(_path_hint(target_dir))
        return messages

    if link.is_symlink() or link.exists():
        if not force:
            kind = "symlink" if link.is_symlink() else "file"
            raise InstallError(
                f"{link} exists and is a {kind} not managed by this checkout; "
                "rerun with --force to replace a symlink"
            )
        if not link.is_symlink():
            raise InstallError(
                f"{link} is a regular file; remove it manually before installing"
            )

    try:
        target_dir.mkdir(parents=True, exist_ok=True)
        if link.is_symlink():
            link.unlink()
        link.symlink_to(launcher)
    except PermissionError as error:
        raise InstallError(
            f"cannot write {target_dir}: {error.strerror}. Rerun with elevated "
            f"privileges, for example: sudo {launcher} install --bin-dir {target_dir}"
        ) from error
    except OSError as error:
        raise InstallError(f"cannot create {link}: {error}") from error

    messages.append(f"Installed {link} -> {launcher}")
    messages.extend(_path_hint(target_dir))
    return messages


def uninstall(
    system: bool = False,
    bin_dir: str | None = None,
    core: Path = CORE_ROOT,
) -> str:
    target_dir = resolve_bin_dir(system, bin_dir)
    link = target_dir / LINK_NAME
    launcher = launcher_path(core)
    if not link.is_symlink():
        if link.exists():
            raise InstallError(f"{link} is not a symlink; leaving it in place")
        return f"Nothing installed at {link}"
    if not _points_at(link, launcher):
        raise InstallError(
            f"{link} points elsewhere ({os.readlink(link)}); leaving it in place"
        )
    try:
        link.unlink()
    except PermissionError as error:
        raise InstallError(
            f"cannot remove {link}: {error.strerror}. Rerun with elevated privileges."
        ) from error
    return f"Removed {link}"


def self_update(ref: str | None = None, core: Path = CORE_ROOT) -> list[str]:
    """Update the core checkout with git. Refuses dirty trees."""
    if not (core / ".git").exists():
        raise InstallError(f"{core} is not a git checkout; update it by other means")
    if ref is not None and not REF_RE.match(ref):
        raise InstallError(f"invalid ref: {ref!r}")
    status = _git(core, "status", "--porcelain")
    if status.stdout.strip():
        raise InstallError(
            f"{core} has uncommitted changes; commit or stash them before self-update"
        )
    before_version = _version(core)
    before_sha = _git(core, "rev-parse", "--short", "HEAD").stdout.strip()

    if ref is None:
        branch = _git(core, "symbolic-ref", "--quiet", "--short", "HEAD")
        if branch.returncode != 0:
            raise InstallError(
                "checkout is detached; pass --ref <tag> to move to a release"
            )
        _run_or_fail(core, "pull", "--ff-only")
    else:
        _run_or_fail(core, "fetch", "--tags", "--prune")
        _run_or_fail(core, "checkout", "--detach", "--quiet", ref)

    after_version = _version(core)
    after_sha = _git(core, "rev-parse", "--short", "HEAD").stdout.strip()
    lines = [
        f"Core {core}",
        f"Before: {before_version} ({before_sha})",
        f"After:  {after_version} ({after_sha})",
    ]
    if (before_version, before_sha) == (after_version, after_sha):
        lines.append("Already up to date.")
    else:
        lines.append(
            "In each instance ROOT run: denv pin-refresh && denv sync-ops"
        )
    return lines


def _points_at(link: Path, launcher: Path) -> bool:
    if not link.is_symlink():
        return False
    try:
        return link.resolve() == launcher.resolve()
    except OSError:
        return False


def _path_hint(target_dir: Path) -> list[str]:
    entries = {
        Path(part).expanduser().resolve()
        for part in os.environ.get("PATH", "").split(os.pathsep)
        if part
    }
    if target_dir in entries:
        return []
    return [
        f"{target_dir} is not on PATH. Add this line to your shell profile:",
        f'  export PATH="{target_dir}:$PATH"',
    ]


def _version(core: Path) -> str:
    try:
        return (core / "VERSION").read_text(encoding="utf-8").strip()
    except OSError:
        return "unknown"


def _git(core: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=core,
        text=True,
        capture_output=True,
        check=False,
    )


def _run_or_fail(core: Path, *args: str) -> None:
    result = _git(core, *args)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise InstallError(f"git {' '.join(args)} failed: {detail}")
