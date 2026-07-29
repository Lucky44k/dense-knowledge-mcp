"""User configuration and path resolution for MMP."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import tomllib
from dataclasses import dataclass
from pathlib import Path

from .errors import ValidationError


@dataclass(frozen=True)
class UserConfig:
    root: Path | None = None
    lm_studio_config: Path | None = None


def config_path() -> Path:
    override = os.environ.get("MMP_CONFIG")
    if override:
        return Path(override).expanduser().resolve()
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "mmp" / "config.toml"


def default_memory_path() -> Path:
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return (base / "mmp" / "memory").resolve()


def load_config(path: Path | None = None) -> UserConfig:
    path = path or config_path()
    if not path.exists():
        return UserConfig()
    try:
        raw = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise ValidationError(f"cannot read config {path}: {exc}") from exc

    root = raw.get("root")
    clients = raw.get("clients", {})
    lm_studio = clients.get("lm_studio") if isinstance(clients, dict) else None
    if root is not None and not isinstance(root, str):
        raise ValidationError(f"config root must be a string: {path}")
    if lm_studio is not None and not isinstance(lm_studio, str):
        raise ValidationError(f"clients.lm_studio must be a string: {path}")
    return UserConfig(
        root=_configured_path(root, path) if root else None,
        lm_studio_config=_configured_path(lm_studio, path) if lm_studio else None,
    )


def save_config(config: UserConfig, path: Path | None = None) -> Path:
    path = path or config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    if config.root is not None:
        lines.append(f"root = {json.dumps(str(config.root))}")
    if config.lm_studio_config is not None:
        if lines:
            lines.append("")
        lines.extend(
            [
                "[clients]",
                f"lm_studio = {json.dumps(str(config.lm_studio_config))}",
            ]
        )
    contents = "\n".join(lines) + "\n"
    fd, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(contents)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
    return path


def resolve_root(override: str | os.PathLike[str] | None = None) -> Path:
    if override is not None:
        return Path(override).expanduser().resolve()
    environment = os.environ.get("MMP_ROOT")
    if environment:
        return Path(environment).expanduser().resolve()
    configured = load_config().root
    return configured if configured is not None else default_memory_path()


def _configured_path(value: str, source: Path) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = source.parent / path
    return path.resolve()
