"""Tests for the style-bible / voice loader (pure; no LLM)."""

from __future__ import annotations

from agents import voice


def test_default_when_missing(tmp_path, monkeypatch):
    monkeypatch.delenv("ART_MANAGER_STYLE_BIBLE", raising=False)
    missing = tmp_path / "nope.md"
    assert voice.load_style_bible(str(missing)) == voice.DEFAULT_STYLE_BIBLE


def test_loads_file_when_present(tmp_path):
    f = tmp_path / "STYLE_BIBLE.md"
    f.write_text("# My Voice\nSound like me.", encoding="utf-8")
    assert voice.load_style_bible(str(f)) == "# My Voice\nSound like me."


def test_empty_file_falls_back(tmp_path):
    f = tmp_path / "STYLE_BIBLE.md"
    f.write_text("   \n", encoding="utf-8")
    assert voice.load_style_bible(str(f)) == voice.DEFAULT_STYLE_BIBLE


def test_env_override(tmp_path, monkeypatch):
    f = tmp_path / "custom.md"
    f.write_text("custom voice", encoding="utf-8")
    monkeypatch.setenv("ART_MANAGER_STYLE_BIBLE", str(f))
    assert voice.load_style_bible() == "custom voice"


def test_default_bible_has_substance():
    # Guardrails the prompt depends on.
    assert "Minot" in voice.DEFAULT_STYLE_BIBLE
    assert "Never use" in voice.DEFAULT_STYLE_BIBLE or "NEVER USE" in voice.DEFAULT_STYLE_BIBLE
