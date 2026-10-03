from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any

from .discover import discover_chain, read_config
from .ops_seed import has_legacy_ops, required_ops_paths
from .paths import config_path
from .secrets import find_secret_keys, scan_markdown
from .specs import resolve_specs_dir, validate_instance
from .vendor import git_metadata


MEMORY_WARN_CHARS = 4_000


def inspect(root: Path) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    path = config_path(root)
    if not path.is_file():
        return [f"missing {path}"], warnings
    config = read_config(path)
    for key in find_secret_keys(config):
        errors.append(f"secret-shaped config key: {key}")
    legacy = has_legacy_ops(root)
    if legacy:
        warnings.append(
            "legacy ops/ layout detected; run `denv migrate-layout`"
        )
        required_paths = [
            root / "AGENTS.md",
            root / "ops/PRINCIPLES.md",
            root / "ops/WAYS_OF_WORKING.md",
            root / "ops/decisions/INDEX.md",
            root / "ops/memory/PROJECT.md",
            root / "ops/sessions/CURRENT.md",
        ]
    else:
        required_paths = required_ops_paths(root)
    for required in required_paths:
        if not required.is_file():
            errors.append(f"missing {required.relative_to(root)}")
    specs_dir, _specs_error = resolve_specs_dir(root)
    for finding in scan_markdown(root, [specs_dir] if _specs_error is None else []):
        errors.append(f"secret-shaped content: {finding.relative_to(root)}")
    memory = (
        root / "ops/memory/PROJECT.md"
        if legacy
        else root / ".denv/cognition/memory/PROJECT.md"
    )
    if memory.is_file() and len(memory.read_text(encoding="utf-8")) > MEMORY_WARN_CHARS:
        warnings.append(
            f"{memory.relative_to(root)} exceeds soft 4,000-character budget"
        )
    pin = root / ".denv/pin.json"
    if not pin.is_file():
        if legacy and (root / ".denv/vendor/VERSION.json").is_file():
            warnings.append(
                "legacy vendor metadata is not a pin; run `denv migrate-layout`"
            )
        else:
            errors.append("missing .denv/pin.json")
    else:
        try:
            metadata: dict[str, Any] = json.loads(pin.read_text(encoding="utf-8"))
            required_pin_keys = {
                "semver",
                "sha",
                "dirty",
                "source_tree_sha256",
                "recorded_at",
            }
            missing = required_pin_keys - metadata.keys()
            if missing:
                errors.append(
                    "invalid .denv/pin.json; missing " + ", ".join(sorted(missing))
                )
            if not metadata.get("sha"):
                warnings.append("pin source has no git commit SHA; core is uncommitted")
            if core_problem(root) is None:
                drift = core_drift(root, metadata)
                if drift:
                    warnings.append(drift)
        except (OSError, json.JSONDecodeError):
            errors.append("invalid .denv/pin.json")
    problem = core_problem(root)
    if problem:
        errors.append(problem)
    if (root / ".denv/vendor").exists():
        warnings.append("legacy vendor snapshot detected; run `denv migrate-layout`")
    errors.extend(validate_instance(root, legacy=legacy))
    return errors, warnings


def core_problem(root: Path) -> str | None:
    """Return an error when this ROOT cannot name a usable core checkout."""
    env_path = root / ".denv/local/env.json"
    if not env_path.is_file():
        return "missing .denv/local/env.json core_path"
    try:
        environment = json.loads(env_path.read_text(encoding="utf-8"))
        raw = environment["core_path"]
        if not isinstance(raw, str) or not raw.strip():
            raise KeyError("core_path")
        core = Path(raw).expanduser().resolve()
    except (OSError, json.JSONDecodeError, KeyError, TypeError):
        return "unreadable .denv/local/env.json core_path"
    if not (core / "VERSION").is_file():
        return (
            f"core_path {core} has no VERSION; reinstall or run "
            "`denv setup --reconfigure`"
        )
    return None


def core_identity(root: Path) -> dict[str, Any] | None:
    """Return version and SHA of the core named in .denv/local/env.json, if any."""
    env_path = root / ".denv/local/env.json"
    if not env_path.is_file():
        return None
    try:
        environment = json.loads(env_path.read_text(encoding="utf-8"))
        raw = environment["core_path"]
        if not isinstance(raw, str) or not raw.strip():
            return None
        core = Path(raw).expanduser().resolve()
    except (OSError, json.JSONDecodeError, KeyError, TypeError):
        return None
    if not (core / "VERSION").is_file():
        return {"path": str(core), "semver": None, "sha": None, "present": False}
    identity = git_metadata(core)
    return {
        "path": str(core),
        "semver": (core / "VERSION").read_text(encoding="utf-8").strip(),
        "sha": identity["sha"],
        "present": True,
    }


def core_drift(root: Path, pin: dict[str, Any]) -> str | None:
    core = core_identity(root)
    if core is None or not core["present"]:
        return None
    mismatch: list[str] = []
    if pin.get("semver") != core["semver"]:
        mismatch.append(f"version {pin.get('semver')} -> {core['semver']}")
    if core["sha"] and pin.get("sha") and pin.get("sha") != core["sha"]:
        mismatch.append(f"sha {str(pin.get('sha'))[:7]} -> {core['sha'][:7]}")
    if not mismatch:
        return None
    return (
        "pin differs from core (" + ", ".join(mismatch) + "); "
        "run `denv pin-refresh` and `denv sync-ops`"
    )


def report(root: Path) -> tuple[int, str]:
    lines = [f"OK Python {sys.version.split()[0]} (requires >= 3.11)"]
    chain = discover_chain(root)
    if not chain:
        return 1, "\n".join(lines + [f"ERROR no denv ROOT found from {root}"])
    for discovered in chain:
        errors, warnings = inspect(discovered)
        lines.append(f"ROOT {discovered}")
        lines.extend(f"WARN {warning}" for warning in warnings)
        lines.extend(f"ERROR {error}" for error in errors)
    return (
        1 if any(line.startswith("ERROR") for line in lines) else 0,
        "\n".join(lines),
    )
