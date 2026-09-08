"""Test-wide policy.

Sockets are disabled for the whole suite via ``--disable-socket`` in
``pyproject.toml``. That is what keeps the default run offline and free: a test that
reaches for the network fails loudly instead of quietly costing money.

Tests marked ``live`` are the deliberate exception. They are deselected by default and
have their socket access restored here when explicitly selected with ``-m live``.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date
from pathlib import Path

import pytest
from pytest_socket import enable_socket

from catchup.sources.models import DateRange

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(autouse=True)
def _socket_policy(request: pytest.FixtureRequest) -> None:
    if request.node.get_closest_marker("live") is not None:
        enable_socket()


@pytest.fixture
def feed_bytes() -> Callable[[str], bytes]:
    """Read a recorded feed or API response from ``tests/fixtures/feeds``."""

    def read(name: str) -> bytes:
        return (FIXTURES / "feeds" / name).read_bytes()

    return read


@pytest.fixture
def wide_window() -> DateRange:
    """A window broad enough that recorded fixtures fall inside it.

    Fixtures age; pinning the window to the fixture's own dates would mean re-recording
    them every few months for no gain, since the window gate is tested directly.
    """
    return DateRange(start=date(2000, 1, 1), end=date(2100, 1, 1))
