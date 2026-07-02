"""
Real (non-mock) government/authority update connectors.

Every source URL and HTML/RSS structure referenced here was independently
verified by actually fetching it (not assumed from training data) as of
2026-07-02. See docs/CONNECTOR_ARCHITECTURE.md for the verification notes.

Two of the originally-requested eight authorities (CBIC, MCA) have NO
currently-reachable public feed or API - their sites either serve a
JavaScript-only SPA with no server-rendered content, return HTTP 500 from
an undocumented internal API, or are blocked entirely by an edge WAF (even
robots.txt returns 403). Rather than fabricate a connector against sources
that don't work, UnavailableConnector reports this honestly: discover()
always returns an empty list (zero fabricated updates) and health_check()
returns "DOWN", which the existing sync() pipeline in base.py already
surfaces as a clean, logged failure with 0 documents downloaded.
"""
import re
import hashlib
import logging
import xml.etree.ElementTree as ET
from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import Any, Dict, List, Optional

import httpx
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

from app.services.connectors.base import BaseConnector

logger = logging.getLogger(__name__)

USER_AGENT = (
    "CA-Intelligence-UpdatesBot/1.0 "
    "(+https://ca-intel.vercel.app; regulatory update aggregator for a CA practice tool)"
)
FETCH_TIMEOUT = 20.0


def fetch(url: str) -> httpx.Response:
    """Fetch a URL with a descriptive User-Agent and a real browser-like Accept
    header (several of these sites block/challenge default-UA clients)."""
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml,*/*;q=0.9",
    }
    with httpx.Client(follow_redirects=True, timeout=FETCH_TIMEOUT, headers=headers) as client:
        resp = client.get(url)
        resp.raise_for_status()
        return resp


def stable_doc_id(url: str) -> str:
    """Derive a stable pseudo document-number from a URL, for sources that
    don't publish an explicit circular/notification number."""
    return hashlib.sha1(url.encode("utf-8")).hexdigest()[:16]


def parse_rss_date(raw: str) -> Optional[datetime]:
    """Parse an RSS pubDate, trying strict RFC-822 first (RBI) then a
    fallback for non-standard variants observed in the wild, e.g. SEBI's
    '01 Jul, 2026 +0530' (comma after day+month, no time component).

    Deliberately keeps the date/time AS PUBLISHED (drops tzinfo without
    converting to UTC) rather than normalizing to UTC: these are all Indian
    regulatory sources publishing IST dates, and converting to UTC would
    shift the calendar date backwards for anything published before 5:30am
    IST (e.g. a genuine "01-Jul-2026" filing would otherwise show as
    "30-Jun-2026" in the database) - the published calendar date is what a
    CA actually needs, not UTC precision.
    """
    if not raw:
        return None
    try:
        dt = parsedate_to_datetime(raw)
        return dt.replace(tzinfo=None)
    except (TypeError, ValueError):
        pass
    try:
        dt = datetime.strptime(raw.replace(",", ""), "%d %b %Y %z")
        return dt.replace(tzinfo=None)
    except ValueError:
        return None


class RealConnectorBase(BaseConnector):
    """Shared plumbing for real connectors.

    download() returns content captured during discover() (the RSS item's
    own description, or the HTML listing row's own text) rather than
    re-fetching each linked page separately - most linked targets are PDFs
    or external pages outside this batch's scope, and the listing entry
    itself already carries real title/date content worth storing.

    extract_metadata() needs the real publish date, but the base sync()
    pipeline only passes it (content, text) - not the source URL. Since
    download(url) and extract_metadata(content, text) are always called
    back-to-back for the same item inside sync()'s single-threaded loop,
    download() stashes the url so extract_metadata() can look up the
    matching cached metadata (including the real parsed issue_date).
    """

    def __init__(self):
        self._content_cache: Dict[str, bytes] = {}
        self._meta_cache: Dict[str, Dict[str, Any]] = {}
        self._last_url: Optional[str] = None

    def download(self, url: str) -> bytes:
        self._last_url = url
        return self._content_cache.get(url, b"")

    def validate(self, content: bytes) -> bool:
        return len(content) > 0

    def normalize(self, text: str) -> str:
        return text.strip()

    def get_version(self, db: Session, doc_num: str) -> int:
        return 1

    def requires_auth(self) -> bool:
        return False

    def schedule(self) -> str:
        return "DAILY"

    def get_official_url(self) -> str:
        # Works automatically for RSSConnector (feed_url) and the HTML
        # listing connectors (LISTING_URL) without needing a per-class override.
        return getattr(self, "feed_url", None) or getattr(self, "LISTING_URL", None) or super().get_official_url()

    def extract_metadata(self, content: bytes, text: str) -> Dict[str, Any]:
        meta = self._meta_cache.get(self._last_url or "", {})
        return {
            "issue_date": meta.get("issue_date"),
            "summary": text[:2000] if text else None,
        }


class UnavailableConnector(RealConnectorBase):
    """Honest placeholder for an authority with no currently-reachable public
    source. Never fabricates data - always returns zero discovered updates."""

    unavailable_reason = "No public source found"

    def discover(self, db: Session) -> List[Dict[str, Any]]:
        logger.info("%s: no live source available - %s", self.get_name(), self.unavailable_reason)
        return []

    def health_check(self) -> str:
        return "DOWN"

    def get_rate_limits(self) -> str:
        return "N/A - no source connected"


class RSSConnector(RealConnectorBase):
    """Generic RSS 2.0 connector: fetch, parse <item> elements, cache each
    item's own description as its content."""

    feed_url: str = ""
    poll_note: str = "1/hour"

    def discover(self, db: Session) -> List[Dict[str, Any]]:
        self._content_cache = {}
        self._meta_cache = {}
        try:
            resp = fetch(self.feed_url)
        except Exception:
            logger.exception("%s: failed to fetch RSS feed %s", self.get_name(), self.feed_url)
            return []

        try:
            root = ET.fromstring(resp.content)
        except ET.ParseError:
            logger.exception("%s: failed to parse RSS feed", self.get_name())
            return []

        items = []
        for entry in root.iter("item"):
            title = (entry.findtext("title") or "").strip()
            link = (entry.findtext("link") or "").strip()
            desc = (entry.findtext("description") or "").strip()
            pub_date_raw = (entry.findtext("pubDate") or "").strip()
            if not title or not link:
                continue

            issue_date = parse_rss_date(pub_date_raw)

            doc_num = stable_doc_id(link)
            content = (desc or title).encode("utf-8", errors="ignore")
            self._content_cache[link] = content
            self._meta_cache[link] = {"issue_date": issue_date}

            items.append({
                "document_number": doc_num,
                "title": title,
                "source_url": link,
            })
        return items

    def health_check(self) -> str:
        try:
            fetch(self.feed_url)
            return "HEALTHY"
        except Exception:
            return "DOWN"

    def get_rate_limits(self) -> str:
        return self.poll_note


class RBINotificationsRealConnector(RSSConnector):
    feed_url = "https://www.rbi.org.in/notifications_rss.xml"
    poll_note = "1 per 15-30 minutes (feed cache-control max-age=20s, but RBI updates a few times/day)"

    def get_name(self) -> str: return "RBI Notifications"
    def get_authority(self) -> str: return "Reserve Bank of India (RBI)"
    def get_category(self) -> str: return "Banking Regulation"


class SEBICircularsRealConnector(RSSConnector):
    feed_url = "https://www.sebi.gov.in/sebirss.xml"
    poll_note = "1/hour (feed <ttl>60</ttl> signals a 60 minute publisher refresh interval)"

    def get_name(self) -> str: return "SEBI Circulars"
    def get_authority(self) -> str: return "Securities and Exchange Board of India (SEBI)"
    def get_category(self) -> str: return "Securities Law"


class IncomeTaxLatestNewsConnector(RealConnectorBase):
    """Income Tax Department / CBDT. Legacy incometaxindia.gov.in (which hosts
    a dedicated numbered Circulars/Notifications index) is blocked entirely by
    an Akamai edge WAF (403 on every path, including robots.txt) - verified
    unusable. The current e-filing portal's News & e-Campaigns listing is the
    real, verified-working alternative; it interleaves genuine circulars/
    notifications (linking to a PDF) with operational portal announcements."""

    LISTING_URL = "https://www.incometax.gov.in/iec/foportal/latest-news"

    def get_name(self) -> str: return "Income Tax ERI"
    def get_authority(self) -> str: return "Income Tax Department"
    def get_category(self) -> str: return "Direct Tax"

    def _fetch_rows(self) -> List[Dict[str, Any]]:
        resp = fetch(self.LISTING_URL)
        soup = BeautifulSoup(resp.text, "html.parser")
        rows = []
        for row in soup.select("div.views-row"):
            date_el = row.select_one("div.up-date")
            text_el = row.select_one("div.gry-ft p")
            if not date_el or not text_el:
                continue
            date_str = date_el.get_text(strip=True)
            title = text_el.get_text(strip=True)
            link_el = text_el.find("a", href=True)
            url = link_el["href"] if link_el else self.LISTING_URL
            if url.startswith("/"):
                url = "https://www.incometax.gov.in" + url
            issue_date = None
            try:
                issue_date = datetime.strptime(date_str, "%d-%b-%Y")
            except ValueError:
                pass
            rows.append({"title": title, "url": url, "issue_date": issue_date})
        return rows

    def discover(self, db: Session) -> List[Dict[str, Any]]:
        self._content_cache = {}
        self._meta_cache = {}
        try:
            rows = self._fetch_rows()
        except Exception:
            logger.exception("%s: failed to fetch/parse listing", self.get_name())
            return []

        items = []
        for row in rows:
            url = row["url"]
            doc_num = stable_doc_id(url) if url != self.LISTING_URL else stable_doc_id(row["title"])
            self._content_cache[url] = row["title"].encode("utf-8", errors="ignore")
            self._meta_cache[url] = {"issue_date": row["issue_date"]}
            items.append({"document_number": doc_num, "title": row["title"], "source_url": url})
        return items

    def health_check(self) -> str:
        try:
            fetch(self.LISTING_URL)
            return "HEALTHY"
        except Exception:
            return "DOWN"

    def get_rate_limits(self) -> str:
        return "1-2/day (page cache-control max-age=900; no benefit polling more often)"


class CBDTCircularsRealConnector(IncomeTaxLatestNewsConnector):
    """Same verified real source as Income Tax Department - CBDT circulars
    and notifications are published on the same e-filing portal listing,
    not a separate CBDT-specific feed (confirmed during research: the
    legacy incometaxindia.gov.in CBDT-specific pages are blocked by WAF)."""

    def get_name(self) -> str: return "CBDT Circulars"
    def get_authority(self) -> str: return "Central Board of Direct Taxes (CBDT)"


class GSTCouncilRealConnector(RealConnectorBase):
    """GST Council 'What's New' listing - a Drupal table with no explicit
    date column; the linked PDF's upload-folder path (e.g. /2026-02/) is
    used as a year-month proxy date, verified against real current entries."""

    LISTING_URL = "https://gstcouncil.gov.in/what-s-new"
    DATE_IN_PATH = re.compile(r"/(\d{4})-(\d{2})/")

    def get_name(self) -> str: return "GST Council Updates"
    def get_authority(self) -> str: return "GST Council Secretariat"
    def get_category(self) -> str: return "Indirect Tax"

    def discover(self, db: Session) -> List[Dict[str, Any]]:
        self._content_cache = {}
        self._meta_cache = {}
        try:
            resp = fetch(self.LISTING_URL)
        except Exception:
            logger.exception("%s: failed to fetch listing", self.get_name())
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        items = []
        for cell in soup.select("td.views-field-title"):
            link_el = cell.find("a", href=True)
            if not link_el:
                continue
            title = link_el.get_text(strip=True)
            href = link_el["href"]
            url = href if href.startswith("http") else "https://gstcouncil.gov.in" + href
            if not title or not url:
                continue

            issue_date = None
            m = self.DATE_IN_PATH.search(href)
            if m:
                try:
                    issue_date = datetime(int(m.group(1)), int(m.group(2)), 1)
                except ValueError:
                    pass

            doc_num = stable_doc_id(url)
            self._content_cache[url] = title.encode("utf-8", errors="ignore")
            self._meta_cache[url] = {"issue_date": issue_date}
            items.append({"document_number": doc_num, "title": title, "source_url": url})
        return items

    def health_check(self) -> str:
        try:
            fetch(self.LISTING_URL)
            return "HEALTHY"
        except Exception:
            return "DOWN"

    def get_rate_limits(self) -> str:
        return "few/day (small government site, no CDN-scale capacity - poll conservatively)"


class ICAIAnnouncementsRealConnector(RealConnectorBase):
    """ICAI announcements listing - a <ul>/<li> list where title and date are
    combined in one <a> text as 'Title. - (DD-MM-YYYY)'."""

    LISTING_URL = "https://www.icai.org/category/announcements"
    TITLE_DATE_RE = re.compile(r"^(.*?)\s*-\s*\((\d{2}-\d{2}-\d{4})\)\s*$")

    def get_name(self) -> str: return "ICAI Announcements"
    def get_authority(self) -> str: return "Institute of Chartered Accountants of India"
    def get_category(self) -> str: return "Professional Standards"

    def discover(self, db: Session) -> List[Dict[str, Any]]:
        self._content_cache = {}
        self._meta_cache = {}
        try:
            resp = fetch(self.LISTING_URL)
        except Exception:
            logger.exception("%s: failed to fetch listing", self.get_name())
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        items = []
        for li in soup.select("ul.list-group li.list-group-item"):
            link_el = li.find("a", href=True)
            if not link_el:
                continue
            raw_text = link_el.get_text(strip=True)
            url = link_el["href"]
            if not raw_text or not url:
                continue

            title = raw_text
            issue_date = None
            m = self.TITLE_DATE_RE.match(raw_text)
            if m:
                title = m.group(1).strip()
                try:
                    issue_date = datetime.strptime(m.group(2), "%d-%m-%Y")
                except ValueError:
                    pass

            doc_num = stable_doc_id(url)
            self._content_cache[url] = title.encode("utf-8", errors="ignore")
            self._meta_cache[url] = {"issue_date": issue_date}
            items.append({"document_number": doc_num, "title": title, "source_url": url})
        return items

    def health_check(self) -> str:
        try:
            fetch(self.LISTING_URL)
            return "HEALTHY"
        except Exception:
            return "DOWN"

    def get_rate_limits(self) -> str:
        return "1 per 1-6 hours (no robots.txt exists; be a well-behaved low-frequency crawler)"


class CBICUnavailableConnector(UnavailableConnector):
    unavailable_reason = (
        "cbic.gov.in serves a JS-only Angular SPA with no server-rendered content; "
        "its internal REST API (taxinformation.cbic.gov.in) returns HTTP 500 to external "
        "calls; the only fetchable mirrors (cbic-gst.gov.in, gstcouncil.gov.in/cgst-circulars) "
        "are stale by 1-3.5 years. No live public feed exists as of 2026-07-02."
    )

    def get_name(self) -> str: return "CBIC Circulars"
    def get_authority(self) -> str: return "Central Board of Indirect Taxes and Customs (CBIC)"
    def get_category(self) -> str: return "Indirect Tax"


class MCAUnavailableConnector(UnavailableConnector):
    unavailable_reason = (
        "mca.gov.in is fronted by an Akamai edge WAF that returns HTTP 403 Access Denied "
        "on every path tested, including robots.txt itself. No live public feed exists "
        "as of 2026-07-02."
    )

    def get_name(self) -> str: return "MCA Public Documents"
    def get_authority(self) -> str: return "Ministry of Corporate Affairs (MCA)"
    def get_category(self) -> str: return "Corporate Law"
