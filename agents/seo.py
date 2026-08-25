"""
Deterministic SEO / AI-search metadata for art pieces.

Given an ``ArtPiece`` this builds valid meta tags and schema.org JSON-LD without
any LLM or network — so it is cheap, testable, and always available. The agent's
LLM methods can then enrich the human-facing copy (``meta_description``,
``keywords``, ``og_*``, ``alt_text``) on top of this baseline.

Structured data (JSON-LD) is what makes a piece legible to both classic search
engines and AI answer engines: it states, in machine-readable form, that this is
an artwork by a named creator, its medium, image, price, and availability.
"""

from __future__ import annotations

import json
from typing import Any

from .models import ArtPiece, PieceSEO

ARTIST_NAME = "Cody Carlson"
_STOPWORDS = {"the", "a", "an", "and", "of", "on", "in", "by", "with", "for"}


def _base(site_url: str) -> str:
    return (site_url or "https://codycarlson.art").rstrip("/")


def piece_url(piece: ArtPiece, site_url: str) -> str:
    """Canonical URL for a piece.

    Prefers an explicit ``buy_url`` (the on-site checkout deep link); otherwise
    the site root, since the catalog is rendered there.
    """
    if piece.buy_url:
        return piece.buy_url
    return f"{_base(site_url)}/?piece={piece.id}"


def _keywords(piece: ArtPiece) -> list[str]:
    words: list[str] = []
    for source in (piece.title, piece.medium):
        for token in source.replace("/", " ").split():
            w = token.strip().lower()
            if len(w) > 2 and w not in _STOPWORDS and w not in words:
                words.append(w)
    # Local-intent terms Cody actually competes for.
    for kw in ("north dakota art", "minot nd artist", ARTIST_NAME.lower()):
        if kw not in words:
            words.append(kw)
    return words


def _fallback_description(piece: ArtPiece) -> str:
    bits = [piece.title]
    if piece.medium:
        bits.append(f"— {piece.medium}")
    if piece.size:
        bits.append(f"({piece.size})")
    bits.append(f"by {ARTIST_NAME}, North Dakota.")
    if piece.for_sale and piece.price is not None:
        bits.append(f"Available for ${piece.price:g}.")
    text = " ".join(b for b in bits if b)
    return text[:157].rstrip() + ("…" if len(text) > 157 else "")


def build_json_ld(piece: ArtPiece, site_url: str) -> dict[str, Any]:
    """schema.org ``VisualArtwork`` (+ ``Offer`` when sellable) for a piece."""
    data: dict[str, Any] = {
        "@context": "https://schema.org",
        "@type": "VisualArtwork",
        "name": piece.title,
        "url": piece_url(piece, site_url),
        "creator": {"@type": "Person", "name": ARTIST_NAME},
    }
    if piece.medium:
        data["artMedium"] = piece.medium
    if piece.size:
        data["size"] = piece.size
    if piece.image_url:
        data["image"] = piece.image_url
    if piece.price is not None:
        availability = (
            "https://schema.org/InStock"
            if piece.for_sale
            else "https://schema.org/SoldOut"
            if piece.status == "sold"
            else "https://schema.org/PreOrder"
        )
        offer: dict[str, Any] = {
            "@type": "Offer",
            "price": f"{piece.price:g}",
            "priceCurrency": "USD",
            "availability": availability,
        }
        if piece.buy_url:
            offer["url"] = piece.buy_url
        data["offers"] = offer
    return data


def piece_metadata(piece: ArtPiece, site_url: str = "https://codycarlson.art") -> PieceSEO:
    """Full deterministic SEO baseline for one piece."""
    title_tag = f"{piece.title} — {piece.medium} by {ARTIST_NAME}" if piece.medium else f"{piece.title} by {ARTIST_NAME}"
    description = _fallback_description(piece)
    alt = ", ".join(b for b in (piece.title, piece.medium, piece.size) if b)
    return PieceSEO(
        piece_id=piece.id,
        title_tag=title_tag,
        meta_description=description,
        keywords=_keywords(piece),
        canonical_url=piece_url(piece, site_url),
        og_title=piece.title,
        og_description=description,
        og_image=piece.image_url or "",
        alt_text=alt,
        json_ld=build_json_ld(piece, site_url),
    )


def head_snippet(seo: PieceSEO) -> str:
    """A ready-to-paste ``<head>`` fragment (meta tags + JSON-LD) for a piece."""
    lines = [
        f"<title>{seo.title_tag}</title>",
        f'<meta name="description" content="{seo.meta_description}">',
    ]
    if seo.keywords:
        lines.append(f'<meta name="keywords" content="{", ".join(seo.keywords)}">')
    if seo.canonical_url:
        lines.append(f'<link rel="canonical" href="{seo.canonical_url}">')
    lines += [
        f'<meta property="og:title" content="{seo.og_title}">',
        f'<meta property="og:description" content="{seo.og_description}">',
        '<meta property="og:type" content="article">',
    ]
    if seo.og_image:
        lines.append(f'<meta property="og:image" content="{seo.og_image}">')
    lines.append(
        '<script type="application/ld+json">\n'
        + json.dumps(seo.json_ld, indent=2)
        + "\n</script>"
    )
    return "\n".join(lines)


def metadata_document(
    pieces: list[ArtPiece],
    site_url: str = "https://codycarlson.art",
) -> str:
    """A single Markdown file of per-piece metadata Cody can hand to the site."""
    out = [
        "# Piece metadata & SEO",
        "",
        f"Generated for {ARTIST_NAME} — {len(pieces)} piece(s).",
        "Paste each piece's `<head>` snippet into that piece's page.",
        "",
    ]
    for piece in pieces:
        seo = piece_metadata(piece, site_url)
        out += [
            f"## {piece.title} (`{piece.id}`)",
            "",
            f"- **Title tag:** {seo.title_tag}",
            f"- **Meta description:** {seo.meta_description}",
            f"- **Keywords:** {', '.join(seo.keywords)}",
            f"- **Alt text:** {seo.alt_text}",
            "",
            "```html",
            head_snippet(seo),
            "```",
            "",
        ]
    return "\n".join(out)
