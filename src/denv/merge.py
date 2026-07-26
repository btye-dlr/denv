from __future__ import annotations

from copy import deepcopy
from typing import Any


JsonObject = dict[str, Any]


def deep_merge(base: JsonObject, overlay: JsonObject) -> JsonObject:
    """Deep-merge dictionaries; all other values, including arrays, replace."""
    result = deepcopy(base)
    for key, value in overlay.items():
        current = result.get(key)
        if isinstance(current, dict) and isinstance(value, dict):
            result[key] = deep_merge(current, value)
        else:
            result[key] = deepcopy(value)
    return result


def leaf_paths(value: Any, prefix: str = "") -> list[str]:
    if isinstance(value, dict):
        paths: list[str] = []
        for key, child in value.items():
            path = f"{prefix}.{key}" if prefix else key
            paths.extend(leaf_paths(child, path))
        return paths
    return [prefix]
