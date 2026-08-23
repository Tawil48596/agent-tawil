"""Network destination policy shared by host-side web tools."""

import asyncio
import socket
from ipaddress import ip_address
from urllib.parse import urlparse


def validate_http_url(url: str) -> str:
    normalized = url.strip()
    parsed = urlparse(normalized)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("url must be a valid HTTP(S) URL")
    if parsed.username or parsed.password:
        raise ValueError("credentials in web URLs are not allowed")
    return normalized


def _resolved_addresses(hostname: str, port: int) -> set[str]:
    return {item[4][0] for item in socket.getaddrinfo(hostname, port, type=socket.SOCK_STREAM)}


async def require_public_http_url(url: str) -> str:
    """Reject destinations that can reach the local host or private networks."""
    normalized = validate_http_url(url)
    parsed = urlparse(normalized)
    hostname = parsed.hostname or ""
    port = parsed.port or (443 if parsed.scheme == "https" else 80)

    try:
        addresses = {str(ip_address(hostname))}
    except ValueError:
        addresses = await asyncio.to_thread(_resolved_addresses, hostname, port)

    if not addresses:
        raise ValueError("web destination did not resolve to an address")
    for address in addresses:
        resolved = ip_address(address)
        if not resolved.is_global:
            raise ValueError(f"web destination resolves to a non-public address: {address}")
    return normalized
