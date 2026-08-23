"""Fail-fast validation for production security configuration."""

import os


def validate_production_config(config: dict) -> list[str]:
    server = config.get("server", {})
    if server.get("environment", "development") != "production":
        return []
    errors = []
    auth = config.get("auth", {})
    if not auth.get("enabled", False):
        errors.append("authentication must be enabled in production")
    secret = os.environ.get("JWT_SECRET", auth.get("jwt_secret", ""))
    if not secret or secret in ("dev-secret-change-me", "${JWT_SECRET}") or len(secret) < 32:
        errors.append("JWT_SECRET must contain at least 32 characters")
    admin_password = os.environ.get("AGENT_ADMIN_PASSWORD", "")
    if len(admin_password) < 12:
        errors.append("AGENT_ADMIN_PASSWORD must contain at least 12 characters")
    origins = server.get("cors_origins", [])
    if not origins or "*" in origins:
        errors.append("explicit CORS origins are required in production")
    if config.get("security", {}).get("sandbox", {}).get("network_disabled") is not True:
        errors.append("sandbox network access must be disabled in production")
    return errors


def enforce_production_config(config: dict) -> None:
    errors = validate_production_config(config)
    if errors:
        raise RuntimeError("Unsafe production configuration: " + "; ".join(errors))
