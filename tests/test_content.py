"""Tests for the deterministic content scaffolding (no nooa / LLM required)."""

from __future__ import annotations

from datetime import date

from agents import content
from agents.models import ArtPiece


def _piece(**kw) -> ArtPiece:
    base = dict(id="buffalo", title="Great American Buffalo", medium="Acrylic on canvas", status="listed")
    base.update(kw)
    return ArtPiece(**base)


def test_default_hashtags_are_relevant_and_capped():
    tags = content.default_hashtags(_piece(for_sale=True), "tiktok")
    assert "#northdakotaart" in tags
    assert "#acrylic" in tags
    assert "#artforsale" in tags
    assert "#arttok" in tags
    assert len(tags) <= 12
    assert len(tags) == len(set(tags))  # deduped


def test_posting_schedule_spreads_and_rotates_platforms():
    slots = content.posting_schedule(date(2026, 1, 1), days=14, per_week=3)
    # 3/week over 2 weeks, step = 7 // 3 = 2 days → 7 slots across 14 days.
    assert len(slots) == 7
    # Dates strictly increasing.
    dates = [d for d, _ in slots]
    assert dates == sorted(dates)
    assert all((dates[i + 1] - dates[i]).days == 2 for i in range(len(dates) - 1))
    # Platforms rotate through all three.
    assert {p for _, p in slots} == {"tiktok", "instagram", "facebook"}


def test_posting_schedule_zero_per_week_is_empty():
    assert content.posting_schedule(date(2026, 1, 1), per_week=0) == []


def test_blank_plan_uses_native_formats():
    posts = content.blank_plan_for_piece(_piece(), date(2026, 1, 1), days=7, per_week=3)
    assert posts  # non-empty
    by_platform = {p.platform: p.format for p in posts}
    assert by_platform["tiktok"] == "short"
    assert by_platform["instagram"] == "reel"
    assert by_platform["facebook"] == "post"
    # Every post is tied to the piece and carries hashtags + a scheduled date.
    assert all(p.related_piece_id == "buffalo" for p in posts)
    assert all(p.hashtags for p in posts)
    assert all(p.scheduled_for for p in posts)


def test_render_plan_lists_every_post():
    posts = content.blank_plan_for_piece(_piece(), date(2026, 1, 1), days=7, per_week=3)
    md = content.render_plan("Great American Buffalo", posts)
    assert "# Content plan: Great American Buffalo" in md
    assert md.count("· tiktok ·") + md.count("· instagram ·") + md.count("· facebook ·") == len(posts)


def test_render_plan_empty():
    assert "No posts planned." in content.render_plan("X", [])
