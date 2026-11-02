"""Health + critical infrastructure: WHO Disease Outbreak News and CISA advisories."""

from __future__ import annotations

import logging

from ..http import _parse_date, get, parse_rss
from ..models import Article, SourceResult

log = logging.getLogger("gci.health_cyber")


def fetch_who(bio_cfg: dict) -> SourceResult:
    """WHO DON JSON API first; fall back to the general WHO news RSS."""
    try:
        payload = get(bio_cfg["who_api"], headers={"Accept": "application/json"}).json()
        arts = []
        for item in payload.get("value", []):
            title = item.get("Title") or item.get("OverrideTitle") or ""
            summary = " ".join(filter(None, [item.get("Summary"), item.get("Overview")]))
            url_name = item.get("UrlName") or item.get("ItemDefaultUrl") or ""
            link = f"https://www.who.int/emergencies/disease-outbreak-news/item/{url_name.strip('/')}" if url_name else ""
            arts.append(Article(title=f"Disease Outbreak News: {title}", source="WHO DON", link=link,
                                summary=summary[:600],
                                published=_parse_date(item.get("PublicationDateAndTime") or item.get("PublicationDate"))))
        if arts:
            return SourceResult("WHO Disease Outbreak News", "bio_infra", True, arts)
        raise ValueError("empty DON payload")
    except Exception as exc:  # noqa: BLE001
        log.warning("WHO DON API failed (%s), trying RSS", exc)
    try:
        items = parse_rss(get(bio_cfg["who_rss"]).content)
        arts = [Article(title=i["title"], source="WHO", link=i["link"], summary=i["summary"][:600],
                        published=i["published"]) for i in items]
        return SourceResult("WHO Disease Outbreak News", "bio_infra", True, arts, note="rss_fallback")
    except Exception as exc:  # noqa: BLE001
        log.warning("WHO RSS failed: %s", exc)
        return SourceResult("WHO Disease Outbreak News", "bio_infra", False, None, error=str(exc)[:200])


def fetch_cisa(bio_cfg: dict) -> SourceResult:
    try:
        items = parse_rss(get(bio_cfg["cisa_rss"]).content)
        arts = [Article(title=i["title"], source="CISA", link=i["link"], summary=i["summary"][:600],
                        published=i["published"]) for i in items]
        return SourceResult("CISA Cybersecurity Alerts", "bio_infra", True, arts)
    except Exception as exc:  # noqa: BLE001
        log.warning("CISA failed: %s", exc)
        return SourceResult("CISA Cybersecurity Alerts", "bio_infra", False, None, error=str(exc)[:200])
