"""
Deterministic phone-first call sheet.

Google Places gives us real business names, phone numbers, and websites — but no
emails. Local art sales happen by phone and drop-in anyway, so the daily
deliverable for a caller (Cody or a hired helper) is a call sheet: who to call,
the number, why the piece fits them, and a short read-aloud script.

Pure and dependency-free (only pydantic models), so it is fully unit-testable
without the agent runtime. The LLM enriches ``BuyerLead.why_fit`` upstream; this
module turns those leads into something a human can dial down.
"""

from __future__ import annotations

from .models import ArtPiece, BuyerLead


def format_price(price: float | None) -> str:
    """A clean dollar string: 550.0 -> $550, 204.8 -> $204.80, None -> ''."""
    if price is None:
        return ""
    return f"${int(price)}" if float(price).is_integer() else f"${price:.2f}"


def call_script(piece: ArtPiece, lead: BuyerLead) -> list[str]:
    """A short, on-voice read-aloud phone script for one lead + one piece."""
    price = format_price(piece.price)
    who = lead.contact_name.strip() if lead.contact_name.strip() else "the owner or manager"
    price_bit = f" ({price})" if price else ""
    fit = lead.why_fit.strip() or "It's a one-of-one, signed, and made here in Minot."
    lines = [
        f'Ask for {who}. "Hi — I\'m calling on behalf of Cody Carlson, a Minot artist."',
        f'"Cody has an original {piece.medium.lower()} piece, “{piece.title}”{price_bit}, '
        f'that made me think of {lead.name}."',
        f'"{fit} Could I send a photo, or drop one by this week?"',
        "If YES: get the best email or set a day/time to bring it in."
        + (f" Preview/buy: {piece.buy_url}" if piece.buy_url else ""),
        "If NOT NOW: thank them, ask to check back later, leave codycarlson.art.",
    ]
    return lines


def render_piece_calls(piece: ArtPiece, leads: list[BuyerLead]) -> str:
    """One piece's call block: phone leads first (with scripts), then the rest."""
    price = format_price(piece.price)
    header = f'## {piece.title}{f" — {price}" if price else ""}'
    if piece.buy_url:
        header += f"\nPreview / buy: {piece.buy_url}"

    phone_leads = [l for l in leads if l.phone.strip()]
    no_phone = [l for l in leads if not l.phone.strip()]

    out = [header, ""]
    if not phone_leads and not no_phone:
        out.append("_No leads yet — run buyer search for this piece._")
        return "\n".join(out).rstrip() + "\n"

    if phone_leads:
        out.append("### Call these (in order)")
        for i, lead in enumerate(phone_leads, 1):
            loc = f" — {lead.location}" if lead.location else ""
            out.append(f"**{i}. {lead.name}{loc} · ☎ {lead.phone}**")
            if lead.website:
                out.append(f"   {lead.website}")
            out.append("   Script:")
            out += [f"   - {line}" for line in call_script(piece, lead)]
            if lead.next_action.strip():
                out.append(f"   Then: {lead.next_action.strip()}")
            out.append("")

    if no_phone:
        out.append("### No phone — walk in or email via their site")
        for lead in no_phone:
            loc = f" ({lead.location})" if lead.location else ""
            site = f" — {lead.website}" if lead.website else ""
            out.append(f"- {lead.name}{loc}{site}: {lead.why_fit.strip()}")
        out.append("")

    return "\n".join(out).rstrip() + "\n"


def render_call_sheet(items: list[tuple[ArtPiece, list[BuyerLead]]], *, date_str: str = "") -> str:
    """The full daily call sheet across several (piece, leads) pairs."""
    total_calls = sum(1 for _, leads in items for l in leads if l.phone.strip())
    title = "# Daily Call Sheet"
    if date_str:
        title += f" — {date_str}"
    out = [
        title,
        "",
        f"{total_calls} call(s) queued across {len(items)} piece(s). "
        "Work top to bottom. Log each: interested / not now / no. "
        "Soft first touch — one personal call beats ten emails.",
        "",
    ]
    if not items:
        out.append("_No pieces to work today._")
        return "\n".join(out) + "\n"
    for piece, leads in items:
        out.append(render_piece_calls(piece, leads))
        out.append("")
    return "\n".join(out).rstrip() + "\n"
