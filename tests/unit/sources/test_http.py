"""Outbound HTTP policy, in one place.

No source gets to reach the network on its own terms.
"""

from __future__ import annotations

import httpx
import pytest

from catchup.sources.http import USER_AGENT, client, describe_error, in_parallel


def test_every_request_identifies_itself() -> None:
    """Feed publishers are other people's servers; anonymous scraping is rude."""
    with client() as http:
        assert http.headers["User-Agent"] == USER_AGENT
        assert "catchup" in USER_AGENT


def test_redirects_are_followed() -> None:
    """Feed URLs move; a 301 is not a failure."""
    with client() as http:
        assert http.follow_redirects is True


@pytest.mark.parametrize(
    ("exc", "expected"),
    [
        (httpx.ReadTimeout("slow"), "timeout"),
        (httpx.ConnectTimeout("slow"), "timeout"),
        (
            httpx.HTTPStatusError(
                "boom",
                request=httpx.Request("GET", "https://x/"),
                response=httpx.Response(503),
            ),
            "http 503",
        ),
        (httpx.ConnectError("no route"), "connection error (ConnectError)"),
        (ValueError("bad xml"), "ValueError"),
    ],
)
def test_failures_get_a_short_loggable_reason(exc: Exception, expected: str) -> None:
    """These strings land in the digest footer, so they are prose, not tracebacks."""
    assert describe_error(exc) == expected


def test_parallel_work_preserves_input_order() -> None:
    """Results are zipped back onto their inputs, so a reorder would mislabel them."""
    assert list(in_parallel(range(20), lambda n: n * 2)) == [n * 2 for n in range(20)]


def test_parallel_work_on_nothing_starts_no_pool() -> None:
    assert in_parallel([], lambda n: n) == ()
