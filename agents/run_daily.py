"""
Quick runner for the Art Manager.

Usage:
  export ANTHROPIC_API_KEY=sk-...
  python -m agents.run_daily
"""

from __future__ import annotations

import asyncio
from agents.art_manager import ArtManagerAgent


async def main() -> None:
    agent = ArtManagerAgent()
    agent.seed_known_pieces()

    print("=== Seeded pieces ===")
    for p in agent.pieces:
        print(f"  • {p.title} ({p.medium}) — {p.status} — {p.size}")

    print("\n=== Daily command board ===")
    board = await agent.daily_command_board()
    print(board)

    print("\n=== Buyers for Summer Walleye ===")
    walleye_buyers = await agent.find_buyers_for_piece("summer-walleye")
    print(walleye_buyers)

    print("\n=== Buyers for Buffalo ===")
    buffalo_buyers = await agent.find_buyers_for_piece("buffalo")
    print(buffalo_buyers)

    print("\n=== Sales brief: Summer Walleye ===")
    brief = await agent.create_sales_brief("summer-walleye")
    print(brief)


if __name__ == "__main__":
    asyncio.run(main())
