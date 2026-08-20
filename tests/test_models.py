"""Tests for the pydantic models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from agents.models import ArtPiece


def test_valid_piece():
    p = ArtPiece(id="x", title="X", medium="wood", status="finished")
    assert p.outdoor_ready is False
    assert p.price is None


def test_invalid_status_rejected_at_construction():
    with pytest.raises(ValidationError):
        ArtPiece(id="x", title="X", medium="wood", status="bogus")


def test_validate_assignment_rejects_bad_status():
    p = ArtPiece(id="x", title="X", medium="wood", status="concept")
    with pytest.raises(ValidationError):
        p.status = "not-a-status"
    # Assignment did not corrupt the value.
    assert p.status == "concept"
