"""URL normalization — what makes two copies of one story collapse into one item."""

from __future__ import annotations

import pytest

from catchup.sources.urls import normalize_url


@pytest.mark.parametrize(
    ("a", "b"),
    [
        ("https://example.com/post", "https://example.com/post/"),
        ("https://Example.COM/post", "https://example.com/post"),
        ("https://example.com/post", "https://example.com/post#section"),
        ("https://example.com/post", "https://example.com/post?utm_source=hn"),
        ("https://example.com/post", "https://example.com/post?ref=newsletter"),
        (
            "https://example.com/post",
            "https://example.com/post?utm_campaign=x&fbclid=y",
        ),
        ("https://example.com/p?a=1&b=2", "https://example.com/p?b=2&a=1"),
        ("https://example.com:443/post", "https://example.com/post"),
        ("  https://example.com/post  ", "https://example.com/post"),
    ],
)
def test_equivalent_urls_normalize_together(a: str, b: str) -> None:
    assert normalize_url(a) == normalize_url(b)


@pytest.mark.parametrize(
    ("a", "b"),
    [
        # Meaningful query parameters are the resource, not decoration.
        ("https://youtube.com/watch?v=abc", "https://youtube.com/watch?v=def"),
        ("https://example.com/a", "https://example.com/b"),
        ("https://example.com/post", "http://example.com/post"),
        ("https://example.com/post", "https://other.com/post"),
        ("https://example.com:8080/p", "https://example.com/p"),
    ],
)
def test_distinct_urls_stay_distinct(a: str, b: str) -> None:
    assert normalize_url(a) != normalize_url(b)


def test_bare_host_keeps_a_root_path() -> None:
    assert normalize_url("https://example.com") == "https://example.com/"
