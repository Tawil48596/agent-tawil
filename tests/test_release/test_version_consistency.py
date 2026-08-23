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

    frontend_constants = (ROOT / "web/src/lib/constants.ts").read_text(encoding="utf-8")
    sidebar = (ROOT / "web/src/components/layout/Sidebar.tsx").read_text(encoding="utf-8")
    windows_launcher = (ROOT / "启动.bat").read_text(encoding="utf-8")
    assert f'APP_VERSION = "{APP_VERSION}"' in frontend_constants
    assert "v{APP_VERSION}" in sidebar
    assert "v0.1.1" not in sidebar
    assert f"title AI Agent Platform {APP_VERSION}" in windows_launcher


def test_release_documents_exist():
    assert (ROOT / "docs/configuration.md").is_file()
    assert (ROOT / "docs/release-checklist.md").is_file()
