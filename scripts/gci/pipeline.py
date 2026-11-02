"""Turns raw source results into latest_state / history / cache. No network here."""

from __future__ import annotations

from datetime import datetime, timedelta

from . import scoring
from .ai_helper import PILLAR_TH, build_narrative
from .models import Article, Event, SourceResult, iso, parse_iso
from .validators import STATUS_TH, overall_status, remember_valid, resolve_pillar

PILLARS = ("econ", "geo", "nat", "bio_infra")


def _ok_data(results: list[SourceResult]) -> list | None:
    """Concatenate data of successful sources; None if every source failed."""
    good = [r for r in results if r.ok and r.data is not None]
    if not good:
        return None
    out: list = []
    for r in good:
        out.extend(r.data)
    return out


def _metric(label: str, value, unit: str = "", hint: str | None = None) -> dict:
    return {"label_th": label, "value": value, "unit": unit, "hint": hint}


def build_state(inputs: dict, cfg: dict, cache: dict, history: list, now: datetime) -> tuple[dict, list, dict]:
    cache = {**cache}
    cache.setdefault("active_events", {})
    cache.setdefault("last_valid", {})
    max_age = cfg["freshness"]["pillar_last_valid_max_age_hours"]
    sources: list[SourceResult] = [inputs["markets"], inputs["gdelt"], *inputs["rss"],
                                   inputs["usgs"], inputs["gdacs"], inputs["who"], inputs["cisa"]]

    # ---- econ
    mk = inputs["markets"]
    econ = scoring.score_econ(mk.data if mk.ok else None, cfg, cache.get("econ_indicators", {}), now)
    if econ["score"] is None:
        econ_score, econ_status, econ_note = resolve_pillar("econ", None, [False], cache, now, max_age)
    else:
        econ_score, econ_status, econ_note = econ["score"], econ["status"], None
    ind_cache = dict(cache.get("econ_indicators", {}))
    for ind in econ["indicators"]:
        if ind["status"] in ("ok", "market_closed"):
            ind_cache[ind["key"]] = {k: ind[k] for k in ("last", "change_pct", "drawdown_pct", "last_date",
                                                         "as_of", "provider")}
    cache["econ_indicators"] = ind_cache

    # ---- geo
    news_results = [inputs["gdelt"], *inputs["rss"]]
    articles: list[Article] | None = _ok_data(news_results)
    geo = scoring.score_geo(articles, cfg, cache["active_events"].get("geo", {}), now)
    geo_score, geo_status, geo_note = resolve_pillar("geo", geo["score"], [r.ok for r in news_results],
                                                     cache, now, max_age)
    cache["active_events"]["geo"] = geo["state"]

    # ---- nat
    hazards = _ok_data([inputs["usgs"], inputs["gdacs"]])
    nat = scoring.score_nat(hazards, cfg, now)
    nat_score, nat_status, nat_note = resolve_pillar("nat", nat["score"] if hazards is not None else None,
                                                     [inputs["usgs"].ok, inputs["gdacs"].ok], cache, now, max_age)

    # ---- bio / infra
    official = _ok_data([inputs["who"], inputs["cisa"]])
    bio = scoring.score_bio_infra(official, articles, cfg, cache["active_events"].get("bio_infra", {}), now)
    bio_score, bio_status, bio_note = resolve_pillar("bio_infra", bio["score"],
                                                     [inputs["who"].ok, inputs["cisa"].ok], cache, now, max_age)
    cache["active_events"]["bio_infra"] = bio["state"]

    scores = {"econ": econ_score, "geo": geo_score, "nat": nat_score, "bio_infra": bio_score}
    statuses = {"econ": econ_status, "geo": geo_status, "nat": nat_status, "bio_infra": bio_status}
    notes = {"econ": econ_note, "geo": geo_note, "nat": nat_note, "bio_infra": bio_note}
    for p in PILLARS:
        remember_valid(cache, p, scores[p], statuses[p], now)

    comp = scoring.compose(scores, cfg)
    band = scoring.band_for(comp["global_score"], cfg)

    events_by_pillar: dict[str, list[Event]] = {"geo": geo["events"], "nat": nat["events"],
                                                "bio_infra": bio["events"], "econ": []}
    all_events = sorted(geo["events"] + nat["events"] + bio["events"], key=lambda e: e.score, reverse=True)
    local_events = sorted([e for e in nat["events"] + bio["events"]
                           if e.is_local and (e.raw_score or 0) >= 30],
                          key=lambda e: e.raw_score or 0, reverse=True)

    # ---- top drivers
    drivers = []
    for p in PILLARS:
        if scores[p] is None:
            continue
        contrib = comp["effective_weights"][p] * scores[p]
        if p == comp["max1_pillar"]:
            contrib += comp["boost"] or 0
        if p == "econ":
            valid = [i for i in econ["indicators"] if i["score"] is not None]
            top_ind = max(valid, key=lambda i: i["score"]) if valid else None
            headline = f"{top_ind['label_th']} {top_ind['value']:,} {top_ind['unit']}" if top_ind else None
        else:
            top_ev = next((e for e in events_by_pillar[p] if not e.is_local), None)
            headline = f"{top_ev.category_th}: {top_ev.title}" if top_ev else None
        drivers.append({"pillar": p, "label_th": PILLAR_TH[p], "score": scores[p],
                        "contribution": round(contrib, 1), "headline": headline})
    drivers.sort(key=lambda d: d["contribution"], reverse=True)

    # ---- narrative (AI or template)
    econ_inds = [i for i in econ["indicators"]]
    ctx = {
        "global_score": comp["global_score"], "band_label_th": band["label_th"] if band else "ไม่ทราบ",
        "top_drivers": drivers, "events": all_events, "local_events": local_events,
        "cross_confirmed": comp["cross_confirmed"], "boost": comp["boost"] or 0,
        "pillar_scores": scores, "econ_indicators": econ_inds, "max_headlines": cfg["ai"]["max_headlines"],
    }
    summary, ai_cache = build_narrative(ctx, cache.get("ai", {}), now, cfg["ai"])
    cache["ai"] = ai_cache

    # ---- pillar blocks for UI
    nat_events = nat["events"]
    pillar_blocks = {
        "econ": {
            "metrics": [_metric(i["label_th"], i["value"], i["unit"],
                                None if i["change_pct"] is None else f"{i['change_pct']:+.1f}% (5 วันทำการ)")
                        for i in econ["indicators"]],
            "indicators": [{k: v for k, v in i.items() if k not in ("last", "as_of")} for i in econ["indicators"]],
            "coverage": econ["coverage"],
        },
        "geo": {
            "metrics": [
                _metric("เหตุการณ์ที่ติดตามอยู่", len(geo["events"]), "เหตุการณ์"),
                _metric("เหตุการณ์ใหม่รอบนี้", sum(1 for e in geo["events"] if e.is_new), "เหตุการณ์"),
                _metric("บทความที่วิเคราะห์", geo["articles"], "ชิ้น", f"ยุบรวมเหลือ {geo['clusters']} กลุ่มเหตุการณ์"),
            ],
        },
        "nat": {
            "metrics": [
                _metric("แผ่นดินไหว M6.0+ (7 วัน)", sum(1 for e in nat_events if e.category == "earthquake"), "ครั้ง"),
                _metric("GDACS ระดับส้ม/แดง", None if hazards is None else sum(
                    1 for h in hazards if h["source"] == "GDACS" and h.get("alert") in ("orange", "red")), "เหตุการณ์"),
                _metric("ใกล้จุดยุทธศาสตร์โลก", sum(1 for e in nat_events if not e.is_local), "เหตุการณ์"),
                _metric("จำกัดเป็นเหตุการณ์ท้องถิ่น", sum(1 for e in nat_events if e.is_local), "เหตุการณ์"),
            ],
        },
        "bio_infra": {
            "metrics": [
                _metric("เหตุการณ์สุขภาพที่ติดตาม", sum(1 for e in bio["events"] if e.category in
                        ("pheic", "novel_pathogen", "high_consequence", "outbreak")), "เหตุการณ์"),
                _metric("เหตุการณ์ไซเบอร์/ระบบล่ม", sum(1 for e in bio["events"] if e.category in
                        ("cyber_incident", "global_outage")), "เหตุการณ์"),
                _metric("ประกาศช่องโหว่ทั่วไป", sum(1 for e in bio["events"] if e.category == "vuln_advisory"), "รายการ"),
            ],
        },
    }
    pillars_out = {}
    for p in PILLARS:
        pillars_out[p] = {
            "label_th": PILLAR_TH[p], "score": scores[p], "weight": cfg["weights"][p],
            "effective_weight": comp["effective_weights"].get(p), "status": statuses[p],
            "status_th": STATUS_TH[statuses[p]], "note": notes[p],
            "top_events": [e.to_dict() for e in events_by_pillar[p] if not e.is_local][:5],
            **pillar_blocks[p],
        }

    # ---- history (90 days)
    hist = [h for h in history if (parse_iso(h.get("t")) or now) >= now - timedelta(days=cfg["freshness"]["history_days"])]
    if comp["global_score"] is not None:
        point = {"t": iso(now), "score": comp["global_score"], **{p: scores[p] for p in PILLARS}}
        if hist and (now - (parse_iso(hist[-1]["t"]) or now)) < timedelta(minutes=30):
            hist[-1] = point
        else:
            hist.append(point)

    latest = {
        "schema_version": 1,
        "generated_at": iso(now),
        "global_score": comp["global_score"],
        "band": band,
        "formula": {k: comp[k] for k in ("base", "boost", "cross_confirmed", "max1", "max2", "max1_pillar")},
        "pillars": pillars_out,
        "top_drivers": drivers[:3],
        "summary": summary,
        "local_events": [e.to_dict() for e in local_events[:8]],
        "data_status": {**overall_status(statuses), "sources": [s.to_status() for s in sources]},
        "config": {"weights": cfg["weights"], "booster": cfg["booster"], "bands": cfg["bands"],
                   "local_cap": cfg["nat"]["local_cap"], "single_country_cap": cfg["bio_infra"]["single_country_cap"],
                   "hub_radius_km": cfg["nat"]["hub_radius_km"],
                   "strategic_hubs": [h["name_th"] for h in cfg["nat"]["strategic_hubs"]],
                   "decay_per_day": cfg["events"]["decay_per_day"]},
    }
    cache["updated_at"] = iso(now)
    cache["version"] = 1
    return latest, hist, cache
