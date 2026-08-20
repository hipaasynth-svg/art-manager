"""
Data models for the Art Manager agent.

These are framework-agnostic (only depend on pydantic), so they can be
imported and unit-tested without the nooa runtime or an LLM.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# Allowed lifecycle states for a piece, in rough order.
PieceStatus = Literal["concept", "in_progress", "finished", "listed", "sold"]
PIECE_STATUSES: tuple[str, ...] = (
    "concept",
    "in_progress",
    "finished",
    "listed",
    "sold",
)


class ArtPiece(BaseModel):
    # validate_assignment ensures `piece.status = "bogus"` raises instead of
    # silently corrupting state.
    model_config = ConfigDict(validate_assignment=True)

    id: str
    title: str
    medium: str
    status: PieceStatus
    size: str = ""
    price: float | None = None
    notes: str = ""
    outdoor_ready: bool = False


class ContentItem(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    id: str
    type: Literal["post", "reel", "story", "email", "listing"]
    platform: str
    status: Literal["idea", "drafted", "scheduled", "posted"]
    related_piece_id: str | None = None
    scheduled_for: str | None = None


class SalesPipeline(BaseModel):
    leads: list[str] = Field(default_factory=list)
    active_conversations: list[str] = Field(default_factory=list)
    closed_this_month: int = 0
    revenue_this_month: float = 0.0


class SiteChange(BaseModel):
    title: str
    rationale: str
    files: list[str]
    priority: Literal["high", "medium", "low"]
    risk: Literal["low", "medium", "high"]


class ResearchInsight(BaseModel):
    source: str
    observation: str
    recommendation: str
    confidence: Literal["high", "medium", "low"]


class AgentState(BaseModel):
    """Serializable snapshot of the agent's mutable business state."""

    pieces: list[ArtPiece] = Field(default_factory=list)
    content_queue: list[ContentItem] = Field(default_factory=list)
    pipeline: SalesPipeline = Field(default_factory=SalesPipeline)
    monthly_revenue_goal: float = 2000.0
    focus_this_week: str = "finish and list highest-leverage pieces"
    last_research: list[ResearchInsight] = Field(default_factory=list)
    pending_changes: list[SiteChange] = Field(default_factory=list)
