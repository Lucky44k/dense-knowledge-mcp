# Contributing

Small, focused changes are easiest to review. If you want to change the file
format or its safety rules, please open an issue first so the compatibility
impact can be discussed.

## Development setup

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
pytest
ruff check src tests
```

Tests should accompany behavior changes. Keep MMP fixtures ASCII-only and do not
commit personal knowledge packages from `memory/`.

## Releases

The version in `src/mmp/__init__.py` is the single source used by the package
build. Releases follow Semantic Versioning and use matching Git tags such as
`v1.2.3`. Move completed changes from `Unreleased` into a dated section in
`CHANGELOG.md` before tagging.

By submitting a contribution, you agree that it may be distributed under the
MIT License.
