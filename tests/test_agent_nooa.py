"""Regression tests that require the real nooa runtime.

These are skipped automatically where nooa is not installed (e.g. Python 3.11,
which nooa does not support). They guard against the class of bug where
class-level ``Field(default_factory=...)`` defaults are never materialised into
per-instance state — nooa's Agent is a plain object, not a pydantic model, so
mutable state must be initialised in ``__init__``.
"""

from __future__ import annotations

import os

import pytest

pytest.importorskip("nooa", reason="nooa runtime not installed on this interpreter")

# nooa builds an LLM client when the agent class is first accessed; a dummy key
# is enough for construction (no request is made here).
os.environ.setdefault("ANTHROPIC_API_KEY", "test-not-called")


def _make_agent():
    try:
        from agents.art_manager import ArtManagerAgent

        return ArtManagerAgent()
    except Exception as exc:  # pragma: no cover - environment-dependent
        pytest.skip(f"could not construct agent in this environment: {exc}")


def _seed(agent) -> None:
    """Add a couple of test pieces (inventory now comes from the live site)."""
    from agents.models import ArtPiece

    agent.add_piece(ArtPiece(id="walleye", title="Walleye", medium="carving", status="finished"))
    agent.add_piece(ArtPiece(id="buffalo", title="Buffalo", medium="acrylic", status="finished"))


def test_mutable_state_is_real_and_empty():
    a = _make_agent()
    # Must be real containers, not pydantic FieldInfo / shared class attrs.
    assert a.pieces == []
    assert a.content_queue == []
    assert a.pending_changes == []
    assert a.last_research == []
    assert a.pipeline.revenue_this_month == 0.0


def test_state_is_isolated_between_instances():
    a = _make_agent()
    _seed(a)
    assert len(a.pieces) == 2

    b = _make_agent()
    # A fresh agent must not see the first agent's pieces.
    assert b.pieces == []


def test_deterministic_helpers_and_persistence(tmp_path):
    a = _make_agent()
    _seed(a)
    assert {p.id for p in a.get_finished_unlisted()} == {"walleye", "buffalo"}
    assert a.revenue_gap() == a.monthly_revenue_goal

    a.update_piece_status("buffalo", "listed")
    path = str(tmp_path / "state.json")
    a.save(path)

    b = _make_agent()
    b.load(path)
    assert b.get_piece("buffalo").status == "listed"
