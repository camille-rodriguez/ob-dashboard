"""Utility functions for network checks (ping, port reachability)."""

import subprocess
import socket


def is_host_reachable(host: str, timeout: int = 2) -> bool:
    """Return True if *host* responds to ICMP ping within *timeout* seconds."""
    try:
        result = subprocess.run(
            ["ping", "-c", "1", "-W", str(timeout), host],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=timeout + 1,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def is_port_open(host: str, port: int, timeout: int = 3) -> bool:
    """Return True if TCP *port* on *host* is accepting connections."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (OSError, socket.timeout):
        return False
