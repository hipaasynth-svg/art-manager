"""
Pure, deterministic business logic for the Art Manager.

These functions take plain data and return plain data — no LLM calls, no
network, no nooa dependency — so they are cheap to reason about and easy to
unit-test. The agent delegates its non-judgment work here.
"""

from __future__ import annotations

from typing import Any

from .models import PIECE_STATUSES, ArtPiece, CheckoutSummary, PieceStatus

DEFAULT_SITE_URL = "https://www.codycarlson.art"


def finished_unlisted(pieces: list[ArtPiece]) -> list[ArtPiece]:
    """Pieces that are finished but not yet listed or sold.

    Because status is a single lifecycle enum, a piece that has been listed or
    sold carries the ``listed`` / ``sold`` status rather than ``finished``, so
    filtering on ``finished`` already excludes them.
    """
    return [p for p in pieces if p.status == "finished"]


def in_progress(pieces: list[ArtPiece]) -> list[ArtPiece]:
    return [p for p in pieces if p.status == "in_progress"]


def for_sale_pieces(pieces: list[ArtPiece]) -> list[ArtPiece]:
    """Pieces the artist is actively offering for sale (for_sale=True)."""
    return [p for p in pieces if p.for_sale]


def sellable_pieces(pieces: list[ArtPiece]) -> list[ArtPiece]:
    """For-sale pieces that a buyer could actually pay for right now:
    marked for sale, with a price and a checkout link.
    """
    return [p for p in pieces if p.for_sale and p.price is not None and p.buy_url]


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


def _parse_price(raw: Any) -> float | None:
    if raw is None or raw == "":
        return None
    try:
        return float(str(raw).replace(",", "").replace("$", "").strip())
    except (TypeError, ValueError):
        return None


def _map_gallery_status(raw: Any) -> tuple[PieceStatus, bool]:
    """Map site status string → (ArtPiece.status, for_sale)."""
    s = str(raw or "available").strip().lower()
    if s == "sold":
        return "sold", False
    if s == "reserved":
        # Still listed inventory, but not currently buyable.
        return "listed", False
    # available / unknown → listed + for sale
    return "listed", True


def checkout_deep_link(piece_id: str, site_url: str = DEFAULT_SITE_URL) -> str:
    """Shareable link that opens on-site Stripe Checkout for ``piece_id``."""
    base = (site_url or DEFAULT_SITE_URL).rstrip("/")
    # Prefer www canonical so redirects don't drop the query in edge cases.
    if base == "https://codycarlson.art":
        base = "https://www.codycarlson.art"
    return f"{base}/?buy={piece_id}"


def pieces_from_gallery(
    gallery: dict[str, Any],
    *,
    site_url: str = DEFAULT_SITE_URL,
) -> list[ArtPiece]:
    """Convert the live ``/api/gallery`` JSON into ArtPiece records.

    Only the ``paintings`` array is treated as inventory. Portfolio galleries
    (featured / studio / stones) are display-only and are not turned into pieces.
    Malformed entries are skipped rather than raising.

    If a piece has a price (or is for sale) but no Stripe Payment Link, ``buy_url``
    is filled with the site deep link ``?buy=<id>`` so outreach can share a
    working checkout URL.
    """
    if not isinstance(gallery, dict) or gallery.get("ok") is False:
        return []

    raw_paintings = gallery.get("paintings", [])
    if not isinstance(raw_paintings, list):
        return []

    out: list[ArtPiece] = []
    for item in raw_paintings:
        if not isinstance(item, dict):
            continue
        pid = str(item.get("id") or "").strip()
        title = str(item.get("title") or "").strip()
        if not pid or not title:
            continue

        status, for_sale = _map_gallery_status(item.get("status"))
        buy = item.get("buyUrl") or item.get("buy_url") or None
        if isinstance(buy, str):
            buy = buy.strip() or None
        else:
            buy = None

        price = _parse_price(item.get("price"))
        # On-site Stripe Checkout works from price alone; give the agent a
        # shareable deep link when no explicit Payment Link is set.
        if for_sale and price is not None and not buy:
            buy = checkout_deep_link(pid, site_url)

        image = item.get("url") or item.get("image") or item.get("image_url")
        image_url = str(image).strip() if image else None

        medium = str(item.get("medium") or "Painting").strip() or "Painting"
        size = str(item.get("size") or "").strip()

        out.append(
            ArtPiece(
                id=pid,
                title=title,
                medium=medium,
                status=status,
                size=size,
                price=price,
                image_url=image_url,
                for_sale=for_sale,
                buy_url=buy,
                notes="Synced from live gallery API",
            )
        )
    return out


def checkout_summary(
    gallery: dict[str, Any],
    *,
    site_url: str = DEFAULT_SITE_URL,
) -> CheckoutSummary:
    """Deterministic buyability read of the live ``/api/gallery`` catalog.

    On-site Stripe Checkout prices an ``available`` piece from its ``price``
    alone, so a piece is buyable now when it is for sale with a resolved
    checkout link — which ``pieces_from_gallery`` fills from the price when no
    explicit Payment Link is set. Empty ``buyUrl``/``stripePriceId`` therefore
    does NOT mean "no checkout"; this counts what a visitor can actually pay for.
    """
    pieces = pieces_from_gallery(gallery, site_url=site_url)
    sellable = sellable_pieces(pieces)
    return CheckoutSummary(
        on_site_checkout=True,
        buyable_count=len(sellable),
        buyable_ids=[p.id for p in sellable],
        for_sale_count=len(for_sale_pieces(pieces)),
        note=(
            "On-site Stripe Checkout prices an 'available' piece from its price "
            "via /api/checkout (Buy Now button + ?buy=<id> deep link), so empty "
            "buyUrl/stripePriceId does NOT mean a piece can't be bought."
        ),
    )


def merge_gallery_into_pieces(
    existing: list[ArtPiece],
    live: list[ArtPiece],
) -> list[ArtPiece]:
    """Upsert live gallery pieces into local inventory.

    - Live catalog fields win (title, price, status, for_sale, buy_url, image).
    - Local-only pieces (e.g. carvings not in the paintings API) are kept.
    - Local notes and outdoor_ready are preserved when already set.
    """
    by_id: dict[str, ArtPiece] = {p.id: p for p in existing}

    for lp in live:
        if lp.id in by_id:
            old = by_id[lp.id]
            by_id[lp.id] = lp.model_copy(
                update={
                    # Keep richer local annotations when present.
                    "notes": old.notes if old.notes and old.notes != "Synced from live gallery API" else lp.notes,
                    "outdoor_ready": old.outdoor_ready or lp.outdoor_ready,
                    # Prefer a more specific local medium over the generic default.
                    "medium": (
                        old.medium
                        if old.medium and old.medium != "Painting" and lp.medium == "Painting"
                        else lp.medium
                    ),
                }
            )
        else:
            by_id[lp.id] = lp

    return list(by_id.values())
