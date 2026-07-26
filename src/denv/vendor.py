from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import subprocess
from typing import Any

from .paths import CORE_ROOT, instance_dir


VENDOR_ASSETS = (
    "VERSION",
    "AGENTS.md",
    ".denv/cognition",
    "bin",
    "defaults.toml",
    "profiles",
    "setup",
    "src",
)


def _git_metadata(core: Path) -> dict[str, Any]:
    revision = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=core,
        text=True,
        capture_output=True,
        check=False,
    )
    status = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=core,
        text=True,
        capture_output=True,
        check=False,
    )
    sha = revision.stdout.strip() if revision.returncode == 0 else None
    return {"sha": sha, "dirty": status.returncode != 0 or bool(status.stdout.strip())}


def _tree_digest(core: Path) -> str:
    digest = hashlib.sha256()
    for relative in VENDOR_ASSETS:
        path = core / relative
        if path.is_file():
            digest.update(relative.encode())
            digest.update(path.read_bytes())
        elif path.is_dir():
            for child in sorted(candidate for candidate in path.rglob("*") if candidate.is_file()):
                digest.update(str(child.relative_to(core)).encode())
                digest.update(child.read_bytes())
    return digest.hexdigest()


def refresh_pin(root: Path, core: Path = CORE_ROOT) -> dict[str, Any]:
    """Record core identity without copying the framework into the instance."""
    destination = instance_dir(root)
    destination.mkdir(parents=True, exist_ok=True)
    version = (core / "VERSION").read_text(encoding="utf-8").strip()
    metadata = {
        **_git_metadata(core),
        "semver": version,
        "source_tree_sha256": _tree_digest(core),
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    }
    (destination / "pin.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return metadata


def refresh_vendor(root: Path, core: Path = CORE_ROOT) -> dict[str, Any]:
    """Deprecated compatibility alias for v0.1 callers."""
    return refresh_pin(root, core)
