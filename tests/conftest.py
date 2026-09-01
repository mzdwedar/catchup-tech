"""Test-wide policy.

Sockets are disabled for the whole suite via ``--disable-socket`` in
``pyproject.toml``. That is what keeps the default run offline and free: a test that
reaches for the network fails loudly instead of quietly costing money.

Tests marked ``live`` are the deliberate exception. They are deselected by default and
have their socket access restored here when explicitly selected with ``-m live``.
"""

from __future__ import annotations

import pytest
from pytest_socket import enable_socket


@pytest.fixture(autouse=True)
def _socket_policy(request: pytest.FixtureRequest) -> None:
    if request.node.get_closest_marker("live") is not None:
        enable_socket()
