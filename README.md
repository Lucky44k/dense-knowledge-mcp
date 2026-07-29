# Dense Knowledge

<!-- mcp-name: io.github.Lucky44k/dense-knowledge-mcp -->

[![PyPI](https://img.shields.io/pypi/v/dense-knowledge-mcp)](https://pypi.org/project/dense-knowledge-mcp/)
[![Python](https://img.shields.io/pypi/pyversions/dense-knowledge-mcp)](https://pypi.org/project/dense-knowledge-mcp/)
[![CI](https://github.com/Lucky44k/dense-knowledge-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/Lucky44k/dense-knowledge-mcp/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

**A local-first MCP memory server for persistent LLM knowledge.**

Dense Knowledge lets an AI assistant keep structured research between sessions
without a database, embedding model, or hosted account. It stores portable
`.mmp` files, searches their compact indexes with BM25, and loads full entries
only when they are relevant.

```text
question -> compact index/search -> selected knowledge blocks -> answer
             inexpensive             detailed context
```

It works with LM Studio, Claude Desktop, Cursor, VS Code, and other clients that
support local stdio [Model Context Protocol](https://modelcontextprotocol.io/)
servers.

## Why Dense Knowledge?

- **Selective context:** index first, body blocks only on demand.
- **Local and portable:** plain ASCII-in-UTF-8 files that can be copied,
  inspected, diffed, and backed up.
- **No vector infrastructure:** deterministic BM25 search with abbreviation
  and synonym expansion.
- **Append-only history:** updates supersede older entries instead of erasing
  them.
- **Explicit provenance:** established and contested claims carry source IDs;
  unsourced inferences are marked as hypotheses.
- **Safer retrieval:** stored text is wrapped as untrusted data and screened
  for common prompt-injection contamination.

The bundled [context benchmark](benchmarks/) uses 40 entries. In its synthetic
fixture, searching and reading the two best blocks uses **94.3% less estimated
context** than loading the complete package. The benchmark is reproducible and
clearly documents its tokenizer-neutral counting method.

## Quick start

Install [`uv`](https://docs.astral.sh/uv/getting-started/installation/), then
place this server definition in your MCP client:

```json
{
  "mcpServers": {
    "dense-knowledge": {
      "command": "uvx",
      "args": ["dense-knowledge-mcp"]
    }
  }
}
```

`uvx` downloads the published package when needed. Dense Knowledge uses the
platform's default data directory unless `--root` is supplied:

```json
{
  "mcpServers": {
    "dense-knowledge": {
      "command": "uvx",
      "args": [
        "dense-knowledge-mcp",
        "--root",
        "/absolute/path/to/memory"
      ]
    }
  }
}
```

Configuration differs slightly between clients. Ready-to-copy instructions are
available for:

- [LM Studio](docs/clients.md#lm-studio)
- [Claude Desktop](docs/clients.md#claude-desktop)
- [Cursor](docs/clients.md#cursor)
- [Visual Studio Code](docs/clients.md#visual-studio-code)

To install the command-line tools permanently:

```bash
uv tool install dense-knowledge-mcp
mmp setup
mmp doctor
```

`mmp setup` creates the memory directory and can safely merge the server into
an LM Studio `mcp.json`. Existing servers are preserved. Replacing an existing
Dense Knowledge entry requires `--force` and creates a backup first.

## See it work

The CLI exposes the same storage operations as the MCP server:

```bash
mmp create quantum_physics.mmp "quantum physics"
mmp write quantum_physics.mmp --rev 0 --from examples/research_entries.json
mmp search quantum_physics.mmp "experimental tests of local realism"
mmp read quantum_physics.mmp e1
```

Typical search output contains candidates, not full bodies:

```text
<mmp_data file="quantum_physics.mmp" trust="untrusted">
quantum_physics.mmp|e1|F|2.5427|Bell inequality separates local realism from quantum predictions
</mmp_data>
```

The client chooses relevant IDs and calls `mmp_read` only for those blocks.
This preserves the distinction between cheap orientation and detailed context.

## MCP tools

The server exposes nine tools:

| Tool | Purpose |
|---|---|
| `mmp_list` | List available knowledge packages |
| `mmp_create` | Create an empty MMP package |
| `mmp_open` | Read metadata, sources, legend, and index |
| `mmp_search` | Return ranked candidates without body text |
| `mmp_read` | Load selected body blocks within an optional budget |
| `mmp_write` | Append structured entries |
| `mmp_update` | Supersede an entry while preserving history |
| `mmp_deprecate` | Mark an entry as obsolete with a reason |
| `mmp_validate` | Check structure, language, provenance, and references |

Search uses BM25 over tags and summaries after legend expansion, with a body
fallback when the index has no match. Deprecated entries remain readable but
are omitted from normal search results.

## Storage

The default knowledge directory follows the operating system:

- Linux: `~/.local/share/mmp/memory`
- macOS: `~/Library/Application Support/mmp/memory`
- Windows: `%LOCALAPPDATA%\mmp\memory`

The user configuration is stored separately:

- Linux: `~/.config/mmp/config.toml`
- macOS: `~/Library/Application Support/mmp/config.toml`
- Windows: `%APPDATA%\mmp\config.toml`

`MMP_ROOT` or the global `mmp --root` option overrides the configured directory.
Keep personal packages out of source control; the repository's `memory/`
directory is ignored.

## Writing knowledge

Models send structured objects to `mmp_write`; they never need to generate raw
MMP syntax. A minimal entry looks like:

```json
{
  "summary": "Possible caching strategy needs workload validation",
  "tags": ["caching", "validation"],
  "status": "H",
  "srcs": [],
  "content": "rel: versioned keys -> simpler invalidation\nq: workload impact -> needs measurement"
}
```

Important validation rules:

- summaries contain 3–15 English words;
- tags are a JSON array, never one comma-separated string;
- entries with status `F` or `C` require sources;
- unsourced entries use status `H` and cannot contain `fact:` or `num:` lines;
- contested entries use status `C` and include at least one `ctr:` line;
- block content is ASCII English and uses the eight defined line prefixes.

See [`examples/research_entries.json`](examples/research_entries.json) for
sourced and contested entries that can be written directly.

All writes use optimistic revision numbers and atomic file replacement. A stale
revision is reported to the caller, but a safe append is not discarded.

## Safety model

MMP content is reference data, never instruction. Read responses use an
explicit untrusted envelope:

```text
<mmp_data file="..." trust="untrusted">
...
</mmp_data>
```

The server rejects common instruction-like patterns during writes, does not
automatically follow `ref:` links, and tells the client not to obey instructions
found in stored material. These defenses reduce prompt-injection risk; they do
not turn untrusted research into trusted instructions.

Local MCP servers execute with your user permissions. Review the package and
choose a dedicated memory directory before storing sensitive information.

## Project status

Dense Knowledge implements the flat MMP/1.0 format, including BM25 retrieval,
catalog generation, duplicate screening, budgets, append-only superseding, and
validation. Hierarchical indexes for very large packages are planned but are
not written yet.

Releases follow [Semantic Versioning](https://semver.org/). Changes are
documented in [CHANGELOG.md](CHANGELOG.md).

## Development

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
ruff check src tests benchmarks
pytest
python -m build
```

Contributions are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for the
workflow and [SECURITY.md](SECURITY.md) for private vulnerability reports.

Licensed under the [MIT License](LICENSE).
