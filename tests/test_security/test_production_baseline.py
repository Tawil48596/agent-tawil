import pytest

from plugins.security.baseline import enforce_production_config, validate_production_config


def test_development_config_is_not_restricted():
    assert validate_production_config({}) == []


def test_unsafe_production_config_fails(monkeypatch):
    monkeypatch.delenv("JWT_SECRET", raising=False)
    monkeypatch.delenv("AGENT_ADMIN_PASSWORD", raising=False)
    config = {"server": {"environment": "production", "cors_origins": ["*"]},
              "auth": {"enabled": False}, "security": {"sandbox": {"network_disabled": False}}}
    errors = validate_production_config(config)
    assert len(errors) == 5
    with pytest.raises(RuntimeError, match="Unsafe production"):
        enforce_production_config(config)


def test_safe_production_config_passes(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "x" * 40)
    monkeypatch.setenv("AGENT_ADMIN_PASSWORD", "correct-horse-battery-staple")
    config = {"server": {"environment": "production", "cors_origins": ["https://agent.example"]},
              "auth": {"enabled": True}, "security": {"sandbox": {"network_disabled": True}}}
    enforce_production_config(config)
