#!/usr/bin/env python3
"""Global Crisis Index — data pipeline entry point.

    python scripts/update_index.py            # fetch live data, write JSON state
    python scripts/update_index.py --dry-run  # fetch + compute, print, write nothing

Writes:
    public/data/latest_state.json   current index (read by the website)
    public/data/history.json        90-day history for the trend chart
    data/state_cache.json           active events, last-known-valid values, AI cache
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from gci import CACHE_PATH, CONFIG_PATH, HISTORY_PATH, LATEST_PATH  # noqa: E402
from gci.fetchers import (fetch_cisa, fetch_gdacs, fetch_gdelt, fetch_markets,  # noqa: E402
                          fetch_rss_news, fetch_usgs, fetch_who)
from gci.models import utcnow  # noqa: E402
from gci.pipeline import build_state  # noqa: E402
from gci.state import load_json, save_json  # noqa: E402

log = logging.getLogger("gci")


def fetch_all(cfg: dict) -> dict:
    with ThreadPoolExecutor(max_workers=6) as pool:
        futs = {
            "markets": pool.submit(fetch_markets, cfg["econ"]),
            "gdelt": pool.submit(fetch_gdelt, cfg["geo"]),
            "rss": pool.submit(fetch_rss_news, cfg["geo"]),
            "usgs": pool.submit(fetch_usgs, cfg["nat"]),
            "gdacs": pool.submit(fetch_gdacs, cfg["nat"]),
            "who": pool.submit(fetch_who, cfg["bio_infra"]),
            "cisa": pool.submit(fetch_cisa, cfg["bio_infra"]),
        }
        return {k: f.result() for k, f in futs.items()}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true", help="compute but do not write files")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    for noisy in ("yfinance", "urllib3", "peewee", "httpx", "google_genai"):
        logging.getLogger(noisy).setLevel(logging.ERROR)

    cfg = load_json(CONFIG_PATH, None)
    if cfg is None:
        log.error("config missing: %s", CONFIG_PATH)
        return 1
    cache = load_json(CACHE_PATH, {})
    history = load_json(HISTORY_PATH, [])

    now = utcnow()
    inputs = fetch_all(cfg)
    for r in [inputs["markets"], inputs["gdelt"], *inputs["rss"], inputs["usgs"], inputs["gdacs"],
              inputs["who"], inputs["cisa"]]:
        n = len(r.data) if isinstance(r.data, (list, dict)) else 0
        log.info("source %-28s %s items=%-4d %s", r.name, "OK " if r.ok else "ERR", n, r.error or "")

    latest, history, cache = build_state(inputs, cfg, cache, history, now)

    p = latest["pillars"]
    log.info("GLOBAL=%s (base=%s boost=%s cross=%s) econ=%s geo=%s nat=%s bio=%s status=%s summary=%s",
             latest["global_score"], latest["formula"]["base"], latest["formula"]["boost"],
             latest["formula"]["cross_confirmed"], p["econ"]["score"], p["geo"]["score"],
             p["nat"]["score"], p["bio_infra"]["score"], latest["data_status"]["key"], latest["summary"]["source"])

    if args.dry_run:
        print(json.dumps(latest, ensure_ascii=False, indent=2)[:4000])
        return 0
    save_json(LATEST_PATH, latest)
    save_json(HISTORY_PATH, history)
    save_json(CACHE_PATH, cache)
    log.info("wrote %s, %s (%d points), %s", LATEST_PATH.name, HISTORY_PATH.name, len(history), CACHE_PATH.name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
