"""
Deterministic rendering of buyer leads into a contact-rich report.

Issue #7: buyer reports were prose that often dropped the actual contact
details. These helpers take structured ``BuyerLead`` records and render a report
that always surfaces every contact field we have — email, phone, website,
address — and flags leads that still need contact info found.

Pure and dependency-free, so it is fully unit-testable without an LLM.
"""

from __future__ import annotations

from .models import BuyerLead


def _contact_lines(lead: BuyerLead) -> list[str]:
    rows = [
        ("Contact", lead.contact_name),
        ("Email", lead.email),
        ("Phone", lead.phone),
        ("Website", lead.website),
        ("Address", lead.address),
    ]
    return [f"  - {label}: {value}" for label, value in rows if value]


def render_lead(lead: BuyerLead) -> str:
    """One lead as a compact block, contact details always shown."""
    head = lead.name
    if lead.category:
        head += f" — {lead.category}"
    if lead.location:
        head += f" ({lead.location})"
    lines = [f"### {head}  [{lead.confidence} confidence]"]
    if lead.why_fit:
        lines.append(f"  Why it fits: {lead.why_fit}")
    contact = _contact_lines(lead)
    if contact:
        lines.append("  Contact info:")
        lines += [f"  {c}" for c in contact]
    else:
        lines.append("  Contact info: ⚠️ none found yet — needs lookup")
    if lead.next_action:
        lines.append(f"  Next action: {lead.next_action}")
    if lead.source:
        lines.append(f"  Source: {lead.source}")
    return "\n".join(lines)


def contacts_report(piece_title: str, leads: list[BuyerLead]) -> str:
    """A full buyer report for a piece, with contacts front and center."""
    if not leads:
        return f"# Buyers for {piece_title}\n\nNo leads yet."
    with_contact = sum(1 for lead in leads if lead.has_contact())
    out = [
        f"# Buyers for {piece_title}",
        "",
        f"{len(leads)} lead(s) — {with_contact} with contact info, "
        f"{len(leads) - with_contact} still need lookup.",
        "",
    ]
    for lead in leads:
        out.append(render_lead(lead))
        out.append("")
    return "\n".join(out).rstrip() + "\n"


def leads_missing_contact(leads: list[BuyerLead]) -> list[BuyerLead]:
    """Leads with no reachable contact detail — the follow-up work list."""
    return [lead for lead in leads if not lead.has_contact()]
