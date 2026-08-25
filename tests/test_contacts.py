"""Tests for the deterministic buyer-contacts report (no LLM required)."""

from __future__ import annotations

from agents import contacts
from agents.models import BuyerLead


def _lead_with_contact() -> BuyerLead:
    return BuyerLead(
        name="Sportsman's Lodge",
        category="fishing lodge",
        location="Devils Lake, ND",
        why_fit="Walleye carving suits a ND fishing lodge lobby.",
        website="https://sportsmanslodge.example",
        phone="701-555-0100",
        email="stay@sportsmanslodge.example",
        source="Google Places",
        next_action="Call and offer a lobby viewing.",
        confidence="high",
    )


def _lead_without_contact() -> BuyerLead:
    return BuyerLead(name="Unknown Designer", category="interior designer", location="Minot, ND")


def test_has_contact_flag():
    assert _lead_with_contact().has_contact() is True
    assert _lead_without_contact().has_contact() is False


def test_report_surfaces_contact_details():
    report = contacts.contacts_report("Summer Walleye", [_lead_with_contact()])
    assert "# Buyers for Summer Walleye" in report
    assert "stay@sportsmanslodge.example" in report
    assert "701-555-0100" in report
    assert "https://sportsmanslodge.example" in report
    assert "1 with contact info" in report


def test_report_flags_missing_contact():
    report = contacts.contacts_report("Buffalo", [_lead_without_contact()])
    assert "needs lookup" in report
    assert "0 with contact info" in report


def test_leads_missing_contact_filter():
    leads = [_lead_with_contact(), _lead_without_contact()]
    missing = contacts.leads_missing_contact(leads)
    assert [lead.name for lead in missing] == ["Unknown Designer"]


def test_empty_report():
    assert "No leads yet." in contacts.contacts_report("X", [])
