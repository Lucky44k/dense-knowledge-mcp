from importlib.metadata import version

from mmp import __version__


def test_package_metadata_matches_runtime_version() -> None:
    assert version("model-module-protocol") == __version__
