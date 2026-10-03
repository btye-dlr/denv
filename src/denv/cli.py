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
from .doctor import core_identity, report
from .guide import guide_text
from .init import InitError, initialize, load_defaults
from .install import InstallError, install, self_update, uninstall
from .migrate import MigrationError, migrate_layout
from .ops_seed import has_legacy_ops, seed_ops
from .paths import config_path, local_dir
from .secrets import is_secret_key
from .setup import interactive_setup
from .specs import (
    SpecError,
    begin_session,
    create_spec,
    end_session,
    format_session,
    format_spec_list,
    read_session,
    transition_status,
)
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
        epilog="Run `denv guide` for the working loop.",
    )
    result.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    commands = result.add_subparsers(dest="command", required=True)

    commands.add_parser("guide", help="print the working loop for humans and agents")

    init = commands.add_parser("init", help="non-interactively initialize a ROOT")
    _add_root(init)
    init.add_argument("--mode", choices=("umbrella", "project"), required=True)
    init.add_argument("--profile", default="generic")
    init.add_argument("--defaults", action="store_true")
    init.add_argument("--config", help="JSON answers file")

    setup = commands.add_parser("setup", help="interactively initialize a ROOT")
    _add_root(setup)
    setup.add_argument("--reconfigure", action="store_true")

    doctor = commands.add_parser(
        "doctor",
        help="validate config, pin, cognition, specs, and secret hygiene",
    )
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

    spec = commands.add_parser("spec", help="create, list, and transition specs")
    spec_commands = spec.add_subparsers(dest="spec_command", required=True)
    new_spec = spec_commands.add_parser("new", help="draft a light spec")
    new_spec.add_argument("title", help="single-line spec title")
    _add_root(new_spec)
    list_specs = spec_commands.add_parser("list", help="list specs from the index")
    _add_root(list_specs)
    set_status = spec_commands.add_parser("status", help="transition a spec status")
    set_status.add_argument("spec_id")
    set_status.add_argument(
        "status",
        choices=("draft", "approved", "active", "done", "abandoned"),
    )
    _add_root(set_status)

    session = commands.add_parser(
        "session", help="show, begin, or end the session packet goal"
    )
    session_commands = session.add_subparsers(dest="session_command", required=True)
    show = session_commands.add_parser("show", help="show goal and linked spec")
    _add_root(show)
    begin = session_commands.add_parser(
        "begin", help="set the goal and link an approved spec"
    )
    begin.add_argument("--goal", required=True, help="single-line session goal")
    begin.add_argument("--spec", required=True, help="spec id or filename stem")
    _add_root(begin)
    end = session_commands.add_parser("end", help="return the session to idle")
    _add_root(end)

    install_cmd = commands.add_parser(
        "install", help="symlink bin/denv onto PATH (user or --system)"
    )
    _add_bin_dir(install_cmd)
    install_cmd.add_argument(
        "--force", action="store_true", help="replace a foreign symlink"
    )
    uninstall_cmd = commands.add_parser(
        "uninstall", help="remove the denv symlink installed by this checkout"
    )
    _add_bin_dir(uninstall_cmd)
    update = commands.add_parser(
        "self-update", help="update this checkout with git (ff-only or --ref)"
    )
    update.add_argument("--ref", help="tag or branch to check out instead of pulling")
    return result


def _add_bin_dir(parser: argparse.ArgumentParser) -> None:
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--system", action="store_true", help="use /usr/local/bin instead of ~/.local/bin"
    )
    group.add_argument("--bin-dir", help="explicit bin directory")


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
        "core": core_identity(root),
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
        if args.command == "guide":
            print(guide_text())
            return 0
        if args.command == "install":
            for line in install(args.system, args.bin_dir, args.force):
                print(line)
            return 0
        if args.command == "uninstall":
            print(uninstall(args.system, args.bin_dir))
            return 0
        if args.command == "self-update":
            for line in self_update(args.ref):
                print(line)
            return 0
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
            print(f"Seeded {len(created)} missing template file(s) at {root}")
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
        if args.command == "spec":
            root = nearest_root(start)
            if args.spec_command == "new":
                created = create_spec(root, args.title)
                print(f"Created {created.relative_to(root)} (draft)")
                return 0
            if args.spec_command == "list":
                print(format_spec_list(root))
                return 0
            if args.spec_command == "status":
                updated = transition_status(root, args.spec_id, args.status)
                print(f"Updated {updated.id} status to {args.status}")
                return 0
        if args.command == "session":
            root = nearest_root(start)
            if args.session_command == "show":
                print(format_session(read_session(root)))
                return 0
            if args.session_command == "begin":
                linked = begin_session(root, args.goal, args.spec)
                print(f"Session active at {root}; spec {linked.id} ({linked.status})")
                return 0
            if args.session_command == "end":
                end_session(root)
                print(f"Session idle at {root}")
                return 0
    except (
        DiscoveryError,
        InitError,
        InstallError,
        MigrationError,
        SpecError,
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
        f"Pin version: {pin.get('semver') or 'unknown'}",
        f"Pin version: {pin.get('semver') or 'unknown'}",
        f"Pin SHA: {pin.get('sha') or 'uncommitted'}",
        f"Pin dirty: {pin.get('dirty', 'unknown')}",
        _format_core(value.get("core")),
        _format_core(value.get("core")),
        "Cognition: "
        + ("present" if value["cognition_present"] else "missing"),
        "Session packet: "
        + ("present" if value["session_packet_present"] else "missing"),
    ]
    if value["migration_hint"]:
        lines.append(f"Migration: {value['migration_hint']}")
    return "\n".join(lines)


def _format_core(core: dict[str, Any] | None) -> str:
    if core is None:
        return "Core: unknown (no .denv/local/env.json)"
    if not core.get("present"):
        return f"Core: {core['path']} (missing VERSION)"
    sha = core.get("sha") or "uncommitted"
    return f"Core: {core['semver']} {sha} at {core['path']}"


def _format_core(core: dict[str, Any] | None) -> str:
    if core is None:
        return "Core: unknown (no .denv/local/env.json)"
    if not core.get("present"):
        return f"Core: {core['path']} (missing VERSION)"
    sha = core.get("sha") or "uncommitted"
    return f"Core: {core['semver']} {sha} at {core['path']}"
