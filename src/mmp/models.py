"""In-memory representation of an MMP file."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

VALID_STATUSES = frozenset({"F", "C", "H", "D"})
VALID_PREFIXES = ("def:", "fact:", "rel:", "num:", "ex:", "ctr:", "q:", "ref:")


@dataclass(slots=True)
class Source:
    source_id: str
    author_or_venue: str
    title: str
    year: str
    identifier: str = ""


@dataclass(slots=True)
class IndexEntry:
    entry_id: str
    status: str
    tags: list[str]
    summary: str
    source_ids: list[str] = field(default_factory=list)
    superseded_by: str | None = None
    section: str | None = None


@dataclass(slots=True)
class Package:
    topic: str
    lang: str = "en"
    rev: int = 0
    created: str = field(
        default_factory=lambda: datetime.now().astimezone().date().isoformat()
    )
    updated: str = field(
        default_factory=lambda: datetime.now().astimezone().date().isoformat()
    )
    meta_extra: dict[str, str] = field(default_factory=dict)
    legend: dict[str, str] = field(default_factory=dict)
    sources: dict[str, Source] = field(default_factory=dict)
    entries: dict[str, IndexEntry] = field(default_factory=dict)
    bodies: dict[str, list[str]] = field(default_factory=dict)
    unknown_sections: list[tuple[str, list[str]]] = field(default_factory=list)

    @property
    def next_entry_number(self) -> int:
        numbers = [
            int(entry_id[1:])
            for entry_id in self.entries
            if entry_id.startswith("e") and entry_id[1:].isdigit()
        ]
        return max(numbers, default=0) + 1

    @property
    def next_source_number(self) -> int:
        numbers = [
            int(source_id[1:])
            for source_id in self.sources
            if source_id.startswith("s") and source_id[1:].isdigit()
        ]
        return max(numbers, default=0) + 1

    def meta(self) -> dict[str, Any]:
        return {
            "topic": self.topic,
            "lang": self.lang,
            "rev": self.rev,
            "entries": len(self.entries),
            "created": self.created,
            "updated": self.updated,
            **self.meta_extra,
        }
