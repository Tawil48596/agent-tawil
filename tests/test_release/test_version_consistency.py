import json
import tomllib
from pathlib import Path

from shared.version import APP_VERSION


ROOT = Path(__file__).parents[2]


def test_release_versions_are_consistent():
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    package = json.loads((ROOT / "web/package.json").read_text(encoding="utf-8"))
    lock = json.loads((ROOT / "web/package-lock.json").read_text(encoding="utf-8"))
    assert APP_VERSION == project["project"]["version"] == package["version"] == lock["version"]


def test_release_documents_exist():
    assert (ROOT / "docs/configuration.md").is_file()
    assert (ROOT / "docs/release-checklist.md").is_file()
