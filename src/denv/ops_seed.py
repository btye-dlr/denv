from __future__ import annotations

from pathlib import Path
import shutil

from .paths import CORE_ROOT


def seed_ops(root: Path) -> list[Path]:
    """Copy missing starter cognition without overwriting user content."""
    created: list[Path] = []
    agents_source = CORE_ROOT / "AGENTS.md"
    agents_destination = root / "AGENTS.md"
    if not agents_destination.exists():
        shutil.copy2(agents_source, agents_destination)
        created.append(agents_destination)

    source = CORE_ROOT / ".denv/cognition"
    destination_root = root / ".denv/cognition"
    for path in source.rglob("*"):
        relative = path.relative_to(source)
        destination = destination_root / relative
        if path.is_dir():
            destination.mkdir(parents=True, exist_ok=True)
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        if not destination.exists():
            shutil.copy2(path, destination)
            created.append(destination)
    return created


def required_ops_paths(root: Path) -> list[Path]:
    return [
        root / "AGENTS.md",
        root / ".denv/cognition/PRINCIPLES.md",
        root / ".denv/cognition/WAYS_OF_WORKING.md",
        root / ".denv/cognition/decisions/INDEX.md",
        root / ".denv/cognition/memory/PROJECT.md",
        root / ".denv/cognition/sessions/CURRENT.md",
    ]


def has_legacy_ops(root: Path) -> bool:
    return (root / "ops").is_dir() and not (root / ".denv/cognition").exists()
