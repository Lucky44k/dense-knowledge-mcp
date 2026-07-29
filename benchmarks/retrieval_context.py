"""Compare full-package context with selective MMP retrieval.

This benchmark uses the project's tokenizer-neutral lexical estimator. It is
intended to make the retrieval path reproducible, not to predict billing for a
particular model tokenizer.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from mmp.service import MMPStore
from mmp.validation import estimate_tokens

RECORDS = [
    ("distributed cache", "versioned keys", "cache invalidation"),
    ("database replication", "write ahead logs", "replica recovery"),
    ("api reliability", "exponential backoff", "retry storms"),
    ("event streaming", "consumer offsets", "message replay"),
    ("service discovery", "health probes", "endpoint routing"),
    ("load balancing", "consistent hashing", "node churn"),
    ("data pipelines", "watermarks", "late events"),
    ("schema evolution", "compatibility checks", "rolling upgrades"),
    ("observability", "trace sampling", "latency diagnosis"),
    ("access control", "short lived tokens", "credential exposure"),
    ("search ranking", "reciprocal rank fusion", "result diversity"),
    ("vector search", "quantized indexes", "memory pressure"),
    ("keyword search", "bm25 scoring", "rare term matching"),
    ("query planning", "cardinality estimates", "join ordering"),
    ("storage engines", "write amplification", "compaction load"),
    ("backup recovery", "incremental snapshots", "restore testing"),
    ("network protocols", "connection pooling", "handshake overhead"),
    ("rate limiting", "token buckets", "traffic bursts"),
    ("task queues", "visibility timeouts", "duplicate delivery"),
    ("distributed locks", "lease expiration", "stale ownership"),
    ("leader election", "monotonic terms", "split brain"),
    ("consensus systems", "quorum voting", "minority partitions"),
    ("feature flags", "staged rollouts", "deployment risk"),
    ("configuration", "immutable snapshots", "runtime drift"),
    ("incident response", "structured timelines", "causal analysis"),
    ("capacity planning", "headroom targets", "demand spikes"),
    ("cost allocation", "resource tagging", "shared infrastructure"),
    ("privacy controls", "data minimization", "retention risk"),
    ("model evaluation", "held out tasks", "benchmark leakage"),
    ("prompt testing", "versioned fixtures", "regression detection"),
    ("agent memory", "selective retrieval", "context growth"),
    ("tool calling", "typed schemas", "invalid arguments"),
    ("knowledge graphs", "entity resolution", "duplicate nodes"),
    ("document parsing", "layout detection", "table extraction"),
    ("language detection", "confidence thresholds", "short samples"),
    ("research provenance", "source identifiers", "claim tracing"),
    ("package publishing", "trusted identities", "token exposure"),
    ("dependency updates", "lock files", "supply chain drift"),
    ("release automation", "signed artifacts", "publisher trust"),
    ("local inference", "model quantization", "memory limits"),
]


def _entry(subject: str, mechanism: str, risk: str) -> dict[str, object]:
    return {
        "summary": f"{subject} uses {mechanism} to reduce {risk}",
        "tags": [subject, mechanism, risk],
        "status": "H",
        "srcs": [],
        "content": (
            f"def: {mechanism} = candidate mechanism for {subject}\n"
            f"rel: {subject} + {mechanism} -> reduced {risk}\n"
            "ctr: operational constraints != universal effectiveness\n"
            "q: measured impact under changing workloads -> further evaluation needed"
        ),
    }


def _payload(enveloped: str) -> str:
    return "\n".join(enveloped.splitlines()[1:-1])


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="mmp-benchmark-") as directory:
        root = Path(directory)
        store = MMPStore(root)
        store.create("systems.mmp", "software systems research")
        store.write(
            "systems.mmp",
            [_entry(*record) for record in RECORDS],
            rev=0,
            force=True,
        )

        full_package = (root / "systems.mmp").read_text(encoding="ascii")
        index = store.open("systems.mmp")
        search = store.search(
            "systems.mmp",
            "How should distributed caches handle invalidation?",
            k=2,
        )
        hit_ids = [
            line.split("|", 3)[1]
            for line in _payload(search).splitlines()
            if line.startswith("systems.mmp|")
        ]
        selected = store.read("systems.mmp", hit_ids)

        full_cost = estimate_tokens(full_package)
        index_cost = estimate_tokens(index) + estimate_tokens(selected)
        search_cost = estimate_tokens(search) + estimate_tokens(selected)

        top_summary = _payload(search).splitlines()[0].split("|", 4)[-1]
        print(f"entries: {len(RECORDS)}")
        print(f"top result: {top_summary}")
        print(f"full package: {full_cost} estimated tokens")
        print(f"index + selected blocks: {index_cost} estimated tokens")
        print(f"search + selected blocks: {search_cost} estimated tokens")
        print(f"index path reduction: {100 * (1 - index_cost / full_cost):.1f}%")
        print(f"search path reduction: {100 * (1 - search_cost / full_cost):.1f}%")


if __name__ == "__main__":
    main()
