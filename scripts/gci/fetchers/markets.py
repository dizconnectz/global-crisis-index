"""Market data: yfinance -> Yahoo chart JSON -> FRED CSV, in that order."""

from __future__ import annotations

import csv
import io
import logging
import math
from datetime import datetime, timedelta, timezone

from ..http import get
from ..models import SourceResult

log = logging.getLogger("gci.markets")


def _clean(rows: list[tuple[str, float | None]]) -> list[tuple[str, float]]:
    out = [(d, float(v)) for d, v in rows if v is not None and not math.isnan(float(v)) and float(v) > 0]
    out.sort(key=lambda r: r[0])
    return out


def _from_yfinance(ticker: str) -> list[tuple[str, float]]:
    import yfinance as yf  # imported lazily: optional dependency
    hist = yf.Ticker(ticker).history(period="1y", interval="1d", auto_adjust=False)
    if hist is None or hist.empty:
        raise ValueError("yfinance returned no rows")
    return _clean([(idx.strftime("%Y-%m-%d"), row["Close"]) for idx, row in hist.iterrows()])


def _from_yahoo_chart(ticker: str) -> list[tuple[str, float]]:
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
    data = get(url, params={"range": "1y", "interval": "1d"}, retries=2).json()
    res = data["chart"]["result"][0]
    stamps = res["timestamp"]
    closes = res["indicators"]["quote"][0]["close"]
    return _clean([
        (datetime.fromtimestamp(t, tz=timezone.utc).strftime("%Y-%m-%d"), c)
        for t, c in zip(stamps, closes)
    ])


def _from_fred(series_id: str) -> list[tuple[str, float]]:
    start = (datetime.now(timezone.utc) - timedelta(days=380)).strftime("%Y-%m-%d")
    text = get("https://fred.stlouisfed.org/graph/fredgraph.csv",
               params={"id": series_id, "cosd": start}, retries=2).text
    rows = []
    for rec in csv.reader(io.StringIO(text)):
        if len(rec) < 2 or rec[1] in ("", ".") or not rec[0][:1].isdigit():
            continue
        rows.append((rec[0], float(rec[1])))
    return _clean(rows)


def fetch_series(ticker: str, fred_id: str | None) -> tuple[list[tuple[str, float]], str]:
    errors = []
    attempts = [("yfinance", lambda: _from_yfinance(ticker)),
                ("yahoo_chart", lambda: _from_yahoo_chart(ticker))]
    if fred_id:
        attempts.append(("fred", lambda: _from_fred(fred_id)))
    for name, fn in attempts:
        try:
            rows = fn()
            if len(rows) >= 6:
                return rows, name
            errors.append(f"{name}: only {len(rows)} rows")
        except Exception as exc:  # noqa: BLE001 - any provider failure falls through
            errors.append(f"{name}: {type(exc).__name__}: {str(exc)[:80]}")
    raise RuntimeError("; ".join(errors))


def fetch_markets(econ_cfg: dict) -> SourceResult:
    """data = {indicator_key: {"rows": [(date, close)], "provider": str} | None}"""
    data: dict[str, dict | None] = {}
    errors: list[str] = []
    for key, ind in econ_cfg["indicators"].items():
        try:
            rows, provider = fetch_series(ind["ticker"], ind.get("fred"))
            data[key] = {"rows": rows, "provider": provider}
        except Exception as exc:  # noqa: BLE001
            log.warning("market %s failed: %s", key, exc)
            data[key] = None
            errors.append(f"{key}: {exc}")
    ok = any(v is not None for v in data.values())
    return SourceResult("Market data (Yahoo/FRED)", "econ", ok, data,
                        error="; ".join(errors)[:400] or None)
