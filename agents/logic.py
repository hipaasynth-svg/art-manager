"""
Pure, deterministic business logic for the Art Manager.

These functions take plain data and return plain data — no LLM calls, no
network, no nooa dependency — so they are cheap to reason about and easy to
unit-test. The agent delegates its non-judgment work here.
"""

from __future__ import annotations

from .models import PIECE_STATUSES, ArtPiece


def finished_unlisted(pieces: list[ArtPiece]) -> list[ArtPiece]:
    """Pieces that are finished but not yet listed or sold.

    Because status is a single lifecycle enum, a piece that has been listed or
    sold carries the ``listed`` / ``sold`` status rather than ``finished``, so
    filtering on ``finished`` already excludes them.
    """
    return [p for p in pieces if p.status == "finished"]


def in_progress(pieces: list[ArtPiece]) -> list[ArtPiece]:
    return [p for p in pieces if p.status == "in_progress"]


def revenue_gap(monthly_goal: float, revenue_this_month: float) -> float:
    """Remaining revenue needed to hit the monthly goal (never negative)."""
    return max(0.0, monthly_goal - revenue_this_month)


def get_piece(pieces: list[ArtPiece], piece_id: str) -> ArtPiece | None:
    for p in pieces:
        if p.id == piece_id:
            return p
    return None


def upsert_piece(pieces: list[ArtPiece], piece: ArtPiece) -> list[ArtPiece]:
    """Return a new list with ``piece`` added or replacing an existing id."""
    return [p for p in pieces if p.id != piece.id] + [piece]


def set_status(pieces: list[ArtPiece], piece_id: str, status: str) -> bool:
    """Update a piece's status in place.

    Returns True if a piece was found and updated. Raises ``ValueError`` for an
    unknown status so bad transitions fail loudly instead of silently.
    """
    if status not in PIECE_STATUSES:
        raise ValueError(
            f"Unknown status {status!r}; expected one of {PIECE_STATUSES}"
        )
    for p in pieces:
        if p.id == piece_id:
            p.status = status  # validated by the model (validate_assignment)
            return True
    return False
