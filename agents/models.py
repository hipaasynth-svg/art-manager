"""
Data models for the Art Manager agent.

These are framework-agnostic (only depend on pydantic), so they can be
imported and unit-tested without the nooa runtime or an LLM.
"""

from __future__ import annotations

from typing import Any, Literal

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
    # Optional catalog image (from live gallery API).
    image_url: str | None = None
    # Selling: whether this piece is actively offered for sale, and the direct
    # checkout link (e.g. a Stripe Payment Link or Gumroad URL) buyers click to
    # pay. A portfolio-only piece has for_sale=False and no buy_url.
    for_sale: bool = False
    buy_url: str | None = None


class ContentItem(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    id: str
    type: Literal["post", "reel", "story", "email", "listing"]
    platform: str
    status: Literal["idea", "drafted", "scheduled", "posted"]
    related_piece_id: str | None = None
    scheduled_for: str | None = None


Platform = Literal["tiktok", "instagram", "facebook"]
ContentFormat = Literal["post", "reel", "short", "story"]


class SocialPost(BaseModel):
    """One piece of social content for TikTok / Instagram / Facebook."""

    model_config = ConfigDict(validate_assignment=True)

    platform: Platform
    format: ContentFormat
    related_piece_id: str | None = None
    hook: str = ""  # the scroll-stopping first line / first 2 seconds
    caption: str = ""
    hashtags: list[str] = Field(default_factory=list)
    visual_brief: str = ""  # what to shoot / show (the "visuals")
    script: str = ""  # shot-by-shot script for reels / shorts
    cta: str = ""
    status: Literal["idea", "drafted", "scheduled", "posted"] = "idea"
    scheduled_for: str = ""  # ISO date, when scheduled


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


class SiteImage(BaseModel):
    src: str
    alt: str = ""


class SiteSnapshot(BaseModel):
    """What the agent actually saw when it read the live website.

    Produced by ``agents.site`` from the real page HTML (and any config script),
    so downstream analysis is grounded in the current site instead of guesses.
    """

    url: str
    fetched_at: str = ""
    ok: bool = False
    status: int | None = None
    title: str = ""
    description: str = ""
    text: str = ""  # visible text, script/style stripped and whitespace-collapsed
    images: list[SiteImage] = Field(default_factory=list)
    links: list[str] = Field(default_factory=list)
    emails: list[str] = Field(default_factory=list)
    phones: list[str] = Field(default_factory=list)
    prices: list[str] = Field(default_factory=list)  # e.g. ["$450", "$1,200"]
    scripts: list[str] = Field(default_factory=list)  # script src URLs
    # Raw gallery API response used to build this snapshot.
    gallery_data: dict[str, Any] = Field(default_factory=dict)
    # Retained for compatibility with older saved snapshots.
    data_scripts: dict[str, str] = Field(default_factory=dict)
    error: str = ""


class PieceSEO(BaseModel):
    """Search-engine + AI-search metadata for one art piece.

    The deterministic parts (``agents/seo.py``) are always available; the LLM
    can enrich ``meta_description`` / ``keywords`` / ``og_*`` / ``alt_text`` with
    compelling, human copy.
    """

    piece_id: str
    title_tag: str = ""
    meta_description: str = ""
    keywords: list[str] = Field(default_factory=list)
    canonical_url: str = ""
    og_title: str = ""
    og_description: str = ""
    og_image: str = ""
    alt_text: str = ""
    # schema.org structured data (JSON-LD) a crawler / AI search can read.
    json_ld: dict[str, Any] = Field(default_factory=dict)


class AgentState(BaseModel):
    """Serializable snapshot of the agent's mutable business state."""

    pieces: list[ArtPiece] = Field(default_factory=list)
    content_queue: list[ContentItem] = Field(default_factory=list)
    pipeline: SalesPipeline = Field(default_factory=SalesPipeline)
    monthly_revenue_goal: float = 2000.0
    focus_this_week: str = "finish and list highest-leverage pieces"
    last_research: list[ResearchInsight] = Field(default_factory=list)
    pending_changes: list[SiteChange] = Field(default_factory=list)
    # What the agent learned from the live site on its last read.
    last_site_snapshot: SiteSnapshot | None = None
