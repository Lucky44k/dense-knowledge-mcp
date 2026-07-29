# MCP client setup

Dense Knowledge is a local stdio MCP server. The examples below use
[`uvx`](https://docs.astral.sh/uv/guides/tools/) so the client can run the
published package without a separate virtual environment.

Replace `/absolute/path/to/memory` with a directory that should contain your
MMP files. The directory is created automatically. You can omit `--root` and
the path to use the platform default documented in the
[storage section](../README.md#storage).

## LM Studio

Open LM Studio's `mcp.json` and merge this server into its existing
`mcpServers` object:

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

A standalone copy is available at
[`examples/clients/lm-studio.mcp.json`](../examples/clients/lm-studio.mcp.json).

LM Studio must be able to find `uvx` on its `PATH`. Save the file and restart
the MCP connection. See LM Studio's
[MCP documentation](https://lmstudio.ai/docs/developer/core/mcp).

For a guided local installation instead, run:

```bash
uv tool install dense-knowledge-mcp
mmp setup
mmp doctor
```

`mmp setup` can merge the server entry into an existing LM Studio
configuration without removing other servers.

## Claude Desktop

Open **Settings > Developer > Edit Config** and merge:

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

A standalone copy is available at
[`examples/clients/claude-desktop.json`](../examples/clients/claude-desktop.json).

Completely restart Claude Desktop after saving. The official MCP guide lists
the config location and troubleshooting steps for
[local Claude Desktop servers](https://modelcontextprotocol.io/docs/2026-07-28/develop/connect-local-servers).

## Cursor

Add the same stdio definition to the global MCP configuration or to
`.cursor/mcp.json` inside a project:

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

A standalone copy is available at
[`examples/clients/cursor.mcp.json`](../examples/clients/cursor.mcp.json).

Restart the server from Cursor's MCP settings after changing the file. See
[Cursor's MCP documentation](https://cursor.com/docs/mcp).

## Visual Studio Code

Run **MCP: Open User Configuration** from the Command Palette, or create
`.vscode/mcp.json` for a workspace. VS Code uses `servers` rather than
`mcpServers`:

```json
{
  "servers": {
    "dense-knowledge": {
      "type": "stdio",
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

A standalone copy is available at
[`examples/clients/vscode.mcp.json`](../examples/clients/vscode.mcp.json).

The same server can be added from a terminal:

```bash
code --add-mcp '{"name":"dense-knowledge","command":"uvx","args":["dense-knowledge-mcp"]}'
```

See the official [VS Code MCP configuration
reference](https://code.visualstudio.com/docs/agents/reference/mcp-configuration).

## Verify the connection

After the client starts the server, it should expose these nine tools:

```text
mmp_list        mmp_create      mmp_open
mmp_search      mmp_read        mmp_write
mmp_update      mmp_deprecate   mmp_validate
```

If you installed the package as a tool, `mmp doctor` checks Python, the MCP
dependency, the memory directory, stored packages, and an optional LM Studio
configuration.

For manual diagnostics, verify that the server command resolves:

```bash
uvx dense-knowledge-mcp --help
```

Local MCP servers run with your user permissions. Review a server before
granting it access to sensitive directories. Dense Knowledge accesses only the
configured memory directory, but stored source text should still be treated as
untrusted data.
