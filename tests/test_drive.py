"""Tests for optional Google Drive persistence (config detection; no network)."""

from __future__ import annotations

from agents import drive


def _clear_drive(monkeypatch):
    monkeypatch.delenv("ART_MANAGER_DRIVE_CREDENTIALS", raising=False)
    monkeypatch.delenv("GOOGLE_APPLICATION_CREDENTIALS", raising=False)


def test_not_configured_without_credentials(monkeypatch):
    _clear_drive(monkeypatch)
    assert drive.drive_configured() is False


def test_not_configured_when_credentials_path_missing(monkeypatch, tmp_path):
    # A path that doesn't exist must not count as configured.
    monkeypatch.setenv("ART_MANAGER_DRIVE_CREDENTIALS", str(tmp_path / "nope.json"))
    assert drive.drive_configured() is False


def test_save_and_load_noop_when_unconfigured(monkeypatch):
    _clear_drive(monkeypatch)
    # Unconfigured Drive is a graceful no-op, never an exception.
    assert drive.save_json("folder", "state.json", "{}") is False
    assert drive.load_json("folder", "state.json") is None
