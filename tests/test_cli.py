from __future__ import annotations

import json
from pathlib import Path

import pytest

from mmp.cli import build_parser, run
from mmp.errors import ValidationError


def test_cli_create_and_list(tmp_path) -> None:
    parser = build_parser()
    create = parser.parse_args(
        ["--root", str(tmp_path), "create", "notes.mmp", "research notes"]
    )
    assert "CREATED" in run(create)
    listing = parser.parse_args(["--root", str(tmp_path), "list"])
    assert "notes.mmp|0 entries" in run(listing)


def test_setup_saves_root_and_merges_lm_studio_config(
    tmp_path: Path, monkeypatch
) -> None:
    config = tmp_path / "config.toml"
    client = tmp_path / "mcp.json"
    client.write_text(
        json.dumps({"mcpServers": {"other": {"command": "other-server"}}}),
        encoding="utf-8",
    )
    monkeypatch.setenv("MMP_CONFIG", str(config))
    parser = build_parser()
    args = parser.parse_args(
        [
            "setup",
            "--memory",
            str(tmp_path / "memory"),
            "--lm-studio-config",
            str(client),
        ]
    )

    result = run(args)

    assert "Next: mmp doctor" in result
    assert (tmp_path / "memory").is_dir()
    assert f'root = "{tmp_path / "memory"}"' in config.read_text(encoding="utf-8")
    document = json.loads(client.read_text(encoding="utf-8"))
    assert document["mcpServers"]["other"]["command"] == "other-server"
    assert str(tmp_path / "memory") in document["mcpServers"]["mmp"]["args"]


def test_configured_root_is_used_by_default(tmp_path: Path, monkeypatch) -> None:
    config = tmp_path / "config.toml"
    memory = tmp_path / "knowledge"
    config.write_text(f'root = "{memory}"\n', encoding="utf-8")
    monkeypatch.setenv("MMP_CONFIG", str(config))
    parser = build_parser()

    created = parser.parse_args(["create", "notes.mmp", "research notes"])

    assert "CREATED" in run(created)
    assert (memory / "notes.mmp").is_file()


def test_doctor_reports_healthy_setup(tmp_path: Path, monkeypatch) -> None:
    config = tmp_path / "config.toml"
    memory = tmp_path / "memory"
    monkeypatch.setenv("MMP_CONFIG", str(config))
    parser = build_parser()
    run(parser.parse_args(["setup", "--memory", str(memory)]))

    result = run(parser.parse_args(["doctor"]))

    assert "MMP doctor" in result
    assert f"Memory directory {memory}" in result
    assert "0 error(s)" in result


def test_write_can_read_entries_from_json_file(tmp_path: Path) -> None:
    entries = tmp_path / "entries.json"
    entries.write_text(
        json.dumps(
            [
                {
                    "summary": "Possible mechanism needs further verification",
                    "tags": ["mechanism"],
                    "status": "H",
                    "srcs": [],
                    "content": "q: proposed mechanism -> verification needed",
                }
            ]
        ),
        encoding="utf-8",
    )
    parser = build_parser()
    run(
        parser.parse_args(
            ["--root", str(tmp_path), "create", "notes.mmp", "research notes"]
        )
    )

    result = run(
        parser.parse_args(
            [
                "--root",
                str(tmp_path),
                "write",
                "notes.mmp",
                "--rev",
                "0",
                "--from",
                str(entries),
            ]
        )
    )

    assert "ids=e1" in result


def test_setup_refuses_to_replace_client_entry_without_force(
    tmp_path: Path, monkeypatch
) -> None:
    config = tmp_path / "config.toml"
    client = tmp_path / "mcp.json"
    client.write_text(
        json.dumps({"mcpServers": {"mmp": {"command": "old-server"}}}),
        encoding="utf-8",
    )
    monkeypatch.setenv("MMP_CONFIG", str(config))
    parser = build_parser()
    command = [
        "setup",
        "--memory",
        str(tmp_path / "memory"),
        "--lm-studio-config",
        str(client),
    ]
    args = parser.parse_args(command)

    with pytest.raises(ValidationError, match="already has an mmp server"):
        run(args)

    assert not config.exists()
    assert not (tmp_path / "memory").exists()

    forced = parser.parse_args([*command, "--force"])
    result = run(forced)
    assert "Backup:" in result
    assert list(tmp_path.glob("mcp.json.bak-*"))
