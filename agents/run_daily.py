"""
Daily runner for the Art Manager — the studio "floor".

Loads state, syncs inventory from the live site, then produces one packet a
human can act on in minutes:

  1. Site diagnosis + a ruthless command board
  2. A phone-first CALL SHEET across a rotating set of for-sale pieces
     (real ND businesses + numbers from Google Places, on-voice scripts)
  3. A sales brief for the day's top piece
  4. A CONTENT pack (Instagram caption + TikTok script) for the top piece

Every step is isolated so one failure doesn't abort the rest. Output prints to
the log and — via the GitHub Actions workflow — is emailed to Cody.

Knobs (env):
  ART_MANAGER_DAILY_PIECES   how many pieces to hunt buyers for per run (default 4)
"""

from __future__ import annotations

import asyncio
import datetime
import logging
import os
from typing import Awaitable, Callable, TypeVar

from agents import logic
from agents.art_manager import ArtManagerAgent
from agents.models import ArtPiece, BuyerLead

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("art_manager")

T = TypeVar("T")


async def _step(title: str, coro_factory: Callable[[], Awaitable[T]]) -> T | None:
    """Run one workflow step, printing the result and swallowing failures."""
    print(f"\n=== {title} ===")
    try:
        result = await coro_factory()
        print(result)
        return result
    except Exception as exc:  # noqa: BLE001 - runner should be resilient
        log.exception("step %r failed: %s", title, exc)
        print(f"[skipped: {exc}]")
        return None


async def _leads(agent: ArtManagerAgent, piece: ArtPiece) -> list[BuyerLead]:
    """Structured leads for one piece; [] on failure (never aborts the run)."""
    try:
        return await agent.find_buyer_leads_for_piece(piece.id) or []
    except Exception as exc:  # noqa: BLE001
        log.exception("leads for %r failed: %s", piece.title, exc)
        return []


async def main() -> None:
    agent = ArtManagerAgent()
    agent.load()

    today = datetime.date.today().isoformat()
    print(f"\n=== Syncing live gallery: {agent.site_url} ===")
    sync = agent.sync_from_gallery()
    if sync.get("ok"):
        print(
            f"  ok — live={sync['live_paintings']}, added={sync['added']}, "
            f"updated={sync['updated']}, total={sync['total']}, "
            f"for_sale={sync['for_sale']}, sellable={sync['sellable']}"
        )
    else:
        print(f"  could not sync gallery: {sync.get('error')}")

    print("=== Inventory ===")
    for p in agent.pieces:
        flag = "  [FOR SALE]" if p.for_sale else ""
        price = f" ${p.price}" if p.price is not None else ""
        print(f"  • {p.title} ({p.medium}) — {p.status} — {p.size}{price}{flag}")

    snap = agent.last_site_snapshot
    if snap and snap.ok:
        await _step("Site diagnosis (grounded in the live page)", lambda: agent.analyze_current_site(snap))
    elif snap:
        print(f"  site snapshot not ok: {snap.error}")

    await _step("Daily command board", agent.daily_command_board)

    # Weekly pulse on Mondays: a bigger-picture review rides along with the brief.
    if datetime.date.today().weekday() == 0:
        await _step("Weekly review", agent.weekly_review)

    # ---- Phone-first call sheet across a rotating set of pieces ----
    n_sculpt = int(os.environ.get("ART_MANAGER_DAILY_SCULPTURES", "2") or "2")
    n_paint = int(os.environ.get("ART_MANAGER_DAILY_PAINTINGS", "4") or "4")
    doy = datetime.date.today().timetuple().tm_yday
    focus = logic.daily_focus(
        agent.get_for_sale(), sculptures=n_sculpt, paintings=n_paint, day=doy
    ) or agent.pieces[: n_sculpt + n_paint]
    pairs: list[tuple[ArtPiece, list[BuyerLead]]] = []
    if not focus:
        print("\n[no pieces from the live site yet — skipping call sheet]")
    else:
        if not agent.has_buyer_search:
            print("\n[note: ART_MANAGER_SEARCH_API_KEY not set — leads will be "
                  "AI-guessed, not verified Google Places businesses]")
        print(f"\n[hunting buyers for {len(focus)} piece(s) this run]")
        for piece in focus:
            leads = await _leads(agent, piece)
            pairs.append((piece, leads))
        print("\n=== CALL SHEET ===")
        print(agent.build_call_sheet(pairs, date_str=today))

    # ---- Sales brief for the day's top piece ----
    if focus:
        top = focus[0]
        await _step(f"Sales brief: {top.title}", lambda pid=top.id: agent.create_sales_brief(pid))

    # ---- Content pack for the day's top piece ----
    if focus:
        top = focus[0]
        try:
            from agents.content_agent import ContentAgent

            content_agent = ContentAgent()
            print("\n=== CONTENT PACK ===")
            await _step(f"Instagram caption: {top.title}",
                        lambda p=top: content_agent.write_caption(p, "instagram"))
            await _step(f"TikTok short script: {top.title}",
                        lambda p=top: content_agent.write_short_script(p, "tiktok"))
        except Exception as exc:  # noqa: BLE001 - content is a bonus, never fatal
            log.exception("content pack failed: %s", exc)
            print(f"[content pack skipped: {exc}]")

    # ---- Self-improvement: record what to do differently, into the playbook ----
    learnings = await _step("Reflect (self-improvement)", agent.reflect)
    if learnings and str(learnings).strip():
        try:
            from agents import notes

            if notes.append_playbook(str(learnings), today=today):
                print("[playbook updated]")
        except Exception as exc:  # noqa: BLE001 - never fatal
            log.exception("playbook update failed: %s", exc)
            print(f"[playbook update skipped: {exc}]")

    agent.save()
    print(f"\n[state saved to {agent.state_path}]")


if __name__ == "__main__":
    asyncio.run(main())
