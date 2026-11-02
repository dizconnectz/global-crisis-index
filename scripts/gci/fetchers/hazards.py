"""Natural hazards: USGS earthquakes (GeoJSON) + GDACS alerts (RSS)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from ..http import get, parse_rss
from ..models import SourceResult

log = logging.getLogger("gci.hazards")

USGS_URL = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/4.5_week.geojson"
GDACS_URL = "https://www.gdacs.org/xml/rss.xml"


def fetch_usgs(nat_cfg: dict) -> SourceResult:
    try:
        feats = get(USGS_URL).json().get("features", [])
        quakes = []
        for f in feats:
            p = f.get("properties", {})
            mag = p.get("mag")
            if mag is None or mag < nat_cfg["min_magnitude"]:
                continue
            lon, lat = f["geometry"]["coordinates"][:2]
            quakes.append({
                "id": f"usgs:{f.get('id')}",
                "source": "USGS",
                "type": "EQ",
                "title": p.get("title") or f"M{mag} earthquake",
                "place": p.get("place") or "",
                "mag": float(mag),
                "lat": float(lat), "lon": float(lon),
                "alert": (p.get("alert") or "").lower() or None,
                "tsunami": bool(p.get("tsunami")),
                "time": datetime.fromtimestamp(p["time"] / 1000, tz=timezone.utc),
                "link": p.get("url", ""),
                "countries": [],
            })
        return SourceResult("USGS Earthquakes", "nat", True, quakes)
    except Exception as exc:  # noqa: BLE001
        log.warning("USGS failed: %s", exc)
        return SourceResult("USGS Earthquakes", "nat", False, None, error=str(exc)[:200])


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower()


def fetch_gdacs(nat_cfg: dict) -> SourceResult:
    try:
        items = parse_rss(get(GDACS_URL).content)
        alerts = []
        for it in items:
            fields: dict[str, str] = {}
            for child in it["raw"].iter():
                if child.text and child.text.strip():
                    fields.setdefault(_local(child.tag), child.text.strip())
            if fields.get("iscurrent", "true").lower() == "false":
                continue
            lat = lon = None
            if "lat" in fields and "long" in fields:
                lat, lon = float(fields["lat"]), float(fields["long"])
            elif "point" in fields:
                parts = fields["point"].split()
                if len(parts) == 2:
                    lat, lon = float(parts[0]), float(parts[1])
            countries = [c.strip() for c in fields.get("country", "").split(",") if c.strip()]
            etype = fields.get("eventtype", "").upper()
            alerts.append({
                "id": f"gdacs:{etype}{fields.get('eventid', it['title'][:40])}",
                "source": "GDACS",
                "type": etype,
                "title": it["title"],
                "place": ", ".join(countries),
                "mag": None,
                "lat": lat, "lon": lon,
                "alert": fields.get("alertlevel", "").lower() or None,
                "tsunami": False,
                "time": it["published"],
                "link": it["link"],
                "countries": countries,
            })
        return SourceResult("GDACS Alerts", "nat", True, alerts)
    except Exception as exc:  # noqa: BLE001
        log.warning("GDACS failed: %s", exc)
        return SourceResult("GDACS Alerts", "nat", False, None, error=str(exc)[:200])
