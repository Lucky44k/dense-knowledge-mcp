"""Streaming-friendly MMP/1.0 parser and serializer."""

from __future__ import annotations

import re
from collections.abc import Iterable

from .errors import ValidationError
from .models import IndexEntry, Package, Source

MAGIC = "MMP/1.0"
KNOWN_SECTIONS = {"!LEGEND", "!SRC", "!INDEX", "!BODY"}
SECTION_RE = re.compile(r"^![A-Z][A-Z0-9_-]*(?: .*)?$")


def _require_ascii(value: str, where: str) -> None:
    try:
        value.encode("ascii")
    except UnicodeEncodeError as exc:
        raise ValidationError(f"{where} must contain ASCII only") from exc


def _split_fields(line: str, count: int, where: str) -> list[str]:
    fields = line.split("|")
    if len(fields) != count:
        raise ValidationError(
            f"{where}: expected {count} pipe-delimited fields, got {len(fields)}"
        )
    return fields


def parse(text: str) -> Package:
    """Parse a complete MMP file, preserving unknown extension sections."""
    _require_ascii(text, "MMP file")
    if "\r" in text:
        raise ValidationError("MMP file must use LF line endings")
    lines = text.splitlines()
    if not lines or lines[0] != MAGIC:
        raise ValidationError("line 1 must be MMP/1.0")
    if len(lines) < 2 or not lines[1].startswith("!META "):
        raise ValidationError("line 2 must be !META")

    meta: dict[str, str] = {}
    for item in lines[1][6:].split(";"):
        item = item.strip()
        if not item:
            continue
        if "=" not in item:
            raise ValidationError(f"invalid META item: {item}")
        key, value = item.split("=", 1)
        meta[key.strip()] = value.strip()
    for required in ("topic", "lang", "rev", "entries", "created", "updated"):
        if required not in meta:
            raise ValidationError(f"META missing {required}")
    try:
        rev = int(meta.pop("rev"))
        declared_entries = int(meta.pop("entries"))
    except ValueError as exc:
        raise ValidationError("META rev and entries must be integers") from exc

    package = Package(
        topic=meta.pop("topic"),
        lang=meta.pop("lang"),
        rev=rev,
        created=meta.pop("created"),
        updated=meta.pop("updated"),
        meta_extra=meta,
    )

    positions: list[tuple[int, str]] = []
    for index, line in enumerate(lines[2:], start=2):
        if SECTION_RE.match(line):
            positions.append((index, line))
    base_names = [header.split()[0] for _, header in positions]
    for required in ("!LEGEND", "!SRC", "!INDEX", "!BODY"):
        if required not in base_names:
            raise ValidationError(f"missing required section {required}")
    if not (
        base_names.index("!LEGEND")
        < base_names.index("!SRC")
        < base_names.index("!INDEX")
        < base_names.index("!BODY")
    ):
        raise ValidationError("required sections are out of order")

    for item_index, (start, header) in enumerate(positions):
        end = positions[item_index + 1][0] if item_index + 1 < len(positions) else len(lines)
        body = lines[start + 1 : end]
        name = header.split()[0]
        if name == "!LEGEND":
            for line in body:
                if not line:
                    continue
                if "=" not in line:
                    raise ValidationError(f"invalid LEGEND line: {line}")
                abbreviation, expansion = line.split("=", 1)
                package.legend[abbreviation] = expansion
        elif name == "!SRC":
            for line in body:
                if not line:
                    continue
                fields = _split_fields(line, 5, "SRC")
                source = Source(*fields)
                if source.source_id in package.sources:
                    raise ValidationError(f"duplicate source ID {source.source_id}")
                package.sources[source.source_id] = source
        elif name == "!INDEX":
            if header != "!INDEX":
                raise ValidationError(
                    "hierarchical INDEX is not supported by this implementation"
                )
            for line in body:
                if not line:
                    continue
                fields = _split_fields(line, 5, "INDEX")
                entry_id, status, tags, summary, source_ids = fields
                superseded_by = None
                match = re.search(r"\s+->(e\d+)$", summary)
                if match:
                    superseded_by = match.group(1)
                    summary = summary[: match.start()]
                entry = IndexEntry(
                    entry_id=entry_id,
                    status=status,
                    tags=tags.split(",") if tags else [],
                    summary=summary,
                    source_ids=source_ids.split(",") if source_ids else [],
                    superseded_by=superseded_by,
                )
                if entry_id in package.entries:
                    raise ValidationError(f"duplicate entry ID {entry_id}")
                package.entries[entry_id] = entry
        elif name == "!BODY":
            current_id: str | None = None
            for line in body:
                if line.startswith("@"):
                    current_id = line[1:]
                    if not current_id:
                        raise ValidationError("empty BODY entry marker")
                    package.bodies.setdefault(current_id, [])
                elif current_id is not None:
                    if line:
                        package.bodies[current_id].append(line)
                elif line:
                    raise ValidationError("BODY content before first @ marker")
        elif name not in KNOWN_SECTIONS:
            package.unknown_sections.append((header, body))

    if declared_entries != len(package.entries):
        raise ValidationError(
            f"META entries={declared_entries}, but INDEX contains {len(package.entries)}"
        )
    return package


def _reject_delimiters(value: str, delimiters: Iterable[str], where: str) -> None:
    hit = next((delimiter for delimiter in delimiters if delimiter in value), None)
    if hit is not None:
        raise ValidationError(f"{where} may not contain {hit!r}")


def serialize(package: Package) -> str:
    """Serialize a package in canonical section and entry order."""
    meta = package.meta()
    preferred = ("topic", "lang", "rev", "entries", "created", "updated")
    meta_line = "; ".join(f"{key}={meta[key]}" for key in preferred)
    extras = sorted(set(meta) - set(preferred))
    if extras:
        meta_line += "; " + "; ".join(f"{key}={meta[key]}" for key in extras)

    lines = [MAGIC, f"!META {meta_line}", "!LEGEND"]
    for abbreviation, expansion in sorted(package.legend.items()):
        _reject_delimiters(abbreviation, "=\n\r", "legend abbreviation")
        _reject_delimiters(expansion, "\n\r", "legend expansion")
        lines.append(f"{abbreviation}={expansion}")

    lines.append("!SRC")
    for source in _sorted_ids(package.sources):
        item = package.sources[source]
        values = (
            item.source_id,
            item.author_or_venue,
            item.title,
            item.year,
            item.identifier,
        )
        for value in values:
            _reject_delimiters(value, "|\n\r", f"source {item.source_id}")
        lines.append("|".join(values))

    lines.append("!INDEX")
    for entry_id in _sorted_ids(package.entries):
        entry = package.entries[entry_id]
        summary = entry.summary
        if entry.superseded_by:
            summary += f" ->{entry.superseded_by}"
        values = (
            entry.entry_id,
            entry.status,
            ",".join(entry.tags),
            summary,
            ",".join(entry.source_ids),
        )
        for value in values:
            _reject_delimiters(value, "|\n\r", f"index {entry.entry_id}")
        lines.append("|".join(values))

    for header, body in package.unknown_sections:
        lines.append(header)
        lines.extend(body)

    lines.append("!BODY")
    for entry_id in _sorted_ids(package.entries):
        if entry_id not in package.bodies:
            continue
        lines.append(f"@{entry_id}")
        lines.extend(package.bodies[entry_id])
        lines.append("")
    result = "\n".join(lines).rstrip() + "\n"
    _require_ascii(result, "MMP file")
    return result


def _sorted_ids(mapping: dict[str, object]) -> list[str]:
    def key(value: str) -> tuple[str, int, str]:
        match = re.fullmatch(r"([A-Za-z]+)(\d+)", value)
        return (
            match.group(1) if match else value,
            int(match.group(2)) if match else -1,
            value,
        )

    return sorted(mapping, key=key)
