"""
Studio voice / style bible — the "voice lock".

The single source of truth for how Cody's studio sounds. It is injected into
every agent's system prompt so briefs, captions, outreach, and call scripts come
out on-voice, and off-voice copy gets rejected before it reaches Cody.

Human-editable: the real content lives in ``STYLE_BIBLE.md`` at the repo root
(override the path with ``ART_MANAGER_STYLE_BIBLE``). Cody edits that file; the
condensed ``DEFAULT_STYLE_BIBLE`` below is only a fallback used when the file is
missing, so the agent always has a voice.

nooa-free and dependency-free, so it can be imported and tested without the
agent runtime or an API key.
"""

from __future__ import annotations

import os
from pathlib import Path

# Condensed fallback. The editable, fuller version is STYLE_BIBLE.md.
DEFAULT_STYLE_BIBLE = """\
# Studio Voice — Cody Carlson (Minot, ND)

WHO: Self-taught sculptor, painter, and lapidary artist in Minot, North Dakota.
Wildlife and animal companions — cats, buffalo, walleye, fox, squirrels — in
wood (boxelder, maple), acrylic on canvas, and cut stone. Nine years, 1,000+
pieces. Every piece is a one-of-one original, signed.

VOICE: Plain, warm, maker-first. Talk about the work — the wood grain, the eyes,
the light on the paint — not hype. Sound like a person from North Dakota, not a
gallery brochure. Short sentences. Confident, never salesy.

NEVER USE: "masterpiece", "stunning", "exquisite", "luxury", "exclusive",
"elevate your space", "must-have", emoji spam, ALL CAPS hype, fake scarcity.

ALWAYS TRUE (say when it fits): one-of-one / original / signed; hand-made in
Minot, ND; ships from Minot; wood pieces are outdoor-ready; commissions are open
(a deposit starts the work); prices are the real price on the site.

PRICE BANDS (current): small paintings ~$140–205 · statement paintings
~$225–260 · large paintings ~$525 · sculptures ~$140–550. These are the floor
to begin a commission, not fixed.

FOLLOW-UP: Soft first touch for cold leads ("thought of you — here's the piece").
Direct only for people who already asked ("this one's still available"). Never
push. One personal note beats ten blasts.

LOCAL FACTS THAT MATTER: Minot; Lake Sakakawea / lake country (fishing lodges,
resorts, bars); regional fairs and markets; ND ranch homes and new builds;
downtown Minot gift shops, coffee shops, vet clinics, interior designers.
"""


def style_bible_path() -> str:
    """Path to the editable style bible (override via ART_MANAGER_STYLE_BIBLE)."""
    return os.environ.get("ART_MANAGER_STYLE_BIBLE", "STYLE_BIBLE.md")


def load_style_bible(path: str | None = None) -> str:
    """Return the studio voice text.

    Reads ``STYLE_BIBLE.md`` (or ``path``) when present and non-empty; otherwise
    falls back to ``DEFAULT_STYLE_BIBLE``. Never raises — the agent must always
    have a voice.
    """
    target = Path(path or style_bible_path())
    try:
        text = target.read_text(encoding="utf-8").strip()
    except (OSError, UnicodeDecodeError):
        return DEFAULT_STYLE_BIBLE
    return text or DEFAULT_STYLE_BIBLE
