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
    assert cfg.search_api_key == ""


def test_search_api_key_override(monkeypatch):
    monkeypatch.setenv("ART_MANAGER_SEARCH_API_KEY", "secret-123")
    assert load_config().search_api_key == "secret-123"


def test_dotenv_file_is_loaded(tmp_path, monkeypatch):
    import pytest

    pytest.importorskip("dotenv")
    monkeypatch.delenv("ART_MANAGER_MODEL", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text("ART_MANAGER_MODEL=from-dotenv\n", encoding="utf-8")

    from agents.config import load_config, load_env

    try:
        assert load_env(str(env_file)) is True
        assert load_config().model == "from-dotenv"
    finally:
        # load_dotenv sets os.environ directly; clean up so other tests are unaffected.
        __import__("os").environ.pop("ART_MANAGER_MODEL", None)


def test_real_env_wins_over_dotenv(tmp_path, monkeypatch):
    import pytest

    pytest.importorskip("dotenv")
    monkeypatch.setenv("ART_MANAGER_MODEL", "real-env")
    env_file = tmp_path / ".env"
    env_file.write_text("ART_MANAGER_MODEL=from-dotenv\n", encoding="utf-8")

    from agents.config import load_config, load_env

    load_env(str(env_file))  # override=False → must not clobber the real value
    assert load_config().model == "real-env"


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
