from __future__ import annotations

from datetime import date
import json
from pathlib import Path
import re
from typing import Any

from .discover import DiscoveryError, read_config
from .paths import CORE_ROOT, config_path


class SpecError(ValueError):
    pass


STATUSES = ("draft", "approved", "active", "done", "abandoned")
RIGORS = ("light", "workflow")
GATE_STATUSES = frozenset({"approved", "active"})
TRANSITIONS = {
    "draft": frozenset({"approved", "abandoned"}),
    "approved": frozenset({"active", "abandoned"}),
    "active": frozenset({"done", "abandoned"}),
    "done": frozenset(),
    "abandoned": frozenset(),
}
IDLE_GOALS = frozenset({"", "No active goal."})
WORKFLOW_ARTIFACTS = ("plan", "tasks")
SPEC_FILE_RE = re.compile(r"^(\d{4})-.+\.md$")
INDEX_ROW_RE = re.compile(
    r"^\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|$"
)
DEFAULT_SPECS_DIR = ".denv/specs"

INDEX_HEADER = """# Spec index

Record tracked specs for this ROOT. `denv spec new` and `denv spec status` maintain this table.

| ID | Status | Rigor | Title |
| --- | --- | --- | --- |
"""


class SpecRecord:
    def __init__(
        self,
        spec_id: str,
        title: str,
        status: str,
        rigor: str,
        artifacts: dict[str, str],
        path: Path,
    ) -> None:
        self.id = spec_id
        self.title = title
        self.status = status
        self.rigor = rigor
        self.artifacts = artifacts
        self.path = path


class IndexRow:
    def __init__(self, spec_id: str, status: str, rigor: str, title: str) -> None:
        self.id = spec_id
        self.status = status
        self.rigor = rigor
        self.title = title


def resolve_specs_dir(root: Path) -> tuple[Path, str | None]:
    """Return the specs directory for this ROOT, or an error if config is unsafe."""
    relative = DEFAULT_SPECS_DIR
    path = config_path(root)
    if path.is_file():
        try:
            value = read_config(path).get("specs_dir", relative)
        except DiscoveryError as error:
            return root / relative, str(error)
        if not isinstance(value, str) or not value.strip():
            return root / relative, f"invalid specs_dir: {value!r}"
        relative = value.strip()
        parts = Path(relative).parts
        if Path(relative).is_absolute() or ".." in parts:
            return root / DEFAULT_SPECS_DIR, f"invalid specs_dir: {relative}"
    specs_dir = (root / relative).resolve()
    if not specs_dir.is_relative_to(root.resolve()):
        return root / DEFAULT_SPECS_DIR, f"invalid specs_dir: {relative}"
    return specs_dir, None


def create_spec(root: Path, title: str) -> Path:
    specs_dir, _error = _require_specs_dir(root)
    cleaned = _clean_title(title)
    index_path = _require_index(specs_dir)
    spec_id = _next_id(specs_dir, index_path)
    destination = specs_dir / f"{spec_id}-{_slug(cleaned)}.md"
    if destination.exists():
        raise SpecError(f"spec file already exists: {destination.name}")
    template = (CORE_ROOT / "setup/spec-template.md").read_text(encoding="utf-8")
    body = template.replace("{{title}}", cleaned).replace("{{id}}", spec_id)
    if not body.endswith("\n"):
        body += "\n"
    _atomic_write(destination, _render_new_spec(spec_id, cleaned, body))
    rows = _read_index(index_path)
    rows.append(IndexRow(spec_id, "draft", "light", cleaned))
    _write_index(index_path, rows)
    return destination


def format_spec_list(root: Path) -> str:
    specs_dir, _error = _require_specs_dir(root)
    rows = _read_index(_require_index(specs_dir))
    if not rows:
        return "No specs."
    return "\n".join(
        f"{row.id}  {row.status}  {row.rigor}  {row.title}" for row in rows
    )


def transition_status(root: Path, token: str, status: str) -> SpecRecord:
    if status not in STATUSES:
        raise SpecError(f"unknown status: {status}")
    specs_dir, _error = _require_specs_dir(root)
    index_path = _require_index(specs_dir)
    spec = _spec_for_token(specs_dir, token)
    allowed = TRANSITIONS.get(spec.status, frozenset())
    if status not in allowed:
        raise SpecError(f"illegal status transition: {spec.status} -> {status}")
    _rewrite_status(spec.path, status)
    spec.status = status
    rows = _read_index(index_path)
    replaced = False
    for row in rows:
        if row.id == spec.id:
            row.status = status
            row.rigor = spec.rigor
            row.title = spec.title
            replaced = True
    if not replaced:
        rows.append(IndexRow(spec.id, status, spec.rigor, spec.title))
    _write_index(index_path, rows)
    return spec


def validate_instance(root: Path, *, legacy: bool = False) -> list[str]:
    """Return spec and session-gate errors for one ROOT."""
    errors: list[str] = []
    specs_dir, location_error = resolve_specs_dir(root)
    if location_error and not legacy:
        return [location_error]
    if location_error:
        return errors

    session = (
        root / "ops/sessions/CURRENT.md"
        if legacy
        else root / ".denv/cognition/sessions/CURRENT.md"
    )
    records = _load_records(root, specs_dir, errors) if specs_dir.is_dir() else []
    index_path = specs_dir / "INDEX.md"
    rows: list[IndexRow] = []
    if index_path.is_file():
        try:
            rows = _read_index(index_path)
        except OSError as error:
            errors.append(f"cannot read {_rel(root, index_path)}: {error}")

    if index_path.is_file() and (records or rows):
        errors.extend(_index_errors(root, index_path, records, rows))
    elif records:
        errors.extend(_artifact_errors(root, records))
    if session.is_file():
        errors.extend(_session_errors(root, session, records, rows, index_path))
    return errors


def _require_specs_dir(root: Path) -> tuple[Path, None]:
    specs_dir, error = resolve_specs_dir(root)
    if error:
        raise SpecError(error)
    return specs_dir, None


def _require_index(specs_dir: Path) -> Path:
    index_path = specs_dir / "INDEX.md"
    if not index_path.is_file():
        raise SpecError(f"missing {index_path}; run denv sync-ops")
    return index_path


def _clean_title(title: str) -> str:
    cleaned = title.strip()
    if not cleaned or "\n" in title or "\r" in title:
        raise SpecError("title must be a single non-empty line")
    if "|" in cleaned:
        raise SpecError("title must not contain '|'")
    return cleaned


def _slug(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    slug = re.sub(r"-{2,}", "-", slug)
    if len(slug) > 48:
        slug = slug[:48].rstrip("-")
    return slug or "spec"


def _next_id(specs_dir: Path, index_path: Path) -> str:
    highest = 0
    if specs_dir.is_dir():
        for path in specs_dir.glob("*.md"):
            match = SPEC_FILE_RE.match(path.name)
            if match:
                highest = max(highest, int(match.group(1)))
    for row in _read_index(index_path):
        if re.fullmatch(r"\d{4}", row.id):
            highest = max(highest, int(row.id))
    if highest >= 9999:
        raise SpecError("spec id space is exhausted")
    return f"{highest + 1:04d}"


def _render_new_spec(spec_id: str, title: str, body: str) -> str:
    return (
        "---\n"
        f"id: {json.dumps(spec_id)}\n"
        f"title: {json.dumps(title)}\n"
        "status: draft\n"
        "rigor: light\n"
        "artifacts: {}\n"
        "---\n\n"
        f"{body}"
    )


def _spec_for_token(specs_dir: Path, token: str) -> SpecRecord:
    errors: list[str] = []
    records = _records_in(specs_dir, errors)
    if errors:
        raise SpecError(errors[0])
    matches = _match_records(records, token)
    if len(matches) != 1:
        raise SpecError(f"unknown spec: {token}")
    return matches[0]


def _records_in(specs_dir: Path, errors: list[str]) -> list[SpecRecord]:
    records: list[SpecRecord] = []
    for path in sorted(specs_dir.glob("*.md")):
        if path.name == "INDEX.md":
            continue
        try:
            records.append(_read_spec(path))
        except (OSError, SpecError) as error:
            errors.append(f"{path.name}: {error}")
    return records


def _load_records(root: Path, specs_dir: Path, errors: list[str]) -> list[SpecRecord]:
    records: list[SpecRecord] = []
    for path in sorted(specs_dir.glob("*.md")):
        if path.name == "INDEX.md":
            continue
        try:
            records.append(_read_spec(path))
        except (OSError, SpecError) as error:
            errors.append(f"{_rel(root, path)}: {error}")
    return records


def _read_spec(path: Path) -> SpecRecord:
    meta, _body = _split_document(path.read_text(encoding="utf-8"))
    spec_id = meta.get("id")
    title = meta.get("title")
    status = meta.get("status")
    rigor = meta.get("rigor")
    artifacts = meta.get("artifacts", {})
    if not isinstance(spec_id, str) or not re.fullmatch(r"\d{4}", spec_id):
        raise SpecError("frontmatter id must be a four-digit string")
    if not isinstance(title, str) or not title.strip():
        raise SpecError("frontmatter title must be a non-empty string")
    if status not in STATUSES:
        raise SpecError(f"frontmatter status must be one of: {', '.join(STATUSES)}")
    if rigor not in RIGORS:
        raise SpecError(f"frontmatter rigor must be one of: {', '.join(RIGORS)}")
    if not isinstance(artifacts, dict) or any(
        not isinstance(key, str) or not isinstance(value, str)
        for key, value in artifacts.items()
    ):
        raise SpecError("frontmatter artifacts must map names to paths")
    match = SPEC_FILE_RE.match(path.name)
    if not match or match.group(1) != spec_id:
        raise SpecError("spec filename must start with its frontmatter id")
    return SpecRecord(spec_id, title, status, rigor, dict(artifacts), path)


def _split_document(text: str) -> tuple[dict[str, Any], str]:
    if not text.startswith("---\n"):
        raise SpecError("missing frontmatter")
    end = text.find("\n---\n", 4)
    if end < 0:
        raise SpecError("unterminated frontmatter")
    return _parse_frontmatter(text[4:end]), text[end + 5 :]


def _parse_frontmatter(block: str) -> dict[str, Any]:
    data: dict[str, Any] = {}
    lines = block.splitlines()
    index = 0
    while index < len(lines):
        line = lines[index]
        if not line.strip() or line.lstrip().startswith("#"):
            index += 1
            continue
        if line[0] in {" ", "\t"}:
            raise SpecError(f"unexpected indent in frontmatter: {line!r}")
        if ":" not in line:
            raise SpecError(f"invalid frontmatter line: {line!r}")
        key, raw = line.split(":", 1)
        key = key.strip()
        raw = raw.strip()
        index += 1
        if raw == "{}":
            data[key] = {}
            continue
        if raw == "":
            nested: dict[str, str] = {}
            while index < len(lines) and lines[index].startswith("  "):
                child = lines[index][2:]
                if child.startswith(" ") or ":" not in child:
                    raise SpecError(f"invalid frontmatter line: {lines[index]!r}")
                child_key, child_value = child.split(":", 1)
                nested[child_key.strip()] = _unquote(child_value.strip())
                index += 1
            data[key] = nested
            continue
        data[key] = _unquote(raw)
    return data


def _unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        quote = value[0]
        inner = value[1:-1]
        return inner.replace("\\\\", "\0").replace(f"\\{quote}", quote).replace("\0", "\\")
    return value


def _read_index(path: Path) -> list[IndexRow]:
    rows: list[IndexRow] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        match = INDEX_ROW_RE.match(line.strip())
        if not match:
            continue
        spec_id, status, rigor, title = (part.strip() for part in match.groups())
        if spec_id in {"ID", "---"} or set(spec_id) <= {"-"}:
            continue
        rows.append(IndexRow(spec_id, status, rigor, title))
    return rows


def _write_index(path: Path, rows: list[IndexRow]) -> None:
    lines = [INDEX_HEADER.rstrip("\n")]
    for row in rows:
        lines.append(f"| {row.id} | {row.status} | {row.rigor} | {row.title} |")
    _atomic_write(path, "\n".join(lines) + "\n")


def _rewrite_status(path: Path, status: str) -> None:
    text = path.read_text(encoding="utf-8")
    meta_end = text.find("\n---\n", 4)
    if not text.startswith("---\n") or meta_end < 0:
        raise SpecError(f"{path.name} is missing frontmatter")
    frontmatter = text[4:meta_end]
    updated, count = re.subn(
        r"(?m)^status:.*$",
        f"status: {status}",
        frontmatter,
        count=1,
    )
    if count != 1:
        raise SpecError(f"{path.name} is missing a status field")
    _atomic_write(path, f"---\n{updated}\n---\n{text[meta_end + 5 :]}")


def _index_errors(
    root: Path,
    index_path: Path,
    records: list[SpecRecord],
    rows: list[IndexRow],
) -> list[str]:
    errors: list[str] = []
    by_id = {row.id: row for row in rows}
    seen: set[str] = set()
    for spec in records:
        seen.add(spec.id)
        row = by_id.get(spec.id)
        if row is None:
            errors.append(f"spec {spec.id} is not listed in {_rel(root, index_path)}")
        elif (row.status, row.rigor, row.title) != (spec.status, spec.rigor, spec.title):
            errors.append(f"spec {spec.id} does not match the index")
    errors.extend(_artifact_errors(root, records))
    for row in rows:
        if row.id not in seen:
            errors.append(f"index lists {row.id} but no spec file exists")
    return errors


def _artifact_errors(root: Path, records: list[SpecRecord]) -> list[str]:
    errors: list[str] = []
    for spec in records:
        if spec.rigor == "workflow":
            for key in WORKFLOW_ARTIFACTS:
                if not spec.artifacts.get(key, "").strip():
                    errors.append(
                        f"spec {spec.id} workflow rigor requires artifact {key}"
                    )
        for key, relative in spec.artifacts.items():
            try:
                artifact = _artifact_path(spec.path.parent, relative)
            except SpecError as error:
                errors.append(f"spec {spec.id} {error}")
                continue
            if not artifact.is_file():
                errors.append(
                    f"spec {spec.id} missing artifact {key}: {_rel(root, artifact)}"
                )
    return errors


def _session_errors(
    root: Path,
    session: Path,
    records: list[SpecRecord],
    rows: list[IndexRow],
    index_path: Path,
) -> list[str]:
    try:
        sections = _sections(session.read_text(encoding="utf-8"))
    except OSError as error:
        return [f"cannot read {_rel(root, session)}: {error}"]
    goal = sections.get("Goal", "")
    if goal in IDLE_GOALS:
        return []
    token = _spec_token(sections.get("Spec"))
    if token is None:
        return ["active session goal requires an approved spec"]
    matches = _match_records(records, token)
    if len(matches) != 1:
        return [f"session spec {token} was not found"]
    spec = matches[0]
    if spec.status not in GATE_STATUSES:
        return [
            f"session spec {spec.id} is {spec.status}; expected approved or active"
        ]
    if not any(row.id == spec.id for row in rows):
        return [f"session spec {spec.id} is not listed in {_rel(root, index_path)}"]
    return []


IDLE_GOAL_TEXT = "No active goal."
IDLE_SPEC_TEXT = "None."


class SessionView:
    def __init__(
        self,
        root: Path,
        goal: str,
        spec: SpecRecord | None,
        token: str | None,
    ) -> None:
        self.root = root
        self.goal = goal
        self.spec = spec
        self.token = token

    @property
    def idle(self) -> bool:
        return self.goal in IDLE_GOALS


def session_path(root: Path) -> Path:
    return root / ".denv/cognition/sessions/CURRENT.md"


def read_session(root: Path) -> SessionView:
    path = session_path(root)
    if not path.is_file():
        raise SpecError(f"missing {_rel(root, path)}; run denv sync-ops")
    sections = _sections(path.read_text(encoding="utf-8"))
    goal = sections.get("Goal", "")
    token = _spec_token(sections.get("Spec"))
    spec: SpecRecord | None = None
    if token is not None:
        specs_dir, error = resolve_specs_dir(root)
        if error is None and specs_dir.is_dir():
            matches = _match_records(_records_in(specs_dir, []), token)
            if len(matches) == 1:
                spec = matches[0]
    return SessionView(root, goal, spec, token)


def format_session(view: SessionView) -> str:
    lines = [f"ROOT: {view.root}"]
    if view.idle:
        lines.append(f"Goal: {IDLE_GOAL_TEXT}")
        lines.append("Spec: none")
        return "\n".join(lines)
    lines.append(f"Goal: {view.goal.splitlines()[0] if view.goal else ''}")
    if view.spec is None:
        lines.append(f"Spec: {view.token or 'none'} (not found)")
    else:
        lines.append(
            f"Spec: {view.spec.id} {view.spec.status} {view.spec.rigor} "
            f"{view.spec.title}"
        )
    return "\n".join(lines)


def begin_session(root: Path, goal: str, token: str) -> SpecRecord:
    cleaned = goal.strip()
    if not cleaned or "\n" in goal or "\r" in goal:
        raise SpecError("goal must be a single non-empty line")
    if cleaned in IDLE_GOALS:
        raise SpecError(f"goal must not be {IDLE_GOAL_TEXT!r}; use session end")
    specs_dir, _error = _require_specs_dir(root)
    index_path = _require_index(specs_dir)
    spec = _spec_for_token(specs_dir, token)
    if spec.status not in GATE_STATUSES:
        raise SpecError(
            f"spec {spec.id} is {spec.status}; expected approved or active. "
            f"A human approves it with: denv spec status {spec.id} approved"
        )
    if not any(row.id == spec.id for row in _read_index(index_path)):
        raise SpecError(f"spec {spec.id} is not listed in {_rel(root, index_path)}")
    _rewrite_session(root, cleaned, spec.id, "active")
    return spec


def end_session(root: Path) -> None:
    _rewrite_session(root, IDLE_GOAL_TEXT, IDLE_SPEC_TEXT, "idle")


def _rewrite_session(root: Path, goal: str, spec: str, status: str) -> None:
    path = session_path(root)
    if not path.is_file():
        raise SpecError(f"missing {_rel(root, path)}; run denv sync-ops")
    text = path.read_text(encoding="utf-8")
    text = _replace_section(text, "Goal", goal)
    text = _replace_section(text, "Spec", spec)
    text = re.sub(r"(?m)^- Status: .*$", f"- Status: {status}", text, count=1)
    text = re.sub(
        r"(?m)^- Updated: .*$",
        f"- Updated: {_today()}",
        text,
        count=1,
    )
    _atomic_write(path, text)


def _replace_section(text: str, name: str, body: str) -> str:
    lines = text.splitlines()
    heading = f"## {name}"
    start = next((i for i, line in enumerate(lines) if line.strip() == heading), None)
    replacement = [heading, "", body, ""]
    if start is None:
        if lines and lines[-1].strip():
            lines.append("")
        return "\n".join(lines + replacement).rstrip("\n") + "\n"
    stop = start + 1
    while stop < len(lines) and not lines[stop].startswith("## "):
        stop += 1
    return "\n".join(lines[:start] + replacement + lines[stop:]).rstrip("\n") + "\n"


def _today() -> str:
    return date.today().isoformat()


def _sections(text: str) -> dict[str, str]:
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for line in text.splitlines():
        if line.startswith("## "):
            current = line[3:].strip()
            sections[current] = []
            continue
        if current is not None:
            sections[current].append(line)
    return {name: "\n".join(lines).strip() for name, lines in sections.items()}


def _spec_token(section: str | None) -> str | None:
    if section is None or not section.strip():
        return None
    token = section.strip().splitlines()[0].strip()
    if token.lower().startswith("spec:"):
        token = token.split(":", 1)[1].strip()
    if token.rstrip(".").lower() == "none":
        return None
    return token or None


def _match_records(records: list[SpecRecord], token: str) -> list[SpecRecord]:
    stem = token.removesuffix(".md")
    return [spec for spec in records if spec.id == token or spec.path.stem == stem]


def _artifact_path(specs_dir: Path, relative: str) -> Path:
    if not relative.strip() or Path(relative).is_absolute() or ".." in Path(relative).parts:
        raise SpecError(f"artifact path escapes specs directory: {relative}")
    path = (specs_dir / relative).resolve()
    if not path.is_relative_to(specs_dir.resolve()):
        raise SpecError(f"artifact path escapes specs directory: {relative}")
    return path


def _rel(root: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path)


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(path)
