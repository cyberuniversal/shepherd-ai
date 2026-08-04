"""Process-level network isolation for measured local model inference."""

from __future__ import annotations

from contextlib import contextmanager
import ipaddress
import os
import socket
import threading
from typing import Iterator
from unittest.mock import patch


OFFLINE_ENVIRONMENT = {
    "HF_HUB_OFFLINE": "1",
    "TRANSFORMERS_OFFLINE": "1",
}

_GUARD_LOCK = threading.RLock()


class NetworkIsolationError(RuntimeError):
    """Raised when measured inference attempts non-loopback network access."""


@contextmanager
def offline_inference_guard() -> Iterator[None]:
    """Block non-loopback Python sockets and force supported libraries offline.

    This is process-level isolation for Python socket users. It is not an
    operating-system firewall and cannot intercept networking performed wholly
    inside native extensions.
    """

    with _GUARD_LOCK:
        previous_environment = {
            name: os.environ.get(name) for name in OFFLINE_ENVIRONMENT
        }
        os.environ.update(OFFLINE_ENVIRONMENT)

        original_connect = socket.socket.connect
        original_connect_ex = socket.socket.connect_ex
        original_create_connection = socket.create_connection
        original_getaddrinfo = socket.getaddrinfo

        def guarded_connect(instance, address):
            _require_loopback_address(address, family=instance.family)
            return original_connect(instance, address)

        def guarded_connect_ex(instance, address):
            _require_loopback_address(address, family=instance.family)
            return original_connect_ex(instance, address)

        def guarded_create_connection(address, *args, **kwargs):
            _require_loopback_address(address)
            return original_create_connection(address, *args, **kwargs)

        def guarded_getaddrinfo(host, *args, **kwargs):
            _require_loopback_host(host)
            return original_getaddrinfo(host, *args, **kwargs)

        try:
            with (
                patch.object(socket.socket, "connect", guarded_connect),
                patch.object(socket.socket, "connect_ex", guarded_connect_ex),
                patch.object(
                    socket,
                    "create_connection",
                    guarded_create_connection,
                ),
                patch.object(socket, "getaddrinfo", guarded_getaddrinfo),
            ):
                yield
        finally:
            for name, previous in previous_environment.items():
                if previous is None:
                    os.environ.pop(name, None)
                else:
                    os.environ[name] = previous


def _require_loopback_address(
    address,
    *,
    family: socket.AddressFamily | int | None = None,
) -> None:
    unix_family = getattr(socket, "AF_UNIX", None)
    if unix_family is not None and family == unix_family:
        return
    if not isinstance(address, tuple) or not address:
        raise NetworkIsolationError(
            f"non-loopback network access blocked: {address!r}"
        )
    _require_loopback_host(address[0])


def _require_loopback_host(host) -> None:
    if isinstance(host, bytes):
        try:
            host = host.decode("ascii")
        except UnicodeDecodeError as error:
            raise NetworkIsolationError(
                "non-loopback network access blocked: non-ASCII host"
            ) from error
    if not isinstance(host, str):
        raise NetworkIsolationError(
            f"non-loopback network access blocked: {host!r}"
        )
    normalized = host.strip().lower().rstrip(".")
    if normalized == "localhost":
        return
    address_text = normalized.split("%", maxsplit=1)[0]
    try:
        address = ipaddress.ip_address(address_text)
    except ValueError as error:
        raise NetworkIsolationError(
            f"non-loopback network access blocked: {host!r}"
        ) from error
    if not address.is_loopback:
        raise NetworkIsolationError(
            f"non-loopback network access blocked: {host!r}"
        )
