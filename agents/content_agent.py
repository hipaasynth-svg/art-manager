"""
Content Agent — a separate NOOA agent for social content generation.

Distinct from the Art Manager: this agent's only job is to turn a finished piece
into ready-to-post content for TikTok, Instagram, and Facebook — captions,
short/reel scripts, and visual briefs — on a posting schedule.

Like ``art_manager``, importing this module has no side effects: the nooa Agent
subclass and its LLM client are built lazily the first time ``ContentAgent`` is
accessed (PEP 562 ``__getattr__``). The deterministic scaffolding in
``agents/content.py`` needs neither nooa nor an API key.
"""

from __future__ import annotations

from datetime import date
from functools import lru_cache

from nooa import Agent

from . import content
from .config import load_config
from .models import ArtPiece, SocialPost

_CONFIG = load_config()


@lru_cache(maxsize=1)
def get_llm():
    """Lazily build and cache the LLM client (see ``art_manager.get_llm``)."""
    from nooa.unifiedllm.registry import get_llm_client

    return get_llm_client(_CONFIG.model)


@lru_cache(maxsize=1)
def _build_agent_class() -> type:
    class ContentAgent(Agent, llm=get_llm()):
        """
        You are a social content producer for the artist Cody Carlson.
        Your only job is to turn finished pieces into scroll-stopping,
        on-brand content for TikTok, Instagram, and Facebook that drives
        awareness and sales — without sounding like an ad.

        Voice: authentic, maker-focused, North Dakota. Show process and story,
        not hype. Every post has a clear hook and, when the piece is for sale,
        a soft call to action to the buy link.
        """

        site_url: str = _CONFIG.site_url

        # === Deterministic scaffolding (no LLM) ===
        def schedule_for_piece(
            self, piece: ArtPiece, start: date | None = None, days: int = 14, per_week: int = 3
        ) -> list[SocialPost]:
            """Skeleton posts on a schedule (hashtags + format filled in)."""
            return content.blank_plan_for_piece(piece, start or date.today(), days, per_week)

        def render_plan(self, piece: ArtPiece, posts: list[SocialPost]) -> str:
            return content.render_plan(piece.title, posts)

        def export_plan(
            self, piece: ArtPiece, posts: list[SocialPost], path: str | None = None
        ) -> str:
            """Write a piece's content plan to ``path`` (Markdown)."""
            from pathlib import Path

            target = path or f"content_{piece.id}.md"
            Path(target).write_text(self.render_plan(piece, posts), encoding="utf-8")
            return target

        # === LLM-completed content generation ===
        async def plan_campaign_for_piece(
            self, piece: ArtPiece, days: int = 14, per_week: int = 3
        ) -> list[SocialPost]:
            """
            Produce a full multi-platform content campaign for one piece.

            Start from ``self.schedule_for_piece(piece, days=days, per_week=per_week)``
            for the calendar + formats, then FILL each SocialPost's creative
            fields — hook, caption, script (for reels/shorts), visual_brief, cta.
            Vary angles across posts (process, finished reveal, story behind it,
            detail shots). Match each platform's native style. Keep the piece's
            for-sale status in mind for the CTA. Return the completed list.
            """
            ...

        async def write_short_script(self, piece: ArtPiece, platform: str = "tiktok") -> str:
            """
            Write a shot-by-shot script for a 20–40s vertical short/reel about
            this piece: a hook in the first 2 seconds, 3–5 beats, on-screen text
            suggestions, and a closing CTA. Concrete and shootable on a phone.
            """
            ...

        async def write_caption(self, piece: ArtPiece, platform: str = "instagram") -> SocialPost:
            """
            Write one ready-to-post SocialPost for the given platform: hook,
            caption in that platform's voice, a tight hashtag set (you may keep
            ``content.default_hashtags``), a visual_brief, and a soft cta.
            """
            ...

        async def visual_brief(self, piece: ArtPiece) -> str:
            """
            Describe the visuals to capture for this piece — angles, lighting,
            props, setting, and any process B-roll — so Cody can shoot content
            without guessing. Specific to the actual medium and subject.
            """
            ...

    return ContentAgent


def __getattr__(name: str):
    if name == "ContentAgent":
        return _build_agent_class()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
