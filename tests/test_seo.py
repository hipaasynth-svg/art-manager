"""Tests for the deterministic SEO / metadata builder (no LLM required)."""

from __future__ import annotations

from agents import seo
from agents.models import ArtPiece


def _sellable() -> ArtPiece:
    return ArtPiece(
        id="buffalo",
        title="Great American Buffalo",
        medium="Acrylic on canvas",
        status="listed",
        size="36x24",
        price=450.0,
        image_url="https://cdn.example.com/buffalo.jpg",
        for_sale=True,
        buy_url="https://www.codycarlson.art/?buy=buffalo",
    )


def test_piece_metadata_basics():
    m = seo.piece_metadata(_sellable())
    assert m.piece_id == "buffalo"
    assert m.title_tag == "Great American Buffalo — Acrylic on canvas by Cody Carlson"
    assert len(m.meta_description) <= 160
    assert "north dakota art" in m.keywords
    assert m.canonical_url == "https://www.codycarlson.art/?buy=buffalo"
    assert m.alt_text == "Great American Buffalo, Acrylic on canvas, 36x24"


def test_json_ld_has_offer_for_sellable():
    ld = seo.build_json_ld(_sellable(), "https://codycarlson.art")
    assert ld["@type"] == "VisualArtwork"
    assert ld["creator"]["name"] == "Cody Carlson"
    assert ld["image"] == "https://cdn.example.com/buffalo.jpg"
    offer = ld["offers"]
    assert offer["price"] == "450"
    assert offer["priceCurrency"] == "USD"
    assert offer["availability"] == "https://schema.org/InStock"
    assert offer["url"] == "https://www.codycarlson.art/?buy=buffalo"


def test_json_ld_sold_has_no_instock_and_no_offer_url():
    sold = ArtPiece(id="s", title="Sold", medium="Oil", status="sold", price=100.0)
    ld = seo.build_json_ld(sold, "https://codycarlson.art")
    assert ld["offers"]["availability"] == "https://schema.org/SoldOut"
    assert "url" not in ld["offers"]


def test_json_ld_portfolio_piece_has_no_offer():
    portfolio = ArtPiece(id="p", title="Study", medium="Ink", status="finished")
    ld = seo.build_json_ld(portfolio, "https://codycarlson.art")
    assert "offers" not in ld


def test_head_snippet_contains_tags_and_jsonld():
    snippet = seo.head_snippet(seo.piece_metadata(_sellable()))
    assert "<title>Great American Buffalo" in snippet
    assert 'name="description"' in snippet
    assert 'property="og:image"' in snippet
    assert 'application/ld+json' in snippet


def test_metadata_document_covers_every_piece():
    pieces = [_sellable(), ArtPiece(id="two", title="Second", medium="Wood", status="finished")]
    doc = seo.metadata_document(pieces)
    assert "# Piece metadata & SEO" in doc
    assert "Great American Buffalo (`buffalo`)" in doc
    assert "Second (`two`)" in doc
    # One fenced head snippet per piece.
    assert doc.count("```html") == 2
