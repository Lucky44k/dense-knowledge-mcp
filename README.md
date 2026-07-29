# Dense Knowledge

Dense Knowledge is a small local server for Model Module Protocol (MMP) files.
It gives language models a persistent research memory without requiring a
database, embeddings, or a hosted service.

An MMP client reads a compact index first and fetches full entries only when
they are relevant. The files remain portable, diffable, and usable offline.

The project currently implements the flat MMP/1.0 format. Hierarchical indexes
are planned, but are not written yet.

<!-- mcp-name: io.github.lucky44k/dense-knowledge-mcp -->

## Install

Python 3.11 or newer is required.

Install the published package:

```bash
uv tool install dense-knowledge-mcp
mmp setup
mmp doctor
```

To install from source instead:

```bash
git clone https://github.com/Lucky44k/dense-knowledge-mcp.git
cd dense-knowledge-mcp
./scripts/install.sh
mmp setup
mmp doctor
```

`mmp setup` asks where knowledge files should be stored. It can also merge the
server entry into an LM Studio `mcp.json`. Existing servers are preserved; if an
MMP entry must be replaced, the command requires `--force` and creates a backup
of the JSON file first.

The non-interactive equivalent is:

```bash
mmp setup \
  --memory "$HOME/.local/share/mmp/memory" \
  --lm-studio-config "/path/to/mcp.json"
```

The selected paths are saved in the user configuration:

- Linux: `~/.config/mmp/config.toml`
- macOS: `~/Library/Application Support/mmp/config.toml`
- Windows: `%APPDATA%\mmp\config.toml`

`MMP_ROOT` or the global `--root` option can override the configured memory
directory for a single process.

## LM Studio

If you prefer to configure LM Studio yourself, the server command is:

```bash
mmp-server --root "/absolute/path/to/memory" --transport stdio
```

Minimal client configuration:

```json
{
  "mcpServers": {
    "mmp": {
      "command": "mmp-server",
      "args": [
        "--root",
        "/absolute/path/to/memory",
        "--transport",
        "stdio"
      ]
    }
  }
}
```

Restart the MCP connection after changing the configuration. `mmp doctor`
checks the installation, memory directory, stored packages, and the configured
LM Studio file.

## Command line

Create and inspect a package:

```bash
mmp create quantum_physics.mmp "quantum physics"
mmp list
mmp open quantum_physics.mmp
mmp search quantum_physics.mmp "Bell inequality tests"
mmp read quantum_physics.mmp e1
```

Structured entries can be passed inline or read from a JSON file:

```bash
mmp write quantum_physics.mmp --rev 0 --from entries.json
mmp validate quantum_physics.mmp
```

An entry in `entries.json` looks like this:

```json
[
  {
    "summary": "Bell inequality separates local realism from quantum predictions",
    "tags": ["BI", "nonlocality", "experimental tests"],
    "status": "F",
    "srcs": [
      {
        "author_or_venue": "Bell",
        "title": "On the Einstein Podolsky Rosen paradox",
        "year": "1964",
        "identifier": "doi:10.1103/PhysicsPhysiqueFizika.1.195"
      }
    ],
    "legend": {
      "BI": "Bell inequality"
    },
    "content": "def: BI = bound on local hidden variable correlations\nfact: quantum predictions -> violation of local realism bound"
  }
]
```

Source objects are registered and deduplicated automatically. Existing source
IDs such as `"s1"` may be reused in later writes.

Important validation rules:

- summaries contain 3–15 English words
- tags are a JSON array, never one comma-separated string
- entries with status `F` or `C` require sources
- unsourced entries use status `H` and cannot contain `fact:` or `num:` lines
- contested entries use status `C` and include at least one `ctr:` line

Run `mmp --help` or `mmp <command> --help` for the complete CLI reference.

## Retrieval and updates

The MCP server exposes nine tools:

- `mmp_list`, `mmp_create`, `mmp_open`, `mmp_search`, and `mmp_read`
- `mmp_write`, `mmp_update`, `mmp_deprecate`, and `mmp_validate`

Search uses BM25 over index metadata with legend expansion and a full-body
fallback. Updates never overwrite an entry: the replacement receives a new ID,
the previous entry is marked deprecated, and its body remains available.

All writes use optimistic revision numbers and atomic file replacement. A stale
revision is reported to the caller, but does not discard an append that can be
applied safely.

## Safety

Content returned from an MMP file is wrapped as untrusted reference data:

```text
<mmp_data file="..." trust="untrusted">
...
</mmp_data>
```

The server rejects common instruction-like contamination during writes. It
never follows `ref:` links automatically, and its tool descriptions tell the
client that stored content is data rather than instructions. These measures
reduce prompt-injection risk; they do not make untrusted research material
equivalent to trusted instructions.

Keep personal packages out of source control. The default `memory/` directory
is ignored by Git.

## Development

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
pytest
ruff check src tests
python -m build
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for contribution notes and
[SECURITY.md](SECURITY.md) for private vulnerability reports.

Releases follow [Semantic Versioning](https://semver.org/). The package version
is defined in `src/mmp/__init__.py`; Git tags use the corresponding `v1.2.3`
form. Release notes are kept in [CHANGELOG.md](CHANGELOG.md).

Licensed under the [MIT License](LICENSE).
