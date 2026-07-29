"""Command-line interface for MMP repositories."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .config import default_memory_path, load_config, resolve_root
from .errors import MMPError, ValidationError
from .onboarding import doctor, setup_environment
from .service import MMPStore


def _json_value(value: str) -> Any:
    try:
        return json.loads(value)
    except json.JSONDecodeError as exc:
        raise argparse.ArgumentTypeError(f"invalid JSON: {exc}") from exc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="mmp")
    parser.add_argument(
        "--root",
        default=None,
        help="override the configured MMP package directory",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    setup = commands.add_parser("setup", help="configure a local MMP installation")
    setup.add_argument(
        "--memory",
        help="knowledge package directory (default: user data directory)",
    )
    setup.add_argument(
        "--lm-studio-config",
        help="merge the MMP server into this mcp.json file",
    )
    setup.add_argument(
        "--force",
        action="store_true",
        help="replace an existing mmp entry in the client configuration",
    )
    setup.add_argument(
        "--dry-run",
        action="store_true",
        help="show the intended setup without writing files",
    )

    doctor_command = commands.add_parser(
        "doctor", help="check the local installation and data files"
    )
    doctor_command.add_argument(
        "--lm-studio-config",
        help="check this LM Studio mcp.json instead of the configured path",
    )

    create = commands.add_parser("create")
    create.add_argument("file")
    create.add_argument("topic")

    commands.add_parser("list")

    open_command = commands.add_parser("open")
    open_command.add_argument("file")
    open_command.add_argument("--section")

    search = commands.add_parser("search")
    search.add_argument("file")
    search.add_argument("query")
    search.add_argument("-k", type=int, default=8)

    read = commands.add_parser("read")
    read.add_argument("file")
    read.add_argument("ids", nargs="+")
    read.add_argument("--budget", type=int)

    write = commands.add_parser("write")
    write.add_argument("file")
    write.add_argument("--rev", required=True, type=int)
    write_input = write.add_mutually_exclusive_group(required=True)
    write_input.add_argument("--entries", type=_json_value)
    write_input.add_argument(
        "--from",
        dest="entries_file",
        help="read the entries array from a JSON file, or - for stdin",
    )
    write.add_argument("--force", action="store_true")

    update = commands.add_parser("update")
    update.add_argument("file")
    update.add_argument("id")
    update.add_argument("--rev", required=True, type=int)
    update_input = update.add_mutually_exclusive_group(required=True)
    update_input.add_argument("--entry", type=_json_value)
    update_input.add_argument(
        "--from",
        dest="entry_file",
        help="read the replacement object from a JSON file, or - for stdin",
    )

    deprecate = commands.add_parser("deprecate")
    deprecate.add_argument("file")
    deprecate.add_argument("id")
    deprecate.add_argument("reason")
    deprecate.add_argument("--rev", required=True, type=int)

    validate = commands.add_parser("validate")
    validate.add_argument("file")
    return parser


def run(args: argparse.Namespace) -> str:
    if args.command == "setup":
        memory = args.memory or str(default_memory_path())
        return setup_environment(
            memory,
            lm_studio_config=args.lm_studio_config,
            force=args.force,
            dry_run=args.dry_run,
        )

    root = resolve_root(args.root)
    if args.command == "doctor":
        client = (
            Path(args.lm_studio_config).expanduser().resolve()
            if args.lm_studio_config
            else None
        )
        return doctor(root, lm_studio_config=client)

    store = MMPStore(root)
    match args.command:
        case "create":
            return store.create(args.file, args.topic)
        case "list":
            return store.list()
        case "open":
            return store.open(args.file, args.section)
        case "search":
            return store.search(args.file, args.query, args.k)
        case "read":
            return store.read(args.file, args.ids, args.budget)
        case "write":
            entries = (
                _json_file(args.entries_file)
                if args.entries_file is not None
                else args.entries
            )
            if not isinstance(entries, list):
                raise ValidationError("--entries JSON must be an array")
            return store.write(args.file, entries, args.rev, args.force)
        case "update":
            entry = (
                _json_file(args.entry_file)
                if args.entry_file is not None
                else args.entry
            )
            if not isinstance(entry, dict):
                raise ValidationError("--entry JSON must be an object")
            return store.update(args.file, args.id, entry, args.rev)
        case "deprecate":
            return store.deprecate(args.file, args.id, args.reason, args.rev)
        case "validate":
            return store.validate(args.file)
        case _:
            raise AssertionError(f"unhandled command {args.command}")


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "setup" and sys.stdin.isatty():
        args = _prompt_for_setup(args)
    try:
        print(run(args))
    except MMPError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(2) from exc


def _prompt_for_setup(args: argparse.Namespace) -> argparse.Namespace:
    configured = load_config()
    default_memory = configured.root or default_memory_path()
    if args.memory is None:
        answer = input(f"Memory directory [{default_memory}]: ").strip()
        args.memory = answer or str(default_memory)
    if args.lm_studio_config is None:
        default_client = configured.lm_studio_config
        prompt = "LM Studio mcp.json"
        if default_client is not None:
            prompt += f" [{default_client}]"
        prompt += " (leave blank to skip): "
        answer = input(prompt).strip()
        if answer:
            args.lm_studio_config = answer
        elif default_client is not None:
            args.lm_studio_config = str(default_client)
    return args


def _json_file(path: str) -> Any:
    try:
        contents = sys.stdin.read() if path == "-" else Path(path).read_text("utf-8")
        return json.loads(contents)
    except (OSError, json.JSONDecodeError) as exc:
        raise ValidationError(f"cannot read JSON from {path}: {exc}") from exc


if __name__ == "__main__":
    main()
