"""Tests for environment-driven configuration."""

from __future__ import annotations

from agents.config import DEFAULT_MODEL, load_config


def test_defaults(monkeypatch):
    # Ensure no ART_MANAGER_* overrides are set.
    for key in list(__import__("os").environ):
        if key.startswith("ART_MANAGER_"):
            monkeypatch.delenv(key, raising=False)
    cfg = load_config()
    assert cfg.model == DEFAULT_MODEL
    assert cfg.github_repo == "codycarlson.art"
    assert cfg.monthly_revenue_goal == 2000.0


def test_env_overrides(monkeypatch):
    monkeypatch.setenv("ART_MANAGER_MODEL", "claude-sonnet-5")
    monkeypatch.setenv("ART_MANAGER_GITHUB_REPO", "example.art")
    monkeypatch.setenv("ART_MANAGER_MONTHLY_REVENUE_GOAL", "5000")
    monkeypatch.setenv("ART_MANAGER_STATE_PATH", "/tmp/state.json")
    cfg = load_config()
    assert cfg.model == "claude-sonnet-5"
    assert cfg.github_repo == "example.art"
    assert cfg.monthly_revenue_goal == 5000.0
    assert cfg.state_path == "/tmp/state.json"
