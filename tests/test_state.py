"""Tests for JSON state persistence."""

from __future__ import annotations

from agents.models import AgentState, ArtPiece, SalesPipeline
from agents.state import load_state, save_state


def test_load_missing_returns_empty(tmp_path):
    state = load_state(str(tmp_path / "does_not_exist.json"))
    assert isinstance(state, AgentState)
    assert state.pieces == []


def test_save_then_load_roundtrip(tmp_path):
    path = str(tmp_path / "nested" / "state.json")  # parent dir created on save
    state = AgentState(
        pieces=[ArtPiece(id="a", title="A", medium="wood", status="finished")],
        pipeline=SalesPipeline(revenue_this_month=750.0, closed_this_month=1),
        monthly_revenue_goal=3000.0,
        focus_this_week="ship the walleye listing",
    )
    save_state(state, path)

    loaded = load_state(path)
    assert loaded.monthly_revenue_goal == 3000.0
    assert loaded.focus_this_week == "ship the walleye listing"
    assert loaded.pipeline.revenue_this_month == 750.0
    assert [p.id for p in loaded.pieces] == ["a"]
    assert loaded.pieces[0].status == "finished"
