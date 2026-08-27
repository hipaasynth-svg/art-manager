"""Tests for the deterministic phone call sheet (pure; no LLM)."""

from __future__ import annotations

from agents import callsheet
from agents.models import ArtPiece, BuyerLead


def _piece(**kw):
    base = dict(id="p1", title="Walleye #2", medium="Boxelder", status="listed",
               price=550.0, for_sale=True, buy_url="https://www.codycarlson.art/?buy=p1")
    base.update(kw)
    return ArtPiece(**base)


def test_format_price():
    assert callsheet.format_price(550.0) == "$550"
    assert callsheet.format_price(204.8) == "$204.80"
    assert callsheet.format_price(None) == ""


def test_call_script_mentions_piece_and_lead():
    piece = _piece()
    lead = BuyerLead(name="North Star Lodge", phone="(701) 555-0100",
                     why_fit="A walleye carving fits a lake lodge.", contact_name="Pat")
    script = callsheet.call_script(piece, lead)
    joined = "\n".join(script)
    assert "Cody Carlson" in joined
    assert "Walleye #2" in joined
    assert "North Star Lodge" in joined
    assert "Pat" in joined
    assert "https://www.codycarlson.art/?buy=p1" in joined


def test_render_piece_calls_splits_phone_and_no_phone():
    piece = _piece()
    leads = [
        BuyerLead(name="Has Phone", phone="(701) 555-0101", why_fit="fit A"),
        BuyerLead(name="No Phone", website="https://example.com", why_fit="fit B"),
    ]
    text = callsheet.render_piece_calls(piece, leads)
    assert "Call these (in order)" in text
    assert "Has Phone" in text and "(701) 555-0101" in text
    assert "No phone — walk in or email" in text
    assert "No Phone" in text


def test_render_call_sheet_counts_calls():
    piece = _piece()
    leads = [
        BuyerLead(name="A", phone="1"),
        BuyerLead(name="B", phone="2"),
        BuyerLead(name="C"),  # no phone → not counted as a call
    ]
    sheet = callsheet.render_call_sheet([(piece, leads)], date_str="2026-08-27")
    assert "Daily Call Sheet — 2026-08-27" in sheet
    assert "2 call(s) queued across 1 piece(s)" in sheet


def test_render_call_sheet_empty():
    assert "No pieces to work today" in callsheet.render_call_sheet([])
