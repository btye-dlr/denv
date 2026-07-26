from __future__ import annotations

import json
from pathlib import Path
import tomllib
from typing import Any

from .merge import deep_merge
from .ops_seed import seed_ops
from .paths import CORE_ROOT, config_path, local_dir
from .secrets import find_secret_keys
from .vendor import refresh_pin


class InitError(RuntimeError):
    pass


def load_toml(path: Path) -> dict[str, Any]:
    with path.open("rb") as handle:
        return tomllib.load(handle)


def load_defaults(profile: str = "generic") -> dict[str, Any]:
    defaults = load_toml(CORE_ROOT / "defaults.toml")
    profile_path = CORE_ROOT / "profiles" / f"{profile}.toml"
    if not profile_path.is_file():
        raise InitError(f"unknown profile: {profile}")
    return deep_merge(defaults, load_toml(profile_path))


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    temporary.replace(path)


def _ensure_local_ignore(root: Path) -> None:
    ignore = root / ".gitignore"
    marker = "/.denv/local/"
    existing = ignore.read_text(encoding="utf-8") if ignore.exists() else ""
    lines = existing.splitlines()
    if marker not in lines and marker.lstrip("/") not in lines:
        content = existing
        if content and not content.endswith("\n"):
            content += "\n"
        ignore.write_text(content + marker + "\n", encoding="utf-8")


def initialize(
    root: Path,
    mode: str,
    profile: str = "generic",
    answers: dict[str, Any] | None = None,
    reconfigure: bool = False,
    local_environment: dict[str, Any] | None = None,
) -> dict[str, Any]:
    root = root.expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    destination = config_path(root)
    if destination.exists() and not reconfigure:
        raise InitError(f"{root} is already initialized; use setup --reconfigure")
    config = load_defaults(profile)
    if destination.exists():
        try:
            existing = json.loads(destination.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise InitError(f"cannot preserve existing config: {error}") from error
        if not isinstance(existing, dict):
            raise InitError("existing config must contain a JSON object")
        config = deep_merge(config, existing)
    if answers:
        config = deep_merge(config, answers)
    config.pop("ops_dir", None)
    config["cognition_dir"] = ".denv/cognition"
    config["mode"] = mode
    config["profile"] = profile
    config["setup_completed"] = True
    secret_keys = find_secret_keys(config)
    if secret_keys:
        raise InitError(
            "tracked config contains secret-shaped keys: " + ", ".join(secret_keys)
        )
    _write_json(destination, config)
    local = local_dir(root)
    local.mkdir(parents=True, exist_ok=True)
    env_path = local / "env.json"
    environment: dict[str, Any] = {}
    if env_path.is_file():
        try:
            existing_environment = json.loads(env_path.read_text(encoding="utf-8"))
            if isinstance(existing_environment, dict):
                environment.update(existing_environment)
        except (OSError, json.JSONDecodeError) as error:
            raise InitError(f"cannot preserve existing local environment: {error}") from error
    environment["core_path"] = str(CORE_ROOT)
    if local_environment:
        environment.update(local_environment)
    _write_json(env_path, environment)
    secrets_path = local / "secrets.json"
    if not secrets_path.exists():
        _write_json(secrets_path, {})
    user = local / "USER.md"
    if not user.exists():
        user.write_text(
            "# Local user preferences\n\nGitignored preferences for this ROOT.\n",
            encoding="utf-8",
        )
    _ensure_local_ignore(root)
    seed_ops(root)
    refresh_pin(root)
    return config
