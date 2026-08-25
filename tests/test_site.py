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
  <script>var hidden = "do not index $9999 scriptbot@hidden.example";</script>
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
    # An address that only appears inside a <script> body is not a real contact.
    assert "scriptbot@hidden.example" not in s.emails
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


def test_fetch_site_uses_gallery_endpoint(monkeypatch):
    seen = []
    monkeypatch.setattr(
        "agents.site._get",
        lambda url, timeout: seen.append(url) or '{"paintings":[{"price":"230.40"}]}',
    )

    snapshot = fetch_site("https://codycarlson.art")

    assert seen == ["https://codycarlson.art/api/gallery"]
    assert snapshot.ok is True
    assert snapshot.gallery_data == {"paintings": [{"price": "230.40"}]}
    assert snapshot.prices == ["$230.40"]
