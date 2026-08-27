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


def test_pieces_from_gallery_maps_paintings():
    gallery = {
        "paintings": [
            {
                "id": "p_1",
                "title": "Great American Buffalo",
                "size": "16x24",
                "price": "230.40",
                "buyUrl": "",
                "status": "available",
                "url": "https://example.com/buffalo.jpg",
            },
            {
                "id": "p_2",
                "title": "Sold Work",
                "size": "10x10",
                "price": "100",
                "buyUrl": "https://buy.example/x",
                "status": "sold",
                "url": "https://example.com/sold.jpg",
            },
            {
                "id": "p_3",
                "title": "Reserved",
                "price": "50",
                "status": "reserved",
            },
            {"title": "missing id"},  # skipped
        ],
        "galleries": {"featured": ["https://example.com/f.jpg"]},
    }
    pieces = logic.pieces_from_gallery(gallery)
    assert len(pieces) == 3

    by_id = {p.id: p for p in pieces}
    assert by_id["p_1"].status == "listed"
    assert by_id["p_1"].for_sale is True
    assert by_id["p_1"].price == 230.40
    # Priced + available with no explicit Payment Link → shareable ?buy= deep link.
    assert by_id["p_1"].buy_url == "https://www.codycarlson.art/?buy=p_1"
    assert by_id["p_1"].image_url == "https://example.com/buffalo.jpg"
    assert by_id["p_1"].medium == "Painting"

    assert by_id["p_2"].status == "sold"
    assert by_id["p_2"].for_sale is False
    assert by_id["p_2"].buy_url == "https://buy.example/x"

    assert by_id["p_3"].status == "listed"
    assert by_id["p_3"].for_sale is False


def test_pieces_from_gallery_buy_url_deep_link_and_explicit_wins():
    gallery = {
        "paintings": [
            {"id": "auto", "title": "Auto", "price": "75", "status": "available"},
            {
                "id": "explicit",
                "title": "Explicit",
                "price": "75",
                "status": "available",
                "buyUrl": "https://buy.stripe.com/abc",
            },
            {"id": "free", "title": "No Price", "status": "available"},
        ]
    }
    by_id = {p.id: p for p in logic.pieces_from_gallery(gallery)}
    # Priced + available with no link → generated deep link.
    assert by_id["auto"].buy_url == "https://www.codycarlson.art/?buy=auto"
    # An explicit admin-set Payment Link always wins.
    assert by_id["explicit"].buy_url == "https://buy.stripe.com/abc"
    # No price → no auto link (can't check out).
    assert by_id["free"].buy_url is None


def test_checkout_summary_counts_price_only_pieces_as_buyable():
    # The exact shape that made the old diagnosis cry "no way to buy": an
    # available, priced painting with empty buyUrl AND no stripePriceId. On-site
    # checkout prices it from `price`, so it IS buyable.
    gallery = {
        "paintings": [
            {"id": "p_1", "title": "Buffalo", "price": "230.40",
             "buyUrl": "", "status": "available"},
            {"id": "p_2", "title": "Sold", "price": "100",
             "status": "sold"},  # not buyable
            {"id": "p_3", "title": "No Price", "status": "available"},  # no price
        ]
    }
    summary = logic.checkout_summary(gallery)
    assert summary.on_site_checkout is True
    assert summary.buyable_count == 1
    assert summary.buyable_ids == ["p_1"]
    assert summary.for_sale_count == 2  # p_1 and p_3 are available/for sale


def test_checkout_summary_empty_when_nothing_buyable():
    summary = logic.checkout_summary({"paintings": []})
    assert summary.buyable_count == 0
    assert summary.buyable_ids == []


def test_pieces_from_gallery_includes_sculptures():
    # The site sells sculptures too (own store + on-site checkout), so they must
    # be ingested as inventory — not left out and wrongly reported "not buyable".
    gallery = {
        "paintings": [
            {"id": "p_1", "title": "So seepee", "price": "205", "status": "available"},
        ],
        "sculptures": [
            {"id": "s_1", "title": "Walleye Carving", "price": "550",
             "buyUrl": "", "status": "available"},
            {"id": "s_2", "title": "Fox", "status": "sold", "price": "300"},
        ],
    }
    pieces = logic.pieces_from_gallery(gallery)
    by_id = {p.id: p for p in pieces}
    assert set(by_id) == {"p_1", "s_1", "s_2"}
    # Available, priced sculpture with no explicit link → buyable via deep link.
    assert by_id["s_1"].for_sale is True
    assert by_id["s_1"].buy_url == "https://www.codycarlson.art/?buy=s_1"
    # Default medium for a sculpture entry that doesn't state its own.
    assert by_id["s_1"].medium == "Sculpture"
    assert by_id["s_2"].for_sale is False  # sold


def test_checkout_summary_counts_sculptures_as_buyable():
    # A priced, available sculpture is buyable exactly like a painting; the
    # summary must include it (the bug: it counted paintings only).
    gallery = {
        "paintings": [
            {"id": "p_1", "title": "Cat", "price": "205", "status": "available"},
        ],
        "sculptures": [
            {"id": "s_1", "title": "Buffalo Carving", "price": "525", "status": "available"},
        ],
    }
    summary = logic.checkout_summary(gallery)
    assert summary.buyable_count == 2
    assert set(summary.buyable_ids) == {"p_1", "s_1"}
    assert summary.for_sale_count == 2


def test_rotate_daily_windows_and_covers():
    items = list(range(14))
    # Same day is deterministic; different days shift the window.
    assert logic.rotate_daily(items, 4, day=0) == [0, 1, 2, 3]
    assert logic.rotate_daily(items, 4, day=1) == [4, 5, 6, 7]
    # Wraps around the end of the list.
    assert logic.rotate_daily(items, 4, day=3) == [12, 13, 0, 1]
    # Over a cycle of days, every item gets covered.
    seen = set()
    for d in range(14):
        seen.update(logic.rotate_daily(items, 4, day=d))
    assert seen == set(items)
    # Edge cases.
    assert logic.rotate_daily([], 4, day=2) == []
    assert logic.rotate_daily([1, 2], 0, day=5) == [2]  # n clamped to >=1; start=(5*1)%2=1


def test_pieces_from_gallery_sets_kind():
    gallery = {
        "paintings": [{"id": "p1", "title": "Cat", "price": "200", "status": "available"}],
        "sculptures": [{"id": "s1", "title": "Walleye", "price": "550", "status": "available"}],
    }
    by_id = {p.id: p for p in logic.pieces_from_gallery(gallery)}
    assert by_id["p1"].kind == "painting"
    assert by_id["s1"].kind == "sculpture"


def test_daily_focus_balances_sculptures_and_paintings():
    from agents.models import ArtPiece

    def mk(i, kind):
        return ArtPiece(id=f"{kind}{i}", title=f"{kind}{i}", medium="m",
                        status="listed", kind=kind, for_sale=True, price=100.0)

    pieces = [mk(i, "sculpture") for i in range(4)] + [mk(i, "painting") for i in range(10)]
    focus = logic.daily_focus(pieces, sculptures=2, paintings=4, day=0)
    kinds = [p.kind for p in focus]
    assert kinds.count("sculpture") == 2
    assert kinds.count("painting") == 4
    # Different day → different pieces (rotation), same balance.
    focus2 = logic.daily_focus(pieces, sculptures=2, paintings=4, day=1)
    assert [p.id for p in focus2] != [p.id for p in focus]
    assert [p.kind for p in focus2].count("sculpture") == 2


def test_daily_focus_handles_short_pools():
    from agents.models import ArtPiece

    only_two_sculpt = [
        ArtPiece(id=f"s{i}", title="s", medium="m", status="listed",
                 kind="sculpture", for_sale=True) for i in range(2)
    ]
    # Asking for 2 sculptures + 4 paintings when there are 2 sculptures / 0 paintings.
    focus = logic.daily_focus(only_two_sculpt, sculptures=2, paintings=4, day=3)
    assert len(focus) == 2 and all(p.kind == "sculpture" for p in focus)


def test_pieces_from_gallery_handles_error_payload():
    assert logic.pieces_from_gallery({"ok": False, "error": "boom"}) == []
    assert logic.pieces_from_gallery({}) == []


def test_merge_gallery_keeps_local_only_and_preserves_notes():
    local = [
        ArtPiece(
            id="summer-walleye",
            title="Summer Walleye",
            medium="Box elder wood carving",
            status="finished",
            outdoor_ready=True,
            notes="Local carving notes",
        ),
        ArtPiece(
            id="p_1",
            title="Old Title",
            medium="Acrylic on canvas",
            status="finished",
            notes="Hand notes about this painting",
            outdoor_ready=False,
        ),
    ]
    live = [
        ArtPiece(
            id="p_1",
            title="Great American Buffalo",
            medium="Painting",
            status="listed",
            size="16x24",
            price=230.40,
            for_sale=True,
            notes="Synced from live gallery API",
            image_url="https://example.com/buffalo.jpg",
        ),
        ArtPiece(
            id="p_new",
            title="New Piece",
            medium="Painting",
            status="listed",
            price=100.0,
            for_sale=True,
            notes="Synced from live gallery API",
        ),
    ]
    merged = logic.merge_gallery_into_pieces(local, live)
    by_id = {p.id: p for p in merged}

    assert set(by_id) == {"summer-walleye", "p_1", "p_new"}
    assert by_id["summer-walleye"].outdoor_ready is True
    assert by_id["p_1"].title == "Great American Buffalo"
    assert by_id["p_1"].price == 230.40
    assert by_id["p_1"].for_sale is True
    assert by_id["p_1"].notes == "Hand notes about this painting"
    assert by_id["p_1"].medium == "Acrylic on canvas"  # local more specific
    assert by_id["p_new"].title == "New Piece"
