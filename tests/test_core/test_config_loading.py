from pathlib import Path

import pytest
import yaml

from app import load_config

ROOT = Path(__file__).parents[2]


def test_default_config_preserves_all_tool_market_settings():
    config = load_config(str(ROOT / "config.yaml"))

    assert config["tool_market"]["package_path"] == "data/tool_packages"
    assert config["tool_market"]["sandbox_mode"] == "subprocess"
    assert "browser" in config["tool_market"]["approval_required_for"]


def test_config_loader_rejects_duplicate_mapping_keys(tmp_path):
    config_path = tmp_path / "duplicate.yaml"
    config_path.write_text("tool_market: {}\ntool_market: {}\n", encoding="utf-8")

    with pytest.raises(yaml.constructor.ConstructorError, match="duplicate key: tool_market"):
        load_config(str(config_path))
