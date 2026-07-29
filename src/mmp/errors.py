"""Public exceptions and non-fatal notices."""

from __future__ import annotations

from dataclasses import dataclass


class MMPError(Exception):
    """Base error for MMP operations."""


class ValidationError(MMPError):
    """Input or on-disk data does not satisfy MMP/1.0."""

    def __init__(self, message: str, issues: list[str] | None = None) -> None:
        super().__init__(message)
        self.issues = issues or [message]


class NotFoundError(MMPError):
    """A package, entry, section, or source was not found."""


@dataclass(slots=True, frozen=True)
class DuplicateCandidate:
    entry_id: str
    score: float
    summary: str


class DuplicateCandidates(MMPError):
    """A write was stopped because existing entries may be duplicates."""

    def __init__(self, candidates: list[DuplicateCandidate]) -> None:
        self.candidates = candidates
        rendered = "; ".join(
            f'{item.entry_id} ({item.score:.2f}) "{item.summary}"'
            for item in candidates
        )
        super().__init__(
            f"DUPLICATE_CANDIDATES: {rendered}. "
            "Choose force=true, update the existing entry, or revise content."
        )


@dataclass(slots=True, frozen=True)
class ConflictNotice:
    """Non-fatal optimistic-locking notice."""

    expected_rev: int
    actual_rev: int
    added_ids: tuple[str, ...]

    def render(self) -> str:
        suffix = f": entries {','.join(self.added_ids)} added by another session"
        if not self.added_ids:
            suffix = ""
        return f"REV_ADVANCED {self.expected_rev}->{self.actual_rev}{suffix}"
