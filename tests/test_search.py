"""Tests for the buyer-search helper (pure parts; no network)."""

from __future__ import annotations

from agents import search
from agents.search import PlaceLead, build_search_text, parse_places


def test_build_search_text():
    assert build_search_text("fishing lodge", "Minot, ND") == "fishing lodge in Minot, ND"
    # Blank location falls back to North Dakota.
    assert build_search_text("interior designer", "") == "interior designer in North Dakota"
    # Blank category → just the location, no dangling "in".
    assert build_search_text("", "Bismarck") == "Bismarck"


def test_parse_places_full_and_partial():
    payload = {
        "places": [
            {
                "displayName": {"text": "North Star Lodge"},
                "formattedAddress": "1 Lake Rd, Minot, ND",
                "nationalPhoneNumber": "(701) 555-0100",
                "websiteUri": "https://northstarlodge.example",
            },
            # A place missing phone/website still yields a lead (name+address).
            {
                "displayName": {"text": "Prairie Design Co"},
                "formattedAddress": "22 Main St, Minot, ND",
            },
            # No name → skipped entirely.
            {"formattedAddress": "nowhere"},
        ]
    }
    leads = parse_places(payload)
    assert [lead.name for lead in leads] == ["North Star Lodge", "Prairie Design Co"]
    assert leads[0].phone == "(701) 555-0100"
    assert leads[0].website == "https://northstarlodge.example"
    assert leads[1].phone == "" and leads[1].website == ""
    assert leads[0].source == "Google Places"


def test_parse_places_handles_junk():
    assert parse_places({}) == []
    assert parse_places({"places": None}) == []
    assert parse_places("not a dict") == []  # type: ignore[arg-type]


def test_search_configured_and_no_key_returns_empty(monkeypatch):
    monkeypatch.delenv("ART_MANAGER_SEARCH_API_KEY", raising=False)
    assert search.search_configured("") is False
    assert search.search_configured("key-123") is True
    # With no key, the network path is never taken and it returns [].
    assert search.search_local_businesses("cafe", "Minot", api_key="") == []


def test_placelead_defaults():
    lead = PlaceLead(name="X")
    assert lead.address == "" and lead.phone == "" and lead.website == ""
