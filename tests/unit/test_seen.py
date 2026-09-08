"""The cross-run ledger, and its refusal to block a run when it is damaged."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from catchup.seen import SeenLedger, run_id_for
from catchup.sources.models import Item

ITEM = Item("A release", "https://example.com/post", "Example", date(2026, 9, 2))


def test_recording_then_checking_round_trips() -> None:
    ledger = SeenLedger.empty().record([ITEM], run_id="2026-09-08")

    assert ITEM.url in ledger
    assert len(ledger) == 1


def test_urls_are_normalized_before_comparison() -> None:
    """The same story with a tracking tag must not slip past as unseen."""
    ledger = SeenLedger.empty().record([ITEM], run_id="2026-09-08")

    assert "https://example.com/post?utm_source=x" in ledger
    assert "https://example.com/post/" in ledger
    assert "https://example.com/other" not in ledger


def test_recording_is_pure() -> None:
    """The caller decides when to persist, which is what keeps dry runs clean."""
    original = SeenLedger.empty()

    original.record([ITEM], run_id="2026-09-08")

    assert len(original) == 0


def test_the_first_run_to_publish_an_item_keeps_it() -> None:
    first = SeenLedger.empty().record([ITEM], "2026-09-01")
    ledger = first.record([ITEM], "2026-09-08")

    assert ledger.entries["https://example.com/post"] == "2026-09-01"


def test_unseen_filters_a_batch() -> None:
    other = Item("Another", "https://example.com/b", "Example", date(2026, 9, 2))
    ledger = SeenLedger.empty().record([ITEM], "2026-09-01")

    assert ledger.unseen([ITEM, other]) == (other,)


def test_save_and_load_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "nested" / "seen.json"

    SeenLedger.empty().record([ITEM], "2026-09-08").save(path)

    assert ITEM.url in SeenLedger.load(path)


def test_a_missing_ledger_loads_empty(tmp_path: Path) -> None:
    assert len(SeenLedger.load(tmp_path / "absent.json")) == 0


def test_a_corrupt_ledger_does_not_block_a_run(tmp_path: Path) -> None:
    """Losing the ledger costs a few repeats. Refusing to run costs the digest."""
    path = tmp_path / "seen.json"
    path.write_text("{not json at all")

    assert len(SeenLedger.load(path)) == 0


def test_a_ledger_of_the_wrong_shape_loads_empty(tmp_path: Path) -> None:
    path = tmp_path / "seen.json"
    path.write_text('["a list, not an object"]')

    assert len(SeenLedger.load(path)) == 0


def test_run_id_is_the_period_end() -> None:
    assert run_id_for(date(2026, 9, 8)) == "2026-09-08"
