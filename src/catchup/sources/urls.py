"""URL normalization, so the same story from two sources is recognised as one.

The dedupe gate and the seen ledger both compare URLs. Comparing them raw fails on the
common case: an item arrives from a feed as `https://example.com/post` and from Hacker
News as `https://example.com/post/?utm_source=hn`, and both survive as separate items.
"""

from __future__ import annotations

from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

TRACKING_PREFIXES = ("utm_",)
TRACKING_PARAMS = frozenset(
    {"ref", "ref_src", "source", "fbclid", "gclid", "mc_cid", "mc_eid", "at_medium"}
)


def _is_tracking(key: str) -> bool:
    lowered = key.lower()
    return lowered in TRACKING_PARAMS or lowered.startswith(TRACKING_PREFIXES)


def normalize_url(url: str) -> str:
    """Return a comparable form of `url`.

    Lowercases the scheme and host, drops a default port, strips a trailing slash from
    the path, removes tracking parameters, drops the fragment, and sorts what remains.

    Query parameters that are not tracking are **kept** — `?v=abc123` and `?id=42` are
    the resource, not decoration, and merging them would lose real items.
    """
    parts = urlsplit(url.strip())
    host = parts.hostname or ""
    if parts.port and not (
        (parts.scheme == "https" and parts.port == 443)
        or (parts.scheme == "http" and parts.port == 80)
    ):
        host = f"{host}:{parts.port}"

    path = parts.path.rstrip("/") or "/"
    kept = sorted(
        (k, v)
        for k, v in parse_qsl(parts.query, keep_blank_values=True)
        if not _is_tracking(k)
    )
    return urlunsplit((parts.scheme.lower(), host, path, urlencode(kept), ""))
