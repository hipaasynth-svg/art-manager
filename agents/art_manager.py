"""
Art Manager Agent — NOOA (NVIDIA Object-Oriented Agents)

Owns codycarlson.art, finds high-intent North Dakota buyers per piece,
and drives sales. Uses Claude Opus 4.8 for creative / sales work.

Install:
  pip install -r requirements.txt

Run (example):
  export ANTHROPIC_API_KEY=...
  python -m agents.run_daily

Note: importing this module has no side effects. The nooa Agent subclass is
built lazily the first time ``ArtManagerAgent`` is accessed (PEP 562
``__getattr__``), and the LLM client is constructed at that same point — so the
data models and pure logic can be imported and tested without nooa, an API key,
or network access.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from nooa import Agent

from . import logic, seo, site
from .config import Config, load_config
from .models import (
    AgentState,
    ArtPiece,
    BuyerLead,
    ContentItem,
    PieceSEO,
    ResearchInsight,
    SalesPipeline,
    SiteChange,
    SiteSnapshot,
)
from .state import load_state, save_state

_CONFIG: Config = load_config()


# ---------- LLM ----------
@lru_cache(maxsize=1)
def get_llm():
    """Lazily build and cache the LLM client.

    Deferred so merely importing the package has no side effects and needs no
    ANTHROPIC_API_KEY; the client is constructed the first time the agent
    class is built (see ``_build_agent_class``).
    """
    from nooa.unifiedllm.registry import get_llm_client

    return get_llm_client(_CONFIG.model)


# ---------- Agent ----------
# The nooa metaclass consumes ``llm`` when the class is defined, so we build the
# class lazily inside a cached factory and expose it via module ``__getattr__``
# (PEP 562). Result: ``import agents`` / ``import agents.art_manager`` has no
# side effects — the LLM client is only constructed the first time
# ``ArtManagerAgent`` is actually accessed.
@lru_cache(maxsize=1)
def _build_agent_class() -> type:
    class ArtManagerAgent(Agent, llm=get_llm()):
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
        # nooa's Agent is a plain object (not a pydantic model), so class-level
        # ``Field(default_factory=...)`` is NOT materialised into per-instance
        # values — it would leave a FieldInfo on the class. Mutable state is
        # therefore declared as bare annotations here and initialised per
        # instance in __init__; only immutable scalars keep class-level defaults.
        pieces: list[ArtPiece]
        content_queue: list[ContentItem]
        pipeline: SalesPipeline
        last_research: list[ResearchInsight]
        pending_changes: list[SiteChange]
        last_site_snapshot: SiteSnapshot | None

        monthly_revenue_goal: float = _CONFIG.monthly_revenue_goal
        focus_this_week: str = "finish and list highest-leverage pieces"

        # Site ownership
        github_owner: str = _CONFIG.github_owner
        github_repo: str = _CONFIG.github_repo
        default_branch: str = _CONFIG.default_branch
        site_url: str = _CONFIG.site_url

        # Google Drive (live folders)
        drive_root_folder_id: str = _CONFIG.drive_root_folder_id
        drive_printouts_id: str = _CONFIG.drive_printouts_id
        drive_briefs_id: str = _CONFIG.drive_briefs_id
        drive_buyers_id: str = _CONFIG.drive_buyers_id
        drive_state_id: str = _CONFIG.drive_state_id

        # Local state persistence
        state_path: str = _CONFIG.state_path

        # Buyer search / enrichment key (empty = AI-guessed leads only).
        search_api_key: str = _CONFIG.search_api_key

        def __init__(self, **kwargs) -> None:
            # Pass through llm / storage / context etc. to nooa's Agent, then
            # give each mutable field a fresh per-instance default.
            super().__init__(**kwargs)
            self.pieces = []
            self.content_queue = []
            self.pipeline = SalesPipeline()
            self.last_research = []
            self.pending_changes = []
            self.last_site_snapshot = None

        # === Deterministic helpers (delegate to pure logic) ===
        def get_finished_unlisted(self) -> list[ArtPiece]:
            return logic.finished_unlisted(self.pieces)

        def get_in_progress(self) -> list[ArtPiece]:
            return logic.in_progress(self.pieces)

        def get_for_sale(self) -> list[ArtPiece]:
            return logic.for_sale_pieces(self.pieces)

        def get_sellable(self) -> list[ArtPiece]:
            """For-sale pieces with a price and a checkout link (buyer can pay now)."""
            return logic.sellable_pieces(self.pieces)

        def fetch_gallery(self) -> dict[str, Any]:
            """Fetch the live gallery JSON for agent use.

            This uses the site's structured ``/api/gallery`` endpoint rather than
            scraping HTML, so the model receives the real catalog data.
            """
            return site.fetch_gallery(self.site_url)

        def fetch_site(self) -> SiteSnapshot:
            """Read the live gallery API and remember a usable summary."""
            snap = site.fetch_site(self.site_url)
            self.last_site_snapshot = snap
            return snap

        def sync_from_gallery(self) -> dict[str, Any]:
            """Pull live ``/api/gallery`` paintings into ``self.pieces``.

            Local-only inventory (e.g. carvings not in the paintings API) is
            preserved. Catalog fields from the site win; local notes and
            outdoor_ready are kept when already set.

            Available pieces with a price get a shareable ``?buy=<id>`` checkout
            deep link when no Stripe Payment Link is set on the site.

            Returns a small summary the daily runner / LLM can log.
            """
            gallery = self.fetch_gallery()
            if isinstance(gallery, dict) and gallery.get("ok") is False:
                return {
                    "ok": False,
                    "error": gallery.get("error", "gallery fetch failed"),
                    "added": 0,
                    "updated": 0,
                    "total": len(self.pieces),
                }

            live = logic.pieces_from_gallery(gallery, site_url=self.site_url)
            before = {p.id for p in self.pieces}
            self.pieces = logic.merge_gallery_into_pieces(self.pieces, live)
            after_ids = {p.id for p in self.pieces}
            live_ids = {p.id for p in live}

            # Also keep a site snapshot so analyze_current_site stays grounded.
            snap = site.fetch_site(self.site_url)
            self.last_site_snapshot = snap

            return {
                "ok": True,
                "live_paintings": len(live),
                "added": len(live_ids - before),
                "updated": len(live_ids & before),
                "total": len(after_ids),
                "for_sale": len(self.get_for_sale()),
                "sellable": len(self.get_sellable()),
            }

        def revenue_gap(self) -> float:
            return logic.revenue_gap(
                self.monthly_revenue_goal, self.pipeline.revenue_this_month
            )

        def add_piece(self, piece: ArtPiece) -> None:
            self.pieces = logic.upsert_piece(self.pieces, piece)

        def get_piece(self, piece_id: str) -> ArtPiece | None:
            return logic.get_piece(self.pieces, piece_id)

        def update_piece_status(self, piece_id: str, status: str) -> bool:
            """Update a piece's status. Raises ValueError on an unknown status."""
            return logic.set_status(self.pieces, piece_id, status)

        # === SEO / metadata (deterministic baseline) ===
        def build_piece_seo(self, piece_id: str) -> PieceSEO | None:
            """Deterministic meta tags + schema.org JSON-LD for one piece.

            Always available (no LLM). ``write_piece_metadata`` can enrich the
            human-facing copy on top of this.
            """
            piece = self.get_piece(piece_id)
            if piece is None:
                return None
            return seo.piece_metadata(piece, self.site_url)

        def export_seo_file(self, path: str | None = None) -> str:
            """Write a Markdown metadata/SEO document for every piece to ``path``.

            Returns the path written. This is the "hand me a file" output: each
            piece gets a ready-to-paste ``<head>`` snippet (meta tags + JSON-LD).
            """
            from pathlib import Path

            target = path or "piece_seo.md"
            Path(target).write_text(
                seo.metadata_document(self.pieces, self.site_url), encoding="utf-8"
            )
            return target

        # === State persistence ===
        def to_state(self) -> AgentState:
            return AgentState(
                pieces=self.pieces,
                content_queue=self.content_queue,
                pipeline=self.pipeline,
                monthly_revenue_goal=self.monthly_revenue_goal,
                focus_this_week=self.focus_this_week,
                last_research=self.last_research,
                pending_changes=self.pending_changes,
                last_site_snapshot=self.last_site_snapshot,
            )

        def apply_state(self, state: AgentState) -> None:
            self.pieces = state.pieces
            self.content_queue = state.content_queue
            self.pipeline = state.pipeline
            self.monthly_revenue_goal = state.monthly_revenue_goal
            self.focus_this_week = state.focus_this_week
            self.last_research = state.last_research
            self.pending_changes = state.pending_changes
            self.last_site_snapshot = state.last_site_snapshot

        def save(self, path: str | None = None) -> None:
            save_state(self.to_state(), path or self.state_path)

        def load(self, path: str | None = None) -> None:
            self.apply_state(load_state(path or self.state_path))

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
            Include the buy link when the piece is sellable.
            """
            ...

        # === SEO / AI-search (LLM-enriched) ===
        async def write_piece_metadata(self, piece_id: str) -> PieceSEO:
            """
            Write compelling SEO metadata for one piece, grounded in the real
            ArtPiece. Start from ``self.build_piece_seo(piece_id)`` as the
            baseline (correct title tag, canonical URL, and schema.org JSON-LD)
            and improve the human-facing copy:
            - meta_description: <=155 chars, specific, buyer-intent, mentions the
              medium and North Dakota / Minot when natural. No keyword stuffing.
            - keywords: the realistic terms a buyer would actually search.
            - og_title / og_description: share-friendly.
            - alt_text: describes the image for accessibility + image search.
            Keep piece_id, canonical_url, and json_ld from the baseline. Return
            the completed PieceSEO.
            """
            ...

        async def research_ai_search_visibility(self) -> list[ResearchInsight]:
            """
            Research how this art business can show up in AI answer engines
            (ChatGPT, Claude, Perplexity, Google AI Overviews) and modern search.
            Focus on concrete, doable moves: schema.org/JSON-LD structured data,
            a clear entity (artist name, location, mediums), consistent NAP,
            image alt text, being cited on pages AI crawls, and llms.txt.
            Return 5–8 concrete insights with sources and recommendations, and
            store them on self.last_research.
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

        async def find_buyer_leads_for_piece(self, piece_id: str) -> list[BuyerLead]:
            """
            Find high-intent North Dakota buyers for one piece as STRUCTURED
            leads, each carrying every contact detail you can find — this is the
            report that must not drop contact info (issue #7).

            For each of 3–6 leads populate BuyerLead: name, category, location,
            why_fit, and as much of website / email / phone / address /
            contact_name as is findable, plus source, next_action, confidence.

            Use a real data source when one is configured: ``self.has_buyer_search``
            tells you whether a search/enrichment key is set (Google Places,
            Brave, SerpAPI, or Apollo). If MCP tools are available, use them to
            enrich company contact info. When no source is configured, still
            return named, plausible local targets but set confidence honestly and
            put the lookup step in next_action rather than inventing emails/phones.

            Return the list. Render it for humans with
            ``self.buyer_contacts_report(piece_id, leads)``.
            """
            ...

        async def create_nd_outreach_brief(self, piece_id: str, target: str) -> str:
            """
            Write a short, specific outreach message (email or DM) for one ND target
            about one specific piece. Personal, not spammy. Reference real local
            context when possible. Keep it under 120 words. Include the buy link
            when available.
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

        async def analyze_current_site(self, snapshot: SiteSnapshot) -> str:
            """
            Diagnose the REAL public website using the provided `snapshot` — the
            actual page title, text, images, prices, contact info, and links the
            agent just read from the page a buyer loads. Do not invent content;
            work only from what the snapshot shows (if snapshot.ok is False, say
            the site could not be read and stop).

            IMPORTANT: the site is a client-rendered SPA, so its catalog is drawn
            in by JavaScript and will NOT appear in the raw page text. The real
            inventory the page renders is in `snapshot.gallery_data` (and merged
            into `snapshot.prices` / `snapshot.images`). Judge products, prices,
            and availability from `gallery_data` — do NOT report them as
            "missing" just because they are absent from the visible page text.

            Judge it as a tool for SELLING art:
            - Is it clear what is for sale and at what price? Can a buyer actually
              buy or inquire (checkout link, contact, commission CTA)?
            - Trust signals, story, photo quality, mobile, load.
            Compare against self.last_research when present. Produce a clear
            diagnosis: what works, what's weak, and the top 3–5 highest-leverage
            improvements — each tied to something concrete in the snapshot.
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

    return ArtManagerAgent


def __getattr__(name: str):
    # PEP 562: resolve ``ArtManagerAgent`` on first access, building the nooa
    # class (and LLM client) only then.
    if name == "ArtManagerAgent":
        return _build_agent_class()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
