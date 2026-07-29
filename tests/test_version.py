import json
from importlib.metadata import distribution, version
from pathlib import Path

from mmp import __version__

ROOT = Path(__file__).parents[1]
REGISTRY_NAME = "io.github.Lucky44k/dense-knowledge-mcp"


def test_package_metadata_matches_runtime_version() -> None:
    assert version("dense-knowledge-mcp") == __version__


def test_registry_metadata_matches_package() -> None:
    server = json.loads((ROOT / "server.json").read_text(encoding="utf-8"))
    package = server["packages"][0]
    assert server["name"] == REGISTRY_NAME
    assert server["version"] == __version__
    assert package["identifier"] == "dense-knowledge-mcp"
    assert package["version"] == __version__
    assert f"mcp-name: {REGISTRY_NAME}" in (ROOT / "README.md").read_text(
        encoding="utf-8"
    )


def test_distribution_exposes_registry_command() -> None:
    scripts = {
        entry.name
        for entry in distribution("dense-knowledge-mcp").entry_points
        if entry.group == "console_scripts"
    }
    assert "dense-knowledge-mcp" in scripts
