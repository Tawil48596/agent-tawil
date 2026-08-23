"""Discoverable entrypoint for the security runtime plugin."""

from plugins.security.security_plugin import SecurityPlugin


def create_plugin() -> SecurityPlugin:
    return SecurityPlugin()
