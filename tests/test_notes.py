"""Tests for the notes inbox + playbook (pure; no LLM)."""

from __future__ import annotations

from agents import notes


def test_load_notes_placeholder_is_empty(tmp_path):
    f = tmp_path / "STUDIO_NOTES.md"
    f.write_text("# Notes\nblah\n---\n<!-- write-below -->\n", encoding="utf-8")
    assert notes.load_notes(str(f)) == ""


def test_load_notes_reads_real_note(tmp_path):
    f = tmp_path / "STUDIO_NOTES.md"
    f.write_text("Buffalo sold at the fair. Chase Koselig on Tuesday.", encoding="utf-8")
    assert "Koselig" in notes.load_notes(str(f))


def test_load_notes_missing_file(tmp_path):
    assert notes.load_notes(str(tmp_path / "nope.md")) == ""


def test_append_playbook_creates_and_appends(tmp_path):
    p = tmp_path / "PLAYBOOK.md"
    assert notes.append_playbook("Vet lobby placements convert to portrait commissions.",
                                 str(p), today="2026-08-27") is True
    text = notes.load_playbook(str(p))
    assert "## 2026-08-27" in text
    assert "Vet lobby" in text
    # A second learning appends without clobbering the first.
    notes.append_playbook("Cafés want statement pieces, not small ones.", str(p),
                          today="2026-08-28")
    text2 = notes.load_playbook(str(p))
    assert "Vet lobby" in text2 and "Cafés want" in text2


def test_append_playbook_ignores_empty(tmp_path):
    p = tmp_path / "PLAYBOOK.md"
    assert notes.append_playbook("   ", str(p)) is False
    assert notes.load_playbook(str(p)) == ""
