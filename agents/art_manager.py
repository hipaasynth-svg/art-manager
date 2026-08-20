"""
Art Manager Agent — NOOA (NVIDIA Object-Oriented Agents)

Owns codycarlson.art, finds high-intent North Dakota buyers per piece,
and drives sales. Uses Claude Opus 4.8 for creative / sales work.

Install:
  pip install nooa pydantic

Run (example):
  export ANTHROPIC_API_KEY=...
  python -m agents.run_daily
"""

from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, Field

from nooa import Agent
from nooa.unifiedllm.registry import get_llm_client

# ---------- LLM ----------
# Requires ANTHROPIC_API_KEY in the environment
# Claude Opus 4.8 — complex agentic / sales / creative work
llm = get_llm_client("claude-opus-4-8")


# ---------- Data models ----------
class ArtPiece(BaseModel):
    id: str
    title: str
    medium: str
    status: Literal["concept", "in_progress", "finished", "listed", "sold"]
    size: str = ""
    price: float | None = None
    notes: str = ""
    outdoor_ready: bool = False


class ContentItem(BaseModel):
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


# ---------- Agent ----------
class ArtManagerAgent(Agent, llm=llm):
    """
    You are a professional art manager whose only job is to turn Cody into
    a consistently paid artist.

    You fully own codycarlson.art (Vercel + GitHub hipaasynth-svg/codycarlson.art).
    You research successful artist sites, diagnose the current site, propose
    concrete improvements, and implement them only via branch + pull request
    (never push directly to main).

    You actively hunt high-intent buyers in North Dakota on a per-piece basis.
    Match each finished work to real local targets (lodges, restaurants,
    designers, builders, collectors) and produce specific next actions.

    Always persist briefs, buyer lists, state, and printouts to Google Drive.
    Printouts run every 3 days (or immediately if something is pressing).

    Be direct, practical, and protective of Cody's limited energy and time.
    Prefer one high-leverage action over many weak ones.
    """

    # === State ===
    pieces: list[ArtPiece] = Field(default_factory=list)
    content_queue: list[ContentItem] = Field(default_factory=list)
    pipeline: SalesPipeline = Field(default_factory=SalesPipeline)
    monthly_revenue_goal: float = 2000.0
    focus_this_week: str = "finish and list highest-leverage pieces"

    # Site ownership
    github_owner: str = "hipaasynth-svg"
    github_repo: str = "codycarlson.art"
    default_branch: str = "main"
    last_research: list[ResearchInsight] = Field(default_factory=list)
    pending_changes: list[SiteChange] = Field(default_factory=list)

    # Google Drive (live folders)
    drive_root_folder_id: str = "1uzI3VXasnvl-4_KemHN60dgwBP1_q4vr"
    drive_printouts_id: str = "1WUh8YNYO7736eUwhU0EctoM9wZWOHARM"
    drive_briefs_id: str = "1s3nujmMevAOGWvfCk-dwZf5l0SVuS2HB"
    drive_buyers_id: str = "103wQVeWOo-gVdeglZD_w7jwNbGsdnXJZ"
    drive_state_id: str = "1shpW9nOsr6EOHNblz23NUiZWIUucrlV4"

    # === Deterministic helpers ===
    def get_finished_unlisted(self) -> list[ArtPiece]:
        return [p for p in self.pieces if p.status == "finished"]

    def get_in_progress(self) -> list[ArtPiece]:
        return [p for p in self.pieces if p.status == "in_progress"]

    def revenue_gap(self) -> float:
        return max(0.0, self.monthly_revenue_goal - self.pipeline.revenue_this_month)

    def add_piece(self, piece: ArtPiece) -> None:
        self.pieces = [p for p in self.pieces if p.id != piece.id] + [piece]

    def get_piece(self, piece_id: str) -> ArtPiece | None:
        for p in self.pieces:
            if p.id == piece_id:
                return p
        return None

    def update_piece_status(self, piece_id: str, status: str) -> None:
        for p in self.pieces:
            if p.id == piece_id:
                p.status = status  # type: ignore
                break

    def seed_known_pieces(self) -> None:
        """Load the two finished pieces we already have."""
        self.add_piece(
            ArtPiece(
                id="summer-walleye",
                title="Summer Walleye",
                medium="Box elder wood carving",
                status="finished",
                size="27 inch",
                outdoor_ready=True,
                notes="Full outdoor UV and water protective coats (3), wet sanded. Strong ND fishing culture piece.",
            )
        )
        self.add_piece(
            ArtPiece(
                id="buffalo",
                title="Buffalo",
                medium="Acrylic on canvas",
                status="finished",
                size="36x24",
                outdoor_ready=False,
                notes="Inspired by gaming machines / Great American Buffalo. Bold graphic portrait with yellow border.",
            )
        )

    # === Core business methods (LLM-completed) ===
    async def daily_command_board(self) -> str:
        """
        Produce a short, ruthless daily command board for the art business.
        Max 8 lines. Include:
        - One highest-leverage action for today
        - What to deliberately ignore
        - Current revenue gap
        - Next piece that should be finished or listed
        - Any high-priority site improvement that should ship this week
        - One ND buyer action tied to a specific piece
        """
        ...

    async def plan_content_for_piece(self, piece_id: str) -> list[ContentItem]:
        """
        Create a tight content plan (3–5 items) that will help sell the given piece.
        Prefer high-signal formats (process video, finished reveal, story behind the work).
        """
        ...

    async def pricing_recommendation(self, piece_id: str) -> float:
        """
        Recommend a realistic selling price based on medium, complexity, market,
        and the goal of becoming a paid artist. Be honest, not optimistic.
        Return only the number.
        """
        ...

    async def weekly_review(self) -> str:
        """
        Short weekly review: what moved the needle, what stalled,
        adjusted focus, one clear ask for Cody, and any open site PRs.
        """
        ...

    async def create_sales_brief(self, piece_id: str) -> str:
        """
        Write a clean sales brief for a finished piece usable for listings,
        DMs, or outreach. Keep it human and specific to the actual piece.
        """
        ...

    # === Per-piece ND buyer hunting ===
    async def find_buyers_for_piece(self, piece_id: str) -> str:
        """
        For one specific piece, find the highest-intent North Dakota buyers.
        Match the piece's medium, scale, style, story, and price to real local
        targets (homes, new builds, designers, businesses, venues, collectors,
        fishing lodges, restaurants).

        Return a ranked shortlist (3–5) with:
        - Who they are
        - Why this piece fits them
        - One clear next outreach action

        Be specific and local to Minot / North Dakota. No generic advice.
        """
        ...

    async def create_nd_outreach_brief(self, piece_id: str, target: str) -> str:
        """
        Write a short, specific outreach message (email or DM) for one ND target
        about one specific piece. Personal, not spammy. Reference real local
        context when possible. Keep it under 120 words.
        """
        ...

    # === Site research & analysis ===
    async def research_successful_art_sites(self) -> list[ResearchInsight]:
        """
        Research high-converting artist / sculptor / carver / commission sites.
        Focus on: layout, pricing presentation, trust signals, CTAs, photo treatment,
        mobile experience, and what actually drives commission inquiries.
        Return 5–8 concrete insights with sources and recommendations.
        Store them on self.last_research.
        """
        ...

    async def analyze_current_site(self) -> str:
        """
        Diagnose codycarlson.art (especially js/config.js, index.html, css/styles.css)
        against the latest research insights.
        Produce a clear diagnosis: what is working, what is weak, and the top 3–5
        highest-leverage improvements.
        """
        ...

    async def propose_improvements(self) -> list[SiteChange]:
        """
        From research + analysis, produce a prioritized list of concrete site changes.
        Each change must name the exact files that will be touched and the rationale.
        Store them on self.pending_changes.
        """
        ...

    # === Implementation (always via PR — human reviews) ===
    async def implement_change_as_pr(
        self,
        change: SiteChange,
        branch_name: str | None = None,
    ) -> str:
        """
        Describe exactly how to implement one SiteChange as a GitHub PR:
        1. Branch name to create from main
        2. Exact file edits (or new content)
        3. Commit message
        4. PR title and body

        Never claim to have pushed. Always produce instructions or diffs that
        can be applied safely. The human creates the PR.
        """
        ...

    async def ship_top_improvements(self, max_prs: int = 2) -> str:
        """
        Take the highest-priority pending changes and produce ready-to-apply
        PR instructions for each (limit max_prs). Return a clear summary.
        """
        ...
