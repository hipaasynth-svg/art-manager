"""Tests for the Zoho Mail sender (pure parts; no SMTP)."""

from __future__ import annotations

import pytest

from agents import mail


def _clear_zoho(monkeypatch):
    for key in (
        "ZOHO_MAIL_USER",
        "ZOHO_MAIL_PASSWORD",
        "ZOHO_MAIL_FROM",
        "ZOHO_SMTP_HOST",
        "ZOHO_SMTP_PORT",
    ):
        monkeypatch.delenv(key, raising=False)


def test_build_message():
    msg = mail.build_message("cody@codycarlson.art", "buyer@example.com", "Hi", "Body text")
    assert msg["From"] == "cody@codycarlson.art"
    assert msg["To"] == "buyer@example.com"
    assert msg["Subject"] == "Hi"
    assert msg.get_content().strip() == "Body text"


def test_mail_not_configured_by_default(monkeypatch):
    _clear_zoho(monkeypatch)
    assert mail.mail_configured() is False


def test_mail_configured_needs_both(monkeypatch):
    _clear_zoho(monkeypatch)
    monkeypatch.setenv("ZOHO_MAIL_USER", "cody@codycarlson.art")
    assert mail.mail_configured() is False  # password still missing
    monkeypatch.setenv("ZOHO_MAIL_PASSWORD", "app-pass")
    assert mail.mail_configured() is True


def test_sender_address_prefers_from_alias(monkeypatch):
    _clear_zoho(monkeypatch)
    monkeypatch.setenv("ZOHO_MAIL_USER", "cody@hipaasynth.com")
    # No alias set -> visible From falls back to the login mailbox.
    assert mail.sender_address() == "cody@hipaasynth.com"
    # Alias set -> mail sends AS the alias while login stays the mailbox.
    monkeypatch.setenv("ZOHO_MAIL_FROM", "cody1@codycarlson.art")
    assert mail.sender_address() == "cody1@codycarlson.art"


def test_send_email_raises_when_unconfigured(monkeypatch):
    _clear_zoho(monkeypatch)
    with pytest.raises(RuntimeError):
        mail.send_email("buyer@example.com", "Hi", "Body")


def test_send_email_requires_recipient(monkeypatch):
    _clear_zoho(monkeypatch)
    monkeypatch.setenv("ZOHO_MAIL_USER", "cody@codycarlson.art")
    monkeypatch.setenv("ZOHO_MAIL_PASSWORD", "app-pass")
    with pytest.raises(ValueError):
        mail.send_email("", "Hi", "Body")
