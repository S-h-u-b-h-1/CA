"""
Tests for the real (non-mock) government-update connectors added in
app/services/connectors/sources/real_sources.py.

These mock the HTTP layer (real_sources.fetch) with fixture content that
mirrors the ACTUAL structure of each live source, as verified by directly
fetching them on 2026-07-01/02 (see docs/CONNECTOR_ARCHITECTURE.md). This
keeps the test suite deterministic and network-independent while still
exercising the real parsing logic against real-shaped data - not fabricated
convenience formats.
"""
import types
import pytest

from app.services.connectors.sources import real_sources as rs
from app.services.connectors.sources.real_sources import (
    parse_rss_date,
    stable_doc_id,
    CBICUnavailableConnector,
    MCAUnavailableConnector,
    RSSConnector,
    IncomeTaxLatestNewsConnector,
    GSTCouncilRealConnector,
    ICAIAnnouncementsRealConnector,
)


def _fake_response(content_bytes=None, text=None):
    resp = types.SimpleNamespace()
    resp.content = content_bytes if content_bytes is not None else (text or "").encode("utf-8")
    resp.text = text if text is not None else (content_bytes or b"").decode("utf-8", errors="ignore")
    return resp


# --- date parsing -----------------------------------------------------------

def test_parse_rss_date_rfc822():
    dt = parse_rss_date("Wed, 01 Jul 2026 19:00:00 GMT")
    assert dt.year == 2026 and dt.month == 7 and dt.day == 1


def test_parse_rss_date_sebi_variant():
    # SEBI's actual format lacks a weekday and time, and has a comma - not
    # strict RFC-822, confirmed via direct fetch during development.
    dt = parse_rss_date("01 Jul, 2026 +0530")
    assert dt is not None
    assert dt.year == 2026 and dt.month == 7 and dt.day == 1


def test_parse_rss_date_garbage_returns_none():
    assert parse_rss_date("not a date") is None
    assert parse_rss_date("") is None


def test_stable_doc_id_deterministic():
    a = stable_doc_id("https://example.com/x")
    b = stable_doc_id("https://example.com/x")
    c = stable_doc_id("https://example.com/y")
    assert a == b
    assert a != c


# --- UnavailableConnector (CBIC / MCA) --------------------------------------

def test_unavailable_connector_never_fabricates_data():
    for conn in (CBICUnavailableConnector(), MCAUnavailableConnector()):
        assert conn.discover(db=None) == []
        assert conn.health_check() == "DOWN"
        assert conn.unavailable_reason  # a real, non-empty explanation must be present


# --- RSS parsing (RBI / SEBI shape) -----------------------------------------

SAMPLE_RSS = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
<title>Sample Feed</title>
<item>
<title>Master Direction on Sample Regulation</title>
<link>https://example.gov.in/notice?id=123</link>
<description>Summary of the sample regulation change.</description>
<pubDate>Wed, 01 Jul 2026 19:00:00 GMT</pubDate>
</item>
<item>
<title>Second Sample Notice</title>
<link>https://example.gov.in/notice?id=124</link>
<description>Another summary.</description>
<pubDate>Tue, 30 Jun 2026 10:00:00 GMT</pubDate>
</item>
</channel>
</rss>
"""


def test_rss_connector_parses_items(monkeypatch):
    monkeypatch.setattr(rs, "fetch", lambda url: _fake_response(content_bytes=SAMPLE_RSS))

    class DummyRSS(RSSConnector):
        feed_url = "https://example.gov.in/feed.xml"
        def get_name(self): return "Dummy RSS"
        def get_authority(self): return "Dummy Authority"
        def get_category(self): return "Dummy Category"

    conn = DummyRSS()
    items = conn.discover(db=None)
    assert len(items) == 2
    assert items[0]["title"] == "Master Direction on Sample Regulation"
    assert items[0]["source_url"] == "https://example.gov.in/notice?id=123"
    meta = conn._meta_cache[items[0]["source_url"]]
    assert meta["issue_date"].year == 2026 and meta["issue_date"].month == 7

    # download() returns the cached per-item content, not a re-fetch
    content = conn.download(items[0]["source_url"])
    assert b"Summary of the sample regulation change" in content

    # extract_metadata threads the real issue_date through via the url stashed by download()
    meta_out = conn.extract_metadata(content, content.decode("utf-8"))
    assert meta_out["issue_date"].year == 2026


def test_rss_connector_health_check_reflects_fetch_failure(monkeypatch):
    def boom(url):
        raise ConnectionError("simulated network failure")
    monkeypatch.setattr(rs, "fetch", boom)

    class DummyRSS(RSSConnector):
        feed_url = "https://example.gov.in/feed.xml"
        def get_name(self): return "Dummy RSS"
        def get_authority(self): return "Dummy Authority"
        def get_category(self): return "Dummy Category"

    conn = DummyRSS()
    assert conn.health_check() == "DOWN"
    assert conn.discover(db=None) == []


# --- Income Tax / CBDT HTML listing (real verified structure) --------------

SAMPLE_INCOMETAX_HTML = """
<div class="view-content">
  <div class="views-row"><div class="views-field views-field-nothing-1"><span class="field-content">
    <div class="d-flex"><div class="up-date"> 30-Jun-2026</div></div>
    <div class="d-flex gry-ft"> <p>Second set of Statutory forms as per Income Tax Rules, 2026 have been rolled out.</p></div>
  </span></div></div>
  <div class="views-row"><div class="views-field views-field-nothing-1"><span class="field-content">
    <div class="d-flex"><div class="up-date"> 23-Jun-2026</div></div>
    <div class="d-flex gry-ft"> <p>Offline Utility for ITR-3 for AY 2026-27 is available for filing. <a href="https://www.incometax.gov.in/iec/foportal/downloads/income-tax-returns">Click here</a></p></div>
  </span></div></div>
</div>
"""


def test_income_tax_connector_parses_real_shaped_html(monkeypatch):
    monkeypatch.setattr(rs, "fetch", lambda url: _fake_response(text=SAMPLE_INCOMETAX_HTML))
    conn = IncomeTaxLatestNewsConnector()
    items = conn.discover(db=None)
    assert len(items) == 2
    assert "Second set of Statutory forms" in items[0]["title"]
    meta = conn._meta_cache[items[0]["source_url"]]
    assert meta["issue_date"].strftime("%Y-%m-%d") == "2026-06-30"
    # the second item's link is extracted from the embedded <a href>
    assert items[1]["source_url"] == "https://www.incometax.gov.in/iec/foportal/downloads/income-tax-returns"


def test_income_tax_connector_health_check_down_on_fetch_error(monkeypatch):
    def boom(url):
        raise ConnectionError("simulated")
    monkeypatch.setattr(rs, "fetch", boom)
    conn = IncomeTaxLatestNewsConnector()
    assert conn.health_check() == "DOWN"
    assert conn.discover(db=None) == []


# --- GST Council table listing (real verified structure) -------------------

SAMPLE_GSTCOUNCIL_HTML = """
<table><tbody>
<tr>
<td class="views-field views-field-counter">1</td>
<td class="views-field views-field-title"><a href="/sites/default/files/2026-02/newsletter_january_issue_0.pdf"> 82nd Edition GSTC Newsletter January 2026</a></td>
</tr>
<tr>
<td class="views-field views-field-counter">2</td>
<td class="views-field views-field-title"><a href="/sites/default/files/2026-02/vacancy_circular_0.pdf"> Appointment of Consultant</a></td>
</tr>
</tbody></table>
"""


def test_gst_council_connector_parses_real_shaped_html(monkeypatch):
    monkeypatch.setattr(rs, "fetch", lambda url: _fake_response(text=SAMPLE_GSTCOUNCIL_HTML))
    conn = GSTCouncilRealConnector()
    items = conn.discover(db=None)
    assert len(items) == 2
    assert "82nd Edition GSTC Newsletter" in items[0]["title"]
    assert items[0]["source_url"].startswith("https://gstcouncil.gov.in/sites/default/files/2026-02/")
    meta = conn._meta_cache[items[0]["source_url"]]
    # no explicit date column - year/month is derived from the PDF upload path
    assert meta["issue_date"].strftime("%Y-%m") == "2026-02"


# --- ICAI list-group listing (real verified structure) ----------------------

SAMPLE_ICAI_HTML = """
<div class="shadow">
<ul class="list-group">
<li class='list-group-item'><a href='https://resource.cdn.icai.org/92971prb-aps5709-web-portal.pdf'>Launch of PRB Web Portal for the Peer Review Process. - (01-07-2026)</a></li>
<li class='list-group-item'><a href='https://resource.cdn.icai.org/92932bos-aps5693-fnd-mtp-sep2026.pdf'>Mock Test Papers Series - I & II - (29-06-2026)</a></li>
</ul>
</div>
"""


def test_icai_connector_parses_real_shaped_html(monkeypatch):
    monkeypatch.setattr(rs, "fetch", lambda url: _fake_response(text=SAMPLE_ICAI_HTML))
    conn = ICAIAnnouncementsRealConnector()
    items = conn.discover(db=None)
    assert len(items) == 2
    assert items[0]["title"] == "Launch of PRB Web Portal for the Peer Review Process."
    meta = conn._meta_cache[items[0]["source_url"]]
    assert meta["issue_date"].strftime("%Y-%m-%d") == "2026-07-01"
