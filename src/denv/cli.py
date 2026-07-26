from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any, Sequence

from . import __version__
from .discover import (
    DiscoveryError,
    nearest_root,
    read_config,
    resolve_config,
)
from .doctor import report
from .init import InitError, initialize, load_defaults
from .migrate import MigrationError, migrate_layout
from .ops_seed import has_legacy_ops, seed_ops
from .paths import config_path, local_dir
from .secrets import is_secret_key
from .setup import interactive_setup
from .vendor import refresh_pin


def _root(value: str | None) -> Path:
    return Path(value).expanduser().resolve() if value else Path.cwd().resolve()


def _add_root(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--root",
        help="ROOT to configure or inspect (default: current directory)",
    )


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        prog="denv",
        description="Clone-first development environment framework",
    )
    result.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    commands = result.add_subparsers(dest="command", required=True)

    init = commands.add_parser("init", help="non-interactively initialize a ROOT")
    _add_root(init)
    init.add_argument("--mode", choices=("umbrella", "project"), required=True)
    init.add_argument("--profile", default="generic")
    init.add_argument("--defaults", action="store_true")
    init.add_argument("--config", help="JSON answers file")

    setup = commands.add_parser("setup", help="interactively initialize a ROOT")
    _add_root(setup)
    setup.add_argument("--reconfigure", action="store_true")

    doctor = commands.add_parser("doctor", help="validate an instance")
    _add_root(doctor)

    status = commands.add_parser("status", help="show resolved instance status")
    _add_root(status)
    status.add_argument("--json", action="store_true")

    resolve = commands.add_parser("resolve", help="show effective configuration")
    _add_root(resolve)
    resolve.add_argument("--json", action="store_true")

    config = commands.add_parser("config", help="read or update nearest config")
    config_commands = config.add_subparsers(dest="config_command", required=True)
    get = config_commands.add_parser("get")
    get.add_argument("key")
    _add_root(get)
    set_value = config_commands.add_parser("set")
    set_value.add_argument("key")
    set_value.add_argument("value")
    _add_root(set_value)

    sync = commands.add_parser("sync-ops", help="seed missing cognition templates")
    _add_root(sync)

    pin = commands.add_parser("pin-refresh", help="refresh local core identity pin")
    _add_root(pin)
    vendor = commands.add_parser(
        "vendor-refresh", help="deprecated alias for pin-refresh"
    )
    _add_root(vendor)
    migrate = commands.add_parser(
        "migrate-layout", help="explicitly migrate a v0.1 instance layout"
    )
    _add_root(migrate)
    return result


def _load_answers(path: str | None) -> dict[str, Any]:
    if not path:
        return {}
    source = Path(path)
    try:
        value = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise InitError(f"cannot read answers file {source}: {error}") from error
    if not isinstance(value, dict):
        raise InitError("answers file must contain a JSON object")
    return value


def _dotted_get(value: dict[str, Any], dotted: str) -> Any:
    current: Any = value
    for key in dotted.split("."):
        if not isinstance(current, dict) or key not in current:
            raise KeyError(dotted)
        current = current[key]
    return current


def _dotted_set(value: dict[str, Any], dotted: str, new_value: Any) -> None:
    keys = dotted.split(".")
    current = value
    for key in keys[:-1]:
        child = current.setdefault(key, {})
        if not isinstance(child, dict):
            raise ValueError(f"{key} is not an object")
        current = child
    current[keys[-1]] = new_value


def _parse_value(raw: str) -> Any:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw


def _write_config(path: Path, value: dict[str, Any]) -> None:
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    temporary.replace(path)


def _status(start: Path) -> dict[str, Any]:
    root = nearest_root(start)
    _, _, chain = resolve_config(start, load_defaults())
    pin_path = root / ".denv/pin.json"
    pin = json.loads(pin_path.read_text()) if pin_path.is_file() else None
    legacy = has_legacy_ops(root)
    return {
        "root": str(root),
        "chain": [str(item) for item in chain],
        "pin": pin,
        "cognition_present": (root / ".denv/cognition").is_dir(),
        "session_packet_present": (
            root / ".denv/cognition/sessions/CURRENT.md"
        ).is_file(),
        "legacy_layout": legacy,
        "migration_hint": (
            "run `denv migrate-layout`" if legacy else None
        ),
    }


def _local_core(root: Path) -> Path:
    env_path = local_dir(root) / "env.json"
    environment = json.loads(env_path.read_text(encoding="utf-8"))
    return Path(environment["core_path"]).expanduser().resolve()


def main(argv: Sequence[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        start = _root(getattr(args, "root", None))
        if args.command == "init":
            config = initialize(
                start,
                args.mode,
                args.profile,
                _load_answers(args.config),
            )
            print(f"Configured this denv instance at {start} ({args.mode})")
            return 0
        if args.command == "setup":
            interactive_setup(start, args.reconfigure)
            print(f"Configured this denv instance at {start}")
            return 0
        if args.command == "doctor":
            code, output = report(start)
            print(output)
            return code
        if args.command == "status":
            value = _status(start)
            print(json.dumps(value, indent=2) if args.json else _format_status(value))
            return 0
        if args.command == "resolve":
            effective, provenance, chain = resolve_config(start, load_defaults())
            value = {
                "effective": effective,
                "provenance": provenance,
                "chain": [str(item) for item in chain],
            }
            if args.json:
                print(json.dumps(value, indent=2, sort_keys=True))
            else:
                print(json.dumps(effective, indent=2, sort_keys=True))
                print("\nProvenance:")
                for key, source in sorted(provenance.items()):
                    print(f"{key}: {source}")
            return 0
        if args.command == "config":
            root = nearest_root(start)
            path = config_path(root)
            value = read_config(path)
            if args.config_command == "get":
                selected = _dotted_get(value, args.key)
                print(json.dumps(selected) if not isinstance(selected, str) else selected)
                return 0
            if any(is_secret_key(key) for key in args.key.split(".")):
                raise ValueError(
                    "secret-shaped keys must be written to .denv/local/secrets.json"
                )
            _dotted_set(value, args.key, _parse_value(args.value))
            _write_config(path, value)
            print(f"Updated {args.key} in {path}")
            return 0
        if args.command == "sync-ops":
            root = nearest_root(start)
            if has_legacy_ops(root):
                print("Legacy ops/ layout detected; run `denv migrate-layout`.")
                return 0
            created = seed_ops(root)
            print(f"Seeded {len(created)} missing cognition file(s) at {root}")
            return 0
        if args.command in {"pin-refresh", "vendor-refresh"}:
            root = nearest_root(start)
            if args.command == "vendor-refresh":
                print(
                    "denv: warning: vendor-refresh is deprecated; use pin-refresh",
                    file=sys.stderr,
                )
            refresh_pin(root, _local_core(root))
            print(f"Refreshed core pin at {root}")
            return 0
        if args.command == "migrate-layout":
            root = nearest_root(start)
            core = _local_core(root)
            agents_template = (core / "AGENTS.md").read_text(encoding="utf-8")
            messages = migrate_layout(root, agents_template)
            seed_ops(root)
            refresh_pin(root, core)
            print("; ".join(messages) if messages else "Layout already current")
            return 0
    except (
        DiscoveryError,
        InitError,
        MigrationError,
        KeyError,
        OSError,
        ValueError,
    ) as error:
        print(f"denv: error: {error}", file=sys.stderr)
        return 2
    return 2


def _format_status(value: dict[str, Any]) -> str:
    pin = value["pin"] or {}
    lines = [
        f"ROOT: {value['root']}",
        f"Chain: {' -> '.join(value['chain'])}",
        f"Pin SHA: {pin.get('sha') or 'uncommitted'}",
        f"Pin dirty: {pin.get('dirty', 'unknown')}",
        "Cognition: "
        + ("present" if value["cognition_present"] else "missing"),
        "Session packet: "
        + ("present" if value["session_packet_present"] else "missing"),
    ]
    if value["migration_hint"]:
        lines.append(f"Migration: {value['migration_hint']}")
    return "\n".join(lines)
