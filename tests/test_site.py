"""Tests for the site reader's pure parser (no network)."""

from __future__ import annotations

from agents.site import fetch_gallery, fetch_site, parse_site

SAMPLE = """
<!doctype html>
<html>
<head>
  <title>Cody Carlson — Art</title>
  <meta name="description" content="Wood carvings and paintings from North Dakota.">
  <script src="/js/config.js"></script>
  <script src="https://cdn.example.com/analytics.js"></script>
</head>
<body>
  <h1>Summer Walleye</h1>
  <p>Box elder carving. Price: $1,200</p>
  <img src="/img/walleye.jpg" alt="Summer Walleye carving">
  <img src="img/buffalo.png" alt="Buffalo painting">
  <a href="mailto:cody@codycarlson.art">Email me</a>
  <a href="tel:701-555-0100">Call</a>
  <a href="/commissions">Commissions</a>
  <style>.x{color:red}</style>
  <script>var hidden = "do not index $9999";</script>
</body>
</html>
"""


def _snap():
    return parse_site(SAMPLE, "https://codycarlson.art/")


def test_title_and_description():
    s = _snap()
    assert s.ok is True
    assert s.title == "Cody Carlson — Art"
    assert "North Dakota" in s.description


def test_images_absolutized_with_alt():
    s = _snap()
    srcs = {i.src for i in s.images}
    assert "https://codycarlson.art/img/walleye.jpg" in srcs
    assert "https://codycarlson.art/img/buffalo.png" in srcs
    assert any(i.alt == "Summer Walleye carving" for i in s.images)


def test_contact_and_price_extraction():
    s = _snap()
    assert "cody@codycarlson.art" in s.emails
    assert any("701" in p for p in s.phones)
    # Visible price captured; price inside <script> is NOT (script text skipped).
    assert "$1,200" in s.prices
    assert "$9999" not in " ".join(s.prices)


def test_links_and_scripts():
    s = _snap()
    assert "https://codycarlson.art/commissions" in s.links
    # mailto/tel are not treated as page links.
    assert not any(l.startswith(("mailto:", "tel:")) for l in s.links)
    assert "https://codycarlson.art/js/config.js" in s.scripts


def test_script_text_excluded_from_visible_text():
    s = _snap()
    assert "do not index" not in s.text
    assert "Summer Walleye" in s.text


def test_fetch_gallery_returns_api_json(monkeypatch):
    payload = '{"galleries":{"featured":["https://example.com/featured.jpg"]},"paintings":[{"title":"Buffalo","price":"230.40"}]}'
    monkeypatch.setattr("agents.site._get", lambda url, timeout: payload)

    assert fetch_gallery("https://codycarlson.art") == {
        "galleries": {"featured": ["https://example.com/featured.jpg"]},
        "paintings": [{"title": "Buffalo", "price": "230.40"}],
    }


def test_fetch_site_reads_public_page_and_grounds_with_gallery(monkeypatch):
    # The public page a buyer loads (a client-rendered SPA shell) + the gallery
    # API the page uses to fill in its catalog.
    page_html = (
        "<!doctype html><html><head><title>Cody Carlson</title>"
        '<meta name="description" content="North Dakota art.">'
        "</head><body><h1>Gallery</h1>"
        '<a href="mailto:cody@codycarlson.art">Email</a></body></html>'
    )
    seen = []

    def fake_get(url, timeout):
        seen.append(url)
        if url.endswith("/api/gallery"):
            return '{"paintings":[{"price":"230.40"}],"galleries":{"featured":["https://example.com/f.jpg"]}}'
        return page_html

    monkeypatch.setattr("agents.site._get", fake_get)

    snapshot = fetch_site("https://codycarlson.art")

    # It reads the REAL public page, not just the admin API.
    assert "https://codycarlson.art" in seen
    assert any(u.endswith("/api/gallery") for u in seen)
    assert snapshot.ok is True
    assert snapshot.url == "https://codycarlson.art"
    assert snapshot.title == "Cody Carlson"
    assert "cody@codycarlson.art" in snapshot.emails
    # Catalog the SPA renders client-side is attached and merged for grounding.
    assert snapshot.gallery_data["paintings"] == [{"price": "230.40"}]
    assert "$230.40" in snapshot.prices
    assert any(i.src == "https://example.com/f.jpg" for i in snapshot.images)


def test_fetch_site_ok_false_when_public_page_unreadable(monkeypatch):
    def boom(url, timeout):
        if url.endswith("/api/gallery"):
            return '{"paintings":[]}'
        raise OSError("connection refused")

    monkeypatch.setattr("agents.site._get", boom)

    snapshot = fetch_site("https://codycarlson.art")
    # Public page couldn't be read → not ok, but gallery data still attached.
    assert snapshot.ok is False
    assert "connection refused" in snapshot.error
    assert snapshot.gallery_data == {"paintings": []}
