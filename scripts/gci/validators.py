"""Data-integrity rules: freshness, last-known-valid fallback, pillar/overall status.

Status vocabulary
  ok             all sources for the pillar answered
  partial        some sources/indicators failed; score uses what remains (or stale values)
  market_closed  weekend: Friday's close is the normal, valid value
  stale          every source failed; using the last known valid value (still within max age)
  degraded       no usable data; pillar excluded from the weighted average
"""

from __future__ import annotations

from datetime import datetime, timedelta

from .models import iso, parse_iso

STATUS_TH = {
    "ok": "ปกติ",
    "partial": "ข้อมูลบางส่วนล่าช้า",
    "market_closed": "ตลาดปิดสุดสัปดาห์",
    "stale": "ใช้ค่าล่าสุดที่ยังไม่หมดอายุ",
    "degraded": "ข้อมูลขาดหาย (ตัดออกจากการเฉลี่ย)",
}


def resolve_pillar(name: str, computed: float | None, sources_ok: list[bool], cache: dict,
                   now: datetime, max_age_hours: float) -> tuple[float | None, str, str | None]:
    """Decide the pillar score + status given which of its sources answered.

    `computed` is what the scorer produced from fresh data (or, for event-state
    pillars, from decayed persisted events when every feed failed).
    """
    last = (cache.get("last_valid") or {}).get(name)
    last_at = parse_iso(last.get("as_of")) if last else None
    last_fresh = bool(last and last_at and now - last_at <= timedelta(hours=max_age_hours))

    if sources_ok and not any(sources_ok):
        if not last_fresh:
            return None, "degraded", "ทุกแหล่งข้อมูลล้มเหลวและไม่มีค่าล่าสุดที่ยังไม่หมดอายุ"
        score = computed if computed is not None else last.get("score")
        return score, "stale", f"ใช้ค่าล่าสุดเมื่อ {last.get('as_of')}"
    if computed is None:
        return None, "degraded", "คำนวณไม่ได้"
    if sources_ok and not all(sources_ok):
        return computed, "partial", "บางแหล่งข้อมูลไม่ตอบสนอง"
    return computed, "ok", None


def remember_valid(cache: dict, name: str, score: float | None, status: str, now: datetime) -> None:
    """Only fresh, measured values become the next run's fallback."""
    if score is not None and status in ("ok", "partial", "market_closed"):
        cache.setdefault("last_valid", {})[name] = {"score": score, "as_of": iso(now)}


def overall_status(pillar_status: dict[str, str]) -> dict:
    values = set(pillar_status.values())
    if values & {"degraded", "stale", "partial"}:
        key = "degraded"
        label = "ข้อมูลบางส่วนล่าช้า"
    elif "market_closed" in values:
        key, label = "market_closed", "ตลาดปิดสุดสัปดาห์"
    else:
        key, label = "ok", "ปกติ"
    return {"key": key, "label_th": label}
