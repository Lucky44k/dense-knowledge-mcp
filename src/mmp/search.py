"""Small dependency-free BM25 implementation for MMP indexes."""

from __future__ import annotations

import math
import re
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass

TOKEN_RE = re.compile(r"[a-z0-9]+(?:'[a-z0-9]+)?")


def tokenize(text: str) -> list[str]:
    return TOKEN_RE.findall(text.lower().replace("_", " "))


def expand_query(query: str, legend: dict[str, str]) -> str:
    """Expand abbreviations and expansions in either direction."""
    query_tokens = set(tokenize(query))
    additions: list[str] = []
    lowered = query.lower()
    for abbreviation, expansion in legend.items():
        abbreviation_tokens = set(tokenize(abbreviation))
        expansion_tokens = set(tokenize(expansion))
        if abbreviation_tokens & query_tokens:
            additions.append(expansion)
        if expansion.lower() in lowered or (
            expansion_tokens and expansion_tokens <= query_tokens
        ):
            additions.append(abbreviation)
    return " ".join([query, *additions])


@dataclass(slots=True, frozen=True)
class SearchHit:
    doc_id: str
    score: float


def bm25(
    query: str,
    documents: Iterable[tuple[str, str]],
    *,
    k1: float = 1.5,
    b: float = 0.75,
) -> list[SearchHit]:
    docs = [(doc_id, tokenize(text)) for doc_id, text in documents]
    if not docs:
        return []
    query_terms = tokenize(query)
    if not query_terms:
        return []
    avg_length = sum(len(tokens) for _, tokens in docs) / len(docs) or 1.0
    frequencies = Counter(
        term
        for term in set(query_terms)
        for _, tokens in docs
        if term in set(tokens)
    )
    hits: list[SearchHit] = []
    for doc_id, tokens in docs:
        term_counts = Counter(tokens)
        score = 0.0
        for term in query_terms:
            count = term_counts[term]
            if not count:
                continue
            doc_frequency = frequencies[term]
            idf = math.log(1 + (len(docs) - doc_frequency + 0.5) / (doc_frequency + 0.5))
            normalization = count + k1 * (
                1 - b + b * len(tokens) / avg_length
            )
            score += idf * count * (k1 + 1) / normalization
        if score > 0:
            hits.append(SearchHit(doc_id, score))
    return sorted(hits, key=lambda hit: (-hit.score, hit.doc_id))


def normalized_similarity(query: str, documents: Iterable[tuple[str, str]]) -> list[SearchHit]:
    """BM25 scores normalized to the best result for duplicate screening."""
    hits = bm25(query, documents)
    if not hits:
        return []
    best = hits[0].score
    return [SearchHit(hit.doc_id, hit.score / best) for hit in hits]
