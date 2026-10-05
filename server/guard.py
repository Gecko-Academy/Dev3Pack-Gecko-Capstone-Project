"""Reject non-public HTTPS URLs before any optional RPC fetch."""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse


def is_public_url(url: str) -> bool:
    """Return whether `url` is HTTPS and resolves only to public addresses."""
    parsed = urlparse(url)

    if parsed.scheme != "https" or not parsed.hostname:
        return False

    try:
        addresses = {
            info[4][0]
            for info in socket.getaddrinfo(
                parsed.hostname,
                parsed.port or 443,
                type=socket.SOCK_STREAM,
            )
        }
    except (socket.gaierror, ValueError):
        # Fail closed: an unresolvable hostname cannot be proved safe to fetch.
        return False

    if not addresses:
        return False

    for address in addresses:
        try:
            ip = ipaddress.ip_address(address)
        except ValueError:
            return False
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
            or ip.is_unspecified
        ):
            return False

    return True
