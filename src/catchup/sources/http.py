"""The one place outbound HTTP is configured.

Every request the system makes carries the same descriptive User-Agent and timeout, and
every failure is classified the same way, so no source can quietly reach the network on
its own terms.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterable, Sequence
from concurrent.futures import ThreadPoolExecutor

import httpx

logger = logging.getLogger(__name__)

USER_AGENT = "catchup-tech/0.1 (+https://github.com/; personal AI news digest)"
TIMEOUT_SECONDS = 15.0
MAX_CONCURRENCY = 5


def client(timeout: float = TIMEOUT_SECONDS) -> httpx.Client:
    """An httpx client with the project's headers, timeout, and redirect policy."""
    return httpx.Client(
        headers={"User-Agent": USER_AGENT, "Accept-Encoding": "gzip, deflate"},
        timeout=timeout,
        follow_redirects=True,
    )


def fetch_bytes(url: str, http: httpx.Client) -> bytes:
    """GET `url` and return the body. Raises on a non-2xx status."""
    response = http.get(url)
    response.raise_for_status()
    return response.content


def in_parallel[T, R](
    work: Iterable[T],
    fn: Callable[[T], R],
    max_workers: int = MAX_CONCURRENCY,
) -> Sequence[R]:
    """Run `fn` over `work` with a bounded pool, preserving input order.

    Bounded because the sources are other people's servers. Order is preserved so a run
    over the same config produces the same ordering, which keeps diffs of the run record
    readable.
    """
    items = list(work)
    if not items:
        return ()
    with ThreadPoolExecutor(max_workers=min(max_workers, len(items))) as pool:
        return tuple(pool.map(fn, items))


def describe_error(exc: BaseException) -> str:
    """A short, loggable reason string for a failed fetch."""
    if isinstance(exc, httpx.TimeoutException):
        return "timeout"
    if isinstance(exc, httpx.HTTPStatusError):
        return f"http {exc.response.status_code}"
    if isinstance(exc, httpx.HTTPError):
        return f"connection error ({type(exc).__name__})"
    return type(exc).__name__
