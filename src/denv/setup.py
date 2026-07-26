from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from .init import initialize, load_defaults
from .paths import config_path


Prompt = Callable[[str], str]


def _ask(prompt: Prompt, label: str, default: str) -> str:
    answer = prompt(f"{label} [{default}]: ").strip()
    return answer or default


def interactive_setup(
    root: Path,
    reconfigure: bool = False,
    prompt: Prompt = input,
) -> dict[str, Any]:
    existing: dict[str, Any] = {}
    existing_path = config_path(root)
    if reconfigure and existing_path.is_file():
        loaded = json.loads(existing_path.read_text(encoding="utf-8"))
        if isinstance(loaded, dict):
            existing = loaded
    default_mode = str(existing.get("mode", "project"))
    default_profile = str(existing.get("profile", "generic"))
    mode = _ask(prompt, "Mode (umbrella/project)", default_mode)
    if mode not in {"umbrella", "project"}:
        raise ValueError("mode must be umbrella or project")
    profile = _ask(prompt, "Profile (generic/python/node)", default_profile)
    defaults = load_defaults(profile)
    branch = _ask(
        prompt, "Default git branch", str(defaults["git"]["default_branch"])
    )
    languages = _ask(
        prompt,
        "Languages (comma-separated)",
        ",".join(defaults["stack"]["languages"]),
    )
    test_command = _ask(
        prompt, "Test command", str(defaults["stack"]["test_command"])
    )
    editor = _ask(prompt, "Preferred editor", "")
    answers = {
        "git": {"default_branch": branch},
        "stack": {
            "languages": [
                language.strip() for language in languages.split(",") if language.strip()
            ],
            "test_command": test_command,
        },
    }
    local_environment = {"editor": editor} if editor else {}
    return initialize(
        root,
        mode,
        profile,
        answers,
        reconfigure,
        local_environment,
    )
