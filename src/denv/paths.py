from __future__ import annotations

from pathlib import Path


CORE_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_NAME = "config.json"


def instance_dir(root: Path) -> Path:
    return root.resolve() / ".denv"


def config_path(root: Path) -> Path:
    return instance_dir(root) / DEFAULT_CONFIG_NAME


def local_dir(root: Path) -> Path:
    return instance_dir(root) / "local"
