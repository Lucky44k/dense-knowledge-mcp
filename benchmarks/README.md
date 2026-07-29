# Selective retrieval benchmark

This benchmark compares loading one complete research package with MMP's two
selective retrieval paths:

- load the compact index and then selected body blocks;
- search index metadata and then load selected body blocks.

Run it from the repository root:

```bash
uv run python benchmarks/retrieval_context.py
```

The fixture contains 40 synthetic entries so the benchmark measures retrieval
shape rather than the quality of a particular research corpus. It also checks
that a cache-invalidation question ranks the intended entry first.

Counts use Dense Knowledge's conservative lexical estimator. They are
tokenizer-neutral estimates used to enforce MMP limits, not billing-token
claims for a specific model. Results can vary slightly when the serialized
metadata date changes.

Current result:

```text
entries: 40
top result: distributed cache uses versioned keys to reduce cache invalidation
full package: 2322 estimated tokens
index + selected blocks: 971 estimated tokens
search + selected blocks: 132 estimated tokens
index path reduction: 58.2%
search path reduction: 94.3%
```
