from __future__ import annotations

import re
from pathlib import Path
from typing import Any


SECRET_KEY_RE = re.compile(
    r"(?:^|_)(?:api_?key|token|secret|password)(?:$|_)", re.IGNORECASE
)
SECRET_ASSIGNMENT_RE = re.compile(
    r"(?im)^\s*[A-Za-z0-9_.-]*(?:api_?key|token|secret|password)"
    r"[A-Za-z0-9_.-]*\s*[:=]\s*[\"']?(?!\s*(?:|example|placeholder|redacted)"
    r"[\"']?\s*$)\S+"
)


def is_secret_key(key: str) -> bool:
    return bool(SECRET_KEY_RE.search(key.replace("-", "_")))


def find_secret_keys(value: Any, prefix: str = "") -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            path = f"{prefix}.{key}" if prefix else key
            if is_secret_key(key):
                found.append(path)
            found.extend(find_secret_keys(child, path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(find_secret_keys(child, f"{prefix}[{index}]"))
    return found


def scan_markdown(root: Path) -> list[Path]:
    findings: list[Path] = []
    cognition = root / ".denv/cognition"
    if not cognition.is_dir():
        cognition = root / "ops"
    if not cognition.is_dir():
        return findings
    for path in cognition.rglob("*.md"):
        try:
            if SECRET_ASSIGNMENT_RE.search(path.read_text(encoding="utf-8")):
                findings.append(path)
        except OSError:
            findings.append(path)
    return findings
