"""Network fetchers. Each returns SourceResult and never raises."""

from .markets import fetch_markets
from .news import fetch_gdelt, fetch_rss_news
from .hazards import fetch_usgs, fetch_gdacs
from .health_cyber import fetch_who, fetch_cisa

__all__ = [
    "fetch_markets", "fetch_gdelt", "fetch_rss_news",
    "fetch_usgs", "fetch_gdacs", "fetch_who", "fetch_cisa",
]
