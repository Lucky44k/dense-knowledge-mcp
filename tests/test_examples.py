from __future__ import annotations

import json
from pathlib import Path

from mmp.service import MMPStore

ROOT = Path(__file__).parents[1]


def test_research_entries_are_valid_and_searchable(tmp_path: Path) -> None:
    entries = json.loads(
        (ROOT / "examples" / "research_entries.json").read_text(encoding="utf-8")
    )
    store = MMPStore(tmp_path)
    store.create("research.mmp", "quantum research")

    assert "ids=e1,e2" in store.write("research.mmp", entries, rev=0)
    assert "VALID" in store.validate("research.mmp")
    assert "e1|F|" in store.search("research.mmp", "local realism experiment")


def test_client_examples_are_valid_json() -> None:
    examples = sorted((ROOT / "examples" / "clients").glob("*.json"))
    assert len(examples) == 4

    for path in examples:
        document = json.loads(path.read_text(encoding="utf-8"))
        servers = document.get("mcpServers", document.get("servers"))
        server = servers["dense-knowledge"]
        assert server["command"] == "uvx"
        assert server["args"][0] == "dense-knowledge-mcp"
