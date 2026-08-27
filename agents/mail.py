"""
Send approved outreach through Zoho Mail over SMTP.

The standalone agent runs outside Claude, so it can't use a hosted mail
connector — it sends directly via Zoho's SMTP server using an app password kept
in the agent's own environment:

    ZOHO_MAIL_USER=cody@hipaasynth.com        # the real mailbox you log into
    ZOHO_MAIL_PASSWORD=<zoho app password>    # an app password, NOT the login
    # optional — send AS a verified alias on that account (login stays the user):
    ZOHO_MAIL_FROM=cody1@codycarlson.art
    # optional SMTP overrides:
    ZOHO_SMTP_HOST=smtp.zoho.com
    ZOHO_SMTP_PORT=465

The agent DRAFTS outreach (``create_nd_outreach_brief``); a human approves the
copy; only then is ``send_email`` called. When the credentials are absent,
``mail_configured()`` is False and ``send_email`` raises a clear error rather
than silently dropping the message.

Deliberately dependency-free: stdlib ``smtplib`` + ``email``.
"""

from __future__ import annotations

import os
import smtplib
from email.message import EmailMessage

DEFAULT_HOST = "smtp.zoho.com"
DEFAULT_PORT = 465


def _creds() -> tuple[str, str, str, int]:
    user = os.environ.get("ZOHO_MAIL_USER", "").strip()
    password = os.environ.get("ZOHO_MAIL_PASSWORD", "")
    host = os.environ.get("ZOHO_SMTP_HOST", DEFAULT_HOST).strip() or DEFAULT_HOST
    try:
        port = int(os.environ.get("ZOHO_SMTP_PORT", str(DEFAULT_PORT)))
    except ValueError:
        port = DEFAULT_PORT
    return user, password, host, port


def mail_configured() -> bool:
    """True only when both a Zoho user and app password are set."""
    user, password, _, _ = _creds()
    return bool(user and password)


def build_message(sender: str, to: str, subject: str, body: str) -> EmailMessage:
    """Build a plain-text email. Pure; no network."""
    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body or "")
    return msg


def sender_address(user: str | None = None) -> str:
    """The visible From address for outgoing mail.

    Zoho authenticates with the real mailbox (``ZOHO_MAIL_USER``), but you often
    want mail to appear *from* a verified alias on that account — e.g. log in as
    ``cody@hipaasynth.com`` yet send as ``cody1@codycarlson.art``. Set
    ``ZOHO_MAIL_FROM`` to that alias; it must be a verified send-address on the
    account or Zoho rejects the send. Falls back to the login address.
    """
    from_env = os.environ.get("ZOHO_MAIL_FROM", "").strip()
    if from_env:
        return from_env
    return (user if user is not None else _creds()[0])


def send_email(to: str, subject: str, body: str, *, from_addr: str | None = None) -> None:
    """Send one approved outreach email via Zoho SMTP.

    Authenticates as the login mailbox (``ZOHO_MAIL_USER``) but sends *from*
    ``from_addr`` (default: ``ZOHO_MAIL_FROM`` or the login address) — so mail
    can come from a verified alias. The SMTP envelope sender stays the
    authenticated mailbox, which is what Zoho expects.

    Raises ``RuntimeError`` when Zoho isn't configured (so nothing is silently
    dropped) and ``ValueError`` when the recipient is missing.
    """
    user, password, host, port = _creds()
    if not (user and password):
        raise RuntimeError(
            "Zoho Mail is not configured — set ZOHO_MAIL_USER and "
            "ZOHO_MAIL_PASSWORD (an app password) to enable sending."
        )
    if not (to or "").strip():
        raise ValueError("recipient (to) is required")
    sender = (from_addr or "").strip() or sender_address(user)
    msg = build_message(sender, to, subject, body)
    with smtplib.SMTP_SSL(host, port) as smtp:
        smtp.login(user, password)
        # Envelope sender = the authenticated mailbox; visible From = the alias.
        smtp.send_message(msg, from_addr=user, to_addrs=[to])
