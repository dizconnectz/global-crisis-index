"""HTTP helpers with timeout + exponential retry backoff."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import requests
from defusedxml.ElementTree import fromstring as safe_fromstring

log = logging.getLogger("gci.http")

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/130.0 Safari/537.36 GlobalCrisisIndex/1.0"
)
DEFAULT_TIMEOUT = 20


def get(url: str, *, params=None, timeout: int = DEFAULT_TIMEOUT, retries: int = 3,
        backoff: float = 2.0, headers: dict | None = None) -> requests.Response:
    """GET with retry on network errors, 429 and 5xx. Other 4xx (403, 404…) are
    permanent for this run, so they fail immediately instead of wasting retries."""
    hdrs = {"User-Agent": USER_AGENT, "Accept": "*/*"}
    if headers:
        hdrs.update(headers)
    last_exc: Exception | None = None
    for attempt in range(retries):
        try:
            resp = requests.get(url, params=params, timeout=timeout, headers=hdrs)
            if resp.status_code == 429 or resp.status_code >= 500:
                raise requests.HTTPError(f"HTTP {resp.status_code}", response=resp)
            resp.raise_for_status()
            return resp
        except requests.RequestException as exc:
            status = getattr(getattr(exc, "response", None), "status_code", None)
            if status is not None and 400 <= status < 500 and status != 429:
                raise
            last_exc = exc
            if attempt < retries - 1:
                wait = backoff * (2 ** attempt)
                log.warning("GET %s failed (%s), retry in %.0fs", url[:80], exc, wait)
                time.sleep(wait)
    assert last_exc is not None
    raise last_exc


def _parse_date(text: str | None) -> datetime | None:
    if not text:
        return None
    text = text.strip()
    try:
        dt = parsedate_to_datetime(text)
    except (TypeError, ValueError):
        try:
            dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def parse_rss(xml_bytes: bytes) -> list[dict]:
    """Minimal RSS 2.0 / Atom parser -> [{title, link, summary, published, raw}].

    Feeds are untrusted input, so parsing goes through defusedxml (blocks entity
    expansion and external entity tricks)."""
    root = safe_fromstring(xml_bytes)
    items: list[dict] = []
    atom = "{http://www.w3.org/2005/Atom}"
    nodes = root.findall(".//item") or root.findall(f".//{atom}entry")
    for node in nodes:
        def text(tag: str) -> str:
            el = node.find(tag)
            if el is None:
                el = node.find(f"{atom}{tag}")
            return (el.text or "").strip() if el is not None and el.text else ""

        link = text("link")
        if not link:
            link_el = node.find(f"{atom}link")
            link = link_el.get("href", "") if link_el is not None else ""
        published = _parse_date(text("pubDate") or text("published") or text("updated"))
        items.append({
            "title": text("title"),
            "link": link,
            "summary": text("description") or text("summary"),
            "published": published,
            "raw": node,
        })
    return items
