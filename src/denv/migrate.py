from __future__ import annotations

import json
from pathlib import Path
import shutil

from .paths import config_path


OLD_AGENTS = """# Agent entry point

This repository uses the denv shared cognition pack. Before work, read in order:

1. `ops/PRINCIPLES.md`
2. `ops/WAYS_OF_WORKING.md`
3. `ops/decisions/INDEX.md` and relevant active decisions
4. `ops/memory/PROJECT.md`
5. `ops/sessions/CURRENT.md`

Project decisions override chat history until explicitly superseded. Never place
secrets in `ops/`. Agent-private transcripts and memory databases are not part
of denv.
"""


class MigrationError(RuntimeError):
    pass


def migrate_layout(root: Path, current_agents: str) -> list[str]:
    """Explicitly move a legacy pre-release instance into the current layout."""
    legacy = root / "ops"
    cognition = root / ".denv/cognition"
    messages: list[str] = []
    if legacy.exists():
        if cognition.exists():
            raise MigrationError(
                "both ops/ and .denv/cognition/ exist; merge them manually"
            )
        cognition.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(legacy), str(cognition))
        messages.append("moved ops/ to .denv/cognition/")

    path = config_path(root)
    config = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(config, dict):
        raise MigrationError("config.json must contain an object")
    changed = config.pop("ops_dir", None) is not None
    if config.get("cognition_dir") != ".denv/cognition":
        config["cognition_dir"] = ".denv/cognition"
        changed = True
    if changed:
        path.write_text(
            json.dumps(config, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        messages.append("updated config.json")

    agents = root / "AGENTS.md"
    if agents.is_file() and agents.read_text(encoding="utf-8") == OLD_AGENTS:
        agents.write_text(current_agents, encoding="utf-8")
        messages.append("updated stock AGENTS.md")

    vendor = root / ".denv/vendor"
    if vendor.exists():
        shutil.rmtree(vendor)
        messages.append("removed legacy vendor snapshot")
    return messages
