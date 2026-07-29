"""MMP structural, safety, and language validation."""

from __future__ import annotations

import importlib.util
import re
from dataclasses import dataclass
from functools import lru_cache

from .models import VALID_PREFIXES, VALID_STATUSES, Package

META_INJECTION_PATTERNS = (
    re.compile(r"\bignore\s+(?:all\s+)?previous\b", re.IGNORECASE),
    re.compile(r"(?:^|\s)system\s*:", re.IGNORECASE),
    re.compile(r"\byou\s+must\b", re.IGNORECASE),
    re.compile(r"<\s*/?\s*instructions?\s*>", re.IGNORECASE),
    re.compile(r"<\s*/?\s*mmp_data\b", re.IGNORECASE),
)
STRUCTURE_RE = re.compile(r"[|=!~+?<>\-]+|\d+")
PREFIX_RE = re.compile(r"^(?:def|fact|rel|num|ex|ctr|q|ref):", re.MULTILINE)
WORD_RE = re.compile(r"[A-Za-z]+(?:'[A-Za-z]+)?")
TAG_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 .+/-]*$")


@dataclass(slots=True, frozen=True)
class LanguageResult:
    accepted: bool
    language: str
    confidence: float
    detector: str


def estimate_tokens(text: str) -> int:
    """Conservative tokenizer-neutral estimate suitable for enforcing limits."""
    lexical = len(re.findall(r"[A-Za-z0-9]+|->|!=|[|=~+?]", text))
    return max(1, lexical)


@lru_cache(maxsize=1)
def _langid_identifier():
    from langid.langid import (  # type: ignore[import-not-found]
        LanguageIdentifier,
        model,
    )

    return LanguageIdentifier.from_modelstring(model, norm_probs=True)


def validate_language(content: str) -> LanguageResult:
    cleaned = PREFIX_RE.sub("", content)
    cleaned = STRUCTURE_RE.sub(" ", cleaned).replace("_", " ")
    if len(cleaned.split()) < 5:
        return LanguageResult(True, "unknown", 0.0, "short-content")

    if importlib.util.find_spec("langid") is not None:
        language, confidence = _langid_identifier().classify(cleaned)
        return LanguageResult(
            language == "en" or confidence < 0.80,
            language,
            float(confidence),
            "langid",
        )

    # A conservative offline fallback catches obvious contamination but never
    # rejects uncertain prose. Install the language extra for strict detection.
    words = [word.lower() for word in WORD_RE.findall(cleaned)]
    german = {
        "aber", "auch", "auf", "das", "der", "die", "ein", "eine", "für",
        "ist", "mit", "nicht", "oder", "und", "von", "wird", "zu",
    }
    english = {
        "a", "and", "are", "as", "by", "for", "from", "in", "is", "of",
        "on", "or", "the", "to", "with",
    }
    de_hits = sum(word in german for word in words)
    en_hits = sum(word in english for word in words)
    if de_hits >= 3 and de_hits >= en_hits + 2:
        confidence = min(0.99, 0.70 + 0.05 * (de_hits - en_hits))
        return LanguageResult(confidence < 0.80, "de", confidence, "heuristic")
    return LanguageResult(True, "unknown", 0.0, "heuristic")


def content_issues(
    content: str,
    *,
    has_sources: bool | None = None,
    status: str | None = None,
) -> list[str]:
    issues: list[str] = []
    try:
        content.encode("ascii")
    except UnicodeEncodeError:
        issues.append("content must contain ASCII only")
    lines = content.splitlines()
    if not lines:
        issues.append("content must contain at least one line")
    for number, line in enumerate(lines, start=1):
        if not line.startswith(VALID_PREFIXES):
            issues.append(f"content line {number} has unknown prefix")
            continue
        prefix, payload = line.split(":", 1)
        if not payload.strip():
            issues.append(f"content line {number} has an empty {prefix}: payload")
        if has_sources is False and prefix in {"fact", "num"}:
            issues.append(
                f"content line {number} uses {prefix}: without a registered source"
            )
    if status == "C" and lines and not any(line.startswith("ctr:") for line in lines):
        issues.append("status C content must include at least one ctr: line")
    token_count = estimate_tokens(content)
    if token_count > 250:
        issues.append(f"content exceeds 250-token hard limit ({token_count})")
    for pattern in META_INJECTION_PATTERNS:
        if pattern.search(content):
            issues.append("content contains a prohibited instruction-like pattern")
            break
    language = validate_language(content)
    if not language.accepted:
        issues.append(
            f"non-English content ({language.language}, {language.confidence:.2f})"
        )
    return issues


def package_issues(package: Package) -> list[str]:
    issues: list[str] = []
    if package.lang != "en":
        issues.append(f"META lang must be en, got {package.lang!r}")
    seen_numbers: set[int] = set()
    for entry_id, entry in package.entries.items():
        if not re.fullmatch(r"e[1-9]\d*", entry_id):
            issues.append(f"invalid entry ID {entry_id}")
        else:
            number = int(entry_id[1:])
            if number in seen_numbers:
                issues.append(f"duplicate entry number {number}")
            seen_numbers.add(number)
        if entry.status not in VALID_STATUSES:
            issues.append(f"{entry_id}: invalid status {entry.status!r}")
        if not entry.summary.strip():
            issues.append(f"{entry_id}: summary must not be empty")
        if len(entry.summary.split()) > 15:
            issues.append(f"{entry_id}: summary exceeds 15 words")
        if entry.status != "D":
            if len(entry.tags) != len(set(entry.tags)):
                issues.append(f"{entry_id}: duplicate tags")
            for tag in entry.tags:
                if len(tag) < 2:
                    issues.append(f"{entry_id}: tag {tag!r} is too short")
                if len(tag) > 40:
                    issues.append(f"{entry_id}: tag {tag!r} exceeds 40 characters")
                if not TAG_RE.fullmatch(tag):
                    issues.append(f"{entry_id}: tag {tag!r} has invalid characters")
                if tag != tag.lower() and tag not in package.legend:
                    issues.append(
                        f"{entry_id}: uppercase tag must be a registered abbreviation"
                    )
        for source_id in entry.source_ids:
            if source_id not in package.sources:
                issues.append(f"{entry_id}: orphan source reference {source_id}")
        if entry.status in {"F", "C"} and not entry.source_ids:
            issues.append(f"{entry_id}: status {entry.status} requires a source")
        if entry_id not in package.bodies:
            issues.append(f"{entry_id}: missing BODY block")
        else:
            semantic_context = (
                {}
                if entry.status == "D"
                else {"has_sources": bool(entry.source_ids), "status": entry.status}
            )
            issues.extend(
                f"{entry_id}: {issue}"
                for issue in content_issues(
                    "\n".join(package.bodies[entry_id]), **semantic_context
                )
            )
        if entry.superseded_by and entry.superseded_by not in package.entries:
            issues.append(f"{entry_id}: orphan supersede reference {entry.superseded_by}")
    for body_id in package.bodies:
        if body_id not in package.entries:
            issues.append(f"orphan BODY block {body_id}")
    for abbreviation, expansion in package.legend.items():
        if len(expansion.split()) < 2:
            issues.append(f"legend {abbreviation}: expansion must have at least 2 words")
    for source_id, source in package.sources.items():
        if not re.fullmatch(r"s[1-9]\d*", source_id):
            issues.append(f"invalid source ID {source_id}")
        if not source.author_or_venue.strip():
            issues.append(f"{source_id}: author_or_venue must not be empty")
        if not source.title.strip():
            issues.append(f"{source_id}: title must not be empty")
        if not re.fullmatch(r"\d{4}", source.year):
            issues.append(f"{source_id}: year must be four digits")
    return issues
