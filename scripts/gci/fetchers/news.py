"""World news: GDELT DOC 2.0 API + RSS feeds."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from ..http import get, parse_rss
from ..models import Article, SourceResult

log = logging.getLogger("gci.news")


def fetch_gdelt(geo_cfg: dict) -> SourceResult:
    g = geo_cfg["gdelt"]
    try:
        resp = get("https://api.gdeltproject.org/api/v2/doc/doc", params={
            "query": g["query"], "mode": "artlist", "format": "json",
            "maxrecords": g["maxrecords"], "timespan": g["timespan"], "sort": "hybridrel",
        }, timeout=30, retries=1)  # GDELT allows 1 req / 5 s per IP; retrying from shared CI IPs only adds 429s
        try:
            payload = resp.json()
        except ValueError:
            # GDELT answers rate limits / bad queries with plain text
            raise RuntimeError(resp.text.strip()[:120]) from None
        if not payload.get("articles"):
            raise RuntimeError("empty response (no articles)")
        articles = []
        for a in payload["articles"]:
            seen = a.get("seendate")
            published = None
            if seen:
                try:
                    published = datetime.strptime(seen, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
                except ValueError:
                    pass
            articles.append(Article(title=a.get("title", ""), source=a.get("domain") or "GDELT",
                                    link=a.get("url", ""), published=published))
        return SourceResult("GDELT DOC 2.0", "geo", True, articles, optional=True)
    except Exception as exc:  # noqa: BLE001
        log.warning("GDELT failed: %s", exc)
        return SourceResult("GDELT DOC 2.0", "geo", False, None, error=str(exc)[:200], optional=True)


def fetch_rss_news(geo_cfg: dict) -> list[SourceResult]:
    results = []
    for feed in geo_cfg["rss"]:
        try:
            items = parse_rss(get(feed["url"]).content)
            arts = [Article(title=i["title"], source=feed["name"], link=i["link"],
                            summary=i["summary"], published=i["published"]) for i in items]
            results.append(SourceResult(feed["name"], "geo", True, arts))
        except Exception as exc:  # noqa: BLE001
            log.warning("RSS %s failed: %s", feed["name"], exc)
            results.append(SourceResult(feed["name"], "geo", False, None, error=str(exc)[:200]))
    return results
