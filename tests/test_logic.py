"""Tests for the pure business logic (no nooa / LLM required)."""

from __future__ import annotations

import pytest

from agents import logic
from agents.models import ArtPiece


def _piece(pid: str, status: str) -> ArtPiece:
    return ArtPiece(id=pid, title=pid.title(), medium="test", status=status)


def test_finished_unlisted_excludes_other_states():
    pieces = [
        _piece("a", "finished"),
        _piece("b", "in_progress"),
        _piece("c", "listed"),
        _piece("d", "sold"),
        _piece("e", "finished"),
    ]
    got = {p.id for p in logic.finished_unlisted(pieces)}
    assert got == {"a", "e"}


def test_in_progress_filter():
    pieces = [_piece("a", "in_progress"), _piece("b", "finished")]
    assert [p.id for p in logic.in_progress(pieces)] == ["a"]


def test_for_sale_and_sellable():
    portfolio = _piece("a", "finished")  # for_sale defaults False
    listed = ArtPiece(id="b", title="B", medium="t", status="finished", for_sale=True)
    ready = ArtPiece(
        id="c", title="C", medium="t", status="finished",
        for_sale=True, price=450.0, buy_url="https://buy.stripe.com/test",
    )
    pieces = [portfolio, listed, ready]
    assert [p.id for p in logic.for_sale_pieces(pieces)] == ["b", "c"]
    # Only the one with a price AND a checkout link is sellable right now.
    assert [p.id for p in logic.sellable_pieces(pieces)] == ["c"]


def test_revenue_gap_never_negative():
    assert logic.revenue_gap(2000.0, 500.0) == 1500.0
    assert logic.revenue_gap(2000.0, 2500.0) == 0.0


def test_get_piece():
    pieces = [_piece("a", "finished")]
    assert logic.get_piece(pieces, "a").id == "a"
    assert logic.get_piece(pieces, "missing") is None


def test_upsert_piece_adds_and_replaces():
    pieces: list[ArtPiece] = []
    pieces = logic.upsert_piece(pieces, _piece("a", "concept"))
    assert len(pieces) == 1

    # Replacing keeps a single entry and takes the new value.
    updated = ArtPiece(id="a", title="A2", medium="test", status="finished")
    pieces = logic.upsert_piece(pieces, updated)
    assert len(pieces) == 1
    assert pieces[0].title == "A2"
    assert pieces[0].status == "finished"


def test_set_status_updates_and_reports():
    pieces = [_piece("a", "concept")]
    assert logic.set_status(pieces, "a", "finished") is True
    assert pieces[0].status == "finished"
    assert logic.set_status(pieces, "missing", "finished") is False


def test_set_status_rejects_unknown_status():
    pieces = [_piece("a", "concept")]
    with pytest.raises(ValueError):
        logic.set_status(pieces, "a", "bogus")
    # Unchanged after the failed transition.
    assert pieces[0].status == "concept"
