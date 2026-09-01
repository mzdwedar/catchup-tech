"""Guards on the project skeleton itself.

These assert the properties the rest of the suite depends on, so a regression in
tooling configuration is caught here rather than as confusing failures elsewhere.
"""

from __future__ import annotations

import socket

import pytest
from pytest_socket import SocketBlockedError

import catchup


def test_package_imports() -> None:
    assert catchup.__version__


@pytest.mark.filterwarnings("ignore:A test tried to use socket.socket:UserWarning")
def test_sockets_are_blocked_by_default() -> None:
    """The offline guarantee is enforced, not merely intended."""
    with pytest.raises(SocketBlockedError):
        socket.socket(socket.AF_INET, socket.SOCK_STREAM)
