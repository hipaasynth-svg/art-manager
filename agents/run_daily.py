"""
Quick runner for the Art Manager.

Usage:
  export ANTHROPIC_API_KEY=sk-...
  python -m agents.run_daily

Loads any persisted state, seeds the known pieces if the state is empty, runs
the daily workflow (each step isolated so one failure doesn't abort the rest),
and saves state back to disk.
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

    # Restore prior state; seed the known pieces only if we're starting fresh.
    agent.load()
    if not agent.pieces:
        agent.seed_known_pieces()

    print("=== Seeded pieces ===")
    for p in agent.pieces:
        print(f"  • {p.title} ({p.medium}) — {p.status} — {p.size}")

    await _step("Daily command board", agent.daily_command_board)
    await _step(
        "Buyers for Summer Walleye",
        lambda: agent.find_buyers_for_piece("summer-walleye"),
    )
    await _step("Buyers for Buffalo", lambda: agent.find_buyers_for_piece("buffalo"))
    await _step(
        "Sales brief: Summer Walleye",
        lambda: agent.create_sales_brief("summer-walleye"),
    )

    agent.save()
    print(f"\n[state saved to {agent.state_path}]")


if __name__ == "__main__":
    asyncio.run(main())
