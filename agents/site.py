"""
Read the live website so the agent works from what is really there.

``parse_site`` remains a pure, backwards-compatible helper for old snapshots.
Live reads use the site's structured ``/api/gallery`` response instead of
scraping HTML, and degrade gracefully to ``ok=False`` with an ``error``.

Deliberately dependency-free (stdlib ``urllib`` + ``html.parser``) so there's
nothing extra to install.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urljoin
from urllib.request import Request, urlopen

from .models import SiteImage, SiteSnapshot

_PRICE_RE = re.compile(r"\$\s?\d[\d,]*(?:\.\d{2})?")
_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
_PHONE_RE = re.compile(r"(?:\+?1[\s.-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}")
_WS_RE = re.compile(r"\s+")

_SKIP_TEXT_TAGS = {"script", "style", "noscript", "template"}
_USER_AGENT = "ArtManagerAgent/0.1 (+https://codycarlson.art)"
_MAX_SCRIPT_CHARS = 20_000


class _Extractor(HTMLParser):
    """Pull structured bits out of a page: title, meta, text, images, links."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title = ""
        self.description = ""
        self.text_parts: list[str] = []
        self.images: list[SiteImage] = []
        self.links: list[str] = []
        self.scripts: list[str] = []
        self._skip_depth = 0
        self._in_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = {k: (v or "") for k, v in attrs}
        if tag in _SKIP_TEXT_TAGS:
            self._skip_depth += 1
        if tag == "title":
            self._in_title = True
        elif tag == "meta":
            name = a.get("name", "").lower() or a.get("property", "").lower()
            if name in ("description", "og:description") and a.get("content"):
                if not self.description:
                    self.description = a["content"].strip()
        elif tag == "img" and a.get("src"):
            self.images.append(SiteImage(src=a["src"], alt=a.get("alt", "").strip()))
        elif tag == "a" and a.get("href"):
            self.links.append(a["href"])
        elif tag == "script" and a.get("src"):
            self.scripts.append(a["src"])

    def handle_endtag(self, tag: str) -> None:
        if tag in _SKIP_TEXT_TAGS and self._skip_depth > 0:
            self._skip_depth -= 1
        if tag == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title += data
        if self._skip_depth == 0:
            stripped = data.strip()
            if stripped:
                self.text_parts.append(stripped)


def _dedupe(seq: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in seq:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def parse_site(html: str, url: str) -> SiteSnapshot:
    """Parse page HTML into a SiteSnapshot. Pure; no network."""
    ex = _Extractor()
    ex.feed(html)

    text = _WS_RE.sub(" ", " ".join(ex.text_parts)).strip()

    # mailto:/tel: links are the most reliable contact signal; also scan the
    # visible text (not raw HTML) so addresses buried in <script>/<style> bodies
    # aren't mistaken for real contact info, matching how prices/phones are read.
    emails = [l.split(":", 1)[1].split("?")[0] for l in ex.links if l.lower().startswith("mailto:")]
    emails += _EMAIL_RE.findall(text)
    phones = [l.split(":", 1)[1] for l in ex.links if l.lower().startswith("tel:")]
    phones += _PHONE_RE.findall(text)

    return SiteSnapshot(
        url=url,
        fetched_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        ok=True,
        title=_WS_RE.sub(" ", ex.title).strip(),
        description=ex.description,
        text=text,
        images=[SiteImage(src=urljoin(url, i.src), alt=i.alt) for i in ex.images],
        links=_dedupe([urljoin(url, l) for l in ex.links if not l.lower().startswith(("mailto:", "tel:", "javascript:"))]),
        emails=_dedupe([e.strip() for e in emails if e.strip()]),
        phones=_dedupe([p.strip() for p in phones if p.strip()]),
        prices=_dedupe(_PRICE_RE.findall(text)),
        scripts=_dedupe([urljoin(url, s) for s in ex.scripts]),
    )


def _get(url: str, timeout: float) -> str:
    req = Request(url, headers={"User-Agent": _USER_AGENT})
    with urlopen(req, timeout=timeout) as resp:  # noqa: S310 - trusted own site
        charset = resp.headers.get_content_charset() or "utf-8"
        return resp.read().decode(charset, errors="replace")


def fetch_gallery(url: str, *, timeout: float = 15.0) -> dict[str, Any]:
    """Fetch the live gallery JSON from ``url``'s API.

    The response is returned unchanged so the NOOA agent can reason over the
    site's real catalog fields (paintings, galleries, prices, and statuses).
    Network and invalid-JSON failures are represented in a small error object
    rather than raised, matching the reader's resilient behavior.
    """
    api_url = f"{url.rstrip('/')}/api/gallery"
    try:
        payload = json.loads(_get(api_url, timeout))
        if not isinstance(payload, dict):
            raise ValueError("gallery API response must be a JSON object")
        return payload
    except Exception as exc:  # noqa: BLE001 - fetch must be resilient
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}


def fetch_site(
    url: str,
    *,
    timeout: float = 15.0,
    fetch_data_scripts: bool = True,
) -> SiteSnapshot:
    """Read the REAL public page a buyer sees, grounded with catalog data.

    Diagnosis must reflect the public website, not the admin ``/api/gallery``
    endpoint: summarizing the API as if it were the page made the agent report
    problems ("no prices", "no products") that a visitor never actually sees.

    So this fetches the public HTML at ``url`` and parses it (title, meta,
    visible text, images, contact links, prices) exactly as a visitor loads it.
    The site is a client-rendered SPA, so its catalog is filled in by JavaScript
    the raw HTML doesn't contain — we therefore ALSO read the gallery API the
    page itself uses and attach it as ``gallery_data`` (merging its prices and
    images) so the diagnosis knows the inventory the page renders rather than
    calling it missing.

    ``fetch_data_scripts`` is retained as a no-op compatibility argument.
    """
    del fetch_data_scripts

    # 1. The public page a buyer actually loads.
    try:
        snap = parse_site(_get(url, timeout), url)
    except Exception as exc:  # noqa: BLE001 - reader must be resilient
        snap = SiteSnapshot(
            url=url,
            fetched_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            ok=False,
            error=f"{type(exc).__name__}: {exc}",
        )

    # 2. Ground it with the catalog the SPA renders client-side, so the
    #    diagnosis doesn't flag inventory/prices the raw HTML can't show.
    gallery = fetch_gallery(url, timeout=timeout)
    if isinstance(gallery, dict) and gallery.get("ok") is not False:
        snap.gallery_data = gallery
        paintings = gallery.get("paintings", [])
        if isinstance(paintings, list):
            snap.prices = _dedupe(
                snap.prices
                + [
                    f"${p['price']}"
                    for p in paintings
                    if isinstance(p, dict) and p.get("price") not in (None, "")
                ]
            )
        galleries = gallery.get("galleries", {})
        if isinstance(galleries, dict):
            catalog_images = [
                SiteImage(src=img)
                for images in galleries.values()
                if isinstance(images, list)
                for img in images
                if isinstance(img, str)
            ]
            have = {i.src for i in snap.images}
            snap.images = snap.images + [i for i in catalog_images if i.src not in have]

    return snap
