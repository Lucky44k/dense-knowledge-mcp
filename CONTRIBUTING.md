# Contributing

Small, focused changes are easiest to review. If you want to change the file
format or its safety rules, please open an issue first so the compatibility
impact can be discussed.

## Development setup

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[mcp,dev]"
pytest
ruff check src tests
```

Tests should accompany behavior changes. Keep MMP fixtures ASCII-only and do not
commit personal knowledge packages from `memory/`.

By submitting a contribution, you agree that it may be distributed under the
MIT License.
