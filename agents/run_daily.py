"""
Quick runner for the Art Manager.

Usage:
  export ANTHROPIC_API_KEY=sk-...
  python -m agents.run_daily

Loads any persisted state, syncs inventory from the live site (the source of
truth — no seeded pieces), runs the daily workflow (each step isolated so one
failure doesn't abort the rest), and saves state back to disk.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Awaitable, Callable, TypeVar

from agents.art_manager import ArtManagerAgent

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("art_manager")

T = TypeVar("T")


async def _step(title: str, coro_factory: Callable[[], Awaitable[T]]) -> T | None:
    """Run one workflow step, logging and swallowing failures.

    Takes a factory so the coroutine is only created when we run it, and a
    failure in one step doesn't prevent the others from running.
    """
    print(f"\n=== {title} ===")
    try:
        result = await coro_factory()
        print(result)
        return result
    except Exception as exc:  # noqa: BLE001 - runner should be resilient
        log.exception("step %r failed: %s", title, exc)
        print(f"[skipped: {exc}]")
        return None


async def main() -> None:
    agent = ArtManagerAgent()

    # Restore prior state. Inventory comes entirely from the live site — no
    # hardcoded/seeded pieces.
    agent.load()

    # Live gallery is source of truth for paintings inventory.
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
        await _step(
            "Site diagnosis (grounded in the live page)",
            lambda: agent.analyze_current_site(snap),
        )
    elif snap:
        print(f"  site snapshot not ok: {snap.error}")

    await _step("Daily command board", agent.daily_command_board)

    # Focus on live for-sale pieces; otherwise the first pieces the site has.
    focus = agent.get_for_sale()[:2] or agent.pieces[:2]
    if not focus:
        print("\n[no pieces from the live site yet — skipping buyer hunt and brief]")
    else:
        for piece in focus:
            await _step(
                f"Buyers for {piece.title}",
                lambda pid=piece.id: agent.find_buyers_for_piece(pid),
            )

        brief_piece = focus[0]
        await _step(
            f"Sales brief: {brief_piece.title}",
            lambda pid=brief_piece.id: agent.create_sales_brief(pid),
        )

    agent.save()
    print(f"\n[state saved to {agent.state_path}]")


if __name__ == "__main__":
    asyncio.run(main())
