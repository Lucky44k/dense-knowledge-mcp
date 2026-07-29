"""Setup and diagnostics for local MMP installations."""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .codec import parse
from .config import UserConfig, config_path, load_config, save_config
from .errors import ValidationError
from .validation import package_issues


def setup_environment(
    memory: str | os.PathLike[str],
    *,
    lm_studio_config: str | os.PathLike[str] | None = None,
    force: bool = False,
    dry_run: bool = False,
) -> str:
    root = Path(memory).expanduser().resolve()
    client_path = (
        Path(lm_studio_config).expanduser().resolve()
        if lm_studio_config is not None
        else None
    )
    current = load_config()
    next_config = UserConfig(
        root=root,
        lm_studio_config=client_path or current.lm_studio_config,
    )

    lines = ["MMP setup", f"Memory: {root}", f"Config: {config_path()}"]
    if client_path is not None:
        configure_lm_studio(client_path, root, force=force, dry_run=True)
    if dry_run:
        lines.append("Mode: dry run")
    else:
        root.mkdir(parents=True, exist_ok=True)
        save_config(next_config)

    if client_path is not None:
        action, backup = configure_lm_studio(
            client_path, root, force=force, dry_run=dry_run
        )
        lines.append(f"LM Studio: {action} {client_path}")
        if backup is not None:
            lines.append(f"Backup: {backup}")
    else:
        lines.append("LM Studio: skipped")
    lines.append("Next: mmp doctor")
    return "\n".join(lines)


def configure_lm_studio(
    path: Path,
    root: Path,
    *,
    force: bool = False,
    dry_run: bool = False,
) -> tuple[str, Path | None]:
    document: dict[str, Any] = {}
    if path.exists():
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValidationError(f"cannot read LM Studio config {path}: {exc}") from exc
        if not isinstance(loaded, dict):
            raise ValidationError("LM Studio config must contain a JSON object")
        document = loaded

    servers = document.setdefault("mcpServers", {})
    if not isinstance(servers, dict):
        raise ValidationError("LM Studio mcpServers must be a JSON object")
    desired = {
        "command": sys.executable,
        "args": [
            "-m",
            "mmp.server",
            "--root",
            str(root),
            "--transport",
            "stdio",
        ],
    }
    existing = servers.get("mmp")
    if existing == desired:
        return "already configured:", None
    if existing is not None and not force:
        raise ValidationError(
            "LM Studio already has an mmp server; inspect it or retry with --force"
        )
    servers["mmp"] = desired
    if dry_run:
        return "would update:", None

    path.parent.mkdir(parents=True, exist_ok=True)
    backup = _backup(path) if path.exists() else None
    _write_json(path, document)
    return ("updated:" if backup else "created:"), backup


def doctor(
    root: Path,
    *,
    lm_studio_config: Path | None = None,
) -> str:
    checks: list[tuple[str, str]] = []
    checks.append(
        (
            "PASS" if sys.version_info >= (3, 11) else "ERROR",
            f"Python {sys.version_info.major}.{sys.version_info.minor}",
        )
    )
    checks.append(
        (
            "PASS" if importlib.util.find_spec("mcp") else "ERROR",
            "MCP server dependency",
        )
    )
    checks.append(
        (
            "PASS" if importlib.util.find_spec("langid") else "WARN",
            "English language detector",
        )
    )
    if root.is_dir():
        writable = os.access(root, os.W_OK)
        checks.append(("PASS" if writable else "ERROR", f"Memory directory {root}"))
    else:
        checks.append(("ERROR", f"Memory directory missing: {root}"))

    packages = sorted(
        path for path in root.glob("*.mmp") if path.name != "_catalog.mmp"
    ) if root.is_dir() else []
    for path in packages:
        try:
            package = parse(path.read_text(encoding="utf-8"))
            issues = package_issues(package)
        except (OSError, ValidationError) as exc:
            issues = [str(exc)]
        checks.append(
            (
                "PASS" if not issues else "ERROR",
                f"{path.name}: valid" if not issues else f"{path.name}: {issues[0]}",
            )
        )
    if not packages:
        checks.append(("PASS", "No knowledge packages yet"))

    client = lm_studio_config or load_config().lm_studio_config
    if client is not None:
        checks.append(_check_lm_studio(client, root))

    passed = sum(level == "PASS" for level, _ in checks)
    warnings = sum(level == "WARN" for level, _ in checks)
    errors = sum(level == "ERROR" for level, _ in checks)
    rendered = ["MMP doctor"]
    rendered.extend(f"{level:5} {message}" for level, message in checks)
    rendered.append(
        f"Summary: {passed} passed, {warnings} warning(s), {errors} error(s)"
    )
    return "\n".join(rendered)


def _check_lm_studio(path: Path, root: Path) -> tuple[str, str]:
    if not path.is_file():
        return "ERROR", f"LM Studio config missing: {path}"
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
        server = document["mcpServers"]["mmp"]
        args = server["args"]
    except (OSError, json.JSONDecodeError, KeyError, TypeError):
        return "ERROR", f"LM Studio config has no usable mmp server: {path}"
    if str(root) not in args:
        return "WARN", f"LM Studio uses a different memory directory: {path}"
    return "PASS", f"LM Studio config {path}"


def _backup(path: Path) -> Path:
    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    backup = path.with_name(f"{path.name}.bak-{stamp}")
    counter = 2
    while backup.exists():
        backup = path.with_name(f"{path.name}.bak-{stamp}-{counter}")
        counter += 1
    shutil.copy2(path, backup)
    return backup


def _write_json(path: Path, document: dict[str, Any]) -> None:
    fd, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(document, handle, indent=2, ensure_ascii=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
