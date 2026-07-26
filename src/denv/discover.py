from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .merge import deep_merge, leaf_paths
from .paths import config_path


MAX_DISCOVERY_DEPTH = 64


class DiscoveryError(RuntimeError):
    pass


def read_config(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise DiscoveryError(f"cannot read {path}: {error}") from error
    if not isinstance(value, dict):
        raise DiscoveryError(f"{path} must contain a JSON object")
    return value


def discover_chain(start: Path) -> list[Path]:
    """Return configured ROOTs from outermost to nearest."""
    current = start.resolve()
    if current.is_file():
        current = current.parent
    nearest_first: list[Path] = []
    for _ in range(MAX_DISCOVERY_DEPTH):
        candidate = config_path(current)
        if candidate.is_file():
            nearest_first.append(current)
            if read_config(candidate).get("mode") == "umbrella":
                break
        parent = current.parent
        if parent == current:
            break
        current = parent
    else:
        raise DiscoveryError("ROOT discovery exceeded 64 directories")
    return list(reversed(nearest_first))


def nearest_root(start: Path) -> Path:
    chain = discover_chain(start)
    if not chain:
        raise DiscoveryError(
            f"no denv instance found from {start.resolve()}; run denv init or setup"
        )
    return chain[-1]


def resolve_config(
    start: Path, defaults: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, str], list[Path]]:
    effective = defaults
    provenance = {path: "core:defaults.toml" for path in leaf_paths(defaults)}
    chain = discover_chain(start)
    for root in chain:
        path = config_path(root)
        overlay = read_config(path)
        effective = deep_merge(effective, overlay)
        for key in leaf_paths(overlay):
            provenance[key] = str(path)
    return effective, provenance, chain
